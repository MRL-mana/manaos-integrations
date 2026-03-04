#!/usr/bin/env python3
"""
ManaOS Gallery Production Server with Gunicorn
本番向けGunicorn設定とDB移動、バリデーション、キュー機能
"""

import os
import typing
import sqlite3
import threading
import queue
import time
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
import requests
import json
import shutil
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
from pathlib import Path

# ベースディレクトリを取得（スクリプトの場所を基準）
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR.parent / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'gallery_production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 設定
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
# ストレージディレクトリ（環境変数で上書き可能、デフォルトは相対パス）
STORAGE_BASE = Path(os.getenv("STORAGE_BASE", str(BASE_DIR.parent / "storage")))
GENERATED_IMAGES_DIR = os.getenv("GENERATED_IMAGES_DIR", str(STORAGE_BASE / "generated_images"))
FIXED_IMAGES_DIR = os.getenv("FIXED_IMAGES_DIR", str(STORAGE_BASE / "fixed_images"))
MUFUFU_IMAGES_DIR = os.getenv("MUFUFU_IMAGES_DIR", str(BASE_DIR.parent / "trinity_workspace" / "generated_images"))
GALLERY_DIR = os.getenv("GALLERY_DIR", str(STORAGE_BASE / "gallery"))
DATABASE_PATH = os.path.join(GALLERY_DIR, "gallery.db")

# 許可されたディレクトリ
ALLOWED_DIRS = [
    GENERATED_IMAGES_DIR,
    FIXED_IMAGES_DIR,
    MUFUFU_IMAGES_DIR
]

# 強化されたジョブキューシステム（動的サイズ調整、優先度付き）
try:
    from enhanced_job_queue import JobPriority, get_enhanced_queue
    use_enhanced_queue = True
    enhanced_queue = get_enhanced_queue()
    logger.info("✅ Enhanced Job Queueシステムを有効化しました")
except Exception as e:
    logger.warning(f"⚠️ Enhanced Job Queueの読み込みに失敗、従来のキューを使用: {e}")
    use_enhanced_queue = False
    JOB_QUEUE_SIZE = int(os.getenv("GALLERY_JOB_QUEUE_SIZE", "10"))
    job_queue = queue.Queue(maxsize=JOB_QUEUE_SIZE)

# 後方互換性のため
if not use_enhanced_queue:
    job_queue = queue.Queue(maxsize=JOB_QUEUE_SIZE)

job_results = {}
job_counter = 0

class SyncWorker:
    def __init__(self, interval_sec: int = 300):
        self.interval_sec = interval_sec
        self.running = True
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
    def loop(self):
        logger.info("🔄 SyncWorkerスレッド開始")
        while self.running:
            try:
                added = gallery_api.sync_unregistered_images(limit=200)
                if added:
                    logger.info(f"✅ 自動同期: {added}件 登録")
            except Exception as e:
                logger.warning(f"⚠️ 自動同期エラー: {e}")
            time.sleep(self.interval_sec)
    def stop(self):
        self.running = False

class JobProcessor:
    def __init__(self):
        self.running = True
        self.thread = threading.Thread(target=self.process_jobs, daemon=True)
        self.thread.start()

    def process_jobs(self):
        logger.info("🔄 JobProcessorスレッド開始")
        loop_count = 0
        while self.running:
            try:
                # 定期的にログ出力（デバッグ用）
                loop_count += 1
                if loop_count % 300 == 0:  # 5分ごと
                    if use_enhanced_queue:
                        stats = enhanced_queue.get_queue_stats()
                        logger.info(f"🔄 JobProcessor動作中（ループ: {loop_count}, キューサイズ: {stats['total_size']}, 統計: {stats['job_stats']})")
                    else:
                        logger.info(f"🔄 JobProcessor動作中（ループ: {loop_count}, キューサイズ: {job_queue.qsize()})")

                # 強化されたキューを使用する場合
                if use_enhanced_queue:
                    job_data = enhanced_queue.get(timeout=1)
                    if job_data is None:
                        continue
                    job_id, job_type, data = job_data
                else:
                    job_id, job_type, data = job_queue.get(timeout=1)

                logger.info(f"🔄 ジョブ処理開始: {job_id} ({job_type})")

                start_time = time.time()
                # 処理中のジョブ情報（開始時刻と元のリクエストデータを保持）
                job_results[job_id] = {
                    "status": "processing",
                    "started_at": datetime.fromtimestamp(start_time).isoformat(),
                    "request_data": data,  # 再試行用に保存
                    "job_type": job_type
                }

                result = self.execute_job(job_type, data)
                duration = time.time() - start_time

                job_results[job_id] = {
                    "status": "completed",
                    "result": result,
                    "duration_sec": round(duration, 3),
                    "completed_at": datetime.now().isoformat()
                }

                # 強化されたキューに完了を記録
                if use_enhanced_queue:
                    enhanced_queue.complete_job(job_id, result, duration)
                else:
                    job_queue.task_done()

                logger.info(f"✅ ジョブ完了: {job_id} (処理時間: {duration:.2f}秒)")

            except queue.Empty:
                continue
            except Exception as e:
                job_id_local = job_id if 'job_id' in locals() else 'unknown'
                logger.error(f"❌ ジョブエラー: {job_id_local} - {e}", exc_info=True)

                if 'job_id' in locals():
                    # エラー時もrequest_dataとjob_typeを保持（再試行用）
                    error_info = {
                        "status": "error",
                        "error": str(e),
                        "completed_at": datetime.now().isoformat()
                    }
                    if job_id in job_results:
                        error_info["request_data"] = job_results[job_id].get("request_data")
                        error_info["job_type"] = job_results[job_id].get("job_type")
                    job_results[job_id] = error_info

                    # 強化されたキューに失敗を記録
                    if use_enhanced_queue:
                        enhanced_queue.fail_job(job_id, str(e))

    def execute_job(self, job_type, data):
        if job_type == "generate":
            # 全パラメータを渡す（width/height/auto_face_fix追加）
            return gallery_api.generate_image(
                prompt=data.get("prompt"),
                model=data.get("model", "majicMIX lux 麦橘辉耀_56967.safetensors"),  # SDXL標準
                steps=data.get("steps", 20),
                guidance_scale=data.get("guidance_scale", 7.5),
                negative_prompt=data.get("negative_prompt"),
                mufufu_mode=data.get("mufufu_mode", False),
                width=data.get("width", 1024),  # SDXL標準解像度
                height=data.get("height", 1024),
                auto_face_fix=data.get("auto_face_fix", False)
            )
        elif job_type == "inpaint":
            return gallery_api.inpaint_face(**data)
        elif job_type == "enhance":
            return gallery_api.enhance_adult(
                image_path=data.get("image_path"),
                enhancement_type=data.get("enhancement_type", "sexy"),
                lora_name=data.get("lora_name")
            )
        else:
            raise ValueError(f"Unknown job type: {job_type}")

    def stop(self):
        self.running = False

