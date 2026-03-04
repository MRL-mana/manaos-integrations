"""
MNISTでのNDM検証実験
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
from tqdm import tqdm
import json
from datetime import datetime
from pathlib import Path

from ndm_layers import create_simple_ndm_model


def train_epoch(model, train_loader, optimizer, criterion, device, use_geometric_loss=True):
    """1エポックの訓練"""
    model.train()
    total_loss = 0.0
    total_task_loss = 0.0
    total_geom_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (data, target) in enumerate(tqdm(train_loader, desc="Training")):
        data = data.view(data.size(0), -1).to(device)  # [batch_size, 784]
        target = target.to(device)

        optimizer.zero_grad()

        # フォワード
        logits = model(data)
        task_loss = criterion(logits, target)

        # 幾何学的正則化項
        if use_geometric_loss:
            geom_loss = model.compute_geometric_loss()
            total_loss_batch = task_loss + geom_loss
            total_geom_loss += geom_loss.item()
        else:
            total_loss_batch = task_loss

        # バックプロパゲーション
        total_loss_batch.backward()
        optimizer.step()

        # メトリクス
        total_loss += total_loss_batch.item()
        total_task_loss += task_loss.item()

        pred = logits.argmax(dim=1)
        correct += pred.eq(target).sum().item()
        total += target.size(0)

    accuracy = 100.0 * correct / total
    avg_loss = total_loss / len(train_loader)
    avg_task_loss = total_task_loss / len(train_loader)
    avg_geom_loss = total_geom_loss / len(train_loader) if use_geometric_loss else 0.0

    return avg_loss, avg_task_loss, avg_geom_loss, accuracy


def validate(model, val_loader, criterion, device):
    """検証"""
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for data, target in tqdm(val_loader, desc="Validation"):
            data = data.view(data.size(0), -1).to(device)
            target = target.to(device)

            logits = model(data)
            loss = criterion(logits, target)

            total_loss += loss.item()
            pred = logits.argmax(dim=1)
            correct += pred.eq(target).sum().item()
            total += target.size(0)

    accuracy = 100.0 * correct / total
    avg_loss = total_loss / len(val_loader)

    return avg_loss, accuracy


def main():
    # 設定
    config = {
        'batch_size': 128,
        'epochs': 5,  # 検証用なので少なめ
        'learning_rate': 0.001,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'use_geometric_loss': True,
        'lambda_geom': 0.01,
        'model_config': {
            'input_dim': 784,
            'num_classes': 10,
            'hidden_dims': [256, 128],
            'use_diagonal_metric': True
        }
    }

    print(f"使用デバイス: {config['device']}")
    print(f"設定: {json.dumps(config, indent=2, ensure_ascii=False)}")

    # データローダー
    train_loader = DataLoader(
        datasets.MNIST(
            './data/mnist',
            train=True,
            download=True,
            transform=transforms.ToTensor()
        ),
        batch_size=config['batch_size'],
        shuffle=True
    )

    val_loader = DataLoader(
        datasets.MNIST(
            './data/mnist',
            train=False,
            download=True,
            transform=transforms.ToTensor()
        ),
        batch_size=config['batch_size'],
        shuffle=False
    )

    # モデル
    model = create_simple_ndm_model(**config['model_config']).to(config['device'])

    # オプティマイザー
    optimizer = optim.Adam(model.parameters(), lr=config['learning_rate'])
    criterion = nn.CrossEntropyLoss()

    # 訓練
    print("\n=== 訓練開始 ===\n")
    history = {
        'train_loss': [],
        'train_task_loss': [],
        'train_geom_loss': [],
        'train_acc': [],
        'val_loss': [],
        'val_acc': []
    }

    best_val_acc = 0.0

    for epoch in range(config['epochs']):
        print(f"\nエポック {epoch+1}/{config['epochs']}")

        # 訓練
        avg_loss, task_loss, geom_loss, train_acc = train_epoch(
            model, train_loader, optimizer, criterion,
            config['device'], config['use_geometric_loss']
        )

        # 検証
        val_loss, val_acc = validate(model, val_loader, criterion, config['device'])

        # 記録
        history['train_loss'].append(avg_loss)
        history['train_task_loss'].append(task_loss)
        history['train_geom_loss'].append(geom_loss)
        history['train_acc'].append(train_acc)
        history['val_loss'].append(val_loss)
        history['val_acc'].append(val_acc)

        print(f"Train - Loss: {avg_loss:.4f} (Task: {task_loss:.4f}, Geom: {geom_loss:.4f}), Acc: {train_acc:.2f}%")
        print(f"Val   - Loss: {val_loss:.4f}, Acc: {val_acc:.2f}%")

        # ベストモデル保存
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), '../logs/best_model.pth')
            print(f"★ ベストモデル保存: {best_val_acc:.2f}%")

    # 結果保存
    results = {
        'config': config,
        'history': history,
        'best_val_acc': best_val_acc,
        'timestamp': datetime.now().isoformat()
    }

    results_path = Path('../logs/results.json')
    results_path.parent.mkdir(exist_ok=True, parents=True)

    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n=== 訓練完了 ===")
    print(f"ベスト検証精度: {best_val_acc:.2f}%")
    print(f"結果保存先: {results_path}")


if __name__ == '__main__':
    main()





