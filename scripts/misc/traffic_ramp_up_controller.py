#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManaOS v1.0 トラフィックラムアップ管理・制御システム
Traffic Ramp-Up System Controller & Manager
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
import subprocess
import signal
import time

class TrafficRampUpController:
    """トラフィック投入システムの管理・制御"""
    
    def __init__(self):
        self.state_file = Path("traffic_rampup_state.json")
        self.log_file = Path("traffic_rampup.log")
        self.metrics_file = Path("metrics/traffic_rampup_metrics.json")
        self.process = None
    
    def start(self):
        """トラフィック投入システムを起動"""
        print(f"""
╔════════════════════════════════════════════════════════════════════╗
║              🚀 トラフィック段階投入システム起動                      ║
╠════════════════════════════════════════════════════════════════════╣
║ 時刻: {datetime.utcnow().isoformat()}
║ スクリプト: automated_traffic_ramp_up.py
║ ログファイル: {self.log_file}
║ 状態ファイル: {self.state_file}
║
║ フェーズ構成:
║   Phase 1:  10% トラフィック (30分)
║   Phase 2:  30% トラフィック (1時間)
║   Phase 3: 100% トラフィック (本格稼動)
╚════════════════════════════════════════════════════════════════════╝
        """)
        
        try:
            self.process = subprocess.Popen(
                [sys.executable, "automated_traffic_ramp_up.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            print(f"✅ プロセス起動成功 (PID: {self.process.pid})")
            
            # PIDをファイルに保存
            with open("traffic_rampup.pid", "w") as f:
                f.write(str(self.process.pid))
            
            # ログ出力を表示
            self.monitor_output()
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            sys.exit(1)
    
    def monitor_output(self):
        """プロセス出力を監視"""
        try:
            while True:
                line = self.process.stdout.readline()
                if line:
                    print(line.rstrip())
                else:
                    break
        except KeyboardInterrupt:
            print("\n⚠️ 監視を中断します...")
    
    def status(self):
        """現在の状態を表示"""
        if not self.state_file.exists():
            print("❌ 状態ファイルが見つかりません")
            return
        
        with open(self.state_file) as f:
            state = json.load(f)
        
        current_phase = state.get("current_phase", "unknown")
        
        print(f"""
╔════════════════════════════════════════════════════════════════════╗
║                  トラフィック投入システム状態                        ║
╠════════════════════════════════════════════════════════════════════╣
║ 現在フェーズ: {current_phase.upper()}
║ 更新時刻: {state.get('timestamp', 'N/A')}
║
║ ログファイル内容 (最後の20行):
╚════════════════════════════════════════════════════════════════════╝
        """)
        
        if self.log_file.exists():
            with open(self.log_file) as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.rstrip())
    
    def metrics(self):
        """メトリクスを表示"""
        if not self.metrics_file.exists():
            print("❌ メトリクスファイルが見つかりません")
            return
        
        with open(self.metrics_file) as f:
            metrics = json.load(f)
        
        print("""
╔════════════════════════════════════════════════════════════════════╗
║                      パフォーマンスメトリクス                        ║
╠════════════════════════════════════════════════════════════════════╣
        """)
        
        for phase in ["phase1", "phase2", "phase3"]:
            phase_metrics = metrics.get(phase, [])
            if phase_metrics:
                latest = phase_metrics[-1]
                print(f"""
{phase.upper()}:
  タイムスタンプ: {latest.get('timestamp', 'N/A')}
  稼働サービス: {latest.get('services_up', 0)}/{len(latest.get('services', {}))}
  平均応答時間: {latest.get('average_latency_ms', 0):.1f}ms
  エラー率: {latest.get('error_rate', 0):.1f}%
  ヘルスチェック成功率: {latest.get('health_check_pass_rate', 0):.1f}%
                """)
        
        print("╚════════════════════════════════════════════════════════════════════╝")
    
    def skip_phase(self, target_phase: str):
        """指定フェーズへスキップ"""
        if target_phase not in ["phase1", "phase2", "phase3"]:
            print(f"❌ 無効なフェーズ: {target_phase}")
            return
        
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    state = json.load(f)
            else:
                state = {}
            
            state["current_phase"] = target_phase
            state["timestamp"] = datetime.utcnow().isoformat()
            
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
            
            print(f"""
✅ フェーズスキップ成功
   対象フェーズ: {target_phase.upper()}
   更新時刻: {state['timestamp']}
            """)
        except Exception as e:
            print(f"❌ エラー: {e}")
    
    def rollback(self):
        """前のフェーズへロールバック"""
        if not self.state_file.exists():
            print("❌ 状態ファイルが見つかりません")
            return
        
        phase_progression = {
            "phase1": "phase1",
            "phase2": "phase1",
            "phase3": "phase2",
        }
        
        with open(self.state_file) as f:
            state = json.load(f)
        
        current_phase = state.get("current_phase", "phase1")
        previous_phase = phase_progression.get(current_phase, "phase1")
        
        state["current_phase"] = previous_phase
        state["timestamp"] = datetime.utcnow().isoformat()
        
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)
        
        print(f"""
⚠️ ロールバック実行
   {current_phase.upper()} → {previous_phase.upper()}
   更新時刻: {state['timestamp']}
        """)
    
    def stop(self):
        """システムを停止"""
        pid_file = Path("traffic_rampup.pid")
        
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text())
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
                print(f"✅ プロセス {pid} を停止しました")
                pid_file.unlink()
            except Exception as e:
                print(f"⚠️ 停止時エラー: {e}")
        else:
            print("❌ PIDファイルが見つかりません")


def print_help():
    """ヘルプを表示"""
    print("""
ManaOS v1.0 トラフィック段階投入システム コントローラー
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

使用方法:
  python traffic_ramp_up_controller.py [コマンド] [オプション]

コマンド:
  start              - トラフィック投入システムを起動
  status             - 現在の状態を表示
  metrics            - パフォーマンスメトリクスを表示
  skip <phase>       - 指定フェーズへスキップ (phase1/phase2/phase3)
  rollback           - 前のフェーズへロールバック
  stop               - システムを停止
  help               - このヘルプを表示

例:
  python traffic_ramp_up_controller.py start
  python traffic_ramp_up_controller.py status
  python traffic_ramp_up_controller.py skip phase3
  python traffic_ramp_up_controller.py rollback
    """)


if __name__ == "__main__":
    controller = TrafficRampUpController()
    
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "start":
        controller.start()
    elif command == "status":
        controller.status()
    elif command == "metrics":
        controller.metrics()
    elif command == "skip":
        if len(sys.argv) < 3:
            print("❌ フェーズを指定してください")
            sys.exit(1)
        controller.skip_phase(sys.argv[2])
    elif command == "rollback":
        controller.rollback()
    elif command == "stop":
        controller.stop()
    elif command == "help":
        print_help()
    else:
        print(f"❌ 不明なコマンド: {command}")
        print_help()
        sys.exit(1)
