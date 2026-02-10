"""
ManaOSワークフロー自動化モジュール
複数の統合システムを組み合わせた自動化ワークフロー
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

try:
    from manaos_logger import get_logger
except ImportError:
    from logging import getLogger as get_logger

from comfyui_integration import ComfyUIIntegration
from google_drive_integration import GoogleDriveIntegration
from civitai_integration import CivitAIIntegration
try:
    from langchain_integration import LangChainIntegration
except (ImportError, NameError):
    LangChainIntegration = None
from mem0_integration import Mem0Integration
from obsidian_integration import ObsidianIntegration


class WorkflowAutomation:
    """ワークフロー自動化クラス"""
    
    def __init__(self):
        """初期化"""
        self.logger = get_logger(f"{__name__}.WorkflowAutomation")
        self.comfyui = ComfyUIIntegration()
        self.drive = GoogleDriveIntegration()
        self.civitai = CivitAIIntegration()
        self.langchain = LangChainIntegration() if LangChainIntegration else None
        self.mem0 = Mem0Integration()
        try:
            default_vault = Path.home() / "Documents" / "Obsidian"
            if default_vault.exists():
                self.obsidian = ObsidianIntegration(str(default_vault))
            else:
                self.obsidian = ObsidianIntegration(str(Path.cwd()))
        except Exception as e:
            self.logger.debug("Obsidian統合初期化スキップ: %s", e)
            self.obsidian = None
        
        self.workflows = {}
        self._load_workflows()
    
    def _load_workflows(self):
        """ワークフロー定義を読み込み"""
        workflow_file = Path("workflows.json")
        if workflow_file.exists():
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    self.workflows = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                self.logger.warning("workflows.json 読み込み失敗: %s", e)
                self.workflows = {}
    
    def _save_workflows(self):
        """ワークフロー定義を保存"""
        workflow_file = Path("workflows.json")
        try:
            with open(workflow_file, 'w', encoding='utf-8') as f:
                json.dump(self.workflows, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"ワークフロー保存エラー: {e}")
    
    def register_workflow(self, name: str, workflow: Dict[str, Any]):
        """
        ワークフローを登録
        
        Args:
            name: ワークフロー名
            workflow: ワークフロー定義
        """
        self.workflows[name] = {
            **workflow,
            "created_at": datetime.now().isoformat()
        }
        self._save_workflows()
    
    def execute_workflow(self, name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        ワークフローを実行
        
        Args:
            name: ワークフロー名
            params: パラメータ
            
        Returns:
            実行結果
        """
        if name not in self.workflows:
            return {"error": f"ワークフロー '{name}' が見つかりません"}
        
        workflow = self.workflows[name]
        params = params or {}
        
        try:
            steps = workflow.get("steps", [])
            results = {}
            
            for step in steps:
                step_type = step.get("type")
                step_params = {**step.get("params", {}), **params}
                
                if step_type == "comfyui_generate":
                    result = self._execute_comfyui_generate(step_params)
                elif step_type == "civitai_search":
                    result = self._execute_civitai_search(step_params)
                elif step_type == "drive_upload":
                    result = self._execute_drive_upload(step_params)
                elif step_type == "obsidian_create":
                    result = self._execute_obsidian_create(step_params)
                elif step_type == "mem0_add":
                    result = self._execute_mem0_add(step_params)
                elif step_type == "langchain_chat":
                    result = self._execute_langchain_chat(step_params)
                else:
                    result = {"error": f"不明なステップタイプ: {step_type}"}
                
                step_name = step.get("name", step_type)
                results[step_name] = result
            
            return {
                "workflow": name,
                "status": "success",
                "results": results,
                "executed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "workflow": name,
                "status": "error",
                "error": str(e)
            }
    
    def _execute_comfyui_generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ComfyUI画像生成を実行"""
        if not self.comfyui.is_available():
            return {"error": "ComfyUIが利用できません"}
        
        prompt_id = self.comfyui.generate_image(
            prompt=params.get("prompt", ""),
            negative_prompt=params.get("negative_prompt", ""),
            width=params.get("width", 512),
            height=params.get("height", 512),
            steps=params.get("steps", 20)
        )
        
        return {"prompt_id": prompt_id} if prompt_id else {"error": "画像生成に失敗"}
    
    def _execute_civitai_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """CivitAI検索を実行"""
        models = self.civitai.search_models(
            query=params.get("query", ""),
            limit=params.get("limit", 10)
        )
        return {"models": models, "count": len(models)}
    
    def _execute_drive_upload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Google Driveアップロードを実行"""
        if not self.drive.is_available():
            return {"error": "Google Driveが利用できません"}
        
        file_id = self.drive.upload_file(
            file_path=params.get("file_path", ""),
            folder_id=params.get("folder_id"),
            file_name=params.get("file_name")
        )
        
        return {"file_id": file_id} if file_id else {"error": "アップロードに失敗"}
    
    def _execute_obsidian_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Obsidianノート作成を実行"""
        if not self.obsidian or not self.obsidian.is_available():
            return {"error": "Obsidianが利用できません"}
        
        note_path = self.obsidian.create_note(
            title=params.get("title", ""),
            content=params.get("content", ""),
            tags=params.get("tags", []),
            folder=params.get("folder")
        )
        
        return {"note_path": str(note_path)} if note_path else {"error": "ノート作成に失敗"}
    
    def _execute_mem0_add(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mem0メモリ追加を実行"""
        if not self.mem0.is_available():
            return {"error": "Mem0が利用できません"}
        
        memory_id = self.mem0.add_memory(
            memory_text=params.get("memory_text", ""),
            user_id=params.get("user_id"),
            metadata=params.get("metadata")
        )
        
        return {"memory_id": memory_id} if memory_id else {"error": "メモリ追加に失敗"}
    
    def _execute_langchain_chat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """LangChainチャットを実行"""
        if not self.langchain.is_available():
            return {"error": "LangChainが利用できません"}
        
        response = self.langchain.chat(
            message=params.get("message", ""),
            system_prompt=params.get("system_prompt")
        )
        
        return {"response": response}


