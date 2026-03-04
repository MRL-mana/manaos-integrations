#!/usr/bin/env python3
"""
Trinity Living System - Master Controller
全システムを統合管理するマスターコントローラー
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests

sys.path.insert(0, '/root/trinity_workspace/orchestrator')
from ticket_manager import TicketManager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s"
)
logger = logging.getLogger("living_system")


class LivingSystemMaster:
    """Trinity Living System マスターコントローラー"""
    
    def __init__(self):
        """初期化"""
        logger.info("🧠 Initializing Trinity Living System...")
        
        # サービスURL
        self.services = {
            "orchestrator_api": "http://127.0.0.1:9400",
            "web_ui": "http://127.0.0.1:9401",
            "dashboard": "http://127.0.0.1:9402",
            "n8n_connector": "http://127.0.0.1:9502",
            "n8n": "http://127.0.0.1:5678"
        }
        
        # チケット管理
        self.ticket_manager = TicketManager()
        
        # システム状態
        self.system_status = {
            "started_at": datetime.now().isoformat(),
            "total_tasks_executed": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "average_confidence": 0.0
        }
        
        logger.info("✅ Trinity Living System initialized")
    
    def check_all_services(self) -> Dict[str, bool]:
        """
        全サービスのヘルスチェック
        
        Returns:
            サービス名: 稼働状況の辞書
        """
        status = {}
        
        for name, url in self.services.items():
            try:
                response = requests.get(f"{url}/health", timeout=2)
                status[name] = response.status_code == 200
            except:
                status[name] = False
        
        return status
    
    def get_system_stats(self) -> Dict:
        """
        システム統計を取得
        
        Returns:
            統計情報
        """
        try:
            # Orchestrator APIから統計取得
            response = requests.get(f"{self.services['orchestrator_api']}/api/stats", timeout=2)
            if response.status_code == 200:
                stats = response.json()
                
                # 学習統計を追加
                self.system_status.update({
                    "active_tickets": stats.get("active_tickets", 0),
                    "orchestrator_version": stats.get("orchestrator_version", "1.0.0")
                })
                
                return self.system_status
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
        
        return self.system_status
    
    def display_status(self):
        """システム状態を表示"""
        print("\n" + "="*70)
        print("🧠 Trinity Living System - Status Report")
        print("="*70)
        
        # サービス状態
        print("\n📊 Services Status:")
        services_status = self.check_all_services()
        for name, running in services_status.items():
            status_icon = "✅" if running else "❌"
            print(f"  {status_icon} {name}: {'RUNNING' if running else 'STOPPED'}")
        
        # システム統計
        print("\n📈 System Statistics:")
        stats = self.get_system_stats()
        print(f"  Started: {stats['started_at']}")
        print(f"  Total Tasks: {stats['total_tasks_executed']}")
        print(f"  Successful: {stats['successful_tasks']}")
        print(f"  Failed: {stats['failed_tasks']}")
        
        # アクティブチケット
        active = self.ticket_manager.list_active_tickets()
        print(f"\n🎫 Active Tickets: {len(active)}")
        
        print("\n" + "="*70)
    
    def run_system_test(self):
        """システム統合テスト"""
        logger.info("🧪 Running system integration test...")
        
        # テスト1: Orchestrator実行
        logger.info("Test 1: Orchestrator execution")
        try:
            response = requests.post(
                f"{self.services['orchestrator_api']}/api/orchestrate",
                json={
                    "goal": "Living System統合テスト用スクリプト",
                    "context": ["Python", "超シンプル"],
                    "budget_turns": 3
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Test 1 passed: {result['ticket_id']}")
            else:
                logger.error(f"❌ Test 1 failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Test 1 error: {e}")
        
        # テスト2: Dashboard データ取得
        logger.info("Test 2: Dashboard data fetch")
        try:
            response = requests.get(
                f"{self.services['dashboard']}/api/dashboard_data",
                timeout=2
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Test 2 passed: {data['stats']['active_tickets']} active tickets")
            else:
                logger.error(f"❌ Test 2 failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Test 2 error: {e}")
        
        # テスト3: n8n Connector
        logger.info("Test 3: n8n Connector")
        try:
            response = requests.get(
                f"{self.services['n8n_connector']}/health",
                timeout=2
            )
            
            if response.status_code == 200:
                logger.info("✅ Test 3 passed: n8n Connector healthy")
            else:
                logger.error(f"❌ Test 3 failed: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Test 3 error: {e}")
        
        logger.info("🎉 System integration test complete")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Trinity Living System Master")
    parser.add_argument("--mode", choices=["status", "test", "monitor"], default="status")
    parser.add_argument("--interval", type=int, default=60, help="監視間隔（秒）")
    
    args = parser.parse_args()
    
    master = LivingSystemMaster()
    
    if args.mode == "status":
        # 状態表示
        master.display_status()
    
    elif args.mode == "test":
        # 統合テスト
        master.run_system_test()
    
    elif args.mode == "monitor":
        # 監視モード
        logger.info(f"👀 Starting system monitor (interval: {args.interval}s)")
        try:
            while True:
                master.display_status()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("👋 Monitor stopped")

