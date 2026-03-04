#!/usr/bin/env python3
"""
Mana Process Cleaner
重複・不要プロセスの自動クリーンアップ
"""

import psutil
import logging
from typing import Dict, List, Any
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaProcessCleaner:
    def __init__(self):
        # 保護するプロセス（絶対に停止しない）
        self.protected_processes = [
            "mana_screen_sharing_enhanced.py",
            "trinity_secretary_enhanced.py",
            "mana_unified_dashboard.py",
            "manaos_v3",
            "trinity_google_services.py",
            "manaspec_llm_remi.py",
            "manaspec_telegram_bot.py",
            "trinity_telegram_bot.py"
        ]
        
        logger.info("🧹 Mana Process Cleaner 初期化")
    
    def find_duplicate_processes(self) -> Dict[str, List[int]]:
        """重複プロセス検出"""
        processes = defaultdict(list)
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                # Python3プロセスのみ対象
                if proc.info['name'] == 'python3' and cmdline:
                    # コマンドラインを正規化
                    normalized = cmdline.strip()
                    processes[normalized].append(proc.info['pid'])
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # 重複のみ返す
        duplicates = {cmd: pids for cmd, pids in processes.items() if len(pids) > 1}
        return duplicates
    
    def find_old_screen_sharing(self) -> List[int]:
        """古いscreen_sharingプロセスを検出"""
        old_pids = []
        
        for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                # 古いmana_screen_sharing.py（enhanced版ではない）
                if 'mana_screen_sharing.py' in cmdline and 'enhanced' not in cmdline:
                    old_pids.append(proc.info['pid'])
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return old_pids
    
    def find_unnecessary_streamlit(self) -> List[Dict[str, Any]]:
        """不要なStreamlitサービスを検出"""
        streamlit_processes = []
        
        for proc in psutil.process_iter(['pid', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                
                if 'streamlit run' in cmdline:
                    # サービス名を抽出
                    import re
                    match = re.search(r'streamlit run\s+(.+?)\.py', cmdline)
                    service_name = match.group(1).split('/')[-1] if match else "unknown"
                    
                    streamlit_processes.append({
                        "pid": proc.info['pid'],
                        "service": service_name,
                        "cmdline": cmdline[:100],
                        "cpu": proc.info['cpu_percent'],
                        "memory": proc.info['memory_percent']
                    })
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return streamlit_processes
    
    def clean_duplicates(self, dry_run: bool = True) -> Dict[str, Any]:
        """重複プロセスクリーンアップ"""
        logger.info("🧹 重複プロセスをクリーンアップ中...")
        
        duplicates = self.find_duplicate_processes()
        old_screen_sharing = self.find_old_screen_sharing()
        
        stopped = []
        protected = []
        
        # 古いscreen_sharingを停止
        for pid in old_screen_sharing:
            if not dry_run:
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    stopped.append({"pid": pid, "service": "old_screen_sharing"})
                    logger.info(f"停止: PID {pid} (old screen_sharing)")
                except Exception as e:
                    logger.error(f"プロセス停止エラー ({pid}): {e}")
            else:
                logger.info(f"[DRY RUN] 停止予定: PID {pid} (old screen_sharing)")
        
        # 重複プロセスの古い方を停止
        for cmdline, pids in duplicates.items():
            # 保護プロセスチェック
            if any(protected in cmdline for protected in self.protected_processes):
                protected.append({"cmdline": cmdline[:100], "pids": pids})
                continue
            
            if len(pids) > 1:
                # 古いプロセス（最初のPID以外）を停止
                for pid in pids[1:]:
                    if not dry_run:
                        try:
                            proc = psutil.Process(pid)
                            proc.terminate()
                            stopped.append({"pid": pid, "cmdline": cmdline[:100]})
                            logger.info(f"停止: PID {pid}")
                        except Exception as e:
                            logger.error(f"プロセス停止エラー ({pid}): {e}")
                    else:
                        logger.info(f"[DRY RUN] 停止予定: PID {pid} - {cmdline[:100]}")
        
        return {
            "duplicates_found": len(duplicates),
            "old_screen_sharing": len(old_screen_sharing),
            "stopped": stopped,
            "protected": protected,
            "dry_run": dry_run
        }
    
    def analyze_and_report(self) -> Dict[str, Any]:
        """分析とレポート"""
        duplicates = self.find_duplicate_processes()
        old_screen = self.find_old_screen_sharing()
        streamlit = self.find_unnecessary_streamlit()
        
        return {
            "duplicate_count": len(duplicates),
            "old_screen_sharing_count": len(old_screen),
            "streamlit_count": len(streamlit),
            "total_cleanup_candidates": len(old_screen) + sum(len(pids)-1 for pids in duplicates.values()),
            "duplicates": {cmd[:100]: pids for cmd, pids in list(duplicates.items())[:10]},
            "streamlit_services": streamlit
        }

def main():
    cleaner = ManaProcessCleaner()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        # 実行モード
        result = cleaner.clean_duplicates(dry_run=False)
        print("\n✅ クリーンアップ完了")
        print(f"停止したプロセス: {len(result['stopped'])}個")
    else:
        # 分析モード（デフォルト）
        report = cleaner.analyze_and_report()
        print("\n📊 プロセス分析レポート")
        print("=" * 60)
        print(f"重複プロセス: {report['duplicate_count']}個")
        print(f"古いscreen_sharing: {report['old_screen_sharing_count']}個")
        print(f"Streamlitサービス: {report['streamlit_count']}個")
        print(f"クリーンアップ候補: {report['total_cleanup_candidates']}個")
        print("\n実行するには: python3 /root/mana_process_cleaner.py clean")

if __name__ == "__main__":
    main()