# ジョブプロセッサー初期化
# Gunicornのpreload_app=Trueの場合、複数初期化される可能性があるため
# 単一のプロセスでのみ初期化されるようにする
job_processor = None

def get_job_processor():
    global job_processor
    if job_processor is None:
        logger.info("🔄 JobProcessor初期化...")
        job_processor = JobProcessor()
        logger.info("✅ JobProcessor初期化完了")
    return job_processor

# 初回初期化
job_processor = get_job_processor()

class GoogleDriveBackup:
    def __init__(self):
        self.service = None
        self.credentials_file = "/root/.mana_vault/google_drive_credentials.json"
        self.token_file = "/root/.mana_vault/google_drive_token.pickle"
        self.backup_folder_id = None
        self.init_service()

    def init_service(self):
        try:
            creds = None
            if os.path.exists(self.token_file):
                try:
                    with open(self.token_file, 'rb') as token:
                        creds = pickle.load(token)
                except Exception as e:
                    logger.warning(f"⚠️ トークンファイルの読み込みエラー: {e}")
                    creds = None

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logger.warning(f"⚠️ トークンリフレッシュエラー: {e}")
                        creds = None
                else:
                    if os.path.exists(self.credentials_file):
                        # 認証情報ファイルの検証
                        try:
                            with open(self.credentials_file, 'r') as f:
                                cred_data = json.load(f)
                            if not cred_data or ('installed' not in cred_data and 'web' not in cred_data):
                                raise ValueError("認証情報ファイルの形式が不正です")
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ 認証情報ファイルのJSON解析エラー: {e}")
                            self.service = None
                            return
                        except Exception as e:
                            logger.error(f"❌ 認証情報ファイルの検証エラー: {e}")
                            self.service = None
                            return

                        try:
                            flow = InstalledAppFlow.from_client_secrets_file(
                                self.credentials_file,
                                ['https://www.googleapis.com/auth/drive.file']
                            )
                            creds = flow.run_local_server(port=0)
                        except Exception as e:
                            logger.warning(f"⚠️ OAuth認証フローエラー: {e}")
                            self.service = None
                            return

                if creds:
                    try:
                        with open(self.token_file, 'wb') as token:
                            pickle.dump(creds, token)
                    except Exception as e:
                        logger.warning(f"⚠️ トークン保存エラー: {e}")

            if creds:
                self.service = build('drive', 'v3', credentials=creds)
                logger.info("✅ Google Drive API初期化完了")
            else:
                self.service = None
                logger.warning("⚠️ Google Drive API認証情報が利用できません")

        except FileNotFoundError:
            logger.warning(f"⚠️ Google Drive認証情報ファイルが見つかりません: {self.credentials_file}")
            self.service = None
        except Exception as e:
            logger.warning(f"⚠️ Google Drive API初期化失敗: {e}")
            self.service = None

    def backup_database(self):
        if not self.service:
            return False

        try:
            # バックアップファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"gallery_backup_{timestamp}.db"
            backup_path = os.path.join(GALLERY_DIR, backup_filename)

            # DBコピー
            shutil.copy2(DATABASE_PATH, backup_path)

            # Google Driveにアップロード
            file_metadata = {
                'name': backup_filename,
                'parents': [self.backup_folder_id] if self.backup_folder_id else None
            }

            media = MediaFileUpload(backup_path, mimetype='application/x-sqlite3')
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            # ローカルバックアップ削除
            os.remove(backup_path)

            logger.info(f"✅ DBバックアップ完了: {backup_filename}")
            return True

        except Exception as e:
            logger.error(f"❌ DBバックアップ失敗: {e}")
            return False

