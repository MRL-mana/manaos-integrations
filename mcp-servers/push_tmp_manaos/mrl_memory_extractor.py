#!/usr/bin/env python3
"""
MRL Memory Extractor
推論中に短期メモリを更新する抽出器
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import hashlib
import threading
import os

# 統一モジュールのインポート
try:
    from unified_logging import get_service_logger
    logger = get_service_logger("mrl-memory-extractor")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """メモリエントリ"""
    timestamp: str
    source: str
    key: str
    value: str
    confidence: str  # "high", "med", "low"
    ttl: str  # "1h", "1d", "7d"
    access_count: int = 0
    last_accessed: Optional[str] = None


class MRLMemoryExtractor:
    """
    推論中に短期メモリを更新する抽出器
    
    3レイヤ構造:
    1. Scratchpad（超短期：数分〜数時間）
    2. Working Memory（短期：数日）
    3. Long-term（長期：Obsidian/Notion/GitHub）
    """
    
    def __init__(self, memory_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            memory_dir: メモリディレクトリ（Noneの場合はデフォルト）
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
        self.working_memory_path = self.memory_dir / "working_memory.md"
        
        # パターン定義
        self.patterns = {
            "proper_nouns": [
                r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*",  # 固有名詞（英語）
                r"[ぁ-んァ-ヶー一-龠]{2,}",  # 固有名詞（日本語）
            ],
            "numbers": [
                r"\d+\.\d+",  # 小数
                r"\d+",  # 整数
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",  # IPアドレス
                r":\d{1,5}",  # ポート番号
            ],
            "decisions": [
                r"決定[した|しました|する]",
                r"決めた",
                r"確定[した|しました|する]",
                r"採用[した|しました|する]",
            ],
            "unsolved": [
                r"わからない",
                r"不明",
                r"エラー",
                r"失敗",
                r"未解決",
            ],
            "todos": [
                r"TODO",
                r"やる",
                r"次[は|に]",
                r"後で",
            ],
        }
        
        self._scratchpad_lock = threading.Lock()
        logger.info(f"✅ MRL Memory Extractor初期化完了: {self.memory_dir}")
    
    def extract(self, text: str, source: str = "unknown") -> List[MemoryEntry]:
        """
        テキストから情報を抽出
        
        Args:
            text: 入力テキスト
            source: ソース（どの入力から）
        
        Returns:
            抽出されたメモリエントリのリスト
        """
        entries = []
        timestamp = datetime.now().isoformat()
        
        # 1. 固有名詞を抽出
        proper_nouns = self._extract_patterns(text, self.patterns["proper_nouns"])
        for noun in proper_nouns:
            if len(noun) > 1:  # 1文字は除外
                entries.append(MemoryEntry(
                    timestamp=timestamp,
                    source=source,
                    key=f"proper_noun:{noun}",
                    value=noun,
                    confidence="med",
                    ttl="1d"
                ))
        
        # 2. 数値を抽出
        numbers = self._extract_patterns(text, self.patterns["numbers"])
        for number in numbers:
            entries.append(MemoryEntry(
                timestamp=timestamp,
                source=source,
                key=f"number:{number}",
                value=number,
                confidence="high",
                ttl="1d"
            ))
        
        # 3. 決定事項を抽出
        decisions = self._extract_patterns(text, self.patterns["decisions"])
        if decisions:
            # 決定事項の前後の文脈を取得
            context = self._extract_context(text, decisions[0], window=50)
            entries.append(MemoryEntry(
                timestamp=timestamp,
                source=source,
                key="decision",
                value=context,
                confidence="high",
                ttl="7d"
            ))
        
        # 4. 未解決事項を抽出
        unsolved = self._extract_patterns(text, self.patterns["unsolved"])
        if unsolved:
            context = self._extract_context(text, unsolved[0], window=50)
            entries.append(MemoryEntry(
                timestamp=timestamp,
                source=source,
                key="unsolved",
                value=context,
                confidence="med",
                ttl="1d"
            ))
        
        # 5. TODOを抽出
        todos = self._extract_patterns(text, self.patterns["todos"])
        if todos:
            context = self._extract_context(text, todos[0], window=50)
            entries.append(MemoryEntry(
                timestamp=timestamp,
                source=source,
                key="todo",
                value=context,
                confidence="high",
                ttl="1d"
            ))

        # 6. raw テキスト（検索性の担保）
        # 抽出型だと「入力全文」で検索できないので、短いTTLの raw を1件入れておく。
        raw = str(text or "").strip()
        if raw:
            h = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:12]
            entries.append(
                MemoryEntry(
                    timestamp=timestamp,
                    source=source,
                    key=f"raw:{h}",
                    value=(raw[:8000] + ("…" if len(raw) > 8000 else "")),
                    confidence="low",
                    ttl="1d",
                )
            )
        
        # 重複チェック（同じキーと値の組み合わせは除外）
        entries = self._deduplicate(entries)
        
        logger.info(f"抽出完了: {len(entries)}件のエントリ")
        return entries
    
    def _extract_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """パターンにマッチする文字列を抽出"""
        matches = []
        for pattern in patterns:
            found = re.findall(pattern, text)
            matches.extend(found)
        return list(set(matches))  # 重複除去
    
    def _extract_context(self, text: str, keyword: str, window: int = 50) -> str:
        """キーワードの前後の文脈を抽出"""
        index = text.find(keyword)
        if index == -1:
            return keyword
        
        start = max(0, index - window)
        end = min(len(text), index + len(keyword) + window)
        context = text[start:end].strip()
        
        return context
    
    def _deduplicate(self, entries: List[MemoryEntry]) -> List[MemoryEntry]:
        """重複を除去"""
        seen = set()
        unique_entries = []
        
        for entry in entries:
            # キーと値の組み合わせで重複チェック
            key_value = f"{entry.key}:{entry.value}"
            if key_value not in seen:
                seen.add(key_value)
                unique_entries.append(entry)
        
        return unique_entries
    
    def append_to_scratchpad(self, entries: List[MemoryEntry]):
        """
        Scratchpadに追記（スレッドセーフ）
        
        Args:
            entries: メモリエントリのリスト
        """
        with self._scratchpad_lock:
            with open(self.scratchpad_path, 'a', encoding='utf-8') as f:
                for entry in entries:
                    f.write(json.dumps(asdict(entry), ensure_ascii=False) + '\n')
        
        logger.info(f"Scratchpadに{len(entries)}件を追記")
    
    def process_text(self, text: str, source: str = "unknown") -> List[MemoryEntry]:
        """
        テキストを処理してScratchpadに追記
        
        Args:
            text: 入力テキスト
            source: ソース
        
        Returns:
            抽出されたエントリ
        """
        # 抽出
        entries = self.extract(text, source)
        
        # Scratchpadに追記
        if entries:
            self.append_to_scratchpad(entries)
        
        return entries
    
    def get_recent_entries(self, hours: int = 24, limit: int = 100) -> List[Dict[str, Any]]:
        """
        最近のエントリを取得
        
        Args:
            hours: 何時間前まで
            limit: 最大取得数
        
        Returns:
            エントリのリスト
        """
        if not self.scratchpad_path.exists():
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        entries = []
        
        with self._scratchpad_lock:
            with open(self.scratchpad_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry_dict = json.loads(line.strip())
                        entry_time = datetime.fromisoformat(entry_dict['timestamp'])
                        
                        if entry_time >= cutoff_time:
                            entries.append(entry_dict)
                            
                            if len(entries) >= limit:
                                break
                    except Exception as e:
                        logger.warning(f"エントリ読み込みエラー: {e}")
                        continue
        
        # 新しい順にソート
        entries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return entries


class MRLMemoryRetriever:
    """
    メモリから情報を検索するリトリーバ
    """
    
    def __init__(self, memory_dir: Optional[Path] = None):
        """
        初期化
        
        Args:
            memory_dir: メモリディレクトリ
        """
        if memory_dir is None:
            env_dir = str(os.getenv("MRL_MEMORY_DIR", "") or "").strip()
            if env_dir:
                memory_dir = Path(env_dir)
            else:
                memory_dir = Path(__file__).parent / "mrl_memory"
        
        self.memory_dir = Path(memory_dir)
        self.scratchpad_path = self.memory_dir / "scratchpad.jsonl"
        self.working_memory_path = self.memory_dir / "working_memory.md"
        
        # 読み取り時のロック
        self._scratchpad_lock = threading.Lock()
    
    def retrieve(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        クエリに関連するメモリを取得
        
        Args:
            query: 検索クエリ
            limit: 最大取得数
        
        Returns:
            関連エントリのリスト
        """
        if not self.scratchpad_path.exists():
            return []
        
        query_lower = query.lower()
        matches = []
        
        # Scratchpadから検索（スレッドセーフ）
        with self._scratchpad_lock:
            with open(self.scratchpad_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry_dict = json.loads(line.strip())
                        
                        # キーまたは値にクエリが含まれるかチェック
                        key = entry_dict.get('key', '').lower()
                        value = entry_dict.get('value', '').lower()
                        
                        if query_lower in key or query_lower in value:
                            # 関連度スコアを計算（簡易実装）
                            score = 0
                            if query_lower in key:
                                score += 2
                            if query_lower in value:
                                score += 1
                            
                            entry_dict['relevance_score'] = score
                            matches.append(entry_dict)
                    except Exception as e:
                        logger.warning(f"エントリ読み込みエラー: {e}")
                        continue
        
        # 関連度でソート
        matches.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return matches[:limit]
    
    def get_context_for_llm(self, query: str, limit: int = 5) -> str:
        """
        LLMに渡すためのコンテキストを構築
        
        Args:
            query: 検索クエリ
            limit: 最大取得数
        
        Returns:
            コンテキスト文字列
        """
        entries = self.retrieve(query, limit)
        
        if not entries:
            return ""
        
        context_parts = ["## 関連メモリ"]
        for i, entry in enumerate(entries, 1):
            context_parts.append(
                f"{i}. [{entry.get('key', 'unknown')}] {entry.get('value', '')[:100]}"
            )
        
        return "\n".join(context_parts)


if __name__ == "__main__":
    # テスト
    extractor = MRLMemoryExtractor()
    
    # サンプルテキスト
    sample_text = """
    今日の会議で、プロジェクトXの開始日を2024年2月1日に決定しました。
    API_KEYは環境変数に設定する必要があります。
    ポート番号は8080を使用します。
    エラーが発生したので、後で調査が必要です。
    """
    
    # 抽出
    entries = extractor.process_text(sample_text, source="test")
    
    print(f"抽出されたエントリ: {len(entries)}件")
    for entry in entries:
        print(f"  - {entry.key}: {entry.value[:50]}")
    
    # 検索テスト
    retriever = MRLMemoryRetriever()
    results = retriever.retrieve("決定", limit=5)
    print(f"\n検索結果: {len(results)}件")
    for result in results:
        print(f"  - {result.get('key')}: {result.get('value')[:50]}")  # type: ignore[index]
