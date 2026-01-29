# Week 8: Gate A Validation & Phase 1 Completion

**Phase 1 Tutorial Series**  
**Duration**: ~5 hours  
**Prerequisites**: Weeks 1-7 complete

---

## Overview

This final week integrates everything:
- Gate A validation in training pipeline
- Post-training analysis automation
- Phase 1 completion checklist
- Preparing for Phase 2

### Weekly Goals
- [ ] Integrate Gate A validation with training
- [ ] Automate post-training statistical analysis
- [ ] Complete Phase 1 checklist
- [ ] Understand Phase 2 readiness criteria

---

## Day 1: Gate A Validator Script

### Gate A Requirements Recap

| Metric | Threshold | Purpose |
|--------|-----------|---------|
| Macro F1 | ≥ 0.84 | Overall classification quality |
| Balanced Accuracy | ≥ 0.85 | No class ignored |
| Per-class F1 | ≥ 0.75 (floor: 0.70) | Each emotion acceptable |
| ECE | ≤ 0.08 | Well-calibrated confidence |
| Brier | ≤ 0.16 | Good probability estimates |

### Gate A Validator Implementation

Create `trainer/gate_a_validator.py`:

```python
#!/usr/bin/env python3
"""
Gate A Validator

Validates trained models against Gate A requirements before
deployment consideration.
"""

import argparse
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import numpy as np
import torch
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gate A Thresholds
GATE_A_THRESHOLDS = {
    "macro_f1": 0.84,
    "balanced_accuracy": 0.85,
    "per_class_f1_min": 0.75,
    "per_class_f1_floor": 0.70,
    "ece": 0.08,
    "brier": 0.16,
}


@dataclass
class GateAResult:
    """Result of Gate A validation."""
    model_name: str
    checkpoint_path: str
    timestamp: str
    
    # Metrics
    macro_f1: float
    balanced_accuracy: float
    per_class_f1: Dict[str, float]
    ece: float
    brier: float
    
    # Gate results
    gates: Dict[str, bool]
    overall_pass: bool
    
    # Details
    failing_classes: List[str]
    recommendations: List[str]
    
    def to_dict(self) -> dict:
        return asdict(self)


def load_model_and_evaluate(
    checkpoint_path: Path,
    test_loader,
    device: str = "cuda"
) -> tuple:
    """
    Load model and run evaluation on test set.
    
    Returns:
        (y_true, y_pred, y_prob) arrays
    """
    from fer_finetune.model import create_model
    
    # Load checkpoint
    checkpoint = torch.load(checkpoint_path, map_location=device)
    
    # Create model
    model = create_model(num_classes=8)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    
    all_true = []
    all_pred = []
    all_prob = []
    
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)
            preds = torch.argmax(probs, dim=1)
            
            all_true.extend(labels.cpu().numpy())
            all_pred.extend(preds.cpu().numpy())
            all_prob.extend(probs.cpu().numpy())
    
    return (
        np.array(all_true),
        np.array(all_pred),
        np.array(all_prob)
    )


def compute_metrics(y_true, y_pred, y_prob, class_names) -> Dict:
    """Compute all Gate A metrics."""
    from sklearn.metrics import f1_score, balanced_accuracy_score
    
    # Macro F1
    macro_f1 = f1_score(y_true, y_pred, average='macro')
    
    # Balanced Accuracy
    balanced_acc = balanced_accuracy_score(y_true, y_pred)
    
    # Per-class F1
    per_class_f1 = {}
    f1_scores = f1_score(y_true, y_pred, average=None)
    for i, name in enumerate(class_names):
        per_class_f1[name] = float(f1_scores[i])
    
    # ECE
    ece = compute_ece(y_true, y_prob)
    
    # Brier
    brier = compute_brier(y_true, y_prob)
    
    return {
        "macro_f1": macro_f1,
        "balanced_accuracy": balanced_acc,
        "per_class_f1": per_class_f1,
        "ece": ece,
        "brier": brier,
    }


def compute_ece(y_true, y_prob, n_bins=10) -> float:
    """Compute Expected Calibration Error."""
    y_pred = np.argmax(y_prob, axis=1)
    confidences = np.max(y_prob, axis=1)
    accuracies = (y_pred == y_true).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    
    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (confidences <= bin_boundaries[i + 1])
        prop_in_bin = in_bin.mean()
        
        if prop_in_bin > 0:
            avg_confidence = confidences[in_bin].mean()
            avg_accuracy = accuracies[in_bin].mean()
            ece += np.abs(avg_accuracy - avg_confidence) * prop_in_bin
    
    return float(ece)


def compute_brier(y_true, y_prob) -> float:
    """Compute Brier Score."""
    n_samples, n_classes = y_prob.shape
    y_true_onehot = np.zeros((n_samples, n_classes))
    y_true_onehot[np.arange(n_samples), y_true] = 1
    return float(np.mean(np.sum((y_prob - y_true_onehot) ** 2, axis=1)))


def validate_gate_a(
    checkpoint_path: Path,
    test_data_dir: Path,
    model_name: str = "model",
    output_dir: Path = Path("outputs/gate_a"),
) -> GateAResult:
    """
    Run complete Gate A validation.
    
    Args:
        checkpoint_path: Path to model checkpoint
        test_data_dir: Path to test dataset
        model_name: Name for reporting
        output_dir: Directory for output files
    
    Returns:
        GateAResult with validation results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("GATE A VALIDATION")
    logger.info("=" * 60)
    logger.info(f"Model: {model_name}")
    logger.info(f"Checkpoint: {checkpoint_path}")
    
    # Class names
    class_names = [
        'anger', 'contempt', 'disgust', 'fear',
        'happiness', 'neutral', 'sadness', 'surprise'
    ]
    
    # Load test data
    from fer_finetune.dataset import create_dataloader
    test_loader = create_dataloader(test_data_dir, batch_size=32, shuffle=False)
    
    # Evaluate model
    logger.info("\nEvaluating model on test set...")
    y_true, y_pred, y_prob = load_model_and_evaluate(checkpoint_path, test_loader)
    
    # Compute metrics
    logger.info("Computing metrics...")
    metrics = compute_metrics(y_true, y_pred, y_prob, class_names)
    
    # Check gates
    gates = {}
    recommendations = []
    failing_classes = []
    
    # Macro F1
    gates["macro_f1"] = metrics["macro_f1"] >= GATE_A_THRESHOLDS["macro_f1"]
    if not gates["macro_f1"]:
        recommendations.append(
            f"Macro F1 ({metrics['macro_f1']:.4f}) below threshold ({GATE_A_THRESHOLDS['macro_f1']})"
        )
    
    # Balanced Accuracy
    gates["balanced_accuracy"] = metrics["balanced_accuracy"] >= GATE_A_THRESHOLDS["balanced_accuracy"]
    if not gates["balanced_accuracy"]:
        recommendations.append(
            f"Balanced Accuracy ({metrics['balanced_accuracy']:.4f}) below threshold"
        )
    
    # Per-class F1
    gates["per_class_f1"] = True
    for class_name, f1 in metrics["per_class_f1"].items():
        if f1 < GATE_A_THRESHOLDS["per_class_f1_floor"]:
            gates["per_class_f1"] = False
            failing_classes.append(class_name)
            recommendations.append(f"Class '{class_name}' F1 ({f1:.4f}) below floor")
        elif f1 < GATE_A_THRESHOLDS["per_class_f1_min"]:
            recommendations.append(f"Class '{class_name}' F1 ({f1:.4f}) below target (but above floor)")
    
    # ECE
    gates["ece"] = metrics["ece"] <= GATE_A_THRESHOLDS["ece"]
    if not gates["ece"]:
        recommendations.append(
            f"ECE ({metrics['ece']:.4f}) above threshold. Consider temperature scaling."
        )
    
    # Brier
    gates["brier"] = metrics["brier"] <= GATE_A_THRESHOLDS["brier"]
    if not gates["brier"]:
        recommendations.append(
            f"Brier score ({metrics['brier']:.4f}) above threshold."
        )
    
    # Overall
    overall_pass = all(gates.values())
    
    if overall_pass:
        recommendations.append("✅ Model passes all Gate A requirements!")
    else:
        recommendations.append("❌ Model does not pass Gate A. Address issues before deployment.")
    
    # Build result
    result = GateAResult(
        model_name=model_name,
        checkpoint_path=str(checkpoint_path),
        timestamp=datetime.now().isoformat(),
        macro_f1=metrics["macro_f1"],
        balanced_accuracy=metrics["balanced_accuracy"],
        per_class_f1=metrics["per_class_f1"],
        ece=metrics["ece"],
        brier=metrics["brier"],
        gates=gates,
        overall_pass=overall_pass,
        failing_classes=failing_classes,
        recommendations=recommendations,
    )
    
    # Print results
    print_gate_a_results(result)
    
    # Save results
    result_path = output_dir / f"gate_a_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_path, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)
    logger.info(f"\nResults saved to: {result_path}")
    
    return result


def print_gate_a_results(result: GateAResult):
    """Print Gate A validation results."""
    print("\n" + "=" * 60)
    print("GATE A VALIDATION RESULTS")
    print("=" * 60)
    
    print(f"\nModel: {result.model_name}")
    print(f"Timestamp: {result.timestamp}")
    
    print("\n--- Metrics ---")
    print(f"Macro F1:           {result.macro_f1:.4f} (threshold: {GATE_A_THRESHOLDS['macro_f1']})")
    print(f"Balanced Accuracy:  {result.balanced_accuracy:.4f} (threshold: {GATE_A_THRESHOLDS['balanced_accuracy']})")
    print(f"ECE:                {result.ece:.4f} (threshold: {GATE_A_THRESHOLDS['ece']})")
    print(f"Brier:              {result.brier:.4f} (threshold: {GATE_A_THRESHOLDS['brier']})")
    
    print("\n--- Per-class F1 ---")
    for class_name, f1 in result.per_class_f1.items():
        status = "✅" if f1 >= GATE_A_THRESHOLDS["per_class_f1_floor"] else "❌"
        print(f"  {status} {class_name}: {f1:.4f}")
    
    print("\n--- Gate Results ---")
    for gate, passed in result.gates.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {gate}: {status}")
    
    print(f"\n{'='*60}")
    print(f"OVERALL: {'✅ PASS' if result.overall_pass else '❌ FAIL'}")
    print(f"{'='*60}")
    
    if result.recommendations:
        print("\nRecommendations:")
        for rec in result.recommendations:
            print(f"  • {rec}")


def main():
    parser = argparse.ArgumentParser(description="Gate A Validation")
    parser.add_argument("--checkpoint", type=Path, required=True, help="Model checkpoint")
    parser.add_argument("--test-dir", type=Path, required=True, help="Test data directory")
    parser.add_argument("--model-name", type=str, default="model", help="Model name")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/gate_a"))
    
    args = parser.parse_args()
    
    result = validate_gate_a(
        args.checkpoint,
        args.test_dir,
        args.model_name,
        args.output_dir,
    )
    
    return 0 if result.overall_pass else 1


if __name__ == "__main__":
    exit(main())
```