class GalleryAPI:
    def __init__(self):
        self.api_base_url = API_BASE_URL
        self.session = requests.Session()
        self.backup = GoogleDriveBackup()
        # タイムアウト/リトライは環境変数で調整可能
        self.generate_timeout_sec = int(os.getenv("GALLERY_SD_TIMEOUT", "600"))
        self.generate_retries = int(os.getenv("GALLERY_SD_RETRIES", "3"))
        # モデル安定化設定
        self.default_model = os.getenv("GALLERY_DEFAULT_MODEL", "majicMIX lux 麦橘辉耀_56967.safetensors")  # SDXL標準
        self.model_denylist = {
            m.strip() for m in os.getenv("GALLERY_MODEL_DENYLIST", "majicmixLux_v3.safetensors").split(",") if m.strip()
        }
        self.available_models_cache = set()
        self.available_models_cached_at = 0.0
        self.init_database()

    def refresh_models_cache(self, force: bool = False):
        try:
            now = time.time()
            if not force and (now - self.available_models_cached_at) < 300:
                return
            resp = self.session.get(f"{self.api_base_url}/models", timeout=10)
            resp.raise_for_status()
            models = resp.json() or []
            names = set()
            for item in models:
                # item は {name, path, dir} 形式を想定
                name = item.get("name") if isinstance(item, dict) else None
                if isinstance(name, str) and name:
                    names.add(name)
            self.available_models_cache = names
            self.available_models_cached_at = now
            logger.info(f"🔄 モデルキャッシュ更新: {len(names)}件")
        except Exception as e:
            logger.warning(f"⚠️ モデルキャッシュ更新失敗: {e}")

    @staticmethod
    def _parse_created_at_from_filename(filename: str) -> str:
        """ファイル名の _YYYYMMDD_HHMMSS を created_at に変換。なければmtime/現在時刻。
        戻り値は 'YYYY-MM-DD HH:MM:SS'。
        """
        try:
            import re
            from datetime import datetime as _dt
            m = re.search(r"_(\d{8})_(\d{6})", filename)
            if m:
                dt = _dt.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        try:
            fp = os.path.join(GENERATED_IMAGES_DIR, filename)
            if os.path.exists(fp):
                from datetime import datetime as _dt
                return _dt.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def init_database(self):
        """データベース初期化（移動先）"""
        # ディレクトリ作成
        os.makedirs(GALLERY_DIR, exist_ok=True)

        # 既存DBを移動
        old_db_path = "/root/gallery.db"
        if os.path.exists(old_db_path) and not os.path.exists(DATABASE_PATH):
            shutil.move(old_db_path, DATABASE_PATH)
            logger.info(f"✅ DB移動完了: {old_db_path} -> {DATABASE_PATH}")

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                prompt TEXT,
                model TEXT,
                rating INTEGER DEFAULT 0,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_path TEXT,
                file_type TEXT DEFAULT 'generated'
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("✅ データベース初期化完了")

    def sync_unregistered_images(self, limit: int = 100) -> int:
        """generated_images に存在し DB未登録の *_api_*.png とbatch_*.png とmufufu_cpu_*.png を登録"""
        try:
            start = time.time()
            from glob import glob
            # API生成、バッチ生成、ムフフ画像の全てをチェック
            api_files = sorted(glob(os.path.join(GENERATED_IMAGES_DIR, "*api_*.png")))[-limit:]
            batch_files = sorted(glob(os.path.join(GENERATED_IMAGES_DIR, "batch_*.png")))[-limit:]
            # CPU生成とRunPod生成の両方をチェック
            mufufu_cpu_files = sorted(glob(os.path.join(MUFUFU_IMAGES_DIR, "mufufu_cpu_*.png")))[-limit:]
            mufufu_runpod_files = sorted(glob(os.path.join(MUFUFU_IMAGES_DIR, "mufufu_runpod_*.png")))[-limit:]
            mufufu_files = sorted(list(set(mufufu_cpu_files + mufufu_runpod_files)))[-limit:]
            files = sorted(list(set(api_files + batch_files + mufufu_files)))[-limit:]
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT filename FROM images")
            registered = {row[0] for row in cursor.fetchall()}
            added = 0
            for path in files:
                filename = os.path.basename(path)
                if filename in registered:
                    continue
                created_at = self._parse_created_at_from_filename(filename)
                # モデル推定（ファイル名から）
                model = "majicmixRealistic_v7.safetensors"  # デフォルト
                if "batch_5224b821" in filename or "batch_7396607b" in filename:
                    model = "majicmixRealistic_v7.safetensors"
                elif "batch_9b85557f" in filename or "batch_3c130854" in filename:
                    model = "majicmixLux_v3.safetensors"
                elif "batch_0f953a89" in filename:
                    model = "majicMIX lux 麦橘辉耀_56967.safetensors"
                elif "batch_14e7a7c4" in filename:
                    model = "majicmixRealistic_v7.safetensors"

                cursor.execute('''
                    INSERT OR IGNORE INTO images (filename, prompt, model, file_path, file_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (filename, f"auto-sync: {filename}", model, path, "generated", created_at))
                added += 1
            conn.commit()
            conn.close()
            logger.info(f"🔄 sync_unregistered_images added={added} elapsed={time.time()-start:.1f}s")
            return added
        except Exception as e:
            logger.error(f"❌ 同期エラー: {e}", exc_info=True)
            return 0

    def validate_image_path(self, image_path):
        """画像パスのバリデーション"""
        if not image_path:
            return False, "画像パスが指定されていません"

        # 絶対パスに変換
        abs_path = os.path.abspath(image_path)

        # 許可されたディレクトリ内かチェック
        for allowed_dir in ALLOWED_DIRS:
            if abs_path.startswith(os.path.abspath(allowed_dir)):
                if os.path.exists(abs_path):
                    return True, "OK"
                else:
                    return False, "ファイルが存在しません"

        return False, "許可されていないディレクトリです"

    def generate_image(self, prompt: str, model: str = "majicmixRealistic_v7.safetensors",
                      steps: int = 30, guidance_scale: float = 7.5,
                      negative_prompt: typing.Optional[str] = None, mufufu_mode: bool = False,
                      width: int = 512, height: int = 512, auto_face_fix: bool = False) -> dict:
        """画像生成"""
        try:
            start_ts = time.time()
            logger.info(f"🟦 generate_image start model={model} steps={steps} gs={guidance_scale} mufufu={mufufu_mode} face_quality=enabled")
            # モデル選択安定化
            self.refresh_models_cache()
            requested_model = model or self.default_model
            fallback_reason = None
            if requested_model in self.model_denylist:
                fallback_reason = f"denylist({requested_model})"
            elif self.available_models_cache and requested_model not in self.available_models_cache:
                fallback_reason = f"unknown({requested_model})"
            if fallback_reason:
                logger.warning(f"🟨 モデルフォールバック: {fallback_reason} -> {self.default_model}")
                requested_model = self.default_model
            # 顔崩れ対策：プロンプトに顔品質向上キーワードを自動追加
            face_quality_keywords = "high quality face, perfect face, beautiful face, detailed face, perfect eyes, perfect nose, perfect mouth, symmetric face"
            enhanced_prompt = prompt
            # 既に顔関連キーワードが含まれていない場合のみ追加
            prompt_lower = prompt.lower()
            if not any(kw in prompt_lower for kw in ["face", "portrait", "head", "顔", "ポートレート"]):
                # 人物関連のプロンプトと思われる場合のみ追加
                if any(kw in prompt_lower for kw in ["girl", "woman", "man", "person", "people", "女性", "男性", "人物"]):
                    enhanced_prompt = f"{face_quality_keywords}, {prompt}"
            else:
                # 既に顔関連がある場合は品質向上キーワードのみ追加
                enhanced_prompt = f"{face_quality_keywords}, {prompt}"

            # ネガティブプロンプト：顔崩れ防止を常に追加
            face_negative = "bad face, deformed face, bad anatomy, blurry face, ugly face, distorted face, bad eyes, bad mouth, asymmetric face, malformed face, disfigured face, extra face, missing face, mutated face, poorly drawn face, bad proportions, long neck, long body, deformed body, disfigured body, poorly drawn hands, extra fingers, missing fingers, extra limbs, missing limbs"
            if negative_prompt is None:
                negative_prompt = face_negative
            else:
                # 既存のネガティブプロンプトに顔崩れ防止を追加
                negative_prompt = f"{face_negative}, {negative_prompt}"

            # ムフフモード時のネガティブプロンプト（服を除外）
            if mufufu_mode:
                negative_prompt += ", clothes, clothing, shirt, dress, underwear, bra, panties, swimsuit, swimwear"

            payload = {
                "prompt": enhanced_prompt,
                # 後方互換のため model_name と model を両方送る
                "model_name": requested_model,
                "model": requested_model,
                "steps": steps,
                # 後方互換のため guidance と cfg_scale を両方送る
                "guidance": guidance_scale,
                "cfg_scale": guidance_scale,
                "width": width,
                "height": height
            }

            # ネガティブプロンプトが指定されている場合は追加
            if negative_prompt:
                payload["negative_prompt"] = str(negative_prompt)

            # API呼び出し（タイムアウトは環境変数で調整可能） + リトライ
            last_err = None
            for attempt in range(1, self.generate_retries + 1):
                try:
                    response = self.session.post(
                        f"{self.api_base_url}/generate",
                        json=payload,
                        timeout=self.generate_timeout_sec
                    )
                    logger.info(f"🟩 generate_image attempt={attempt} status={response.status_code} elapsed={time.time()-start_ts:.1f}s timeout={self.generate_timeout_sec}s retries={self.generate_retries}")
                    response.raise_for_status()
                    break
                except Exception as e:
                    last_err = e
                    wait = 3 * attempt
                    logger.warning(f"🟨 generate_image retry in {wait}s (attempt {attempt}/{self.generate_retries}): {e}")
                    time.sleep(wait)
            else:
                if last_err:
                    raise last_err
                raise RuntimeError("generation request failed")

            result = response.json()
            # 受信フィールド名の差異に備えて冗長に取得
            filename = result.get('filename') or ""
            if not filename:
                output_path = result.get('output_path') or result.get('image_path') or result.get('path') or ""
                if isinstance(output_path, str) and output_path:
                    try:
                        filename = os.path.basename(output_path)
                    except Exception:
                        pass
            if not filename:
                # URLにファイル名が含まれるケース
                url = result.get('url') or result.get('image_url') or ""
                if isinstance(url, str) and url:
                    try:
                        filename = os.path.basename(url.split('?')[0])
                    except Exception:
                        pass

            # 自動顔補正（オプション）
            final_filename = filename
            if filename and auto_face_fix:
                try:
                    image_path = os.path.join(GENERATED_IMAGES_DIR, filename)
                    if os.path.exists(image_path):
                        logger.info(f"🔄 自動顔補正開始: {filename}")
                        face_result = self.inpaint_face(image_path, "beautiful face, perfect face, high quality face")
                        if face_result.get("success") and face_result.get("data"):
                            fixed_path = face_result["data"].get("output_path") or face_result["data"].get("filename", "")
                            if fixed_path:
                                final_filename = os.path.basename(fixed_path) if os.path.dirname(fixed_path) else fixed_path
                                logger.info(f"✅ 自動顔補正完了: {final_filename}")
                        else:
                            # 顔補正失敗時も元ファイルは使う（エラーをログに記録のみ）
                            logger.warning(f"⚠️ 自動顔補正失敗（元画像を使用）: {face_result.get('error', 'unknown error')}")
                except Exception as e:
                    # 顔補正エラー時も生成自体は成功として扱う
                    logger.warning(f"⚠️ 自動顔補正エラー（元画像を使用）: {e}")

            # データベースに記録
            if filename:
                self.save_image_record(final_filename or filename, prompt, model)
                logger.info(f"✅ データベース登録: {final_filename or filename} (ムフフモード: {mufufu_mode}, 顔補正: {auto_face_fix}) total_elapsed={time.time()-start_ts:.1f}s")
            else:
                # 主要キーのみを要約してログ
                try:
                    keys_summary = {k: result.get(k) for k in ["filename", "output_path", "image_path", "url", "status"]}
                except Exception:
                    keys_summary = {"raw_keys": list(result.keys()) if isinstance(result, dict) else str(type(result))}
                logger.warning(f"⚠️ filenameが空。レスポンス要約: {keys_summary}")

            logger.info(f"✅ 画像生成完了: {final_filename or filename}")
            # 戻り値にfinal_filenameを含める（顔補正適用済みの場合）
            if final_filename != filename:
                result["filename"] = final_filename
            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"❌ 画像生成エラー: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def inpaint_face(self, image_path: str, face_prompt: str = "beautiful face") -> dict:
        """顔修正"""
        # パスバリデーション
        is_valid, message = self.validate_image_path(image_path)
        if not is_valid:
            return {"success": False, "error": f"パスバリデーションエラー: {message}"}

        try:
            payload = {
                "image_path": image_path,
                "face_prompt": face_prompt
            }

            response = self.session.post(f"{self.api_base_url}/inpaint", json=payload)
            response.raise_for_status()

            result = response.json()

            # データベースに記録（filenameベース）
            output_filename = os.path.basename(result.get('output_path', '')) if result.get('output_path') else result.get('filename', '')
            if output_filename:
                self.save_image_record(output_filename, face_prompt, "face_inpaint", "fixed")

            logger.info(f"✅ 顔修正完了: {result.get('output_path', 'unknown')}")
            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"❌ 顔修正エラー: {e}")
            return {"success": False, "error": str(e)}

    def enhance_adult(self, image_path: str, enhancement_type: str = "sexy", lora_name: typing.Optional[str] = None) -> dict:
        """アダルト強化・服脱がし"""
        # パスバリデーション
        is_valid, message = self.validate_image_path(image_path)
        if not is_valid:
            return {"success": False, "error": f"パスバリデーションエラー: {message}"}

        try:
            payload = {
                "image_path": image_path,
                "enhancement_type": enhancement_type
            }

            # 服脱がしの場合はLoRA名を指定（デフォルトはClothingAdjuster 3.0）
            if enhancement_type == "strip":
                if lora_name is None:
                    lora_name = "ClothingAdjuster"  # 部分一致で検索
                payload["lora_name"] = lora_name
                payload["lora_weight"] = 0.8

            response = self.session.post(f"{self.api_base_url}/enhance", json=payload)
            response.raise_for_status()

            result = response.json()

            # データベースに記録
            output_path = result.get('output_path', '')
            filename = os.path.basename(output_path) if output_path else ''
            if filename:
                self.save_image_record(filename, f"{enhancement_type} enhancement", "enhance", "fixed")

            logger.info(f"✅ {enhancement_type}完了: {result.get('output_path', 'unknown')}")
            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"❌ {enhancement_type}エラー: {e}")
            return {"success": False, "error": str(e)}

    def get_models(self) -> dict:
        """利用可能モデル一覧取得"""
        try:
            response = self.session.get(f"{self.api_base_url}/models")
            response.raise_for_status()

            models = response.json()
            logger.info(f"✅ モデル一覧取得: {len(models)}個")
            return {"success": True, "data": models}

        except Exception as e:
            logger.error(f"❌ モデル一覧取得エラー: {e}")
            return {"success": False, "error": str(e)}

    def save_image_record(self, filename: str, prompt: str, model: str, file_type: str = "generated"):
        """画像記録をデータベースに保存"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            file_path = os.path.join(GENERATED_IMAGES_DIR if file_type == "generated" else FIXED_IMAGES_DIR, filename)
            created_at = self._parse_created_at_from_filename(filename)

            cursor.execute('''
                INSERT OR REPLACE INTO images (filename, prompt, model, file_path, file_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (filename, prompt, model, file_path, file_type, created_at))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"❌ データベース保存エラー: {e}")

    def get_images(self, limit: int = 50) -> list:
        """画像一覧取得"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, filename, prompt, model, rating, comment, created_at, file_path, file_type
                FROM images
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT ?
            ''', (limit,))

            images = []
            for row in cursor.fetchall():
                filename = row[1]
                # 画像URLを生成（/images/で始まるパス）
                image_url = f"/images/{filename}"
                images.append({
                    "id": row[0],
                    "filename": filename,
                    "prompt": row[2],
                    "model": row[3],
                    "rating": row[4],
                    "comment": row[5],
                    "created_at": row[6],
                    "file_path": row[7],
                    "file_type": row[8],
                    "image_url": image_url  # 画像URLを追加
                })

            conn.close()
            return images

        except Exception as e:
            logger.error(f"❌ 画像一覧取得エラー: {e}")
            return []

    def organize_gallery(self) -> dict:
        """画像を日付フォルダに整理（シンボリックリンク作成）。"""
        try:
            linked = 0
            moved = 0
            base = os.path.join(GALLERY_DIR, 'organized')
            os.makedirs(base, exist_ok=True)
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT filename, file_path, created_at FROM images')
            for filename, file_path, created_at in cursor.fetchall():
                # 日付階層を作成
                try:
                    dt = datetime.fromisoformat(created_at)
                except Exception:
                    dt = datetime.now()
                y = dt.strftime('%Y'); m = dt.strftime('%m')
                target_dir = os.path.join(base, y, m)
                os.makedirs(target_dir, exist_ok=True)
                link_path = os.path.join(target_dir, filename)
                if not os.path.exists(link_path):
                    try:
                        os.symlink(file_path, link_path)
                        linked += 1
                    except FileExistsError:
                        pass
                    except Exception:
                        # リンク不可の環境ではコピー
                        import shutil
                        shutil.copy2(file_path, link_path)
                        moved += 1
            conn.close()
            return {"success": True, "linked": linked, "moved": moved}
        except Exception as e:
            logger.error(f"❌ organize_gallery エラー: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def update_rating(self, image_id: int, rating: int) -> bool:
        """評価更新"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE images SET rating = ? WHERE id = ?
            ''', (rating, image_id))

            conn.commit()
            conn.close()

            logger.info(f"✅ 評価更新: ID {image_id} -> {rating}星")
            return True

        except Exception as e:
            logger.error(f"❌ 評価更新エラー: {e}")
            return False

    def update_comment(self, image_id: int, comment: str) -> bool:
        """コメント更新"""
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE images SET comment = ? WHERE id = ?
            ''', (comment, image_id))

            conn.commit()
            conn.close()

            logger.info(f"✅ コメント更新: ID {image_id}")
            return True

        except Exception as e:
            logger.error(f"❌ コメント更新エラー: {e}")
            return False

