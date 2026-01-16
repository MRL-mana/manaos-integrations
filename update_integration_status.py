#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統合システムの状態を更新するスクリプト
実際の統合システムの状態を確認してintegration_status.jsonを更新
"""

import os
import sys
import json
from pathlib import Path

# Windows環境でのエンコーディング設定
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# パスを追加
sys.path.insert(0, str(Path(__file__).parent))

# 環境変数の読み込み
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

def check_integration(name: str, module_name: str, class_name: str, init_args: dict = None) -> bool:
    """統合システムの利用可能性をチェック"""
    try:
        # ログ出力を完全に抑制
        import logging
        import sys
        from io import StringIO
        
        # ログハンドラーを一時的に無効化
        old_handlers = logging.root.handlers[:]
        logging.root.handlers = []
        
        # 標準出力も一時的に抑制
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            
            if init_args:
                instance = cls(**init_args)
            else:
                instance = cls()
            
            if hasattr(instance, 'is_available'):
                result = instance.is_available()
            else:
                result = True  # is_availableメソッドがない場合は利用可能とみなす
        finally:
            # 標準出力を戻す
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            # ログハンドラーを戻す
            logging.root.handlers = old_handlers
        
        return result
    except Exception:
        return False

def main():
    print("=" * 70)
    print("統合システム状態の更新")
    print("=" * 70)
    print()
    
    status = {
        "integrations": {}
    }
    
    # ComfyUI
    print("[ComfyUI] 確認中...")
    comfyui_available = check_integration("ComfyUI", "comfyui_integration", "ComfyUIIntegration")
    status["integrations"]["comfyui"] = {
        "available": comfyui_available,
        "type": "ComfyUIIntegration"
    }
    print(f"  {'[OK] 利用可能' if comfyui_available else '[NG] 利用不可'}")
    
    # Google Drive
    print("[Google Drive] 確認中...")
    drive_available = check_integration("Google Drive", "google_drive_integration", "GoogleDriveIntegration")
    status["integrations"]["google_drive"] = {
        "available": drive_available,
        "type": "GoogleDriveIntegration"
    }
    print(f"  {'[OK] 利用可能' if drive_available else '[NG] 利用不可'}")
    
    # CivitAI
    print("[CivitAI] 確認中...")
    civitai_available = check_integration(
        "CivitAI", 
        "civitai_integration", 
        "CivitAIIntegration",
        {"api_key": os.getenv("CIVITAI_API_KEY")}
    )
    status["integrations"]["civitai"] = {
        "available": civitai_available,
        "type": "CivitAIIntegration"
    }
    print(f"  {'[OK] 利用可能' if civitai_available else '[NG] 利用不可'}")
    
    # LangChain
    print("[LangChain] 確認中...")
    langchain_available = check_integration("LangChain", "langchain_integration", "LangChainIntegration")
    status["integrations"]["langchain"] = {
        "available": langchain_available,
        "type": "LangChainIntegration"
    }
    print(f"  {'[OK] 利用可能' if langchain_available else '[NG] 利用不可'}")
    
    # LangGraph
    print("[LangGraph] 確認中...")
    langgraph_available = check_integration("LangGraph", "langchain_integration", "LangGraphIntegration")
    status["integrations"]["langgraph"] = {
        "available": langgraph_available,
        "type": "LangGraphIntegration"
    }
    print(f"  {'[OK] 利用可能' if langgraph_available else '[NG] 利用不可'}")
    
    # Obsidian
    print("[Obsidian] 確認中...")
    obsidian_vault = os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
    obsidian_available = check_integration(
        "Obsidian",
        "obsidian_integration",
        "ObsidianIntegration",
        {"vault_path": obsidian_vault}
    )
    status["integrations"]["obsidian"] = {
        "available": obsidian_available,
        "type": "ObsidianIntegration"
    }
    print(f"  {'[OK] 利用可能' if obsidian_available else '[NG] 利用不可'}")
    
    # GitHub
    print("[GitHub] 確認中...")
    github_available = check_integration(
        "GitHub",
        "github_integration",
        "GitHubIntegration",
        {"token": os.getenv("GITHUB_TOKEN")}
    )
    status["integrations"]["github"] = {
        "available": github_available,
        "type": "GitHubIntegration"
    }
    print(f"  {'[OK] 利用可能' if github_available else '[NG] 利用不可'}")
    
    # Rows
    print("[Rows] 確認中...")
    rows_available = check_integration("Rows", "rows_integration", "RowsIntegration")
    status["integrations"]["rows"] = {
        "available": rows_available,
        "type": "RowsIntegration"
    }
    print(f"  {'[OK] 利用可能' if rows_available else '[NG] 利用不可'}")
    
    # Mem0
    print("[Mem0] 確認中...")
    mem0_available = check_integration("Mem0", "mem0_integration", "Mem0Integration")
    status["integrations"]["mem0"] = {
        "available": mem0_available,
        "type": "Mem0Integration"
    }
    print(f"  {'[OK] 利用可能' if mem0_available else '[NG] 利用不可'}")
    
    # SVI × Wan 2.2
    print("[SVI × Wan 2.2] 確認中...")
    try:
        svi_available = check_integration("SVI × Wan 2.2", "svi_wan22_video_integration", "SVIWan22VideoIntegration")
    except:
        svi_available = False
    status["integrations"]["svi_wan22"] = {
        "available": svi_available,
        "type": "SVIWan22VideoIntegration"
    }
    print(f"  {'[OK] 利用可能' if svi_available else '[NG] 利用不可'}")
    
    # その他の統合（オプション）
    # LLM Routing
    print("[LLM Routing] 確認中...")
    try:
        llm_routing_available = check_integration("LLM Routing", "llm_routing", "LLMRouter")
    except:
        llm_routing_available = False
    status["integrations"]["llm_routing"] = {
        "available": llm_routing_available,
        "type": "LLMRouter"
    }
    print(f"  {'[OK] 利用可能' if llm_routing_available else '[NG] 利用不可'}")
    
    # Local LLM
    print("[Local LLM] 確認中...")
    try:
        local_llm_available = check_integration("Local LLM", "local_llm_unified", "LocalLLMUnified")
    except:
        local_llm_available = False
    status["integrations"]["local_llm"] = {
        "available": local_llm_available,
        "type": "LocalLLMUnified"
    }
    print(f"  {'[OK] 利用可能' if local_llm_available else '[NG] 利用不可'}")
    
    # Memory Unified
    print("[Memory Unified] 確認中...")
    try:
        memory_unified_available = check_integration("Memory Unified", "memory_unified", "UnifiedMemory")
    except:
        memory_unified_available = False
    status["integrations"]["memory_unified"] = {
        "available": memory_unified_available,
        "type": "UnifiedMemory"
    }
    print(f"  {'[OK] 利用可能' if memory_unified_available else '[NG] 利用不可'}")
    
    # Notification Hub
    print("[Notification Hub] 確認中...")
    try:
        notification_hub_available = check_integration("Notification Hub", "notification_hub", "NotificationHub")
    except:
        notification_hub_available = False
    status["integrations"]["notification_hub"] = {
        "available": notification_hub_available,
        "type": "NotificationHub"
    }
    print(f"  {'[OK] 利用可能' if notification_hub_available else '[NG] 利用不可'}")
    
    # Secretary
    print("[Secretary] 確認中...")
    try:
        secretary_available = check_integration("Secretary", "secretary_routines", "SecretaryRoutines")
    except:
        secretary_available = False
    status["integrations"]["secretary"] = {
        "available": secretary_available,
        "type": "SecretaryRoutines"
    }
    print(f"  {'[OK] 利用可能' if secretary_available else '[NG] 利用不可'}")
    
    # Image Stock
    print("[Image Stock] 確認中...")
    try:
        image_stock_available = check_integration("Image Stock", "image_stock", "ImageStock")
    except:
        image_stock_available = False
    status["integrations"]["image_stock"] = {
        "available": image_stock_available,
        "type": "ImageStock"
    }
    print(f"  {'[OK] 利用可能' if image_stock_available else '[NG] 利用不可'}")
    
    # 状態を保存
    status_path = Path(__file__).parent / "integration_status.json"
    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=4, ensure_ascii=False)
    
    print()
    print("=" * 70)
    print("状態を更新しました")
    print("=" * 70)
    
    # サマリー
    available_count = sum(1 for v in status["integrations"].values() if v.get("available", False))
    total_count = len(status["integrations"])
    print(f"  利用可能: {available_count}/{total_count}")
    print(f"  状態ファイル: {status_path}")
    print()

if __name__ == "__main__":
    main()
