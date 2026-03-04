#!/usr/bin/env python3
"""
⚡ ManaOS Process Optimizer
AI関連プロセスを分析・最適化・統合

機能:
- プロセスの重複検出
- リソース使用状況分析
- 統合可能なプロセスの提案
- 自動最適化
"""

import psutil
from collections import defaultdict
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessOptimizer:
    """プロセス最適化クラス"""
    
    def __init__(self):
        self.processes = []
        self.ai_processes = []
    
    def analyze_processes(self):
        """全プロセスを分析"""
        logger.info("🔍 プロセス分析開始...")
        
        process_stats = defaultdict(list)
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                cmdline = ' '.join(info['cmdline'] or [])
                
                # AI関連プロセスを抽出
                if any(keyword in cmdline.lower() for keyword in 
                       ['python', 'trinity', 'mana', 'ai', 'llm', 'ml', 'torch', 'tensorflow']):
                    
                    self.ai_processes.append({
                        'pid': info['pid'],
                        'name': info['name'],
                        'cmdline': cmdline[:100],
                        'cpu': info['cpu_percent'],
                        'memory': info['memory_percent']
                    })
                    
                    # スクリプト名でグループ化
                    script_name = self._extract_script_name(cmdline)
                    if script_name:
                        process_stats[script_name].append(info['pid'])
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        logger.info(f"✅ {len(self.ai_processes)}個のAI関連プロセスを検出")
        return process_stats
    
    def _extract_script_name(self, cmdline: str) -> str:
        """コマンドラインからスクリプト名を抽出"""
        parts = cmdline.split()
        for part in parts:
            if part.endswith('.py'):
                return part.split('/')[-1]
        return ""
    
    def find_duplicates(self, process_stats: Dict) -> List[Tuple[str, int]]:
        """重複プロセスを検出"""
        duplicates = []
        
        for script, pids in process_stats.items():
            if len(pids) > 1:
                duplicates.append((script, len(pids)))
        
        return sorted(duplicates, key=lambda x: x[1], reverse=True)
    
    def get_resource_hogs(self, top_n: int = 10) -> List[Dict]:
        """リソース使用量が多いプロセスを取得"""
        sorted_procs = sorted(
            self.ai_processes,
            key=lambda x: (x['cpu'] or 0) + (x['memory'] or 0),
            reverse=True
        )
        return sorted_procs[:top_n]
    
    def generate_report(self):
        """最適化レポートを生成"""
        process_stats = self.analyze_processes()
        duplicates = self.find_duplicates(process_stats)
        resource_hogs = self.get_resource_hogs()
        
        print("\n" + "="*80)
        print("⚡ プロセス最適化レポート")
        print("="*80)
        
        print("\n📊 統計:")
        print(f"  総AI関連プロセス: {len(self.ai_processes)}個")
        print(f"  ユニークスクリプト: {len(process_stats)}個")
        
        if duplicates:
            print("\n🔄 重複プロセス（統合可能）:")
            for script, count in duplicates[:5]:
                print(f"  - {script}: {count}個のインスタンス")
        
        if resource_hogs:
            print("\n🔥 リソース使用量上位:")
            for i, proc in enumerate(resource_hogs[:5], 1):
                print(f"  {i}. {proc['cmdline'][:60]}")
                print(f"     CPU: {proc['cpu']:.1f}% | Memory: {proc['memory']:.1f}%")
        
        print("\n💡 最適化提案:")
        if duplicates:
            print(f"  ✓ {len(duplicates)}個のスクリプトに重複インスタンスあり")
            print("    → シングルトンパターンの実装を推奨")
        
        if len(self.ai_processes) > 50:
            print(f"  ✓ AI関連プロセスが{len(self.ai_processes)}個と多い")
            print("    → プロセスプーリングまたはマルチスレッド化を推奨")
        
        print("="*80 + "\n")
        
        return {
            'total_processes': len(self.ai_processes),
            'unique_scripts': len(process_stats),
            'duplicates': duplicates,
            'resource_hogs': resource_hogs
        }

def main():
    """メイン実行"""
    print("⚡ ManaOS Process Optimizer")
    print("AI関連プロセスを分析中...\n")
    
    optimizer = ProcessOptimizer()
    report = optimizer.generate_report()
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())