# グローバルAPIインスタンス
gallery_api = GalleryAPI()
sync_worker = SyncWorker(interval_sec=300)

@app.route('/')
def index():
    """メインページ"""
    return render_template('gallery_api.html')

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """画像生成API（非同期）"""
    global job_counter
    job_counter += 1
    job_id = f"generate_{job_counter}_{int(time.time())}"

    data = request.json
    prompt = data.get('prompt', '')
    model = data.get('model', 'majicMIX lux 麦橘辉耀_56967.safetensors')  # SDXL標準
    # 高品質既定：デフォルト値を調整（steps20, guidance7.5）- SD APIの上限に合わせて20に制限
    steps = data.get('steps', 20)
    guidance_scale = data.get('guidance_scale', 7.5)
    negative_prompt = data.get('negative_prompt', None)
    mufufu_mode = data.get('mufufu_mode', False)  # ムフフモードフラグ
    # 解像度と自動顔補正オプション（SDXL標準: 1024×1024）
    width = data.get('width', 1024)
    height = data.get('height', 1024)
    auto_face_fix = data.get('auto_face_fix', False)

    if not prompt:
        return jsonify({"success": False, "error": "プロンプトが指定されていません"})

    try:
        # ステップ数の最小値チェック
        if steps < 10:
            steps = 10
            logger.warning("⚠️ ステップ数が少なすぎるため、10に設定しました")

        # guidance_scaleの上限チェック（8.0まで許可）
        if guidance_scale > 8.0:
            guidance_scale = 8.0
            logger.warning("⚠️ guidance_scaleが大きすぎるため、8.0に設定しました")

        # ジョブをキューに追加（強化されたキューを使用）
        job_data = {
            "prompt": prompt,
            "model": model,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "negative_prompt": negative_prompt,
            "mufufu_mode": mufufu_mode,
            "width": width,
            "height": height,
            "auto_face_fix": auto_face_fix
        }

        if use_enhanced_queue:
            # 優先度を決定（mufufu_modeは通常優先度、その他は標準）
            priority = JobPriority.NORMAL
            success = enhanced_queue.put(job_id, "generate", job_data, priority=priority)
            if not success:
                logger.warning(f"⚠️ ジョブキューが満杯: {job_id}")
                return jsonify({
                    "success": False,
                    "error": "ジョブキューが満杯です。しばらく待ってから再試行してください。"
                }), 503
            stats = enhanced_queue.get_queue_stats()
            logger.info(f"📥 ジョブ追加: {job_id} (キューサイズ: {stats['total_size']})")
        else:
            try:
                job_queue.put_nowait((job_id, "generate", job_data))
                logger.info(f"📥 ジョブ追加: {job_id} (キューサイズ: {job_queue.qsize()})")
            except queue.Full:
                logger.warning(f"⚠️ ジョブキューが満杯: {job_id}")
                return jsonify({
                    "success": False,
                    "error": "ジョブキューが満杯です。しばらく待ってから再試行してください。"
                }), 503

        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": "画像生成を開始しました"
        })

    except queue.Full:
        return jsonify({"success": False, "error": "サーバーが混雑しています。しばらく待ってから再試行してください"})