### Exercises

1. **Run Gate A validation**:
   ```bash
   python trainer/gate_a_validator.py \
       --checkpoint outputs/best_model.pt \
       --test-dir data/test \
       --model-name resnet50_v1
   ```

2. **Interpret results**:
   - Which gates passed/failed?
   - Which classes need improvement?
   - What are the recommendations?

### Checkpoint: Day 1
- [ ] Gate A validator script created
- [ ] Understand all thresholds
- [ ] Can run validation

---

## Day 2: Post-Training Analysis Automation

### Integrating Stats with Training

Create `trainer/post_training_analysis.py`:

```python
#!/usr/bin/env python3
"""
Post-Training Analysis

Automatically runs statistical analysis after training completes.
"""

import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
import sys

# Add stats scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "stats" / "scripts"))

from gate_a_validator import validate_gate_a
from run_full_analysis import run_full_analysis
from mlflow_stats_logger import StatsMLflowLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_post_training_analysis(
    checkpoint_path: Path,
    test_data_dir: Path,
    predictions_path: Path = None,
    paired_predictions_path: Path = None,
    fold_metrics_path: Path = None,
    model_name: str = "model",
    output_dir: Path = Path("outputs"),
    log_mlflow: bool = True,
) -> dict:
    """
    Run complete post-training analysis.
    
    Args:
        checkpoint_path: Path to trained model checkpoint
        test_data_dir: Path to test dataset
        predictions_path: Path to save/load predictions
        paired_predictions_path: Path to paired predictions (for comparison)
        fold_metrics_path: Path to fold metrics (for per-class tests)
        model_name: Name for reporting
        output_dir: Directory for outputs
        log_mlflow: Whether to log to MLflow
    
    Returns:
        Dictionary with all analysis results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("POST-TRAINING ANALYSIS")
    logger.info("=" * 60)
    logger.info(f"Model: {model_name}")
    logger.info(f"Checkpoint: {checkpoint_path}")
    
    results = {
        "model_name": model_name,
        "checkpoint_path": str(checkpoint_path),
        "timestamp": datetime.now().isoformat(),
    }
    
    # Step 1: Gate A Validation
    logger.info("\n--- Step 1: Gate A Validation ---")
    gate_a_result = validate_gate_a(
        checkpoint_path,
        test_data_dir,
        model_name,
        output_dir / "gate_a"
    )
    results["gate_a"] = gate_a_result.to_dict()
    results["gate_a_passed"] = gate_a_result.overall_pass
    
    # Step 2: Full Statistical Analysis (if predictions available)
    if predictions_path and predictions_path.exists():
        logger.info("\n--- Step 2: Full Statistical Analysis ---")
        stats_report = run_full_analysis(
            predictions_path,
            paired_predictions_path,
            fold_metrics_path,
            model_name,
            output_dir / "stats"
        )
        results["stats_analysis"] = stats_report.__dict__
        results["phase1_ready"] = stats_report.phase1_ready
    else:
        logger.info("\n--- Step 2: Skipped (no predictions file) ---")
        results["phase1_ready"] = gate_a_result.overall_pass
    
    # Step 3: Log to MLflow
    if log_mlflow:
        logger.info("\n--- Step 3: Logging to MLflow ---")
        try:
            mlflow_logger = StatsMLflowLogger()
            mlflow_logger.log_full_analysis(results, run_name=f"post_training_{model_name}")
            results["mlflow_logged"] = True
        except Exception as e:
            logger.warning(f"MLflow logging failed: {e}")
            results["mlflow_logged"] = False
    
    # Save combined results
    results_path = output_dir / f"post_training_{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved to: {results_path}")
    
    # Print summary
    print_summary(results)
    
    return results


def print_summary(results: dict):
    """Print analysis summary."""
    print("\n" + "=" * 60)
    print("POST-TRAINING ANALYSIS SUMMARY")
    print("=" * 60)
    
    print(f"\nModel: {results['model_name']}")
    print(f"Gate A: {'✅ PASS' if results['gate_a_passed'] else '❌ FAIL'}")
    print(f"Phase 1 Ready: {'✅ YES' if results['phase1_ready'] else '❌ NO'}")
    
    if results.get('gate_a'):
        ga = results['gate_a']
        print(f"\nKey Metrics:")
        print(f"  Macro F1: {ga['macro_f1']:.4f}")
        print(f"  Balanced Accuracy: {ga['balanced_accuracy']:.4f}")
        print(f"  ECE: {ga['ece']:.4f}")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Post-Training Analysis")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--test-dir", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, default=None)
    parser.add_argument("--paired", type=Path, default=None)
    parser.add_argument("--folds", type=Path, default=None)
    parser.add_argument("--model-name", type=str, default="model")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--no-mlflow", action="store_true")
    
    args = parser.parse_args()
    
    results = run_post_training_analysis(
        args.checkpoint,
        args.test_dir,
        args.predictions,
        args.paired,
        args.folds,
        args.model_name,
        args.output_dir,
        log_mlflow=not args.no_mlflow,
    )
    
    return 0 if results["phase1_ready"] else 1


if __name__ == "__main__":
    exit(main())
```

