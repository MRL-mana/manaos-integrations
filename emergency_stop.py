#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚨 ManaOS 緊急停止システム
すべてのサービスを安全に停止する最後の手段
"""

import subprocess
import sys
import time
import logging
from typing import List, Dict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s'
)
logger = logging.getLogger(__name__)


class EmergencyStop:
    """緊急停止システム"""
    
    # 停止対象のプロセスキーワード
    MANAOS_PROCESS_KEYWORDS = [
        "mrl_memory",
        "learning_system",
        "llm_routing",
        "unified_api",
        "autonomous_operations",
        "start_vscode_cursor_services"
    ]
    
    def __init__(self):
        """初期化"""
        self.stopped_processes: List[Dict] = []
        logger.info("🚨 緊急停止システムを初期化しました")
    
    def find_manaos_processes(self) -> List[Dict]:
        """
        ManaOS関連のPythonプロセスを検索
        
        Returns:
            プロセス情報のリスト
        """
        try:
            # PowerShellコマンドでプロセスを検索
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process python | Where-Object { $_.CommandLine -like '*manaos*' } | Select-Object Id,ProcessName,CommandLine | ConvertTo-Json"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.warning(f"プロセス検索失敗: {result.stderr}")
                return []
            
            # JSONパース
            import json
            output = result.stdout.strip()
            if not output or output == "null":
                return []
            
            processes = json.loads(output)
            if not isinstance(processes, list):
                processes = [processes]
            
            return processes
            
        except Exception as e:
            logger.error(f"プロセス検索エラー: {e}")
            return []
    
    def stop_process(self, pid: int, name: str = "unknown") -> bool:
        """
        プロセスを停止
        
        Args:
            pid: プロセスID
            name: プロセス名
            
        Returns:
            停止成功したらTrue
        """
        try:
            # まず穏やかに終了を試みる
            logger.info(f"プロセスを停止中: PID={pid}, Name={name}")
            
            cmd = ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -ErrorAction SilentlyContinue"]
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            
            # 停止を確認
            time.sleep(1)
            check_cmd = ["powershell", "-NoProfile", "-Command", f"Get-Process -Id {pid} -ErrorAction SilentlyContinue"]
            check_result = subprocess.run(check_cmd, capture_output=True, timeout=5)
            
            if check_result.returncode != 0:
                # プロセスが見つからない = 停止成功
                logger.info(f"✅ プロセス {pid} を停止しました")
                return True
            else:
                # まだ動いている場合は強制終了
                logger.warning(f"⚠️ プロセス {pid} の穏やかな停止に失敗。強制終了します")
                force_cmd = ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force"]
                subprocess.run(force_cmd, capture_output=True, timeout=5)
                time.sleep(1)
                logger.info(f"✅ プロセス {pid} を強制終了しました")
                return True
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ プロセス {pid} の停止がタイムアウトしました")
            return False
        except Exception as e:
            logger.error(f"❌ プロセス {pid} の停止エラー: {e}")
            return False
    
    def execute(self, confirm: bool = True) -> bool:
        """
        緊急停止を実行
        
        Args:
            confirm: 確認を求めるか
            
        Returns:
            すべて停止成功したらTrue
        """
        logger.warning("\n" + "="*60)
        logger.warning("🚨 緊急停止システムを起動します")
        logger.warning("="*60)
        
        # プロセスを検索
        logger.info("ManaOS関連プロセスを検索中...")
        processes = self.find_manaos_processes()
        
        if not processes:
            logger.info("✅ 停止対象のプロセスは見つかりませんでした")
            return True
        
        logger.warning(f"⚠️ {len(processes)}個のプロセスが見つかりました:")
        for proc in processes:
            pid = proc.get("Id", "unknown")
            cmd = proc.get("CommandLine", "unknown")
            # コマンドラインを短縮表示
            cmd_short = cmd[:80] + "..." if len(cmd) > 80 else cmd
            logger.warning(f"  PID {pid}: {cmd_short}")
        
        # 確認
        if confirm:
            print("\n⚠️ これらのプロセスをすべて停止します。よろしいですか？")
            response = input("続行するには 'yes' と入力してください: ")
            if response.lower() != 'yes':
                logger.info("キャンセルしました")
                return False
        
        # すべて停止
        logger.info("\nプロセスを停止中...")
        success_count = 0
        
        for proc in processes:
            pid = proc.get("Id")
            name = proc.get("ProcessName", "python")
            
            if self.stop_process(pid, name):
                success_count += 1
                self.stopped_processes.append(proc)
        
        # 結果表示
        logger.info("\n" + "="*60)
        if success_count == len(processes):
            logger.info(f"✅ すべてのプロセス（{success_count}個）を停止しました")
            return True
        else:
            logger.warning(f"⚠️ {success_count}/{len(processes)} 個のプロセスを停止しました")
            logger.warning(f"❌ {len(processes) - success_count} 個の停止に失敗")
            return False
    
    def get_stopped_count(self) -> int:
        """停止したプロセス数を取得"""
        return len(self.stopped_processes)


def main():
    """メイン処理"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🚨 ManaOS 緊急停止システム 🚨                   ║
║                                                              ║
║  すべてのManaOS関連プロセスを停止します                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 緊急停止を実行
    emergency = EmergencyStop()
    
    try:
        success = emergency.execute(confirm=True)
        
        if success:
            print("\n✅ 緊急停止が完了しました")
            print(f"   停止したプロセス数: {emergency.get_stopped_count()}")
            return 0
        else:
            print("\n⚠️ 一部のプロセスの停止に失敗しました")
            print("   タスクマネージャーで手動確認が必要です")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nキャンセルされました")
        return 1
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
