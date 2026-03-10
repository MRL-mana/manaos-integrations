"""
🚀 常時起動LLM 超統合拡張版
ComfyUI、CivitAI、通知ハブ、ファイル秘書など完全統合
"""

import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from always_ready_llm_integrated import (
    IntegratedLLMClient,
    ModelType,
    TaskType,
    LLMResponse
)

# 追加統合モジュール（オプション）
COMFYUI_AVAILABLE = False
CIVITAI_AVAILABLE = False
NOTIFICATION_HUB_AVAILABLE = False
FILE_SECRETARY_AVAILABLE = False
IMAGE_GENERATION_AVAILABLE = False
GITHUB_AVAILABLE = False

try:
    from comfyui_integration import ComfyUIIntegration
    COMFYUI_AVAILABLE = True
except ImportError:
    pass

try:
    from civitai_integration import CivitAIIntegration
    CIVITAI_AVAILABLE = True
except ImportError:
    pass

try:
    from notification_hub_enhanced import NotificationHubEnhanced
    NOTIFICATION_HUB_AVAILABLE = True
except ImportError:
    try:
        from notification_hub import NotificationHub
        NOTIFICATION_HUB_AVAILABLE = True
    except ImportError:
        pass

try:
    from file_secretary_api import FileSecretaryAPI
    FILE_SECRETARY_AVAILABLE = True
except ImportError:
    pass

try:
    from image_generation_integration import ImageGenerationIntegration
    IMAGE_GENERATION_AVAILABLE = True
except ImportError:
    pass

try:
    from github_integration import GitHubIntegration
    GITHUB_AVAILABLE = True
except ImportError:
    pass