@app.route('/api/inpaint', methods=['POST'])
def api_inpaint():
    """顔修正API（非同期）"""
    global job_counter
    job_counter += 1
    job_id = f"inpaint_{job_counter}_{int(time.time())}"

    data = request.json
    image_path = data.get('image_path', '')
    face_prompt = data.get('face_prompt', 'beautiful face')

    job_data = {
        "image_path": image_path,
        "face_prompt": face_prompt
    }

    if use_enhanced_queue:
        priority = JobPriority.NORMAL
        success = enhanced_queue.put(job_id, "inpaint", job_data, priority=priority)
        if not success:
            return jsonify({
                "success": False,
                "error": "ジョブキューが満杯です。しばらく待ってから再試行してください。"
            }), 503
    else:
        try:
            job_queue.put((job_id, "inpaint", job_data))
        except queue.Full:
            return jsonify({"success": False, "error": "サーバーが混雑しています。しばらく待ってから再試行してください"}), 503

    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "顔修正を開始しました"
    })

@app.route('/api/enhance', methods=['POST'])
def api_enhance():
    """アダルト強化API（非同期）"""
    global job_counter
    job_counter += 1
    job_id = f"enhance_{job_counter}_{int(time.time())}"

    data = request.json
    image_path = data.get('image_path', '')
    enhancement_type = data.get('enhancement_type', 'sexy')
    lora_name = data.get('lora_name', None)  # 服脱がしの場合はLoRA名を指定可能

    job_data = {
        "image_path": image_path,
        "enhancement_type": enhancement_type,
        "lora_name": lora_name
    }

    if use_enhanced_queue:
        priority = JobPriority.NORMAL
        success = enhanced_queue.put(job_id, "enhance", job_data, priority=priority)
        if not success:
            return jsonify({
                "success": False,
                "error": "ジョブキューが満杯です。しばらく待ってから再試行してください。"
            }), 503
    else:
        try:
            job_queue.put((job_id, "enhance", job_data))
        except queue.Full:
            return jsonify({"success": False, "error": "サーバーが混雑しています。しばらく待ってから再試行してください"}), 503

    return jsonify({
        "success": True,
        "job_id": job_id,
        "message": "アダルト強化を開始しました"
    })

