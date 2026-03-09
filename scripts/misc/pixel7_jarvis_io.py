#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📱 Pixel7 JARVIS I/O ブリッジ
Pixel 7 をマイク・スピーカー・カメラとして使うための ADB ブリッジ

パイプライン:
  [マイク]  Pixel7 → ADB録音 → WAV → STT (Whisper)
  [スピーカー] TTS音声 → ADB push → Pixel7再生
  [カメラ]  Pixel7カメラ撮影 → ADB pull → Vision LLM
"""

import os
import sys
import subprocess
import tempfile
import time
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable

# sys.path: repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from manaos_logger import get_service_logger

logger = get_service_logger("pixel7-jarvis-io")

# ========================================
# 設定
# ========================================

ADB_CONFIG_PATH = _REPO_ROOT / "adb_automation_config.json"

def _load_adb_config() -> Dict[str, Any]:
    try:
        with open(ADB_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _get_adb_path() -> str:
    """ADB実行ファイルを探す"""
    cfg = _load_adb_config()
    if cfg.get("adb_path"):
        return cfg["adb_path"]
    # PATH上のadb
    import shutil
    found = shutil.which("adb")
    if found:
        return found
    # scrcpyディレクトリ（バージョン付きサブディレクトリも探索）
    scrcpy_root = _REPO_ROOT.parent / "scrcpy"
    for candidate in [
        scrcpy_root / "adb.exe",
        scrcpy_root / "scrcpy-win64-v3.3.4" / "adb.exe",
    ]:
        if candidate.exists():
            return str(candidate)
    return "adb"

def _get_device_serial() -> str:
    cfg = _load_adb_config()
    ip = cfg.get("device_ip", os.getenv("ADB_DEVICE_IP", ""))
    port = cfg.get("device_port", os.getenv("ADB_DEVICE_PORT", "5555"))
    if ip:
        return f"{ip}:{port}"
    return os.getenv("ANDROID_SERIAL", "")


def _get_ssh_params() -> tuple:
    """SSH 接続パラメータ: (host, port, key_path) を返す"""
    cfg = _load_adb_config()
    host = cfg.get("device_ip", os.getenv("ADB_DEVICE_IP", "100.84.2.125"))
    port = cfg.get("ssh_port", 8022)
    raw_key = cfg.get("ssh_key_path", "~/.ssh/id_ed25519")
    key_path = os.path.expanduser(raw_key)
    return host, port, key_path


def _run_ssh(cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Termux SSH 経由でコマンドを実行する"""
    host, port, key_path = _get_ssh_params()
    ssh_cmd = [
        "ssh",
        "-i", key_path,
        "-p", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        host,
        cmd,
    ]
    logger.debug(f"SSH: {' '.join(ssh_cmd)}")
    return subprocess.run(
        ssh_cmd,
        capture_output=True,
        timeout=timeout,
        encoding="utf-8",
        errors="ignore",
    )

def _run_adb(args: list, timeout: int = 30, capture: bool = True) -> subprocess.CompletedProcess:
    adb = _get_adb_path()
    serial = _get_device_serial()
    cmd = [adb]
    if serial:
        cmd += ["-s", serial]
    cmd += args
    logger.debug(f"ADB: {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        capture_output=capture,
        timeout=timeout,
        encoding="utf-8",
        errors="ignore",
    )

