#!/usr/bin/env python3
"""
Trinity AI Advanced Analytics System
高度な分析システム
"""

import os
import json
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from collections import defaultdict, Counter

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedAnalyticsSystem:
    def __init__(self):
        self.data_dir = "/root/trinity_workspace/analytics"
        self.reports_dir = os.path.join(self.data_dir, "reports")
        self.charts_dir = os.path.join(self.data_dir, "charts")
        
        # ディレクトリを作成
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.charts_dir, exist_ok=True)
        
        # データファイル
        self.generation_log = os.path.join(self.data_dir, "generation_log.json")
        self.performance_log = os.path.join(self.data_dir, "performance_log.json")
        self.user_behavior_log = os.path.join(self.data_dir, "user_behavior_log.json")
        
        # データを初期化
        self._initialize_data()
    
    def _initialize_data(self):
        """データファイルを初期化"""
        if not os.path.exists(self.generation_log):
            with open(self.generation_log, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(self.performance_log):
            with open(self.performance_log, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(self.user_behavior_log):
            with open(self.user_behavior_log, 'w') as f:
                json.dump([], f)
    
    def log_generation(self, prompt: str, style: str, success: bool, 
                      generation_time: float, file_size: int = 0):
        """画像生成ログを記録"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "style": style,
            "success": success,
            "generation_time": generation_time,
            "file_size": file_size
        }
        
        self._append_to_log(self.generation_log, entry)
        logger.info(f"📊 生成ログ記録: {style} - {generation_time:.1f}秒")
    
    def log_performance(self, cpu_percent: float, memory_percent: float, 
                       disk_percent: float, gpu_percent: float = 0):
        """パフォーマンスログを記録"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "gpu_percent": gpu_percent
        }
        
        self._append_to_log(self.performance_log, entry)
    
    def log_user_behavior(self, action: str, details: Dict = None):
        """ユーザー行動ログを記録"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {}
        }
        
        self._append_to_log(self.user_behavior_log, entry)
    
    def _append_to_log(self, log_file: str, entry: Dict):
        """ログファイルにエントリを追加"""
        try:
            with open(log_file, 'r') as f:
                data = json.load(f)
            
            data.append(entry)
            
            # 最新1000件のみ保持
            if len(data) > 1000:
                data = data[-1000:]
            
            with open(log_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"ログ記録エラー: {e}")
    
    def generate_generation_analytics(self) -> Dict:
        """生成分析レポートを生成"""
        try:
            with open(self.generation_log, 'r') as f:
                generations = json.load(f)
            
            if not generations:
                return {"error": "データがありません"}
            
            # 基本統計
            total_generations = len(generations)
            successful = sum(1 for g in generations if g.get("success", False))
            failed = total_generations - successful
            success_rate = (successful / total_generations) * 100 if total_generations > 0 else 0
            
            # 生成時間分析
            generation_times = [g.get("generation_time", 0) for g in generations if g.get("generation_time")]
            avg_time = sum(generation_times) / len(generation_times) if generation_times else 0
            min_time = min(generation_times) if generation_times else 0
            max_time = max(generation_times) if generation_times else 0
            
            # スタイル分析
            styles = [g.get("style", "unknown") for g in generations]
            style_counts = Counter(styles)
            most_popular_style = style_counts.most_common(1)[0] if style_counts else ("unknown", 0)
            
            # プロンプト分析
            prompts = [g.get("prompt", "") for g in generations]
            prompt_lengths = [len(p.split()) for p in prompts]
            avg_prompt_length = sum(prompt_lengths) / len(prompt_lengths) if prompt_lengths else 0
            
            # 時間別分析（過去24時間）
            now = datetime.now()
            recent_generations = [
                g for g in generations 
                if datetime.fromisoformat(g["timestamp"]) > now - timedelta(hours=24)
            ]
            
            return {
                "summary": {
                    "total_generations": total_generations,
                    "successful": successful,
                    "failed": failed,
                    "success_rate": round(success_rate, 2)
                },
                "performance": {
                    "average_time": round(avg_time, 2),
                    "min_time": round(min_time, 2),
                    "max_time": round(max_time, 2)
                },
                "popularity": {
                    "most_popular_style": most_popular_style[0],
                    "style_usage": dict(style_counts.most_common(5))
                },
                "prompts": {
                    "average_length": round(avg_prompt_length, 1),
                    "total_prompts": len(prompts)
                },
                "recent_activity": {
                    "last_24h": len(recent_generations),
                    "timestamp": now.isoformat()
                }
            }
        except Exception as e:
            logger.error(f"生成分析エラー: {e}")
            return {"error": str(e)}
    
    def generate_performance_analytics(self) -> Dict:
        """パフォーマンス分析レポートを生成"""
        try:
            with open(self.performance_log, 'r') as f:
                performance_data = json.load(f)
            
            if not performance_data:
                return {"error": "パフォーマンスデータがありません"}
            
            # 最新100件のデータを使用
            recent_data = performance_data[-100:] if len(performance_data) > 100 else performance_data
            
            # CPU分析
            cpu_values = [p.get("cpu_percent", 0) for p in recent_data]
            avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            max_cpu = max(cpu_values) if cpu_values else 0
            
            # メモリ分析
            memory_values = [p.get("memory_percent", 0) for p in recent_data]
            avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
            max_memory = max(memory_values) if memory_values else 0
            
            # ディスク分析
            disk_values = [p.get("disk_percent", 0) for p in recent_data]
            avg_disk = sum(disk_values) / len(disk_values) if disk_values else 0
            max_disk = max(disk_values) if disk_values else 0
            
            # システム状態判定
            system_status = "healthy"
            if avg_cpu > 80 or avg_memory > 90 or avg_disk > 95:
                system_status = "warning"
            if max_cpu > 95 or max_memory > 98 or max_disk > 98:
                system_status = "critical"
            
            return {
                "system_status": system_status,
                "cpu": {
                    "average": round(avg_cpu, 2),
                    "maximum": round(max_cpu, 2),
                    "current": cpu_values[-1] if cpu_values else 0
                },
                "memory": {
                    "average": round(avg_memory, 2),
                    "maximum": round(max_memory, 2),
                    "current": memory_values[-1] if memory_values else 0
                },
                "disk": {
                    "average": round(avg_disk, 2),
                    "maximum": round(max_disk, 2),
                    "current": disk_values[-1] if disk_values else 0
                },
                "recommendations": self._get_performance_recommendations(avg_cpu, avg_memory, avg_disk)
            }
        except Exception as e:
            logger.error(f"パフォーマンス分析エラー: {e}")
            return {"error": str(e)}
    
    def _get_performance_recommendations(self, avg_cpu: float, avg_memory: float, avg_disk: float) -> List[str]:
        """パフォーマンス改善推奨事項を取得"""
        recommendations = []
        
        if avg_cpu > 80:
            recommendations.append("CPU使用率が高いです。並列処理数を減らすか、より強力なCPUを検討してください。")
        
        if avg_memory > 85:
            recommendations.append("メモリ使用率が高いです。モデルのメモリ最適化を検討してください。")
        
        if avg_disk > 90:
            recommendations.append("ディスク使用率が高いです。古いファイルの削除やストレージの拡張を検討してください。")
        
        if not recommendations:
            recommendations.append("システムは良好な状態です。")
        
        return recommendations
    
    def generate_user_behavior_analytics(self) -> Dict:
        """ユーザー行動分析レポートを生成"""
        try:
            with open(self.user_behavior_log, 'r') as f:
                behavior_data = json.load(f)
            
            if not behavior_data:
                return {"error": "ユーザー行動データがありません"}
            
            # 行動分析
            actions = [b.get("action", "unknown") for b in behavior_data]
            action_counts = Counter(actions)
            
            # 時間別分析
            hourly_activity = defaultdict(int)
            for entry in behavior_data:
                timestamp = datetime.fromisoformat(entry["timestamp"])
                hour = timestamp.hour
                hourly_activity[hour] += 1
            
            # 最も活発な時間帯
            most_active_hour = max(hourly_activity.items(), key=lambda x: x[1]) if hourly_activity else (0, 0)
            
            return {
                "total_actions": len(behavior_data),
                "action_breakdown": dict(action_counts.most_common(10)),
                "activity_patterns": {
                    "most_active_hour": most_active_hour[0],
                    "hourly_distribution": dict(hourly_activity)
                },
                "recent_activity": {
                    "last_24h": len([b for b in behavior_data 
                                   if datetime.fromisoformat(b["timestamp"]) > datetime.now() - timedelta(hours=24)])
                }
            }
        except Exception as e:
            logger.error(f"ユーザー行動分析エラー: {e}")
            return {"error": str(e)}
    
    def create_performance_chart(self):
        """パフォーマンスチャートを作成"""
        try:
            with open(self.performance_log, 'r') as f:
                performance_data = json.load(f)
            
            if not performance_data:
                logger.warning("パフォーマンスデータがありません")
                return None
            
            # 最新50件のデータを使用
            recent_data = performance_data[-50:] if len(performance_data) > 50 else performance_data
            
            # データを準備
            timestamps = [datetime.fromisoformat(p["timestamp"]) for p in recent_data]
            cpu_values = [p.get("cpu_percent", 0) for p in recent_data]
            memory_values = [p.get("memory_percent", 0) for p in recent_data]
            disk_values = [p.get("disk_percent", 0) for p in recent_data]
            
            # チャートを作成
            plt.figure(figsize=(12, 8))
            plt.plot(timestamps, cpu_values, label='CPU %', linewidth=2)
            plt.plot(timestamps, memory_values, label='Memory %', linewidth=2)
            plt.plot(timestamps, disk_values, label='Disk %', linewidth=2)
            
            plt.title('Trinity AI System Performance', fontsize=16, fontweight='bold')
            plt.xlabel('Time', fontsize=12)
            plt.ylabel('Usage %', fontsize=12)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # チャートを保存
            chart_path = os.path.join(self.charts_dir, f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 パフォーマンスチャート作成: {chart_path}")
            return chart_path
        except Exception as e:
            logger.error(f"チャート作成エラー: {e}")
            return None
    
    def generate_comprehensive_report(self) -> Dict:
        """包括的分析レポートを生成"""
        logger.info("📊 包括的分析レポート生成開始")
        
        # 各分析を実行
        generation_analytics = self.generate_generation_analytics()
        performance_analytics = self.generate_performance_analytics()
        behavior_analytics = self.generate_user_behavior_analytics()
        
        # チャートを作成
        chart_path = self.create_performance_chart()
        
        # レポートを統合
        comprehensive_report = {
            "timestamp": datetime.now().isoformat(),
            "generation_analytics": generation_analytics,
            "performance_analytics": performance_analytics,
            "behavior_analytics": behavior_analytics,
            "chart_path": chart_path,
            "summary": {
                "total_generations": generation_analytics.get("summary", {}).get("total_generations", 0),
                "success_rate": generation_analytics.get("summary", {}).get("success_rate", 0),
                "system_status": performance_analytics.get("system_status", "unknown"),
                "total_actions": behavior_analytics.get("total_actions", 0)
            }
        }
        
        # レポートを保存
        report_path = os.path.join(self.reports_dir, f"comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w') as f:
            json.dump(comprehensive_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 包括的分析レポート生成完了: {report_path}")
        return comprehensive_report
    
    def start_monitoring(self, interval: int = 60):
        """システム監視を開始"""
        logger.info(f"🔍 システム監視開始 (間隔: {interval}秒)")
        
        while True:
            try:
                # システム情報を取得
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # パフォーマンスログを記録
                self.log_performance(
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    disk_percent=(disk.used / disk.total) * 100
                )
                
                logger.info(f"📊 監視データ記録: CPU {cpu_percent:.1f}%, Memory {memory.percent:.1f}%, Disk {(disk.used/disk.total)*100:.1f}%")
                
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("🔍 システム監視停止")
                break
            except Exception as e:
                logger.error(f"監視エラー: {e}")
                time.sleep(interval)

def main():
    """メイン実行関数"""
    print("📊 Trinity AI Advanced Analytics System")
    print("=" * 60)
    
    analytics = AdvancedAnalyticsSystem()
    
    # サンプルデータを生成
    print("📊 サンプルデータ生成中...")
    analytics.log_generation("a beautiful anime girl", "anime", True, 3.2, 1024000)
    analytics.log_generation("a professional woman", "realistic", True, 4.1, 2048000)
    analytics.log_generation("a fantasy character", "fantasy", False, 0, 0)
    
    analytics.log_user_behavior("image_generation", {"style": "anime", "success": True})
    analytics.log_user_behavior("style_transfer", {"style": "cyberpunk"})
    analytics.log_user_behavior("gallery_view", {"images_viewed": 5})
    
    # 現在のシステム状態を記録
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    analytics.log_performance(cpu_percent, memory.percent, (disk.used / disk.total) * 100)
    
    # 分析レポートを生成
    print("📊 分析レポート生成中...")
    report = analytics.generate_comprehensive_report()
    
    print(f"\n🎉 分析レポート生成完了!")
    print(f"   総生成数: {report['summary']['total_generations']}")
    print(f"   成功率: {report['summary']['success_rate']}%")
    print(f"   システム状態: {report['summary']['system_status']}")
    print(f"   総アクション数: {report['summary']['total_actions']}")
    
    if report.get('chart_path'):
        print(f"   チャート: {report['chart_path']}")

if __name__ == "__main__":
    main()
