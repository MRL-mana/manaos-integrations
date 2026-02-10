#!/usr/bin/env python3
"""
MRL Memory System
統合システム（抽出→追記→参照→昇格）
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from mrl_memory_extractor import MRLMemoryExtractor, MRLMemoryRetriever
from mrl_memory_rehearsal import MRLMemoryRehearsal
from mrl_memory_promoter import MRLMemoryPromoter
from mrl_memory_kill_switch import KillSwitch
from mrl_memory_quarantine import MemoryQuarantine
from mrl_memory_ttl_manager import TTLManager

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MRLMemorySystem:
    """
    MRL Memory System（統合）
    
    3レイヤ構造:
    1. Scratchpad（超短期：数分〜数時間）
    2. Working Memory（短期：数日）
    3. Long-term（長期：Obsidian/Notion/GitHub）
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
            memory_dir = Path(__file__).parent / "mrl_memory"
        
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # コンポーネント初期化
        self.extractor = MRLMemoryExtractor(memory_dir)
        self.retriever = MRLMemoryRetriever(memory_dir)
        self.rehearsal = MRLMemoryRehearsal(memory_dir)
        self.promoter = MRLMemoryPromoter(memory_dir, obsidian_vault)
        
        # Kill Switch
        self.kill_switch = KillSwitch()
        
        # Quarantine
        self.quarantine = MemoryQuarantine(memory_dir)
        
        # TTL Manager
        self.ttl_manager = TTLManager(memory_dir)
        
        logger.info(f"✅ MRL Memory System初期化完了: {self.memory_dir}")
    
    def process(
        self,
        text: str,
        source: str = "unknown",
        enable_rehearsal: bool = True,
        enable_promotion: bool = False
    ) -> Dict[str, Any]:
        """
        テキストを処理（抽出→追記→復習効果）
        
        Args:
            text: 入力テキスト
            source: ソース
            enable_rehearsal: 復習効果を有効にするか
            enable_promotion: 昇格チェックを有効にするか
        
        Returns:
            処理結果
        """
        # Kill Switchチェック
        self.kill_switch.check_and_raise(operation="write")
        
        # 復習効果を適用
        if enable_rehearsal:
            rehearsal_result = self.rehearsal.rehearse(text, source)
        else:
            # 通常の抽出
            entries = self.extractor.process_text(text, source)
            rehearsal_result = {
                "new_entries": len(entries),
                "updated_entries": 0,
                "total_processed": len(entries)
            }
        
        # 昇格チェック（オプション）
        promoted = []
        if enable_promotion:
            promoted = self.promoter.check_and_promote()
        
        result = {
            "rehearsal": rehearsal_result,
            "promoted": len(promoted),
            "timestamp": datetime.now().isoformat(),
            "kill_switch_status": self.kill_switch.get_status()
        }
        
        return result
    
    def retrieve(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        メモリから検索
        
        Args:
            query: 検索クエリ
            limit: 最大取得数
        
        Returns:
            検索結果
        """
        return self.retriever.retrieve(query, limit)
    
    def get_context_for_llm(self, query: str, limit: int = 5) -> str:
        """
        LLMに渡すためのコンテキストを構築
        
        Args:
            query: 検索クエリ
            limit: 最大取得数
        
        Returns:
            コンテキスト文字列
        """
        return self.retriever.get_context_for_llm(query, limit)
    
    def update_working_memory(self):
        """
        Working Memoryを更新
        
        Scratchpadから重要な情報を要約してWorking Memoryに反映
        """
        working_memory_path = self.memory_dir / "working_memory.md"
        
        # 最近のエントリを取得
        recent_entries = self.extractor.get_recent_entries(hours=24, limit=20)
        
        # 要約を生成
        summary = self._generate_summary(recent_entries)
        
        # Working Memoryを更新
        with open(working_memory_path, 'w', encoding='utf-8') as f:
            f.write(summary)
        
        logger.info("Working Memoryを更新しました")
    
    def _generate_summary(self, entries: List[Dict[str, Any]]) -> str:
        """
        Working Memoryの要約を生成
        
        Args:
            entries: エントリのリスト
        
        Returns:
            Markdown形式の要約
        """
        lines = [
            "# Working Memory",
            "",
            f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 今日の作業要点",
            ""
        ]
        
        # 決定事項
        decisions = [e for e in entries if e.get('key') == 'decision']
        if decisions:
            lines.append("### 決定事項")
            for d in decisions[:5]:
                lines.append(f"- {d.get('value', '')[:100]}")
            lines.append("")
        
        # TODOエントリをリスト化
        todos = [e for e in entries if e.get('key') == 'todo']
        if todos:
            lines.append("### TODO")
            for t in todos[:5]:
                lines.append(f"- [ ] {t.get('value', '')[:100]}")
            lines.append("")
        
        # 未確定事項
        unsolved = [e for e in entries if e.get('key') == 'unsolved']
        if unsolved:
            lines.append("## 未確定事項")
            for u in unsolved[:5]:
                lines.append(f"- {u.get('value', '')[:100]}")
            lines.append("")
        
        # 次アクション
        lines.append("## 次アクション")
        lines.append("")
        lines.append("- メモリシステムの動作確認")
        lines.append("")
        
        lines.append("## メモ")
        lines.append("")
        lines.append("このファイルは自動的に更新されます。")
        
        return "\n".join(lines)
    
    def cleanup_expired_entries(self) -> int:
        """
        期限切れエントリを削除
        
        Returns:
            削除されたエントリ数
        """
        return self.ttl_manager.cleanup_expired_entries()
    
    def cleanup_session(self, session_id: str) -> int:
        """
        セッション終了で削除
        
        Args:
            session_id: セッションID
        
        Returns:
            削除されたエントリ数
        """
        return self.ttl_manager.cleanup_session(session_id)


if __name__ == "__main__":
    # テスト
    system = MRLMemorySystem()
    
    # 処理
    text = """
    今日の会議で、プロジェクトXの開始日を2024年2月1日に決定しました。
    API_KEYは環境変数に設定する必要があります。
    ポート番号は8080を使用します。
    """
    
    result = system.process(text, source="test", enable_rehearsal=True)
    print(f"処理結果: {result}")
    
    # 検索
    results = system.retrieve("決定", limit=5)
    print(f"\n検索結果: {len(results)}件")
    
    # LLMコンテキスト
    context = system.get_context_for_llm("決定", limit=3)
    print(f"\nLLMコンテキスト:\n{context}")
    
    # Working Memory更新
    system.update_working_memory()
