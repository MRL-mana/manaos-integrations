#!/usr/bin/env python3
"""
思考ログ監査システム - AIの自己反省
LangFuse/LangSmith的な思考プロセス追跡＋改善提案
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import hashlib

@dataclass
class ThoughtStep:
    """思考ステップ"""
    step_id: str
    timestamp: float
    thought: str
    action: str
    result: str
    success: bool
    confidence: float
    duration: float

@dataclass
class ThinkingSession:
    """思考セッション"""
    session_id: str
    task: str
    start_time: float
    end_time: Optional[float]
    steps: List[ThoughtStep]
    final_result: Optional[str]
    success: bool
    total_confidence: float

class ThinkingAuditSystem:
    """思考ログ監査システム"""
    
    def __init__(self):
        self.log_dir = Path("/root/god_mode/thinking_logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[ThinkingSession] = None
        self.sessions_db = self.log_dir / "sessions.jsonl"
        self.analysis_cache = self.log_dir / "analysis_cache.json"
    
    def start_session(self, task: str) -> str:
        """思考セッション開始"""
        session_id = hashlib.md5(
            f"{task}_{time.time()}".encode()
        ).hexdigest()[:12]
        
        self.current_session = ThinkingSession(
            session_id=session_id,
            task=task,
            start_time=time.time(),
            end_time=None,
            steps=[],
            final_result=None,
            success=False,
            total_confidence=0.0
        )
        
        return session_id
    
    def log_thought(
        self,
        thought: str,
        action: str,
        result: str,
        success: bool,
        confidence: float,
        duration: float = 0.0
    ):
        """思考ステップを記録"""
        if not self.current_session:
            raise ValueError("セッション未開始")
        
        step_id = f"step_{len(self.current_session.steps) + 1}"
        
        step = ThoughtStep(
            step_id=step_id,
            timestamp=time.time(),
            thought=thought,
            action=action,
            result=result,
            success=success,
            confidence=confidence,
            duration=duration
        )
        
        self.current_session.steps.append(step)
    
    def end_session(self, final_result: str, success: bool):
        """セッション終了"""
        if not self.current_session:
            return
        
        self.current_session.end_time = time.time()
        self.current_session.final_result = final_result
        self.current_session.success = success
        
        # 平均信頼度計算
        if self.current_session.steps:
            avg_conf = sum(s.confidence for s in self.current_session.steps) / len(self.current_session.steps)
            self.current_session.total_confidence = avg_conf
        
        # セッション保存
        self._save_session(self.current_session)
        
        # 分析実行
        analysis = self._analyze_session(self.current_session)
        self._save_analysis(analysis)
        
        self.current_session = None
        
        return analysis
    
    def _save_session(self, session: ThinkingSession):
        """セッション保存（JSONL形式）"""
        with open(self.sessions_db, 'a') as f:
            data = asdict(session)
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
    def _analyze_session(self, session: ThinkingSession) -> Dict:
        """セッション分析"""
        if not session.steps:
            return {"error": "ステップなし"}
        
        # 失敗パターン検出
        failed_steps = [s for s in session.steps if not s.success]
        
        # 低信頼度ステップ
        low_confidence_steps = [s for s in session.steps if s.confidence < 0.7]
        
        # 時間分析
        total_duration = sum(s.duration for s in session.steps)
        avg_duration = total_duration / len(session.steps) if session.steps else 0
        
        # パターン抽出
        action_counts = {}
        for step in session.steps:
            action_counts[step.action] = action_counts.get(step.action, 0) + 1
        
        analysis = {
            "session_id": session.session_id,
            "task": session.task,
            "success": session.success,
            "total_steps": len(session.steps),
            "failed_steps": len(failed_steps),
            "low_confidence_steps": len(low_confidence_steps),
            "avg_confidence": session.total_confidence,
            "total_duration": total_duration,
            "avg_step_duration": avg_duration,
            "action_distribution": action_counts,
            "insights": self._generate_insights(session),
            "improvements": self._suggest_improvements(session)
        }
        
        return analysis
    
    def _generate_insights(self, session: ThinkingSession) -> List[str]:
        """インサイト生成"""
        insights = []
        
        # 成功率
        success_rate = sum(1 for s in session.steps if s.success) / len(session.steps)
        if success_rate < 0.5:
            insights.append(f"⚠️ 成功率が低い（{success_rate*100:.1f}%）- アプローチの見直しが必要")
        elif success_rate > 0.9:
            insights.append(f"✅ 高い成功率（{success_rate*100:.1f}%）- パターンを学習価値あり")
        
        # 信頼度
        if session.total_confidence < 0.7:
            insights.append(f"⚠️ 平均信頼度が低い（{session.total_confidence*100:.1f}%）- より確実な手法を検討")
        
        # 時間効率
        total_time = session.end_time - session.start_time if session.end_time else 0
        if total_time > 300:  # 5分以上
            insights.append(f"⏰ 実行時間が長い（{total_time:.1f}秒）- 並列化や最適化を検討")
        
        # アクション多様性
        unique_actions = len(set(s.action for s in session.steps))
        if unique_actions < 3:
            insights.append("💡 アクションの種類が少ない - より多様なアプローチを試す余地あり")
        
        return insights
    
    def _suggest_improvements(self, session: ThinkingSession) -> List[str]:
        """改善提案"""
        improvements = []
        
        # 失敗パターン分析
        failed_actions = [s.action for s in session.steps if not s.success]
        if failed_actions:
            action_freq = {}
            for action in failed_actions:
                action_freq[action] = action_freq.get(action, 0) + 1
            
            most_failed = max(action_freq.items(), key=lambda x: x[1])
            improvements.append(
                f"🔧 「{most_failed[0]}」アクションが{most_failed[1]}回失敗 - 代替手法の検討"
            )
        
        # 低信頼度改善
        low_conf_actions = [s.action for s in session.steps if s.confidence < 0.7]
        if low_conf_actions:
            improvements.append(
                f"📊 信頼度が低いアクション: {', '.join(set(low_conf_actions))} - データ収集や検証強化"
            )
        
        # 時間最適化
        slow_steps = [s for s in session.steps if s.duration > 10]
        if slow_steps:
            improvements.append(
                f"⚡ 時間のかかるステップ（{len(slow_steps)}個）- キャッシュや並列化を検討"
            )
        
        return improvements
    
    def _save_analysis(self, analysis: Dict):
        """分析結果をキャッシュ"""
        cache = []
        if self.analysis_cache.exists():
            with open(self.analysis_cache, 'r') as f:
                cache = json.load(f)
        
        cache.append({
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis
        })
        
        # 最新100件のみ保持
        cache = cache[-100:]
        
        with open(self.analysis_cache, 'w') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    
    def get_failure_patterns(self, days: int = 7) -> Dict:
        """失敗パターン分析"""
        cutoff = time.time() - (days * 86400)
        
        sessions = self._load_recent_sessions(cutoff)
        
        failure_patterns = {}
        for session_data in sessions:
            for step in session_data.get('steps', []):
                if not step.get('success', True):
                    action = step.get('action', 'unknown')
                    if action not in failure_patterns:
                        failure_patterns[action] = {
                            'count': 0,
                            'examples': []
                        }
                    
                    failure_patterns[action]['count'] += 1
                    failure_patterns[action]['examples'].append({
                        'thought': step.get('thought', '')[:100],
                        'result': step.get('result', '')[:100]
                    })
        
        # 頻度順にソート
        sorted_patterns = dict(
            sorted(failure_patterns.items(), key=lambda x: x[1]['count'], reverse=True)
        )
        
        return sorted_patterns
    
    def get_learning_recommendations(self) -> List[Dict]:
        """学習推奨事項"""
        # 最近の分析から推奨事項を抽出
        if not self.analysis_cache.exists():
            return []
        
        with open(self.analysis_cache, 'r') as f:
            cache = json.load(f)
        
        # 最新10件から推奨事項を集約
        recent = cache[-10:]
        all_improvements = []
        
        for item in recent:
            improvements = item.get('analysis', {}).get('improvements', [])
            all_improvements.extend(improvements)
        
        # 重複を削除して頻度カウント
        improvement_freq = {}
        for imp in all_improvements:
            improvement_freq[imp] = improvement_freq.get(imp, 0) + 1
        
        # 頻度順にソートして返す
        recommendations = [
            {
                'recommendation': imp,
                'frequency': freq,
                'priority': 'high' if freq >= 3 else 'medium' if freq >= 2 else 'low'
            }
            for imp, freq in sorted(improvement_freq.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return recommendations
    
    def _load_recent_sessions(self, cutoff_time: float) -> List[Dict]:
        """最近のセッション読み込み"""
        if not self.sessions_db.exists():
            return []
        
        sessions = []
        with open(self.sessions_db, 'r') as f:
            for line in f:
                try:
                    session = json.loads(line)
                    if session.get('start_time', 0) >= cutoff_time:
                        sessions.append(session)
                except:
                    continue
        
        return sessions
    
    def generate_report(self, days: int = 7) -> str:
        """レポート生成"""
        sessions = self._load_recent_sessions(time.time() - days * 86400)
        
        if not sessions:
            return "📊 データなし（まだセッションが記録されていません）"
        
        # 統計
        total_sessions = len(sessions)
        successful = sum(1 for s in sessions if s.get('success', False))
        success_rate = successful / total_sessions * 100
        
        # 平均信頼度
        avg_confidence = sum(s.get('total_confidence', 0) for s in sessions) / total_sessions * 100
        
        # 失敗パターン
        failure_patterns = self.get_failure_patterns(days)
        
        # 学習推奨
        recommendations = self.get_learning_recommendations()
        
        report = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 思考ログ監査レポート（過去{days}日間）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 統計:
  セッション数: {total_sessions}
  成功率: {success_rate:.1f}%
  平均信頼度: {avg_confidence:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ 失敗パターン TOP3:
"""
        
        for i, (action, data) in enumerate(list(failure_patterns.items())[:3], 1):
            report += f"\n  {i}. {action}: {data['count']}回失敗"
        
        report += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += "\n💡 学習推奨事項:\n"
        
        for i, rec in enumerate(recommendations[:5], 1):
            priority_emoji = "🔥" if rec['priority'] == 'high' else "⚠️" if rec['priority'] == 'medium' else "💡"
            report += f"\n  {priority_emoji} {rec['recommendation']}"
        
        report += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return report

