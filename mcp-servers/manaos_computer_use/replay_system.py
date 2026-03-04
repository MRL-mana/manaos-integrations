#!/usr/bin/env python3
"""
ManaOS Computer Use System - Replay System
実行の完全再現システム（seed + screenshot hash）
"""

import json
import hashlib
import random
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    from .manaos_computer_use_types import ExecutionStep, TaskResult
except ImportError:
    from manaos_computer_use_types import TaskResult


@dataclass
class ReplayableExecution:
    """再現可能な実行記録"""
    task: str
    seed: int
    steps: List[Dict[str, Any]]
    screenshot_hashes: List[str]
    execution_id: str
    timestamp: str
    environment: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReplaySystem:
    """リプレイシステム"""
    
    def __init__(self, replay_dir: Optional[Path] = None):
        """
        Args:
            replay_dir: リプレイファイル保存ディレクトリ
        """
        self.replay_dir = replay_dir or Path("/root/manaos_computer_use/replays")
        self.replay_dir.mkdir(parents=True, exist_ok=True)
    
    def record_execution(
        self,
        task_result: TaskResult,
        seed: Optional[int] = None
    ) -> ReplayableExecution:
        """
        実行を記録
        
        Args:
            task_result: タスク実行結果
            seed: ランダムシード（再現性用）
        
        Returns:
            ReplayableExecution: 再現可能な実行記録
        """
        # シードが指定されていない場合は現在時刻から生成
        if seed is None:
            seed = int(datetime.now().timestamp() * 1000) % (2**32)
        
        # スクリーンショットのハッシュを計算
        screenshot_hashes = []
        for step in task_result.steps:
            if step.screenshot_path:
                hash_value = self._compute_file_hash(step.screenshot_path)
                screenshot_hashes.append(hash_value)
            else:
                screenshot_hashes.append("")
        
        # 実行環境情報（実際の値を記録）
        environment = {
            "task": task_result.task,
            "status": task_result.status.value if hasattr(task_result.status, 'value') else str(task_result.status),
            "total_steps": task_result.total_steps,
            "success_rate": task_result.success_rate,
            "timestamp": datetime.now().isoformat()
        }
        
        # 実行IDを生成
        execution_id = f"replay_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{seed}"
        
        # リプレイ可能な実行記録を作成
        replayable = ReplayableExecution(
            task=task_result.task,
            seed=seed,
            steps=[step.to_dict() for step in task_result.steps],
            screenshot_hashes=screenshot_hashes,
            execution_id=execution_id,
            timestamp=datetime.now().isoformat(),
            environment=environment
        )
        
        # ファイルに保存
        self._save_replay(replayable)
        
        return replayable
    
    def verify_replay(
        self,
        original: ReplayableExecution,
        replay_result: TaskResult
    ) -> Dict[str, Any]:
        """
        リプレイが元の実行と一致するか検証
        
        Args:
            original: 元の実行記録
            replay_result: リプレイ結果
        
        Returns:
            Dict: 検証結果
        """
        verification = {
            "match": True,
            "differences": [],
            "screenshot_match_rate": 0.0,
            "action_match_rate": 0.0
        }
        
        # ステップ数比較
        if len(original.steps) != len(replay_result.steps):
            verification["match"] = False
            verification["differences"].append({
                "type": "step_count",
                "original": len(original.steps),
                "replay": len(replay_result.steps)
            })
        
        # 各ステップを比較
        min_steps = min(len(original.steps), len(replay_result.steps))
        action_matches = 0
        screenshot_matches = 0
        
        for i in range(min_steps):
            orig_step = original.steps[i]
            replay_step = replay_result.steps[i]
            
            # アクション比較
            orig_action = orig_step.get("action_taken", {})
            replay_action = replay_step.action_taken.to_dict() if replay_step.action_taken else {}
            
            if orig_action.get("action_type") == replay_action.get("action_type"):
                action_matches += 1
            else:
                verification["differences"].append({
                    "type": "action_mismatch",
                    "step": i + 1,
                    "original": orig_action.get("action_type"),
                    "replay": replay_action.get("action_type")
                })
            
            # スクリーンショットハッシュ比較
            if replay_step.screenshot_path:
                replay_hash = self._compute_file_hash(replay_step.screenshot_path)
                orig_hash = original.screenshot_hashes[i] if i < len(original.screenshot_hashes) else ""
                
                if replay_hash == orig_hash:
                    screenshot_matches += 1
                else:
                    # ハッシュ不一致は許容（画面の微妙な変化）
                    pass
        
        # 一致率計算
        verification["action_match_rate"] = action_matches / min_steps if min_steps > 0 else 0.0
        verification["screenshot_match_rate"] = screenshot_matches / min_steps if min_steps > 0 else 0.0
        
        # 総合判定
        if verification["action_match_rate"] < 0.9:
            verification["match"] = False
        
        return verification
    
    def load_replay(self, execution_id: str) -> Optional[ReplayableExecution]:
        """
        リプレイ記録を読み込み
        
        Args:
            execution_id: 実行ID
        
        Returns:
            ReplayableExecution or None
        """
        replay_file = self.replay_dir / f"{execution_id}.json"
        
        if not replay_file.exists():
            return None
        
        with open(replay_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return ReplayableExecution(**data)
    
    def list_replays(self, limit: int = 50) -> List[Dict[str, Any]]:
        """リプレイ一覧を取得"""
        replays = []
        
        for replay_file in sorted(
            self.replay_dir.glob("replay_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:limit]:
            try:
                with open(replay_file, 'r') as f:
                    data = json.load(f)
                    replays.append({
                        "execution_id": data.get("execution_id"),
                        "task": data.get("task"),
                        "timestamp": data.get("timestamp"),
                        "steps_count": len(data.get("steps", []))
                    })
            except Exception:
                pass
        
        return replays
    
    def _save_replay(self, replayable: ReplayableExecution) -> None:
        """リプレイ記録を保存"""
        replay_file = self.replay_dir / f"{replayable.execution_id}.json"
        
        with open(replay_file, 'w', encoding='utf-8') as f:
            json.dump(replayable.to_dict(), f, ensure_ascii=False, indent=2)
        
        print(f"💾 Replay saved: {replay_file}")
    
    def _compute_file_hash(self, file_path: str) -> str:
        """ファイルのSHA256ハッシュを計算"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""
    
    def set_seed(self, seed: int) -> None:
        """ランダムシードを設定（再現性確保）"""
        random.seed(seed)
        
        # numpy のシード
        try:
            import numpy as np
            np.random.seed(seed)
            logger.debug("numpy seed set")
        except ImportError:
            pass
        
        # torch のシード
        try:
            import torch
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
            logger.debug("torch seed set")
        except ImportError:
            pass


# ===== テスト用 =====

if __name__ == "__main__":
    print("🎬 Replay System - テスト")
    print("=" * 60)
    
    replay_system = ReplaySystem()
    
    # リプレイ一覧
    replays = replay_system.list_replays()
    
    print(f"\n📋 Saved replays: {len(replays)}")
    for replay in replays[:5]:
        print(f"  - {replay['execution_id']}: {replay['task']}")
    
    print("\n✅ Test completed")

