#!/usr/bin/env python3
"""
MRL Memory TTL Manager
TTL（Time To Live）による自動削除
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json

# 統一モジュールのインポート
try:
    from unified_logging import get_service_logger
    logger = get_service_logger("mrl-memory-ttl-manager")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class TTLManager:
    """
    TTL（Time To Live）による自動削除
    
    短期メモリは消える前提:
    - セッション終了で削除
    - TTLで自動削除
    - 昇格条件満たしたものだけ長期へ
    """
    
    def __init__(self, memory_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            memory_dir: メモリディレクトリ
        """
        if memory_dir is None:
            memory_dir = Path(__file__).parent / "mrl_memory"
        
        self.memory_dir = Path(memory_dir)
        self.scratchpad_path = self.memory_dir / "scratchpad.jsonl"
        
        # TTLマッピング
        self.ttl_hours = {
            "1h": 1,
            "1d": 24,
            "7d": 168
        }
        
        logger.info("✅ TTL Manager初期化完了")
    
    def cleanup_expired_entries(self) -> int:
        """
        期限切れエントリを削除
        
        Returns:
            削除されたエントリ数
        """
        if not self.scratchpad_path.exists():
            return 0
        
        # 全エントリを読み込み
        all_entries = []
        expired_count = 0
        
        with open(self.scratchpad_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry_dict = json.loads(line.strip())
                    
                    # TTLチェック
                    if self._is_expired(entry_dict):
                        expired_count += 1
                        continue
                    
                    all_entries.append(entry_dict)
                except Exception as e:
                    logger.warning(f"エントリ読み込みエラー: {e}")
                    continue
        
        # ファイルに書き戻し
        with open(self.scratchpad_path, 'w', encoding='utf-8') as f:
            for entry in all_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        if expired_count > 0:
            logger.info(f"期限切れエントリを削除: {expired_count}件")
        
        return expired_count
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """
        エントリが期限切れかチェック
        
        Args:
            entry: エントリ
        
        Returns:
            期限切れかどうか
        """
        timestamp = entry.get('timestamp', '')
        ttl_str = entry.get('ttl', '1d')
        
        if not timestamp:
            return False
        
        try:
            entry_time = datetime.fromisoformat(timestamp)
            ttl_hours = self.ttl_hours.get(ttl_str, 24)
            
            age_hours = (datetime.now() - entry_time).total_seconds() / 3600
            
            return age_hours > ttl_hours
        except Exception:
            return False
    
    def cleanup_session(self, session_id: str) -> int:
        """
        セッション終了で削除
        
        Args:
            session_id: セッションID
        
        Returns:
            削除されたエントリ数
        """
        if not self.scratchpad_path.exists():
            return 0
        
        # 全エントリを読み込み
        all_entries = []
        deleted_count = 0
        
        with open(self.scratchpad_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry_dict = json.loads(line.strip())
                    
                    # セッションIDでフィルタ
                    if entry_dict.get('source', '').startswith(session_id):
                        deleted_count += 1
                        continue
                    
                    all_entries.append(entry_dict)
                except Exception as e:
                    logger.warning(f"エントリ読み込みエラー: {e}")
                    continue
        
        # ファイルに書き戻し
        with open(self.scratchpad_path, 'w', encoding='utf-8') as f:
            for entry in all_entries:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        if deleted_count > 0:
            logger.info(f"セッション終了で削除: {deleted_count}件 (session_id: {session_id})")
        
        return deleted_count
