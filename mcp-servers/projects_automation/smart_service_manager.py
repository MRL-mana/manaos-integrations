#!/usr/bin/env python3
"""
スマートサービスマネージャー
サービスの自動検出・重複チェック・統合提案
"""

import subprocess
import json
from datetime import datetime
from collections import defaultdict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/smart_service_manager.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('SmartServiceManager')

class SmartServiceManager:
    """スマートサービス管理"""
    
    def __init__(self):
        self.categories = {
            'monitoring': ['monitor', 'health', 'check', 'watch'],
            'dashboard': ['dashboard', 'portal', 'viewer', 'ui'],
            'gpu': ['gpu', 'runpod', 'cuda'],
            'trinity': ['trinity', 'secretary'],
            'mcp': ['mcp_server'],
            'backup': ['backup', 'archive'],
            'automation': ['auto_', 'scheduler', 'cron']
        }
    
    def get_running_processes(self):
        """実行中のPythonプロセスを取得"""
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        
        processes = []
        for line in result.stdout.split('\n'):
            if 'python' in line and 'grep' not in line:
                parts = line.split()
                if len(parts) > 10:
                    pid = parts[1]
                    cmd = ' '.join(parts[10:])
                    # .pyファイルを抽出
                    for part in parts:
                        if '.py' in part:
                            processes.append({
                                'pid': pid,
                                'script': part.split('/')[-1],
                                'full_path': part if '/' in part else None,
                                'cmd': cmd
                            })
                            break
        
        return processes
    
    def categorize_processes(self, processes):
        """プロセスをカテゴリ分け"""
        categorized = defaultdict(list)
        
        for proc in processes:
            script = proc['script'].lower()
            matched = False
            
            for category, keywords in self.categories.items():
                if any(keyword in script for keyword in keywords):
                    categorized[category].append(proc)
                    matched = True
                    break
            
            if not matched:
                categorized['other'].append(proc)
        
        return categorized
    
    def find_duplicates(self, categorized):
        """重複・統合可能なサービスを検出"""
        duplicates = {}
        
        for category, procs in categorized.items():
            if len(procs) > 3:  # 3個以上で統合推奨
                duplicates[category] = {
                    'count': len(procs),
                    'processes': procs,
                    'consolidation_potential': len(procs) - 1  # 1個に統合した場合の削減数
                }
        
        return duplicates
    
    def generate_report(self):
        """統合レポート生成"""
        logger.info("🔍 サービス分析開始")
        
        processes = self.get_running_processes()
        total_python_processes = len(processes)
        
        categorized = self.categorize_processes(processes)
        duplicates = self.find_duplicates(categorized)
        
        # レポート作成
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_processes': total_python_processes,
            'categories': {k: len(v) for k, v in categorized.items()},
            'duplicates': {k: v['count'] for k, v in duplicates.items()},
            'consolidation_potential': sum(v['consolidation_potential'] for v in duplicates.values())
        }
        
        # コンソール出力
        print(f"\n{'='*60}")
        print("📊 スマートサービス分析レポート")
        print(f"{'='*60}\n")
        
        print(f"総Pythonプロセス数: {total_python_processes}個\n")
        
        print("カテゴリ別:")
        for category, count in sorted(report['categories'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {category:15}: {count:3}個")
        
        print(f"\n{'='*60}")
        print("🎯 統合推奨（3個以上のカテゴリ）")
        print(f"{'='*60}\n")
        
        if duplicates:
            for category, data in sorted(duplicates.items(), key=lambda x: x[1]['count'], reverse=True):
                print(f"📦 {category}:")
                print(f"   現在: {data['count']}個")
                print("   統合後: 1個")
                print(f"   削減: -{data['consolidation_potential']}個\n")
                
                # 具体的なスクリプト名を表示
                print("   スクリプト:")
                for proc in data['processes'][:5]:  # 最初の5個
                    print(f"     • {proc['script']}")
                if len(data['processes']) > 5:
                    print(f"     ... 他{len(data['processes']) - 5}個")
                print()
        else:
            print("✅ 統合推奨なし（すべて最適化済み）\n")
        
        print(f"{'='*60}")
        print("💡 統合可能性")
        print(f"{'='*60}\n")
        print(f"統合により削減可能: {report['consolidation_potential']}プロセス")
        print(f"統合後の予想数: {total_python_processes - report['consolidation_potential']}個\n")
        
        # JSONファイルに保存
        report_file = f"/root/logs/service_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 レポート保存: {report_file}")
        
        return report
    
    def auto_consolidate(self, category):
        """指定カテゴリの自動統合（プラン生成）"""
        processes = self.get_running_processes()
        categorized = self.categorize_processes(processes)
        
        if category not in categorized:
            logger.warning(f"⚠️ カテゴリ {category} が見つかりません")
            return None
        
        procs = categorized[category]
        
        consolidation_plan = {
            'category': category,
            'target_count': len(procs),
            'consolidated_name': f'unified_{category}_service.py',
            'processes_to_stop': [p['script'] for p in procs],
            'estimated_reduction': len(procs) - 1
        }
        
        logger.info(f"📋 {category} 統合プラン作成完了")
        
        return consolidation_plan

if __name__ == "__main__":
    import sys
    
    manager = SmartServiceManager()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--analyze':
            manager.generate_report()
        elif sys.argv[1] == '--consolidate':
            if len(sys.argv) > 2:
                plan = manager.auto_consolidate(sys.argv[2])
                print(json.dumps(plan, indent=2, ensure_ascii=False))
            else:
                print("使用方法: --consolidate <category>")
        else:
            print("使用方法:")
            print("  --analyze            全サービスを分析")
            print("  --consolidate <cat>  指定カテゴリの統合プラン生成")
    else:
        # デフォルト: 分析実行
        manager.generate_report()


