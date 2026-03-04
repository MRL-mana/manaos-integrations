#!/usr/bin/env python3
"""
Mana Service Consolidator
サービス統合・ポート削減システム
93個のpython3プロセスを統合して最適化
"""

import psutil
import logging
from typing import Dict, List, Any
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaServiceConsolidator:
    def __init__(self):
        # 統合対象外（重要サービス）
        self.critical_services = [
            "manaos_v3",
            "trinity",
            "screen_sharing_enhanced",
            "trinity_secretary_enhanced",
            "unified_dashboard",
            "auto_optimizer",
            "voice_assistant"
        ]
        
        logger.info("🔧 Mana Service Consolidator 初期化")
    
    def analyze_python_processes(self) -> Dict[str, List]:
        """Python3プロセス分析"""
        processes = defaultdict(list)
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['name'] == 'python3':
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # Streamlitプロセス検出
                    if 'streamlit run' in cmdline:
                        key = 'streamlit_services'
                        processes[key].append({
                            "pid": proc.info['pid'],
                            "cmdline": cmdline,
                            "cpu": proc.info['cpu_percent'],
                            "memory": proc.info['memory_percent']
                        })
                    
                    # manaos_unified_systemサービス
                    elif '/manaos_unified_system/services/' in cmdline:
                        key = 'unified_system_services'
                        processes[key].append({
                            "pid": proc.info['pid'],
                            "cmdline": cmdline,
                            "cpu": proc.info['cpu_percent'],
                            "memory": proc.info['memory_percent']
                        })
                    
                    # その他
                    else:
                        key = 'other_python'
                        processes[key].append({
                            "pid": proc.info['pid'],
                            "cmdline": cmdline[:100],
                            "cpu": proc.info['cpu_percent'],
                            "memory": proc.info['memory_percent']
                        })
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return dict(processes)
    
    def get_consolidation_plan(self) -> Dict[str, Any]:
        """統合計画取得"""
        processes = self.analyze_python_processes()
        
        plan = {
            "streamlit_services": {
                "count": len(processes.get("streamlit_services", [])),
                "action": "統合可能（1つのStreamlitアプリに統合）",
                "potential_reduction": len(processes.get("streamlit_services", [])) - 1
            },
            "unified_system_services": {
                "count": len(processes.get("unified_system_services", [])),
                "action": "統合可能（APIゲートウェイ経由）",
                "potential_reduction": len(processes.get("unified_system_services", [])) - 5
            },
            "total_python_processes": sum(len(v) for v in processes.values()),
            "potential_total_reduction": 0
        }
        
        plan["potential_total_reduction"] = (
            plan["streamlit_services"]["potential_reduction"] +
            plan["unified_system_services"]["potential_reduction"]
        )
        
        return plan
    
    def find_duplicate_services(self) -> List[Dict[str, Any]]:
        """重複サービス検出"""
        processes = self.analyze_python_processes()
        duplicates = []
        
        # Streamlitサービスをチェック
        streamlit_services = processes.get("streamlit_services", [])
        service_names = {}
        
        for proc in streamlit_services:
            # サービス名を抽出
            import re
            match = re.search(r'streamlit run\s+(.+?)\.py', proc['cmdline'])
            if match:
                service_name = match.group(1).split('/')[-1]
                if service_name not in service_names:
                    service_names[service_name] = []
                service_names[service_name].append(proc['pid'])
        
        # 重複検出
        for name, pids in service_names.items():
            if len(pids) > 1:
                duplicates.append({
                    "service": name,
                    "duplicate_count": len(pids),
                    "pids": pids
                })
        
        return duplicates

def main():
    consolidator = ManaServiceConsolidator()
    
    print("\n" + "=" * 60)
    print("🔧 サービス統合分析")
    print("=" * 60)
    
    processes = consolidator.analyze_python_processes()
    print("\nPython3プロセス分類:")
    for key, procs in processes.items():
        print(f"  {key}: {len(procs)}個")
    
    print("\n統合計画:")
    plan = consolidator.get_consolidation_plan()
    print(f"  Streamlitサービス: {plan['streamlit_services']['count']}個 → {plan['streamlit_services']['potential_reduction']}個削減可能")
    print(f"  統合システムサービス: {plan['unified_system_services']['count']}個 → {plan['unified_system_services']['potential_reduction']}個削減可能")
    print(f"  合計削減可能: {plan['potential_total_reduction']}個")
    
    duplicates = consolidator.find_duplicate_services()
    if duplicates:
        print("\n重複サービス検出:")
        for dup in duplicates:
            print(f"  {dup['service']}: {dup['duplicate_count']}個の重複")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

