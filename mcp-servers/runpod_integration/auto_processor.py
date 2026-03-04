#!/usr/bin/env python3
"""
自動処理システム
イベント駆動・スケジュール実行で自動処理
"""

import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import json
import logging
from logging.handlers import RotatingFileHandler

sys.path.insert(0, '/root/runpod_integration')
sys.path.insert(0, '/root')


class AutoProcessor:
    """自動処理クラス"""

    def __init__(self):
        self.running = False
        self.thread = None
        self.config_file = Path("/root/runpod_integration/auto_config.json")
        self.log_dir = Path("/root/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()
        self.load_config()
        self.stats = {
            "total_generated": 0,
            "total_upscaled": 0,
            "total_gifs": 0,
            "total_trainings": 0,
            "last_update": datetime.now().isoformat()
        }
        self.stats_file = Path("/root/runpod_integration/auto_stats.json")
        self.load_stats()

    def _setup_logging(self):
        """ログ設定"""
        log_file = self.log_dir / "auto_processor.log"
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)

        self.logger = logging.getLogger('AutoProcessor')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(handler)

    def _log(self, message: str, level: str = "INFO"):
        """ログ出力"""
        log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        print(log_msg)

        if level == "ERROR":
            self.logger.error(message)
        elif level == "WARNING":
            self.logger.warning(message)
        else:
            self.logger.info(message)

    def _log_error(self, message: str):
        """エラーログ出力"""
        self._log(message, "ERROR")

    def load_stats(self):
        """統計情報を読み込み"""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats.update(json.load(f))
            except:
                pass

    def save_stats(self):
        """統計情報を保存"""
        self.stats["last_update"] = datetime.now().isoformat()
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)

    def load_config(self):
        """設定を読み込み"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "auto_generate": {
                    "enabled": False,
                    "interval_minutes": 60,
                    "prompts": [],
                    "count_per_run": 5
                },
                "auto_upscale": {
                    "enabled": False,
                    "on_new_image": True,
                    "scale": 2,
                    "method": "simple"
                },
                "auto_training": {
                    "enabled": False,
                    "on_dataset_update": True,
                    "auto_steps": 1000
                },
                "auto_gif": {
                    "enabled": False,
                    "on_new_batch": True,
                    "batch_size": 5
                }
            }
            self.save_config()

    def save_config(self):
        """設定を保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def start(self):
        """自動処理を開始"""
        if self.running:
            print("⚠️  既に実行中です")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._log("自動処理システムを開始しました")

    def stop(self):
        """自動処理を停止"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self._log("自動処理システムを停止しました")

    def _run_loop(self):
        """メインループ"""
        last_generate_time = datetime.now()
        last_check_time = datetime.now()
        last_training_check_time = datetime.now()

        # データセット更新履歴を追跡
        self.tracked_datasets = self._get_tracked_datasets()

        while self.running:
            try:
                now = datetime.now()

                # 1. 自動画像生成（スケジュール実行）
                if self.config.get("auto_generate", {}).get("enabled"):
                    interval = self.config["auto_generate"]["interval_minutes"]
                    if (now - last_generate_time).total_seconds() >= interval * 60:
                        self._auto_generate()
                        last_generate_time = now

                # 2. 新規画像の自動超解像
                if self.config.get("auto_upscale", {}).get("enabled") and \
                   self.config.get("auto_upscale", {}).get("on_new_image"):
                    if (now - last_check_time).total_seconds() >= 60:  # 1分ごとにチェック
                        self._auto_upscale_new_images()
                        last_check_time = now

                # 3. 新規画像バッチの自動GIF生成
                if self.config.get("auto_gif", {}).get("enabled") and \
                   self.config.get("auto_gif", {}).get("on_new_batch"):
                    if (now - last_check_time).total_seconds() >= 60:
                        self._auto_gif_new_batch()

                # 4. 自動LoRA学習（データセット更新時）
                if self.config.get("auto_training", {}).get("enabled") and \
                   self.config.get("auto_training", {}).get("on_dataset_update"):
                    if (now - last_training_check_time).total_seconds() >= 300:  # 5分ごとにチェック
                        self._auto_training_on_dataset_update()
                        last_training_check_time = now

                time.sleep(10)  # 10秒ごとにチェック

            except Exception as e:
                self._log_error(f"自動処理エラー: {e}")
                time.sleep(60)  # エラー時は1分待機

    def _auto_generate(self):
        """自動画像生成"""
        try:
            from manaos_unified_system.services.runpod_serverless_client import RunPodServerlessClient

            config = self.config.get("auto_generate", {})
            prompts = config.get("prompts", [])
            count = config.get("count_per_run", 5)

            if not prompts:
                self._log("自動生成: プロンプトが設定されていません", "WARNING")
                return

            self._log(f"自動画像生成開始: {count}枚")

            client = RunPodServerlessClient()
            success_count = 0

            for i, prompt in enumerate(prompts[:count], 1):
                try:
                    result = client.generate_image(
                        prompt=prompt,
                        model="stable_diffusion",
                        width=1024,
                        height=768,
                        steps=30,
                        negative_prompt="nsfw, low quality",
                        save_to_network_storage=False
                    )

                    if result.get('status') == 'completed':
                        self._log(f"  [{i}/{count}] ✅ 生成成功: {prompt[:50]}...")
                        success_count += 1
                    else:
                        self._log_error(f"  [{i}/{count}] ❌ 生成失敗: {result.get('error')}")

                    time.sleep(2)  # レート制限対策

                except Exception as e:
                    self._log_error(f"  [{i}/{count}] ❌ エラー: {e}")

            self.stats["total_generated"] += success_count
            self.save_stats()
            self._log(f"自動画像生成完了: {success_count}/{count}枚成功")

        except Exception as e:
            self._log_error(f"自動画像生成エラー: {e}")

    def _auto_upscale_new_images(self):
        """新規画像の自動超解像"""
        try:
            import requests

            gallery_dir = Path("/root/trinity_workspace/generated_images")
            config = self.config.get("auto_upscale", {})

            # 最近追加された画像をチェック（直近1時間）
            now = datetime.now()
            new_images = []

            for img_file in gallery_dir.glob("*.png"):
                if "upscaled_" in img_file.name:
                    continue  # 既に超解像済みはスキップ

                mtime = datetime.fromtimestamp(img_file.stat().st_mtime)
                if (now - mtime).total_seconds() < 3600:  # 1時間以内
                    new_images.append(img_file.name)

            if not new_images:
                return

            self._log(f"新規画像の自動超解像: {len(new_images)}枚")

            BASE_URL = "http://localhost:5556"
            scale = config.get("scale", 2)
            method = config.get("method", "simple")
            success_count = 0

            for img_name in new_images[:10]:  # 最大10枚まで
                try:
                    response = requests.post(
                        f"{BASE_URL}/api/upscale",
                        json={
                            "filename": img_name,
                            "scale": scale,
                            "method": method
                        },
                        timeout=60
                    )

                    if response.status_code == 200:
                        self._log(f"  ✅ 超解像完了: {img_name}")
                        success_count += 1
                    else:
                        self._log_error(f"  ❌ 超解像失敗: {img_name}")

                    time.sleep(1)

                except Exception as e:
                    self._log_error(f"  ❌ エラー: {img_name} - {e}")

            self.stats["total_upscaled"] += success_count
            self.save_stats()

        except Exception as e:
            self._log_error(f"自動超解像エラー: {e}")

    def _auto_gif_new_batch(self):
        """新規画像バッチの自動GIF生成"""
        try:
            import requests

            gallery_dir = Path("/root/trinity_workspace/generated_images")
            config = self.config.get("auto_gif", {})
            batch_size = config.get("batch_size", 5)

            # 最近追加された画像を取得
            now = datetime.now()
            new_images = []

            for img_file in sorted(gallery_dir.glob("*.png"),
                                  key=lambda x: x.stat().st_mtime,
                                  reverse=True):
                if "gif_" in img_file.name or "video_" in img_file.name:
                    continue

                mtime = datetime.fromtimestamp(img_file.stat().st_mtime)
                if (now - mtime).total_seconds() < 3600:  # 1時間以内
                    new_images.append(img_file.name)

            if len(new_images) < batch_size:
                return

            self._log(f"新規画像バッチの自動GIF生成: {batch_size}枚")

            BASE_URL = "http://localhost:5556"
            image_group = new_images[:batch_size]

            try:
                response = requests.post(
                    f"{BASE_URL}/api/generate_gif",
                    json={
                        "filenames": image_group,
                        "duration": 0.5,
                        "loop": 0
                    },
                    timeout=300
                )

                if response.status_code == 200:
                    result = response.json()
                    self._log(f"  ✅ GIF生成完了: {result.get('filename')}")
                    self.stats["total_gifs"] += 1
                    self.save_stats()
                else:
                    self._log_error(f"  ❌ GIF生成失敗: {response.text}")

            except Exception as e:
                self._log_error(f"  ❌ エラー: {e}")

        except Exception as e:
            self._log_error(f"自動GIF生成エラー: {e}")

    def enable_auto_generate(self, prompts: List[str], interval_minutes: int = 60, count_per_run: int = 5):
        """自動画像生成を有効化"""
        self.config["auto_generate"] = {
            "enabled": True,
            "interval_minutes": interval_minutes,
            "prompts": prompts,
            "count_per_run": count_per_run
        }
        self.save_config()
        print(f"✅ 自動画像生成を有効化: {interval_minutes}分ごとに{count_per_run}枚生成")

    def enable_auto_upscale(self, scale: int = 2, method: str = "simple"):
        """自動超解像を有効化"""
        self.config["auto_upscale"] = {
            "enabled": True,
            "on_new_image": True,
            "scale": scale,
            "method": method
        }
        self.save_config()
        print(f"✅ 自動超解像を有効化: 新規画像を自動で{scale}倍に拡大")

    def enable_auto_gif(self, batch_size: int = 5):
        """自動GIF生成を有効化"""
        self.config["auto_gif"] = {
            "enabled": True,
            "on_new_batch": True,
            "batch_size": batch_size
        }
        self.save_config()
        print(f"✅ 自動GIF生成を有効化: {batch_size}枚の新規画像で自動生成")

    def _get_tracked_datasets(self) -> Dict[str, datetime]:
        """追跡中のデータセットを取得"""
        try:
            from dataset_manager import DatasetManager
            manager = DatasetManager()
            datasets = manager.list_datasets()

            tracked = {}
            for dataset in datasets:
                dataset_dir = Path(dataset["path"])
                info_file = dataset_dir / "dataset_info.json"
                if info_file.exists():
                    mtime = datetime.fromtimestamp(info_file.stat().st_mtime)
                    tracked[dataset["name"]] = mtime

            return tracked
        except:
            return {}

    def _auto_training_on_dataset_update(self):
        """データセット更新時の自動LoRA学習"""
        try:
            from dataset_manager import DatasetManager
            from manaos_training_client import ManaOSTrainingClient

            config = self.config.get("auto_training", {})

            # 現在のデータセットを取得
            manager = DatasetManager()
            datasets = manager.list_datasets()

            # 更新されたデータセットを検出
            updated_datasets = []
            current_tracked = {}

            for dataset in datasets:
                dataset_name = dataset["name"]
                dataset_dir = Path(dataset["path"])
                info_file = dataset_dir / "dataset_info.json"

                if info_file.exists():
                    mtime = datetime.fromtimestamp(info_file.stat().st_mtime)
                    current_tracked[dataset_name] = mtime

                    # 前回の追跡結果と比較
                    if dataset_name not in self.tracked_datasets or \
                       mtime > self.tracked_datasets[dataset_name]:
                        updated_datasets.append(dataset)

            # 追跡情報を更新
            self.tracked_datasets = current_tracked

            if not updated_datasets:
                return

            self._log(f"データセット更新検出: {len(updated_datasets)}件")

            # 各データセットで学習を実行
            client = ManaOSTrainingClient()

            for dataset in updated_datasets:
                try:
                    dataset_name = dataset["name"]
                    dataset_dir = Path(dataset["path"])
                    trigger_word = dataset.get("trigger_word", dataset_name)
                    image_count = dataset.get("image_count", 0)

                    if image_count < 5:
                        self._log(f"  データセット '{dataset_name}' は画像数が少ないためスキップ", "WARNING")
                        continue

                    self._log(f"  自動学習開始: {dataset_name} (画像数: {image_count})")

                    # 画像パスを取得
                    image_paths = []
                    for img_file in dataset_dir.glob("*.png"):
                        if img_file.name != "metadata.jsonl":
                            image_paths.append(str(img_file))

                    if not image_paths:
                        continue

                    # 学習ステップ数を決定（画像数に応じて）
                    steps = min(config.get("auto_steps", 1000), image_count * 200)

                    # 学習実行
                    result = client.train_lora(
                        image_paths=image_paths,
                        trigger_word=trigger_word,
                        output_name=f"{dataset_name}_auto",
                        steps=steps,
                        learning_rate=1e-4,
                        batch_size=1,
                        resolution=512
                    )

                    if result.get("success"):
                        self._log(f"  ✅ 学習完了: {dataset_name}")
                        self.stats["total_trainings"] += 1
                        self.save_stats()
                    else:
                        self._log_error(f"  ❌ 学習失敗: {dataset_name} - {result.get('error')}")

                    time.sleep(10)  # レート制限対策

                except Exception as e:
                    self._log_error(f"  ❌ エラー: {dataset['name']} - {e}")

        except Exception as e:
            self._log_error(f"自動学習エラー: {e}")

    def enable_auto_training(self, auto_steps: int = 1000):
        """自動LoRA学習を有効化"""
        self.config["auto_training"] = {
            "enabled": True,
            "on_dataset_update": True,
            "auto_steps": auto_steps
        }
        self.save_config()
        print(f"✅ 自動LoRA学習を有効化: データセット更新時に自動学習（{auto_steps}ステップ）")

    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        self.load_stats()
        return self.stats.copy()

    def get_status(self) -> Dict[str, Any]:
        """現在のステータスを取得"""
        return {
            "running": self.running,
            "config": self.config,
            "stats": self.get_stats()
        }


def main():
    """メイン処理"""
    processor = AutoProcessor()

    print("🤖 自動処理システム")
    print("=" * 60)
    print()

    # 現在の設定を表示
    print("📊 現在の設定:")
    print(f"   自動画像生成: {'有効' if processor.config.get('auto_generate', {}).get('enabled') else '無効'}")
    print(f"   自動超解像: {'有効' if processor.config.get('auto_upscale', {}).get('enabled') else '無効'}")
    print(f"   自動GIF生成: {'有効' if processor.config.get('auto_gif', {}).get('enabled') else '無効'}")
    print()

    print("💡 使い方:")
    print("   processor = AutoProcessor()")
    print("   processor.enable_auto_generate(prompts=['beautiful landscape', ...])")
    print("   processor.enable_auto_upscale()")
    print("   processor.start()")
    print()
    print("   自動処理を停止: processor.stop()")


if __name__ == "__main__":
    main()





