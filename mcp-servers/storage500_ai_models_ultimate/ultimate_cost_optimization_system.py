#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
究極のAPI使用料金最適化システム
すべての最適化機能を統合した包括的なシステム
"""

import os
import json
import time
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import threading
import logging
import subprocess
import schedule

class UltimateCostOptimizationSystem:
    """究極のAPI使用料金最適化システム"""
    
    def __init__(self):
        self.setup_logging()
        self.setup_directories()
        
        # 各システムのインポート
        try:
            from api_cost_optimization import APICostOptimizer
            from api_cache_system import APICacheSystem
            from api_usage_monitor import APIUsageMonitor
            from advanced_cost_optimizer import AdvancedCostOptimizer
            
            self.cost_optimizer = APICostOptimizer()
            self.cache_system = APICacheSystem()
            self.usage_monitor = APIUsageMonitor()
            self.advanced_optimizer = AdvancedCostOptimizer()
            
            self.systems_loaded = True
        except ImportError as e:
            self.logger.error(f"システムの読み込みに失敗: {e}")
            self.systems_loaded = False
    
    def setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/mnt/data/ultimate_cost_optimization.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_directories(self):
        """ディレクトリ設定"""
        directories = [
            "/mnt/data/logs",
            "/mnt/data/cache",
            "/mnt/data/db"
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                self.logger.info(f"ディレクトリを作成: {directory}")
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """包括的な分析を実行"""
        self.logger.info("包括的なAPI使用料金分析を開始")
        
        analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "systems": {},
            "recommendations": [],
            "savings": 0.0
        }
        
        if not self.systems_loaded:
            analysis_results["error"] = "システムの読み込みに失敗"
            return analysis_results
        
        # 1. 基本コスト最適化
        try:
            status = self.cost_optimizer.get_usage_status()
            analysis_results["systems"]["basic_optimization"] = {
                "status": "success",
                "data": status
            }
        except Exception as e:
            analysis_results["systems"]["basic_optimization"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 2. キャッシュシステム
        try:
            cache_stats = self.cache_system.get_cache_stats()
            analysis_results["systems"]["cache_system"] = {
                "status": "success",
                "data": cache_stats
            }
        except Exception as e:
            analysis_results["systems"]["cache_system"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 3. 使用量監視
        try:
            usage_stats = self.usage_monitor.get_usage_stats()
            analysis_results["systems"]["usage_monitor"] = {
                "status": "success",
                "data": usage_stats
            }
        except Exception as e:
            analysis_results["systems"]["usage_monitor"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 4. 高度な最適化
        try:
            advanced_results, advanced_report = self.advanced_optimizer.run_full_optimization()
            analysis_results["systems"]["advanced_optimization"] = {
                "status": "success",
                "data": advanced_results,
                "report": advanced_report
            }
        except Exception as e:
            analysis_results["systems"]["advanced_optimization"] = {
                "status": "error",
                "error": str(e)
            }
        
        # 推奨事項を生成
        analysis_results["recommendations"] = self.generate_recommendations(analysis_results)
        
        # 節約額を計算
        analysis_results["savings"] = self.calculate_total_savings(analysis_results)
        
        return analysis_results
    
    def generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        # 基本推奨事項
        recommendations.append("✅ 無料枠を最大限活用")
        recommendations.append("✅ キャッシュシステムを有効活用")
        recommendations.append("✅ 使用量を継続的に監視")
        
        # システム固有の推奨事項
        if "basic_optimization" in analysis_results["systems"]:
            basic_data = analysis_results["systems"]["basic_optimization"].get("data", {})
            for api_name, info in basic_data.items():
                if info.get("enabled", False):
                    usage_percentage = info.get("usage_percentage", 0)
                    if usage_percentage > 80:
                        recommendations.append(f"⚠️ {api_name}の使用量が80%を超えています")
        
        if "cache_system" in analysis_results["systems"]:
            cache_data = analysis_results["systems"]["cache_system"].get("data", {})
            for api_name, stats in cache_data.items():
                cache_count = stats.get("cache_count", 0)
                max_size = stats.get("max_size", 0)
                if cache_count > max_size * 0.8:
                    recommendations.append(f"💾 {api_name}のキャッシュが80%に達しています")
        
        return recommendations
    
    def calculate_total_savings(self, analysis_results: Dict[str, Any]) -> float:
        """総節約額を計算"""
        total_savings = 0.0
        
        # 基本最適化からの節約
        if "basic_optimization" in analysis_results["systems"]:
            basic_data = analysis_results["systems"]["basic_optimization"].get("data", {})
            for api_name, info in basic_data.items():
                if not info.get("enabled", False):
                    # 無効化されたAPIの節約額
                    if api_name == "x_twitter":
                        total_savings += 15000  # ¥15,000/月
                    elif api_name == "instagram":
                        total_savings += 7500   # ¥7,500/月
        
        # 高度な最適化からの節約
        if "advanced_optimization" in analysis_results["systems"]:
            advanced_data = analysis_results["systems"]["advanced_optimization"].get("data", {})
            for api_name, result in advanced_data.items():
                if result.get("success", False):
                    savings = result.get("savings", 0.0)
                    total_savings += savings
        
        return total_savings
    
    def generate_comprehensive_report(self, analysis_results: Dict[str, Any]) -> str:
        """包括的なレポートを生成"""
        report = "🚀 究極のAPI使用料金最適化レポート\n"
        report += "=" * 60 + "\n\n"
        
        # 基本情報
        report += f"📅 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"💰 総節約額: ¥{analysis_results['savings']:,.0f}/月\n\n"
        
        # システム状況
        report += "🔧 システム状況:\n"
        for system_name, system_data in analysis_results["systems"].items():
            status = system_data.get("status", "unknown")
            if status == "success":
                report += f"  ✅ {system_name}: 正常動作\n"
            else:
                error = system_data.get("error", "不明なエラー")
                report += f"  ❌ {system_name}: エラー - {error}\n"
        
        report += "\n"
        
        # 推奨事項
        report += "🎯 推奨事項:\n"
        for recommendation in analysis_results.get("recommendations", []):
            report += f"  {recommendation}\n"
        
        report += "\n"
        
        # 詳細分析
        if "basic_optimization" in analysis_results["systems"]:
            basic_data = analysis_results["systems"]["basic_optimization"].get("data", {})
            if basic_data:
                report += "📊 詳細分析:\n"
                for api_name, info in basic_data.items():
                    if info.get("enabled", False):
                        usage_percentage = info.get("usage_percentage", 0)
                        report += f"  {api_name}: {info['current_usage']}/{info['daily_limit']} ({usage_percentage:.1f}%)\n"
                    else:
                        report += f"  {api_name}: 無効化済み\n"
        
        report += "\n" + "=" * 60 + "\n"
        report += "✅ 最適化完了\n"
        
        return report
    
    def run_automated_optimization(self):
        """自動最適化を実行"""
        self.logger.info("自動最適化を開始")
        
        # 包括的な分析を実行
        analysis_results = self.run_comprehensive_analysis()
        
        # レポートを生成
        report = self.generate_comprehensive_report(analysis_results)
        
        # レポートを保存
        report_file = f"/mnt/data/logs/ultimate_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # 分析結果も保存
        results_file = f"/mnt/data/logs/ultimate_optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"レポートを保存: {report_file}")
        self.logger.info(f"結果を保存: {results_file}")
        
        return analysis_results, report
    
    def start_continuous_monitoring(self):
        """継続的監視を開始"""
        self.logger.info("継続的監視を開始")
        
        def monitoring_job():
            try:
                self.run_automated_optimization()
            except Exception as e:
                self.logger.error(f"監視ジョブでエラーが発生: {e}")
        
        # 毎時間実行
        schedule.every().hour.do(monitoring_job)
        
        # 初回実行
        monitoring_job()
        
        # スケジュールループ
        while True:
            schedule.run_pending()
            time.sleep(60)  # 1分ごとにチェック
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム状況を取得"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "systems": {},
            "overall_status": "unknown"
        }
        
        if not self.systems_loaded:
            status["overall_status"] = "error"
            status["error"] = "システムの読み込みに失敗"
            return status
        
        # 各システムの状況をチェック
        systems_status = []
        
        try:
            self.cost_optimizer.get_usage_status()
            systems_status.append("basic_optimization")
        except:
            pass
        
        try:
            self.cache_system.get_cache_stats()
            systems_status.append("cache_system")
        except:
            pass
        
        try:
            self.usage_monitor.get_usage_stats()
            systems_status.append("usage_monitor")
        except:
            pass
        
        try:
            self.advanced_optimizer.get_current_usage("youtube")
            systems_status.append("advanced_optimization")
        except:
            pass
        
        status["systems"] = systems_status
        
        if len(systems_status) == 4:
            status["overall_status"] = "healthy"
        elif len(systems_status) > 0:
            status["overall_status"] = "partial"
        else:
            status["overall_status"] = "error"
        
        return status

def create_ultimate_system():
    """究極のシステムを作成"""
    system = UltimateCostOptimizationSystem()
    return system

if __name__ == "__main__":
    print("🚀 究極のAPI使用料金最適化システムを初期化中...")
    
    # システムを作成
    ultimate_system = create_ultimate_system()
    
    # システム状況を確認
    status = ultimate_system.get_system_status()
    print(f"\n📊 システム状況: {status['overall_status']}")
    
    if status["overall_status"] == "error":
        print("❌ システムの初期化に失敗しました")
        exit(1)
    
    # 自動最適化を実行
    results, report = ultimate_system.run_automated_optimization()
    
    print("\n" + report)
    print("\n✅ 究極の最適化システムの初期化完了")
    
    # 継続的監視のオプション
    print("\n💡 継続的監視を開始するには: ultimate_system.start_continuous_monitoring()")