# グローバルインスタンス
_audit_system = None

def get_audit_system() -> ThinkingAuditSystem:
    """グローバル監査システム取得"""
    global _audit_system
    if _audit_system is None:
        _audit_system = ThinkingAuditSystem()
    return _audit_system

# テスト実行
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 思考ログ監査システム - デモ実行")
    print("=" * 70)
    
    system = ThinkingAuditSystem()
    
    # デモセッション1: 成功例
    print("\n[デモ1] 成功例...")
    session_id = system.start_session("GitHub PR自動レビュー")
    
    system.log_thought(
        thought="PRの変更ファイルを取得",
        action="github_api_call",
        result="3ファイルの変更を検出",
        success=True,
        confidence=0.95,
        duration=1.2
    )
    
    system.log_thought(
        thought="各ファイルをコード品質チェック",
        action="code_review",
        result="軽微な問題2件発見",
        success=True,
        confidence=0.88,
        duration=2.5
    )
    
    system.log_thought(
        thought="レビューコメント生成",
        action="generate_comment",
        result="改善提案を作成",
        success=True,
        confidence=0.92,
        duration=0.8
    )
    
    analysis1 = system.end_session("レビュー完了", True)
    print(f"  成功率: {analysis1['total_steps'] - analysis1['failed_steps']}/{analysis1['total_steps']}")  # type: ignore[index]
    print(f"  平均信頼度: {analysis1['avg_confidence']*100:.1f}%")  # type: ignore[index]
    
    # デモセッション2: 失敗を含む例
    print("\n[デモ2] 失敗を含む例...")
    session_id = system.start_session("自動バグ修正")
    
    system.log_thought(
        thought="エラーログを解析",
        action="log_analysis",
        result="ImportError検出",
        success=True,
        confidence=0.90,
        duration=1.0
    )
    
    system.log_thought(
        thought="修正パッチを生成",
        action="generate_patch",
        result="パッチ生成失敗（依存関係不明）",
        success=False,
        confidence=0.45,
        duration=3.2
    )
    
    system.log_thought(
        thought="代替アプローチ：依存関係を調査",
        action="dependency_check",
        result="必要なパッケージを特定",
        success=True,
        confidence=0.85,
        duration=2.1
    )
    
    analysis2 = system.end_session("部分的に成功", False)
    print(f"  成功率: {analysis2['total_steps'] - analysis2['failed_steps']}/{analysis2['total_steps']}")  # type: ignore[index]
    print(f"  平均信頼度: {analysis2['avg_confidence']*100:.1f}%")  # type: ignore[index]
    
    # レポート生成
    print("\n" + "=" * 70)
    print(system.generate_report(days=1))
    print("=" * 70)
    
    print("\n✅ デモ完了")
    print(f"   ログ保存先: {system.log_dir}")

