"""
🚀 常時起動LLM統合拡張版
Obsidian、Slack、Google Drive、n8nなどと完全統合
"""

import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from always_ready_llm_client import (
    AlwaysReadyLLMClient,
    ModelType,
    TaskType,
    LLMResponse
)

# 統合モジュール（オプション）
OBSIDIAN_AVAILABLE = False
SLACK_AVAILABLE = False
GOOGLE_DRIVE_AVAILABLE = False
MEM0_AVAILABLE = False

try:
    from obsidian_integration import ObsidianIntegration
    OBSIDIAN_AVAILABLE = True
except ImportError:
    pass

try:
    from notification_system import NotificationSystem
    SLACK_AVAILABLE = True
except ImportError:
    pass

try:
    from google_drive_integration import GoogleDriveIntegration
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    pass

try:
    from mem0_integration import Mem0Integration
    MEM0_AVAILABLE = True
except ImportError:
    pass


class IntegratedLLMClient:
    """統合拡張版LLMクライアント"""
    
    def __init__(
        self,
        auto_save_obsidian: bool = True,
        auto_notify_slack: bool = False,
        auto_save_drive: bool = False,
        auto_save_memory: bool = True,
        obsidian_folder: str = "LLM",
        slack_channel: Optional[str] = None
    ):
        """
        初期化
        
        Args:
            auto_save_obsidian: Obsidianに自動保存するか
            auto_notify_slack: Slackに自動通知するか
            auto_save_drive: Google Driveに自動保存するか
            auto_save_memory: Mem0に自動保存するか
            obsidian_folder: Obsidianの保存フォルダ
            slack_channel: Slackチャンネル
        """
        self.client = AlwaysReadyLLMClient()
        
        # 自動保存設定
        self.auto_save_obsidian = auto_save_obsidian
        self.auto_notify_slack = auto_notify_slack
        self.auto_save_drive = auto_save_drive
        self.auto_save_memory = auto_save_memory
        self.obsidian_folder = obsidian_folder
        self.slack_channel = slack_channel
        
        # 統合モジュール初期化
        self.obsidian = None
        self.slack = None
        self.drive = None
        self.mem0 = None
        
        if auto_save_obsidian and OBSIDIAN_AVAILABLE:
            vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
            self.obsidian = ObsidianIntegration(vault_path)
        
        if auto_notify_slack and SLACK_AVAILABLE:
            self.slack = NotificationSystem()
        
        if auto_save_drive and GOOGLE_DRIVE_AVAILABLE:
            self.drive = GoogleDriveIntegration()
        
        if auto_save_memory and MEM0_AVAILABLE:
            self.mem0 = Mem0Integration()
    
    def chat(
        self,
        message: str,
        model: ModelType = ModelType.LIGHT,
        task_type: TaskType = TaskType.CONVERSATION,
        save_to_obsidian: Optional[bool] = None,
        notify_slack: Optional[bool] = None,
        save_to_drive: Optional[bool] = None,
        save_to_memory: Optional[bool] = None,
        **kwargs
    ) -> LLMResponse:
        """
        LLMチャット（統合機能付き）
        
        Args:
            message: メッセージ
            model: モデル
            task_type: タスクタイプ
            save_to_obsidian: Obsidianに保存するか（Noneの場合は自動設定を使用）
            notify_slack: Slackに通知するか（Noneの場合は自動設定を使用）
            save_to_drive: Google Driveに保存するか（Noneの場合は自動設定を使用）
            save_to_memory: Mem0に保存するか（Noneの場合は自動設定を使用）
            **kwargs: その他のパラメータ
        
        Returns:
            LLMResponse
        """
        # LLM呼び出し
        response = self.client.chat(message, model, task_type, **kwargs)
        
        # 統合処理
        integration_results = {}
        
        # Obsidian保存
        if (save_to_obsidian if save_to_obsidian is not None else self.auto_save_obsidian):
            obsidian_result = self._save_to_obsidian(message, response, task_type)
            integration_results["obsidian"] = obsidian_result
        
        # Slack通知
        if (notify_slack if notify_slack is not None else self.auto_notify_slack):
            slack_result = self._notify_slack(message, response, task_type)
            integration_results["slack"] = slack_result
        
        # Google Drive保存
        if (save_to_drive if save_to_drive is not None else self.auto_save_drive):
            drive_result = self._save_to_drive(message, response, task_type)
            integration_results["drive"] = drive_result
        
        # Mem0保存
        if (save_to_memory if save_to_memory is not None else self.auto_save_memory):
            memory_result = self._save_to_memory(message, response, task_type)
            integration_results["memory"] = memory_result
        
        # 統合結果をレスポンスに追加
        response.integration_results = integration_results
        
        return response
    
    def _save_to_obsidian(
        self,
        message: str,
        response: LLMResponse,
        task_type: TaskType
    ) -> Dict[str, Any]:
        """Obsidianに保存"""
        if not self.obsidian or not self.obsidian.is_available():
            return {"success": False, "error": "Obsidianが利用できません"}
        
        try:
            # タイトル生成
            title = f"LLM会話 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # コンテンツ生成
            content = f"""# LLM会話記録

## メッセージ
{message}

## レスポンス
{response.response}

## メタデータ
- モデル: {response.model}
- タスクタイプ: {task_type.value}
- レイテンシ: {response.latency_ms:.2f}ms
- キャッシュ: {'Yes' if response.cached else 'No'}
- トークン数: {response.tokens or 'N/A'}
- ソース: {response.source}
- タイムスタンプ: {datetime.now().isoformat()}
"""
            
            # タグ生成
            tags = ["LLM", "会話", task_type.value]
            if response.cached:
                tags.append("キャッシュ")
            
            # ノート作成
            note_path = self.obsidian.create_note(
                title=title,
                content=content,
                tags=tags,
                folder=self.obsidian_folder
            )
            
            return {
                "success": note_path is not None,
                "note_path": str(note_path) if note_path else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _notify_slack(
        self,
        message: str,
        response: LLMResponse,
        task_type: TaskType
    ) -> Dict[str, Any]:
        """Slackに通知"""
        if not self.slack:
            return {"success": False, "error": "Slackが利用できません"}
        
        try:
            # メッセージ生成
            slack_message = f"""🤖 LLM応答

**メッセージ**: {message[:100]}{'...' if len(message) > 100 else ''}
**レスポンス**: {response.response[:200]}{'...' if len(response.response) > 200 else ''}
**モデル**: {response.model}
**レイテンシ**: {response.latency_ms:.2f}ms
**キャッシュ**: {'✅' if response.cached else '❌'}
"""
            
            # 通知送信
            success = self.slack.send_slack(slack_message, self.slack_channel)
            
            return {"success": success}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _save_to_drive(
        self,
        message: str,
        response: LLMResponse,
        task_type: TaskType
    ) -> Dict[str, Any]:
        """Google Driveに保存"""
        if not self.drive or not self.drive.is_available():
            return {"success": False, "error": "Google Driveが利用できません"}
        
        try:
            # 一時ファイル作成
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                data = {
                    "message": message,
                    "response": response.response,
                    "model": response.model,
                    "task_type": task_type.value,
                    "latency_ms": response.latency_ms,
                    "cached": response.cached,
                    "tokens": response.tokens,
                    "timestamp": datetime.now().isoformat()
                }
                json.dump(data, f, ensure_ascii=False, indent=2)
                temp_path = f.name
            
            # Google Driveにアップロード
            file_name = f"LLM_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file_id = self.drive.upload_file(temp_path, file_name=file_name)
            
            # 一時ファイル削除
            os.unlink(temp_path)
            
            return {
                "success": file_id is not None,
                "file_id": file_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _save_to_memory(
        self,
        message: str,
        response: LLMResponse,
        task_type: TaskType
    ) -> Dict[str, Any]:
        """Mem0に保存"""
        if not self.mem0 or not self.mem0.is_available():
            return {"success": False, "error": "Mem0が利用できません"}
        
        try:
            # メモリテキスト生成
            memory_text = f"ユーザー: {message}\nAI: {response.response}"
            
            # メタデータ
            metadata = {
                "model": response.model,
                "task_type": task_type.value,
                "latency_ms": response.latency_ms,
                "cached": response.cached,
                "tokens": response.tokens,
                "source": response.source
            }
            
            # メモリ追加
            memory_id = self.mem0.add_memory(
                memory_text=memory_text,
                user_id="mana",
                metadata=metadata
            )
            
            return {
                "success": memory_id is not None,
                "memory_id": memory_id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def batch_chat_with_integration(
        self,
        messages: List[str],
        model: ModelType = ModelType.LIGHT,
        task_type: TaskType = TaskType.CONVERSATION,
        **kwargs
    ) -> List[LLMResponse]:
        """バッチチャット（統合機能付き）"""
        results = []
        for message in messages:
            try:
                response = self.chat(message, model, task_type, **kwargs)
                results.append(response)
            except Exception as e:
                # エラー時は空レスポンスを追加
                error_response = LLMResponse(
                    response=f"エラー: {e}",
                    model=model.value,
                    cached=False,
                    latency_ms=0.0,
                    source="error"
                )
                results.append(error_response)
        
        return results


# 便利関数
def integrated_chat(
    message: str,
    model: ModelType = ModelType.LIGHT,
    save_to_obsidian: bool = True,
    notify_slack: bool = False
) -> LLMResponse:
    """
    統合チャット（簡単に使える関数）
    
    Args:
        message: メッセージ
        model: モデル
        save_to_obsidian: Obsidianに保存するか
        notify_slack: Slackに通知するか
    
    Returns:
        LLMResponse
    """
    client = IntegratedLLMClient(
        auto_save_obsidian=save_to_obsidian,
        auto_notify_slack=notify_slack
    )
    return client.chat(message, model)


# 使用例
if __name__ == "__main__":
    print("統合拡張版LLMクライアントテスト")
    
    # クライアント初期化（Obsidian自動保存有効）
    client = IntegratedLLMClient(
        auto_save_obsidian=True,
        auto_notify_slack=False,
        auto_save_memory=True
    )
    
    # チャット実行
    print("\n=== 統合チャットテスト ===")
    response = client.chat(
        "こんにちは！短く挨拶してください。",
        ModelType.LIGHT,
        TaskType.CONVERSATION
    )
    
    print(f"レスポンス: {response.response}")
    print(f"統合結果: {response.integration_results}")

