"""
SVI × Wan 2.2 自動化モジュール
スケジュール実行、フォルダ監視、自動生成などの自動化機能
"""

import os
import time
import json
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
import requests

logger = logging.getLogger(__name__)

try:
    from svi_wan22_video_integration import SVIWan22VideoIntegration
    SVI_AVAILABLE = True
except ImportError:
    SVI_AVAILABLE = False
    logger.warning("SVI統合モジュールが見つかりません")


class SVIWatchdogHandler(FileSystemEventHandler):
    """ファイルシステム監視ハンドラー"""
    
    def __init__(self, callback: Callable, watch_extensions: List[str] = ['.png', '.jpg', '.jpeg']):
        """
        初期化
        
        Args:
            callback: ファイル追加時のコールバック関数
            watch_extensions: 監視するファイル拡張子
        """
        self.callback = callback
        self.watch_extensions = [ext.lower() for ext in watch_extensions]
        self.processed_files = set()
    
    def on_created(self, event):
        """ファイル作成時の処理"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.suffix.lower() in self.watch_extensions:
            # 少し待ってから処理（ファイル書き込み完了を待つ）
            time.sleep(1)
            if file_path not in self.processed_files:
                self.processed_files.add(file_path)
                logger.info(f"新しい画像ファイルを検出: {file_path}")
                self.callback(str(file_path))


class SVIAutomation:
    """SVI自動化クラス"""
    
    def __init__(
        self,
        svi_integration: Optional[SVIWan22VideoIntegration] = None,
        api_base_url: str = "http://localhost:9500"
    ):
        """
        初期化
        
        Args:
            svi_integration: SVI統合インスタンス
            api_base_url: 統合APIサーバーのベースURL
        """
        self.svi = svi_integration or (SVIWan22VideoIntegration() if SVI_AVAILABLE else None)
        self.api_base_url = api_base_url
        self.observer = None
        self.scheduled_tasks = []
        self.running = False
        self.thread = None
        self.config_path = Path(__file__).parent / "svi_automation_config.json"
        self.load_config()
    
    def load_config(self):
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                logger.warning(f"設定読み込みエラー: {e}")
                self.config = {}
        else:
            self.config = {
                "watch_folders": [],
                "scheduled_tasks": [],
                "auto_generate": {
                    "enabled": False,
                    "default_prompt": "beautiful scene, cinematic, smooth motion",
                    "video_length_seconds": 5,
                    "steps": 6,
                    "motion_strength": 1.3
                },
                "notifications": {
                    "enabled": False,
                    "webhook_url": None
                }
            }
            self.save_config()
    
    def save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def watch_folder(
        self,
        folder_path: str,
        auto_generate: bool = True,
        default_prompt: Optional[str] = None
    ):
        """
        フォルダを監視して、新しい画像が追加されたら自動生成
        
        Args:
            folder_path: 監視するフォルダのパス
            auto_generate: 自動生成を有効にするか
            default_prompt: デフォルトプロンプト
        """
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"フォルダが見つかりません: {folder_path}")
            return False
        
        def on_image_added(image_path: str):
            """画像追加時の処理"""
            if auto_generate:
                prompt = default_prompt or self.config.get("auto_generate", {}).get("default_prompt", "")
                logger.info(f"自動生成を開始: {image_path}")
                self.auto_generate_video(image_path, prompt)
        
        handler = SVIWatchdogHandler(on_image_added)
        observer = Observer()
        observer.schedule(handler, str(folder), recursive=False)
        observer.start()
        
        if self.observer is None:
            self.observer = observer
        
        # 設定に追加
        watch_folders = self.config.get("watch_folders", [])
        if folder_path not in watch_folders:
            watch_folders.append({
                "path": folder_path,
                "auto_generate": auto_generate,
                "default_prompt": default_prompt
            })
            self.config["watch_folders"] = watch_folders
            self.save_config()
        
        logger.info(f"フォルダ監視を開始: {folder_path}")
        return True
    
    def auto_generate_video(
        self,
        image_path: str,
        prompt: Optional[str] = None,
        video_length_seconds: int = 5
    ) -> Optional[str]:
        """
        自動的に動画を生成
        
        Args:
            image_path: 画像パス
            prompt: プロンプト（Noneの場合はデフォルト）
            video_length_seconds: 動画の長さ
            
        Returns:
            プロンプトID
        """
        if not self.svi or not self.svi.is_available():
            logger.error("SVI統合が利用できません")
            return None
        
        auto_config = self.config.get("auto_generate", {})
        prompt = prompt or auto_config.get("default_prompt", "beautiful scene, cinematic")
        video_length_seconds = video_length_seconds or auto_config.get("video_length_seconds", 5)
        steps = auto_config.get("steps", 6)
        motion_strength = auto_config.get("motion_strength", 1.3)
        
        try:
            prompt_id = self.svi.generate_video(
                start_image_path=image_path,
                prompt=prompt,
                video_length_seconds=video_length_seconds,
                steps=steps,
                motion_strength=motion_strength
            )
            
            if prompt_id:
                logger.info(f"自動生成開始: {prompt_id} (画像: {image_path})")
                self.send_notification("動画生成開始", {
                    "prompt_id": prompt_id,
                    "image_path": image_path,
                    "prompt": prompt
                })
            
            return prompt_id
        except Exception as e:
            logger.error(f"自動生成エラー: {e}")
            return None
    
    def schedule_task(
        self,
        task_name: str,
        schedule_time: datetime,
        image_path: str,
        prompt: str,
        video_length_seconds: int = 5,
        repeat: bool = False,
        repeat_interval: Optional[timedelta] = None
    ):
        """
        スケジュールタスクを追加
        
        Args:
            task_name: タスク名
            schedule_time: 実行時刻
            image_path: 画像パス
            prompt: プロンプト
            video_length_seconds: 動画の長さ
            repeat: 繰り返し実行するか
            repeat_interval: 繰り返し間隔
        """
        task = {
            "name": task_name,
            "schedule_time": schedule_time.isoformat(),
            "image_path": image_path,
            "prompt": prompt,
            "video_length_seconds": video_length_seconds,
            "repeat": repeat,
            "repeat_interval": repeat_interval.total_seconds() if repeat_interval else None,
            "enabled": True
        }
        
        scheduled_tasks = self.config.get("scheduled_tasks", [])
        scheduled_tasks.append(task)
        self.config["scheduled_tasks"] = scheduled_tasks
        self.save_config()
        
        logger.info(f"スケジュールタスクを追加: {task_name} ({schedule_time})")
    
    def start_scheduler(self):
        """スケジューラーを開始"""
        if self.running:
            logger.warning("スケジューラーは既に実行中です")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        logger.info("スケジューラーを開始しました")
    
    def stop_scheduler(self):
        """スケジューラーを停止"""
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join()
        logger.info("スケジューラーを停止しました")
    
    def _scheduler_loop(self):
        """スケジューラーのメインループ"""
        while self.running:
            try:
                scheduled_tasks = self.config.get("scheduled_tasks", [])
                now = datetime.now()
                
                for task in scheduled_tasks:
                    if not task.get("enabled", True):
                        continue
                    
                    schedule_time = datetime.fromisoformat(task["schedule_time"])
                    
                    # 実行時刻を過ぎているかチェック
                    if now >= schedule_time:
                        # タスクを実行
                        self._execute_scheduled_task(task)
                        
                        # 繰り返し設定
                        if task.get("repeat", False):
                            interval = task.get("repeat_interval")
                            if interval:
                                next_time = schedule_time + timedelta(seconds=interval)
                                task["schedule_time"] = next_time.isoformat()
                            else:
                                task["enabled"] = False
                        else:
                            task["enabled"] = False
                
                self.save_config()
                time.sleep(60)  # 1分ごとにチェック
            except Exception as e:
                logger.error(f"スケジューラーループエラー: {e}")
                time.sleep(60)
    
    def _execute_scheduled_task(self, task: Dict[str, Any]):
        """スケジュールタスクを実行"""
        logger.info(f"スケジュールタスクを実行: {task.get('name', 'Unknown')}")
        
        self.auto_generate_video(
            image_path=task["image_path"],
            prompt=task["prompt"],
            video_length_seconds=task.get("video_length_seconds", 5)
        )
    
    def send_notification(self, title: str, data: Dict[str, Any]):
        """通知を送信"""
        notifications = self.config.get("notifications", {})
        if not notifications.get("enabled", False):
            return
        
        webhook_url = notifications.get("webhook_url")
        if not webhook_url:
            return
        
        try:
            payload = {
                "title": title,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            requests.post(webhook_url, json=payload, timeout=5)
            logger.info(f"通知を送信: {title}")
        except Exception as e:
            logger.warning(f"通知送信エラー: {e}")
    
    def batch_process_folder(
        self,
        folder_path: str,
        prompt: Optional[str] = None,
        max_files: Optional[int] = None
    ) -> List[str]:
        """
        フォルダ内の画像を一括処理
        
        Args:
            folder_path: フォルダパス
            prompt: プロンプト（Noneの場合はデフォルト）
            max_files: 最大処理ファイル数
            
        Returns:
            プロンプトIDのリスト
        """
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"フォルダが見つかりません: {folder_path}")
            return []
        
        image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
        image_files = [
            f for f in folder.iterdir()
            if f.suffix.lower() in image_extensions and f.is_file()
        ]
        
        if max_files:
            image_files = image_files[:max_files]
        
        execution_ids = []
        for image_file in image_files:
            prompt_id = self.auto_generate_video(str(image_file), prompt)
            if prompt_id:
                execution_ids.append(prompt_id)
            time.sleep(1)  # API負荷を軽減
        
        logger.info(f"バッチ処理完了: {len(execution_ids)}/{len(image_files)}件")
        return execution_ids











