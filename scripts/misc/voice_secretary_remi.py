#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎤 秘書レミ完全体 - 音声会話システム
ホットワード「レミ」で呼び出せる音声秘書
"""

import os
import sys
import asyncio
import tempfile
import threading
import httpx
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from datetime import datetime

try:
    from manaos_integrations._paths import (
        INTENT_ROUTER_PORT, LLM_ROUTING_PORT, UNIFIED_API_PORT,
        PERSONALITY_SYSTEM_PORT, AUTONOMY_SYSTEM_PORT,
        RAG_MEMORY_PORT, LEARNING_SYSTEM_PORT, N8N_PORT,
        WINDOWS_AUTOMATION_PORT, PICO_HID_PORT,
    )
except Exception:  # pragma: no cover
    try:
        from _paths import (  # type: ignore
            INTENT_ROUTER_PORT, LLM_ROUTING_PORT, UNIFIED_API_PORT,
            PERSONALITY_SYSTEM_PORT, AUTONOMY_SYSTEM_PORT,
            RAG_MEMORY_PORT, LEARNING_SYSTEM_PORT, N8N_PORT,
            WINDOWS_AUTOMATION_PORT, PICO_HID_PORT,
        )
    except Exception:  # pragma: no cover
        UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))
        INTENT_ROUTER_PORT = int(os.getenv("INTENT_ROUTER_PORT", "5100"))
        LLM_ROUTING_PORT = int(os.getenv("LLM_ROUTING_PORT", "5117"))
        PERSONALITY_SYSTEM_PORT = int(os.getenv("PERSONALITY_SYSTEM_PORT", "5123"))
        AUTONOMY_SYSTEM_PORT = int(os.getenv("AUTONOMY_SYSTEM_PORT", "5124"))
        RAG_MEMORY_PORT = int(os.getenv("RAG_MEMORY_PORT", "5103"))
        LEARNING_SYSTEM_PORT = int(os.getenv("LEARNING_SYSTEM_PORT", "5126"))
        N8N_PORT = int(os.getenv("N8N_PORT", "5678"))
        WINDOWS_AUTOMATION_PORT = int(os.getenv("WINDOWS_AUTOMATION_PORT", "5115"))
        PICO_HID_PORT = int(os.getenv("PICO_HID_PORT", "5136"))

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from voice_integration import (
    create_stt_engine,
    create_tts_engine,
    VoiceConversationLoop
)
try:
    from unified_logging import get_service_logger  # type: ignore[import]
except (ImportError, PermissionError):
    from manaos_logger import get_service_logger  # type: ignore[import,no-redef]
logger = get_service_logger("voice-secretary-remi")

# 設定
INTENT_ROUTER_URL = os.getenv("INTENT_ROUTER_URL", f"http://127.0.0.1:{INTENT_ROUTER_PORT}")
UNIFIED_API_URL = os.getenv("UNIFIED_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")
LLM_ROUTING_URL = os.getenv("LLM_ROUTING_URL", f"http://127.0.0.1:{LLM_ROUTING_PORT}")
PERSONALITY_SYSTEM_URL = os.getenv("PERSONALITY_SYSTEM_URL", f"http://127.0.0.1:{PERSONALITY_SYSTEM_PORT}")
AUTONOMY_SYSTEM_URL = os.getenv("AUTONOMY_SYSTEM_URL", f"http://127.0.0.1:{AUTONOMY_SYSTEM_PORT}")
RAG_MEMORY_URL = os.getenv("RAG_MEMORY_URL", f"http://127.0.0.1:{RAG_MEMORY_PORT}")
LEARNING_SYSTEM_URL = os.getenv("LEARNING_SYSTEM_URL", f"http://127.0.0.1:{LEARNING_SYSTEM_PORT}")
N8N_URL = os.getenv("N8N_URL", f"http://127.0.0.1:{N8N_PORT}")
WINDOWS_AUTOMATION_URL = os.getenv("WINDOWS_AUTOMATION_URL", f"http://127.0.0.1:{WINDOWS_AUTOMATION_PORT}")
PICO_HID_URL = os.getenv("PICO_HID_URL", f"http://127.0.0.1:{PICO_HID_PORT}")
NOTION_AVAILABLE = os.getenv("NOTION_API_KEY") is not None
SLACK_AVAILABLE = os.getenv("SLACK_WEBHOOK_URL") is not None

# personality systemプロンプトのキャッシュ（起動後に一度取得して再利用）
_personality_prompt_cache: Optional[str] = None

# 会話セッション識別子（プロセス起動ごとに一意）
_CONVERSATION_SESSION_ID: str = datetime.now().strftime("remi_%Y%m%d%H%M%S")

# エピソード記憶インスタンス（遅延初期化）
_episodic_memory_instance = None

def _get_episodic_memory() -> "Optional[Any]":
    """EpisodicMemory インスタンスを遅延取得"""
    global _episodic_memory_instance
    if _episodic_memory_instance is None:
        try:
            from episodic_memory import get_episodic_memory
            _episodic_memory_instance = get_episodic_memory()
        except Exception:
            pass
    return _episodic_memory_instance

# autonomy systemに通知する intent の種別
_AUTONOMY_INTENT_TYPES = {"task_execution", "system_control", "scheduling"}
# N8N ワークフローを発火する intent の種別
_N8N_INTENT_TYPES = {"automation", "external_service", "notification", "webhook"}
# PC 操作系 intent の種別
_PC_CONTROL_INTENT_TYPES = {"system_control", "ui_operation", "window_control"}


async def _rag_search(query: str, top_k: int = 3) -> str:
    """RAG 長期記憶から関連コンテキストを検索（サービス未起動時は空文字列）"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{RAG_MEMORY_URL}/api/search",
                json={"query": query, "top_k": top_k},
            )
            if response.status_code == 200:
                results = response.json().get("results", [])
                if results:
                    return "\n".join(r.get("content", "") for r in results[:top_k])
    except Exception:
        pass
    return ""


