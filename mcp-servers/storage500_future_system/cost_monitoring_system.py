#!/usr/bin/env python3
"""
💰 API使用量・コスト監視システム
API使用量とコストをリアルタイムで監視・可視化
"""

import asyncio
import json
import logging
import random
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List
from dataclasses import dataclass
import numpy as np

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@dataclass
class APICost:
    """APIコスト情報"""
    api_name: str
    requests_per_hour: int
    cost_per_request: float
    total_cost: float
    usage_limit: int
    usage_percentage: float

@dataclass
class SystemCost:
    """システムコスト情報"""
    total_cost: float
    cost_per_hour: float
    cost_per_day: float
    cost_per_month: float
    budget_remaining: float
    budget_usage_percentage: float

class CostMonitoringSystem:
    """コスト監視システム"""
    
    def __init__(self):
        self.api_costs = {
            'gemini_api': {
                'name': 'Gemini API',
                'cost_per_1k_tokens': 0.0005,  # $0.0005 per 1K tokens
                'usage_limit': 15000000,  # 15M tokens/month
                'current_usage': 0,
                'requests_per_hour': 0
            },
            'openai_api': {
                'name': 'OpenAI API',
                'cost_per_1k_tokens': 0.002,  # $0.002 per 1K tokens
                'usage_limit': 5000000,  # 5M tokens/month
                'current_usage': 0,
                'requests_per_hour': 0
            },
            'anthropic_api': {
                'name': 'Anthropic API',
                'cost_per_1k_tokens': 0.0015,  # $0.0015 per 1K tokens
                'usage_limit': 10000000,  # 10M tokens/month
                'current_usage': 0,
                'requests_per_hour': 0
            },
            'quantum_api': {
                'name': 'Quantum API',
                'cost_per_request': 0.01,  # $0.01 per request
                'usage_limit': 100000,  # 100K requests/month
                'current_usage': 0,
                'requests_per_hour': 0
            }
        }
        
        self.monthly_budget = 1000.0  # $1000/month
        self.current_month_cost = 0.0
        self.results = []
        self.is_running = False
    
    async def initialize(self):
        """システム初期化"""
        logger.info("💰 API使用量・コスト監視システム初期化中...")
        
        for api_name, api_info in self.api_costs.items():
            logger.info(f"📊 {api_info['name']} 監視開始")
        
        self.is_running = True
        logger.info("✅ コスト監視システム準備完了")
    
    async def simulate_api_usage(self):
        """API使用量シミュレーション"""
        logger.info("📈 API使用量シミュレーション開始")
        
        for api_name, api_info in self.api_costs.items():
            # 時間あたりのリクエスト数シミュレーション
            requests_per_hour = random.randint(10, 100)
            api_info['requests_per_hour'] = requests_per_hour
            
            # トークン使用量シミュレーション
            if 'cost_per_1k_tokens' in api_info:
                tokens_per_request = random.randint(100, 1000)
                total_tokens = requests_per_hour * tokens_per_request
                cost_per_request = (tokens_per_request / 1000) * api_info['cost_per_1k_tokens']
                total_cost = requests_per_hour * cost_per_request
                
                api_info['current_usage'] += total_tokens
                usage_percentage = (api_info['current_usage'] / api_info['usage_limit']) * 100
                
                cost_info = APICost(
                    api_name=api_info['name'],
                    requests_per_hour=requests_per_hour,
                    cost_per_request=cost_per_request,
                    total_cost=total_cost,
                    usage_limit=api_info['usage_limit'],
                    usage_percentage=usage_percentage
                )
            else:
                # 固定コストのAPI
                total_cost = requests_per_hour * api_info['cost_per_request']
                api_info['current_usage'] += requests_per_hour
                usage_percentage = (api_info['current_usage'] / api_info['usage_limit']) * 100
                
                cost_info = APICost(
                    api_name=api_info['name'],
                    requests_per_hour=requests_per_hour,
                    cost_per_request=api_info['cost_per_request'],
                    total_cost=total_cost,
                    usage_limit=api_info['usage_limit'],
                    usage_percentage=usage_percentage
                )
            
            self.results.append({
                'timestamp': datetime.now().isoformat(),
                'api_name': api_name,
                'cost_info': cost_info
            })
            
            logger.info(f"💰 {api_info['name']}: {requests_per_hour} req/h, ${total_cost:.4f}/h, {usage_percentage:.1f}%使用")
    
    async def calculate_system_cost(self) -> SystemCost:
        """システム全体のコスト計算"""
        total_cost_per_hour = sum(api['requests_per_hour'] * api.get('cost_per_request', 0.001) for api in self.api_costs.values())
        cost_per_day = total_cost_per_hour * 24
        cost_per_month = cost_per_day * 30
        
        self.current_month_cost += total_cost_per_hour
        budget_remaining = self.monthly_budget - self.current_month_cost
        budget_usage_percentage = (self.current_month_cost / self.monthly_budget) * 100
        
        return SystemCost(
            total_cost=total_cost_per_hour,
            cost_per_hour=total_cost_per_hour,
            cost_per_day=cost_per_day,
            cost_per_month=cost_per_month,
            budget_remaining=budget_remaining,
            budget_usage_percentage=budget_usage_percentage
        )
    
    async def show_cost_dashboard(self):
        """コストダッシュボード表示"""
        system_cost = await self.calculate_system_cost()
        
        logger.info("=" * 60)
        logger.info("💰 API使用量・コストダッシュボード")
        logger.info("=" * 60)
        
        # 各APIの使用状況
        for api_name, api_info in self.api_costs.items():
            usage_percentage = (api_info['current_usage'] / api_info['usage_limit']) * 100
            logger.info(f"📊 {api_info['name']}:")
            logger.info(f"   - リクエスト/時: {api_info['requests_per_hour']}")
            logger.info(f"   - 使用量: {api_info['current_usage']:,} / {api_info['usage_limit']:,}")
            logger.info(f"   - 使用率: {usage_percentage:.1f}%")
        
        logger.info("-" * 60)
        logger.info("💰 コスト概要:")
        logger.info(f"   - 時間あたり: ${system_cost.cost_per_hour:.4f}")
        logger.info(f"   - 日あたり: ${system_cost.cost_per_day:.2f}")
        logger.info(f"   - 月あたり: ${system_cost.cost_per_month:.2f}")
        logger.info(f"   - 予算残高: ${system_cost.budget_remaining:.2f}")
        logger.info(f"   - 予算使用率: {system_cost.budget_usage_percentage:.1f}%")
        
        # 警告表示
        if system_cost.budget_usage_percentage > 80:
            logger.warning("⚠️  予算使用率が80%を超えています！")
        if system_cost.budget_usage_percentage > 95:
            logger.error("🚨 予算使用率が95%を超えています！緊急対応が必要です！")
        
        logger.info("=" * 60)
    
    async def continuous_cost_monitoring(self):
        """継続的コスト監視"""
        logger.info("🔄 継続的コスト監視開始")
        
        cycle_count = 0
        
        while self.is_running:
            try:
                # API使用量シミュレーション
                await self.simulate_api_usage()
                
                cycle_count += 1
                
                # 定期的なダッシュボード表示
                if cycle_count % 5 == 0:
                    await self.show_cost_dashboard()
                
                await asyncio.sleep(10)  # 10秒間隔
                
            except KeyboardInterrupt:
                logger.info("⏹️ 継続的コスト監視停止")
                break
            except Exception as e:
                logger.error(f"❌ エラー: {e}")
                await asyncio.sleep(15)
    
    async def get_cost_statistics(self) -> Dict[str, Any]:
        """コスト統計情報取得"""
        if not self.results:
            return {}
        
        total_requests = sum(r['cost_info'].requests_per_hour for r in self.results)
        total_cost = sum(r['cost_info'].total_cost for r in self.results)
        avg_usage_percentage = sum(r['cost_info'].usage_percentage for r in self.results) / len(self.results)
        
        return {
            'total_requests': total_requests,
            'total_cost': total_cost,
            'avg_usage_percentage': avg_usage_percentage,
            'monitoring_duration': len(self.results)
        }
    
    async def cleanup(self):
        """クリーンアップ"""
        self.is_running = False
        logger.info("🧹 コスト監視システムクリーンアップ完了")

async def main():
    """メイン実行"""
    system = CostMonitoringSystem()
    
    try:
        await system.initialize()
        
        # 初期ダッシュボード表示
        await system.show_cost_dashboard()
        
        # 継続的コスト監視開始
        await system.continuous_cost_monitoring()
        
    except KeyboardInterrupt:
        logger.info("⏹️ システム停止要求")
    finally:
        await system.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 