def _check_ssh_connection() -> bool:
    """Pixel7 への SSH 接続確認"""
    try:
        r = _run_ssh("echo ping", timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def _scp_push(local_path: Path, remote_path: str, timeout: int = 30) -> bool:
    """SCP でファイルを Pixel7 へ転送する"""
    host, port, key_path = _get_ssh_params()
    cmd = [
        "scp",
        "-i", key_path,
        "-P", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        str(local_path),
        f"{host}:{remote_path}",
    ]
    logger.debug(f"SCP push: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        logger.debug(f"SCP push 失敗: {r.stderr[:200]}")
    return r.returncode == 0


def _scp_pull(remote_path: str, local_path: Path, timeout: int = 30) -> bool:
    """SCP で Pixel7 からファイルを取得する"""
    host, port, key_path = _get_ssh_params()
    cmd = [
        "scp",
        "-i", key_path,
        "-P", str(port),
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        f"{host}:{remote_path}",
        str(local_path),
    ]
    logger.debug(f"SCP pull: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, timeout=timeout, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        logger.debug(f"SCP pull 失敗: {r.stderr[:200]}")
    return r.returncode == 0


def check_connection() -> bool:
    """Pixel7 への接続確認 (ADB 優先, SSH フォールバック)"""
    try:
        r = _run_adb(["get-state"], timeout=5)
        if r.returncode == 0 and "device" in r.stdout:
            return True
    except Exception:
        pass
    # ADB が使えない場合は SSH で確認
    return _check_ssh_connection()

# ========================================
# マイク: Pixel7 で録音 → WAV に変換
# ========================================

ANDROID_TMP_WAV = "/sdcard/jarvis_mic_input.wav"
ANDROID_TMP_MP4 = "/sdcard/jarvis_mic_input.mp4"

def record_audio_on_pixel7(
    duration_sec: int = 5,
    local_out: Optional[Path] = None,
) -> Optional[Path]:
    """
    Pixel7 のマイクで録音して WAV ファイルとして返す。

    優先順:
      1. SSH+rec (SCP pull) — ADB 不要
      2. termux-microphone-record (Termux:API アプリ必要)
      3. フォールバック: 接続確認のみ (録音不可メッセージ)
    """
    if not check_connection():
        logger.error("Pixel7 に接続されていません")
        return None

    local_out = local_out or Path(tempfile.gettempdir()) / f"pixel7_mic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"

    # 録音前に古い一時ファイルを削除 (ADB or SSH)
    try:
        _run_adb(["shell", f"rm -f {ANDROID_TMP_WAV}"], timeout=5)
    except Exception:
        _run_ssh(f"rm -f {ANDROID_TMP_WAV}", timeout=5)

    logger.info(f"📱 Pixel7 で {duration_sec}秒 録音中...")

    # --- 方法1: Termux SSH 経由 (rec コマンド / sox) ---
    try:
        rec_cmd = f"rec -r 16000 -c 1 -b 16 {ANDROID_TMP_WAV} trim 0 {duration_sec}"
        ssh_result = _run_ssh(rec_cmd, timeout=duration_sec + 15)
        if ssh_result.returncode == 0:
            # まず ADB pull を試みる
            pulled = False
            try:
                pull_result = _run_adb(["pull", ANDROID_TMP_WAV, str(local_out)], timeout=15)
                if pull_result.returncode == 0 and local_out.exists() and local_out.stat().st_size > 1000:
                    pulled = True
            except Exception:
                pass
            # ADB pull 失敗時は SCP pull
            if not pulled:
                pulled = _scp_pull(ANDROID_TMP_WAV, local_out, timeout=15)
            if pulled and local_out.exists() and local_out.stat().st_size > 1000:
                logger.info(f"✅ 録音成功 (SSH+rec): {local_out.name}")
                try:
                    _run_adb(["shell", f"rm -f {ANDROID_TMP_WAV}"], timeout=5)
                except Exception:
                    _run_ssh(f"rm -f {ANDROID_TMP_WAV}", timeout=5)
                return local_out
        logger.debug(f"SSH rec 失敗 (rc={ssh_result.returncode}): {ssh_result.stderr[:200]}")
    except Exception as e:
        logger.debug(f"SSH rec 例外: {e}")

    # --- 方法2: termux-microphone-record (Termux:API アプリ) ---
    mic_result = _run_adb([
        "shell", "termux-microphone-record",
        "-l", str(duration_sec),
        "-f", ANDROID_TMP_WAV,
    ], timeout=duration_sec + 15)

    if mic_result.returncode == 0:
        pull_result = _run_adb(["pull", ANDROID_TMP_WAV, str(local_out)], timeout=15)
        if pull_result.returncode == 0 and local_out.exists() and local_out.stat().st_size > 1000:
            logger.info(f"✅ 録音成功 (termux-microphone-record): {local_out.name}")
            _run_adb(["shell", f"rm -f {ANDROID_TMP_WAV}"], timeout=5)
            return local_out

    logger.warning(
        "⚠️  Pixel7 マイク録音失敗。以下のいずれかを行ってください:\n"
        "  A) Termux で: mkdir -p ~/.termux && echo 'allow-external-apps = true' >> ~/.termux/termux.properties\n"
        "  B) F-Droid から Termux:API アプリをインストール\n"
        "  その後 Termux で: pkg install -y sox"
    )
    return None


def _convert_mp4_to_wav(mp4_path: Path, wav_path: Path) -> bool:
    """PC 側の ffmpeg で mp4 → wav 変換"""
    import shutil
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.error("ffmpeg が見つかりません。pip install ffmpeg-python または chocolatey でインストールしてください")
        return False
    try:
        r = subprocess.run(
            [ffmpeg, "-y", "-i", str(mp4_path), "-ar", "16000", "-ac", "1", str(wav_path)],
            capture_output=True, timeout=60
        )
        return r.returncode == 0
    except Exception as e:
        logger.error(f"ffmpeg 変換エラー: {e}")
        return False


# ========================================
# スピーカー: TTS 音声 → Pixel7 で再生
# ========================================

ANDROID_TMP_PLAY = "/sdcard/jarvis_tts_output.wav"

def play_audio_on_pixel7(wav_path: Path) -> bool:
    """
    WAV ファイルを Pixel7 のスピーカーで再生する。
    SCP/adb push → SSH play (または Termux media-player)
    """
    if not check_connection():
        logger.error("Pixel7 に接続されていません")
        return False

    if not wav_path.exists():
        logger.error(f"音声ファイルが見つかりません: {wav_path}")
        return False

    logger.info(f"Pixel7 スピーカーで再生: {wav_path.name}")

    # --- ファイル転送: ADB push 優先、失敗時 SCP ---
    pushed = False
    try:
        push_result = _run_adb(["push", str(wav_path), ANDROID_TMP_PLAY], timeout=30)
        if push_result.returncode == 0:
            pushed = True
        else:
            logger.debug(f"ADB push 失敗: {push_result.stderr[:200]}")
    except Exception as e:
        logger.debug(f"ADB push 例外: {e}")

    if not pushed:
        logger.debug("SCP push を試みます")
        pushed = _scp_push(wav_path, ANDROID_TMP_PLAY, timeout=30)

    if not pushed:
        logger.error("ファイル転送失敗 (ADB push / SCP 両方)")
        return False

    # WAV の再生時間を推定（16-bit mono 16kHz ≒ 32 kB/s）
    try:
        wait_sec = max(2, wav_path.stat().st_size / 32000)
    except Exception:
        wait_sec = 5

    # 方法1: Termux SSH 経由 (play コマンド)
    try:
        play_result_ssh = _run_ssh(f"play {ANDROID_TMP_PLAY}", timeout=int(wait_sec) + 15)
        if play_result_ssh.returncode == 0:
            logger.debug("✅ SSH play 再生成功")
            try:
                _run_adb(["shell", f"rm -f {ANDROID_TMP_PLAY}"], timeout=5)
            except Exception:
                _run_ssh(f"rm -f {ANDROID_TMP_PLAY}", timeout=5)
            return True
        logger.debug(f"SSH play 失敗 (rc={play_result_ssh.returncode}): {play_result_ssh.stderr[:200]}")
    except Exception as e:
        logger.debug(f"SSH play 例外: {e}")

    # 方法2: termux-media-player (Termux:API)
    try:
        play_result = _run_adb([
            "shell", f"termux-media-player play {ANDROID_TMP_PLAY}"
        ], timeout=5)
        if play_result.returncode == 0:
            time.sleep(wait_sec)
            _run_adb(["shell", f"rm -f {ANDROID_TMP_PLAY}"], timeout=5)
            return True
    except Exception:
        pass

    # 方法3: am start で標準メディアプレイヤー
    try:
        logger.debug("フォールバック: am start VIEW で再生")
        _run_adb([
            "shell",
            f"am start -a android.intent.action.VIEW -d file://{ANDROID_TMP_PLAY} -t audio/wav"
        ], timeout=10)
        time.sleep(wait_sec)
        _run_adb(["shell", f"rm -f {ANDROID_TMP_PLAY}"], timeout=5)
    except Exception:
        pass
    return True


# ========================================
# カメラ: Pixel7 で撮影 → PNG を返す
# ========================================

ANDROID_TMP_PHOTO = "/sdcard/jarvis_camera_shot.jpg"

def capture_photo_from_pixel7(
    local_out: Optional[Path] = None,
    use_front_camera: bool = False,
) -> Optional[Path]:
    """
    Pixel7 のカメラで写真を撮影して画像ファイルを返す。

    実装方式 (優先順):
    1. Termux camera-photo コマンド (termux-api)
    2. ADB Intent で Camera アプリ起動 → スクリーンショット取得
    """
    if not check_connection():
        logger.error("Pixel7 に接続されていません")
        return None

    local_out = local_out or Path(tempfile.gettempdir()) / f"pixel7_photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    camera_id = "1" if use_front_camera else "0"

    logger.info(f"Pixel7 カメラで撮影中 (camera_id={camera_id})...")

    # 方法1: termux-camera-photo
    shot_result = _run_adb([
        "shell", f"termux-camera-photo -c {camera_id} {ANDROID_TMP_PHOTO}"
    ], timeout=15)

    if shot_result.returncode != 0:
        # 方法2: ADB Intent でカメラシャッター → MediaStore から最新画像を取得
        logger.warning("termux-camera-photo 失敗、Intent 経由を試みます")
        _run_adb([
            "shell",
            "am start -a android.media.action.STILL_IMAGE_CAMERA"
        ], timeout=5)
        time.sleep(2)
        # キーイベント: カメラシャッター (KEYCODE_CAMERA = 27)
        _run_adb(["shell", "input keyevent 27"], timeout=5)
        time.sleep(3)
        # MediaStore から最新 JPEG を取得
        latest = _run_adb([
            "shell",
            "find /sdcard/DCIM -name '*.jpg' -newer /sdcard/ 2>/dev/null | tail -1"
        ], timeout=10)
        photo_path_on_device = latest.stdout.strip()
        if not photo_path_on_device:
            logger.error("撮影画像が見つかりませんでした")
            return None
        pull_result = _run_adb(["pull", photo_path_on_device, str(local_out)], timeout=30)
        if pull_result.returncode == 0 and local_out.exists():
            logger.info(f"カメラ画像保存: {local_out}")
            return local_out
        return None

    # pull
    pull_result = _run_adb(["pull", ANDROID_TMP_PHOTO, str(local_out)], timeout=30)
    if pull_result.returncode == 0 and local_out.exists():
        logger.info(f"カメラ画像保存: {local_out}")
        _run_adb(["shell", f"rm -f {ANDROID_TMP_PHOTO}"], timeout=5)
        return local_out

    logger.error(f"カメラ画像の取得に失敗: {pull_result.stderr}")
    return None


# ========================================
# Vision: 画像 → LLM で説明
# ========================================

import httpx

try:
    from _paths import UNIFIED_API_PORT, LLM_ROUTING_PORT
except Exception:
    UNIFIED_API_PORT = int(os.getenv("UNIFIED_API_PORT", "9510"))
    LLM_ROUTING_PORT = int(os.getenv("LLM_ROUTING_PORT", "5117"))

UNIFIED_API_URL = os.getenv("UNIFIED_API_URL", f"http://127.0.0.1:{UNIFIED_API_PORT}")
LLM_ROUTING_URL = os.getenv("LLM_ROUTING_URL", f"http://127.0.0.1:{LLM_ROUTING_PORT}")


async def describe_image_async(image_path: Path, prompt: str = "この画像を日本語で説明してください。") -> str:
    """Pixel7 カメラ画像を Vision LLM で説明する"""
    import base64

    if not image_path.exists():
        return "画像ファイルが見つかりません"

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    ext = image_path.suffix.lstrip(".").lower() or "jpeg"
    data_uri = f"data:image/{ext};base64,{b64}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # OpenAI 互換 vision エンドポイント
            response = await client.post(
                f"{LLM_ROUTING_URL}/v1/chat/completions",
                json={
                    "model": "auto-local",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text",      "text": prompt},
                                {"type": "image_url", "image_url": {"url": data_uri}},
                            ],
                        }
                    ],
                },
            )
            if response.status_code == 200:
                result = response.json()
                if "choices" in result:
                    return result["choices"][0]["message"]["content"]
                return result.get("response", "応答なし")

            # フォールバック: unified_api の vision エンドポイント
            response = await client.post(
                f"{UNIFIED_API_URL}/api/vision/describe",
                json={"image_base64": b64, "prompt": prompt},
            )
            if response.status_code == 200:
                return response.json().get("description", "応答なし")

    except Exception as e:
        logger.error(f"Vision LLM エラー: {e}")

    return "画像の説明を取得できませんでした"


