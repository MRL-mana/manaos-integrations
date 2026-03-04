#!/usr/bin/env python3
"""
Mana Port Optimizer
ポート最適化・整理システム
"""

import subprocess
import logging
import json
from typing import Dict, List, Any
from collections import Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaPortOptimizer:
    def __init__(self):
        # 重要ポート（絶対に停止しない）
        self.critical_ports = {
            22: "SSH",
            5432: "PostgreSQL",
            6379: "Redis",
            9200: "ManaOS Orchestrator",
            9201: "ManaOS Intention",
            9202: "ManaOS Policy",
            9203: "ManaOS Actuator",
            9204: "ManaOS Ingestor",
            9205: "ManaOS Insight",
            5008: "Screen Sharing",
            8889: "Trinity Secretary",
            9999: "Unified Dashboard"
        }
        
        # 安全に停止可能なポート範囲
        self.safe_to_stop_ports = range(8500, 8600)
        
        logger.info("🔧 Mana Port Optimizer 初期化完了")
    
    def get_listening_ports(self) -> List[Dict[str, Any]]:
        """リスニングポート一覧取得"""
        ports = []
        
        try:
            result = subprocess.run(
                "netstat -tlnp 2>/dev/null | grep LISTEN || ss -tlnp | grep LISTEN",
                shell=True,
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.strip().split('\n'):
                # ポート番号とプロセスを抽出
                import re
                port_match = re.search(r'0\.0\.0\.0:(\d+)|:::(\d+)', line)
                if not port_match:
                    continue
                
                port = int(port_match.group(1) or port_match.group(2))
                
                # プロセス情報
                process_match = re.search(r'(\d+)/(\S+)', line)
                pid = int(process_match.group(1)) if process_match else None
                process = process_match.group(2) if process_match else "unknown"
                
                # 分類
                is_critical = port in self.critical_ports
                is_safe_to_stop = port in self.safe_to_stop_ports
                
                ports.append({
                    "port": port,
                    "pid": pid,
                    "process": process,
                    "is_critical": is_critical,
                    "is_safe_to_stop": is_safe_to_stop,
                    "name": self.critical_ports.get(port, "Unknown")
                })
            
            return ports
            
        except Exception as e:
            logger.error(f"ポート取得エラー: {e}")
            return []
    
    def analyze_ports(self) -> Dict[str, Any]:
        """ポート分析"""
        ports = self.get_listening_ports()
        
        critical_count = len([p for p in ports if p["is_critical"]])
        safe_count = len([p for p in ports if p["is_safe_to_stop"]])
        unknown_count = len([p for p in ports if not p["is_critical"] and not p["is_safe_to_stop"]])
        
        # プロセス別集計
        process_counter = Counter([p["process"] for p in ports])
        
        analysis = {
            "total_ports": len(ports),
            "critical_ports": critical_count,
            "safe_to_stop": safe_count,
            "unknown_ports": unknown_count,
            "by_process": dict(process_counter),
            "ports": ports
        }
        
        logger.info(f"ポート分析: 合計{len(ports)}個, Critical{critical_count}個, 停止可能{safe_count}個")
        
        return analysis
    
    def generate_recommendations(self) -> List[str]:
        """最適化推奨事項"""
        analysis = self.analyze_ports()
        recommendations = []
        
        if analysis["total_ports"] > 50:
            recommendations.append(f"ポート数が{analysis['total_ports']}個と多すぎます。不要なサービスを停止することを推奨します。")
        
        if analysis["safe_to_stop"] > 0:
            recommendations.append(f"{analysis['safe_to_stop']}個の安全に停止可能なポートがあります。")
        
        if analysis["unknown_ports"] > 20:
            recommendations.append(f"{analysis['unknown_ports']}個の不明なポートがあります。各サービスの必要性を確認してください。")
        
        # プロセス別推奨
        for process, count in analysis["by_process"].items():
            if count > 10:
                recommendations.append(f"{process}が{count}個のポートを使用しています。統合を検討してください。")
        
        return recommendations
    
    def export_report(self) -> str:
        """レポート出力"""
        analysis = self.analyze_ports()
        recommendations = self.generate_recommendations()
        
        report = {
            "analysis": analysis,
            "recommendations": recommendations,
            "timestamp": subprocess.run("date", capture_output=True, text=True).stdout.strip()
        }
        
        report_file = "/root/port_optimization_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"レポート保存: {report_file}")
        return report_file

def main():
    optimizer = ManaPortOptimizer()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        analysis = optimizer.analyze_ports()
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "report":
        report_file = optimizer.export_report()
        print(f"レポート: {report_file}")
    else:
        print("ポート最適化分析")
        print("=" * 60)
        analysis = optimizer.analyze_ports()
        print(f"合計ポート: {analysis['total_ports']}")
        print(f"Critical: {analysis['critical_ports']}")
        print(f"停止可能: {analysis['safe_to_stop']}")
        print(f"不明: {analysis['unknown_ports']}")
        print("\n推奨事項:")
        for i, rec in enumerate(optimizer.generate_recommendations(), 1):
            print(f"{i}. {rec}")

if __name__ == "__main__":
    main()

