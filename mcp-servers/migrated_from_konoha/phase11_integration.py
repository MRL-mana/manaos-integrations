#!/usr/bin/env python3
"""
Phase 11 API統合モジュール
Trinity統合秘書システムとPhase 11 Orchestratorを連携
"""

import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

PHASE11_API_URL = "http://127.0.0.1:9400"


class Phase11Integration:
    """Phase 11 Orchestrator統合"""
    
    def __init__(self):
        self.api_url = PHASE11_API_URL
        self.available = self._check_availability()
        if self.available:
            logger.info("✅ Phase 11 API connected")
        else:
            logger.warning("⚠️  Phase 11 API not available")
    
    def _check_availability(self) -> bool:
        """Phase 11 APIの可用性確認"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """Phase 11 APIのステータス取得"""
        if not self.available:
            return None
        
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get Phase 11 status: {e}")
        
        return None
    
    def orchestrate_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Phase 11でタスクをオーケストレート"""
        if not self.available:
            logger.warning("Phase 11 API not available for orchestration")
            return None
        
        try:
            # Phase 11 APIにタスクを送信（エンドポイントは実際のAPIに合わせて調整）
            response = requests.post(
                f"{self.api_url}/api/orchestrate",
                json=task_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Phase 11 orchestration successful")
                return result
            else:
                logger.warning(f"Phase 11 orchestration failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Phase 11 orchestration error: {e}")
            return None
    
    def enhance_task_with_phase11(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 11の機能でタスクを強化"""
        if not self.available:
            return task
        
        # Phase 11のAI機能を活用してタスクを分析・最適化
        enhanced = task.copy()
        
        # Phase 11のステータスを追加
        phase11_status = self.get_status()
        if phase11_status:
            enhanced['phase11_available'] = True
            enhanced['phase11_service'] = phase11_status.get('service', 'unknown')
        else:
            enhanced['phase11_available'] = False
        
        return enhanced
    
    def get_integration_info(self) -> Dict[str, Any]:
        """統合情報を取得"""
        return {
            "phase11_api_url": self.api_url,
            "available": self.available,
            "features": {
                "orchestration": self.available,
                "task_enhancement": self.available,
                "status_monitoring": self.available
            }
        }


# グローバルインスタンス
phase11 = Phase11Integration()


def enhance_with_phase11(task: Dict[str, Any]) -> Dict[str, Any]:
    """タスクをPhase 11で強化（便利関数）"""
    return phase11.enhance_task_with_phase11(task)


def orchestrate_with_phase11(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Phase 11でオーケストレート（便利関数）"""
    return phase11.orchestrate_task(task)

