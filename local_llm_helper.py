#!/usr/bin/env python3
"""
ローカルLLM（Ollama）を簡単に呼び出すヘルパー関数
Cursorのチャットから直接使えるように設計
WSL2経由でGPUモードで実行可能
"""
import requests
import json
import subprocess
import os
from typing import Optional, Dict, Any, List

OLLAMA_URL = "http://localhost:11434"
LM_STUDIO_URL = "http://localhost:1234/v1"
USE_WSL2 = os.environ.get("OLLAMA_USE_WSL2", "true").lower() == "true"

def _should_use_lm_studio() -> bool:
    """LM Studioを使用すべきか判定（環境変数と起動状況を確認）"""
    use_lm_studio_env = os.environ.get("USE_LM_STUDIO", "false").strip().lower() in ("1", "true", "yes", "y", "on")
    if use_lm_studio_env:
        return _check_lm_studio()
    return False

def _check_lm_studio() -> bool:
    """LM Studioが起動しているか確認"""
    try:
        response = requests.get(f"{LM_STUDIO_URL}/models", timeout=2)
        return response.status_code == 200
    except:
        return False


def _check_wsl2_ollama() -> bool:
    """WSL2内でOllamaが起動しているか確認"""
    try:
        result = subprocess.run(
            ["wsl", "-d", "Ubuntu-22.04", "--", "bash", "-c", "curl -s http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=5,
            text=True
        )
        return result.returncode == 0 and "models" in result.stdout
    except:
        return False


def _check_windows_ollama() -> bool:
    """Windows版Ollamaが起動しているか確認"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


def _get_ollama_url() -> str:
    """使用するOllama URLを決定（WSL2優先）"""
    if USE_WSL2 and _check_wsl2_ollama():
        return OLLAMA_URL  # WSL2内のOllamaはlocalhost:11434でアクセス可能
    elif _check_windows_ollama():
        return OLLAMA_URL  # Windows版Ollama
    else:
        # どちらも起動していない場合はWSL2を試す
        return OLLAMA_URL


def chat(model: str = "qwen3:4b", message: str = "", messages: Optional[List[Dict]] = None,
         stream: bool = False, timeout: int = 120) -> Dict[str, Any]:
    """
    ローカルLLMとチャットする（WSL2経由でGPUモード対応）

    Args:
        model: 使用するモデル名（デフォルト: qwen3:4b）
        message: 単一のメッセージ（messagesがNoneの場合）
        messages: メッセージ履歴（[{"role": "user", "content": "..."}]形式）
        stream: ストリーミングするか（デフォルト: False）
        timeout: タイムアウト秒数（デフォルト: 120）

    Returns:
        LLMの応答を含む辞書
    """
    # LM Studioを優先使用（GPU対応、Windowsネイティブ）
    if _should_use_lm_studio():
        # LM Studio OpenAI互換API
        url = f"{LM_STUDIO_URL}/chat/completions"
        
        if messages is None:
            messages = [{"role": "user", "content": message}]
        
        data = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": 0.7
        }
        
        extended_timeout = max(timeout, 60)  # 大きいモデルの初回ロードを考慮
        try:
            response = requests.post(url, json=data, timeout=extended_timeout)

            if response.status_code != 200:
                # dict/str両対応でエラー抽出
                error_msg = ""
                try:
                    ed = response.json()
                    if isinstance(ed, dict):
                        err = ed.get("error", {})
                        if isinstance(err, dict):
                            error_msg = str(err.get("message", ""))[:200]
                        else:
                            error_msg = str(err)[:200]
                    else:
                        error_msg = str(ed)[:200]
                except Exception:
                    error_msg = (response.text or "")[:200]

                if "load" in error_msg.lower() or "not found" in error_msg.lower():
                    return {"error": "モデル未ロード", "message": f"モデル '{model}' がロードされていません。LM Studioでモデルをロードしてください。"}
                return {"error": f"HTTP {response.status_code}", "message": f"LM Studio APIエラー: {error_msg}"}

            result = response.json()
            if not isinstance(result, dict) or "choices" not in result:
                return {"error": "不正なレスポンス", "message": "LM Studioからの応答が不正です。"}

            content = result["choices"][0]["message"]["content"]
            return {"message": content, "model": model, "source": "lm_studio"}
        except requests.exceptions.Timeout:
            return {"error": "タイムアウト", "message": f"モデルのロード/推論に時間がかかっています（タイムアウト: {extended_timeout}秒）。LM Studioでモデルを事前にロードしてください。"}
        except Exception as e:
            return {"error": str(e), "message": f"LM Studioへの接続に失敗しました: {str(e)[:200]}"}
    
    # Ollama（WSL2優先）
    url = f"{_get_ollama_url()}/api/chat"

    if messages is None:
        messages = [{"role": "user", "content": message}]

    # GPU使用を強制（環境変数で制御可能）
    use_gpu = os.environ.get("OLLAMA_USE_GPU", "1").strip().lower() in ("1", "true", "yes", "y", "on")
    
    data = {
        "model": model,
        "messages": messages,
        "stream": stream
    }
    
    # GPU使用を強制する場合、optionsにnum_gpuを指定
    if use_gpu:
        data["options"] = {
            "num_gpu": 99  # 可能な限りGPUを使用
        }

    try:
        response = requests.post(url, json=data, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "タイムアウト", "message": "モデルのロードに時間がかかっています。もう一度試してください。"}
    except Exception as e:
        return {"error": str(e), "message": "ローカルLLMへの接続に失敗しました。"}


def generate(model: str = "qwen3:4b", prompt: str = "", stream: bool = False,
             timeout: int = 120) -> Dict[str, Any]:
    """
    ローカルLLMでテキスト生成する（LM Studio優先、WSL2経由でGPUモード対応）

    Args:
        model: 使用するモデル名（デフォルト: qwen3:4b）
        prompt: プロンプト
        stream: ストリーミングするか（デフォルト: False）
        timeout: タイムアウト秒数（デフォルト: 120）

    Returns:
        LLMの応答を含む辞書
    """
    # LM Studioを優先使用（GPU対応、Windowsネイティブ）
    if _should_use_lm_studio():
        # LM Studio OpenAI互換API
        url = f"{LM_STUDIO_URL}/chat/completions"
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream,
            "temperature": 0.7
        }
        
        try:
            # タイムアウトを延長（大きなモデルの読み込みに対応）
            extended_timeout = max(timeout, 60)  # 最低60秒
            response = requests.post(url, json=data, timeout=extended_timeout)
            
            # HTTPエラーチェック
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict):
                        error_msg = error_data.get('error', {})
                        if isinstance(error_msg, dict):
                            error_msg = error_msg.get('message', '')
                        elif isinstance(error_msg, str):
                            pass  # 既に文字列
                        else:
                            error_msg = str(error_msg)
                    else:
                        error_msg = str(error_data)
                except:
                    error_msg = response.text[:200] if response.text else f"HTTP {response.status_code}"
                
                if 'load' in error_msg.lower() or 'not found' in error_msg.lower():
                    return {"error": "モデル未ロード", "message": f"モデル '{model}' がロードされていません。LM Studioでモデルをロードしてください。"}
                return {"error": f"HTTP {response.status_code}", "message": f"LM Studio APIエラー: {error_msg[:200]}"}
            
            result = response.json()
            if not isinstance(result, dict) or 'choices' not in result:
                return {"error": "不正なレスポンス", "message": "LM Studioからの応答が不正です。"}
            
            return {
                "response": result["choices"][0]["message"]["content"],
                "model": model,
                "source": "lm_studio"
            }
        except requests.exceptions.Timeout:
            return {"error": "タイムアウト", "message": f"モデルのロードに時間がかかっています（タイムアウト: {extended_timeout}秒）。モデルが大きすぎるか、LM Studioでモデルを事前にロードしてください。"}
        except requests.exceptions.HTTPError as e:
            try:
                error_data = e.response.json() if e.response and e.response.content else {}
                if isinstance(error_data, dict):
                    error_msg = error_data.get('error', {})
                    if isinstance(error_msg, dict):
                        error_msg = error_msg.get('message', '')
                    elif isinstance(error_msg, str):
                        pass  # 既に文字列
                    else:
                        error_msg = str(error_msg)
                else:
                    error_msg = str(error_data)
            except:
                error_msg = str(e)
            
            if e.response and e.response.status_code == 400:
                if 'load' in error_msg.lower() or 'not found' in error_msg.lower():
                    return {"error": "モデル未ロード", "message": f"モデル '{model}' がロードされていません。LM Studioでモデルをロードしてください。"}
            return {"error": str(e), "message": f"LM Studioへの接続に失敗しました（HTTP {e.response.status_code if e.response else 'unknown'}）。"}
        except Exception as e:
            return {"error": str(e), "message": f"LM Studioへの接続に失敗しました: {str(e)[:200]}"}
    
    # Ollama（WSL2優先）
    url = f"{_get_ollama_url()}/api/generate"

    # GPU使用を強制（環境変数で制御可能）
    use_gpu = os.environ.get("OLLAMA_USE_GPU", "1").strip().lower() in ("1", "true", "yes", "y", "on")
    
    data = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }
    
    # GPU使用を強制する場合、optionsにnum_gpuを指定
    if use_gpu:
        data["options"] = {
            "num_gpu": 99  # 可能な限りGPUを使用
        }

    try:
        response = requests.post(url, json=data, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "タイムアウト", "message": "モデルのロードに時間がかかっています。"}
    except Exception as e:
        return {"error": str(e), "message": "ローカルLLMへの接続に失敗しました。"}


def list_models() -> List[str]:
    """インストール済みモデル一覧を取得（WSL2優先）"""
    try:
        url = _get_ollama_url()
        response = requests.get(f"{url}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]
    except Exception as e:
        print(f"モデル一覧の取得に失敗: {e}")
        return []


def check_status() -> Dict[str, Any]:
    """Ollamaの状態を確認（WSL2優先）"""
    try:
        url = _get_ollama_url()
        wsl2_running = _check_wsl2_ollama()
        windows_running = _check_windows_ollama()

        # モデル一覧を取得
        models = list_models()

        # 実行中のモデルを確認
        running_models = []
        try:
            response = requests.get(f"{url}/api/ps", timeout=5)
            if response.status_code == 200:
                data = response.json()
                running_models = [m["name"] for m in data.get("models", [])]
        except:
            pass

        # GPU使用状況を確認（WSL2の場合）
        gpu_mode = False
        if wsl2_running:
            try:
                result = subprocess.run(
                    ["wsl", "-d", "Ubuntu-22.04", "--", "ollama", "ps"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if "GPU" in result.stdout:
                    gpu_mode = True
            except:
                pass

        return {
            "status": "running",
            "available_models": models,
            "running_models": running_models,
            "url": url,
            "wsl2_running": wsl2_running,
            "windows_running": windows_running,
            "gpu_mode": gpu_mode
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Ollamaが起動していない可能性があります"
        }


# 簡単に使える関数
def ask(question: str, model: str = "qwen3:4b") -> str:
    """
    簡単に質問する関数

    Args:
        question: 質問内容
        model: 使用するモデル（デフォルト: qwen3:4b）

    Returns:
        回答テキスト
    """
    result = chat(model=model, message=question)

    if "error" in result:
        return f"エラー: {result.get('message', result.get('error', '不明なエラー'))}"

    # LM Studio: {"message": "<text>", ...}
    if isinstance(result.get("message"), str):
        return result["message"]
    # Ollama: {"message": {"content": "..."}}
    if isinstance(result.get("message"), dict) and "content" in result["message"]:
        return str(result["message"]["content"])
    # generate系の互換
    if isinstance(result.get("response"), str):
        return result["response"]

    return json.dumps(result, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # テスト実行
    print("=" * 60)
    print("ローカルLLMヘルパーのテスト")
    print("=" * 60)

    # 状態確認
    print("\n1. Ollamaの状態確認:")
    status = check_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))

    # 簡単な質問
    print("\n2. 簡単な質問テスト:")
    answer = ask("こんにちは、元気ですか？", model="qwen3:4b")
    print(answer)
