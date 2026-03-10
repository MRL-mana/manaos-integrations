#!/usr/bin/env python3
"""
Mana PDF Excel AI Ultimate Automation System
自動化・スケジューリング・監視システム
"""

import os
import json
import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import psutil
import requests
from mana_pdf_excel_ai_ultimate import get_ultimate_converter, batch_pdf_to_excel_ai

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/mana_pdf_excel_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ManaPDFExcelAutomation")

class PDFFileHandler(FileSystemEventHandler):
    """PDFファイル監視ハンドラー"""
    
    def __init__(self, converter, callback):
        self.converter = converter
        self.callback = callback
        self.processing_files = set()
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = event.src_path
        if file_path.lower().endswith('.pdf') and file_path not in self.processing_files:
            self.processing_files.add(file_path)
            logger.info(f"📁 新しいPDFファイル検出: {Path(file_path).name}")
            
            # ファイルが完全に書き込まれるまで待機
            time.sleep(2)
            
            # 変換実行
            asyncio.create_task(self.callback(file_path))
            
            # 処理完了後にリストから削除
            self.processing_files.discard(file_path)

class ManaPDFExcelAutomation:
    """PDF→Excel自動化システム"""
    
    def __init__(self):
        self.name = "Mana PDF Excel Automation Ultimate"
        self.version = "2.0.0"
        self.converter = get_ultimate_converter()
        
        # 設定
        self.config = {
            'watch_directories': [
                '/root/automation_input',
                '/root/Documents/PDF',
                '/root/Downloads'
            ],
            'output_directory': '/root/excel_output_ultimate',
            'backup_directory': '/root/Google Drive/Automated_Excel',
            'schedule_config': {
                'daily_conversion': True,
                'hourly_monitoring': True,
                'weekly_cleanup': True,
                'monthly_report': True
            },
            'notification': {
                'enabled': True,
                'webhook_url': None,
                'email': None
            },
            'quality_threshold': 0.8,
            'max_file_size_mb': 100
        }
        
        # 監視設定
        self.observers = []
        self.is_running = False
        
        # 統計情報
        self.stats = {
            'total_automated_conversions': 0,
            'total_watched_files': 0,
            'total_errors': 0,
            'last_activity': None,
            'uptime_start': datetime.now(),
            'schedule_runs': 0
        }
        
        logger.info(f"🚀 {self.name} v{self.version} 初期化完了")
    
    def load_config(self, config_path: str = "/root/automation_config.json"):
        """設定ファイル読み込み"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                logger.info(f"✅ 設定ファイル読み込み完了: {config_path}")
            else:
                self.save_config(config_path)
        except Exception as e:
            logger.error(f"❌ 設定ファイル読み込みエラー: {e}")
    
    def save_config(self, config_path: str = "/root/automation_config.json"):
        """設定ファイル保存"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 設定ファイル保存完了: {config_path}")
        except Exception as e:
            logger.error(f"❌ 設定ファイル保存エラー: {e}")
    
    async def process_pdf_file(self, file_path: str):
        """PDFファイル自動処理"""
        try:
            logger.info(f"🔄 自動処理開始: {Path(file_path).name}")
            
            # ファイルサイズチェック
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.config['max_file_size_mb']:
                logger.warning(f"⚠️ ファイルサイズ超過: {file_size_mb:.1f}MB > {self.config['max_file_size_mb']}MB")
                return
            
            # 変換実行
            result = await self.converter.convert_pdf_to_excel_ai(file_path, use_multi_ai=True)
            
            if result['success']:
                self.stats['total_automated_conversions'] += 1
                logger.info(f"✅ 自動変換完了: {result['excel_file']}")
                
                # バックアップ
                await self.backup_file(result['excel_path'])
                
                # 通知送信
                await self.send_notification(
                    "✅ PDF自動変換完了",
                    f"ファイル: {Path(file_path).name}\nExcel: {result['excel_file']}\n処理時間: {result['processing_time']:.2f}秒"
                )
                
                # 元ファイル移動（オプション）
                if self.config.get('move_processed_files', False):
                    processed_dir = Path(self.config['output_directory']) / "processed_pdfs"
                    processed_dir.mkdir(exist_ok=True)
                    
                    new_path = processed_dir / Path(file_path).name
                    os.rename(file_path, new_path)
                    logger.info(f"📁 元ファイル移動: {new_path}")
                
            else:
                self.stats['total_errors'] += 1
                logger.error(f"❌ 自動変換失敗: {result['error']}")
                
                await self.send_notification(
                    "❌ PDF自動変換失敗",
                    f"ファイル: {Path(file_path).name}\nエラー: {result['error']}"
                )
            
            self.stats['total_watched_files'] += 1
            self.stats['last_activity'] = datetime.now().isoformat()
            
        except Exception as e:
            self.stats['total_errors'] += 1
            logger.error(f"❌ 自動処理エラー: {e}")
    
    async def backup_file(self, file_path: str):
        """ファイルバックアップ"""
        try:
            if not self.config.get('backup_directory'):
                return
            
            backup_dir = Path(self.config['backup_directory'])
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            file_name = Path(file_path).name
            backup_path = backup_dir / file_name
            
            # Google Driveへのバックアップ
            if backup_dir.name == "Google Drive":
                from simple_gdrive_upload import upload_single_file
                result = upload_single_file(file_path)
                if result.get('success'):
                    logger.info(f"☁️ Google Driveバックアップ完了: {file_name}")
                else:
                    logger.warning(f"⚠️ Google Driveバックアップ失敗: {result.get('error')}")
            else:
                # ローカルバックアップ
                import shutil
                shutil.copy2(file_path, backup_path)
                logger.info(f"💾 ローカルバックアップ完了: {backup_path}")
                
        except Exception as e:
            logger.error(f"❌ バックアップエラー: {e}")
    
    async def send_notification(self, title: str, message: str):
        """通知送信"""
        try:
            if not self.config['notification']['enabled']:
                return
            
            # Webhook通知
            webhook_url = self.config['notification'].get('webhook_url')
            if webhook_url:
                payload = {
                    'text': f"📊 {title}\n{message}",
                    'username': 'Mana PDF Excel AI',
                    'icon_emoji': ':robot_face:'
                }
                
                response = requests.post(webhook_url, json=payload, timeout=10)
                if response.status_code == 200:
                    logger.info("📢 Webhook通知送信完了")
                else:
                    logger.warning(f"⚠️ Webhook通知送信失敗: {response.status_code}")
            
            # メール通知（実装予定）
            email = self.config['notification'].get('email')
            if email:
                # メール送信機能をここに実装
                pass
                
        except Exception as e:
            logger.error(f"❌ 通知送信エラー: {e}")
    
    def setup_file_watching(self):
        """ファイル監視設定"""
        logger.info("👁️ ファイル監視設定開始")
        
        for watch_dir in self.config['watch_directories']:
            watch_path = Path(watch_dir)
            if watch_path.exists():
                handler = PDFFileHandler(self.converter, self.process_pdf_file)
                observer = Observer()
                observer.schedule(handler, str(watch_path), recursive=True)
                observer.start()
                self.observers.append(observer)
                
                logger.info(f"✅ 監視開始: {watch_dir}")
            else:
                # ディレクトリ作成
                watch_path.mkdir(parents=True, exist_ok=True)
                handler = PDFFileHandler(self.converter, self.process_pdf_file)
                observer = Observer()
                observer.schedule(handler, str(watch_path), recursive=True)
                observer.start()
                self.observers.append(observer)
                
                logger.info(f"✅ 監視ディレクトリ作成・監視開始: {watch_dir}")
        
        logger.info(f"👁️ ファイル監視設定完了: {len(self.observers)}ディレクトリ")
    
    def setup_scheduling(self):
        """スケジューリング設定"""
        logger.info("⏰ スケジューリング設定開始")
        
        # 日次処理
        if self.config['schedule_config']['daily_conversion']:
            schedule.every().day.at("09:00").do(self.daily_automation)
            logger.info("✅ 日次自動処理設定: 09:00")
        
        # 時間毎監視
        if self.config['schedule_config']['hourly_monitoring']:
            schedule.every().hour.do(self.hourly_monitoring)
            logger.info("✅ 時間毎監視設定")
        
        # 週次クリーンアップ
        if self.config['schedule_config']['weekly_cleanup']:
            schedule.every().monday.at("02:00").do(self.weekly_cleanup)
            logger.info("✅ 週次クリーンアップ設定: 月曜 02:00")
        
        # 月次レポート
        if self.config['schedule_config']['monthly_report']:
            schedule.every().month.do(self.monthly_report)  # type: ignore
            logger.info("✅ 月次レポート設定")
        
        logger.info("⏰ スケジューリング設定完了")
    
    def daily_automation(self):
        """日次自動処理"""
        logger.info("🌅 日次自動処理開始")
        self.stats['schedule_runs'] += 1
        
        try:
            # 監視ディレクトリの未処理PDFをチェック
            for watch_dir in self.config['watch_directories']:
                watch_path = Path(watch_dir)
                if watch_path.exists():
                    pdf_files = list(watch_path.glob("*.pdf"))
                    if pdf_files:
                        logger.info(f"📁 未処理PDF発見: {len(pdf_files)}ファイル ({watch_dir})")
                        
                        # 非同期でバッチ処理
                        asyncio.create_task(self.batch_process_files(pdf_files))
            
            # システム状態チェック
            self.system_health_check()
            
        except Exception as e:
            logger.error(f"❌ 日次自動処理エラー: {e}")
    
    def hourly_monitoring(self):
        """時間毎監視"""
        logger.info("👁️ 時間毎監視実行")
        
        try:
            # システムリソース監視
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent
            
            logger.info(f"📊 システム状態 - CPU: {cpu_percent}%, Memory: {memory_percent}%, Disk: {disk_percent}%")
            
            # 警告閾値チェック
            if cpu_percent > 90:
                asyncio.create_task(self.send_notification(
                    "⚠️ CPU使用率警告",
                    f"CPU使用率: {cpu_percent}%"
                ))
            
            if memory_percent > 90:
                asyncio.create_task(self.send_notification(
                    "⚠️ メモリ使用率警告",
                    f"メモリ使用率: {memory_percent}%"
                ))
            
            if disk_percent > 90:
                asyncio.create_task(self.send_notification(
                    "⚠️ ディスク使用率警告",
                    f"ディスク使用率: {disk_percent}%"
                ))
            
        except Exception as e:
            logger.error(f"❌ 時間毎監視エラー: {e}")
    
    def weekly_cleanup(self):
        """週次クリーンアップ"""
        logger.info("🧹 週次クリーンアップ開始")
        
        try:
            output_dir = Path(self.config['output_directory'])
            
            # 古いファイル削除（7日以上前）
            cutoff_date = datetime.now() - timedelta(days=7)
            removed_count = 0
            
            for file_path in output_dir.glob("*.xlsx"):
                if datetime.fromtimestamp(file_path.stat().st_mtime) < cutoff_date:
                    file_path.unlink()
                    removed_count += 1
            
            logger.info(f"🗑️ 古いファイル削除: {removed_count}ファイル")
            
            # ログファイルローテーション
            log_dir = Path("/root/logs")
            for log_file in log_dir.glob("*.log"):
                if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                    # ログファイル圧縮・アーカイブ
                    import gzip
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                            f_out.writelines(f_in)
                    log_file.unlink()
                    logger.info(f"📦 ログファイル圧縮: {log_file.name}")
            
        except Exception as e:
            logger.error(f"❌ 週次クリーンアップエラー: {e}")
    
    def monthly_report(self):
        """月次レポート生成"""
        logger.info("📊 月次レポート生成開始")
        
        try:
            # 統計情報収集
            uptime = datetime.now() - self.stats['uptime_start']
            
            report = {
                'report_date': datetime.now().isoformat(),
                'uptime_days': uptime.days,
                'statistics': self.stats.copy(),
                'system_info': {
                    'cpu_count': psutil.cpu_count(),
                    'memory_total': psutil.virtual_memory().total,
                    'disk_total': psutil.disk_usage('/').total
                },
                'config': self.config
            }
            
            # レポート保存
            report_path = Path(self.config['output_directory']) / f"monthly_report_{datetime.now().strftime('%Y%m')}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 月次レポート保存: {report_path}")
            
            # 通知送信
            asyncio.create_task(self.send_notification(
                "📊 月次レポート生成完了",
                f"総変換数: {self.stats['total_automated_conversions']}\n稼働日数: {uptime.days}日"
            ))
            
        except Exception as e:
            logger.error(f"❌ 月次レポート生成エラー: {e}")
    
    async def batch_process_files(self, pdf_files: List[Path]):
        """ファイル一括処理"""
        try:
            file_paths = [str(f) for f in pdf_files]
            result = await batch_pdf_to_excel_ai(file_paths, use_multi_ai=True)
            
            logger.info(f"✅ バッチ処理完了: {result['successful']}/{result['total_files']}成功")
            
        except Exception as e:
            logger.error(f"❌ バッチ処理エラー: {e}")
    
    def system_health_check(self):
        """システムヘルスチェック"""
        try:
            # 基本的なシステムチェック
            health_status = {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'process_count': len(psutil.pids()),
                'automation_stats': self.stats.copy()
            }
            
            # ヘルスステータス保存
            health_path = Path("/root/logs/automation_health.json")
            with open(health_path, 'w', encoding='utf-8') as f:
                json.dump(health_status, f, ensure_ascii=False, indent=2)
            
            logger.info("💚 システムヘルスチェック完了")
            
        except Exception as e:
            logger.error(f"❌ システムヘルスチェックエラー: {e}")
    
    def start(self):
        """自動化システム開始"""
        logger.info("🚀 自動化システム開始")
        
        try:
            # 設定読み込み
            self.load_config()
            
            # ファイル監視開始
            self.setup_file_watching()
            
            # スケジューリング開始
            self.setup_scheduling()
            
            self.is_running = True
            logger.info("✅ 自動化システム起動完了")
            
            # メインループ
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # 1分間隔でチェック
                
        except KeyboardInterrupt:
            logger.info("🛑 自動化システム停止要求受信")
            self.stop()
        except Exception as e:
            logger.error(f"❌ 自動化システムエラー: {e}")
            self.stop()
    
    def stop(self):
        """自動化システム停止"""
        logger.info("🛑 自動化システム停止中...")
        
        self.is_running = False
        
        # 監視停止
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        logger.info("✅ 自動化システム停止完了")
    
    def get_status(self) -> Dict[str, Any]:
        """システム状態取得"""
        uptime = datetime.now() - self.stats['uptime_start']
        
        return {
            'system_info': {
                'name': self.name,
                'version': self.version,
                'is_running': self.is_running,
                'uptime_days': uptime.days,
                'uptime_hours': uptime.total_seconds() / 3600
            },
            'automation_stats': self.stats.copy(),
            'watch_directories': self.config['watch_directories'],
            'observers_count': len(self.observers),
            'config': self.config
        }


# グローバルインスタンス
_automation_system = None

def get_automation_system() -> ManaPDFExcelAutomation:
    """自動化システム取得"""
    global _automation_system
    if _automation_system is None:
        _automation_system = ManaPDFExcelAutomation()
    return _automation_system


if __name__ == "__main__":
    print("🚀 Mana PDF Excel AI Ultimate Automation System")
    print("=" * 60)
    
    automation = get_automation_system()
    
    try:
        automation.start()
    except Exception as e:
        print(f"❌ システムエラー: {e}")
        automation.stop()



