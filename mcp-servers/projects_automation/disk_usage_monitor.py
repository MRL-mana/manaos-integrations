#!/usr/bin/env python3
"""
📊 ディスク使用率監視システム
90%超過で警告・自動クリーンアップ
"""
import shutil
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/disk_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DiskMonitor")

class DiskUsageMonitor:
    """ディスク使用率監視・自動対応システム"""
    
    def __init__(self):
        self.warning_threshold = 90  # 90%で警告
        self.critical_threshold = 95  # 95%で緊急対応
        self.target_usage = 85  # 85%まで削減する目標
        
        # 監視対象パーティション
        self.partitions = {
            '/': {'name': 'メインストレージ', 'critical': True},
            '/mnt/storage500': {'name': '追加ストレージ', 'critical': False}
        }
        
        # クリーンアップ対象（優先度順）
        self.cleanup_targets = [
            {
                'path': '/root/logs',
                'pattern': '*.log',
                'keep_days': 7,
                'priority': 1,
                'description': '古いログファイル'
            },
            {
                'path': '/mnt/storage500/tmp',
                'pattern': '*',
                'keep_days': 3,
                'priority': 2,
                'description': '一時ファイル'
            },
            {
                'path': '/mnt/storage500/backups_root',
                'pattern': '*',
                'keep_days': 30,
                'priority': 3,
                'description': '古いバックアップ'
            },
            {
                'path': '/root/.cache',
                'pattern': '*',
                'keep_days': 14,
                'priority': 4,
                'description': 'キャッシュファイル'
            },
            {
                'path': '/root/.npm',
                'pattern': '*',
                'keep_days': 30,
                'priority': 5,
                'description': 'NPMキャッシュ'
            }
        ]
        
        # 通知設定
        self.notification_log = Path('/root/logs/disk_alerts.log')
        self.notification_log.parent.mkdir(parents=True, exist_ok=True)
    
    def get_disk_usage(self, partition: str) -> dict:
        """ディスク使用状況を取得"""
        try:
            stat = shutil.disk_usage(partition)
            used_percent = (stat.used / stat.total) * 100
            
            return {
                'partition': partition,
                'total_gb': stat.total / (1024**3),
                'used_gb': stat.used / (1024**3),
                'free_gb': stat.free / (1024**3),
                'used_percent': used_percent
            }
        except Exception as e:
            logger.error(f"ディスク使用状況取得エラー: {e}")
            return None
    
    def check_all_partitions(self) -> dict:
        """全パーティションをチェック"""
        results = {}
        alerts = []
        
        for partition, info in self.partitions.items():
            usage = self.get_disk_usage(partition)
            if not usage:
                continue
            
            results[partition] = usage
            
            # アラートレベル判定
            if usage['used_percent'] >= self.critical_threshold:
                level = '🔴 CRITICAL'
                alerts.append({
                    'level': 'critical',
                    'partition': partition,
                    'usage': usage
                })
            elif usage['used_percent'] >= self.warning_threshold:
                level = '🟡 WARNING'
                alerts.append({
                    'level': 'warning',
                    'partition': partition,
                    'usage': usage
                })
            else:
                level = '🟢 OK'
            
            logger.info(
                f"{level} {info['name']} ({partition}): "
                f"{usage['used_percent']:.1f}% "
                f"({usage['free_gb']:.1f}GB free)"
            )
        
        return {'results': results, 'alerts': alerts}
    
    def cleanup_old_files(self, target: dict, dry_run=False) -> int:
        """古いファイルをクリーンアップ"""
        path = Path(target['path'])
        if not path.exists():
            return 0
        
        pattern = target['pattern']
        keep_days = target['keep_days']
        cutoff_timestamp = datetime.now().timestamp() - (keep_days * 86400)
        
        freed_bytes = 0
        files_deleted = 0
        
        try:
            for file_path in path.rglob(pattern):
                if not file_path.is_file():
                    continue
                
                # 作成日時チェック
                if file_path.stat().st_mtime < cutoff_timestamp:
                    file_size = file_path.stat().st_size
                    
                    if dry_run:
                        logger.info(f"[DRY-RUN] 削除予定: {file_path} ({file_size / 1024 / 1024:.1f}MB)")
                    else:
                        try:
                            file_path.unlink()
                            freed_bytes += file_size
                            files_deleted += 1
                            logger.info(f"削除: {file_path} ({file_size / 1024 / 1024:.1f}MB)")
                        except Exception as e:
                            logger.error(f"削除失敗: {file_path} - {e}")
            
            if not dry_run and files_deleted > 0:
                logger.info(
                    f"✅ {target['description']} クリーンアップ完了: "
                    f"{files_deleted}ファイル, {freed_bytes / 1024 / 1024:.1f}MB解放"
                )
            
        except Exception as e:
            logger.error(f"クリーンアップエラー: {e}")
        
        return freed_bytes
    
    def auto_cleanup(self, partition: str, target_percent: float) -> bool:
        """自動クリーンアップ実行"""
        logger.info(f"🧹 自動クリーンアップ開始: {partition}")
        
        current_usage = self.get_disk_usage(partition)
        if not current_usage:
            return False
        
        total_freed = 0
        target_bytes = (current_usage['used_percent'] - target_percent) / 100 * (current_usage['total_gb'] * 1024**3)
        
        # 優先度順にクリーンアップ
        for target in sorted(self.cleanup_targets, key=lambda x: x['priority']):
            if total_freed >= target_bytes:
                break
            
            logger.info(f"クリーンアップ: {target['description']}")
            freed = self.cleanup_old_files(target, dry_run=False)
            total_freed += freed
        
        # 結果確認
        new_usage = self.get_disk_usage(partition)
        logger.info(
            f"✅ クリーンアップ完了: {total_freed / 1024 / 1024:.1f}MB解放\n"
            f"   使用率: {current_usage['used_percent']:.1f}% → {new_usage['used_percent']:.1f}%"
        )
        
        return new_usage['used_percent'] < target_percent
    
    def send_alert(self, alert: dict):
        """アラート送信（ログ記録）"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        usage = alert['usage']
        level = alert['level']
        
        message = (
            f"[{timestamp}] {level.upper()} ALERT\n"
            f"パーティション: {alert['partition']}\n"
            f"使用率: {usage['used_percent']:.1f}%\n"
            f"空き容量: {usage['free_gb']:.1f}GB\n"
            f"{'=' * 50}\n"
        )
        
        # ログファイルに記録
        with open(self.notification_log, 'a') as f:
            f.write(message)
        
        logger.warning(message)
    
    def monitor(self, auto_cleanup_enabled=True):
        """監視実行"""
        logger.info("=" * 60)
        logger.info("📊 ディスク使用率監視開始")
        logger.info("=" * 60)
        
        check_result = self.check_all_partitions()
        
        # アラート処理
        for alert in check_result['alerts']:
            self.send_alert(alert)
            
            # CRITICAL状態なら自動クリーンアップ
            if alert['level'] == 'critical' and auto_cleanup_enabled:
                logger.warning("⚠️ CRITICAL状態検出: 自動クリーンアップ実行")
                self.auto_cleanup(
                    alert['partition'],
                    self.target_usage
                )
        
        logger.info("=" * 60)
        logger.info("✅ 監視完了")
        logger.info("=" * 60)
        
        return check_result

if __name__ == "__main__":
    monitor = DiskUsageMonitor()
    monitor.monitor(auto_cleanup_enabled=True)