def _episodic_recall(n: int = 5) -> str:
    """直近のエピソード記憶を取得して文字列で返す"""
    try:
        mem = _get_episodic_memory()
        if mem is None:
            return ""
        entries = mem.recall(limit=n, min_importance=0.0)
        if entries:
            return "\n---\n".join(e.content[:200] for e in reversed(entries[:n]))
    except Exception:
        pass
    return ""


async def _fetch_personality_prompt() -> Optional[str]:
    """personality systemからシステムプロンプトを取得（キャッシュ付き）"""
    global _personality_prompt_cache
    if _personality_prompt_cache is not None:
        return _personality_prompt_cache
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{PERSONALITY_SYSTEM_URL}/api/persona/apply",
                json={"prompt": "あなたはManaの音声AIアシスタント・レミです。", "context": "conversation"}
            )
            if response.status_code == 200:
                result = response.json()
                _personality_prompt_cache = result.get("enhanced_prompt")
                logger.info("✅ personality systemプロンプトを取得しました")
                return _personality_prompt_cache
    except Exception as e:
        logger.warning(f"personality system未接続、デフォルトプロンプトを使用: {e}")
    return None


def create_llm_callback():
    """LLM応答生成コールバックを作成（personality systemプロンプト注入）"""
    async def llm_chat_async(text: str) -> str:
        """非同期LLMチャット（personality systemプロンプト付き）"""
        try:
            # personality systemプロンプトを取得
            system_prompt = await _fetch_personality_prompt()

            # RAG + エピソード記憶からコンテキストを収集
            rag_context = await _rag_search(text)
            episodic_context = _episodic_recall(n=5)

            # LLMルーティングAPIにmessages形式で送信（personality + RAG + episodic 注入）
            async with httpx.AsyncClient(timeout=30.0) as client:
                messages = []
                # システムプロンプト統合（personality + 過去知識 + 会話履歴）
                system_parts = []
                if system_prompt:
                    system_parts.append(system_prompt)
                if rag_context:
                    system_parts.append(f"\n【関連する過去の知識】\n{rag_context}")
                if episodic_context:
                    system_parts.append(f"\n【直近の会話履歴】\n{episodic_context}")
                if system_parts:
                    messages.append({"role": "system", "content": "\n".join(system_parts)})
                messages.append({"role": "user", "content": text})

                response = await client.post(
                    f"{LLM_ROUTING_URL}/v1/chat/completions",
                    json={"model": "auto-local", "messages": messages}
                )
                if response.status_code == 200:
                    result = response.json()
                    # OpenAI互換フォーマット または routing形式の両方に対応
                    if "choices" in result:
                        return result["choices"][0]["message"]["content"]
                    return result.get("response", "すみません、応答を生成できませんでした。")

                # フォールバック: /api/route を使用
                response = await client.post(
                    f"{LLM_ROUTING_URL}/api/route",
                    json={"task_type": "conversation", "prompt": text}
                )
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "すみません、応答を生成できませんでした。")

                # 最終フォールバック: 統合API
                response = await client.post(
                    f"{UNIFIED_API_URL}/api/lfm25/chat",
                    json={"message": text}
                )
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "すみません、応答を生成できませんでした。")
        except Exception as e:
            logger.error(f"LLM呼び出しエラー: {e}")

        # 最終フォールバック
        return f"「{text}」についてですね。確認しました。"

    def llm_callback(text: str) -> str:
        """同期ラッパー"""
        return asyncio.run(llm_chat_async(text))

    return llm_callback


