#!/usr/bin/env python3
"""
QSR Monitor - Quality Self Reflection測定ツール

Trinity AIエージェントのQSR（Quality Self Reflection）スコアを
リアルタイムで測定・監視するツール。

使用方法:
    python3 qsr_monitor.py                # 全エージェント
    python3 qsr_monitor.py --agent remi   # 特定エージェント
    python3 qsr_monitor.py --watch        # 継続監視モード
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Reflection Engineをインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge"))
from reflection_engine import ReflectionEngine


class QSRMonitor:
    """QSR監視ツール"""
    
    def __init__(self, workspace_path: str = "/root/trinity_workspace"):
        self.workspace = Path(workspace_path)
        self.engine = ReflectionEngine(workspace_path)
        self.agents = ['remi', 'luna', 'mina', 'aria']
        
    def monitor_all(self) -> Dict:
        """全エージェントを監視"""
        results = {}
        
        print("="*60)
        print("QSR Monitor - Trinity AI Reflection Metrics")
        print("="*60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for agent in self.agents:
            qsr = self.engine.calculate_qsr(agent, days=7)
            results[agent] = qsr
            self._print_agent_metrics(agent, qsr)
            
        # 全体サマリー
        overall = self._calculate_overall(results)
        self._print_overall(overall)
        
        return results
        
    def monitor_agent(self, agent: str, days: int = 7) -> Dict:
        """特定エージェントを監視"""
        print("="*60)
        print(f"QSR Monitor - {agent.upper()}")
        print("="*60)
        print(f"Period: Last {days} days")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        qsr = self.engine.calculate_qsr(agent, days)
        self._print_agent_metrics(agent, qsr, detailed=True)
        
        # 改善提案を取得
        improvements = self.engine.generate_improvements(agent, days)
        if improvements:
            print("\n📋 Improvement Suggestions:")
            for i, imp in enumerate(improvements[:5], 1):
                print(f"  {i}. [{imp['priority']}] {imp['suggestion']}")
                
        return qsr
        
    def _print_agent_metrics(self, agent: str, qsr: Dict, detailed: bool = False):
        """エージェントメトリクスを表示"""
        score = qsr['qsr_score']
        confidence = qsr['reflection_confidence']
        delta = qsr['learning_delta']
        
        # スコアに応じた評価
        if score >= 0.9:
            status = "🟢 EXCELLENT"
            color = "\033[92m"  # Green
        elif score >= 0.7:
            status = "🟡 GOOD"
            color = "\033[93m"  # Yellow
        elif score >= 0.5:
            status = "🟠 FAIR"
            color = "\033[91m"  # Red
        else:
            status = "🔴 NEEDS IMPROVEMENT"
            color = "\033[91m"  # Red
            
        reset = "\033[0m"
        
        print(f"┌─ {agent.upper()} {status}")
        print(f"│  QSR Score: {color}{score:.3f}{reset}")
        print(f"│  Reflection Confidence: {confidence:.3f}")
        print(f"│  Learning Delta: {'+' if delta >= 0 else ''}{delta:.2f}%")
        
        if detailed and 'total_actions' in qsr:
            print(f"│  Total Actions: {qsr['total_actions']}")
            if 'success_rate' in qsr:
                print(f"│  Success Rate: {qsr['success_rate']:.1%}")
                
        print("└─")
        print()
        
    def _calculate_overall(self, results: Dict) -> Dict:
        """全体スコアを計算"""
        if not results:
            return {
                'average_qsr': 0.0,
                'average_confidence': 0.0,
                'total_learning_delta': 0.0
            }
            
        scores = [r['qsr_score'] for r in results.values()]
        confidences = [r['reflection_confidence'] for r in results.values()]
        deltas = [r['learning_delta'] for r in results.values()]
        
        return {
            'average_qsr': sum(scores) / len(scores),
            'average_confidence': sum(confidences) / len(confidences),
            'total_learning_delta': sum(deltas) / len(deltas),
            'agent_count': len(results)
        }
        
    def _print_overall(self, overall: Dict):
        """全体サマリーを表示"""
        avg_qsr = overall['average_qsr']
        
        if avg_qsr >= 0.9:
            status = "🎯 TRINITY SYSTEM: EXCELLENT"
        elif avg_qsr >= 0.7:
            status = "✅ TRINITY SYSTEM: GOOD"
        elif avg_qsr >= 0.5:
            status = "⚠️  TRINITY SYSTEM: FAIR"
        else:
            status = "❌ TRINITY SYSTEM: NEEDS ATTENTION"
            
        print("="*60)
        print(status)
        print("="*60)
        print(f"Average QSR Score: {avg_qsr:.3f}")
        print(f"Average Confidence: {overall['average_confidence']:.3f}")
        print(f"Learning Rate: {'+' if overall['total_learning_delta'] >= 0 else ''}{overall['total_learning_delta']:.2f}%")
        print("="*60)
        
    def watch_mode(self, interval: int = 60):
        """継続監視モード"""
        print("🔍 Watch Mode: Monitoring every {} seconds (Ctrl+C to stop)\n".format(interval))
        
        try:
            while True:
                self.monitor_all()
                print(f"\n⏰ Next update in {interval} seconds...\n")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n👋 Monitoring stopped")
            
    def export_report(self, output_file: Optional[str] = None) -> str:
        """レポートをエクスポート"""
        results = {}
        
        for agent in self.agents:
            qsr = self.engine.calculate_qsr(agent, days=7)
            improvements = self.engine.generate_improvements(agent, days=7)
            
            results[agent] = {
                'qsr_metrics': qsr,
                'improvements': improvements
            }
            
        # 全体スコア
        overall = self._calculate_overall({
            agent: data['qsr_metrics'] 
            for agent, data in results.items()
        })
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_metrics': overall,
            'agent_details': results,
            'system_status': self._get_system_status(overall)
        }
        
        # ファイル出力
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"qsr_report_{timestamp}.json"
            
        output_path = self.workspace / "logs" / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"📄 Report exported: {output_path}")
        
        return str(output_path)
        
    def _get_system_status(self, overall: Dict) -> str:
        """システムステータスを取得"""
        avg_qsr = overall['average_qsr']
        
        if avg_qsr >= 0.9:
            return "excellent"
        elif avg_qsr >= 0.7:
            return "good"
        elif avg_qsr >= 0.5:
            return "fair"
        else:
            return "needs_improvement"
            
    def get_trend(self, agent: str, days: int = 30) -> List[Dict]:
        """トレンドデータを取得"""
        import sqlite3
        
        conn = sqlite3.connect(self.engine.db_path)
        cursor = conn.cursor()
        
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT timestamp, qsr_score, reflection_confidence, learning_delta
            FROM qsr_scores
            WHERE agent = ? AND timestamp > ?
            ORDER BY timestamp ASC
        """, (agent, since))
        
        trends = []
        for row in cursor.fetchall():
            trends.append({
                'timestamp': row[0],
                'qsr_score': row[1],
                'reflection_confidence': row[2],
                'learning_delta': row[3]
            })
            
        conn.close()
        return trends
        
    def show_trend(self, agent: str, days: int = 7):
        """トレンドを表示"""
        print(f"\n📈 QSR Trend: {agent.upper()} (Last {days} days)")
        print("="*60)
        
        trends = self.get_trend(agent, days)
        
        if not trends:
            print("No trend data available")
            return
            
        for trend in trends[-10:]:  # 最新10件
            timestamp = datetime.fromisoformat(trend['timestamp'])
            score = trend['qsr_score']
            
            # ASCIIグラフ
            bar_length = int(score * 40)
            bar = "█" * bar_length
            
            print(f"{timestamp.strftime('%m/%d %H:%M')} | {bar} {score:.3f}")
            
        # 変化率
        if len(trends) >= 2:
            first_score = trends[0]['qsr_score']
            last_score = trends[-1]['qsr_score']
            change = ((last_score - first_score) / first_score) * 100
            
            change_str = f"{'+' if change >= 0 else ''}{change:.1f}%"
            print(f"\n📊 Change: {change_str}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='QSR Monitor for Trinity AI')
    parser.add_argument('--agent', choices=['remi', 'luna', 'mina', 'aria'],
                       help='Monitor specific agent')
    parser.add_argument('--days', type=int, default=7,
                       help='Analysis period in days (default: 7)')
    parser.add_argument('--watch', action='store_true',
                       help='Enable watch mode (continuous monitoring)')
    parser.add_argument('--interval', type=int, default=60,
                       help='Watch mode interval in seconds (default: 60)')
    parser.add_argument('--export', action='store_true',
                       help='Export report to JSON file')
    parser.add_argument('--trend', action='store_true',
                       help='Show trend graph')
    
    args = parser.parse_args()
    
    monitor = QSRMonitor()
    
    try:
        if args.watch:
            monitor.watch_mode(args.interval)
        elif args.export:
            monitor.export_report()
        elif args.trend and args.agent:
            monitor.show_trend(args.agent, args.days)
        elif args.agent:
            monitor.monitor_agent(args.agent, args.days)
        else:
            monitor.monitor_all()
            
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1
        
    return 0


if __name__ == '__main__':
    sys.exit(main())



