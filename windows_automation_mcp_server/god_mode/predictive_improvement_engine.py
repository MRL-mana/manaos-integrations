#!/usr/bin/env python3
"""
予測的改善エンジン - 問題が起きる前に対策
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class Prediction:
    """予測"""
    prediction_id: str
    timestamp: float
    category: str
    risk_level: float  # 0-1
    confidence: float  # 0-1
    title: str
    description: str
    recommended_actions: List[str]
    deadline: Optional[float]

class PredictiveImprovementEngine:
    """予測的改善エンジン"""
    
    def __init__(self):
        self.data_dir = Path("/root/god_mode/predictions")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.predictions_file = self.data_dir / "predictions.jsonl"
        self.history_file = self.data_dir / "history.jsonl"
    
    def analyze_trends(self) -> List[Prediction]:
        """トレンド分析＆予測生成"""
        predictions = []
        
        # 1. システムリソーストレンド
        resource_prediction = self._predict_resource_issues()
        if resource_prediction:
            predictions.append(resource_prediction)
        
        # 2. エラーパターントレンド
        error_prediction = self._predict_error_surge()
        if error_prediction:
            predictions.append(error_prediction)
        
        # 3. パフォーマンストレンド
        performance_prediction = self._predict_performance_degradation()
        if performance_prediction:
            predictions.append(performance_prediction)
        
        # 4. メンテナンス必要性
        maintenance_prediction = self._predict_maintenance_needs()
        if maintenance_prediction:
            predictions.append(maintenance_prediction)
        
        # 保存
        for pred in predictions:
            self._save_prediction(pred)
        
        return predictions
    
    def _predict_resource_issues(self) -> Optional[Prediction]:
        """リソース問題予測"""
        try:
            from god_mode.lightweight_monitor import get_monitor
            monitor = get_monitor()
            
            # 過去のメトリクス取得
            metrics_file = Path("/root/god_mode/monitoring/metrics.jsonl")
            if not metrics_file.exists():
                return None
            
            recent_metrics = []
            cutoff = time.time() - (3600 * 24)  # 24時間
            
            with open(metrics_file, 'r') as f:
                for line in f:
                    try:
                        metric = json.loads(line)
                        if metric.get('timestamp', 0) >= cutoff:
                            recent_metrics.append(metric)
                    except IOError:
                        continue
            
            if len(recent_metrics) < 10:
                return None
            
            # トレンド分析
            disk_trend = [m['disk_percent'] for m in recent_metrics[-10:]]
            avg_disk = sum(disk_trend) / len(disk_trend)
            
            if avg_disk > 75:
                # ディスク使用量が増加傾向
                days_until_full = self._estimate_days_until_full(disk_trend)
                
                risk = min(1.0, (avg_disk - 75) / 20)
                
                return Prediction(
                    prediction_id=hashlib.md5(f"disk_{time.time()}".encode()).hexdigest()[:12],
                    timestamp=time.time(),
                    category="resource",
                    risk_level=risk,
                    confidence=0.75,
                    title="ディスク容量不足の可能性",
                    description=f"現在のディスク使用率は{avg_disk:.1f}%で増加傾向です。約{days_until_full}日で満杯になる可能性があります。",
                    recommended_actions=[
                        "古いログファイルを削除",
                        "不要なバックアップを整理",
                        "バックアップをGoogle Driveに移動",
                        "ディスククリーンアップ実行"
                    ],
                    deadline=time.time() + (days_until_full * 86400)
                )
        
        except Exception as e:
            print(f"リソース予測エラー: {e}")
        
        return None
    
    def _predict_error_surge(self) -> Optional[Prediction]:
        """エラー急増予測"""
        try:
            # Level 3のエラーログをチェック
            log_files = [
                "/root/logs/agi_evolution.log",
                "/root/logs/auto_bug_fix.log"
            ]
            
            error_count = 0
            recent_errors = []
            
            for log_file in log_files:
                log_path = Path(log_file)
                if not log_path.exists():
                    continue
                
                # 最新100行をチェック
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-100:]:
                        if 'ERROR' in line or 'Exception' in line:
                            error_count += 1
                            recent_errors.append(line.strip())
            
            if error_count > 5:
                # エラーが多い
                return Prediction(
                    prediction_id=hashlib.md5(f"errors_{time.time()}".encode()).hexdigest()[:12],
                    timestamp=time.time(),
                    category="stability",
                    risk_level=min(1.0, error_count / 20),
                    confidence=0.70,
                    title="エラー発生率が上昇中",
                    description=f"過去のログで{error_count}件のエラーを検出しました。システムの安定性に影響する可能性があります。",
                    recommended_actions=[
                        "エラーログを詳細分析",
                        "自動バグ修正システムの確認",
                        "Level 3設定の見直し",
                        "システム再起動の検討"
                    ],
                    deadline=time.time() + (86400 * 1)  # 1日以内
                )
        
        except Exception as e:
            print(f"エラー予測エラー: {e}")
        
        return None
    
    def _predict_performance_degradation(self) -> Optional[Prediction]:
        """パフォーマンス劣化予測"""
        try:
            # 思考ログから実行時間トレンドをチェック
            from god_mode.thinking_audit_system import get_audit_system
            audit = get_audit_system()
            
            sessions_file = Path("/root/god_mode/thinking_logs/sessions.jsonl")
            if not sessions_file.exists():
                return None
            
            recent_durations = []
            cutoff = time.time() - (3600 * 24 * 7)  # 7日間
            
            with open(sessions_file, 'r') as f:
                for line in f:
                    try:
                        session = json.loads(line)
                        if session.get('start_time', 0) >= cutoff:
                            duration = session.get('end_time', 0) - session.get('start_time', 0)
                            if duration > 0:
                                recent_durations.append(duration)
                    except IOError:
                        continue
            
            if len(recent_durations) >= 10:
                # 最近の平均と初期の平均を比較
                recent_avg = sum(recent_durations[-5:]) / 5
                initial_avg = sum(recent_durations[:5]) / 5
                
                if recent_avg > initial_avg * 1.5:
                    # 実行時間が50%以上増加
                    degradation = (recent_avg - initial_avg) / initial_avg
                    
                    return Prediction(
                        prediction_id=hashlib.md5(f"perf_{time.time()}".encode()).hexdigest()[:12],
                        timestamp=time.time(),
                        category="performance",
                        risk_level=min(1.0, degradation),
                        confidence=0.65,
                        title="パフォーマンス劣化の兆候",
                        description=f"タスク実行時間が{degradation*100:.1f}%増加しています。システムの最適化が必要な可能性があります。",
                        recommended_actions=[
                            "キャッシュクリア",
                            "データベース最適化",
                            "不要なプロセス停止",
                            "メモリリーク確認"
                        ],
                        deadline=time.time() + (86400 * 3)  # 3日以内
                    )
        
        except Exception as e:
            print(f"パフォーマンス予測エラー: {e}")
        
        return None
    
    def _predict_maintenance_needs(self) -> Optional[Prediction]:
        """メンテナンス必要性予測"""
        try:
            # バックアップの古さをチェック
            backup_dir = Path("/root/backups/level3")
            if not backup_dir.exists():
                return None
            
            backups = list(backup_dir.glob("*.tar.gz"))
            if not backups:
                return Prediction(
                    prediction_id=hashlib.md5(f"maint_{time.time()}".encode()).hexdigest()[:12],
                    timestamp=time.time(),
                    category="maintenance",
                    risk_level=0.8,
                    confidence=1.0,
                    title="バックアップが存在しません",
                    description="Level 3のバックアップが見つかりません。定期バックアップの設定が必要です。",
                    recommended_actions=[
                        "バックアップスクリプト実行",
                        "cron設定確認",
                        "手動バックアップ実施"
                    ],
                    deadline=time.time() + (3600 * 24)  # 24時間以内
                )
            
            # 最新バックアップの日時
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
            age_days = (time.time() - latest_backup.stat().st_mtime) / 86400
            
            if age_days > 3:
                return Prediction(
                    prediction_id=hashlib.md5(f"backup_{time.time()}".encode()).hexdigest()[:12],
                    timestamp=time.time(),
                    category="maintenance",
                    risk_level=min(1.0, age_days / 7),
                    confidence=1.0,
                    title="バックアップが古い",
                    description=f"最新のバックアップは{age_days:.1f}日前です。定期的なバックアップを推奨します。",
                    recommended_actions=[
                        "手動バックアップ実行",
                        "cron設定確認",
                        "バックアップ自動化確認"
                    ],
                    deadline=time.time() + (86400 * 1)  # 1日以内
                )
        
        except Exception as e:
            print(f"メンテナンス予測エラー: {e}")
        
        return None
    
    def _estimate_days_until_full(self, disk_trend: List[float]) -> int:
        """ディスクが満杯になるまでの日数推定"""
        if len(disk_trend) < 2:
            return 999
        
        # 線形回帰（簡易版）
        avg_increase_per_record = (disk_trend[-1] - disk_trend[0]) / len(disk_trend)
        
        if avg_increase_per_record <= 0:
            return 999
        
        remaining = 100 - disk_trend[-1]
        records_until_full = remaining / avg_increase_per_record
        
        # 1レコード = 1時間と仮定（監視間隔による）
        hours_until_full = records_until_full
        days_until_full = max(1, int(hours_until_full / 24))
        
        return days_until_full
    
    def _save_prediction(self, prediction: Prediction):
        """予測保存"""
        with open(self.predictions_file, 'a') as f:
            f.write(json.dumps(asdict(prediction), ensure_ascii=False) + '\n')
    
    def get_active_predictions(self) -> List[Dict]:
        """アクティブな予測取得"""
        if not self.predictions_file.exists():
            return []
        
        now = time.time()
        active = []
        
        with open(self.predictions_file, 'r') as f:
            for line in f:
                try:
                    pred = json.loads(line)
                    deadline = pred.get('deadline')
                    
                    # 期限内のもの
                    if deadline and deadline > now:
                        active.append(pred)
                except IOError:
                    continue
        
        # リスクレベル順にソート
        active.sort(key=lambda x: x.get('risk_level', 0), reverse=True)
        
        return active
    
    def generate_report(self) -> str:
        """レポート生成"""
        predictions = self.get_active_predictions()
        
        if not predictions:
            return "✅ 予測される問題はありません"
        
        report = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += "🔮 予測的改善レポート\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, pred in enumerate(predictions, 1):
            risk = pred['risk_level']
            risk_emoji = "🔥" if risk >= 0.7 else "⚠️" if risk >= 0.4 else "💡"
            
            deadline = pred.get('deadline')
            if deadline:
                hours_left = (deadline - time.time()) / 3600
                deadline_str = f"{hours_left:.1f}時間以内" if hours_left < 48 else f"{hours_left/24:.1f}日以内"
            else:
                deadline_str = "期限なし"
            
            report += f"{i}. {risk_emoji} {pred['title']}\n"
            report += f"   カテゴリ: {pred['category']}\n"
            report += f"   リスク: {risk*100:.0f}% | 信頼度: {pred['confidence']*100:.0f}%\n"
            report += f"   期限: {deadline_str}\n"
            report += f"   {pred['description']}\n\n"
            report += "   推奨アクション:\n"
            for action in pred['recommended_actions']:
                report += f"     • {action}\n"
            report += "\n"
        
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return report

# グローバルインスタンス
_engine = None

def get_predictive_engine() -> PredictiveImprovementEngine:
    """グローバルエンジン取得"""
    global _engine
    if _engine is None:
        _engine = PredictiveImprovementEngine()
    return _engine

# テスト実行
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔮 予測的改善エンジン - デモ実行")
    print("=" * 70)
    
    engine = PredictiveImprovementEngine()
    
    print("\n[予測分析実行中...]")
    predictions = engine.analyze_trends()
    
    if predictions:
        print(f"  ✅ {len(predictions)}件の予測を生成")
    else:
        print("  ✅ 予測される問題なし")
    
    # レポート生成
    report = engine.generate_report()
    print(report)
    
    print("=" * 70)
    print("✅ デモ完了")
    print(f"   予測保存先: {engine.data_dir}")
    print("=" * 70)

