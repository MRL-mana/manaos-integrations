#!/usr/bin/env python3
"""
System Status Report
Trinity AI システム全体の状況レポート
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
import psutil

class SystemStatusReport:
    def __init__(self):
        self.models_dir = Path("/root/civitai_models")
        self.output_dir = Path("/root/trinity_workspace/generated_images")
        self.workspace_dir = Path("/root/trinity_workspace")
        
    def get_system_info(self):
        """システム情報取得"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "memory": {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total / (1024**3),
                "free_gb": disk.free / (1024**3),
                "used_percent": (disk.used / disk.total) * 100
            },
            "cpu": {
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
                "usage_percent": cpu_percent
            }
        }
    
    def get_models_status(self):
        """モデル状況取得"""
        models = {}
        
        if self.models_dir.exists():
            for model_file in self.models_dir.glob("*.safetensors"):
                info_file = model_file.with_suffix('.json')
                
                model_info = {
                    "name": model_file.stem,
                    "size_mb": model_file.stat().st_size / (1024 * 1024),
                    "modified": datetime.fromtimestamp(model_file.stat().st_mtime).isoformat()
                }
                
                if info_file.exists():
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info_data = json.load(f)
                        model_info["civitai_info"] = {
                            "name": info_data.get('name', ''),
                            "type": info_data.get('type', ''),
                            "description": info_data.get('description', '')[:100] + "..." if info_data.get('description') else ""
                        }
                    except:
                        pass
                
                models[model_file.stem] = model_info
        
        return models
    
    def get_generated_images_status(self):
        """生成画像状況取得"""
        images = []
        
        if self.output_dir.exists():
            for image_file in self.output_dir.glob("*.png"):
                image_info = {
                    "name": image_file.name,
                    "size_mb": image_file.stat().st_size / (1024 * 1024),
                    "created": datetime.fromtimestamp(image_file.stat().st_mtime).isoformat()
                }
                images.append(image_info)
        
        # 作成日時順でソート
        images.sort(key=lambda x: x['created'], reverse=True)
        return images
    
    def get_workspace_status(self):
        """ワークスペース状況取得"""
        tools = []
        
        if self.workspace_dir.exists():
            tools_dir = self.workspace_dir / "tools"
            if tools_dir.exists():
                for tool_file in tools_dir.glob("*.py"):
                    tool_info = {
                        "name": tool_file.name,
                        "size_kb": tool_file.stat().st_size / 1024,
                        "modified": datetime.fromtimestamp(tool_file.stat().st_mtime).isoformat()
                    }
                    tools.append(tool_info)
        
        return tools
    
    def generate_report(self):
        """レポート生成"""
        print("📊 Trinity AI System Status Report")
        print("=" * 80)
        print(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # システム情報
        system_info = self.get_system_info()
        print("💻 システム情報:")
        print("-" * 40)
        print(f"メモリ: {system_info['memory']['total_gb']:.1f}GB (使用率: {system_info['memory']['used_percent']:.1f}%)")
        print(f"ディスク: {system_info['disk']['total_gb']:.1f}GB (使用率: {system_info['disk']['used_percent']:.1f}%)")
        print(f"CPU: {system_info['cpu']['cores']} cores, {system_info['cpu']['threads']} threads (使用率: {system_info['cpu']['usage_percent']:.1f}%)")
        print()
        
        # モデル状況
        models = self.get_models_status()
        print("🎨 AIモデル状況:")
        print("-" * 40)
        if models:
            total_size = sum(model['size_mb'] for model in models.values())
            print(f"総モデル数: {len(models)}")
            print(f"総サイズ: {total_size:.1f}MB")
            print()
            for model_name, model_info in models.items():
                print(f"📦 {model_name}:")
                print(f"   サイズ: {model_info['size_mb']:.1f}MB")
                print(f"   更新日: {model_info['modified'][:19]}")
                if 'civitai_info' in model_info:
                    print(f"   名前: {model_info['civitai_info']['name']}")
                print()
        else:
            print("❌ モデルが見つかりません")
        print()
        
        # 生成画像状況
        images = self.get_generated_images_status()
        print("🖼️ 生成画像状況:")
        print("-" * 40)
        if images:
            total_size = sum(img['size_mb'] for img in images)
            print(f"総画像数: {len(images)}")
            print(f"総サイズ: {total_size:.1f}MB")
            print()
            print("最新の画像:")
            for img in images[:5]:  # 最新5枚
                print(f"  📸 {img['name']} ({img['size_mb']:.1f}MB) - {img['created'][:19]}")
        else:
            print("❌ 生成された画像がありません")
        print()
        
        # ワークスペース状況
        tools = self.get_workspace_status()
        print("🛠️ ワークスペース状況:")
        print("-" * 40)
        if tools:
            print(f"ツール数: {len(tools)}")
            print("主要ツール:")
            for tool in tools[:10]:  # 最新10個
                print(f"  🔧 {tool['name']} ({tool['size_kb']:.1f}KB) - {tool['modified'][:19]}")
        else:
            print("❌ ツールが見つかりません")
        print()
        
        # 総合評価
        print("📈 総合評価:")
        print("-" * 40)
        
        # メモリ使用率評価
        memory_usage = system_info['memory']['used_percent']
        if memory_usage < 50:
            memory_status = "✅ 良好"
        elif memory_usage < 80:
            memory_status = "⚠️ 注意"
        else:
            memory_status = "❌ 危険"
        
        # ディスク使用率評価
        disk_usage = system_info['disk']['used_percent']
        if disk_usage < 70:
            disk_status = "✅ 良好"
        elif disk_usage < 90:
            disk_status = "⚠️ 注意"
        else:
            disk_status = "❌ 危険"
        
        # モデル状況評価
        if len(models) >= 3:
            model_status = "✅ 充実"
        elif len(models) >= 1:
            model_status = "⚠️ 最低限"
        else:
            model_status = "❌ 不足"
        
        # 生成画像状況評価
        if len(images) >= 5:
            image_status = "✅ 活発"
        elif len(images) >= 1:
            image_status = "⚠️ 少ない"
        else:
            image_status = "❌ なし"
        
        print(f"メモリ使用率: {memory_status} ({memory_usage:.1f}%)")
        print(f"ディスク使用率: {disk_status} ({disk_usage:.1f}%)")
        print(f"AIモデル: {model_status} ({len(models)}個)")
        print(f"生成画像: {image_status} ({len(images)}枚)")
        print()
        
        # 推奨事項
        print("💡 推奨事項:")
        print("-" * 40)
        
        recommendations = []
        
        if memory_usage > 80:
            recommendations.append("メモリ使用率が高いです。不要なプロセスを終了してください。")
        
        if disk_usage > 90:
            recommendations.append("ディスク使用率が高いです。古いファイルを削除してください。")
        
        if len(models) < 3:
            recommendations.append("AIモデルが少ないです。追加のモデルをダウンロードしてください。")
        
        if len(images) == 0:
            recommendations.append("生成画像がありません。画像生成を実行してください。")
        
        if not recommendations:
            recommendations.append("システムは正常に動作しています。")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        print()
        print("🎉 Trinity AI System Status Report 完了")


def main():
    """メイン関数"""
    reporter = SystemStatusReport()
    reporter.generate_report()


if __name__ == "__main__":
    main()


