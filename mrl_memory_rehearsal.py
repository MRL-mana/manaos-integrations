#!/usr/bin/env python3
"""
MRL Memory Rehearsal
復習効果の実装（同じテーマでメモリを強化）
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict

from mrl_memory_extractor import MRLMemoryExtractor, MemoryEntry

# 統一モジュールのインポート
try:
    from unified_logging import get_service_logger
    logger = get_service_logger("mrl-memory-rehearsal")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MRLMemoryRehearsal:
    """
    復習効果の実装
    
    同じテーマが出たら：
    - 既存メモリに追記 or 強化（confidence↑）
    - 重複はマージ
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
        self.extractor = MRLMemoryExtractor(memory_dir)
    
    def rehearse(self, text: str, source: str = "unknown") -> Dict[str, Any]:
        """
        復習効果を適用
        
        Args:
            text: 入力テキスト
            source: ソース
        
        Returns:
            復習結果
        """
        # 新しいエントリを抽出
        new_entries = self.extractor.extract(text, source)
        
        # 既存エントリを読み込み
        existing_entries = self._load_all_entries()
        
        # 重複チェックと強化
        updated_count = 0
        new_count = 0
        
        for new_entry in new_entries:
            # 既存エントリとマッチング
            matched = self._find_match(new_entry, existing_entries)
            
            if matched:
                # 既存エントリを強化
                self._enhance_entry(matched, new_entry)
                updated_count += 1
            else:
                # 新しいエントリとして追加
                self.extractor.append_to_scratchpad([new_entry])
                new_count += 1
        
        result = {
            "new_entries": new_count,
            "updated_entries": updated_count,
            "total_processed": len(new_entries)
        }
        
        logger.info(f"復習効果適用: 新規{new_count}件, 更新{updated_count}件")
        return result
    
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
    
    def _find_match(
        self,
        new_entry: MemoryEntry,
        existing_entries: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        既存エントリとマッチング
        
        Args:
            new_entry: 新しいエントリ
            existing_entries: 既存エントリのリスト
        
        Returns:
            マッチした既存エントリ（なければNone）
        """
        # キーが同じものを探す
        for existing in existing_entries:
            if existing.get('key') == new_entry.key:
                # 値も似ているかチェック（簡易実装）
                existing_value = existing.get('value', '').lower()
                new_value = new_entry.value.lower()
                
                # 部分一致または類似度が高い
                if new_value in existing_value or existing_value in new_value:
                    return existing
        
        return None
    
    def _enhance_entry(
        self,
        existing: Dict[str, Any],
        new_entry: MemoryEntry
    ):
        """
        既存エントリを強化
        
        Args:
            existing: 既存エントリ
            new_entry: 新しいエントリ
        """
        # confidenceを上げる
        confidence_map = {"low": 0, "med": 1, "high": 2}
        existing_conf = confidence_map.get(existing.get('confidence', 'low'), 0)
        new_conf = confidence_map.get(new_entry.confidence, 0)
        
        if new_conf > existing_conf:
            reverse_map = {0: "low", 1: "med", 2: "high"}
            existing['confidence'] = reverse_map[new_conf]
        
        # アクセス回数を増やす
        existing['access_count'] = existing.get('access_count', 0) + 1
        existing['last_accessed'] = datetime.now().isoformat()
        
        # 値に新しい情報を追加（重複しない場合）
        existing_value = existing.get('value', '')
        if new_entry.value not in existing_value:
            existing['value'] = f"{existing_value} | {new_entry.value}"
        
        # ファイルを更新（簡易実装：全件書き直し）
        self._update_scratchpad_entry(existing)
    
    def _update_scratchpad_entry(self, entry: Dict[str, Any]):
        """
        Scratchpadのエントリを更新
        
        Note: 簡易実装。本番ではインデックスを使うべき
        """
        # 全エントリを読み込み
        all_entries = self._load_all_entries()
        
        # 該当エントリを更新
        key = entry.get('key')
        for i, e in enumerate(all_entries):
            if e.get('key') == key:
                all_entries[i] = entry
                break
        
        # ファイルに書き戻し
        with open(self.scratchpad_path, 'w', encoding='utf-8') as f:
            for e in all_entries:
                f.write(json.dumps(e, ensure_ascii=False) + '\n')


if __name__ == "__main__":
    # テスト
    rehearsal = MRLMemoryRehearsal()
    
    # 1回目
    text1 = "プロジェクトXの開始日は2024年2月1日です。"
    result1 = rehearsal.rehearse(text1, source="test1")
    print(f"1回目: {result1}")
    
    # 2回目（復習）
    text2 = "プロジェクトXは2024年2月1日に開始されます。"
    result2 = rehearsal.rehearse(text2, source="test2")
    print(f"2回目: {result2}")
