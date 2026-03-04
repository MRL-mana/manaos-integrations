#!/usr/bin/env python3
"""
Health Checker - ヘルスチェックシステム

システム全体の健全性をチェックします。
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List

workspace = Path("/root/trinity_workspace")


class HealthChecker:
    """ヘルスチェックシステム"""
    
    def __init__(self):
        self.workspace = workspace
        self.checks = []
        
    def check_all(self) -> Dict:
        """全ヘルスチェックを実行"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'overall_status': 'healthy'
        }
        
        # 各チェックを実行
        checks = [
            self._check_databases(),
            self._check_files(),
            self._check_memory(),
            self._check_disk()
        ]
        
        for check in checks:
            results['checks'].append(check)
            if check['status'] != 'pass':
                results['overall_status'] = 'degraded' if results['overall_status'] == 'healthy' else 'unhealthy'
                
        return results
        
    def _check_databases(self) -> Dict:
        """データベースチェック"""
        required_dbs = [
            'cognitive_memory.db',
            'reflection_memory.db',
            'consciousness.db',
            'daily_reflections.db',
            'auto_improvement.db'
        ]
        
        missing = []
        for db_name in required_dbs:
            db_path = self.workspace / "shared" / db_name
            if not db_path.exists():
                missing.append(db_name)
                
        return {
            'name': 'databases',
            'status': 'pass' if not missing else 'fail',
            'message': f"All databases present" if not missing else f"Missing: {', '.join(missing)}"
        }
        
    def _check_files(self) -> Dict:
        """重要ファイルチェック"""
        required_files = [
            'evolution/emotion_system.py',
            'evolution/consciousness_state.py',
            'evolution/daily_reflection.py'
        ]
        
        missing = []
        for file_path in required_files:
            if not (self.workspace / file_path).exists():
                missing.append(file_path)
                
        return {
            'name': 'files',
            'status': 'pass' if not missing else 'fail',
            'message': f"All files present" if not missing else f"Missing: {', '.join(missing)}"
        }
        
    def _check_memory(self) -> Dict:
        """メモリチェック"""
        try:
            import psutil
            memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            if memory < 500:
                status = 'pass'
                message = f"Memory usage: {memory:.0f}MB (healthy)"
            elif memory < 700:
                status = 'warn'
                message = f"Memory usage: {memory:.0f}MB (elevated)"
            else:
                status = 'fail'
                message = f"Memory usage: {memory:.0f}MB (critical)"
                
            return {
                'name': 'memory',
                'status': status,
                'message': message
            }
        except:
            return {
                'name': 'memory',
                'status': 'warn',
                'message': 'Could not check memory'
            }
            
    def _check_disk(self) -> Dict:
        """ディスクチェック"""
        try:
            import psutil
            disk = psutil.disk_usage(str(self.workspace))
            used_percent = disk.percent
            
            if used_percent < 80:
                status = 'pass'
                message = f"Disk usage: {used_percent}% (healthy)"
            elif used_percent < 90:
                status = 'warn'
                message = f"Disk usage: {used_percent}% (elevated)"
            else:
                status = 'fail'
                message = f"Disk usage: {used_percent}% (critical)"
                
            return {
                'name': 'disk',
                'status': status,
                'message': message
            }
        except:
            return {
                'name': 'disk',
                'status': 'warn',
                'message': 'Could not check disk'
            }
            
    def print_report(self, results: Dict):
        """レポートを表示"""
        print("\n" + "="*60)
        print("🏥 Health Check Report")
        print("="*60)
        print(f"Time: {results['timestamp']}")
        print(f"Overall Status: {results['overall_status'].upper()}")
        print()
        
        for check in results['checks']:
            icon = "✅" if check['status'] == 'pass' else "⚠️" if check['status'] == 'warn' else "❌"
            print(f"{icon} {check['name']}: {check['message']}")
            
        print("="*60)


if __name__ == '__main__':
    checker = HealthChecker()
    results = checker.check_all()
    checker.print_report(results)