def describe_image(image_path: Path, prompt: str = "この画像を日本語で説明してください。") -> str:
    """同期ラッパー"""
    return asyncio.run(describe_image_async(image_path, prompt))


# ========================================
# SSH ヘルスチェック & 自動復旧
# ========================================

def ensure_sshd_running() -> bool:
    """
    Pixel7 Termux の sshd が起動しているか確認し、
    未起動なら ADB 経由で Termux に起動コマンドを送る。

    Returns:
        True  : SSH 接続可能（または起動に成功）
        False : ADB 未接続 / 起動失敗
    """
    if not check_connection():
        logger.warning("ensure_sshd_running: ADB 未接続")
        return False

    # 実際に SSH 接続テスト（最速チェック）
    try:
        r = _run_ssh("echo SSHD_OK", timeout=8)
        if r.returncode == 0 and "SSHD_OK" in r.stdout:
            logger.debug("sshd 起動確認済み (SSH OK)")
            return True
    except Exception:
        pass

    logger.info("🔄 sshd が未応答 → ADB 経由で起動を試みます...")

    # Termux フォアグラウンド起動
    _run_adb(["shell", "am start -n com.termux/.app.TermuxActivity"], timeout=5)
    time.sleep(3)

    # sshd 起動コマンドを input text で送信
    _, port, _ = _get_ssh_params()
    _run_adb(["shell", f"input text 'sshd%s-p%s{port}'"], timeout=5)
    _run_adb(["shell", "input keyevent 66"], timeout=5)
    time.sleep(5)

    # 再テスト
    try:
        r = _run_ssh("echo SSHD_OK", timeout=8)
        if r.returncode == 0 and "SSHD_OK" in r.stdout:
            logger.info("✅ sshd 起動成功")
            return True
    except Exception:
        pass

    logger.error("❌ sshd 起動失敗。Pixel7 の Termux 画面を確認してください")
    return False


