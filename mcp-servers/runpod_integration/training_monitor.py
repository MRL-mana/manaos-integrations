#!/usr/bin/env python3
"""
学習進捗監視システム
学習中の進捗状況をリアルタイムで監視
"""

import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, Any, Optional, List

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')


class TrainingMonitor:
    """学習進捗監視クラス"""

    def __init__(self, log_dir: str = "/root/runpod_integration/training_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def create_training_session(
        self,
        session_name: str,
        dataset_name: str,
        trigger_word: str,
        steps: int,
        learning_rate: float
    ) -> Dict[str, Any]:
        """
        学習セッションを作成

        Args:
            session_name: セッション名
            dataset_name: データセット名
            trigger_word: トリガーワード
            steps: 総ステップ数
            learning_rate: 学習率

        Returns:
            セッション情報
        """
        session_dir = self.log_dir / session_name
        session_dir.mkdir(parents=True, exist_ok=True)

        session_info = {
            "session_name": session_name,
            "dataset_name": dataset_name,
            "trigger_word": trigger_word,
            "total_steps": steps,
            "learning_rate": learning_rate,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "current_step": 0,
            "loss_history": [],
            "progress": 0.0
        }

        # セッション情報を保存
        info_file = session_dir / "session_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(session_info, f, indent=2, ensure_ascii=False)

        return session_info

    def update_progress(
        self,
        session_name: str,
        current_step: int,
        loss: float,
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        学習進捗を更新

        Args:
            session_name: セッション名
            current_step: 現在のステップ
            loss: 損失値
            additional_info: 追加情報

        Returns:
            更新されたセッション情報
        """
        session_dir = self.log_dir / session_name
        info_file = session_dir / "session_info.json"

        if not info_file.exists():
            return {
                "success": False,
                "error": f"セッションが見つかりません: {session_name}"
            }

        # セッション情報を読み込み
        with open(info_file, 'r', encoding='utf-8') as f:
            session_info = json.load(f)

        # 進捗を更新
        session_info["current_step"] = current_step
        session_info["progress"] = (current_step / session_info["total_steps"]) * 100
        session_info["loss_history"].append({
            "step": current_step,
            "loss": loss,
            "timestamp": datetime.now().isoformat()
        })

        if additional_info:
            session_info.update(additional_info)

        # 保存
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(session_info, f, indent=2, ensure_ascii=False)

        return session_info

    def complete_training(
        self,
        session_name: str,
        output_path: str,
        final_loss: float
    ) -> Dict[str, Any]:
        """
        学習完了を記録

        Args:
            session_name: セッション名
            output_path: 出力モデルパス
            final_loss: 最終損失値

        Returns:
            セッション情報
        """
        session_dir = self.log_dir / session_name
        info_file = session_dir / "session_info.json"

        if not info_file.exists():
            return {
                "success": False,
                "error": f"セッションが見つかりません: {session_name}"
            }

        # セッション情報を読み込み
        with open(info_file, 'r', encoding='utf-8') as f:
            session_info = json.load(f)

        # 完了情報を更新
        session_info["status"] = "completed"
        session_info["completed_at"] = datetime.now().isoformat()
        session_info["output_path"] = output_path
        session_info["final_loss"] = final_loss

        # 経過時間を計算
        started_at = datetime.fromisoformat(session_info["started_at"])
        completed_at = datetime.now()
        elapsed = (completed_at - started_at).total_seconds()
        session_info["elapsed_time"] = elapsed

        # 保存
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(session_info, f, indent=2, ensure_ascii=False)

        return session_info

    def get_session_info(self, session_name: str) -> Dict[str, Any]:
        """セッション情報を取得"""
        session_dir = self.log_dir / session_name
        info_file = session_dir / "session_info.json"

        if not info_file.exists():
            return {
                "success": False,
                "error": f"セッションが見つかりません: {session_name}"
            }

        with open(info_file, 'r', encoding='utf-8') as f:
            session_info = json.load(f)

        return {
            "success": True,
            **session_info
        }

    def list_sessions(self) -> List[Dict[str, Any]]:
        """全セッション一覧を取得"""
        sessions = []

        for session_dir in self.log_dir.iterdir():
            if not session_dir.is_dir():
                continue

            info_file = session_dir / "session_info.json"
            if info_file.exists():
                with open(info_file, 'r', encoding='utf-8') as f:
                    session_info = json.load(f)
                    sessions.append(session_info)

        # 開始日時でソート（新しい順）
        sessions.sort(key=lambda x: x.get('started_at', ''), reverse=True)

        return sessions

    def get_progress_summary(self, session_name: str) -> Dict[str, Any]:
        """進捗サマリーを取得"""
        session_info = self.get_session_info(session_name)

        if not session_info.get('success'):
            return session_info

        loss_history = session_info.get('loss_history', [])

        if loss_history:
            recent_losses = loss_history[-10:]  # 直近10ステップ
            avg_loss = sum(l['loss'] for l in recent_losses) / len(recent_losses)
            min_loss = min(l['loss'] for l in loss_history)
            max_loss = max(l['loss'] for l in loss_history)
        else:
            avg_loss = min_loss = max_loss = 0.0

        return {
            "session_name": session_name,
            "status": session_info.get('status'),
            "progress": session_info.get('progress', 0.0),
            "current_step": session_info.get('current_step', 0),
            "total_steps": session_info.get('total_steps', 0),
            "avg_loss": avg_loss,
            "min_loss": min_loss,
            "max_loss": max_loss,
            "loss_trend": "down" if len(loss_history) > 1 and loss_history[-1]['loss'] < loss_history[0]['loss'] else "up"
        }


def main():
    """メイン処理"""
    monitor = TrainingMonitor()

    print("📊 学習進捗監視システム")
    print("=" * 60)
    print()

    # セッション一覧を表示
    print("📁 学習セッション一覧:")
    sessions = monitor.list_sessions()

    if sessions:
        for session in sessions[:5]:  # 最新5件
            print(f"  - {session['session_name']}")
            print(f"    ステータス: {session.get('status', 'unknown')}")
            print(f"    進捗: {session.get('progress', 0.0):.1f}%")
            print(f"    開始: {session.get('started_at', '不明')}")

            if session.get('status') == 'completed':
                print(f"    完了: {session.get('completed_at', '不明')}")
                print(f"    経過時間: {session.get('elapsed_time', 0):.0f}秒")
            print()
    else:
        print("  （セッションなし）")
        print()
        print("💡 学習セッションを作成するには:")
        print("   monitor = TrainingMonitor()")
        print("   monitor.create_training_session(...)")


if __name__ == "__main__":
    main()

