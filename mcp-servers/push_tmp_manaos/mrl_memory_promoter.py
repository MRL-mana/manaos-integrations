#!/usr/bin/env python3
"""
MRL Memory Promoter
昇格ルールの実装（短期→長期）
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# 統一モジュールのインポート
try:
    from unified_logging import get_service_logger
    logger = get_service_logger("mrl-memory-promoter")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Obsidian統合（オプション）
try:
    from obsidian_integration import ObsidianIntegration
    OBSIDIAN_AVAILABLE = True
except ImportError:
    OBSIDIAN_AVAILABLE = False


class MRLMemoryPromoter:
    """
    昇格ルールの実装
    
    一定条件を満たしたら長期へ：
    - 3回以上参照された
    - confidence=high
    - ttl切れても残したい
    """
    
    def __init__(
        self,
        memory_dir: Optional[Path] = None,
        obsidian_vault: Optional[str] = None
    ):
        """
        初期化
        
        Args:
            memory_dir: メモリディレクトリ
            obsidian_vault: Obsidian Vaultパス（オプション）
        """
        if memory_dir is None:
            env_dir = str(os.getenv("MRL_MEMORY_DIR", "") or "").strip()
            if env_dir:
                memory_dir = Path(env_dir)
            else:
                memory_dir = Path(__file__).parent / "mrl_memory"

        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.scratchpad_path = self.memory_dir / "scratchpad.jsonl"
        self.promoted_path = self.memory_dir / "promoted.jsonl"
        
        # Obsidian統合
        self.obsidian = None
        if OBSIDIAN_AVAILABLE and obsidian_vault:
            try:
                self.obsidian = ObsidianIntegration(obsidian_vault)  # type: ignore[possibly-unbound]
                if not self.obsidian.is_available():
                    self.obsidian = None
            except Exception as e:
                logger.warning(f"Obsidian統合エラー: {e}")
                self.obsidian = None
        
        # 昇格条件
        self.promotion_rules = {
            "min_access_count": 3,  # 最低アクセス回数
            "min_confidence": "high",  # 最低信頼度
            "min_age_days": 1,  # 最低経過日数
        }
    
    def check_and_promote(self) -> List[Dict[str, Any]]:
        """
        昇格条件を満たすエントリをチェックして昇格
        
        Returns:
            昇格したエントリのリスト
        """
        if not self.scratchpad_path.exists():
            return []
        
        # 全エントリを読み込み
        all_entries = self._load_all_entries()
        
        # 昇格候補を選定
        candidates = []
        for entry in all_entries:
            if self._should_promote(entry):
                candidates.append(entry)
        
        # 昇格処理
        promoted = []
        for candidate in candidates:
            try:
                self._promote_entry(candidate)
                promoted.append(candidate)
            except Exception as e:
                logger.error(f"昇格エラー: {e}")
        
        logger.info(f"昇格完了: {len(promoted)}件")
        return promoted
    
    def _load_all_entries(self) -> List[Dict[str, Any]]:
        """全エントリを読み込み"""
        if not self.scratchpad_path.exists():
            return []
        
        entries = []
        with open(self.scratchpad_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry_dict = json.loads(line.strip())
                    entries.append(entry_dict)
                except Exception as e:
                    logger.warning(f"エントリ読み込みエラー: {e}")
                    continue
        
        return entries
    
    def _should_promote(self, entry: Dict[str, Any]) -> bool:
        """
        昇格すべきかチェック
        
        Args:
            entry: エントリ
        
        Returns:
            昇格すべきかどうか
        """
        # アクセス回数チェック
        access_count = entry.get('access_count', 0)
        if access_count < self.promotion_rules["min_access_count"]:
            return False
        
        # 信頼度チェック
        confidence = entry.get('confidence', 'low')
        confidence_map = {"low": 0, "med": 1, "high": 2}
        min_conf = confidence_map.get(self.promotion_rules["min_confidence"], 0)
        entry_conf = confidence_map.get(confidence, 0)
        
        if entry_conf < min_conf:
            return False
        
        # 経過日数チェック
        timestamp = entry.get('timestamp', '')
        try:
            entry_time = datetime.fromisoformat(timestamp)
            age_days = (datetime.now() - entry_time).days
            
            if age_days < self.promotion_rules["min_age_days"]:
                return False
        except Exception as e:
            logger.warning(f"タイムスタンプ解析エラー: {e}")
            return False
        
        return True
    
    def _promote_entry(self, entry: Dict[str, Any]):
        """
        エントリを昇格
        
        Args:
            entry: 昇格するエントリ
        """
        # 昇格済みリストに追加
        promoted_entry = {
            **entry,
            "promoted_at": datetime.now().isoformat(),
            "promoted_from": "scratchpad"
        }
        
        with open(self.promoted_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(promoted_entry, ensure_ascii=False) + '\n')
        
        # Obsidianに保存（オプション）
        if self.obsidian:
            try:
                self._save_to_obsidian(entry)
            except Exception as e:
                logger.warning(f"Obsidian保存エラー: {e}")
        
        # Scratchpadから削除（簡易実装：全件書き直し）
        self._remove_from_scratchpad(entry)
    
    def _save_to_obsidian(self, entry: Dict[str, Any]):
        """
        Obsidianに保存
        
        Args:
            entry: エントリ
        """
        if not self.obsidian:
            return
        
        # タイトルを生成
        key = entry.get('key', 'unknown')
        title = f"MRL Memory: {key}"
        
        # コンテンツを生成
        content = f"""# {title}

## キー
{key}

## 値
{entry.get('value', '')}

## メタデータ
- 信頼度: {entry.get('confidence', 'unknown')}
- アクセス回数: {entry.get('access_count', 0)}
- 作成日: {entry.get('timestamp', 'unknown')}
- 昇格日: {datetime.now().isoformat()}

## ソース
{entry.get('source', 'unknown')}
"""
        
        # ノートを作成
        self.obsidian.create_note(
            title=title,
            content=content,
            tags=["MRL-Memory", "Promoted"],
            folder="MRL Memory"
        )
    
    def _remove_from_scratchpad(self, entry: Dict[str, Any]):
        """
        Scratchpadから削除
        
        Args:
            entry: 削除するエントリ
        """
        # 全エントリを読み込み
        all_entries = self._load_all_entries()
        
        # 該当エントリを除外
        key = entry.get('key')
        timestamp = entry.get('timestamp')
        
        filtered_entries = [
            e for e in all_entries
            if not (e.get('key') == key and e.get('timestamp') == timestamp)
        ]
        
        # ファイルに書き戻し
        with open(self.scratchpad_path, 'w', encoding='utf-8') as f:
            for e in filtered_entries:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')


if __name__ == "__main__":
    # テスト
    promoter = MRLMemoryPromoter()
    
    # 昇格チェック
    promoted = promoter.check_and_promote()
    print(f"昇格したエントリ: {len(promoted)}件")
