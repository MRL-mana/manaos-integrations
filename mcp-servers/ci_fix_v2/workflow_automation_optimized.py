#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔄 ManaOSワークフロー自動化モジュール（最適化版）
データベース接続プールとキャッシュシステムを使用
"""

import os
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from pathlib import Path

# 統一モジュールのインポート
from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# 最適化モジュールのインポート
from unified_cache_system import get_unified_cache
from config_cache import get_config_cache

# ロガーの初期化
logger = get_service_logger("workflow-automation-optimized")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("WorkflowAutomation")

# キャッシュシステムの取得
cache_system = get_unified_cache()
config_cache = get_config_cache()


class WorkflowAutomationOptimized:
    """ワークフロー自動化クラス（最適化版）"""
    
    def __init__(self):
        """初期化"""
        from comfyui_integration import ComfyUIIntegration
        from google_drive_integration import GoogleDriveIntegration
        from civitai_integration import CivitAIIntegration
        from mem0_integration import Mem0Integration
        from obsidian_integration import ObsidianIntegration
        
        self.comfyui = ComfyUIIntegration()
        self.drive = GoogleDriveIntegration()
        self.civitai = CivitAIIntegration()
        self.mem0 = Mem0Integration()
        
        try:
            default_vault = Path.home() / "Documents" / "Obsidian Vault"
            if default_vault.exists():
                self.obsidian = ObsidianIntegration(str(default_vault))
            else:
                self.obsidian = ObsidianIntegration(str(Path.cwd()))
        except Exception:
            self.obsidian = None
        
        # ワークフロー定義（キャッシュ使用）
        self.workflows = {}
        self._load_workflows()
    
    def _load_workflows(self):
        """ワークフロー定義を読み込む（キャッシュ使用）"""
        workflow_file = Path("workflows.json")
        
        # キャッシュから取得
        cached_workflows = cache_system.get("workflows", file_path=str(workflow_file))
        if cached_workflows:
            self.workflows = cached_workflows
            return
        
        # ファイルから読み込み
        if workflow_file.exists():
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    self.workflows = json.load(f)
                
                # キャッシュに保存
                cache_system.set("workflows", self.workflows, file_path=str(workflow_file), ttl_seconds=300)
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"workflow_file": str(workflow_file)},
                    user_message="ワークフロー定義の読み込みに失敗しました"
                )
                logger.warning(f"ワークフロー読み込みエラー: {error.message}")
                self.workflows = {}
        else:
            self.workflows = {}
    
    def _save_workflows(self):
        """ワークフロー定義を保存"""
        workflow_file = Path("workflows.json")
        try:
            with open(workflow_file, 'w', encoding='utf-8') as f:
                json.dump(self.workflows, f, ensure_ascii=False, indent=2)
            
            # キャッシュを更新
            cache_system.set("workflows", self.workflows, file_path=str(workflow_file), ttl_seconds=300)
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"workflow_file": str(workflow_file)},
                user_message="ワークフロー定義の保存に失敗しました"
            )
            logger.error(f"ワークフロー保存エラー: {error.message}")
    
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
        logger.info(f"✅ ワークフロー登録: {name}")
    
    def execute_workflow(self, name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        ワークフローを実行（最適化版）
        
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
                
                # ステップ実行（キャッシュチェック）
                cache_key = f"workflow_step:{name}:{step_type}:{json.dumps(step_params, sort_keys=True)}"
                cached_result = cache_system.get("workflow_result", cache_key=cache_key)
                if cached_result:
                    results[step.get("name", step_type)] = cached_result
                    continue
                
                # ステップを実行
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
                else:
                    result = {"error": f"不明なステップタイプ: {step_type}"}
                
                step_name = step.get("name", step_type)
                results[step_name] = result
                
                # キャッシュに保存（成功時のみ）
                if "error" not in result:
                    cache_system.set("workflow_result", result, cache_key=cache_key, ttl_seconds=3600)
            
            return {
                "workflow": name,
                "status": "success",
                "results": results,
                "executed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"workflow": name, "params": params},
                user_message="ワークフローの実行に失敗しました"
            )
            return {
                "workflow": name,
                "status": "error",
                "error": error.user_message or error.message
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
        if not self.civitai.is_available():
            return {"error": "CivitAIが利用できません"}
        
        query = params.get("query", "")
        results = self.civitai.search_models(query)
        
        return {"results": results[:10]} if results else {"error": "検索に失敗"}
    
    def _execute_drive_upload(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Google Driveアップロードを実行"""
        if not self.drive.is_available():
            return {"error": "Google Driveが利用できません"}
        
        file_path = params.get("file_path")
        folder_id = params.get("folder_id")
        
        result = self.drive.upload_file(file_path, folder_id)  # type: ignore
        return {"file_id": result} if result else {"error": "アップロードに失敗"}
    
    def _execute_obsidian_create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Obsidianノート作成を実行"""
        if not self.obsidian or not self.obsidian.is_available():
            return {"error": "Obsidianが利用できません"}
        
        title = params.get("title", "")
        content = params.get("content", "")
        
        note_path = self.obsidian.create_note(title, content)
        return {"note_path": note_path} if note_path else {"error": "ノート作成に失敗"}
    
    def _execute_mem0_add(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mem0記憶追加を実行"""
        if not self.mem0.is_available():
            return {"error": "Mem0が利用できません"}
        
        memory_text = params.get("memory_text", "")
        user_id = params.get("user_id", "default")
        
        result = self.mem0.add_memory(memory_text, user_id)
        return {"memory_id": result} if result else {"error": "記憶追加に失敗"}


def main():
    """テスト用メイン関数"""
    print("ワークフロー自動化（最適化版）テスト")
    print("=" * 60)
    
    workflow = WorkflowAutomationOptimized()
    print(f"登録済みワークフロー: {len(workflow.workflows)}件")


if __name__ == "__main__":
    main()






















