#!/usr/bin/env python3
"""
Performance Analyzer
システム性能分析とアップグレード提案
"""

import subprocess
import sys
import time
import psutil
from pathlib import Path

class PerformanceAnalyzer:
    def __init__(self):
        self.system_info = self._get_system_info()
        self.performance_metrics = self._analyze_performance()
    
    def _get_system_info(self):
        """システム情報取得"""
        try:
            # CPU情報
            cpu_info = {
                "model": subprocess.run(['lscpu'], capture_output=True, text=True).stdout,
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
                "usage": psutil.cpu_percent(interval=1)
            }
            
            # メモリ情報
            memory = psutil.virtual_memory()
            memory_info = {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percentage": memory.percent
            }
            
            # ディスク情報
            disk = psutil.disk_usage('/')
            disk_info = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percentage": (disk.used / disk.total) * 100
            }
            
            # GPU情報
            gpu_info = self._check_gpu()
            
            return {
                "cpu": cpu_info,
                "memory": memory_info,
                "disk": disk_info,
                "gpu": gpu_info
            }
            
        except Exception as e:
            print(f"❌ システム情報取得エラー: {str(e)}")
            return {}
    
    def _check_gpu(self):
        """GPU情報確認"""
        try:
            # NVIDIA GPU確認
            nvidia_result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if nvidia_result.returncode == 0:
                return {
                    "type": "NVIDIA",
                    "available": True,
                    "info": nvidia_result.stdout
                }
            else:
                return {
                    "type": "None",
                    "available": False,
                    "info": "No GPU detected"
                }
        except:
            return {
                "type": "None",
                "available": False,
                "info": "GPU check failed"
            }
    
    def _analyze_performance(self):
        """性能分析"""
        current_models = self._get_current_models()
        
        return {
            "current_models": current_models,
            "generation_time": self._estimate_generation_time(),
            "memory_usage": self._estimate_memory_usage(),
            "disk_usage": self._estimate_disk_usage()
        }
    
    def _get_current_models(self):
        """現在のモデル情報"""
        models_dir = Path("/root/civitai_models")
        models = []
        
        if models_dir.exists():
            for model_file in models_dir.glob("*.safetensors"):
                size_mb = model_file.stat().st_size / (1024 * 1024)
                models.append({
                    "name": model_file.name,
                    "size_mb": size_mb,
                    "size_gb": size_mb / 1024
                })
        
        return models
    
    def _estimate_generation_time(self):
        """生成時間推定"""
        # 現在の生成時間（CPU環境）
        base_time = 600  # 10分（600秒）
        
        # システム性能による調整
        cpu_cores = self.system_info.get("cpu", {}).get("cores", 1)
        memory_gb = self.system_info.get("memory", {}).get("total", 0) / (1024**3)
        
        # 性能係数
        cpu_factor = max(0.5, 1.0 - (cpu_cores - 1) * 0.1)
        memory_factor = max(0.5, 1.0 - (memory_gb - 8) * 0.05)
        
        estimated_time = base_time * cpu_factor * memory_factor
        return max(300, estimated_time)  # 最低5分
    
    def _estimate_memory_usage(self):
        """メモリ使用量推定"""
        # 現在のモデルサイズ
        current_models = self._get_current_models()
        total_model_size = sum(model["size_gb"] for model in current_models)
        
        # 生成時のメモリ使用量（モデルサイズの1.5倍）
        generation_memory = total_model_size * 1.5
        
        # システムメモリとの比較
        available_memory = self.system_info.get("memory", {}).get("available", 0) / (1024**3)
        
        return {
            "model_size_gb": total_model_size,
            "generation_memory_gb": generation_memory,
            "available_gb": available_memory,
            "sufficient": generation_memory < available_memory
        }
    
    def _estimate_disk_usage(self):
        """ディスク使用量推定"""
        current_usage = self.system_info.get("disk", {}).get("percentage", 0)
        available_gb = self.system_info.get("disk", {}).get("free", 0) / (1024**3)
        
        return {
            "current_usage_percent": current_usage,
            "available_gb": available_gb,
            "status": "Good" if current_usage < 80 else "Warning" if current_usage < 90 else "Critical"
        }
    
    def analyze_upgrade_options(self):
        """アップグレードオプション分析"""
        return {
            "wan2_2": {
                "name": "WAN 2.2 (Waifu Diffusion 2.2)",
                "size_gb": 2.0,
                "quality": "High",
                "speed": "Medium",
                "compatibility": "Good",
                "recommendation": "Yes - Better quality than current models"
            },
            "sd_xl": {
                "name": "Stable Diffusion XL",
                "size_gb": 6.0,
                "quality": "Very High",
                "speed": "Slow",
                "compatibility": "Good",
                "recommendation": "Maybe - High quality but slow"
            },
            "sd3": {
                "name": "Stable Diffusion 3",
                "size_gb": 8.0,
                "quality": "Excellent",
                "speed": "Very Slow",
                "compatibility": "Limited",
                "recommendation": "No - Too heavy for CPU"
            },
            "lightweight_models": {
                "name": "Lightweight Models (TinySD, etc.)",
                "size_gb": 0.5,
                "quality": "Medium",
                "speed": "Fast",
                "compatibility": "Excellent",
                "recommendation": "Yes - Good balance"
            }
        }
    
    def generate_recommendations(self):
        """推奨事項生成"""
        memory_analysis = self.performance_metrics["memory_usage"]
        disk_analysis = self.performance_metrics["disk_usage"]
        upgrade_options = self.analyze_upgrade_options()
        
        recommendations = []
        
        # メモリ分析
        if not memory_analysis["sufficient"]:
            recommendations.append({
                "type": "warning",
                "message": "メモリ不足の可能性があります",
                "solution": "軽量モデルの使用を推奨"
            })
        
        # ディスク分析
        if disk_analysis["status"] == "Warning":
            recommendations.append({
                "type": "warning",
                "message": "ディスク容量が不足しています",
                "solution": "不要なファイルの削除を推奨"
            })
        elif disk_analysis["status"] == "Critical":
            recommendations.append({
                "type": "critical",
                "message": "ディスク容量が危険レベルです",
                "solution": "即座にファイル整理が必要"
            })
        
        # モデル推奨
        if memory_analysis["available_gb"] > 10:
            recommendations.append({
                "type": "recommendation",
                "message": "WAN 2.2の導入を推奨",
                "reason": "高品質で適度なサイズ"
            })
        else:
            recommendations.append({
                "type": "recommendation",
                "message": "軽量モデルの導入を推奨",
                "reason": "メモリ効率が良い"
            })
        
        return recommendations
    
    def print_analysis_report(self):
        """分析レポート表示"""
        print("🔍 Trinity Performance Analysis")
        print("=" * 80)
        
        # システム情報
        print(f"\n💻 システム情報:")
        print("-" * 50)
        cpu = self.system_info.get("cpu", {})
        memory = self.system_info.get("memory", {})
        disk = self.system_info.get("disk", {})
        gpu = self.system_info.get("gpu", {})
        
        print(f"  🖥️ CPU: {cpu.get('cores', 'Unknown')} cores, {cpu.get('threads', 'Unknown')} threads")
        print(f"  💾 メモリ: {memory.get('total', 0) / (1024**3):.1f}GB (使用率: {memory.get('percentage', 0):.1f}%)")
        print(f"  💿 ディスク: {disk.get('total', 0) / (1024**3):.1f}GB (使用率: {disk.get('percentage', 0):.1f}%)")
        print(f"  🎮 GPU: {gpu.get('type', 'None')} ({'利用可能' if gpu.get('available') else '利用不可'})")
        
        # 現在のモデル
        print(f"\n📦 現在のモデル:")
        print("-" * 50)
        models = self.performance_metrics["current_models"]
        total_size = sum(model["size_gb"] for model in models)
        print(f"  総サイズ: {total_size:.1f}GB")
        for model in models:
            print(f"  • {model['name']}: {model['size_gb']:.1f}GB")
        
        # 性能分析
        print(f"\n⚡ 性能分析:")
        print("-" * 50)
        generation_time = self.performance_metrics["generation_time"]
        memory_usage = self.performance_metrics["memory_usage"]
        disk_usage = self.performance_metrics["disk_usage"]
        
        print(f"  ⏱️ 推定生成時間: {generation_time/60:.1f}分")
        print(f"  💾 メモリ使用量: {memory_usage['generation_memory_gb']:.1f}GB")
        print(f"  💿 ディスク状況: {disk_usage['status']}")
        
        # アップグレードオプション
        print(f"\n🚀 アップグレードオプション:")
        print("-" * 50)
        upgrade_options = self.analyze_upgrade_options()
        for key, option in upgrade_options.items():
            print(f"\n📦 {option['name']}:")
            print(f"  サイズ: {option['size_gb']}GB")
            print(f"  品質: {option['quality']}")
            print(f"  速度: {option['speed']}")
            print(f"  推奨: {option['recommendation']}")
        
        # 推奨事項
        print(f"\n💡 推奨事項:")
        print("-" * 50)
        recommendations = self.generate_recommendations()
        for rec in recommendations:
            icon = "⚠️" if rec["type"] == "warning" else "🚨" if rec["type"] == "critical" else "✅"
            print(f"  {icon} {rec['message']}")
            print(f"     → {rec.get('solution', rec.get('reason', ''))}")


def main():
    """メイン関数"""
    analyzer = PerformanceAnalyzer()
    analyzer.print_analysis_report()


if __name__ == "__main__":
    main()
