#!/usr/bin/env python3
"""
Level 3 マスターコントローラー
全Level 3システムを統括
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict
import sys
import subprocess

sys.path.insert(0, '/root')
from level3.autonomous_decision_engine import AutonomousDecisionEngine
from level3.agi_evolution_engine import AGIEvolutionEngine
from level3.auto_bug_fix_system import AutoBugFixSystem
from integrated_monitoring_system import IntegratedMonitoringSystem

class Level3MasterController:
    """Level 3マスターコントローラー"""
    
    def __init__(self):
        self.decision_engine = AutonomousDecisionEngine()
        self.agi_engine = AGIEvolutionEngine()
        self.bugfix_system = AutoBugFixSystem()
        self.monitor = IntegratedMonitoringSystem()
        self.status_file = Path("/root/level3/level3_status.json")
    
    def log(self, message: str):
        """ログ出力"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    async def start_all_systems(self):
        """全システム起動"""
        self.log("=" * 70)
        self.log("🚀 Level 3 全システム起動中...")
        self.log("=" * 70)
        
        processes = []
        
        # 1. AGI進化エンジン（バックグラウンド）
        self.log("\n1️⃣ AGI進化エンジン起動中...")
        proc1 = subprocess.Popen([
            "python3", "/root/level3/agi_evolution_engine.py", "continuous"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(("AGI進化エンジン", proc1))
        self.log("✅ AGI進化エンジン起動完了（PID: {})".format(proc1.pid))
        
        # 2. 自動バグ修正システム（バックグラウンド）
        self.log("\n2️⃣ 自動バグ修正システム起動中...")
        proc2 = subprocess.Popen([
            "python3", "/root/level3/auto_bug_fix_system.py", "continuous"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(("自動バグ修正", proc2))
        self.log("✅ 自動バグ修正システム起動完了（PID: {})".format(proc2.pid))
        
        # ステータス保存
        status = {
            "started_at": datetime.now().isoformat(),
            "processes": [
                {"name": name, "pid": proc.pid}
                for name, proc in processes
            ]
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)
        
        self.log("\n" + "=" * 70)
        self.log("✅ Level 3全システム起動完了")
        self.log("=" * 70)
        self.log(f"\nステータスファイル: {self.status_file}")
        
        return processes
    
    async def stop_all_systems(self):
        """全システム停止"""
        self.log("=" * 70)
        self.log("⏹️  Level 3 全システム停止中...")
        self.log("=" * 70)
        
        if not self.status_file.exists():
            self.log("ステータスファイルが見つかりません")
            return
        
        with open(self.status_file, 'r') as f:
            status = json.load(f)
        
        for proc_info in status['processes']:
            name = proc_info['name']
            pid = proc_info['pid']
            
            try:
                subprocess.run(["kill", str(pid)])
                self.log(f"✅ {name} 停止完了（PID: {pid})")
            except:
                self.log(f"⚠️  {name} 停止失敗（PID: {pid}）")
        
        self.status_file.unlink()
        
        self.log("\n" + "=" * 70)
        self.log("✅ Level 3全システム停止完了")
        self.log("=" * 70)
    
    async def get_comprehensive_status(self) -> Dict:
        """総合ステータス取得"""
        self.log("📊 総合ステータス取得中...")
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "level3_running": self.status_file.exists(),
            "decision_engine": {},
            "agi_engine": {},
            "bugfix_system": {},
            "overall_health": 0
        }
        
        # 各システムの統計取得
        try:
            status['decision_engine'] = await self.decision_engine.get_decision_stats()
        except:
            pass
        
        try:
            status['agi_engine'] = await self.agi_engine.get_evolution_stats()
        except:
            pass
        
        try:
            status['bugfix_system'] = await self.bugfix_system.get_fix_stats()
        except:
            pass
        
        # 総合ヘルススコア計算
        health_score = 0
        
        if status['level3_running']:
            health_score += 30
        
        if status['decision_engine'].get('total', 0) > 0:
            health_score += 20
        
        if status['agi_engine'].get('total_nights', 0) > 0:
            health_score += 25
        
        if status['bugfix_system'].get('total_errors', 0) > 0:
            health_score += 25
        
        status['overall_health'] = health_score
        
        return status
    
    def print_status(self, status: Dict):
        """ステータスを整形表示"""
        print("\n" + "=" * 70)
        print("📊 Level 3 総合ステータス")
        print("=" * 70)
        print(f"生成日時: {status['timestamp']}")
        print(f"Level 3稼働: {'✅ 稼働中' if status['level3_running'] else '⏹️  停止中'}")
        print(f"総合ヘルススコア: {status['overall_health']}/100")
        print()
        
        # 自律判断エンジン
        print("🤖 完全自律判断エンジン:")
        dec = status['decision_engine']
        if dec:
            print(f"  総判断数: {dec.get('total', 0)}")
            print(f"  自動実装: {dec.get('auto_implemented', 0)}")
            print(f"  自動化率: {dec.get('auto_rate', 0):.1f}%")
        else:
            print("  データなし")
        print()
        
        # AGI進化エンジン
        print("🌙 AGI進化エンジン:")
        agi = status['agi_engine']
        if agi:
            print(f"  総サイクル数: {agi.get('total_nights', 0)}")
            print(f"  総実装数: {agi.get('total_implementations', 0)}")
            print(f"  総コード行数: {agi.get('total_code_lines', 0)}")
        else:
            print("  データなし")
        print()
        
        # 自動バグ修正
        print("🔧 自動バグ修正システム:")
        bug = status['bugfix_system']
        if bug:
            print(f"  総エラー数: {bug.get('total_errors', 0)}")
            print(f"  自動修正: {bug.get('auto_fixed', 0)}")
            if bug.get('auto_fixed', 0) > 0:
                print(f"  平均修正時間: {bug.get('average_fix_time', 0):.1f}秒")
        else:
            print("  データなし")
        
        print("=" * 70)

async def main():
    import sys
    
    controller = Level3MasterController()
    
    if len(sys.argv) < 2:
        print("\n" + "=" * 70)
        print("🎮 Level 3 マスターコントローラー")
        print("=" * 70)
        print("\n使い方:")
        print("  python3 level3_master_controller.py start   # 全システム起動")
        print("  python3 level3_master_controller.py stop    # 全システム停止")
        print("  python3 level3_master_controller.py status  # ステータス確認")
        print("  python3 level3_master_controller.py emergency_stop  # 緊急停止")
        print()
        return
    
    command = sys.argv[1]
    
    if command == "start":
        await controller.start_all_systems()
    
    elif command == "stop":
        await controller.stop_all_systems()
    
    elif command == "status":
        status = await controller.get_comprehensive_status()
        controller.print_status(status)
    
    elif command == "emergency_stop":
        print("\n⚠️  緊急停止実行")
        await controller.stop_all_systems()
    
    else:
        print(f"未知のコマンド: {command}")

if __name__ == "__main__":
    asyncio.run(main())