@app.route('/api/job/<job_id>', methods=['GET'])
def api_job_status(job_id):
    """ジョブステータス確認"""
    if job_id in job_results:
        info = job_results[job_id].copy()  # コピーして返す
        # 処理中で started_at があれば簡易経過時間を付与
        if info.get("status") == "processing" and info.get("started_at"):
            try:
                started = datetime.fromisoformat(info["started_at"]).timestamp()
                info["elapsed_sec"] = round(time.time() - started, 1)
            except Exception:
                pass
        # 完了済みでresultがある場合、filenameを抽出しやすくする
        if info.get("status") == "completed" and info.get("result"):
            result = info.get("result", {})
            # result.result.data.filename または result.data.filename を確認
            if isinstance(result, dict):
                data = result.get("data") or result.get("result", {}).get("data", {})
                if isinstance(data, dict) and data.get("filename"):
                    info["filename"] = data.get("filename")
        return jsonify(info)
    else:
        # 既知でないIDでも、キュー中の可能性があるため現在のキューサイズを返す
        return jsonify({"status": "processing", "queue_size": job_queue.qsize()})

@app.route('/api/models', methods=['GET'])
def api_models():
    """モデル一覧API"""
    result = gallery_api.get_models()
    return jsonify(result)

@app.route('/api/images', methods=['GET'])
def api_images():
    """画像一覧API"""
    limit = request.args.get('limit', 50, type=int)
    images = gallery_api.get_images(limit)
    return jsonify({"images": images})

