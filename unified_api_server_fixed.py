"""
ManaOS統合APIサーバー（修正版）
すべての外部システム統合を管理する統合API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# ロギング設定（最初に設定）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
try:
    from dotenv import load_dotenv
    # .envファイルを読み込む
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# 統合モジュールのインポート（すべてオプション）
COMFYUI_AVAILABLE = False
GOOGLE_DRIVE_AVAILABLE = False
CIVITAI_AVAILABLE = False
LANGCHAIN_AVAILABLE = False
MEM0_AVAILABLE = False
OBSIDIAN_AVAILABLE = False
LOCAL_LLM_AVAILABLE = False

# ComfyUI統合（オプション）
try:
    from comfyui_integration import ComfyUIIntegration
    COMFYUI_AVAILABLE = True
except ImportError:
    logger.warning("ComfyUI統合モジュールが見つかりません")

# GoogleDrive統合（オプション）
try:
    from google_drive_integration import GoogleDriveIntegration
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    logger.warning("GoogleDrive統合モジュールが見つかりません")

# CivitAI統合（オプション）
try:
    from civitai_integration import CivitAIIntegration
    CIVITAI_AVAILABLE = True
except ImportError:
    logger.warning("CivitAI統合モジュールが見つかりません")

# LangChain統合（オプション）
try:
    from langchain_integration import LangChainIntegration, LangGraphIntegration
    LANGCHAIN_AVAILABLE = True
except ImportError:
    logger.warning("LangChain統合モジュールが見つかりません")

# Mem0統合（オプション）
try:
    from mem0_integration import Mem0Integration
    MEM0_AVAILABLE = True
except ImportError:
    logger.warning("Mem0統合モジュールが見つかりません")

# Obsidian統合（オプション）
try:
    from obsidian_integration import ObsidianIntegration
    OBSIDIAN_AVAILABLE = True
except ImportError:
    logger.warning("Obsidian統合モジュールが見つかりません")

# ローカルLLM統合（オプション）
try:
    from local_llm_unified import LocalLLMUnified
    LOCAL_LLM_AVAILABLE = True
except ImportError:
    logger.warning("LocalLLM統合モジュールが見つかりません")

app = Flask(__name__)
CORS(app)

# 統合システムのインスタンス
integrations: Dict[str, Any] = {}


def initialize_integrations():
    """統合システムを初期化"""
    global integrations
    
    # ComfyUI統合（オプション）
    if COMFYUI_AVAILABLE:
        try:
            integrations["comfyui"] = ComfyUIIntegration(
                base_url=os.getenv("COMFYUI_URL", "http://localhost:8188")
            )
            logger.info("ComfyUI統合を初期化しました")
        except Exception as e:
            logger.warning(f"ComfyUI統合の初期化に失敗: {e}")
    
    # Google Drive統合（オプション）
    if GOOGLE_DRIVE_AVAILABLE:
        try:
            integrations["google_drive"] = GoogleDriveIntegration(
                credentials_path=os.getenv("GOOGLE_DRIVE_CREDENTIALS", "credentials.json"),
                token_path=os.getenv("GOOGLE_DRIVE_TOKEN", "token.json")
            )
            logger.info("GoogleDrive統合を初期化しました")
        except Exception as e:
            logger.warning(f"GoogleDrive統合の初期化に失敗: {e}")
    
    # CivitAI統合（オプション）
    if CIVITAI_AVAILABLE:
        try:
            integrations["civitai"] = CivitAIIntegration(
                api_key=os.getenv("CIVITAI_API_KEY")
            )
            logger.info("CivitAI統合を初期化しました")
        except Exception as e:
            logger.warning(f"CivitAI統合の初期化に失敗: {e}")
    
    # LangChain統合（オプション）
    if LANGCHAIN_AVAILABLE:
        try:
            integrations["langchain"] = LangChainIntegration(
                ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
                model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
            )
            integrations["langgraph"] = LangGraphIntegration(
                ollama_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
                model_name=os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
            )
            logger.info("LangChain/LangGraph統合を初期化しました")
        except Exception as e:
            logger.warning(f"LangChain統合の初期化に失敗: {e}")
    
    # Mem0統合（オプション）
    if MEM0_AVAILABLE:
        try:
            integrations["mem0"] = Mem0Integration()
            logger.info("Mem0統合を初期化しました")
        except Exception as e:
            logger.warning(f"Mem0統合の初期化に失敗: {e}")
    
    # Obsidian統合（オプション）
    if OBSIDIAN_AVAILABLE:
        try:
            integrations["obsidian"] = ObsidianIntegration(
                vault_path=os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
            )
            logger.info("Obsidian統合を初期化しました")
        except Exception as e:
            logger.warning(f"Obsidian統合の初期化に失敗: {e}")
    
    # ローカルLLM統合
    if LOCAL_LLM_AVAILABLE:
        try:
            integrations["local_llm"] = LocalLLMUnified()
            logger.info("ローカルLLM統合を初期化しました")
        except Exception as e:
            logger.warning(f"ローカルLLM統合の初期化に失敗: {e}")


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    status = {}
    for name, integration in integrations.items():
        status[name] = integration.is_available() if hasattr(integration, "is_available") else False
    
    return jsonify({
        "status": "ok",
        "integrations": status
    })


@app.route("/api/comfyui/generate", methods=["POST"])
def comfyui_generate():
    """ComfyUIで画像生成"""
    data = request.json
    prompt = data.get("prompt", "")
    negative_prompt = data.get("negative_prompt", "")
    width = data.get("width", 512)
    height = data.get("height", 512)
    steps = data.get("steps", 20)
    cfg_scale = data.get("cfg_scale", 7.0)
    seed = data.get("seed", -1)
    
    comfyui = integrations.get("comfyui")
    if not comfyui or not comfyui.is_available():
        return jsonify({"error": "ComfyUIが利用できません"}), 503
    
    prompt_id = comfyui.generate_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=cfg_scale,
        seed=seed
    )
    
    if prompt_id:
        return jsonify({"prompt_id": prompt_id, "status": "success"})
    else:
        return jsonify({"error": "画像生成に失敗しました"}), 500


@app.route("/api/google_drive/upload", methods=["POST"])
def google_drive_upload():
    """Google Driveにファイルをアップロード"""
    data = request.json
    file_path = data.get("file_path", "")
    folder_id = data.get("folder_id")
    
    google_drive = integrations.get("google_drive")
    if not google_drive or not google_drive.is_available():
        return jsonify({"error": "GoogleDriveが利用できません"}), 503
    
    file_id = google_drive.upload_file(file_path, folder_id)
    
    if file_id:
        return jsonify({"file_id": file_id, "status": "success"})
    else:
        return jsonify({"error": "アップロードに失敗しました"}), 500


@app.route("/api/civitai/search", methods=["GET"])
def civitai_search():
    """CivitAIでモデルを検索"""
    query = request.args.get("query", "")
    limit = int(request.args.get("limit", 20))
    model_type = request.args.get("type")
    
    civitai = integrations.get("civitai")
    if not civitai:
        return jsonify({"error": "CivitAIが利用できません"}), 503
    
    models = civitai.search_models(query=query, limit=limit, model_type=model_type)
    return jsonify({"models": models, "count": len(models)})


@app.route("/api/langchain/chat", methods=["POST"])
def langchain_chat():
    """LangChainでチャット"""
    data = request.json
    message = data.get("message", "")
    system_prompt = data.get("system_prompt")
    
    langchain = integrations.get("langchain")
    if not langchain or not langchain.is_available():
        return jsonify({"error": "LangChainが利用できません"}), 503
    
    response = langchain.chat(message, system_prompt)
    return jsonify({"response": response, "status": "success"})


@app.route("/api/mem0/add", methods=["POST"])
def mem0_add():
    """Mem0にメモリを追加"""
    data = request.json
    memory_text = data.get("memory_text", "")
    user_id = data.get("user_id")
    metadata = data.get("metadata")
    
    mem0 = integrations.get("mem0")
    if not mem0 or not mem0.is_available():
        return jsonify({"error": "Mem0が利用できません"}), 503
    
    memory_id = mem0.add_memory(memory_text, user_id, metadata)
    
    if memory_id:
        return jsonify({"memory_id": memory_id, "status": "success"})
    else:
        return jsonify({"error": "メモリ追加に失敗しました"}), 500


@app.route("/api/obsidian/create", methods=["POST"])
def obsidian_create():
    """Obsidianにノートを作成"""
    data = request.json
    title = data.get("title", "")
    content = data.get("content", "")
    tags = data.get("tags", [])
    folder = data.get("folder")
    
    obsidian = integrations.get("obsidian")
    if not obsidian or not obsidian.is_available():
        return jsonify({"error": "Obsidianが利用できません"}), 503
    
    note_path = obsidian.create_note(title, content, tags, folder)
    
    if note_path:
        return jsonify({"note_path": str(note_path), "status": "success"})
    else:
        return jsonify({"error": "ノート作成に失敗しました"}), 500


@app.route("/api/integrations/status", methods=["GET"])
def integrations_status():
    """すべての統合システムの状態を取得"""
    status = {}
    
    for name, integration in integrations.items():
        if hasattr(integration, "is_available"):
            status[name] = {
                "available": integration.is_available(),
                "type": type(integration).__name__
            }
        else:
            status[name] = {
                "available": False,
                "type": type(integration).__name__
            }
    
    # ローカルLLMシステムの状態も追加
    if LOCAL_LLM_AVAILABLE and "local_llm" in integrations:
        try:
            llm_status = integrations["local_llm"].get_status()
            status["local_llm_systems"] = llm_status
        except:
            pass
    
    return jsonify({"integrations": status})


@app.route("/api/local-llm/systems", methods=["GET"])
def local_llm_systems():
    """ローカルLLMシステム一覧を取得"""
    if not LOCAL_LLM_AVAILABLE:
        return jsonify({"error": "ローカルLLM統合が利用できません"}), 503
    
    if "local_llm" not in integrations:
        return jsonify({"error": "ローカルLLMが初期化されていません"}), 503
    
    try:
        status = integrations["local_llm"].get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"ローカルLLMシステム取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("ManaOS統合APIサーバーを起動中...")
    initialize_integrations()
    
    port = int(os.getenv("MANAOS_INTEGRATION_PORT", 9500))
    host = os.getenv("MANAOS_INTEGRATION_HOST", "0.0.0.0")
    
    print(f"サーバー起動: http://{host}:{port}")
    print("利用可能なエンドポイント:")
    print("  GET  /health - ヘルスチェック")
    print("  GET  /api/integrations/status - 統合システム状態")
    print("  POST /api/comfyui/generate - ComfyUI画像生成")
    print("  POST /api/google_drive/upload - GoogleDriveアップロード")
    print("  GET  /api/civitai/search - CivitAI検索")
    print("  POST /api/langchain/chat - LangChainチャット")
    print("  POST /api/mem0/add - Mem0メモリ追加")
    print("  POST /api/obsidian/create - Obsidianノート作成")
    print("  GET  /api/local-llm/systems - ローカルLLMシステム一覧")
    
    app.run(host=host, port=port, debug=True)


