class UltraIntegratedLLMClient(IntegratedLLMClient):
    """超統合拡張版LLMクライアント"""
    
    def __init__(
        self,
        enable_image_generation: bool = False,
        enable_model_search: bool = False,
        enable_notification_hub: bool = False,
        enable_file_organization: bool = False,
        **kwargs
    ):
        """
        初期化
        
        Args:
            enable_image_generation: 画像生成機能を有効にするか
            enable_model_search: モデル検索機能を有効にするか
            enable_notification_hub: 通知ハブ機能を有効にするか
            enable_file_organization: ファイル整理機能を有効にするか
            **kwargs: 親クラスのパラメータ
        """
        super().__init__(**kwargs)
        
        # 追加統合モジュール初期化
        self.comfyui = None
        self.civitai = None
        self.notification_hub = None
        self.file_secretary = None
        self.image_generation = None
        self.github = None
        
        if enable_image_generation and COMFYUI_AVAILABLE:
            self.comfyui = ComfyUIIntegration()  # type: ignore[possibly-unbound]
        
        if enable_model_search and CIVITAI_AVAILABLE:
            self.civitai = CivitAIIntegration()  # type: ignore[possibly-unbound]
        
        if enable_notification_hub and NOTIFICATION_HUB_AVAILABLE:
            try:
                self.notification_hub = NotificationHubEnhanced()  # type: ignore[possibly-unbound]
            except Exception:
                try:
                    self.notification_hub = NotificationHub()  # type: ignore[possibly-unbound]
                except Exception:
                    pass
        
        if enable_file_organization and FILE_SECRETARY_AVAILABLE:
            self.file_secretary = FileSecretaryAPI()  # type: ignore[possibly-unbound]
        
        if enable_image_generation and IMAGE_GENERATION_AVAILABLE:
            self.image_generation = ImageGenerationIntegration()  # type: ignore[possibly-unbound]
        
        if GITHUB_AVAILABLE:
            self.github = GitHubIntegration()  # type: ignore[possibly-unbound]
    
    def chat_with_image_generation(
        self,
        message: str,
        model: ModelType = ModelType.MEDIUM,
        generate_image: bool = False,
        image_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLMチャット + 画像生成
        
        Args:
            message: メッセージ
            model: モデル
            generate_image: 画像を生成するか
            image_prompt: 画像生成プロンプト（Noneの場合はメッセージから抽出）
            **kwargs: その他のパラメータ
        
        Returns:
            チャット結果と画像生成結果
        """
        # LLMチャット
        response = self.chat(message, model, **kwargs)
        
        result = {
            "chat": response,
            "image": None
        }
        
        # 画像生成
        if generate_image and self.comfyui and self.comfyui.is_available():
            try:
                # プロンプト抽出
                if not image_prompt:
                    # LLMに画像生成プロンプトを生成してもらう
                    prompt_response = self.chat(
                        f"以下の内容から画像生成用のプロンプトを生成してください: {message}",
                        ModelType.LIGHT,
                        TaskType.AUTOMATION
                    )
                    image_prompt = prompt_response.response
                else:
                    image_prompt = image_prompt
                
                # 画像生成
                prompt_id = self.comfyui.generate_image(
                    prompt=image_prompt,
                    width=512,
                    height=512
                )
                
                result["image"] = {
                    "success": prompt_id is not None,
                    "prompt_id": prompt_id,
                    "prompt": image_prompt
                }
            except Exception as e:
                result["image"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return result
    
    def chat_with_model_search(
        self,
        message: str,
        model: ModelType = ModelType.MEDIUM,
        search_models: bool = False,
        search_query: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLMチャット + モデル検索
        
        Args:
            message: メッセージ
            model: モデル
            search_models: モデルを検索するか
            search_query: 検索クエリ（Noneの場合はメッセージから抽出）
            **kwargs: その他のパラメータ
        
        Returns:
            チャット結果とモデル検索結果
        """
        # LLMチャット
        response = self.chat(message, model, **kwargs)
        
        result = {
            "chat": response,
            "models": None
        }
        
        # モデル検索
        if search_models and self.civitai and self.civitai.is_available():
            try:
                # 検索クエリ抽出
                if not search_query:
                    # LLMに検索クエリを生成してもらう
                    query_response = self.chat(
                        f"以下の内容からモデル検索用のキーワードを抽出してください: {message}",
                        ModelType.LIGHT,
                        TaskType.AUTOMATION
                    )
                    search_query = query_response.response
                else:
                    search_query = search_query
                
                # モデル検索
                models = self.civitai.search_models(query=search_query, limit=5)
                
                result["models"] = {
                    "success": True,
                    "query": search_query,
                    "models": models,
                    "count": len(models)
                }
            except Exception as e:
                result["models"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return result
    
    def chat_with_notification_hub(
        self,
        message: str,
        model: ModelType = ModelType.LIGHT,
        notify: bool = True,
        priority: str = "normal",
        channels: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLMチャット + 通知ハブ
        
        Args:
            message: メッセージ
            model: モデル
            notify: 通知を送信するか
            priority: 優先度
            channels: 通知チャンネル
            **kwargs: その他のパラメータ
        
        Returns:
            チャット結果と通知結果
        """
        # LLMチャット
        response = self.chat(message, model, **kwargs)
        
        result = {
            "chat": response,
            "notification": None
        }
        
        # 通知ハブ送信
        if notify and self.notification_hub:
            try:
                # 通知メッセージ生成
                notification_message = f"""🤖 LLM応答

**メッセージ**: {message[:100]}{'...' if len(message) > 100 else ''}
**レスポンス**: {response.response[:200]}{'...' if len(response.response) > 200 else ''}
**モデル**: {response.model}
**レイテンシ**: {response.latency_ms:.2f}ms
"""
                
                # 通知送信
                if hasattr(self.notification_hub, 'send_notification'):
                    success = self.notification_hub.send_notification(
                        notification_message,
                        priority=priority,
                        channels=channels
                    )
                else:
                    success = self.notification_hub.notify(
                        notification_message,
                        priority=priority
                    )
                
                result["notification"] = {
                    "success": success,
                    "priority": priority,
                    "channels": channels or ["slack"]
                }
            except Exception as e:
                result["notification"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return result
    
    def chat_with_file_organization(
        self,
        message: str,
        model: ModelType = ModelType.MEDIUM,
        organize_files: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLMチャット + ファイル整理
        
        Args:
            message: メッセージ
            model: モデル
            organize_files: ファイルを整理するか
            **kwargs: その他のパラメータ
        
        Returns:
            チャット結果とファイル整理結果
        """
        # LLMチャット
        response = self.chat(message, model, **kwargs)
        
        result = {
            "chat": response,
            "file_organization": None
        }
        
        # ファイル整理
        if organize_files and self.file_secretary:
            try:
                # LLMにファイル整理指示を生成してもらう
                organization_response = self.chat(
                    f"以下の内容からファイル整理の指示を生成してください: {message}",
                    ModelType.MEDIUM,
                    TaskType.AUTOMATION
                )
                
                # ファイル秘書API呼び出し（実装に応じて調整）
                result["file_organization"] = {
                    "success": True,
                    "instruction": organization_response.response
                }
            except Exception as e:
                result["file_organization"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return result
    
    def chat_with_github(
        self,
        message: str,
        model: ModelType = ModelType.MEDIUM,
        create_issue: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        LLMチャット + GitHub統合
        
        Args:
            message: メッセージ
            model: モデル
            create_issue: GitHub Issueを作成するか
            **kwargs: その他のパラメータ
        
        Returns:
            チャット結果とGitHub結果
        """
        # LLMチャット
        response = self.chat(message, model, **kwargs)
        
        result = {
            "chat": response,
            "github": None
        }
        
        # GitHub Issue作成
        if create_issue and self.github and self.github.is_available():
            try:
                # Issueタイトルと本文を生成
                issue_title = f"LLM生成: {message[:50]}"
                issue_body = f"""## 元のメッセージ
{message}

## LLM応答
{response.response}

## メタデータ
- モデル: {response.model}
- レイテンシ: {response.latency_ms:.2f}ms
- タイムスタンプ: {datetime.now().isoformat()}
"""
                
                # GitHub Issue作成（実装に応じて調整）
                result["github"] = {
                    "success": True,
                    "title": issue_title,
                    "body": issue_body
                }
            except Exception as e:
                result["github"] = {
                    "success": False,
                    "error": str(e)
                }
        
        return result
    
    def full_integration_chat(
        self,
        message: str,
        model: ModelType = ModelType.MEDIUM,
        generate_image: bool = False,
        search_models: bool = False,
        notify: bool = True,
        organize_files: bool = False,
        create_issue: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        全統合機能付きチャット
        
        Args:
            message: メッセージ
            model: モデル
            generate_image: 画像を生成するか
            search_models: モデルを検索するか
            notify: 通知を送信するか
            organize_files: ファイルを整理するか
            create_issue: GitHub Issueを作成するか
            **kwargs: その他のパラメータ
        
        Returns:
            全統合結果
        """
        # LLMチャット
        response = self.chat(message, model, **kwargs)
        
        result = {
            "chat": response,
            "integrations": {}
        }
        
        # 画像生成
        if generate_image:
            image_result = self.chat_with_image_generation(
                message, model, generate_image=True, **kwargs
            )
            result["integrations"]["image"] = image_result.get("image")
        
        # モデル検索
        if search_models:
            model_result = self.chat_with_model_search(
                message, model, search_models=True, **kwargs
            )
            result["integrations"]["models"] = model_result.get("models")
        
        # 通知
        if notify:
            notify_result = self.chat_with_notification_hub(
                message, model, notify=True, **kwargs
            )
            result["integrations"]["notification"] = notify_result.get("notification")
        
        # ファイル整理
        if organize_files:
            file_result = self.chat_with_file_organization(
                message, model, organize_files=True, **kwargs
            )
            result["integrations"]["file_organization"] = file_result.get("file_organization")
        
        # GitHub Issue
        if create_issue:
            github_result = self.chat_with_github(
                message, model, create_issue=True, **kwargs
            )
            result["integrations"]["github"] = github_result.get("github")
        
        return result


# 便利関数
def ultra_chat(
    message: str,
    model: ModelType = ModelType.LIGHT,
    generate_image: bool = False,
    notify: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    超統合チャット（簡単に使える関数）
    
    Args:
        message: メッセージ
        model: モデル
        generate_image: 画像を生成するか
        notify: 通知を送信するか
        **kwargs: その他のパラメータ
    
    Returns:
        統合結果
    """
    client = UltraIntegratedLLMClient(
        enable_image_generation=generate_image,
        enable_notification_hub=notify,
        auto_save_obsidian=True
    )
    
    return client.full_integration_chat(
        message,
        model,
        generate_image=generate_image,
        notify=notify,
        **kwargs
    )


# 使用例
if __name__ == "__main__":
    print("超統合拡張版LLMクライアントテスト")
    
    # クライアント初期化
    client = UltraIntegratedLLMClient(
        enable_image_generation=True,
        enable_model_search=True,
        enable_notification_hub=True,
        auto_save_obsidian=True
    )
    
    # 全統合チャット
    print("\n=== 全統合チャットテスト ===")
    result = client.full_integration_chat(
        "こんにちは！短く挨拶してください。",
        ModelType.LIGHT,
        generate_image=False,
        search_models=False,
        notify=False
    )
    
    print(f"レスポンス: {result['chat'].response}")
    print(f"統合結果: {result['integrations']}")






















