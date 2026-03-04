#!/usr/bin/env python3
"""
MRL Memory Integration Test
RAG × FWPKM が喧嘩しないか
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from mrl_memory_priority_resolver import MemoryPriorityResolver


class TestMRLMemoryIntegration:
    """統合テスト"""
    
    @pytest.fixture
    def priority_resolver(self):
        """優先度解決器"""
        return MemoryPriorityResolver()
    
    def test_rag_fwpkm_conflict_resolution(self, priority_resolver):
        """
        統合テスト：RAG × FWPKM が喧嘩しないか
        
        典型的な事故:
        - RAGの古い知識（長期）が強すぎて、短期の正しい情報を上書きする
        - FWPKMが直近のノイズを拾って、RAGの正しい知識を壊す
        """
        # RAGの古い知識（長期）
        rag_results = [
            {
                "key": "project_manager",
                "value": "佐藤花子",  # 古い情報
                "confidence": "high",
                "timestamp": "2024-01-01T00:00:00"
            }
        ]
        
        # FWPKMの新しい知識（短期）
        fwpkm_results = [
            {
                "key": "project_manager",
                "value": "田中太郎",  # 新しい情報（正しい）
                "confidence": "high",
                "timestamp": "2024-01-02T00:00:00"  # 最近
            }
        ]
        
        # 競合解決
        resolved = priority_resolver.resolve_conflict(
            rag_results=rag_results,
            fwpkm_results=fwpkm_results,
            query="project_manager"
        )
        
        # 検証：FWPKMが優先されるか（高確度＋直近）
        assert len(resolved["results"]) > 0, "結果がありません"
        
        # 最初の結果がFWPKM由来か
        first_result = resolved["results"][0]
        assert first_result["source"] == "fwpkm", "FWPKMが優先されていません"
        assert "田中" in first_result["value"], "正しい情報が採用されていません"
    
    def test_rag_priority_for_low_confidence_fwpkm(self, priority_resolver):
        """
        統合テスト：短期が低確度ならRAG優先
        """
        # RAGの安定情報（長期）
        rag_results = [
            {
                "key": "api_endpoint",
                "value": "https://api.example.com",
                "confidence": "high",
                "timestamp": "2024-01-01T00:00:00"
            }
        ]
        
        # FWPKMの低確度情報（短期）
        fwpkm_results = [
            {
                "key": "api_endpoint",
                "value": "https://wrong.example.com",  # 誤情報
                "confidence": "low",  # 低確度
                "timestamp": "2024-01-02T00:00:00"
            }
        ]
        
        # 競合解決
        resolved = priority_resolver.resolve_conflict(
            rag_results=rag_results,
            fwpkm_results=fwpkm_results,
            query="api_endpoint"
        )
        
        # 検証：RAGが優先されるか（短期が低確度）
        assert len(resolved["results"]) > 0, "結果がありません"
        
        # RAGが含まれているか
        rag_found = any(r["source"] == "rag" for r in resolved["results"])
        assert rag_found, "RAGが優先されていません"
    
    def test_conflict_detection(self, priority_resolver):
        """
        統合テスト：矛盾検出
        """
        # 矛盾する情報
        rag_results = [
            {
                "key": "budget",
                "value": "500万円",
                "confidence": "high",
                "timestamp": "2024-01-01T00:00:00"
            }
        ]
        
        fwpkm_results = [
            {
                "key": "budget",
                "value": "1000万円",  # 矛盾
                "confidence": "high",
                "timestamp": "2024-01-02T00:00:00"
            }
        ]
        
        # 競合解決
        resolved = priority_resolver.resolve_conflict(
            rag_results=rag_results,
            fwpkm_results=fwpkm_results,
            query="budget"
        )
        
        # 検証：矛盾が検出されているか
        assert len(resolved["conflicts"]) > 0, "矛盾が検出されていません"


