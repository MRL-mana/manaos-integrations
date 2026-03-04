#!/usr/bin/env python3
"""
Smart Cost Optimizer
タスクを自動で分類して、最適な方法（無料/有料）を選択
"""

import re
from typing import Dict, Any, List
from enum import Enum

class TaskComplexity(Enum):
    """タスクの複雑度"""
    SIMPLE = "simple"           # 完全無料版でOK
    MODERATE = "moderate"       # 状況による
    COMPLEX = "complex"         # 有料版推奨

class ExecutionMethod(Enum):
    """実行方法"""
    UI_TEST_FREE = "ui_test"    # 完全無料（UI Test System）
    COMPUTER_USE_PAID = "computer_use"  # 有料（Computer Use with AI）

class SmartCostOptimizer:
    """
    賢いコスト最適化エンジン
    タスクを分析して、最適な実行方法を自動選択
    """
    
    def __init__(self):
        # 定型パターン（無料版で実行可能）
        self.simple_patterns = [
            # アプリ起動系
            r"メモ帳.*開",
            r"notepad.*開",
            r"電卓.*開",
            r"calculator.*開",
            r"エクスプローラ.*開",
            r"explorer.*開",
            
            # 定型入力系
            r".*入力.*保存",
            r".*タイプ.*保存",
            r".*書.*保存",
            
            # ホットキー系
            r"ctrl\+",
            r"alt\+",
            r"win\+",
            
            # 定型操作
            r"クリック.*保存",
            r"保存.*閉じ",
            r"開.*入力.*保存",
        ]
        
        # 複雑パターン（有料版推奨）
        self.complex_patterns = [
            # 検索系
            r"検索.*して",
            r"探.*して",
            r"見つけ.*て",
            
            # 条件分岐
            r"もし.*なら",
            r".*の場合",
            r".*確認.*て",
            
            # 複数アプリ連携
            r".*から.*へ",
            r"コピー.*貼り付け",
            
            # 柔軟な操作
            r"適当.*",
            r"いい感じ.*",
            r"よろしく.*",
        ]
        
        # コスト情報
        self.costs = {
            ExecutionMethod.UI_TEST_FREE: 0.0,
            ExecutionMethod.COMPUTER_USE_PAID: 0.12
        }
    
    def analyze_task(self, task: str) -> Dict[str, Any]:
        """
        タスクを分析して最適な実行方法を判定
        
        Args:
            task: タスクの説明（自然言語）
        
        Returns:
            Dict: 分析結果
            {
                "complexity": TaskComplexity,
                "recommended_method": ExecutionMethod,
                "cost": float,
                "reasoning": str,
                "alternative": Dict  # 代替案
            }
        """
        task_lower = task.lower()
        
        # シンプルパターンチェック
        is_simple = any(re.search(pattern, task_lower) for pattern in self.simple_patterns)
        
        # 複雑パターンチェック
        is_complex = any(re.search(pattern, task_lower) for pattern in self.complex_patterns)
        
        # 判定
        if is_simple and not is_complex:
            complexity = TaskComplexity.SIMPLE
            method = ExecutionMethod.UI_TEST_FREE
            reasoning = "定型操作のため、無料版（UI Test System）で実行可能"
            
        elif is_complex:
            complexity = TaskComplexity.COMPLEX
            method = ExecutionMethod.COMPUTER_USE_PAID
            reasoning = "柔軟な判断が必要なため、有料版（Computer Use with AI）を推奨"
            
        else:
            complexity = TaskComplexity.MODERATE
            method = ExecutionMethod.UI_TEST_FREE
            reasoning = "定型化できる可能性あり。まず無料版を試すことを推奨"
        
        # 代替案
        if method == ExecutionMethod.UI_TEST_FREE:
            alternative = {
                "method": ExecutionMethod.COMPUTER_USE_PAID,
                "cost": self.costs[ExecutionMethod.COMPUTER_USE_PAID],
                "reason": "YAMLを書くのが面倒な場合"
            }
        else:
            alternative = {
                "method": ExecutionMethod.UI_TEST_FREE,
                "cost": self.costs[ExecutionMethod.UI_TEST_FREE],
                "reason": "定型化できれば無料で実行可能"
            }
        
        return {
            "task": task,
            "complexity": complexity.value,
            "recommended_method": method.value,
            "cost": self.costs[method],
            "reasoning": reasoning,
            "alternative": alternative
        }
    
    def generate_monthly_estimate(self, tasks: List[Dict[str, int]]) -> Dict[str, Any]:
        """
        月間コスト見積もり
        
        Args:
            tasks: タスクリスト
            [
                {"task": "メモ帳を開く", "frequency": 20},  # 月20回
                {"task": "ブラウザで検索", "frequency": 5},  # 月5回
            ]
        
        Returns:
            Dict: 見積もり結果
        """
        total_cost = 0.0
        breakdown = []
        
        for task_info in tasks:
            task = task_info["task"]
            frequency = task_info["frequency"]
            
            analysis = self.analyze_task(task)
            cost_per_execution = analysis["cost"]
            monthly_cost = cost_per_execution * frequency
            total_cost += monthly_cost
            
            breakdown.append({
                "task": task,
                "frequency": frequency,
                "method": analysis["recommended_method"],
                "cost_per_execution": cost_per_execution,
                "monthly_cost": monthly_cost
            })
        
        return {
            "total_monthly_cost": total_cost,
            "breakdown": breakdown,
            "summary": {
                "ui_test_tasks": sum(1 for b in breakdown if b["method"] == "ui_test"),
                "computer_use_tasks": sum(1 for b in breakdown if b["method"] == "computer_use"),
                "total_executions": sum(b["frequency"] for b in breakdown)
            }
        }
    
    def suggest_optimization(self, tasks: List[Dict[str, int]]) -> Dict[str, Any]:
        """
        コスト最適化の提案
        
        Args:
            tasks: タスクリスト
        
        Returns:
            Dict: 最適化提案
        """
        estimate = self.generate_monthly_estimate(tasks)
        
        # 最適化可能なタスクを検出
        optimization_suggestions = []
        potential_savings = 0.0
        
        for task_info, breakdown in zip(tasks, estimate["breakdown"]):
            if breakdown["method"] == "computer_use":
                task = task_info["task"]
                frequency = task_info["frequency"]
                
                # 定型化できるかチェック
                analysis = self.analyze_task(task)
                if analysis["complexity"] == TaskComplexity.MODERATE.value:
                    savings = breakdown["monthly_cost"]
                    potential_savings += savings
                    
                    optimization_suggestions.append({
                        "task": task,
                        "current_method": "computer_use",
                        "current_cost": breakdown["monthly_cost"],
                        "suggested_method": "ui_test",
                        "suggested_cost": 0.0,
                        "savings": savings,
                        "action": f"このタスクはYAML化すれば月${savings:.2f}削減可能"
                    })
        
        return {
            "current_estimate": estimate,
            "potential_savings": potential_savings,
            "optimized_monthly_cost": estimate["total_monthly_cost"] - potential_savings,
            "suggestions": optimization_suggestions
        }