@app.route('/api/register', methods=['POST'])
def api_register():
    """外部からの画像登録通知（ファイル名ベース）"""
    data = request.json or {}
    filename = data.get('filename')
    prompt = data.get('prompt', f"API生成画像: {filename}")
    model = data.get('model', 'majicmixRealistic_v7.safetensors')
    file_type = data.get('file_type', 'generated')
    if not filename:
        return jsonify({"success": False, "error": "filename is required"}), 400
    try:
        gallery_api.save_image_record(filename, prompt, model, file_type)
        logger.info(f"✅ 外部登録完了: {filename}")
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"❌ 外部登録失敗: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/rating', methods=['POST'])
def api_rating():
    """評価更新API"""
    data = request.json
    image_id = data.get('id')
    rating = data.get('rating')

    success = gallery_api.update_rating(image_id, rating)
    return jsonify({"success": success})

@app.route('/api/comment', methods=['POST'])
def api_comment():
    """コメント更新API"""
    data = request.json
    image_id = data.get('id')
    comment = data.get('comment')

    success = gallery_api.update_comment(image_id, comment)
    return jsonify({"success": success})

@app.route('/api/backup', methods=['POST'])
def api_backup():
    """DBバックアップAPI"""
    success = gallery_api.backup.backup_database()
    return jsonify({"success": success})

@app.route('/api/queue/stats', methods=['GET'])
def api_queue_stats():
    """キュー統計情報を取得"""
    if use_enhanced_queue:
        stats = enhanced_queue.get_queue_stats()
        return jsonify({
            "success": True,
            "enhanced": True,
            "stats": stats
        })
    else:
        return jsonify({
            "success": True,
            "enhanced": False,
            "queue_size": job_queue.qsize(),
            "max_size": JOB_QUEUE_SIZE if not use_enhanced_queue else None
        })

@app.route('/api/queue/job/<job_id>', methods=['GET'])
def api_queue_job_status(job_id):
    """特定ジョブの状態を取得"""
    if use_enhanced_queue:
        job_info = enhanced_queue.get_job_status(job_id)
        if job_info:
            return jsonify({
                "success": True,
                "job": job_info
            })
        else:
            # 従来のjob_resultsから取得
            if job_id in job_results:
                return jsonify({
                    "success": True,
                    "job": job_results[job_id]
                })
            return jsonify({
                "success": False,
                "error": "ジョブが見つかりません"
            }), 404
    else:
        if job_id in job_results:
            return jsonify({
                "success": True,
                "job": job_results[job_id]
            })
        return jsonify({
            "success": False,
            "error": "ジョブが見つかりません"
        }), 404

@app.route('/api/sync', methods=['POST'])
def api_sync():
    """未登録画像の手動同期"""
    added = gallery_api.sync_unregistered_images(limit=500)
    return jsonify({"success": True, "added": added})

