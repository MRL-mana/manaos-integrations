"""
Pixel 7 ManaOS統合API
既存の秘書APIと統合してPixel 7からのリクエストを処理
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
import logging
import os
import httpx
import json
import subprocess
import platform
import psutil
from datetime import datetime
from pathlib import Path
from pixel7_adb_helper import Pixel7ADBHelper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pixel 7 ManaOS Integration API",
    description="Pixel 7とManaOSシステムの統合API",
    version="1.0.0"
)

# ADBヘルパー
adb_helper = Pixel7ADBHelper()

# 設定
SECRETARY_API_URL = os.getenv("SECRETARY_API_URL", "http://127.0.0.1:8080")
PIXEL7_HUB_URL = os.getenv("PIXEL7_HUB_URL", "http://127.0.0.1:9405")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
API_KEY = os.getenv("PIXEL7_API_KEY", "")

# チャット履歴の保存先
CHAT_HISTORY_DIR = Path(os.getenv("CHAT_HISTORY_DIR", "./chat_history"))
CHAT_HISTORY_DIR.mkdir(exist_ok=True)


class Pixel7SecretaryRequest(BaseModel):
    """Pixel 7からの秘書リクエスト"""
    user: str = "mana"
    text: str
    source: str = "pixel7"
    device_id: Optional[str] = None
    timestamp: Optional[float] = None
    intent: Optional[str] = None


class Pixel7CommandRequest(BaseModel):
    """Pixel 7からのコマンドリクエスト"""
    command: str
    parameters: Optional[Dict] = None


class Pixel7LLMChatRequest(BaseModel):
    """Pixel 7からのLLMチャットリクエスト"""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    stream: bool = False
    system_message: Optional[str] = None
    session_id: Optional[str] = None
    save_history: bool = True


class RemoteCommandRequest(BaseModel):
    """リモートコマンド実行リクエスト"""
    command: str
    parameters: Optional[Dict] = None
    timeout: Optional[int] = 30


class RemoteFileRequest(BaseModel):
    """リモートファイル操作リクエスト"""
    path: str
    action: str  # read, write, list, delete
    content: Optional[str] = None


@app.post("/pixel7/secretary")
async def pixel7_secretary(
    request: Pixel7SecretaryRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Pixel 7からの秘書リクエストを処理
    
    既存の秘書APIに転送し、必要に応じてPixel 7に通知を送信
    """
    # API Key認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        # デバイスIDを自動取得（指定されていない場合）
        if not request.device_id:
            device_id = adb_helper.find_pixel7()
            if device_id:
                request.device_id = device_id
        
        # タイムスタンプ設定
        if not request.timestamp:
            request.timestamp = datetime.now().timestamp()
        
        # 既存の秘書APIに転送
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                secretary_payload = {
                    "user": request.user,
                    "text": request.text,
                    "source": request.source,
                    "timestamp": request.timestamp,
                    "intent": request.intent
                }
                
                response = await client.post(
                    f"{SECRETARY_API_URL}/secretary",
                    json=secretary_payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 必要に応じてPixel 7に通知を送信
                    if request.device_id and result.get("message"):
                        try:
                            adb_helper.send_notification(
                                title="ManaOS秘書",
                                text=result.get("message", "処理完了")
                            )
                        except Exception as e:
                            logger.warning(f"Failed to send notification: {e}")
                    
                    return {
                        "success": True,
                        "device_id": request.device_id,
                        "secretary_response": result,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Secretary API error: {response.text}"
                    )
            except httpx.RequestError as e:
                logger.error(f"Secretary API request failed: {e}")
                raise HTTPException(
                    status_code=503,
                    detail="Secretary API is not available"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pixel7 secretary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pixel7/command")
async def pixel7_command(
    request: Pixel7CommandRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Pixel 7からコマンドを実行
    
    例:
    - "screenshot": スクリーンショット取得
    - "battery": バッテリー情報取得
    - "notification": 通知送信
    """
    # API Key認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        device_id = adb_helper.find_pixel7()
        if not device_id:
            raise HTTPException(status_code=404, detail="Pixel 7 not connected")
        
        command = request.command.lower()
        params = request.parameters or {}
        
        if command == "screenshot":
            # スクリーンショット取得
            screenshot_path = adb_helper.take_screenshot()
            return {
                "success": True,
                "command": command,
                "result": {
                    "screenshot_path": screenshot_path
                },
                "timestamp": datetime.now().isoformat()
            }
        
        elif command == "battery":
            # バッテリー情報取得
            battery_info = adb_helper.get_battery_info()
            return {
                "success": True,
                "command": command,
                "result": battery_info,
                "timestamp": datetime.now().isoformat()
            }
        
        elif command == "notification":
            # 通知送信
            title = params.get("title", "ManaOS")
            text = params.get("text", "")
            success = adb_helper.send_notification(title=title, text=text)
            return {
                "success": success,
                "command": command,
                "result": {
                    "notification_sent": success
                },
                "timestamp": datetime.now().isoformat()
            }
        
        elif command == "info":
            # デバイス情報取得
            info = adb_helper.get_device_info()
            return {
                "success": True,
                "command": command,
                "result": info,
                "timestamp": datetime.now().isoformat()
            }
        
        else:
            # カスタムコマンド実行
            result = adb_helper.execute_command(request.command)
            return {
                "success": result is not None,
                "command": command,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pixel7 command error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/status")
async def pixel7_status():
    """Pixel 7の状態を取得"""
    try:
        device_id = adb_helper.find_pixel7()
        device_info = adb_helper.get_device_info() if device_id else None
        
        return {
            "connected": device_id is not None,
            "device_id": device_id,
            "device_info": device_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _load_chat_history(session_id: str) -> List[Dict[str, str]]:
    """チャット履歴を読み込む"""
    history_file = CHAT_HISTORY_DIR / f"{session_id}.json"
    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load chat history: {e}")
    return []


def _save_chat_history(session_id: str, messages: List[Dict[str, str]]):
    """チャット履歴を保存"""
    try:
        history_file = CHAT_HISTORY_DIR / f"{session_id}.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save chat history: {e}")


@app.post("/pixel7/llm/chat")
async def pixel7_llm_chat(
    request: Pixel7LLMChatRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Pixel 7からローカルLLM（Ollama）にチャット
    
    アンドロイド端末から母艦のローカルLLMに接続してチャットできます
    
    チャット履歴機能:
    - session_idを指定すると、過去の会話を読み込んで続きから会話できます
    - save_history=trueの場合、会話を保存します
    """
    # API Key認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        # セッションIDを生成（指定されていない場合）
        session_id = request.session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # メッセージを構築
        messages = request.messages.copy()
        
        # チャット履歴を読み込む（セッションIDが指定されている場合）
        if request.session_id:
            history = _load_chat_history(session_id)
            if history:
                # 履歴の最後のN件を使用（最新の会話を優先）
                messages = history[-10:] + messages  # 最新10件の履歴 + 新しいメッセージ
        
        # システムメッセージを追加（指定されている場合）
        if request.system_message:
            # システムメッセージが既にない場合のみ追加
            if not any(msg.get("role") == "system" for msg in messages):
                messages.insert(0, {
                    "role": "system",
                    "content": request.system_message
                })
        
        # デフォルトモデル
        model = request.model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        
        # ストリーミングの場合
        if request.stream:
            async def generate_stream():
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        async with client.stream(
                            "POST",
                            f"{OLLAMA_URL}/api/chat",
                            json={
                                "model": model,
                                "messages": messages,
                                "stream": True
                            }
                        ) as response:
                            if response.status_code != 200:
                                error_text = await response.aread()
                                yield f"data: {json.dumps({'error': error_text.decode()})}\n\n"
                                return
                            
                            async for line in response.aiter_lines():
                                if line:
                                    try:
                                        data = json.loads(line)
                                        content = data.get("message", {}).get("content", "")
                                        if content:
                                            yield f"data: {json.dumps({'content': content})}\n\n"
                                    except json.JSONDecodeError:
                                        pass
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(generate_stream(), media_type="text/event-stream")
        
        # 通常のリクエスト
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                response_content = data.get("message", {}).get("content", "")
                
                # チャット履歴を保存
                if request.save_history:
                    # ユーザーメッセージとアシスタントレスポンスを履歴に追加
                    history_messages = messages.copy()
                    history_messages.append({
                        "role": "assistant",
                        "content": response_content,
                        "timestamp": datetime.now().isoformat()
                    })
                    _save_chat_history(session_id, history_messages)
                
                return {
                    "success": True,
                    "model": model,
                    "response": response_content,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama API error: {response.text}"
                )
    
    except httpx.RequestError as e:
        logger.error(f"Ollama connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"ローカルLLMに接続できません: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/llm/models")
async def pixel7_llm_models(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """利用可能なローカルLLMモデル一覧を取得"""
    # API Key認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return {
                    "success": True,
                    "models": models,
                    "count": len(models),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ollama API error: {response.text}"
                )
    except httpx.RequestError as e:
        logger.error(f"Ollama connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"ローカルLLMに接続できません: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM models error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pixel7/llm/status")
async def pixel7_llm_status(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """ローカルLLMの接続状態を確認"""
    # API Key認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            
            connected = response.status_code == 200
            
            # モデル一覧も取得
            models = []
            if connected:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
            
            return {
                "connected": connected,
                "ollama_url": OLLAMA_URL,
                "models_count": len(models),
                "models": models[:5] if models else [],  # 最初の5つだけ表示
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        return {
            "connected": False,
            "ollama_url": OLLAMA_URL,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/pixel7/llm/history/{session_id}")
async def pixel7_llm_history(
    session_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """チャット履歴を取得"""
    # API Key認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    history = _load_chat_history(session_id)
    return {
        "success": True,
        "session_id": session_id,
        "messages": history,
        "count": len(history),
        "timestamp": datetime.now().isoformat()
    }


@app.delete("/pixel7/llm/history/{session_id}")
async def pixel7_llm_delete_history(
    session_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """チャット履歴を削除"""
    # API Key認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    history_file = CHAT_HISTORY_DIR / f"{session_id}.json"
    if history_file.exists():
        history_file.unlink()
        return {
            "success": True,
            "session_id": session_id,
            "message": "履歴を削除しました",
            "timestamp": datetime.now().isoformat()
        }
    else:
        raise HTTPException(status_code=404, detail="履歴が見つかりません")


@app.get("/pixel7/llm/history")
async def pixel7_llm_list_history(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """チャット履歴一覧を取得"""
    # API Key認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    sessions = []
    for history_file in CHAT_HISTORY_DIR.glob("*.json"):
        try:
            session_id = history_file.stem
            history = _load_chat_history(session_id)
            sessions.append({
                "session_id": session_id,
                "message_count": len(history),
                "last_message_time": history[-1].get("timestamp") if history else None,
                "created_time": history[0].get("timestamp") if history else None
            })
        except Exception as e:
            logger.warning(f"Failed to read session {history_file}: {e}")
    
    # 最新順にソート
    sessions.sort(key=lambda x: x.get("last_message_time") or "", reverse=True)
    
    return {
        "success": True,
        "sessions": sessions,
        "count": len(sessions),
        "timestamp": datetime.now().isoformat()
    }


# ==================== リモート操作機能 ====================

# 許可されたコマンドのホワイトリスト（セキュリティ）
ALLOWED_COMMANDS = {
    "system_info": "システム情報取得",
    "process_list": "プロセス一覧",
    "process_kill": "プロセス終了",
    "service_status": "サービス状態確認",
    "service_start": "サービス起動",
    "service_stop": "サービス停止",
    "file_read": "ファイル読み取り",
    "file_write": "ファイル書き込み",
    "file_list": "ディレクトリ一覧",
    "file_delete": "ファイル削除",
    "disk_usage": "ディスク使用量",
    "network_info": "ネットワーク情報",
    "screenshot": "スクリーンショット取得",
    "powershell": "PowerShellコマンド実行（制限付き）"
}


@app.post("/remote/command")
async def remote_command(
    request: RemoteCommandRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    アンドロイド端末から母艦のコマンドを実行
    
    セキュリティのため、許可されたコマンドのみ実行可能
    """
    # API Key認証（設定されている場合）
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        command = request.command.lower()
        params = request.parameters or {}
        timeout = request.timeout or 30
        
        if command == "system_info":
            # システム情報取得
            info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "hostname": platform.node(),
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total_gb": round(psutil.virtual_memory().total / 1024**3, 2),
                "memory_available_gb": round(psutil.virtual_memory().available / 1024**3, 2),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": {}
            }
            
            # ディスク使用量
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    info["disk_usage"][partition.mountpoint] = {
                        "total_gb": round(usage.total / 1024**3, 2),
                        "used_gb": round(usage.used / 1024**3, 2),
                        "free_gb": round(usage.free / 1024**3, 2),
                        "percent": usage.percent
                    }
                except:
                    pass
            
            return {
                "success": True,
                "command": command,
                "result": info,
                "timestamp": datetime.now().isoformat()
            }
        
        elif command == "process_list":
            # プロセス一覧
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except:
                    pass
            
            # CPU使用率でソート
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return {
                "success": True,
                "command": command,
                "result": processes[:50],  # 上位50件
                "count": len(processes),
                "timestamp": datetime.now().isoformat()
            }
        
        elif command == "process_kill":
            # プロセス終了
            pid = params.get("pid")
            if not pid:
                raise HTTPException(status_code=400, detail="pid parameter is required")
            
            try:
                proc = psutil.Process(int(pid))
                proc.terminate()
                proc.wait(timeout=5)
                return {
                    "success": True,
                    "command": command,
                    "result": {"pid": pid, "status": "terminated"},
                    "timestamp": datetime.now().isoformat()
                }
            except psutil.NoSuchProcess:
                raise HTTPException(status_code=404, detail=f"Process {pid} not found")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        elif command == "service_status":
            # サービス状態確認
            service_name = params.get("name")
            if not service_name:
                raise HTTPException(status_code=400, detail="name parameter is required")
            
            try:
                if platform.system() == "Windows":
                    result = subprocess.run(
                        ["sc", "query", service_name],
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    return {
                        "success": True,
                        "command": command,
                        "result": {
                            "name": service_name,
                            "output": result.stdout,
                            "status": "running" if "RUNNING" in result.stdout else "stopped"
                        },
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    result = subprocess.run(
                        ["systemctl", "status", service_name],
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    return {
                        "success": True,
                        "command": command,
                        "result": {
                            "name": service_name,
                            "output": result.stdout,
                            "status": "running" if "active" in result.stdout else "stopped"
                        },
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        elif command == "file_list":
            # ディレクトリ一覧
            path = params.get("path", ".")
            try:
                path_obj = Path(path)
                if not path_obj.exists():
                    raise HTTPException(status_code=404, detail=f"Path not found: {path}")
                
                items = []
                for item in path_obj.iterdir():
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    })
                
                return {
                    "success": True,
                    "command": command,
                    "result": {
                        "path": str(path_obj.absolute()),
                        "items": items
                    },
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        elif command == "file_read":
            # ファイル読み取り
            path = params.get("path")
            if not path:
                raise HTTPException(status_code=400, detail="path parameter is required")
            
            try:
                path_obj = Path(path)
                if not path_obj.exists():
                    raise HTTPException(status_code=404, detail=f"File not found: {path}")
                
                if path_obj.is_dir():
                    raise HTTPException(status_code=400, detail="Path is a directory, not a file")
                
                # ファイルサイズ制限（10MB）
                if path_obj.stat().st_size > 10 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="File too large (max 10MB)")
                
                with open(path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                return {
                    "success": True,
                    "command": command,
                    "result": {
                        "path": str(path_obj.absolute()),
                        "content": content,
                        "size": path_obj.stat().st_size
                    },
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        elif command == "powershell":
            # PowerShellコマンド実行（制限付き）
            script = params.get("script")
            if not script:
                raise HTTPException(status_code=400, detail="script parameter is required")
            
            # 危険なコマンドをブロック
            dangerous_keywords = ["format", "del /f", "rm -rf", "shutdown", "restart"]
            if any(keyword in script.lower() for keyword in dangerous_keywords):
                raise HTTPException(status_code=403, detail="Dangerous command blocked")
            
            try:
                result = subprocess.run(
                    ["powershell", "-Command", script],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=False
                )
                
                return {
                    "success": result.returncode == 0,
                    "command": command,
                    "result": {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    },
                    "timestamp": datetime.now().isoformat()
                }
            except subprocess.TimeoutExpired:
                raise HTTPException(status_code=408, detail="Command timeout")
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown command: {command}. Allowed commands: {list(ALLOWED_COMMANDS.keys())}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remote command error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/remote/system")
async def remote_system_info(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """システム情報を取得"""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    try:
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "hostname": platform.node(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / 1024**3, 2),
                "available_gb": round(psutil.virtual_memory().available / 1024**3, 2),
                "used_gb": round(psutil.virtual_memory().used / 1024**3, 2),
                "percent": psutil.virtual_memory().percent
            },
            "disk": {},
            "network": []
        }
        
        # ディスク情報
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info["disk"][partition.mountpoint] = {
                    "total_gb": round(usage.total / 1024**3, 2),
                    "used_gb": round(usage.used / 1024**3, 2),
                    "free_gb": round(usage.free / 1024**3, 2),
                    "percent": usage.percent
                }
            except:
                pass
        
        # ネットワーク情報
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == 2:  # IPv4
                    info["network"].append({
                        "interface": interface,
                        "address": addr.address,
                        "netmask": addr.netmask
                    })
        
        return {
            "success": True,
            "system": info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"System info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/remote/commands")
async def remote_commands_list(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """利用可能なリモートコマンド一覧"""
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    return {
        "success": True,
        "commands": ALLOWED_COMMANDS,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    """ヘルスチェック"""
    adb_available = adb_helper.check_adb_available()
    device_id = adb_helper.find_pixel7()
    
    # LLM接続状態も確認
    llm_connected = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            llm_connected = response.status_code == 200
    except:
        pass
    
    return {
        "status": "healthy" if adb_available else "degraded",
        "adb_available": adb_available,
        "device_connected": device_id is not None,
        "device_id": device_id,
        "llm_connected": llm_connected,
        "ollama_url": OLLAMA_URL,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PIXEL7_INTEGRATION_PORT", "9406"))
    host = os.getenv("PIXEL7_INTEGRATION_HOST", "0.0.0.0")
    
    logger.info(f"Starting Pixel 7 Integration API on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )




