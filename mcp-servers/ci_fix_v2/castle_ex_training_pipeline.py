#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CASTLE-EXフレームワーク: 学習パイプライン

階層的カリキュラム学習の自動化
段階的学習スケジュールの管理
"""

import sys
import json
import random
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
from datetime import datetime

if sys.platform == 'win32':
    try:
        import io
        if not hasattr(sys.stdout, 'buffer') or sys.stdout.buffer.closed:
            pass
        else:
            sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass


class CastleEXTrainingPipeline:
    """CASTLE-EX学習パイプライン"""
    
    # 段階的学習スケジュール（エポックごとの層別配分）
    TRAINING_SCHEDULE = {
        # Phase 1: 基盤層のみ（エポック1-5）
        (1, 5): {
            0: 1.0,  # Layer 0のみ
        },
        # Phase 2: 基盤層 + 操作・関係層（エポック6-10）
        (6, 10): {
            0: 0.40,  # Layer 0: 40%
            1: 0.60,  # Layer 1: 60%
        },
        # Phase 3: 基盤層 + 操作・関係層（エポック7-9）
        (7, 9): {
            0: 0.20,  # Layer 0: 20%
            1: 0.30,  # Layer 1: 30%
            2: 0.50,  # Layer 2: 50%
        },
        # Phase 4: 基盤層 + 感情・文脈基礎層（エポック10-12）
        (10, 12): {
            0: 0.10,  # Layer 0: 10%
            1: 0.20,  # Layer 1: 20%
            2: 0.30,  # Layer 2: 30%
            3: 0.40,  # Layer 3: 40%（感情基礎層）
        },
        # Phase 5: 感情・文脈基礎層（エポック11-15）
        (11, 15): {
            0: 0.10,  # Layer 0: 10%
            1: 0.15,  # Layer 1: 15%
            2: 0.15,  # Layer 2: 15%
            3: 0.30,  # Layer 3: 30%
            4: 0.30,  # Layer 4: 30%（文脈基礎層）
        },
        # Phase 6: 因果層統合（エポック16-20）
        (16, 20): {
            0: 0.05,  # Layer 0: 5%
            1: 0.10,  # Layer 1: 10%
            2: 0.15,  # Layer 2: 15%
            3: 0.15,  # Layer 3: 15%
            4: 0.15,  # Layer 4: 15%
            5: 0.40,  # Layer 5: 40%（因果層）
        },
        # Phase 7: 統合層（エポック21+）
        (21, 999): {
            0: 0.05,  # Layer 0: 5%
            1: 0.05,  # Layer 1: 5%
            2: 0.10,  # Layer 2: 10%
            3: 0.10,  # Layer 3: 10%
            4: 0.10,  # Layer 4: 10%
            5: 0.30,  # Layer 5: 30%
            6: 0.30,  # Layer 6: 30%（統合層）
        },
    }
    
    def __init__(self, dataset_path: str, output_dir: str = "./castle_ex_training"):
        """初期化"""
        self.dataset_path = Path(dataset_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.dataset = []
        self.by_layer = defaultdict(list)
        
    def load_dataset(self):
        """データセットを読み込み、層別に分類"""
        print("=" * 60)
        print("データセット読み込み")
        print("=" * 60)
        
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"データセットファイルが見つかりません: {self.dataset_path}")
        
        with open(self.dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    self.dataset.append(item)
                    
                    # 層別分類（layer情報がない場合は推定を試みる）
                    layer = item.get("layer")
                    if layer is None:
                        # 回答長から層を推定
                        assistant_content = item["messages"][-1]["content"]
                        length = len(assistant_content)
                        if length <= 5:
                            layer = 0
                        elif length <= 20:
                            layer = 1
                        elif length <= 40:
                            layer = 2 if "関係" in assistant_content or ":" in item["messages"][0]["content"] else 3
                        elif length <= 60:
                            layer = 4
                        elif length <= 100:
                            layer = 5
                        else:
                            layer = 6
                    
                    self.by_layer[layer].append(item)
                except json.JSONDecodeError as e:
                    print(f"警告: JSON解析エラー - {e}")
        
        print(f"総データ数: {len(self.dataset)}")
        print("\n層別データ数:")
        for layer in sorted(self.by_layer.keys()):
            print(f"  Layer {layer}: {len(self.by_layer[layer])}件")
    
    def get_phase_for_epoch(self, epoch: int) -> Dict[int, float]:
        """エポックに対応するフェーズの層別配分を取得"""
        for (start, end), distribution in self.TRAINING_SCHEDULE.items():
            if start <= epoch <= end:
                return distribution
        
        # デフォルトは最終フェーズ
        return self.TRAINING_SCHEDULE[(21, 999)]
    
    def sample_data_for_epoch(self, epoch: int, batch_size: int = 100) -> List[Dict]:
        """指定エポック用のデータをサンプリング"""
        phase_distribution = self.get_phase_for_epoch(epoch)
        
        # 各層から必要な数だけサンプリング
        sampled = []
        
        for layer, ratio in phase_distribution.items():
            if layer not in self.by_layer or len(self.by_layer[layer]) == 0:
                continue
            
            count = int(batch_size * ratio)
            layer_data = self.by_layer[layer]
            
            # 重複を許可してサンプリング
            if count > 0:
                samples = random.choices(layer_data, k=count)
                sampled.extend(samples)
        
        # シャッフル
        random.shuffle(sampled)
        
        return sampled
    
    def generate_epoch_dataset(self, epoch: int, batch_size: int = 100, 
                               output_prefix: str = "epoch") -> str:
        """エポック用のデータセットを生成"""
        sampled_data = self.sample_data_for_epoch(epoch, batch_size)
        
        phase_distribution = self.get_phase_for_epoch(epoch)
        
        # 出力ファイル名
        output_file = self.output_dir / f"{output_prefix}_{epoch:03d}.jsonl"
        
        # JSONL形式で保存
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in sampled_data:
                # layer情報は除外（必要に応じて残すことも可能）
                output_item = {"messages": item["messages"]}
                f.write(json.dumps(output_item, ensure_ascii=False) + '\n')
        
        # 統計情報
        layer_counts = defaultdict(int)
        for item in sampled_data:
            layer = item.get("layer")
            if layer is not None:
                layer_counts[layer] += 1
        
        print(f"エポック {epoch}:")
        print(f"  出力ファイル: {output_file}")
        print(f"  サンプル数: {len(sampled_data)}")
        print(f"  層別内訳:")
        for layer in sorted(layer_counts.keys()):
            actual = layer_counts[layer]
            expected_ratio = phase_distribution.get(layer, 0.0)
            expected = int(batch_size * expected_ratio)
            print(f"    Layer {layer}: {actual}件 (期待値: {expected}件, 比率: {expected_ratio:.0%})")
        
        return str(output_file)
    
    def generate_training_schedule(self, start_epoch: int = 1, end_epoch: int = 25,
                                   batch_size: int = 100) -> Dict[str, Any]:
        """全エポックの学習スケジュールを生成"""
        print("=" * 60)
        print("CASTLE-EX 学習スケジュール生成")
        print("=" * 60)
        print(f"エポック範囲: {start_epoch} - {end_epoch}")
        print(f"バッチサイズ: {batch_size}")
        
        schedule = {
            "generated_at": datetime.now().isoformat(),
            "start_epoch": start_epoch,
            "end_epoch": end_epoch,
            "batch_size": batch_size,
            "epochs": []
        }
        
        for epoch in range(start_epoch, end_epoch + 1):
            phase_distribution = self.get_phase_for_epoch(epoch)
            output_file = self.generate_epoch_dataset(epoch, batch_size)
            
            schedule["epochs"].append({
                "epoch": epoch,
                "file": output_file,
                "distribution": phase_distribution,
            })
        
        # スケジュール情報を保存
        schedule_file = self.output_dir / "training_schedule.json"
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)
        
        print(f"\nスケジュール情報を保存: {schedule_file}")
        
        return schedule
    
    def print_schedule_summary(self, schedule: Dict[str, Any]):
        """スケジュールサマリーの表示"""
        print("\n" + "=" * 60)
        print("学習スケジュールサマリー")
        print("=" * 60)
        
        # フェーズ別にグループ化
        phases = defaultdict(list)
        for epoch_info in schedule["epochs"]:
            epoch = epoch_info["epoch"]
            phase_distribution = epoch_info["distribution"]
            
            # フェーズを特定
            phase_name = None
            if 1 <= epoch <= 5:
                phase_name = "Phase 1: 公理層のみ"
            elif 6 <= epoch <= 9:
                phase_name = "Phase 2: 操作層追加"
            elif 10 <= epoch <= 12:
                phase_name = "Phase 3: 関係層追加"
            elif 13 <= epoch <= 15:
                phase_name = "Phase 4: 感情・文脈基礎層"
            elif 16 <= epoch <= 20:
                phase_name = "Phase 5: 因果層統合"
            else:
                phase_name = "Phase 6: 統合層"
            
            phases[phase_name].append(epoch)
        
        for phase_name, epochs in sorted(phases.items()):
            print(f"\n{phase_name}:")
            print(f"  エポック: {min(epochs)} - {max(epochs)}")
            sample_epoch = min(epochs)
            sample_info = next(e for e in schedule["epochs"] if e["epoch"] == sample_epoch)
            print(f"  層別配分:")
            for layer, ratio in sorted(sample_info["distribution"].items()):
                print(f"    Layer {layer}: {ratio:.0%}")


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CASTLE-EX学習パイプライン')
    parser.add_argument('dataset', type=str, help='入力データセットJSONLファイル')
    parser.add_argument('--output-dir', type=str, default='./castle_ex_training',
                       help='出力ディレクトリ（デフォルト: ./castle_ex_training）')
    parser.add_argument('--start-epoch', type=int, default=1,
                       help='開始エポック（デフォルト: 1）')
    parser.add_argument('--end-epoch', type=int, default=25,
                       help='終了エポック（デフォルト: 25）')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='バッチサイズ（デフォルト: 100）')
    
    args = parser.parse_args()
    
    pipeline = CastleEXTrainingPipeline(args.dataset, args.output_dir)
    pipeline.load_dataset()
    schedule = pipeline.generate_training_schedule(
        args.start_epoch, args.end_epoch, args.batch_size
    )
    pipeline.print_schedule_summary(schedule)
    
    print("\n✓ 学習スケジュール生成が完了しました")


if __name__ == "__main__":
    main()