class ImageGenerationWorkflow:
    """画像生成ワークフロー"""
    
    def __init__(self, automation: WorkflowAutomation):
        """
        初期化
        
        Args:
            automation: WorkflowAutomationインスタンス
        """
        self.automation = automation
    
    def generate_and_backup(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        backup_to_drive: bool = True,
        create_note: bool = True
    ) -> Dict[str, Any]:
        """
        画像を生成してバックアップ
        
        Args:
            prompt: プロンプト
            negative_prompt: ネガティブプロンプト
            width: 画像幅
            height: 画像高さ
            backup_to_drive: Google Driveにバックアップするか
            create_note: Obsidianにノートを作成するか
            
        Returns:
            実行結果
        """
        workflow = {
            "name": "画像生成とバックアップ",
            "steps": [
                {
                    "type": "comfyui_generate",
                    "name": "画像生成",
                    "params": {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "width": width,
                        "height": height
                    }
                }
            ]
        }
        
        if backup_to_drive:
            workflow["steps"].append({
                "type": "drive_upload",
                "name": "Google Driveバックアップ",
                "params": {
                    "file_path": "${comfyui_generate.output_path}",
                    "folder_id": None
                }
            })
        
        if create_note:
            workflow["steps"].append({
                "type": "obsidian_create",
                "name": "Obsidianノート作成",
                "params": {
                    "title": f"画像生成: {prompt[:50]}",
                    "content": f"プロンプト: {prompt}\n\nネガティブプロンプト: {negative_prompt}",
                    "tags": ["画像生成", "ManaOS"]
                }
            })
        
        return self.automation.execute_workflow("generate_and_backup", {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height
        })


def create_default_workflows(automation: WorkflowAutomation):
    """デフォルトワークフローを作成"""
    
    # 画像生成とバックアップワークフロー
    automation.register_workflow("generate_and_backup", {
        "description": "画像を生成してGoogle Driveにバックアップ",
        "steps": [
            {
                "type": "comfyui_generate",
                "name": "画像生成",
                "params": {}
            },
            {
                "type": "drive_upload",
                "name": "バックアップ",
                "params": {}
            }
        ]
    })
    
    # モデル検索とメモリ保存ワークフロー
    automation.register_workflow("search_and_memorize", {
        "description": "CivitAIでモデルを検索してMem0に保存",
        "steps": [
            {
                "type": "civitai_search",
                "name": "モデル検索",
                "params": {}
            },
            {
                "type": "mem0_add",
                "name": "メモリ保存",
                "params": {}
            }
        ]
    })


def main():
    """テスト用メイン関数"""
    print("ワークフロー自動化テスト")
    print("=" * 50)
    
    automation = WorkflowAutomation()
    create_default_workflows(automation)
    
    print(f"登録済みワークフロー: {list(automation.workflows.keys())}")
    
    # ワークフロー実行テスト
    if "generate_and_backup" in automation.workflows:
        print("\n画像生成ワークフローを実行中...")
        result = automation.execute_workflow("generate_and_backup", {
            "prompt": "a beautiful landscape",
            "width": 512,
            "height": 512
        })
        print(f"結果: {result}")


if __name__ == "__main__":
    main()