### Exercises

1. **Run post-training analysis**:
   ```bash
   python trainer/post_training_analysis.py \
       --checkpoint outputs/best_model.pt \
       --test-dir data/test \
       --model-name resnet50_final
   ```

2. **Check MLflow for logged results**:
   - Open http://localhost:5000
   - Find the post_training run
   - Review metrics and artifacts

### Checkpoint: Day 2
- [ ] Post-training analysis script created
- [ ] Integration with Gate A working
- [ ] MLflow logging working

---

## Day 3-4: Phase 1 Completion Checklist

### Database Track Checklist

| Item | Status | Notes |
|------|--------|-------|
| PostgreSQL installed and running | [ ] | |
| Can connect with psql | [ ] | |
| All 12 tables understood | [ ] | |
| Video lifecycle mastered | [ ] | |
| Stored procedures working | [ ] | |
| SQLAlchemy ORM working | [ ] | |
| Repository pattern understood | [ ] | |
| Migrations can be run | [ ] | |
| Troubleshooting skills | [ ] | |

### Statistical Analysis Track Checklist

| Item | Status | Notes |
|------|--------|-------|
| Quality gate metrics understood | [ ] | |
| Script 01 runs successfully | [ ] | |
| Stuart-Maxwell test understood | [ ] | |
| Script 02 runs successfully | [ ] | |
| Per-class t-tests understood | [ ] | |
| Script 03 runs successfully | [ ] | |
| ECE and Brier understood | [ ] | |
| Bootstrap CIs implemented | [ ] | |
| Orchestrator script working | [ ] | |
| MLflow integration working | [ ] | |

