#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base AI API統合モジュール
"""

import os
import requests
from manaos_logger import get_logger, get_service_logger
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = get_service_logger("base-ai-integration")


@dataclass


class BaseAIResponse:
    """Base AI APIレスポンス"""
    content: str
    model: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


class BaseAIIntegration:
    """Base AI API統合"""
    
    def __init__(self, api_key: Optional[str] = None, use_free: bool = False):
        """
        初期化
        
        Args:
            api_key: Base AI APIキー（Noneの場合は環境変数から取得）
            use_free: 無料のAI APIキーを使用するか（デフォルト: False）
        """
        if use_free:
            self.api_key = api_key or os.getenv("BASE_AI_FREE_API_KEY")
        else:
            self.api_key = api_key or os.getenv("BASE_AI_API_KEY")
        
        self.base_url = "https://api.baseai.com/v1"  # 正しいエンドポイント
        
        if not self.api_key:
            logger.warning("Base AI APIキーが設定されていません")
    
    def is_available(self) -> bool:
        """APIが利用可能か確認"""
        return self.api_key is not None and len(self.api_key) > 0
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "base-ai",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> BaseAIResponse:
        """
        チャットを実行
        
        Args:
            messages: メッセージのリスト（[{"role": "user", "content": "..."}]）
            model: モデル名（デフォルト: base-ai）
            temperature: 温度パラメータ（デフォルト: 0.7）
            max_tokens: 最大トークン数（オプション）
            stream: ストリーミングを有効にするか（デフォルト: False）
        
        Returns:
            Base AI APIレスポンス
        """
        if not self.is_available():
            logger.error("Base AI APIキーが設定されていません")
            raise ValueError("Base AI APIキーが設定されていません")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            if stream:
                payload["stream"] = True
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            data = response.json()
            
            # レスポンスを解析
            content = ""
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
            
            model_name = data.get("model")
            usage = data.get("usage")
            
            logger.info(f"Base AI: チャット完了（モデル: {model_name}）")
            
            return BaseAIResponse(
                content=content,
                model=model_name,
                usage=usage
            )
            
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = f" - {error_data}"
            except Exception:
                error_detail = f" - {e.response.text[:200]}"
            logger.error(f"Base AI API HTTPエラー ({e.response.status_code}): {e}{error_detail}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Base AI APIリクエストエラー: {e}")
            raise
        except Exception as e:
            logger.error(f"Base AI APIエラー: {e}", exc_info=True)
            raise
    
    def chat_simple(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        シンプルなチャット（プロンプトのみ）
        
        Args:
            prompt: ユーザープロンプト
            system_prompt: システムプロンプト（オプション）
        
        Returns:
            レスポンステキスト
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.chat(messages=messages)
        return response.content

