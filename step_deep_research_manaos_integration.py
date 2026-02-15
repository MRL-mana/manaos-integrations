#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step-Deep-Research ManaOS統合
Intent Routerへの登録と統合処理
"""

import json
import httpx
from pathlib import Path
from typing import Dict, Any

from manaos_logger import get_logger
from step_deep_research.orchestrator import StepDeepResearchOrchestrator

logger = get_logger(__name__)


class StepDeepResearchManaOSIntegration:
    """ManaOS統合クラス"""
    
    def __init__(self):
        """初期化"""
        # 設定読み込み
        config_path = Path("step_deep_research_config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        
        self.service_id = self.config.get("service_id", "5121")
        self.service_name = self.config.get("service_name", "Step Deep Research")
        self.service_url = f"http://127.0.0.1:{self.service_id}"
        
        # オーケストレーター初期化
        self.orchestrator = StepDeepResearchOrchestrator(self.config)
        
        # Intent Router URL
        self.intent_router_url = "http://127.0.0.1:5100"
    
    def register_with_intent_router(self) -> bool:
        """
        Intent Routerに登録
        API経由でキーワードマッピングを登録
        
        Returns:
            登録成功かどうか
        """
        try:
            logger.info(f"Intent Routerへの登録: {self.service_name}")
            
            # Intent Router API経由で登録を試みる
            try:
                # キーワードマッピングを準備
                research_keywords = [
                    "調査", "リサーチ", "調べて", "研究", "専門調査",
                    "深く調べて", "詳しく調べて", "徹底的に調べて",
                    "deep research", "research", "investigate"
                ]
                
                # Intent Router APIにPOSTリクエストを送信
                # 設定更新APIを使用
                response = httpx.post(
                    f"{self.intent_router_url}/api/config",
                    json={
                        "action": "add_keywords",
                        "intent_type": "information_search",  # または新しいintent_typeを作成
                        "keywords": research_keywords,
                        "service_id": self.service_id,
                        "service_name": self.service_name,
                        "service_url": self.service_url
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info("Intent Router API経由で登録成功")
                    return True
                else:
                    logger.warning(f"Intent Router API登録失敗: HTTP {response.status_code}")
                    # フォールバック: 設定ファイルを直接更新
                    return self._update_intent_router_config_file()
            
            except httpx.RequestError as e:
                logger.warning(f"Intent Router API接続エラー: {e}。設定ファイルを直接更新します。")
                # フォールバック: 設定ファイルを直接更新
                return self._update_intent_router_config_file()
            
        except Exception as e:
            logger.error(f"Intent Router登録エラー: {e}")
            return False
    
    def _update_intent_router_config_file(self) -> bool:
        """
        Intent Router設定ファイルを直接更新（フォールバック）
        
        Returns:
            更新成功かどうか
        """
        try:
            config_path = Path("intent_router_config.json")
            
            if not config_path.exists():
                logger.warning("Intent Router設定ファイルが見つかりません")
                return False
            
            # 設定読み込み
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # キーワードマッピングに追加
            keyword_mapping = config.get("keyword_mapping", {})
            
            # Step-Deep-Research用のキーワード追加
            research_keywords = [
                "調査", "リサーチ", "調べて", "研究", "専門調査",
                "深く調べて", "詳しく調べて", "徹底的に調べて"
            ]
            
            # 既存のdeep_researchキーワードリストに追加、または新規作成
            if "deep_research" in keyword_mapping:
                existing_keywords = keyword_mapping["deep_research"]
                if isinstance(existing_keywords, list):
                    keyword_mapping["deep_research"] = list(set(existing_keywords + research_keywords))
                else:
                    keyword_mapping["deep_research"] = research_keywords
            else:
                keyword_mapping["deep_research"] = research_keywords
            
            config["keyword_mapping"] = keyword_mapping
            
            # 設定保存
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info("Intent Router設定ファイルを更新しました")
            return True
            
        except Exception as e:
            logger.error(f"Intent Router設定更新エラー: {e}")
            return False
    
    def handle_research_request(self, user_query: str) -> Dict[str, Any]:
        """
        調査リクエスト処理
        
        Args:
            user_query: ユーザーの調査依頼
        
        Returns:
            処理結果
        """
        try:
            # ジョブ作成
            job_id = self.orchestrator.create_job(user_query)
            
            # 非同期実行（実際の実装ではバックグラウンドで実行）
            # ここでは即座に実行
            result = self.orchestrator.execute_job(job_id)
            
            return {
                "success": True,
                "job_id": job_id,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"調査リクエスト処理エラー: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        サービス情報取得
        
        Returns:
            サービス情報
        """
        return {
            "service_id": self.service_id,
            "service_name": self.service_name,
            "service_url": self.service_url,
            "version": self.config.get("version", "1.0.0"),
            "status": "running"
        }


def update_intent_router_config():
    """Intent Router設定ファイルを更新"""
    config_path = Path("intent_router_config.json")
    
    if not config_path.exists():
        logger.warning("Intent Router設定ファイルが見つかりません")
        return False
    
    try:
        # 設定読み込み
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # キーワードマッピングに追加
        keyword_mapping = config.get("keyword_mapping", {})
        
        # Step-Deep-Research用のキーワード追加
        research_keywords = [
            "調査", "リサーチ", "調べて", "研究", "専門調査",
            "深く調べて", "詳しく調べて", "徹底的に調べて"
        ]
        
        # INFORMATION_SEARCHに追加（または新しいintent_typeを作成）
        # ここでは既存のINFORMATION_SEARCHを使用
        for keyword in research_keywords:
            if keyword not in keyword_mapping:
                keyword_mapping[keyword] = "information_search"
        
        config["keyword_mapping"] = keyword_mapping
        
        # 設定保存
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.info("Intent Router設定ファイルを更新しました")
        return True
        
    except Exception as e:
        logger.error(f"Intent Router設定更新エラー: {e}")
        return False


if __name__ == "__main__":
    # 統合テスト
    integration = StepDeepResearchManaOSIntegration()
    
    # Intent Router設定更新
    update_intent_router_config()
    
    # サービス情報表示
    info = integration.get_service_info()
    print(f"サービス情報: {json.dumps(info, ensure_ascii=False, indent=2)}")
    
    print("\n✅ ManaOS統合完了！")



