"""
Quick training run to verify the pipeline works.
Uses minimal epochs for fast verification.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from pathlib import Path
from sklearn.metrics import f1_score, balanced_accuracy_score

from trainer.fer_finetune.model_efficientnet import HSEmotionEfficientNet

def quick_train(data_dir='data_quick', epochs=3, batch_size=8):
    """Run a quick training session."""

    print("=" * 60)
    print("QUICK TRAINING: EfficientNet-B0 Fine-Tuning")
    print("=" * 60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nDevice: {device}")

    # Data transforms
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    # Load datasets
    train_dataset = datasets.ImageFolder(f'{data_dir}/train', transform=train_transform)
    val_dataset = datasets.ImageFolder(f'{data_dir}/val', transform=val_transform)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)

    print(f"\nDataset: {data_dir}")
    print(f"  Train: {len(train_dataset)} images")
    print(f"  Val: {len(val_dataset)} images")
    print(f"  Classes: {train_dataset.classes}")

    # Load model
    print("\nLoading model...")
    model = HSEmotionEfficientNet(
        num_classes=3,
        pretrained_weights='enet_b0_8_best_vgaf',
        dropout_rate=0.3,
    )
    model = model.to(device)

    # Freeze backbone for quick training
    model.freeze_backbone()
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Trainable parameters: {trainable:,}")

    # Setup training
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=0.001)

    # Training loop
    print(f"\nTraining for {epochs} epochs...")
    print("-" * 60)

    best_f1 = 0
    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs['logits'], labels)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        train_loss /= len(train_loader)

        # Validate
        model.eval()
        all_preds, all_labels = [], []
        val_loss = 0

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs['logits'], labels)
                val_loss += loss.item()

                preds = outputs['logits'].argmax(dim=1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        val_loss /= len(val_loader)
        f1 = f1_score(all_labels, all_preds, average='macro')
        bal_acc = balanced_accuracy_score(all_labels, all_preds)

        if f1 > best_f1:
            best_f1 = f1
            torch.save(model.state_dict(), 'quick_model.pth')

        print(f"Epoch {epoch+1}/{epochs}: "
              f"Train Loss: {train_loss:.4f} | "
              f"Val Loss: {val_loss:.4f} | "
              f"F1: {f1:.4f} | "
              f"Bal Acc: {bal_acc:.4f}")

    # Final evaluation
    print("\n" + "=" * 60)
    print("QUICK TRAINING RESULTS")
    print("=" * 60)
    print(f"\nBest Macro F1: {best_f1:.4f}")
    print(f"Model saved to: quick_model.pth")

    # Gate A check (simplified)
    print("\n--- Gate A Quick Check ---")
    gate_a_f1 = 0.84
    gate_a_bal = 0.85

    print(f"Macro F1:          {best_f1:.4f} {'&' if best_f1 >= gate_a_f1 else 'XX'} (threshold: {gate_a_f1})")
    print(f"Balanced Accuracy: {bal_acc:.4f} {'&' if bal_acc >= gate_a_bal else 'XX'} (threshold: {gate_a_bal})")

    if best_f1 >= gate_a_f1 and bal_acc >= gate_a_bal:
        print("\& Quick model PASSES simplified Gate A!")
    else:
        print("\n!  Quick model does not pass Gate A (expected with synthetic data)")
        print("    With real emotion data, performance will be much better.")

    print("\n" + "=" * 60)
    print("SUCCESS! Training pipeline verified.")
    print("=" * 60)

if __name__ == '__main__':
    quick_train()