@app.route('/api/reindex', methods=['POST'])
def api_reindex():
    """既存レコードのcreated_atをファイル名ベースで再計算"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename FROM images")
        rows = cursor.fetchall()
        updated = 0
        for _id, filename in rows:
            new_created = gallery_api._parse_created_at_from_filename(filename)
            cursor.execute("UPDATE images SET created_at = ? WHERE id = ?", (new_created, _id))
            updated += 1
        conn.commit()
        conn.close()
        return jsonify({"success": True, "updated": updated})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    """簡易ヘルス（キューサイズと最新応答）"""
    try:
        # キューサイズ取得（enhanced_queueまたは通常のキュー）
        if use_enhanced_queue:
            stats = enhanced_queue.get_queue_stats()
            size = stats.get('total_size', 0)
        else:
            size = job_queue.qsize() if 'job_queue' in globals() else 0

        # 直近完了ジョブの平均処理時間（最大50件）
        durations = []
        for v in list(job_results.values())[-50:]:
            if isinstance(v, dict) and v.get("status") == "completed" and isinstance(v.get("duration_sec"), (int, float)):
                durations.append(float(v["duration_sec"]))
        avg = round(sum(durations) / len(durations), 3) if durations else None
        return jsonify({"status": "ok", "queue_size": size, "avg_duration_sec": avg})
    except Exception as e:
        logger.error(f"❌ ヘルスチェックエラー: {e}")
        return jsonify({"status": "degraded", "error": str(e), "queue_size": 0}), 200  # 500ではなく200を返す

@app.route('/api/organize', methods=['POST'])
def api_organize():
    """ギャラリー整理（日付フォルダへリンク/コピー）"""
    result = gallery_api.organize_gallery()
    status = 200 if result.get('success') else 500
    return jsonify(result), status

@app.route('/api/metrics', methods=['GET'])
def api_metrics():
    """生成メトリクス: 件数、平均時間、直近の完了ジョブ情報"""
    try:
        completed = [v for v in job_results.values() if isinstance(v, dict) and v.get("status") == "completed"]
        durations = [float(v.get("duration_sec")) for v in completed if isinstance(v.get("duration_sec"), (int, float))]
        last5 = completed[-5:]
        return jsonify({
            "success": True,
            "count_completed": len(completed),
            "avg_duration_sec": (round(sum(durations) / len(durations), 3) if durations else None),
            "last5": last5
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/presets', methods=['GET'])
def api_presets():
    """モデルプリセット一覧取得"""
    try:
        # 安定モデルのプリセット
        models_resp = gallery_api.get_models()
        available = models_resp.get("data", []) if models_resp.get("success") else []
        model_names = [m.get("name") if isinstance(m, dict) else m for m in available]

        presets = {
            "recommended": {
                "name": "推奨（SDXL標準）",
                "model": "majicMIX lux 麦橘辉耀_56967.safetensors",
                "steps": 20,
                "guidance_scale": 7.5,
                "width": 1024,
                "height": 1024,
                "auto_face_fix": False,
                "description": "SDXL標準、高品質、バランス重視"
            },
            "quality": {
                "name": "高品質（SDXL 高解像度）",
                "model": "majicMIX lux 麦橘辉耀_56967.safetensors",
                "steps": 20,
                "guidance_scale": 7.5,
                "width": 1024,
                "height": 1024,
                "auto_face_fix": True,
                "description": "SDXL高解像度＋自動顔補正、時間はかかる（約10-15分）"
            },
            "fast": {
                "name": "高速（SDXL）",
                "model": "majicMIX lux 麦橘辉耀_56967.safetensors",
                "steps": 15,
                "guidance_scale": 6.5,
                "width": 1024,
                "height": 1024,
                "auto_face_fix": False,
                "description": "SDXL速めの生成（約5-7分）"
            },
            "face_priority": {
                "name": "顔品質最優先（SDXL）",
                "model": "majicMIX lux 麦橘辉耀_56967.safetensors",
                "steps": 20,
                "guidance_scale": 8.0,
                "width": 1024,
                "height": 1024,
                "auto_face_fix": True,
                "description": "SDXL顔品質最優先（guidance 8.0 + 自動顔補正）"
            }
        }

        # 利用可能なモデルでプリセットを更新
        for key in presets:
            preset_model = presets[key]["model"]
            if preset_model not in model_names and model_names:
                presets[key]["model"] = model_names[0]  # フォールバック

        # 顔安定モデル推奨（名前から判定）
        face_stable_keywords = ["realistic", "real", "face", "portrait", "beauty", "pro", "lux", "写实"]
        recommended_models = []
        for m in model_names:
            m_lower = m.lower()
            if any(kw in m_lower for kw in face_stable_keywords):
                recommended_models.append(m)

        return jsonify({
            "success": True,
            "presets": presets,
            "available_models": model_names[:10],
            "recommended_face_models": recommended_models[:5]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/job/<job_id>/retry', methods=['POST'])
def api_job_retry(job_id):
    """ジョブ再試行API（失敗したジョブを再実行）"""
    try:
        if job_id not in job_results:
            return jsonify({"success": False, "error": "ジョブが見つかりません"}), 404

        job_info = job_results[job_id]
        if job_info.get("status") != "error":
            return jsonify({"success": False, "error": "エラー状態のジョブのみ再試行可能です"}), 400

        # 元のリクエストデータから再実行
        request_data = job_info.get("request_data")
        if not request_data:
            return jsonify({"success": False, "error": "元のリクエストデータが取得できません"}), 400

        # 新しいジョブとして再実行
        global job_counter
        job_counter += 1
        new_job_id = f"retry_{job_counter}_{int(time.time())}"

        try:
            job_queue.put_nowait((new_job_id, job_info.get("job_type", "generate"), request_data))
            logger.info(f"🔄 ジョブ再試行: {job_id} -> {new_job_id}")
            return jsonify({
                "success": True,
                "new_job_id": new_job_id,
                "message": "再試行ジョブをキューに追加しました"
            })
        except queue.Full:
            return jsonify({"success": False, "error": "ジョブキューが満杯です"}), 503

    except Exception as e:
        logger.error(f"❌ ジョブ再試行エラー: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/job/<job_id>/estimate', methods=['GET'])
def api_job_estimate(job_id):
    """ジョブの推定残り時間計算"""
    try:
        if job_id not in job_results:
            return jsonify({"success": False, "estimated_sec": None, "message": "ジョブが見つかりません"})

        job_info = job_results[job_id]
        if job_info.get("status") != "processing":
            return jsonify({"success": True, "estimated_sec": 0, "status": job_info.get("status")})

        # 平均処理時間から推定
        completed = [v for v in job_results.values() if isinstance(v, dict) and v.get("status") == "completed"]
        durations = [float(v.get("duration_sec")) for v in completed if isinstance(v.get("duration_sec"), (int, float))]
        avg_duration = sum(durations) / len(durations) if durations else 300.0  # デフォルト5分

        # 開始からの経過時間
        started_at = job_info.get("started_at")
        if started_at:
            try:
                elapsed = time.time() - datetime.fromisoformat(started_at).timestamp()
                estimated_remaining = max(0, avg_duration - elapsed)
                return jsonify({
                    "success": True,
                    "estimated_sec": round(estimated_remaining, 1),
                    "elapsed_sec": round(elapsed, 1),
                    "avg_duration_sec": round(avg_duration, 1)
                })
            except Exception:
                pass

        return jsonify({"success": True, "estimated_sec": round(avg_duration, 1), "method": "average"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/images/<path:filename>')
def serve_image(filename):
    """画像ファイル配信"""
    # 生成画像、修正画像、ムフフ画像の順にチェック
    generated_path = os.path.join(GENERATED_IMAGES_DIR, filename)
    fixed_path = os.path.join(FIXED_IMAGES_DIR, filename)
    mufufu_path = os.path.join(MUFUFU_IMAGES_DIR, filename)

    if os.path.exists(generated_path):
        return send_file(generated_path)
    elif os.path.exists(fixed_path):
        return send_file(fixed_path)
    elif os.path.exists(mufufu_path):
        return send_file(mufufu_path)
    else:
        return "Image not found", 404

if __name__ == '__main__':
    logger.info("🎨 ManaOS Gallery Production Server 起動中...")

    # API接続確認
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            logger.info("✅ SD Inference API接続成功")
        else:
            logger.error("❌ SD Inference API接続失敗")
    except Exception as e:
        logger.error(f"❌ SD Inference API接続エラー: {e}")

    # 主要環境変数の要約を出力
    try:
        logger.info(
            "⚙️ 設定: JOB_QUEUE_SIZE=%s, SD_TIMEOUT=%ss, SD_RETRIES=%s",
            JOB_QUEUE_SIZE,
            getattr(gallery_api, 'generate_timeout_sec', 'n/a'),
            getattr(gallery_api, 'generate_retries', 'n/a')
        )
    except Exception:
        pass

    logger.info("🌐 Production Gallery Server起動: http://localhost:5559")
    app.run(host='0.0.0.0', port=5559, debug=os.getenv("DEBUG", "False").lower() == "true")