def create_intent_router_callback():
    """Intent Routerコールバックを作成"""
    async def classify_intent_async(text: str) -> Dict[str, Any]:
        """非同期意図分類"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{INTENT_ROUTER_URL}/api/classify",
                    json={"text": text}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Intent Router呼び出しエラー: {e}")
        
        return {"intent_type": "conversation", "confidence": 0.5}
    
    def intent_router_callback(text: str) -> Dict[str, Any]:
        """同期ラッパー"""
        return asyncio.run(classify_intent_async(text))
    
    return intent_router_callback
  # type: ignore

def create_task_registration_callback():
    """タスク自動登録コールバックを作成（タスクキュー + autonomy system 両方に通知）"""
    async def register_task_async(text: str, intent_result: Dict[str, Any]) -> bool:
        """非同期タスク登録"""
        intent_type = intent_result.get("intent_type", "task_execution")
        success = False
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. タスクキューシステムに登録
            try:
                response = await client.post(
                    f"{UNIFIED_API_URL}/api/task/queue/add",
                    json={
                        "input_text": text,
                        "intent_type": intent_type,
                        "priority": "medium",
                    }
                )
                if response.status_code == 200:
                    success = True
            except Exception as e:
                logger.warning(f"タスクキュー登録エラー: {e}")

            # 2. autonomy system にも通知（実行系 intent のみ）
            if intent_type in _AUTONOMY_INTENT_TYPES:
                try:
                    response = await client.post(
                        f"{AUTONOMY_SYSTEM_URL}/api/tasks",
                        json={
                            "task_type": intent_type,
                            "priority": "medium",
                            "condition": {"type": "always"},
                            "action": {"type": "voice_request", "input_text": text},
                        }
                    )
                    if response.status_code == 200:
                        logger.info(f"✅ autonomy systemにタスク通知: {intent_type}")
                except Exception as e:
                    logger.warning(f"autonomy system通知エラー: {e}")

            # 3. N8N ワークフロー発火（automation 系 intent）
            if intent_type in _N8N_INTENT_TYPES:
                try:
                    webhook_path = os.getenv("N8N_VOICE_WEBHOOK_PATH", "/webhook/voice-intent")
                    response = await client.post(
                        f"{N8N_URL}{webhook_path}",
                        json={
                            "intent_type": intent_type,
                            "text": text,
                            "session_id": _CONVERSATION_SESSION_ID,
                        },
                    )
                    if response.status_code in (200, 201):
                        logger.info(f"✅ N8N ワークフロー発火: {intent_type}")
                except Exception as e:
                    logger.debug(f"N8N 呼び出しエラー（サービス未起動?）: {e}")

            # 4. PC 操作（Windows Automation → Pico HID フォールバック）
            if intent_type in _PC_CONTROL_INTENT_TYPES:
                try:
                    response = await client.post(
                        f"{WINDOWS_AUTOMATION_URL}/api/control",
                        json={"command": text, "intent_type": intent_type, "source": "voice"},
                    )
                    if response.status_code == 200:
                        logger.info(f"✅ Windows Automation コマンド送信: {intent_type}")
                    else:
                        await client.post(
                            f"{PICO_HID_URL}/api/execute",
                            json={"command": text, "source": "voice"},
                        )
                except Exception as e:
                    logger.debug(f"PC操作エラー（サービス未起動?）: {e}")

        return success

    def task_registration_callback(text: str, intent_result: Dict[str, Any]) -> bool:
        """同期ラッパー"""
        return asyncio.run(register_task_async(text, intent_result))

    return task_registration_callback


def create_conversation_save_callback():
    """会話履歴保存コールバックを作成"""
    async def save_conversation_async(conversation_entry: Dict[str, Any]) -> None:
        """非同期会話履歴保存"""
        # Notionに保存
        if NOTION_AVAILABLE:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{UNIFIED_API_URL}/api/obsidian/create",
                        json={
                            "title": f"音声会話 - {conversation_entry['timestamp']}",
                            "content": f"**ユーザー**: {conversation_entry['user']}\n\n**レミ**: {conversation_entry['assistant']}\n\n**意図**: {conversation_entry.get('intent', 'unknown')}"
                        }
                    )
                    if response.status_code == 200:
                        logger.info("✅ 会話履歴をObsidianに保存しました")
            except Exception as e:
                logger.warning(f"Obsidian保存エラー: {e}")
        
        # Slackに通知（オプション）
        if SLACK_AVAILABLE:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        os.getenv("SLACK_WEBHOOK_URL"),  # type: ignore
                        json={
                            "text": f"🎤 音声会話\n**ユーザー**: {conversation_entry['user']}\n**レミ**: {conversation_entry['assistant']}"
                        }
                    )
                    if response.status_code == 200:
                        logger.info("✅ 会話履歴をSlackに送信しました")
            except Exception as e:
                logger.warning(f"Slack送信エラー: {e}")

        # エピソード記憶に保存（SQLite 直接）
        try:
            mem = _get_episodic_memory()
            if mem:
                mem.store(
                    content=(
                        f"ユーザー: {conversation_entry.get('user', '')}\n"
                        f"レミ: {conversation_entry.get('assistant', '')}"
                    ),
                    session_id=_CONVERSATION_SESSION_ID,
                    memory_type="conversation",
                    importance_score=0.5,
                )
        except Exception as e:
            logger.warning(f"エピソード記憶保存エラー: {e}")

        # Learning System に学習データを送信
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{LEARNING_SYSTEM_URL}/api/learn",
                    json={
                        "input": conversation_entry.get("user", ""),
                        "output": conversation_entry.get("assistant", ""),
                        "intent": conversation_entry.get("intent", "unknown"),
                        "session_id": _CONVERSATION_SESSION_ID,
                        "timestamp": conversation_entry.get("timestamp", datetime.now().isoformat()),
                    },
                )
                logger.debug("✅ Learning System に学習データを送信しました")
        except Exception as e:
            logger.debug(f"Learning System 送信エラー（サービス未起動?）: {e}")

    def conversation_save_callback(conversation_entry: Dict[str, Any]) -> None:
        """同期ラッパー"""
        asyncio.run(save_conversation_async(conversation_entry))
    
    return conversation_save_callback


# ========================================
# Pixel7 プロアクティブ監視（バッテリー自動通知）
# ========================================

class ProactivePixel7Watcher(threading.Thread):
    """Pixel7 のバッテリー状態を監視し、レミが自発的に喋る（5分ごと）"""

    _BATTERY_WARN_LEVELS = (20, 10, 5)  # 警告バッテリー残量 (%)

    def __init__(self, tts_engine: "Any", pixel7_io: "Optional[Any]" = None) -> None:
        super().__init__(daemon=True, name="ProactivePixel7Watcher")
        self.tts_engine = tts_engine
        self.pixel7_io = pixel7_io
        self._stop = threading.Event()
        self._warned_levels: set = set()
        self._last_battery: Optional[int] = None

    def stop(self) -> None:
        self._stop.set()

    def _speak(self, text: str) -> None:
        import time as _t
        try:
            audio_data = self.tts_engine.synthesize(text)
            if audio_data:
                out = Path(tempfile.gettempdir()) / f"remi_alert_{int(_t.time())}.wav"
                out.write_bytes(audio_data)
                if self.pixel7_io:
                    self.pixel7_io.speak(out)
        except Exception as e:
            logger.warning(f"proactive_speak error: {e}")
        logger.info(f"[レミ 🔔] {text}")

    def _get_battery_level(self) -> Optional[int]:
        import re
        try:
            from pixel7_jarvis_io import _run_adb
            r = _run_adb(["shell", "dumpsys battery"], timeout=5)
            if r.returncode == 0:
                m = re.search(r"level:\s*(\d+)", r.stdout)
                if m:
                    return int(m.group(1))
        except Exception:
            pass
        return None

    def run(self) -> None:
        while not self._stop.wait(timeout=300):  # 5分ごとにチェック
            battery = self._get_battery_level()
            if battery is not None and battery != self._last_battery:
                self._last_battery = battery
                for lvl in self._BATTERY_WARN_LEVELS:
                    if battery <= lvl and lvl not in self._warned_levels:
                        self._warned_levels.add(lvl)
                        suffix = "今すぐ充電をお願いします！" if battery <= 10 else "充電してください。"
                        self._speak(
                            f"マナさん、Pixel7 のバッテリーが残り {battery}% です。{suffix}"
                        )
                        break


# ========================================
# Pixel7 モード: ADB 経由 I/O ループ
# ========================================

def _run_pixel7_loop(
    pixel7_io: "Any",
    stt_engine: "Any",
    tts_engine: "Any",
    llm_callback: "Callable[[str], str]",
) -> None:
    """Pixel7 をマイク・スピーカーとして使う会話ループ"""
    import time
    import json

    # 会話ログファイル（日付付き）
    _log_dir = Path(os.getenv("JARVIS_LOG_DIR", Path(__file__).parent.parent.parent / "logs"))
    _log_dir.mkdir(parents=True, exist_ok=True)
    _conv_log = _log_dir / f"jarvis_conv_{datetime.now().strftime('%Y%m%d')}.jsonl"

    def _save_turn(user: str, assistant: str) -> None:
        """会話を JSONL に追記保存"""
        entry = {
            "ts": datetime.now().isoformat(),
            "user": user,
            "assistant": assistant,
        }
        with open(_conv_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def stt_fn(wav_path: "Path") -> str:
        result = stt_engine.transcribe(wav_path.read_bytes())
        return result.get("text", "")

    def tts_fn(text: str) -> "Optional[Path]":
        audio_data = tts_engine.synthesize(text)
        if audio_data:
            out = Path(tempfile.gettempdir()) / f"remi_tts_{int(time.time())}.wav"
            out.write_bytes(audio_data)
            return _apply_voice_filter(out)
        return None

    def _apply_voice_filter(wav_path: "Path") -> "Path":
        """So-VITS-SVC による声質変換（torch + so_vits_svc_fork が必要）
        未インストールなら原音声をそのまま返す。
        モデルパスは VOICE_SVC_MODEL 環境変数で指定。
        """
        model_path = os.getenv("VOICE_SVC_MODEL", "")
        if not model_path:
            return wav_path
        try:
            import so_vits_svc_fork.inference.main as _svc  # type: ignore
            out_path = wav_path.with_suffix(".svc.wav")
            _svc.infer(
                input_path=wav_path,
                output_path=out_path,
                model_path=model_path,
                transpose=int(os.getenv("VOICE_SVC_TRANSPOSE", "0")),
                auto_predict_f0=True,
                cluster_infer_ratio=0.0,
            )
            if out_path.exists() and out_path.stat().st_size > 1000:
                logger.debug("🎤 SVC 変換完了")
                return out_path
        except ImportError:
            pass  # torch/so_vits_svc_fork 未インストール → スキップ
        except Exception as e:
            logger.debug(f"SVC 変換失敗（スキップ）: {e}")
        return wav_path

    def _run_ssh_cmd(cmd: str, timeout: int = 3) -> None:
        """SSH コマンドをサイレント実行（失敗は無視）"""
        try:
            if hasattr(pixel7_io, '_run_ssh'):
                pixel7_io._run_ssh(cmd)
            else:
                from pixel7_jarvis_io import _run_ssh as _p7_ssh  # type: ignore
                _p7_ssh(cmd, timeout=timeout)
        except Exception:
            pass

    def _vibrate_pixel7() -> None:
        """録音開始前に Pixel7 を振動させ、通知バナーを表示"""
        _run_ssh_cmd(
            "termux-vibrate -d 200 2>/dev/null || true && "
            "termux-notification --id 9001 --title 'JARVIS' "
            "--content '🎤 聞いています...' "
            "--icon microphone --priority high --alert-once 2>/dev/null || true",
            timeout=4,
        )

    def _notify_pixel7(title: str, content: str) -> None:
        """Pixel7 に通知バナーを送る（バイブなし）"""
        # シェルインジェクション防止: title/content を単純 ASCII に制限
        _safe = content[:60].replace("'", "").replace('"', "").replace("`", "")
        _t = title.replace("'", "").replace('"', "")
        _run_ssh_cmd(
            f"termux-notification --id 9002 --title '{_t}' "
            f"--content '{_safe}' --icon check --priority default 2>/dev/null || true",
            timeout=4,
        )

    logger.info("📱 Pixel7 JARVIS I/O ループ 開始")
    logger.info("💡 Pixel7 のマイクに話しかけてください")
    logger.info(f"📝 会話ログ: {_conv_log}")
    logger.info("🛑 停止するには Ctrl+C")

    silence_count = 0
    while True:
        _vibrate_pixel7()  # 録音開始の合図（バイブ + 通知バナー）
        result = pixel7_io.run_voice_turn(stt_fn, llm_callback, tts_fn)
        if result.get("user"):
            silence_count = 0
            logger.info(f"[ユーザー] {result['user']}")
            logger.info(f"[レミ]     {result['assistant']}")
            _save_turn(result["user"], result["assistant"])
            # 応答内容を通知バナーに表示
            _notify_pixel7("レミ", result["assistant"])
        else:
            silence_count += 1
            if silence_count % 6 == 0:  # 約30秒ごとに生存ログ
                logger.info(f"🔇 待機中... (無音 {silence_count} 回連続)")
        time.sleep(0.5)


def main() -> None:
    """メイン関数"""
    import argparse
    import time

    parser = argparse.ArgumentParser(description="秘書レミ完全体")
    parser.add_argument(
        "--pixel7", action="store_true",
        help="Pixel7 の ADB マイク/スピーカーを使う"
    )
    parser.add_argument(
        "--pixel7-camera", action="store_true",
        help="Pixel7 カメラで Vision 入力も有効化"
    )
    parser.add_argument(
        "--record-sec", type=int, default=5,
        help="Pixel7 1回の録音秒数（デフォルト: 5）"
    )
    args = parser.parse_args()

    use_pixel7 = args.pixel7 or bool(os.getenv("REMI_USE_PIXEL7", ""))

    logger.info("🤖 ManaOS JARVISパイプライン 起動中...")
    if use_pixel7:
        logger.info("   📱 Pixel7 I/O → STT → Intent Router → [Autonomy/LLM+Personality] → Pixel7 スピーカー")
    else:
        logger.info("   音声入力 → STT → Intent Router → [Autonomy/LLM+Personality] → VOICEVOX → 音声出力")

    # エンジン初期化（Pixel7モードはデフォルトを軽量設定に変更）
    _default_model = "small" if use_pixel7 else "large-v3"
    _default_device = "cpu" if use_pixel7 else "cuda"
    _default_compute = "int8" if use_pixel7 else "float16"
    logger.info("📦 STTエンジンを初期化中...")
    stt_engine = create_stt_engine(
        model_size=os.getenv("VOICE_STT_MODEL", _default_model),
        device=os.getenv("VOICE_STT_DEVICE", _default_device),
        compute_type=os.getenv("VOICE_STT_COMPUTE_TYPE", _default_compute)
    )

    logger.info("📦 TTSエンジンを初期化中...")
    tts_engine = create_tts_engine(
        engine=os.getenv("VOICE_TTS_ENGINE", "voicevox"),
        voicevox_url=os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021"),
        speaker_id=int(os.getenv("VOICEVOX_SPEAKER_ID", "3"))
    )

    # コールバック作成
    logger.info("🔗 コールバックを設定中...")
    logger.info(f"   - personality system: {PERSONALITY_SYSTEM_URL}")
    logger.info(f"   - autonomy system:    {AUTONOMY_SYSTEM_URL}")
    logger.info(f"   - intent router:      {INTENT_ROUTER_URL}")
    logger.info(f"   - LLM routing:        {LLM_ROUTING_URL}")
    llm_callback = create_llm_callback()
    intent_router_callback = create_intent_router_callback()
    task_registration_callback = create_task_registration_callback()
    conversation_save_callback = create_conversation_save_callback()

    # ========== Pixel7 モード ==========
    if use_pixel7:
        try:
            from pixel7_jarvis_io import Pixel7JarvisIO
        except ImportError:
            from scripts.misc.pixel7_jarvis_io import Pixel7JarvisIO  # type: ignore

        pixel7_io = Pixel7JarvisIO(
            record_duration=args.record_sec,
            use_front_camera=args.pixel7_camera,
            auto_ensure_sshd=True,
            reconnect_retries=int(os.getenv("PIXEL7_RECONNECT_RETRIES", "5")),
            reconnect_wait=float(os.getenv("PIXEL7_RECONNECT_WAIT", "10")),
        )

        if not pixel7_io.is_connected():
            logger.warning("⚠️  Pixel7 未接続。接続を待機します（最大50秒）...")
            if not pixel7_io.wait_for_connection():
                logger.error("❌ Pixel7 に接続できませんでした。adb connect / Tailscale を確認してください")
            return

        logger.info(f"✅ Pixel7 接続確認 OK (record={args.record_sec}秒, camera={args.pixel7_camera})")

        # プロアクティブ監視スレッド起動（バッテリー警告・接続監視）
        _watcher = ProactivePixel7Watcher(tts_engine=tts_engine, pixel7_io=pixel7_io)
        _watcher.start()
        logger.info("🔔 Pixel7 プロアクティブ監視 開始（5分ごとにバッテリー確認）")

        # カメラ起動メッセージ
        if args.pixel7_camera:
            logger.info("📷 Pixel7 カメラ Vision 有効 — 「カメラ」と話しかけると撮影＆説明します")

            # llm_callback をラップしてカメラキーワードを横取り
            _orig_llm = llm_callback
            def llm_callback_with_camera(text: str) -> str:  # type: ignore[misc]
                if any(kw in text for kw in ["カメラ", "撮影", "見て", "何が見える"]):
                    return pixel7_io.shoot(prompt=text)
                return _orig_llm(text)
            llm_callback = llm_callback_with_camera  # type: ignore[assignment]

        try:
            _run_pixel7_loop(pixel7_io, stt_engine, tts_engine, llm_callback)
        except KeyboardInterrupt:
            logger.info("🛑 停止シグナルを受信しました")
        finally:
            _watcher.stop()
        logger.info("✅ Pixel7 JARVIS モードを停止しました")
        return

    # ========== PC モード（既存）==========
    logger.info("🎯 音声会話ループを作成中...")
    conversation_loop = VoiceConversationLoop(
        stt_engine=stt_engine,
        tts_engine=tts_engine,
        llm_callback=llm_callback,
        hotword="レミ",
        continuous=True,
        intent_router_callback=intent_router_callback,
        task_registration_callback=task_registration_callback,
        conversation_save_callback=conversation_save_callback
    )

    logger.info("🚀 音声会話ループを開始します...")
    logger.info("💡 ホットワード「レミ」で呼び出せます")
    logger.info("🛑 停止するには Ctrl+C を押してください")

    try:
        conversation_loop.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 停止シグナルを受信しました")
    finally:
        conversation_loop.stop()
        logger.info("✅ 秘書レミ完全体を停止しました")


if __name__ == "__main__":
    main()
