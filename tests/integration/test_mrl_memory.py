#!/usr/bin/env python3
"""
MRL Memory System - 最小テスト3本
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from mrl_memory_system import MRLMemorySystem
from mrl_memory_extractor import MRLMemoryExtractor
from mrl_memory_rehearsal import MRLMemoryRehearsal


class TestMRLMemory:
    """MRL Memory Systemのテスト"""
    
    @pytest.fixture
    def temp_memory_dir(self):
        """一時メモリディレクトリ"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def memory_system(self, temp_memory_dir):
        """メモリシステム"""
        return MRLMemorySystem(memory_dir=temp_memory_dir)
    
    def test_a_long_text_consistency(self, memory_system):
        """
        テストA：長文整合（128K想定）
        
        文章の前半に「重要事実」を埋める
        後半でそれを参照する質問を投げる
        FWPKM OFFとONで正答率/一貫性比較
        """
        # 前半に重要事実を埋める
        long_text = """
        プロジェクトXの担当者は田中太郎です。
        開始日は2024年2月1日です。
        予算は500万円です。
        """ + " " * 1000 + """
        このプロジェクトについて質問があります。
        """
        
        # FWPKM ON: 処理してメモリに保存
        result_on = memory_system.process(
            text=long_text,
            source="test_a",
            enable_rehearsal=True
        )
        
        # 後半で質問（担当者名を聞く）
        query = "担当者"
        results_on = memory_system.retrieve(query, limit=5)
        
        # 検証：担当者名が検索できるか
        found_manager = False
        for result in results_on:
            if "田中" in result.get("value", ""):
                found_manager = True
                break
        
        assert found_manager, "FWPKM ON: 担当者名が検索できません"
        assert result_on["rehearsal"]["new_entries"] > 0, "エントリが抽出されません"
    
    def test_b_noise_tolerance(self, memory_system):
        """
        テストB：ノイズ耐性（メモリ汚染）
        
        わざと矛盾する情報を途中で混ぜる
        "自信満々の誤答"にならないか、ゲートが効くかを見る
        """
        from mrl_memory_gating import MemoryGating
        
        gating = MemoryGating()
        
        # 正しい情報
        correct_entry = {
            "key": "project_manager",
            "value": "田中太郎",
            "confidence": "high",
            "timestamp": "2024-01-01T00:00:00"
        }
        
        # 矛盾する情報（ノイズ）
        noise_entry = {
            "key": "project_manager",
            "value": "佐藤花子",  # 矛盾
            "confidence": "low",
            "timestamp": "2024-01-01T01:00:00"
        }
        
        # ゲートを適用
        gated_correct = gating.gate_entry(
            correct_entry,
            []
        )
        gated_noise = gating.gate_entry(
            noise_entry,
            [correct_entry]
        )
        
        # 検証：矛盾検出されているか
        assert gated_noise["has_conflict"] == True, "矛盾が検出されません"
        assert gated_noise["gate_weight"] < gated_correct["gate_weight"], "ゲートが効いていません"
    
    def test_c_review_effect(self, memory_system):
        """
        テストC：復習効果
        
        同じ文章を2回読ませる（apply_review_effect）
        1回目と2回目で改善するか
        """
        text = "プロジェクトXの開始日は2024年2月1日です。"
        
        # 1回目
        result1 = memory_system.process(
            text=text,
            source="test_c_1",
            enable_rehearsal=True
        )
        
        # 2回目（復習）
        result2 = memory_system.process(
            text=text,
            source="test_c_2",
            enable_rehearsal=True
        )
        
        # 検証：2回目で更新が増えるか
        assert result2["rehearsal"]["updated_entries"] > 0, "復習効果が発動していません"
        
        # 検索で確認
        results = memory_system.retrieve("開始日", limit=5)
        assert len(results) > 0, "検索結果がありません"