### Integration Checklist

| Item | Status | Notes |
|------|--------|-------|
| Gate A validator working | [ ] | |
| Post-training analysis working | [ ] | |
| All Gate A thresholds known | [ ] | |
| Can interpret analysis results | [ ] | |
| Know what to do when gates fail | [ ] | |

### Final Verification

Run the complete workflow:

```bash
# 1. Verify database
psql -U reachy_app -d reachy_local -c "SELECT COUNT(*) FROM video;"

# 2. Run quality gates demo
python stats/scripts/01_quality_gate_metrics.py --demo

# 3. Run Stuart-Maxwell demo
python stats/scripts/02_stuart_maxwell_test.py --demo

# 4. Run per-class tests demo
python stats/scripts/03_perclass_paired_ttests.py --demo

# 5. Run full analysis
python stats/scripts/run_full_analysis.py --predictions stats/data/demo_preds.npz

# 6. Run Gate A validation (if model available)
python trainer/gate_a_validator.py --checkpoint outputs/best_model.pt --test-dir data/test
```

### Checkpoint: Days 3-4
- [ ] All checklist items verified
- [ ] Complete workflow runs successfully

---

## Day 5: Phase 1 Complete & Phase 2 Preview

### Phase 1 Completion Certificate

If you've completed all checklist items, you have mastered:

