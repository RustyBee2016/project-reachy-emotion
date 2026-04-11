"""
Training module for EfficientNet-B0 emotion classifier fine-tuning.

Implements:
- Two-phase training (frozen backbone → selective unfreezing)
- Mixed precision training (FP16)
- Mixup augmentation
- Learning rate scheduling with warmup
- Early stopping
- MLflow integration
- Quality gate validation (Gate A)

Model: HSEmotion enet_b0_8_best_vgaf
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import (
    CosineAnnealingWarmRestarts,
    LinearLR,
    SequentialLR,
    ReduceLROnPlateau,
)
from torch.cuda.amp import GradScaler, autocast
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Any
from datetime import datetime
import numpy as np
import hashlib
import json
import logging

from .config import TrainingConfig
from .model_efficientnet import HSEmotionEfficientNet, create_efficientnet_model
from .dataset import EmotionDataset, get_train_transforms, get_val_transforms, create_dataloaders
from .evaluate import compute_metrics, compute_calibration_metrics

logger = logging.getLogger(__name__)


class EfficientNetTrainer:
    """
    Training orchestrator for EfficientNet-B0 emotion classifier.
    
    Training strategy:
    1. Phase 1 (epochs 1-N): Freeze backbone, train classification head only
    2. Phase 2 (epochs N+1-end): Unfreeze final blocks, fine-tune with lower LR
    
    Features:
    - Mixed precision (FP16) for faster training
    - Mixup augmentation for regularization
    - Cosine LR schedule with warmup
    - Early stopping on validation F1
    - MLflow experiment tracking
    - Quality gate validation (Gate A from requirements)
    """
    
    def __init__(self, config: TrainingConfig, weights_path: Optional[str] = None):
        """
        Initialize trainer.
        
        Args:
            config: Training configuration
            weights_path: Optional explicit path to pretrained weights
        """
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Set seeds for reproducibility
        self._set_seed(config.seed)
        
        # Initialize model
        self.model = create_efficientnet_model(
            num_classes=config.model.num_classes,
            dropout_rate=config.model.dropout_rate,
            pretrained=config.model.pretrained_weights is not None,
            weights_path=weights_path,
            use_multi_task=config.model.use_multi_task,
        ).to(self.device)
        
        # Freeze backbone for Phase 1
        self.model.freeze_backbone()
        
        # Class weights (computed after data loaders are created)
        self.class_weights: Optional[torch.Tensor] = None
        
        # Loss function with label smoothing
        self.criterion = nn.CrossEntropyLoss(
            label_smoothing=config.label_smoothing
        )
        
        # VA loss for multi-task (if enabled)
        if config.model.use_multi_task:
            self.va_criterion = nn.MSELoss()
        else:
            self.va_criterion = None
        
        # Optimizer (only trainable params initially)
        self.optimizer = AdamW(
            filter(lambda p: p.requires_grad, self.model.parameters()),
            lr=config.learning_rate,
            weight_decay=config.weight_decay,
        )
        
        # Learning rate scheduler
        self.scheduler = self._create_scheduler()
        
        # Mixed precision scaler
        self.scaler = GradScaler() if config.mixed_precision else None
        
        # Early stopping state
        self.best_metric = 0.0
        self.patience_counter = 0
        
        # Training state
        self.current_epoch = 0
        self.global_step = 0
        self.training_phase = 1  # 1 = frozen backbone, 2 = fine-tuning
        
        # Data loaders (created lazily)
        self.train_loader: Optional[DataLoader] = None
        self.val_loader: Optional[DataLoader] = None
        
        # MLflow tracking
        self.mlflow_run_id: Optional[str] = None
        
        # Checkpoint resume state
        self.resumed_from: Optional[str] = None
        
        logger.info(f"EfficientNetTrainer initialized on device: {self.device}")
        logger.info(f"Model params: {self.model.get_total_params():,} total, "
                   f"{self.model.get_trainable_params():,} trainable")
    
    def _set_seed(self, seed: int):
        """Set random seeds for reproducibility."""
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        np.random.seed(seed)
        
        if self.config.deterministic:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    
    def _create_scheduler(self):
        """Create learning rate scheduler with warmup."""
        if self.config.lr_scheduler == "cosine":
            warmup_scheduler = LinearLR(
                self.optimizer,
                start_factor=0.1,
                end_factor=1.0,
                total_iters=self.config.warmup_epochs,
            )
            
            main_scheduler = CosineAnnealingWarmRestarts(
                self.optimizer,
                T_0=10,
                T_mult=2,
                eta_min=self.config.min_lr,
            )
            
            return SequentialLR(
                self.optimizer,
                schedulers=[warmup_scheduler, main_scheduler],
                milestones=[self.config.warmup_epochs],
            )
        
        elif self.config.lr_scheduler == "plateau":
            return ReduceLROnPlateau(
                self.optimizer,
                mode='max',
                factor=0.5,
                patience=5,
                min_lr=self.config.min_lr,
            )
        
        else:
            return CosineAnnealingWarmRestarts(
                self.optimizer,
                T_0=self.config.num_epochs,
                eta_min=self.config.min_lr,
            )
    
    def _create_dataloaders(self, run_id: Optional[str] = None):
        """Create train and validation data loaders."""
        self.train_loader, self.val_loader = create_dataloaders(
            data_dir=self.config.data.data_root,
            batch_size=self.config.data.batch_size,
            num_workers=self.config.data.num_workers,
            input_size=self.config.model.input_size,
            class_names=self.config.data.class_names,
            frame_sampling_train="random",
            frame_sampling_val="middle",
            run_id=run_id,
            frames_per_video=max(1, int(self.config.data.frames_per_video)),
            val_dir=getattr(self.config.data, 'val_dir', None),
            val_dataset_type=getattr(self.config.data, 'val_dataset_type', 'emotion'),
        )
        
        logger.info(f"Data loaders created: {len(self.train_loader)} train batches, "
                   f"{len(self.val_loader)} val batches")

        # Compute class weights from training dataset
        if hasattr(self.train_loader.dataset, 'get_class_weights'):
            self.class_weights = self.train_loader.dataset.get_class_weights()
            if self.class_weights is not None:
                self.class_weights = self.class_weights.to(self.device)
                self.criterion = nn.CrossEntropyLoss(
                    weight=self.class_weights,
                    label_smoothing=self.config.label_smoothing
                )
                logger.info(f"Class weights applied: {self.class_weights.cpu().numpy()}")

        # Compute dataset hash for reproducibility (FR-TRACK-001)
        self.dataset_hash = self._compute_dataset_hash()

    def _compute_dataset_hash(self) -> str:
        """Compute a deterministic hash from the training dataset file paths."""
        h = hashlib.sha256()
        dataset = getattr(self.train_loader, 'dataset', None)
        if dataset is None:
            return "unknown"
        # For Subset (from random_split), reach into the underlying dataset
        inner = getattr(dataset, 'dataset', dataset)
        samples = getattr(inner, 'samples', [])
        for s in sorted(samples, key=lambda x: str(x.get("path", ""))):
            h.update(str(s.get("path", "")).encode())
        digest = h.hexdigest()[:16]
        logger.info(f"Dataset hash: {digest} ({len(samples)} samples)")
        return digest
    
    def _mixup_data(
        self,
        x: torch.Tensor,
        y: torch.Tensor,
        alpha: float = 0.2,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
        """Apply mixup augmentation."""
        if alpha > 0:
            lam = np.random.beta(alpha, alpha)
        else:
            lam = 1.0
        
        batch_size = x.size(0)
        index = torch.randperm(batch_size).to(self.device)
        
        mixed_x = lam * x + (1 - lam) * x[index]
        y_a, y_b = y, y[index]
        
        return mixed_x, y_a, y_b, lam
    
    def train_epoch(self, epoch: int) -> Dict[str, float]:
        """Train for one epoch."""
        self.model.train()
        
        total_loss = 0.0
        all_preds = []
        all_labels = []
        
        for batch_idx, (images, labels) in enumerate(self.train_loader):
            images = images.to(self.device)
            labels = labels.to(self.device)
            
            # Apply mixup with probability
            use_mixup = (
                self.config.data.mixup_alpha > 0 and
                np.random.random() < self.config.data.mixup_probability
            )
            
            if use_mixup:
                images, labels_a, labels_b, lam = self._mixup_data(
                    images, labels, self.config.data.mixup_alpha
                )
            
            # Forward pass with mixed precision
            self.optimizer.zero_grad()
            
            if self.scaler is not None:
                with autocast():
                    outputs = self.model(images)
                    logits = outputs['logits']
                    
                    if use_mixup:
                        loss = lam * self.criterion(logits, labels_a) + \
                               (1 - lam) * self.criterion(logits, labels_b)
                    else:
                        loss = self.criterion(logits, labels)
                
                self.scaler.scale(loss).backward()
                self.scaler.unscale_(self.optimizer)
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config.gradient_clip_norm
                )
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                outputs = self.model(images)
                logits = outputs['logits']
                
                if use_mixup:
                    loss = lam * self.criterion(logits, labels_a) + \
                           (1 - lam) * self.criterion(logits, labels_b)
                else:
                    loss = self.criterion(logits, labels)
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config.gradient_clip_norm
                )
                self.optimizer.step()
            
            # Track metrics
            total_loss += loss.item()
            preds = logits.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            
            if not use_mixup:
                all_labels.extend(labels.cpu().numpy())
            else:
                all_labels.extend(labels_a.cpu().numpy())
            
            self.global_step += 1
            
            if batch_idx % 10 == 0:
                logger.debug(f"Epoch {epoch} [{batch_idx}/{len(self.train_loader)}] "
                           f"Loss: {loss.item():.4f}")
        
        metrics = compute_metrics(all_labels, all_preds)
        metrics['loss'] = total_loss / len(self.train_loader)
        
        return metrics
    
    def validate(self) -> Dict[str, float]:
        """Run validation."""
        self.model.eval()
        
        total_loss = 0.0
        all_preds = []
        all_labels = []
        all_probs = []
        
        with torch.no_grad():
            for images, labels in self.val_loader:
                images = images.to(self.device)
                labels = labels.to(self.device)
                
                if self.scaler is not None:
                    with autocast():
                        outputs = self.model(images)
                        logits = outputs['logits']
                        loss = self.criterion(logits, labels)
                else:
                    outputs = self.model(images)
                    logits = outputs['logits']
                    loss = self.criterion(logits, labels)
                
                total_loss += loss.item()
                
                probs = torch.softmax(logits, dim=1)
                preds = logits.argmax(dim=1)
                
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                all_probs.extend(probs.cpu().numpy())
        
        metrics = compute_metrics(all_labels, all_preds)
        calibration = compute_calibration_metrics(all_labels, np.array(all_probs))
        metrics.update(calibration)
        metrics['loss'] = total_loss / len(self.val_loader)
        
        return metrics
    
    def _check_phase_transition(self, epoch: int):
        """Check if we should transition from Phase 1 to Phase 2."""
        if (self.training_phase == 1 and 
            epoch > self.config.model.freeze_backbone_epochs):
            
            logger.info("=" * 50)
            logger.info("Transitioning to Phase 2: Unfreezing backbone layers")
            logger.info("=" * 50)
            
            self.model.unfreeze_layers(self.config.model.unfreeze_layers)
            
            self.optimizer = AdamW(
                self.model.get_param_groups(self.config.learning_rate),
                weight_decay=self.config.weight_decay,
            )
            
            self.scheduler = self._create_scheduler()
            self.training_phase = 2
            
            logger.info(f"Trainable params: {self.model.get_trainable_params():,}")
    
    def _check_early_stopping(self, current_metric: float) -> bool:
        """Check early stopping condition."""
        if not self.config.early_stopping_enabled:
            return False
        
        if current_metric > self.best_metric + self.config.min_delta:
            self.best_metric = current_metric
            self.patience_counter = 0
            return False
        else:
            self.patience_counter += 1
            return self.patience_counter >= self.config.patience
    
    def _check_quality_gates(self, metrics: Dict[str, float]) -> Dict[str, bool]:
        """Check quality gates from requirements."""
        results = {}
        
        f1_macro = metrics.get('f1_macro', 0.0)
        f1_per_class = [metrics.get(f'f1_class_{i}', 0.0) 
                       for i in range(self.config.model.num_classes)]
        balanced_acc = metrics.get('balanced_accuracy', 0.0)
        ece = metrics.get('ece', 1.0)
        brier = metrics.get('brier', 1.0)
        
        gate_a_passed = (
            f1_macro >= self.config.gate_a_min_f1_macro and
            all(f1 >= self.config.gate_a_min_per_class_f1 for f1 in f1_per_class) and
            balanced_acc >= self.config.gate_a_min_balanced_accuracy and
            ece <= self.config.gate_a_max_ece and
            brier <= self.config.gate_a_max_brier
        )
        
        results['gate_a'] = gate_a_passed
        results['gate_a_details'] = {
            'f1_macro': f1_macro,
            'f1_per_class': f1_per_class,
            'balanced_accuracy': balanced_acc,
            'ece': ece,
            'brier': brier,
            'accuracy': metrics.get('accuracy', 0.0),
            'precision_macro': metrics.get('precision_macro', 0.0),
            'recall_macro': metrics.get('recall_macro', 0.0),
            'confusion_matrix': metrics.get('confusion_matrix', []),
            'mce': metrics.get('mce', 0.0),
        }
        
        logger.info(f"Gate A: {'PASSED' if gate_a_passed else 'FAILED'}")
        logger.info(f"  F1 macro: {f1_macro:.4f} (req: {self.config.gate_a_min_f1_macro})")
        logger.info(f"  Balanced acc: {balanced_acc:.4f} (req: {self.config.gate_a_min_balanced_accuracy})")
        logger.info(f"  ECE: {ece:.4f} (req: ≤{self.config.gate_a_max_ece})")
        
        return results
    
    def _save_checkpoint(self, epoch: int, metrics: Dict[str, float], is_best: bool = False):
        """Save model checkpoint."""
        checkpoint_dir = Path(self.config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict() if self.scheduler else None,
            'scaler_state_dict': self.scaler.state_dict() if self.scaler else None,
            'metrics': metrics,
            'config': self.config.to_dict(),
            'training_phase': self.training_phase,
            'best_metric': self.best_metric,
            'patience_counter': self.patience_counter,
            'global_step': self.global_step,
            'model_type': 'efficientnet_b0_hsemotion',
        }
        
        latest_path = checkpoint_dir / 'latest.pth'
        torch.save(checkpoint, latest_path)
        
        if is_best:
            best_path = checkpoint_dir / 'best_model.pth'
            torch.save(checkpoint, best_path)
            logger.info(f"Saved best model: {best_path}")
        
        if epoch % self.config.save_interval == 0:
            epoch_path = checkpoint_dir / f'checkpoint_epoch_{epoch}.pth'
            torch.save(checkpoint, epoch_path)
    
    def load_checkpoint(self, checkpoint_path: str) -> int:
        """Load training state from checkpoint."""
        logger.info(f"Loading checkpoint: {checkpoint_path}")
        
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.training_phase = checkpoint.get('training_phase', 1)
        
        if self.training_phase == 2:
            self.model.unfreeze_layers(self.config.model.unfreeze_layers)
            self.optimizer = AdamW(
                self.model.get_param_groups(self.config.learning_rate),
                weight_decay=self.config.weight_decay,
            )
        
        if 'optimizer_state_dict' in checkpoint:
            try:
                self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            except ValueError as e:
                logger.warning(f"Could not load optimizer state: {e}")
        
        if 'scheduler_state_dict' in checkpoint and checkpoint['scheduler_state_dict']:
            try:
                self.scheduler = self._create_scheduler()
                self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
            except Exception as e:
                logger.warning(f"Could not load scheduler state: {e}")
        
        if 'scaler_state_dict' in checkpoint and checkpoint['scaler_state_dict'] and self.scaler:
            try:
                self.scaler.load_state_dict(checkpoint['scaler_state_dict'])
            except Exception as e:
                logger.warning(f"Could not load scaler state: {e}")
        
        self.best_metric = checkpoint.get('best_metric', 0.0)
        self.patience_counter = checkpoint.get('patience_counter', 0)
        self.global_step = checkpoint.get('global_step', 0)
        
        resume_epoch = checkpoint.get('epoch', 0)
        self.current_epoch = resume_epoch
        self.resumed_from = checkpoint_path
        
        logger.info(f"Resumed from epoch {resume_epoch}, phase {self.training_phase}")
        logger.info(f"Best metric so far: {self.best_metric:.4f}")
        
        return resume_epoch
    
    def train(self, run_id: Optional[str] = None, resume_epoch: int = 0) -> Dict[str, Any]:
        """Run full training loop."""
        if run_id is None:
            run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        logger.info("=" * 60)
        if resume_epoch > 0:
            logger.info(f"Resuming training run: {run_id} from epoch {resume_epoch + 1}")
        else:
            logger.info(f"Starting training run: {run_id}")
        logger.info("=" * 60)
        
        if self.train_loader is None:
            self._create_dataloaders(run_id=run_id)
        
        # MLflow tracking
        try:
            import mlflow
            mlflow.set_tracking_uri(self.config.mlflow_tracking_uri)
            mlflow.set_experiment(self.config.mlflow_experiment_name)
            
            if self.resumed_from and self.mlflow_run_id:
                mlflow.start_run(run_id=self.mlflow_run_id)
            else:
                mlflow.start_run(run_name=run_id)
                mlflow.log_params(self.config.to_dict())
                mlflow.log_param('model_type', 'efficientnet_b0_hsemotion')
                mlflow.log_param('dataset_hash', getattr(self, 'dataset_hash', 'unknown'))
                self.mlflow_run_id = mlflow.active_run().info.run_id
        except ImportError:
            logger.warning("MLflow not available, skipping tracking")
            mlflow = None
        
        results = {
            'run_id': run_id,
            'model_type': 'efficientnet_b0_hsemotion',
            'status': 'running',
            'epochs_completed': resume_epoch,
            'best_metric': self.best_metric,
            'gate_results': {},
            'resumed_from': self.resumed_from,
        }
        
        start_epoch = resume_epoch + 1
        
        try:
            for epoch in range(start_epoch, self.config.num_epochs + 1):
                self.current_epoch = epoch
                
                self._check_phase_transition(epoch)
                
                train_metrics = self.train_epoch(epoch)
                val_metrics = self.validate()
                
                if isinstance(self.scheduler, ReduceLROnPlateau):
                    self.scheduler.step(val_metrics['f1_macro'])
                else:
                    self.scheduler.step()
                
                current_lr = self.optimizer.param_groups[0]['lr']
                
                logger.info(f"Epoch {epoch}/{self.config.num_epochs} (LR: {current_lr:.2e})")
                logger.info(f"  Train - Loss: {train_metrics['loss']:.4f}, "
                           f"F1: {train_metrics['f1_macro']:.4f}")
                logger.info(f"  Val   - Loss: {val_metrics['loss']:.4f}, "
                           f"F1: {val_metrics['f1_macro']:.4f}, "
                           f"ECE: {val_metrics.get('ece', 0):.4f}")
                
                if mlflow is not None:
                    mlflow.log_metrics({f'train_{k}': v for k, v in train_metrics.items() if isinstance(v, (int, float))}, step=epoch)
                    mlflow.log_metrics({f'val_{k}': v for k, v in val_metrics.items() if isinstance(v, (int, float))}, step=epoch)
                    mlflow.log_metric('learning_rate', current_lr, step=epoch)
                    mlflow.log_metric('training_phase', self.training_phase, step=epoch)
                
                gate_results = self._check_quality_gates(val_metrics)
                
                is_best = val_metrics['f1_macro'] > results['best_metric']
                if is_best:
                    results['best_metric'] = val_metrics['f1_macro']
                
                self._save_checkpoint(epoch, val_metrics, is_best)
                
                if self._check_early_stopping(val_metrics['f1_macro']):
                    logger.info(f"Early stopping at epoch {epoch}")
                    break
                
                results['epochs_completed'] = epoch
                results['gate_results'] = gate_results
            
            results['status'] = 'completed'
            
            if results['gate_results'].get('gate_a', False):
                results['status'] = 'completed_gate_passed'
                logger.info("Training completed - Gate A PASSED")
            else:
                results['status'] = 'completed_gate_failed'
                logger.warning("Training completed - Gate A FAILED")
        
        except Exception as e:
            logger.error(f"Training error: {e}", exc_info=True)
            results['status'] = 'error'
            results['error'] = str(e)
        
        finally:
            if mlflow is not None:
                mlflow.log_metrics({'final_f1': results['best_metric']})
                mlflow.end_run()
        
        logger.info("=" * 60)
        logger.info(f"Training finished: {results['status']}")
        logger.info("=" * 60)
        
        return results
