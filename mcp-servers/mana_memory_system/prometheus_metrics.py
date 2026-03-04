#!/usr/bin/env python3
"""
Prometheusメトリクスエクスポーター
記憶システムの監視メトリクスを提供

メトリクス:
- memory_hot_total: ホットメモリ件数
- obsidian_sync_last_seconds: 最終同期からの経過秒
- backup_last_ok_seconds: 最後に成功したバックアップからの経過秒
- backup_rpo_breach: RPO違反（0/1）
- restore_checksum_mismatch_total: 復元ハッシュ不一致回数
"""

from prometheus_client import Gauge, Counter, start_http_server
import time
import sqlite3
import sys
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MEMORY_DIR = Path("/root/.mana_memory")
DB_PATH = MEMORY_DIR / "hot_memory.db"
AUDIT_DB_PATH = MEMORY_DIR / "memory_audit.db"
SYNC_STATE_FILE = MEMORY_DIR / "obsidian_sync_state.json"
BACKUP_INDEX_FILE = Path("/root/Google Drive/ManaMemoryArchive/encrypted_backups/index.json")

# Prometheusメトリクス定義
memory_hot_total = Gauge('memory_hot_total', 'ホットメモリ件数')
obsidian_sync_last_seconds = Gauge('obsidian_sync_last_seconds', '最終同期からの経過秒')
backup_last_ok_seconds = Gauge('backup_last_ok_seconds', '最後に成功したバックアップからの経過秒')
backup_rpo_breach = Gauge('backup_rpo_breach', 'RPO違反（0=正常, 1=違反）', ['backup_type'])
restore_checksum_mismatch_total = Counter('restore_checksum_mismatch_total', '復元ハッシュ不一致回数')
memory_drift_total = Gauge('memory_drift_total', 'ドリフト検出件数')

# 追加メトリクス
backup_snapshot_bytes = Gauge('backup_snapshot_bytes', 'スナップショット容量（バイト）', ['backup_type'])
memory_write_conflict_total = Counter('memory_write_conflict_total', '楽観ロック競合回数')
pii_masked_records_total = Counter('pii_masked_records_total', 'PIIマスク件数')
tamper_chain_break_total = Counter('tamper_chain_break_total', '監査ハッシュ不一致回数')


def update_metrics():
    """メトリクスを更新"""
    try:
        # ホットメモリ件数
        if DB_PATH.exists():
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM memories")
            count = cur.fetchone()[0]
            memory_hot_total.set(count)
            conn.close()

        # Obsidian同期最終時刻
        if SYNC_STATE_FILE.exists():
            try:
                with open(SYNC_STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    last_sync = state.get('last_sync_time')
                    if last_sync:
                        from datetime import datetime
                        last_sync_dt = datetime.fromisoformat(last_sync)
                        elapsed = (datetime.now() - last_sync_dt).total_seconds()
                        obsidian_sync_last_seconds.set(elapsed)
            except IOError as e:
                obsidian_sync_last_seconds.set(-1)
        else:
            obsidian_sync_last_seconds.set(-1)

        # バックアップ最終成功時刻
        if BACKUP_INDEX_FILE.exists():
            try:
                with open(BACKUP_INDEX_FILE, 'r', encoding='utf-8') as f:
                    index = json.load(f)
                    backups = index.get('backups', [])
                    if backups:
                        # 最新のバックアップを取得
                        latest = max(backups, key=lambda b: b.get('date', ''))
                        from datetime import datetime
                        latest_dt = datetime.fromisoformat(latest.get('date', ''))
                        elapsed = (datetime.now() - latest_dt).total_seconds()
                        backup_last_ok_seconds.set(elapsed)

                        # RPO違反チェック（24時間以内にバックアップがあるか）
                        rpo_ok = elapsed <= 86400  # 24時間
                        backup_rpo_breach.labels(backup_type='all').set(0 if rpo_ok else 1)
                    else:
                        backup_last_ok_seconds.set(-1)
                        backup_rpo_breach.labels(backup_type='all').set(1)
            except Exception as e:
                backup_last_ok_seconds.set(-1)
                backup_rpo_breach.labels(backup_type='all').set(1)
        else:
            backup_last_ok_seconds.set(-1)
            backup_rpo_breach.labels(backup_type='all').set(1)

        # ドリフト検出件数
        if AUDIT_DB_PATH.exists():
            try:
                conn = sqlite3.connect(str(AUDIT_DB_PATH))
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM memory_audit WHERE event = 'desynced'")
                drift_count = cur.fetchone()[0]
                memory_drift_total.set(drift_count)
                conn.close()
            except sqlite3.Error as e:
                memory_drift_total.set(-1)
        else:
            memory_drift_total.set(0)

        # バックアップスナップショット容量
        try:
            backup_dir = Path("/root/.mana_memory_backups")
            if backup_dir.exists():
                total_size = sum(f.stat().st_size for f in backup_dir.glob("*.tar.gz"))
                backup_snapshot_bytes.labels(backup_type='local').set(total_size)
        except Exception as e:
            pass

        # チェーン整合性チェック
        try:
            sys.path.insert(0, '/root/.mana_memory')
            from memory_audit import MemoryAudit
            audit = MemoryAudit()
            integrity = audit.verify_chain_integrity()
            if not integrity.get('integrity_ok'):
                tamper_chain_break_total.inc(integrity.get('break_count', 0))
        except Exception as e:
            pass

    except Exception as e:
        logger.error(f"メトリクス更新エラー: {e}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Prometheusメトリクスエクスポーター')
    parser.add_argument('--port', type=int, default=9091, help='HTTPサーバーポート')
    parser.add_argument('--once', action='store_true', help='1回だけ更新して終了')
    args = parser.parse_args()

    if args.once:
        # 1回だけ更新
        update_metrics()
        print("✅ メトリクス更新完了")
    else:
        # HTTPサーバー起動
        start_http_server(args.port)
        logger.info(f"📊 Prometheusメトリクスサーバー起動: ポート{args.port}")

        # 定期的にメトリクス更新
        while True:
            update_metrics()
            time.sleep(30)  # 30秒ごとに更新


if __name__ == '__main__':
    main()