**Database Skills**:
- ✅ PostgreSQL fundamentals
- ✅ SQL queries (CRUD operations)
- ✅ Reachy schema (12 tables)
- ✅ Video lifecycle management
- ✅ Stored procedures
- ✅ SQLAlchemy ORM
- ✅ Repository pattern
- ✅ Database migrations
- ✅ Troubleshooting

**Statistical Analysis Skills**:
- ✅ Quality gate metrics (Macro F1, Balanced Accuracy, F1 Neutral)
- ✅ Calibration metrics (ECE, Brier)
- ✅ Stuart-Maxwell test for model comparison
- ✅ Per-class paired t-tests with BH correction
- ✅ Bootstrap confidence intervals
- ✅ Analysis orchestration
- ✅ MLflow integration
- ✅ Gate A validation

### Phase 2 Preview

Phase 2 focuses on **system integration and deployment**:

| Week | Focus |
|------|-------|
| 1-2 | n8n workflow automation |
| 3-4 | Web UI and Reconciler Agent |
| 5-6 | Jetson deployment and Gate B |
| 7-8 | E2E testing and release |

See `docs/tutorials/` for Phase 2 tutorials (already created).

### What's Different in Phase 2

| Phase 1 | Phase 2 |
|---------|---------|
| Database fundamentals | Database already working |
| Statistical analysis | Stats integrated with training |
| Local development | Multi-node deployment |
| Manual testing | Automated E2E testing |
| Learning focus | Implementation focus |

### Recommended Next Steps

1. **Practice**: Run the full analysis pipeline on real training outputs
2. **Experiment**: Try different models and compare Gate A results
3. **Document**: Keep notes on any issues encountered
4. **Prepare**: Review Phase 2 tutorials before starting

---

## Week 8 Deliverables

| Deliverable | Status |
|-------------|--------|
| Gate A validator working | [ ] |
| Post-training analysis working | [ ] |
| All checklists completed | [ ] |
| Final verification passed | [ ] |
| **Phase 1 Complete** | [ ] |

---

## Phase 1 Complete! 🎉

Congratulations, Russ! You've completed the 8-week Phase 1 learning plan.

### Summary of Achievements

| Weeks | Track | Key Skills |
|-------|-------|------------|
| 1-4 | Database | PostgreSQL, SQL, ORM, migrations |
| 5-7 | Statistics | Quality gates, hypothesis tests, calibration |
| 8 | Integration | Gate A validation, automation |

### Total Learning Time

- Database: ~28 hours
- Statistics: ~15 hours
- Integration: ~5 hours
- **Total**: ~48 hours over 8 weeks

### You Are Now Ready To

1. Work with the Reachy database confidently
2. Evaluate emotion classification models statistically
3. Validate models against Gate A requirements
4. Integrate analysis into training pipelines
5. Begin Phase 2 system integration work

### Resources for Continued Learning

- Database curriculum: `docs/database/curriculum/`
- Stats curriculum: `stats/curriculum/`
- Phase 2 tutorials: `docs/tutorials/`
- Project requirements: `memory-bank/requirements.md`

---

*Great work completing Phase 1, Russ!* 🚀