# ========================================
# 統合: Pixel7 をフル I/O にした会話ループ
# ========================================

class Pixel7JarvisIO:
    """
    Pixel7 をマイク・スピーカー・カメラとして使う JARVIS I/O ブリッジ。

    voice_secretary_remi.py の VoiceConversationLoop と組み合わせて使う。
    独立して単体テストもできる。
    """

    def __init__(
        self,
        record_duration: int = 5,
        use_front_camera: bool = False,
        auto_ensure_sshd: bool = True,
    ):
        self.record_duration = record_duration
        self.use_front_camera = use_front_camera
        if auto_ensure_sshd and check_connection():
            ensure_sshd_running()

    def is_connected(self) -> bool:
        return check_connection()

    def listen(self) -> Optional[Path]:
        """Pixel7 マイクで録音して WAV パスを返す"""
        return record_audio_on_pixel7(duration_sec=self.record_duration)

    def speak(self, wav_path: Path) -> bool:
        """Pixel7 スピーカーで WAV を再生する"""
        return play_audio_on_pixel7(wav_path)

    def shoot(self, prompt: str = "この画像を日本語で説明してください。") -> str:
        """Pixel7 カメラで撮影して Vision LLM で説明を返す"""
        photo = capture_photo_from_pixel7(use_front_camera=self.use_front_camera)
        if photo is None:
            return "撮影に失敗しました"
        return describe_image(photo, prompt)

    def run_voice_turn(
        self,
        stt_fn: Callable[[Path], str],
        llm_fn: Callable[[str], str],
        tts_fn: Callable[[str], Optional[Path]],
    ) -> Dict[str, Any]:
        """
        1ターン分の JARVIS 音声対話を実行する。

        Args:
            stt_fn: WAVパス → テキスト変換関数
            llm_fn: テキスト → 応答テキスト変換関数
            tts_fn: テキスト → WAVパス変換関数（出力 WAV を返す）

        Returns:
            {"user": ..., "assistant": ..., "success": bool}
        """
        if not self.is_connected():
            return {"user": "", "assistant": "Pixel7 に接続されていません", "success": False}

        # 録音
        wav_in = self.listen()
        if wav_in is None:
            return {"user": "", "assistant": "録音に失敗しました", "success": False}

        # STT
        try:
            user_text = stt_fn(wav_in)
        except Exception as e:
            logger.error(f"STT エラー: {e}")
            return {"user": "", "assistant": "音声認識に失敗しました", "success": False}

        if not user_text.strip():
            return {"user": "", "assistant": "(無音)", "success": False}

        logger.info(f"[Pixel7 STT] {user_text}")

        # LLM
        try:
            assistant_text = llm_fn(user_text)
        except Exception as e:
            logger.error(f"LLM エラー: {e}")
            assistant_text = "応答を生成できませんでした"

        logger.info(f"[Pixel7 LLM] {assistant_text}")

        # TTS → Pixel7 再生
        try:
            wav_out = tts_fn(assistant_text)
            if wav_out:
                self.speak(wav_out)
        except Exception as e:
            logger.error(f"TTS/再生エラー: {e}")

        return {
            "user": user_text,
            "assistant": assistant_text,
            "success": True,
        }


# ========================================
# 単体テスト用 CLI
# ========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pixel7 JARVIS I/O テスト")
    parser.add_argument("mode", choices=["connect", "mic", "speak", "camera"], help="テストモード")
    parser.add_argument("--duration", type=int, default=5, help="録音秒数")
    parser.add_argument("--wav", type=str, help="再生する WAV ファイルパス")
    parser.add_argument("--front", action="store_true", help="フロントカメラ使用")
    args = parser.parse_args()

    if args.mode == "connect":
        ok = check_connection()
        print(f"Pixel7 接続: {'OK' if ok else 'NG'}")

    elif args.mode == "mic":
        path = record_audio_on_pixel7(duration_sec=args.duration)
        if path:
            print(f"録音完了: {path}")
        else:
            print("録音失敗")

    elif args.mode == "speak":
        if not args.wav:
            print("--wav オプションで再生ファイルを指定してください")
            sys.exit(1)
        ok = play_audio_on_pixel7(Path(args.wav))
        print(f"再生: {'成功' if ok else '失敗'}")

    elif args.mode == "camera":
        desc = Pixel7JarvisIO(use_front_camera=args.front).shoot()
        print(f"カメラ説明:\n{desc}")
