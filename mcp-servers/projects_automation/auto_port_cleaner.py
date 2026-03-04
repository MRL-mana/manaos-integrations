#!/usr/bin/env python3
"""
自動ポート停止スクリプト
不要なポートを安全に停止
"""

import subprocess
import json
from datetime import datetime

class PortCleaner:
    def __init__(self):
        self.safe_to_stop = [
            # 一時的なポート
            10000, 10001,  # 一時的なWebサービス
            6002, 6060,    # 一時的な開発ポート
            41075, 35113, 32897,  # 一時的なシステムポート
            41872,         # 一時的なネットワークポート
        ]
        
        self.never_stop = [
            # 絶対に停止してはいけないポート
            22,    # SSH
            80, 443,  # HTTP/HTTPS
            53,     # DNS
            631,    # CUPS (プリンター)
        ]
    
    def get_port_processes(self, port: int) -> list:
        """ポートを使用しているプロセス一覧を取得"""
        try:
            result = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                processes = []
                lines = result.stdout.strip().split('\n')[1:]  # ヘッダーをスキップ
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2:
                        processes.append({
                            'pid': parts[1],
                            'process': parts[0],
                            'user': parts[2] if len(parts) > 2 else 'unknown'
                        })
                return processes
        except Exception as e:
            print(f"プロセス取得エラー (ポート{port}): {e}")
        
        return []
    
    def is_safe_to_stop(self, port: int, processes: list) -> bool:
        """ポートを安全に停止できるかチェック"""
        if port in self.never_stop:
            return False
        
        # システムプロセスは停止しない
        for proc in processes:
            if proc['user'] == 'root' and proc['process'] in ['systemd', 'kernel']:
                return False
        
        return True
    
    def stop_port_processes(self, port: int, processes: list) -> bool:
        """ポートのプロセスを停止"""
        stopped = []
        failed = []
        
        for proc in processes:
            try:
                # プロセスを停止
                result = subprocess.run(['kill', '-TERM', proc['pid']], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    stopped.append(proc)
                    print(f"  ✓ 停止: PID {proc['pid']} ({proc['process']})")
                else:
                    failed.append(proc)
                    print(f"  ✗ 停止失敗: PID {proc['pid']} ({proc['process']})")
            except Exception as e:
                failed.append(proc)
                print(f"  ✗ エラー: PID {proc['pid']} - {e}")
        
        return len(failed) == 0
    
    def clean_ports(self, ports_to_clean: list) -> dict:
        """指定されたポートをクリーンアップ"""
        results = {
            'cleaned': [],
            'failed': [],
            'skipped': []
        }
        
        print(f"🧹 ポートクリーンアップ開始 ({len(ports_to_clean)}個)")
        
        for port in ports_to_clean:
            print(f"\n🔍 ポート {port} をチェック...")
            
            # プロセス取得
            processes = self.get_port_processes(port)
            
            if not processes:
                print("  ℹ️ プロセスなし - スキップ")
                results['skipped'].append(port)
                continue
            
            # 安全性チェック
            if not self.is_safe_to_stop(port, processes):
                print("  ⚠️ 安全でない - スキップ")
                results['skipped'].append(port)
                continue
            
            # 停止実行
            print("  🛑 停止実行...")
            if self.stop_port_processes(port, processes):
                results['cleaned'].append(port)
                print(f"  ✅ ポート {port} クリーンアップ完了")
            else:
                results['failed'].append(port)
                print(f"  ❌ ポート {port} クリーンアップ失敗")
        
        return results
    
    def create_cleanup_report(self, results: dict):
        """クリーンアップレポートを生成"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_processed': len(results['cleaned']) + len(results['failed']) + len(results['skipped']),
                'cleaned': len(results['cleaned']),
                'failed': len(results['failed']),
                'skipped': len(results['skipped'])
            },
            'details': results
        }
        
        with open('/root/port_cleanup_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print("\n📊 クリーンアップ結果:")
        print(f"  ✅ 成功: {len(results['cleaned'])}個")
        print(f"  ❌ 失敗: {len(results['failed'])}個")
        print(f"  ⏭️ スキップ: {len(results['skipped'])}個")
        print("📝 レポート: /root/port_cleanup_report.json")

def main():
    cleaner = PortCleaner()
    
    # 停止推奨ポートを読み込み
    try:
        with open('/root/port_forwarding_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 停止推奨ポートを抽出（実際の設定から）
        ports_to_clean = [53, 45303, 10000, 10001, 34641, 37010, 39131, 631, 6002, 6060, 41075, 35113, 41872, 32897]
        
        print("🚀 自動ポートクリーンアップ開始")
        print(f"📋 対象ポート: {len(ports_to_clean)}個")
        
        # 確認
        response = input("続行しますか？ (y/N): ")
        if response.lower() != 'y':
            print("❌ キャンセルされました")
            return
        
        # クリーンアップ実行
        results = cleaner.clean_ports(ports_to_clean)
        cleaner.create_cleanup_report(results)
        
    except FileNotFoundError:
        print("❌ 設定ファイルが見つかりません: /root/port_forwarding_config.json")
        print("先に python3 /root/auto_port_optimizer.py を実行してください")
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
