#!/usr/bin/env python3
"""
記憶監査ログシステム
整合性＆ドリフト検知

機能:
- 楽観ロック（更新時の競合検知）
- ドリフト検出（Obsidian↔DBの差分検知）
- 監査ログ（全変更履歴）
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MEMORY_DIR = Path("/root/.mana_memory")
DB_PATH = MEMORY_DIR / "hot_memory.db"
AUDIT_DB_PATH = MEMORY_DIR / "memory_audit.db"
OBSIDIAN_VAULT = Path("/root/Obsidian/ManaOS_Chronicle")


class MemoryAudit:
    """記憶監査システム"""

    def __init__(self):
        self._init_audit_db()

    def _init_audit_db(self):
        """監査DB初期化（ハッシュ連鎖対応）"""
        conn = sqlite3.connect(str(AUDIT_DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER,
                event TEXT NOT NULL,
                source TEXT NOT NULL,
                diff TEXT,
                old_value TEXT,
                new_value TEXT,
                checksum TEXT,
                prev_hash TEXT,
                chain_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_id ON memory_audit(memory_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_event ON memory_audit(event)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON memory_audit(created_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chain_hash ON memory_audit(chain_hash)
        """)
        conn.commit()
        conn.close()

    def log_event(self, memory_id: Optional[int], event: str, source: str,
                  diff: Optional[Dict] = None, old_value: Optional[Dict] = None,
                  new_value: Optional[Dict] = None):
        """イベントをログ（ハッシュ連鎖対応）"""
        try:
            conn = sqlite3.connect(str(AUDIT_DB_PATH))

            # チェックサム計算
            content = json.dumps(new_value or old_value or {}, sort_keys=True, ensure_ascii=False)
            checksum = hashlib.sha256(content.encode()).hexdigest()

            # 前のレコードのハッシュを取得（ハッシュ連鎖）
            prev_hash = None
            cur = conn.cursor()
            cur.execute("SELECT chain_hash FROM memory_audit ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if row and row[0]:
                prev_hash = row[0]

            # チェーンハッシュ計算（前のハッシュ + 現在のデータ）
            chain_input = (prev_hash or "") + checksum + str(memory_id or "") + event + source
            chain_hash = hashlib.sha256(chain_input.encode()).hexdigest()

            conn.execute("""
                INSERT INTO memory_audit (
                    memory_id, event, source, diff, old_value, new_value, checksum, prev_hash, chain_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                event,
                source,
                json.dumps(diff, ensure_ascii=False) if diff else None,
                json.dumps(old_value, ensure_ascii=False) if old_value else None,
                json.dumps(new_value, ensure_ascii=False) if new_value else None,
                checksum,
                prev_hash,
                chain_hash
            ))
            conn.commit()
            conn.close()
            logger.debug(f"監査ログ記録: {event} (memory_id={memory_id}, source={source}, chain_hash={chain_hash[:16]}...)")
        except Exception as e:
            logger.error(f"監査ログ記録エラー: {e}")

    def verify_chain_integrity(self) -> Dict:
        """ハッシュ連鎖の整合性検証"""
        try:
            conn = sqlite3.connect(str(AUDIT_DB_PATH))
            conn.row_factory = sqlite3.Row

            rows = conn.execute("SELECT id, prev_hash, chain_hash, event, memory_id, source FROM memory_audit ORDER BY id").fetchall()
            conn.close()

            breaks = []
            prev_chain_hash = None

            for row in rows:
                expected_prev = prev_chain_hash
                actual_prev = row['prev_hash']

                if expected_prev != actual_prev:
                    breaks.append({
                        'id': row['id'],
                        'expected_prev_hash': expected_prev,
                        'actual_prev_hash': actual_prev,
                        'event': row['event'],
                        'memory_id': row['memory_id']
                    })

                # チェーンハッシュ検証
                checksum = hashlib.sha256(
                    json.dumps({
                        'memory_id': row['memory_id'],
                        'event': row['event'],
                        'source': row['source']
                    }, sort_keys=True).encode()
                ).hexdigest()

                chain_input = (prev_chain_hash or "") + checksum + str(row['memory_id'] or "") + row['event'] + row['source']
                expected_chain = hashlib.sha256(chain_input.encode()).hexdigest()

                if expected_chain != row['chain_hash']:
                    breaks.append({
                        'id': row['id'],
                        'type': 'chain_hash_mismatch',
                        'expected': expected_chain,
                        'actual': row['chain_hash']
                    })

                prev_chain_hash = row['chain_hash']

            return {
                "integrity_ok": len(breaks) == 0,
                "total_records": len(rows),
                "breaks": breaks,
                "break_count": len(breaks)
            }
        except Exception as e:
            logger.error(f"チェーン整合性検証エラー: {e}")
            return {"error": str(e)}

    def export_anchor(self, output_path: Path) -> bool:
        """アンカー（最新のチェーンハッシュ）をエクスポート"""
        try:
            conn = sqlite3.connect(str(AUDIT_DB_PATH))
            cur = conn.cursor()
            cur.execute("SELECT chain_hash FROM memory_audit ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            conn.close()

            if row and row[0]:
                anchor = {
                    "chain_hash": row[0],
                    "timestamp": datetime.now().isoformat(),
                    "description": "監査ログチェーンハッシュアンカー"
                }

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(anchor, f, ensure_ascii=False, indent=2)

                logger.info(f"アンカーエクスポート: {output_path}")
                return True
            else:
                logger.warning("アンカーが存在しません（レコードなし）")
                return False
        except Exception as e:
            logger.error(f"アンカーエクスポートエラー: {e}")
            return False

    def check_optimistic_lock(self, memory_id: int, expected_updated_at: str) -> bool:
        """楽観ロックチェック"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.cursor()
            cur.execute("SELECT updated_at FROM memories WHERE id = ?", (memory_id,))
            row = cur.fetchone()
            conn.close()

            if row and row[0] == expected_updated_at:
                return True
            return False
        except Exception as e:
            logger.error(f"楽観ロックチェックエラー: {e}")
            return False

    def detect_drift(self) -> List[Dict]:
        """ドリフト検出（Obsidian↔DBの差分）"""
        drifts = []

        try:
            # DBから記憶を取得
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            db_memories = {}
            for row in conn.execute("SELECT id, content, importance, category, updated_at FROM memories"):
                db_memories[row['id']] = dict(row)
            conn.close()

            # Obsidianから記憶を取得
            obsidian_memories = {}
            memories_dir = OBSIDIAN_VAULT / "Memories"
            if memories_dir.exists():
                for md_file in memories_dir.rglob("*.md"):
                    try:
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # フロントマターからIDを抽出（存在する場合）
                        # 簡易実装: ファイル名から推測
                        # 実際の実装では、フロントマターにmemory_idを保存する必要がある
                        pass
                    except IOError as e:
                        continue

            # 差分検出
            # TODO: より詳細な差分検出ロジック

            return drifts
        except Exception as e:
            logger.error(f"ドリフト検出エラー: {e}")
            return []

    def get_audit_log(self, memory_id: Optional[int] = None,
                     event: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """監査ログ取得"""
        try:
            conn = sqlite3.connect(str(AUDIT_DB_PATH))
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM memory_audit WHERE 1=1"
            params = []

            if memory_id:
                query += " AND memory_id = ?"
                params.append(memory_id)

            if event:
                query += " AND event = ?"
                params.append(event)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            logs = [dict(row) for row in rows]

            conn.close()
            return logs
        except Exception as e:
            logger.error(f"監査ログ取得エラー: {e}")
            return []

    def get_drift_stats(self) -> Dict:
        """ドリフト統計"""
        try:
            conn = sqlite3.connect(str(AUDIT_DB_PATH))
            cur = conn.cursor()

            # ドリフトイベント数
            cur.execute("SELECT COUNT(*) FROM memory_audit WHERE event = 'desynced'")
            drift_count = cur.fetchone()[0]

            # 最近のドリフト（24時間以内）
            cur.execute("""
                SELECT COUNT(*) FROM memory_audit
                WHERE event = 'desynced'
                AND created_at > datetime('now', '-24 hours')
            """)
            recent_drift = cur.fetchone()[0]

            conn.close()

            return {
                "total_drifts": drift_count,
                "recent_drifts_24h": recent_drift,
                "drift_rate": recent_drift / 24.0 if recent_drift > 0 else 0.0
            }
        except Exception as e:
            logger.error(f"ドリフト統計取得エラー: {e}")
            return {"error": str(e)}


def main():
    import argparse

    parser = argparse.ArgumentParser(description='記憶監査システム')
    parser.add_argument('--detect-drift', action='store_true', help='ドリフト検出')
    parser.add_argument('--stats', action='store_true', help='統計表示')
    parser.add_argument('--log', type=int, help='監査ログ表示（件数）')
    args = parser.parse_args()

    audit = MemoryAudit()

    if args.detect_drift:
        drifts = audit.detect_drift()
        print(f"ドリフト検出: {len(drifts)}件")
        for drift in drifts:
            print(json.dumps(drift, ensure_ascii=False, indent=2))

    if args.stats:
        stats = audit.get_drift_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    if args.log:
        logs = audit.get_audit_log(limit=args.log)
        print(f"監査ログ: {len(logs)}件")
        for log in logs:
            print(f"  [{log['created_at']}] {log['event']} (memory_id={log['memory_id']}, source={log['source']})")


if __name__ == '__main__':
    main()

