#!/usr/bin/env python3
"""
MRL Memory Priority Resolver
RAG（長期）とFWPKM（短期）の競合解決
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Quarantine統合
try:
    from mrl_memory_quarantine import MemoryQuarantine
    QUARANTINE_AVAILABLE = True
except ImportError:
    QUARANTINE_AVAILABLE = False

# 統一モジュールのインポート
try:
    from unified_logging import get_service_logger
    logger = get_service_logger("mrl-memory-priority-resolver")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MemoryPriorityResolver:
    """
    RAG（長期）とFWPKM（短期）の競合解決
    
    優先度ルール:
    - 「このセッション内の事実」→ FWPKM優先
    - 「一般知識/過去の安定情報」→ RAG優先
    - 矛盾したら:
      * 短期＝低確度ならRAG採用
      * 短期＝高確度＋直近根拠ありなら短期採用
    """
    
    def __init__(self):
        """初期化"""
        # セッション管理（直近N時間の情報をFWPKMとして扱う）
        self.session_window_hours = 24  # セッションウィンドウ（時間）
        
        # 信頼度マッピング
        self.confidence_map = {
            "low": 0.3,
            "med": 0.6,
            "high": 0.9
        }
        
        # ソース重み（根拠の強さ）
        self.source_weights = {
            "user_input": 1.0,  # ユーザー直入力
            "external_document": 0.8,  # 外部文書
            "rag": 0.6,  # RAG（長期記憶）
            "fwpkm": 0.7,  # FWPKM（短期記憶）
            "unknown": 0.5
        }
        
        # Quarantine（オプション）
        self.quarantine = None
        if QUARANTINE_AVAILABLE:
            try:
                self.quarantine = MemoryQuarantine()
            except Exception as e:
                logger.warning(f"Quarantine初期化エラー: {e}")
        
        logger.info("✅ Memory Priority Resolver初期化完了")
    
    def resolve_conflict(
        self,
        rag_results: List[Dict[str, Any]],
        fwpkm_results: List[Dict[str, Any]],
        query: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        競合を解決して統合結果を返す
        
        Args:
            rag_results: RAG（長期記憶）の検索結果
            fwpkm_results: FWPKM（短期記憶）の検索結果
            query: 検索クエリ
            session_id: セッションID
        
        Returns:
            統合結果
        """
        # 1. 重複チェック（同じキー/内容のもの）
        merged_results = []
        seen_keys = set()
        
        # 2. FWPKMを優先（セッション内の情報）
        # まず、RAGとFWPKMの最新タイムスタンプを取得
        latest_rag_time = None
        if rag_results:
            try:
                rag_times = [
                    datetime.fromisoformat(r.get('timestamp', ''))
                    for r in rag_results
                    if r.get('timestamp')
                ]
                if rag_times:
                    latest_rag_time = max(rag_times)
            except Exception:
                pass
        
        for fwpkm_entry in fwpkm_results:
            key = fwpkm_entry.get('key', '')
            value = fwpkm_entry.get('value', '')
            
            # セッション内かチェック（現在時刻との比較）
            is_recent_absolute = self._is_recent(fwpkm_entry)
            
            # 相対的な新旧判定（RAGより新しいか）
            is_recent_relative = False
            if latest_rag_time:
                try:
                    fwpkm_time = datetime.fromisoformat(fwpkm_entry.get('timestamp', ''))
                    if fwpkm_time > latest_rag_time:
                        is_recent_relative = True
                except Exception:
                    pass
            
            # どちらかの条件を満たせば「最近」とみなす
            is_recent = is_recent_absolute or is_recent_relative
            
            confidence = self.confidence_map.get(
                fwpkm_entry.get('confidence', 'low'), 
                0.3
            )
            
            # 優先スコアを計算（recency + confidence + source_weight）
            source_weight = self.source_weights.get("fwpkm", 0.7)
            recency_score = 1.0 if is_recent else 0.3
            priority_score = recency_score + confidence + source_weight
            
            # 高確度＋直近なら優先
            if is_recent and confidence >= 0.6:
                merged_results.append({
                    **fwpkm_entry,
                    "source": "fwpkm",
                    "priority": "high",
                    "priority_score": priority_score,
                    "reason": "recent_high_confidence"
                })
                seen_keys.add(key)
        
        # 3. RAGを追加（重複チェック：キーが同じでも値が異なる場合は追加して矛盾検出に備える）
        for rag_entry in rag_results:
            rag_key = rag_entry.get('key', '')
            rag_value = rag_entry.get('value', '').lower()
            
            # 既存のエントリとキーが同じかチェック
            is_duplicate = False
            for merged in merged_results:
                merged_key = merged.get('key', '')
                merged_value = merged.get('value', '').lower()
                
                # キーが同じで値も同じ場合は重複
                if rag_key == merged_key and rag_value == merged_value:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # キーが同じでも値が異なる場合は追加（矛盾検出のため）
                merged_results.append({
                    **rag_entry,
                    "source": "rag",
                    "priority": "medium",
                    "reason": "long_term_stable"
                })
        
        # 4. ソート（優先スコア順、なければ優先度順）
        for result in merged_results:
            if "priority_score" not in result:
                # 優先スコアを計算
                source = result.get("source", "unknown")
                source_weight = self.source_weights.get(source, 0.5)
                confidence = self.confidence_map.get(result.get("confidence", "low"), 0.3)
                recency = 1.0 if self._is_recent(result) else 0.3
                result["priority_score"] = recency + confidence + source_weight
        
        merged_results.sort(
            key=lambda x: (
                x.get("priority_score", 0),
                {"high": 2, "medium": 1, "low": 0}.get(x.get("priority", "low"), 0),
                self.confidence_map.get(x.get("confidence", "low"), 0)
            ),
            reverse=True
        )
        
        # 5. 矛盾検出と隔離
        conflicts = self._detect_conflicts(merged_results)
        
        # 矛盾がある場合は勝者決定＋敗者隔離
        active_results = []
        quarantined_results = []
        
        if conflicts and self.quarantine:
            # 矛盾ペアを解決
            conflict_keys = set()
            for conflict in conflicts:
                key = conflict["entry1"]["key"]
                if key not in conflict_keys:
                    conflict_keys.add(key)
                    
                    # 該当するエントリを探す
                    entry1 = next((r for r in merged_results if r.get("key") == key and r.get("source") == conflict["entry1"]["source"]), None)
                    entry2 = next((r for r in merged_results if r.get("key") == key and r.get("source") == conflict["entry2"]["source"]), None)
                    
                    if entry1 and entry2:
                        # 勝者決定＋敗者隔離
                        resolution = self.quarantine.resolve_conflict_with_quarantine(entry1, entry2)
                        active_results.append(resolution["active"])
                        quarantined_results.append(resolution["quarantined"])
            
            # 矛盾していないエントリを追加
            for result in merged_results:
                if result.get("key") not in conflict_keys:
                    active_results.append(result)
        else:
            # Quarantineがない場合は従来通り
            active_results = merged_results
        
        result = {
            "results": active_results,
            "conflicts": conflicts,
            "quarantined": quarantined_results,
            "resolved_count": len(active_results),
            "rag_count": len(rag_results),
            "fwpkm_count": len(fwpkm_results)
        }
        
        if conflicts:
            logger.warning(f"矛盾検出: {len(conflicts)}件, 隔離: {len(quarantined_results)}件")
        
        return result
    
    def _is_recent(self, entry: Dict[str, Any]) -> bool:
        """エントリが最近のものかチェック"""
        timestamp = entry.get('timestamp', '')
        if not timestamp:
            return False
        
        try:
            entry_time = datetime.fromisoformat(timestamp)
            # 相対的な新旧判定：より新しいタイムスタンプを「最近」とみなす
            # テスト用：現在時刻との比較ではなく、他のエントリとの相対比較
            # 実運用では現在時刻との比較を使用
            now = datetime.now()
            age_hours = (now - entry_time).total_seconds() / 3600
            
            # 過去の日付でも、セッションウィンドウ内なら「最近」とみなす
            # （テスト用：過去の日付でも24時間以内の差があればOK）
            if age_hours < 0:
                # 未来の日付は無視
                return False
            
            return age_hours <= self.session_window_hours
        except Exception:
            return False
    
    def _is_similar(
        self,
        entry1: Dict[str, Any],
        entry2: Dict[str, Any]
    ) -> bool:
        """2つのエントリが似ているかチェック"""
        key1 = entry1.get('key', '').lower()
        key2 = entry2.get('key', '').lower()
        value1 = entry1.get('value', '').lower()
        value2 = entry2.get('value', '').lower()
        
        # キーが同じ
        if key1 == key2:
            return True
        
        # 値が部分的に一致
        if value1 in value2 or value2 in value1:
            return True
        
        return False
    
    def _detect_conflicts(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """矛盾を検出"""
        conflicts = []
        
        for i, result1 in enumerate(results):
            for j, result2 in enumerate(results[i+1:], start=i+1):
                # キーが同じ場合のみ矛盾チェック
                key1 = result1.get('key', '').lower()
                key2 = result2.get('key', '').lower()
                
                if key1 == key2:
                    # 値が矛盾しているかチェック
                    value1 = result1.get('value', '').lower()
                    value2 = result2.get('value', '').lower()
                    
                    # 値が異なる場合
                    if value1 != value2:
                        # 数値が含まれる場合は数値部分を比較
                        import re
                        nums1 = re.findall(r'\d+', value1)
                        nums2 = re.findall(r'\d+', value2)
                        
                        # 数値が異なる場合は矛盾
                        if nums1 and nums2 and nums1 != nums2:
                            conflicts.append({
                                "entry1": {
                                    "source": result1.get("source"),
                                    "key": result1.get("key"),
                                    "value": result1.get("value")[:50],
                                    "confidence": result1.get("confidence")
                                },
                                "entry2": {
                                    "source": result2.get("source"),
                                    "key": result2.get("key"),
                                    "value": result2.get("value")[:50],
                                    "confidence": result2.get("confidence")
                                }
                            })
                        # 数値がない場合でも、完全に異なる値なら矛盾
                        elif not nums1 and not nums2:
                            # 部分一致でない場合のみ矛盾とみなす
                            if value1 not in value2 and value2 not in value1 and len(value1) >= 3 and len(value2) >= 3:
                                conflicts.append({
                                    "entry1": {
                                        "source": result1.get("source"),
                                        "key": result1.get("key"),
                                        "value": result1.get("value")[:50],
                                        "confidence": result1.get("confidence")
                                    },
                                    "entry2": {
                                        "source": result2.get("source"),
                                        "key": result2.get("key"),
                                        "value": result2.get("value")[:50],
                                        "confidence": result2.get("confidence")
                                    }
                                })
        
        return conflicts
    
    def get_context_for_llm(
        self,
        resolved_result: Dict[str, Any],
        include_conflicts: bool = False
    ) -> str:
        """
        LLMに渡すためのコンテキストを構築
        
        Args:
            resolved_result: 解決済み結果
            include_conflicts: 矛盾情報を含めるか
        
        Returns:
            コンテキスト文字列
        """
        results = resolved_result.get("results", [])
        conflicts = resolved_result.get("conflicts", [])
        
        context_parts = ["## 関連メモリ（統合結果）"]
        
        # 結果を追加
        for i, result in enumerate(results[:5], 1):
            source = result.get("source", "unknown")
            key = result.get("key", "unknown")
            value = result.get("value", "")[:100]
            confidence = result.get("confidence", "low")
            
            context_parts.append(
                f"{i}. [{source}] [{confidence}] {key}: {value}"
            )
        
        # 矛盾情報を追加（オプション）
        if include_conflicts and conflicts:
            context_parts.append("\n## ⚠️ 矛盾検出")
            for conflict in conflicts[:3]:
                context_parts.append(
                    f"- {conflict['entry1']['source']} vs {conflict['entry2']['source']}"
                )
        
        return "\n".join(context_parts)
