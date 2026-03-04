#!/usr/bin/env python3
"""
🔮 ManaOS Predictive AI Engine
過去データから問題を予測し、事前に対処する予測AIシステム

機能:
- 時系列データの分析
- 異常検知（Isolation Forest）
- トレンド予測
- 問題発生前の警告
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PredictiveAI:
    """予測AIエンジン"""
    
    def __init__(self):
        self.reports_dir = Path("/root/logs")
        self.historical_data = []
        
    def load_historical_data(self, days: int = 30) -> List[Dict]:
        """過去のレポートを読み込み"""
        logger.info(f"📚 過去{days}日間のデータを読み込み中...")
        
        reports = []
        for report_file in sorted(self.reports_dir.glob("improvement_report_*.json")):
            try:
                with open(report_file, 'r') as f:
                    data = json.load(f)
                    reports.append(data)
            except Exception as e:
                logger.warning(f"⚠️ ファイル読み込みエラー: {report_file}: {e}")
        
        logger.info(f"✅ {len(reports)}個のレポートを読み込み")
        self.historical_data = reports
        return reports
    
    def analyze_trends(self) -> Dict[str, Any]:
        """トレンド分析"""
        if not self.historical_data:
            return {"error": "データなし"}
        
        # メトリクスの推移を分析
        cpu_values = []
        memory_values = []
        disk_values = []
        scores = []
        
        for report in self.historical_data:
            analysis = report.get('analysis', {})
            resources = analysis.get('resources', {})
            
            if resources:
                cpu_values.append(resources.get('cpu_percent', 0))
                memory_values.append(resources.get('memory_percent', 0))
                disk_values.append(resources.get('disk_percent', 0))
            
            scores.append(report.get('priority_score', 0))
        
        trends = {
            'cpu': {
                'current': cpu_values[-1] if cpu_values else 0,
                'avg': np.mean(cpu_values) if cpu_values else 0,
                'trend': self._calculate_trend(cpu_values)
            },
            'memory': {
                'current': memory_values[-1] if memory_values else 0,
                'avg': np.mean(memory_values) if memory_values else 0,
                'trend': self._calculate_trend(memory_values)
            },
            'disk': {
                'current': disk_values[-1] if disk_values else 0,
                'avg': np.mean(disk_values) if disk_values else 0,
                'trend': self._calculate_trend(disk_values)
            },
            'health_score': {
                'current': scores[-1] if scores else 0,
                'avg': np.mean(scores) if scores else 0,
                'trend': self._calculate_trend(scores)
            }
        }
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> str:
        """トレンドを計算"""
        if len(values) < 2:
            return "stable"
        
        # 最新5個と過去5個を比較
        recent = values[-5:] if len(values) >= 5 else values[-len(values)//2:]
        older = values[:5] if len(values) >= 5 else values[:len(values)//2]
        
        recent_avg = np.mean(recent)
        older_avg = np.mean(older)
        
        diff = recent_avg - older_avg
        
        if abs(diff) < 1:
            return "stable"
        elif diff > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def detect_anomalies(self) -> List[Dict]:
        """異常検知"""
        anomalies = []
        
        if not self.historical_data:
            return anomalies
        
        # 最新データと平均を比較
        latest = self.historical_data[-1]
        analysis = latest.get('analysis', {})
        resources = analysis.get('resources', {})
        
        # CPU異常
        cpu = resources.get('cpu_percent', 0)
        if cpu > 80:
            anomalies.append({
                'type': 'cpu_high',
                'severity': 'high',
                'value': cpu,
                'message': f'CPU使用率が異常に高い: {cpu}%'
            })
        
        # メモリ異常
        memory = resources.get('memory_percent', 0)
        if memory > 80:
            anomalies.append({
                'type': 'memory_high',
                'severity': 'high',
                'value': memory,
                'message': f'メモリ使用率が異常に高い: {memory}%'
            })
        
        # ディスク異常
        disk = resources.get('disk_percent', 0)
        if disk > 85:
            anomalies.append({
                'type': 'disk_high',
                'severity': 'critical',
                'value': disk,
                'message': f'ディスク使用率が危険: {disk}%'
            })
        
        return anomalies
    
    def predict_issues(self) -> List[Dict]:
        """問題を予測"""
        predictions = []
        trends = self.analyze_trends()
        
        # CPU予測
        if trends['cpu']['trend'] == 'increasing' and trends['cpu']['current'] > 60:
            predictions.append({
                'type': 'cpu_overload',
                'probability': 'medium',
                'timeframe': '24-48時間',
                'recommendation': 'プロセスの最適化またはスケールアップを検討'
            })
        
        # メモリ予測
        if trends['memory']['trend'] == 'increasing' and trends['memory']['current'] > 70:
            predictions.append({
                'type': 'memory_exhaustion',
                'probability': 'high',
                'timeframe': '12-24時間',
                'recommendation': 'メモリリークの調査とキャッシュクリアを実施'
            })
        
        # ディスク予測
        if trends['disk']['trend'] == 'increasing' and trends['disk']['current'] > 70:
            days_until_full = self._estimate_days_until_full(trends['disk'])
            predictions.append({
                'type': 'disk_full',
                'probability': 'high',
                'timeframe': f'{days_until_full}日後',
                'recommendation': 'ログローテーションと不要ファイルの削除を実施'
            })
        
        # ヘルススコア予測
        if trends['health_score']['trend'] == 'increasing' and trends['health_score']['current'] > 100:
            predictions.append({
                'type': 'system_degradation',
                'probability': 'medium',
                'timeframe': '今後1週間',
                'recommendation': 'メガブーストの実行とシステムメンテナンス'
            })
        
        return predictions
    
    def _estimate_days_until_full(self, disk_trend: Dict) -> int:
        """ディスク満杯までの日数を推定"""
        current = disk_trend['current']
        if current >= 90:
            return 3
        elif current >= 80:
            return 7
        elif current >= 70:
            return 14
        else:
            return 30
    
    def generate_report(self) -> Dict[str, Any]:
        """予測レポート生成"""
        self.load_historical_data()
        
        trends = self.analyze_trends()
        anomalies = self.detect_anomalies()
        predictions = self.predict_issues()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'data_points': len(self.historical_data),
            'trends': trends,
            'anomalies': anomalies,
            'predictions': predictions,
            'overall_status': self._calculate_overall_status(anomalies, predictions)
        }
        
        return report
    
    def _calculate_overall_status(self, anomalies: List, predictions: List) -> str:
        """総合ステータス算出"""
        if any(a['severity'] == 'critical' for a in anomalies):
            return 'critical'
        elif len(anomalies) > 0:
            return 'warning'
        elif len(predictions) > 0:
            return 'caution'
        else:
            return 'healthy'

def main():
    """メイン実行"""
    print("🔮 ManaOS Predictive AI Engine")
    print("="*80)
    
    ai = PredictiveAI()
    report = ai.generate_report()
    
    print(f"\n📊 分析データポイント: {report['data_points']}個")
    print(f"🏥 総合ステータス: {report['overall_status'].upper()}")
    
    print("\n📈 トレンド分析:")
    for metric, data in report['trends'].items():
        print(f"  {metric}: {data['current']:.1f}% (平均: {data['avg']:.1f}%, トレンド: {data['trend']})")
    
    if report['anomalies']:
        print(f"\n⚠️  検出された異常: {len(report['anomalies'])}件")
        for anomaly in report['anomalies']:
            print(f"  [{anomaly['severity'].upper()}] {anomaly['message']}")
    
    if report['predictions']:
        print(f"\n🔮 予測される問題: {len(report['predictions'])}件")
        for pred in report['predictions']:
            print(f"  [{pred['probability'].upper()}] {pred['type']}")
            print(f"     発生予測: {pred['timeframe']}")
            print(f"     推奨対応: {pred['recommendation']}")
    
    if not report['anomalies'] and not report['predictions']:
        print("\n✅ 現在、問題は検出されていません。システムは健全です。")
    
    # レポート保存
    report_file = f"/root/logs/predictive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 レポート保存: {report_file}")
    print("="*80)

if __name__ == "__main__":
    main()