def demo():
    """デモ実行"""
    print("🎯 Smart Cost Optimizer デモ")
    print("=" * 70)
    print()
    
    optimizer = SmartCostOptimizer()
    
    # タスク分析デモ
    print("📝 タスク分析")
    print("-" * 70)
    
    test_tasks = [
        "X280でメモ帳を開いてHello Worldと入力して保存",
        "X280でブラウザを開いてPythonのドキュメントを検索",
        "X280で電卓を起動して123+456を計算",
        "X280でExcelを開いて適当にデータを入力",
    ]
    
    for task in test_tasks:
        analysis = optimizer.analyze_task(task)
        print(f"\nタスク: {task}")
        print(f"  複雑度: {analysis['complexity']}")
        print(f"  推奨方法: {analysis['recommended_method']}")
        print(f"  コスト: ${analysis['cost']:.2f}")
        print(f"  理由: {analysis['reasoning']}")
    
    print("\n" + "=" * 70)
    print()
    
    # 月間見積もりデモ
    print("💰 月間コスト見積もり")
    print("-" * 70)
    
    monthly_tasks = [
        {"task": "メモ帳を開いて入力", "frequency": 20},      # 毎営業日
        {"task": "ブラウザで検索", "frequency": 5},           # 週1回程度
        {"task": "電卓で計算", "frequency": 10},              # 週2回程度
        {"task": "Excelにデータ入力", "frequency": 3},        # たまに
    ]
    
    suggestion = optimizer.suggest_optimization(monthly_tasks)
    
    print("\n現在の見積もり:")
    for breakdown in suggestion["current_estimate"]["breakdown"]:
        print(f"  {breakdown['task']}")
        print(f"    方法: {breakdown['method']}")
        print(f"    頻度: {breakdown['frequency']}回/月")
        print(f"    月額: ${breakdown['monthly_cost']:.2f}")
    
    print(f"\n合計月額: ${suggestion['current_estimate']['total_monthly_cost']:.2f}")
    
    if suggestion["suggestions"]:
        print(f"\n最適化後: ${suggestion['optimized_monthly_cost']:.2f}")
        print(f"削減額: ${suggestion['potential_savings']:.2f}")
        
        print("\n💡 最適化提案:")
        for sug in suggestion["suggestions"]:
            print(f"  • {sug['action']}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    demo()

