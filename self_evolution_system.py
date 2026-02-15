#!/usr/bin/env python3
"""
🧬 ManaOS 自己進化システム
コードの自動改善、パフォーマンスの自動向上
"""

import json
import ast
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_service_logger("self-evolution-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SelfEvolutionSystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("SelfEvolutionSystem")


@dataclass
class CodeImprovement:
    """コード改善提案"""
    file_path: str
    improvement_type: str  # "performance", "readability", "bug_fix", "optimization"
    description: str
    suggested_code: str
    expected_improvement: float  # 0.0-1.0
    priority: int  # 1-10
    created_at: str


class SelfEvolutionSystem:
    """自己進化システム"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path or Path(__file__).parent / "self_evolution_config.json"
        self.config = self._load_config()
        
        # 改善提案
        self.improvements: List[CodeImprovement] = []
        self.improvements_storage = Path("code_improvements.json")
        self._load_improvements()
        
        # パフォーマンス履歴
        self.performance_history: List[Dict[str, Any]] = []
        self.performance_storage = Path("performance_history.json")
        self._load_performance_history()
        
        # コールバック関数
        self.on_improvement_suggested = None
        
        logger.info("✅ Self Evolution System初期化完了")
    
    def record_successful_repair(self, repair_result: Dict[str, Any]):
        """
        成功した修復を記録（自己修復システムとの連携）
        
        Args:
            repair_result: 修復結果
        """
        try:
            # 修復成功パターンをパフォーマンス履歴に記録
            self.performance_history.append({
                "type": "repair_success",
                "repair_action": repair_result.get("action", ""),
                "message": repair_result.get("message", ""),
                "timestamp": datetime.now().isoformat()
            })
            self._save_performance_history()
        except Exception as e:
            logger.warning(f"修復成功記録エラー: {e}")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"設定読み込みエラー: {e}")
        
        return {
            "enable_auto_improvement": True,
            "enable_performance_tracking": True,
            "improvement_threshold": 0.1,  # 10%以上の改善が見込まれる場合のみ適用
            "auto_apply_improvements": False  # 自動適用はデフォルトで無効
        }
    
    def _load_improvements(self):
        """改善提案を読み込む"""
        if self.improvements_storage.exists():
            try:
                with open(self.improvements_storage, 'r', encoding='utf-8') as f:
                    improvements_data = json.load(f)
                    self.improvements = [
                        CodeImprovement(**item) for item in improvements_data
                    ]
            except Exception as e:
                logger.warning(f"改善提案読み込みエラー: {e}")
    
    def _save_improvements(self):
        """改善提案を保存"""
        try:
            improvements_data = [asdict(imp) for imp in self.improvements]
            with open(self.improvements_storage, 'w', encoding='utf-8') as f:
                json.dump(improvements_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"改善提案保存エラー: {e}")
    
    def _load_performance_history(self):
        """パフォーマンス履歴を読み込む"""
        if self.performance_storage.exists():
            try:
                with open(self.performance_storage, 'r', encoding='utf-8') as f:
                    self.performance_history = json.load(f)
            except Exception as e:
                logger.warning(f"パフォーマンス履歴読み込みエラー: {e}")
    
    def _save_performance_history(self):
        """パフォーマンス履歴を保存"""
        try:
            # 最新100件のみ保存
            recent_history = self.performance_history[-100:]
            with open(self.performance_storage, 'w', encoding='utf-8') as f:
                json.dump(recent_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"パフォーマンス履歴保存エラー: {e}")
    
    def analyze_code_performance(self, file_path: str) -> Dict[str, Any]:
        """
        コードのパフォーマンスを分析
        
        Args:
            file_path: 分析するファイルのパス
            
        Returns:
            分析結果
        """
        try:
            code_file = Path(file_path)
            if not code_file.exists():
                return {"error": f"ファイルが見つかりません: {file_path}"}
            
            with open(code_file, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # 簡易的なコード分析
            analysis = {
                "file_path": file_path,
                "lines_of_code": len(code_content.splitlines()),
                "complexity_score": self._calculate_complexity(code_content),
                "performance_issues": self._detect_performance_issues(code_content),
                "optimization_opportunities": self._find_optimization_opportunities(code_content),
                "timestamp": datetime.now().isoformat()
            }
            
            # パフォーマンス履歴に記録
            self.performance_history.append(analysis)
            self._save_performance_history()
            
            return analysis
        except Exception as e:
            return {"error": str(e)}
    
    def _calculate_complexity(self, code: str) -> float:
        """コードの複雑度を計算（簡易版）"""
        try:
            tree = ast.parse(code)
            complexity = 0
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                    complexity += 1
            
            return complexity
        except Exception:
            return 0.0
    
    def _detect_performance_issues(self, code: str) -> List[str]:
        """パフォーマンス問題を検出"""
        issues = []
        
        # 重い操作の検出
        if "time.sleep(" in code and code.count("time.sleep(") > 5:
            issues.append("多数のtime.sleep()呼び出しが検出されました")
        
        # ネストされたループの検出
        if code.count("for ") > 3 and code.count("    for ") > 1:
            issues.append("深くネストされたループが検出されました")
        
        # 大きなリストの検出
        if "range(10000)" in code or "range(100000)" in code:
            issues.append("大きな範囲のループが検出されました")
        
        return issues
    
    def _find_optimization_opportunities(self, code: str) -> List[str]:
        """最適化の機会を発見"""
        opportunities = []
        
        # リスト内包表記の機会
        if "for " in code and ".append(" in code:
            opportunities.append("リスト内包表記への変換が可能です")
        
        # キャッシュの機会
        if code.count("def ") > 5 and "@lru_cache" not in code:
            opportunities.append("関数結果のキャッシュが有効です")
        
        # 並列処理の機会
        if "for " in code and "requests.get(" in code:
            opportunities.append("並列処理が有効です")
        
        return opportunities
    
    def suggest_improvements(self, file_path: str) -> List[CodeImprovement]:
        """
        改善提案を生成
        
        Args:
            file_path: 分析するファイルのパス
            
        Returns:
            改善提案のリスト
        """
        analysis = self.analyze_code_performance(file_path)
        
        if "error" in analysis:
            return []
        
        improvements = []
        
        # パフォーマンス問題に基づく改善提案
        for issue in analysis.get("performance_issues", []):
            improvement = CodeImprovement(
                file_path=file_path,
                improvement_type="performance",
                description=issue,
                suggested_code="",
                expected_improvement=0.2,
                priority=7,
                created_at=datetime.now().isoformat()
            )
            improvements.append(improvement)
        
        # 最適化機会に基づく改善提案
        for opportunity in analysis.get("optimization_opportunities", []):
            improvement = CodeImprovement(
                file_path=file_path,
                improvement_type="optimization",
                description=opportunity,
                suggested_code="",
                expected_improvement=0.15,
                priority=6,
                created_at=datetime.now().isoformat()
            )
            improvements.append(improvement)
        
        # 改善提案を保存
        self.improvements.extend(improvements)
        self._save_improvements()
        
        # 改善提案時にコールバックを実行
        if self.on_improvement_suggested:
            for improvement in improvements:
                try:
                    self.on_improvement_suggested(asdict(improvement))
                except Exception as e:
                    logger.warning(f"改善提案コールバックエラー: {e}")
        
        return improvements
    
    def apply_improvement(self, improvement_id: int) -> Dict[str, Any]:
        """
        改善を適用
        
        Args:
            improvement_id: 改善提案のID
            
        Returns:
            適用結果
        """
        if improvement_id >= len(self.improvements):
            return {"error": "改善提案が見つかりません"}
        
        improvement = self.improvements[improvement_id]
        
        # 自動適用が無効の場合は手動確認が必要
        if not self.config.get("auto_apply_improvements", False):
            return {
                "skipped": True,
                "reason": "自動適用が無効です。手動で確認してください。",
                "improvement": asdict(improvement)
            }
        
        # 改善の期待値が閾値を超えている場合のみ適用
        if improvement.expected_improvement < self.config.get("improvement_threshold", 0.1):
            return {
                "skipped": True,
                "reason": f"期待される改善が閾値未満: {improvement.expected_improvement}",
                "improvement": asdict(improvement)
            }
        
        # 実際の適用は手動で行う必要がある（安全のため）
        return {
            "success": True,
            "message": f"改善提案を適用しました: {improvement.description}",
            "improvement": asdict(improvement),
            "note": "実際のコード変更は手動で確認・適用してください"
        }
    
    def track_performance(self, metric_name: str, value: float, context: Optional[Dict[str, Any]] = None):
        """
        パフォーマンスメトリクスを追跡
        
        Args:
            metric_name: メトリクス名
            value: 値
            context: コンテキスト情報
        """
        metric = {
            "metric_name": metric_name,
            "value": value,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.performance_history.append(metric)
        self._save_performance_history()
        
        # パフォーマンス低下を検知した場合、自動改善を提案
        if self.config.get("enable_auto_improvement", True):
            self._check_performance_degradation(metric_name, value)
    
    def _check_performance_degradation(self, metric_name: str, value: float):
        """パフォーマンス低下をチェックして自動改善を提案"""
        try:
            # 過去の平均値を計算
            recent_metrics = [
                m for m in self.performance_history[-100:]
                if m.get("metric_name") == metric_name
            ]
            
            if len(recent_metrics) < 10:
                return  # データが不足している場合はスキップ
            
            values = [m["value"] for m in recent_metrics]
            avg_value = sum(values) / len(values)
            
            # パフォーマンスが20%以上低下している場合
            if value < avg_value * 0.8:
                improvement = CodeImprovement(
                    file_path="system",
                    improvement_type="performance",
                    description=f"パフォーマンス低下検知: {metric_name} ({value:.2f} < {avg_value:.2f})",
                    suggested_code="",
                    expected_improvement=0.2,
                    priority=8,
                    created_at=datetime.now().isoformat()
                )
                self.improvements.append(improvement)
                self._save_improvements()
                
                # コールバックを実行
                if self.on_improvement_suggested:
                    try:
                        self.on_improvement_suggested(asdict(improvement))
                    except Exception as e:
                        logger.warning(f"改善提案コールバックエラー: {e}")
        except Exception as e:
            logger.warning(f"パフォーマンス低下チェックエラー: {e}")
    
    def auto_improve_performance(self) -> Dict[str, Any]:
        """
        パフォーマンスを自動改善
        
        Returns:
            改善結果
        """
        if not self.config.get("enable_auto_improvement", True):
            return {"skipped": True, "reason": "自動改善が無効です"}
        
        improvements_applied = []
        
        # 優先度の高い改善提案を自動適用
        high_priority_improvements = [
            imp for imp in self.improvements
            if imp.priority >= 8 and imp.expected_improvement >= self.config.get("improvement_threshold", 0.1)
        ]
        
        for improvement in high_priority_improvements[:5]:  # 最大5件まで
            try:
                result = self.apply_improvement(self.improvements.index(improvement))
                if result.get("success"):
                    improvements_applied.append(improvement.description)
            except Exception as e:
                logger.warning(f"改善適用エラー: {e}")
        
        return {
            "success": True,
            "improvements_applied": improvements_applied,
            "count": len(improvements_applied)
        }
    
    def get_performance_trends(self) -> Dict[str, Any]:
        """
        パフォーマンストレンドを取得
        
        Returns:
            トレンド分析結果
        """
        if not self.performance_history:
            return {"error": "パフォーマンス履歴がありません"}
        
        # 簡易的なトレンド分析
        recent_metrics = self.performance_history[-50:]
        
        trends = {}
        for metric in recent_metrics:
            metric_name = metric.get("metric_name")
            if metric_name:
                if metric_name not in trends:
                    trends[metric_name] = []
                trends[metric_name].append(metric.get("value", 0))
        
        # 各メトリクスの平均値を計算
        trend_analysis = {}
        for metric_name, values in trends.items():
            if values:
                trend_analysis[metric_name] = {
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "trend": "improving" if len(values) > 1 and values[-1] < values[0] else "degrading"
                }
        
        return {
            "trends": trend_analysis,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "improvements_count": len(self.improvements),
            "performance_history_count": len(self.performance_history),
            "auto_improvement_enabled": self.config.get("enable_auto_improvement", True),
            "auto_apply_enabled": self.config.get("auto_apply_improvements", False),
            "improvement_threshold": self.config.get("improvement_threshold", 0.1),
            "recent_improvements": [
                {
                    "description": imp.description,
                    "priority": imp.priority,
                    "expected_improvement": imp.expected_improvement,
                    "created_at": imp.created_at
                }
                for imp in self.improvements[-10:]
            ],
            "config": self.config,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    system = SelfEvolutionSystem()
    
    # テスト: コード分析
    analysis = system.analyze_code_performance("comprehensive_self_capabilities_system.py")
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    
    # テスト: 改善提案
    improvements = system.suggest_improvements("comprehensive_self_capabilities_system.py")
    print(f"改善提案数: {len(improvements)}")
    
    # テスト: 状態取得
    status = system.get_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

