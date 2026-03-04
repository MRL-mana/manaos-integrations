#!/usr/bin/env python3
"""
Advanced Model Analyzer
WAN 2.2, SDXL, Fast モデルの詳細分析
"""

import subprocess
import sys
import time
import psutil
from pathlib import Path

class AdvancedModelAnalyzer:
    def __init__(self):
        self.system_info = self._get_system_info()
        self.model_requirements = self._get_model_requirements()
    
    def _get_system_info(self):
        """システム情報取得"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "memory_gb": memory.total / (1024**3),
            "available_memory_gb": memory.available / (1024**3),
            "disk_gb": disk.total / (1024**3),
            "available_disk_gb": disk.free / (1024**3),
            "cpu_cores": psutil.cpu_count(logical=False),
            "cpu_threads": psutil.cpu_count(logical=True)
        }
    
    def _get_model_requirements(self):
        """モデル要件定義"""
        return {
            "wan_2_2": {
                "name": "WAN 2.2 (Waifu Diffusion 2.2)",
                "size_gb": 2.0,
                "memory_gb": 4.0,
                "generation_time_min": 8,
                "quality": "High",
                "compatibility": "Excellent",
                "description": "アニメ・イラスト特化、高品質"
            },
            "sdxl": {
                "name": "Stable Diffusion XL",
                "size_gb": 6.0,
                "memory_gb": 8.0,
                "generation_time_min": 15,
                "quality": "Very High",
                "compatibility": "Good",
                "description": "汎用高品質、リアル・アート両対応"
            },
            "fast": {
                "name": "Fast Models (TinySD, etc.)",
                "size_gb": 0.5,
                "memory_gb": 2.0,
                "generation_time_min": 3,
                "quality": "Medium",
                "compatibility": "Excellent",
                "description": "軽量高速、リアルタイム生成"
            }
        }
    
    def analyze_feasibility(self):
        """実現可能性分析"""
        system = self.system_info
        models = self.model_requirements
        
        results = {}
        
        for model_key, model_info in models.items():
            # メモリチェック
            memory_ok = model_info["memory_gb"] <= system["available_memory_gb"]
            
            # ディスクチェック
            disk_ok = model_info["size_gb"] <= system["available_disk_gb"]
            
            # 総合評価
            feasible = memory_ok and disk_ok
            
            results[model_key] = {
                "feasible": feasible,
                "memory_ok": memory_ok,
                "disk_ok": disk_ok,
                "memory_usage_percent": (model_info["memory_gb"] / system["available_memory_gb"]) * 100,
                "disk_usage_percent": (model_info["size_gb"] / system["available_disk_gb"]) * 100,
                "recommendation": self._get_recommendation(model_key, feasible)
            }
        
        return results
    
    def _get_recommendation(self, model_key, feasible):
        """推奨度計算"""
        if not feasible:
            return "❌ 非推奨 - システム要件不足"
        
        system = self.system_info
        model = self.model_requirements[model_key]
        
        # メモリ使用率
        memory_usage = (model["memory_gb"] / system["available_memory_gb"]) * 100
        
        # 生成時間
        generation_time = model["generation_time_min"]
        
        # 品質
        quality_score = {"Medium": 1, "High": 2, "Very High": 3}[model["quality"]]
        
        # 総合スコア
        if memory_usage < 50 and generation_time < 10:
            return "✅ 強く推奨 - 最適なバランス"
        elif memory_usage < 70 and generation_time < 15:
            return "✅ 推奨 - 良好な性能"
        elif memory_usage < 90:
            return "⚠️ 条件付き推奨 - メモリ使用量に注意"
        else:
            return "❌ 非推奨 - メモリ不足の可能性"
    
    def analyze_combination(self):
        """組み合わせ分析"""
        system = self.system_info
        models = self.model_requirements
        
        combinations = {
            "wan_sdxl": {
                "models": ["wan_2_2", "sdxl"],
                "total_size_gb": models["wan_2_2"]["size_gb"] + models["sdxl"]["size_gb"],
                "max_memory_gb": max(models["wan_2_2"]["memory_gb"], models["sdxl"]["memory_gb"]),
                "description": "WAN 2.2 + SDXL - アニメ・リアル両対応"
            },
            "wan_fast": {
                "models": ["wan_2_2", "fast"],
                "total_size_gb": models["wan_2_2"]["size_gb"] + models["fast"]["size_gb"],
                "max_memory_gb": max(models["wan_2_2"]["memory_gb"], models["fast"]["memory_gb"]),
                "description": "WAN 2.2 + Fast - 高品質・高速両立"
            },
            "sdxl_fast": {
                "models": ["sdxl", "fast"],
                "total_size_gb": models["sdxl"]["size_gb"] + models["fast"]["size_gb"],
                "max_memory_gb": max(models["sdxl"]["memory_gb"], models["fast"]["memory_gb"]),
                "description": "SDXL + Fast - 汎用・高速両立"
            },
            "all_three": {
                "models": ["wan_2_2", "sdxl", "fast"],
                "total_size_gb": sum(models[m]["size_gb"] for m in ["wan_2_2", "sdxl", "fast"]),
                "max_memory_gb": max(models[m]["memory_gb"] for m in ["wan_2_2", "sdxl", "fast"]),
                "description": "全モデル - 完全対応"
            }
        }
        
        results = {}
        for combo_key, combo_info in combinations.items():
            disk_ok = combo_info["total_size_gb"] <= system["available_disk_gb"]
            memory_ok = combo_info["max_memory_gb"] <= system["available_memory_gb"]
            
            results[combo_key] = {
                "feasible": disk_ok and memory_ok,
                "disk_ok": disk_ok,
                "memory_ok": memory_ok,
                "total_size_gb": combo_info["total_size_gb"],
                "max_memory_gb": combo_info["max_memory_gb"],
                "description": combo_info["description"]
            }
        
        return results
    
    def generate_implementation_plan(self):
        """実装計画生成"""
        system = self.system_info
        individual = self.analyze_feasibility()
        combinations = self.analyze_combination()
        
        plan = {
            "phase_1": {
                "name": "段階的導入",
                "steps": [
                    "1. Fast Models導入（軽量・高速）",
                    "2. WAN 2.2導入（アニメ特化）",
                    "3. SDXL導入（汎用高品質）"
                ],
                "total_size_gb": 8.5,
                "estimated_time_hours": 2
            },
            "phase_2": {
                "name": "最適化",
                "steps": [
                    "1. モデル切り替えシステム構築",
                    "2. メモリ管理最適化",
                    "3. 生成時間短縮設定"
                ],
                "estimated_time_hours": 1
            },
            "phase_3": {
                "name": "統合テスト",
                "steps": [
                    "1. 全モデル動作確認",
                    "2. 性能ベンチマーク",
                    "3. Webインターフェース統合"
                ],
                "estimated_time_hours": 1
            }
        }
        
        return plan
    
    def print_analysis_report(self):
        """分析レポート表示"""
        print("🚀 Advanced Model Analysis - WAN 2.2, SDXL, Fast")
        print("=" * 80)
        
        # システム情報
        system = self.system_info
        print(f"\n💻 システム情報:")
        print("-" * 50)
        print(f"  💾 メモリ: {system['memory_gb']:.1f}GB (利用可能: {system['available_memory_gb']:.1f}GB)")
        print(f"  💿 ディスク: {system['disk_gb']:.1f}GB (利用可能: {system['available_disk_gb']:.1f}GB)")
        print(f"  🖥️ CPU: {system['cpu_cores']} cores, {system['cpu_threads']} threads")
        
        # 個別モデル分析
        print(f"\n📦 個別モデル分析:")
        print("-" * 50)
        individual = self.analyze_feasibility()
        models = self.model_requirements
        
        for model_key, model_info in models.items():
            result = individual[model_key]
            print(f"\n🎨 {model_info['name']}:")
            print(f"  サイズ: {model_info['size_gb']}GB")
            print(f"  メモリ: {model_info['memory_gb']}GB")
            print(f"  生成時間: {model_info['generation_time_min']}分")
            print(f"  品質: {model_info['quality']}")
            print(f"  実現可能: {'✅' if result['feasible'] else '❌'}")
            print(f"  推奨: {result['recommendation']}")
        
        # 組み合わせ分析
        print(f"\n🔄 組み合わせ分析:")
        print("-" * 50)
        combinations = self.analyze_combination()
        
        for combo_key, combo_info in combinations.items():
            print(f"\n📦 {combo_info['description']}:")
            print(f"  総サイズ: {combo_info['total_size_gb']}GB")
            print(f"  最大メモリ: {combo_info['max_memory_gb']}GB")
            print(f"  実現可能: {'✅' if combo_info['feasible'] else '❌'}")
        
        # 実装計画
        print(f"\n📋 実装計画:")
        print("-" * 50)
        plan = self.generate_implementation_plan()
        
        for phase_key, phase_info in plan.items():
            print(f"\n{phase_info['name']}:")
            for step in phase_info['steps']:
                print(f"  • {step}")
            if 'total_size_gb' in phase_info:
                print(f"  総サイズ: {phase_info['total_size_gb']}GB")
            print(f"  推定時間: {phase_info['estimated_time_hours']}時間")
        
        # 最終推奨
        print(f"\n💡 最終推奨:")
        print("-" * 50)
        if combinations["all_three"]["feasible"]:
            print("  ✅ 全モデル導入可能 - 完全対応システム構築推奨")
        elif combinations["wan_sdxl"]["feasible"]:
            print("  ✅ WAN 2.2 + SDXL 推奨 - 高品質システム")
        elif combinations["wan_fast"]["feasible"]:
            print("  ✅ WAN 2.2 + Fast 推奨 - バランス型システム")
        else:
            print("  ⚠️ 段階的導入推奨 - システム負荷を考慮")


def main():
    """メイン関数"""
    analyzer = AdvancedModelAnalyzer()
    analyzer.print_analysis_report()


if __name__ == "__main__":
    main()


