"""
A/Bテスト機能
プロンプト最適化の効果を検証
"""

import json
from manaos_logger import get_logger
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import statistics

logger = get_logger(__name__)


class ABTest:
    """A/Bテストクラス"""
    
    def __init__(self, results_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            results_dir: 結果保存ディレクトリ
        """
        if results_dir:
            self.results_dir = Path(results_dir)
        else:
            self.results_dir = Path.home() / "llm_ab_test_results"
        
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.results_file = self.results_dir / "ab_test_results.json"
        self.results = self._load_results()
    
    def _load_results(self) -> List[Dict[str, Any]]:
        """結果を読み込み"""
        if self.results_file.exists():
            try:
                with open(self.results_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 結果読み込みエラー: {e}")
        
        return []
    
    def _save_results(self):
        """結果を保存"""
        try:
            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ 結果保存エラー: {e}")
    
    def run_test(
        self,
        prompt: str,
        variant_a_func,
        variant_b_func,
        test_name: str = "default",
        iterations: int = 10
    ) -> Dict[str, Any]:
        """
        A/Bテストを実行
        
        Args:
            prompt: テストプロンプト
            variant_a_func: バリアントAの関数
            variant_b_func: バリアントBの関数
            test_name: テスト名
            iterations: 反復回数
            
        Returns:
            テスト結果
        """
        logger.info(f"🧪 A/Bテスト開始: {test_name}")
        
        variant_a_results = []
        variant_b_results = []
        
        for i in range(iterations):
            # バリアントA
            start_time = time.time()
            try:
                result_a = variant_a_func(prompt)
                response_time_a = time.time() - start_time
                variant_a_results.append({
                    "response_time": response_time_a,
                    "success": True,
                    "result": result_a
                })
            except Exception as e:
                variant_a_results.append({
                    "response_time": time.time() - start_time,
                    "success": False,
                    "error": str(e)
                })
            
            # バリアントB
            start_time = time.time()
            try:
                result_b = variant_b_func(prompt)
                response_time_b = time.time() - start_time
                variant_b_results.append({
                    "response_time": response_time_b,
                    "success": True,
                    "result": result_b
                })
            except Exception as e:
                variant_b_results.append({
                    "response_time": time.time() - start_time,
                    "success": False,
                    "error": str(e)
                })
        
        # 統計を計算
        variant_a_stats = self._calculate_stats(variant_a_results)
        variant_b_stats = self._calculate_stats(variant_b_results)
        
        # 統計的有意性を検証
        significance = self._test_significance(
            variant_a_results,
            variant_b_results
        )
        
        test_result = {
            "test_name": test_name,
            "prompt": prompt[:200],  # 最初の200文字のみ
            "timestamp": datetime.now().isoformat(),
            "iterations": iterations,
            "variant_a": {
                "stats": variant_a_stats,
                "results": variant_a_results
            },
            "variant_b": {
                "stats": variant_b_stats,
                "results": variant_b_results
            },
            "significance": significance,
            "winner": self._determine_winner(variant_a_stats, variant_b_stats)
        }
        
        self.results.append(test_result)
        self._save_results()
        
        logger.info(f"✅ A/Bテスト完了: {test_name}")
        logger.info(f"   勝者: {test_result['winner']}")
        
        return test_result
    
    def _calculate_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """統計を計算"""
        successful_results = [r for r in results if r.get("success", False)]
        
        if not successful_results:
            return {
                "success_rate": 0.0,
                "average_response_time": 0.0,
                "median_response_time": 0.0,
                "min_response_time": 0.0,
                "max_response_time": 0.0,
                "std_dev": 0.0
            }
        
        response_times = [r["response_time"] for r in successful_results]
        
        return {
            "success_rate": len(successful_results) / len(results),
            "average_response_time": statistics.mean(response_times),
            "median_response_time": statistics.median(response_times),
            "min_response_time": min(response_times),
            "max_response_time": max(response_times),
            "std_dev": statistics.stdev(response_times) if len(response_times) > 1 else 0.0,
            "count": len(successful_results)
        }
    
    def _test_significance(
        self,
        variant_a_results: List[Dict[str, Any]],
        variant_b_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """統計的有意性を検証（簡易版）"""
        a_times = [r["response_time"] for r in variant_a_results if r.get("success")]
        b_times = [r["response_time"] for r in variant_b_results if r.get("success")]
        
        if not a_times or not b_times:
            return {
                "significant": False,
                "p_value": None,
                "method": "insufficient_data"
            }
        
        # 簡易的なt検定（実際にはscipy.statsを使うべき）
        a_mean = statistics.mean(a_times)
        b_mean = statistics.mean(b_times)
        a_std = statistics.stdev(a_times) if len(a_times) > 1 else 0.0
        b_std = statistics.stdev(b_times) if len(b_times) > 1 else 0.0
        
        # 簡易的な効果量計算
        pooled_std = ((a_std ** 2 + b_std ** 2) / 2) ** 0.5
        if pooled_std > 0:
            cohens_d = abs(a_mean - b_mean) / pooled_std
        else:
            cohens_d = 0.0
        
        # 効果量に基づく判定（簡易版）
        significant = cohens_d > 0.5  # 中程度以上の効果
        
        return {
            "significant": significant,
            "cohens_d": cohens_d,
            "method": "cohens_d",
            "interpretation": self._interpret_effect_size(cohens_d)
        }
    
    def _interpret_effect_size(self, cohens_d: float) -> str:
        """効果量を解釈"""
        if cohens_d < 0.2:
            return "効果なし"
        elif cohens_d < 0.5:
            return "小さい効果"
        elif cohens_d < 0.8:
            return "中程度の効果"
        else:
            return "大きい効果"
    
    def _determine_winner(
        self,
        variant_a_stats: Dict[str, Any],
        variant_b_stats: Dict[str, Any]
    ) -> str:
        """勝者を決定"""
        # 成功率を優先
        if variant_a_stats["success_rate"] > variant_b_stats["success_rate"]:
            return "variant_a"
        elif variant_b_stats["success_rate"] > variant_a_stats["success_rate"]:
            return "variant_b"
        
        # 応答時間を比較
        if variant_a_stats["average_response_time"] < variant_b_stats["average_response_time"]:
            return "variant_a"
        elif variant_b_stats["average_response_time"] < variant_a_stats["average_response_time"]:
            return "variant_b"
        
        return "tie"
    
    def get_test_results(self, test_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """テスト結果を取得"""
        if test_name:
            return [r for r in self.results if r["test_name"] == test_name]
        return self.results
    
    def generate_report(self, test_name: Optional[str] = None) -> str:
        """レポートを生成"""
        results = self.get_test_results(test_name)
        
        if not results:
            return "テスト結果がありません。"
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("A/Bテストレポート")
        report_lines.append("=" * 60)
        
        for result in results:
            report_lines.append(f"\nテスト名: {result['test_name']}")
            report_lines.append(f"実行日時: {result['timestamp']}")
            report_lines.append(f"反復回数: {result['iterations']}")
            report_lines.append(f"\nバリアントA:")
            report_lines.append(f"  成功率: {result['variant_a']['stats']['success_rate']:.1%}")
            report_lines.append(f"  平均応答時間: {result['variant_a']['stats']['average_response_time']:.2f}秒")
            report_lines.append(f"\nバリアントB:")
            report_lines.append(f"  成功率: {result['variant_b']['stats']['success_rate']:.1%}")
            report_lines.append(f"  平均応答時間: {result['variant_b']['stats']['average_response_time']:.2f}秒")
            report_lines.append(f"\n勝者: {result['winner']}")
            report_lines.append(f"統計的有意性: {result['significance']['significant']}")
            report_lines.append("-" * 60)
        
        return "\n".join(report_lines)

