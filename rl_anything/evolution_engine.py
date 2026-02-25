#!/usr/bin/env python3
"""
Phase 3: 自己進化エンジン (Evolution Engine)
=============================================
成功パターンから「スキル」を抽出し、MEMORY.md / プロンプトに自動適用する。
動的難易度調整 (カリキュラム) による環境制御も行う。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .types import (
    DifficultyLevel,
    FeedbackType,
    RewardSignal,
    Skill,
    TaskOutcome,
    TaskRecord,
)

_DIR = Path(__file__).parent


class EvolutionEngine:
    """Phase 3: スキル抽出 + MEMORY.md 更新 + 難易度調整"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or self._load_config()
        evo_cfg = cfg.get("evolution", {})

        self.enabled: bool = evo_cfg.get("enabled", True)
        self.min_samples: int = evo_cfg.get("skill_extraction_min_samples", 3)
        self.success_threshold: float = evo_cfg.get("skill_success_threshold", 0.70)
        self.max_skills: int = evo_cfg.get("max_skills", 100)
        self.auto_apply: bool = evo_cfg.get("auto_apply_skills", True)

        # MEMORY.md パス
        memory_path = evo_cfg.get("memory_md_path", "MEMORY.md")
        self.memory_md_path = _DIR.parent / memory_path

        # データディレクトリ
        self._data_dir = _DIR.parent / "logs" / "rl_anything"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # スキルDB
        self.skills: List[Skill] = []
        self._load_skills()

        # 難易度状態
        self.current_difficulty: DifficultyLevel = DifficultyLevel.STANDARD
        self._difficulty_history: List[Dict[str, Any]] = []

    # ═══════════════════════════════════════════════════════
    # スキル抽出
    # ═══════════════════════════════════════════════════════
    def extract_skills(self, records: List[TaskRecord]) -> List[Skill]:
        """
        完了タスク群から成功パターンを「スキル」として抽出する。
        十分なサンプル数 + 高い成功率を持つパターンのみ。
        """
        if not self.enabled or len(records) < self.min_samples:
            return []

        pattern_stats = self._analyze_action_patterns(records)
        new_skills: List[Skill] = []

        for pattern_key, stats in pattern_stats.items():
            if stats["count"] < self.min_samples:
                continue
            if stats["success_rate"] < self.success_threshold:
                continue

            # 既存スキルと重複しないか
            existing_ids = {s.skill_id for s in self.skills}
            skill_id = self._make_skill_id(pattern_key)
            if skill_id in existing_ids:
                # 既存のものを更新
                for s in self.skills:
                    if s.skill_id == skill_id:
                        s.success_rate = stats["success_rate"]
                        s.sample_count = stats["count"]
                        s.last_used = datetime.now().isoformat()
                continue

            skill = Skill(
                skill_id=skill_id,
                name=stats["name"],
                description=stats["description"],
                pattern=pattern_key,
                context_tags=stats.get("tags", []),
                success_rate=stats["success_rate"],
                sample_count=stats["count"],
            )
            new_skills.append(skill)
            self.skills.append(skill)

        # 上限管理
        if len(self.skills) > self.max_skills:
            # 成功率が低い順に間引き
            self.skills.sort(key=lambda s: s.success_rate, reverse=True)
            self.skills = self.skills[: self.max_skills]

        if new_skills:
            self._save_skills()

        return new_skills

    def _analyze_action_patterns(self, records: List[TaskRecord]) -> Dict[str, Dict[str, Any]]:
        """アクション列のパターンを分析"""
        patterns: Dict[str, Dict[str, Any]] = {}

        # パターン1: テスト先行 (test-first)
        test_first_count = 0
        test_first_success = 0
        for r in records:
            tools = [a.tool_name.lower() for a in r.actions]
            test_idx = [i for i, t in enumerate(tools) if "test" in t]
            if test_idx and test_idx[0] < len(tools) * 0.3:
                test_first_count += 1
                if r.outcome == TaskOutcome.SUCCESS:
                    test_first_success += 1
        if test_first_count > 0:
            patterns["test_first"] = {
                "name": "テスト先行開発",
                "description": "テストをタスク前半で作成し、実装をテスト駆動で進める",
                "count": test_first_count,
                "success_rate": round(test_first_success / test_first_count, 3),
                "tags": ["test", "tdd"],
            }

        # パターン2: エラーリカバリー
        recovery_count = 0
        recovery_success = 0
        for r in records:
            errors = [a for a in r.actions if a.error]
            if errors:
                recovery_count += 1
                if r.outcome == TaskOutcome.SUCCESS:
                    recovery_success += 1
        if recovery_count > 0:
            patterns["error_recovery"] = {
                "name": "エラー回復パターン",
                "description": "エラー発生後に回復手順を実行して最終的に成功する",
                "count": recovery_count,
                "success_rate": round(recovery_success / recovery_count, 3),
                "tags": ["error-handling", "resilience"],
            }

        # パターン3: 段階的実装 (小さなステップ)
        incremental_count = 0
        incremental_success = 0
        for r in records:
            if 3 <= len(r.actions) <= 10:
                incremental_count += 1
                if r.outcome == TaskOutcome.SUCCESS:
                    incremental_success += 1
        if incremental_count > 0:
            patterns["incremental"] = {
                "name": "段階的実装",
                "description": "3-10 ステップの適度な粒度でタスクを分割して実行",
                "count": incremental_count,
                "success_rate": round(incremental_success / incremental_count, 3),
                "tags": ["incremental", "stepwise"],
            }

        # パターン4: 事前調査 (read-first)
        read_first_count = 0
        read_first_success = 0
        for r in records:
            tools = [a.tool_name.lower() for a in r.actions]
            read_idx = [i for i, t in enumerate(tools) if "read" in t or "search" in t or "grep" in t]
            if read_idx and read_idx[0] < len(tools) * 0.2:
                read_first_count += 1
                if r.outcome == TaskOutcome.SUCCESS:
                    read_first_success += 1
        if read_first_count > 0:
            patterns["read_first"] = {
                "name": "事前調査パターン",
                "description": "コード変更前にファイル読み込み/検索で十分なコンテキストを取得",
                "count": read_first_count,
                "success_rate": round(read_first_success / read_first_count, 3),
                "tags": ["research", "context-gathering"],
            }

        # パターン5: ツール組み合わせ頻度
        tool_pairs = Counter()
        pair_success = Counter()
        for r in records:
            tools = [a.tool_name for a in r.actions]
            for i in range(len(tools) - 1):
                pair = f"{tools[i]} → {tools[i + 1]}"
                tool_pairs[pair] += 1
                if r.outcome == TaskOutcome.SUCCESS:
                    pair_success[pair] += 1

        for pair, count in tool_pairs.most_common(5):
            if count >= self.min_samples:
                sr = pair_success[pair] / count
                patterns[f"toolpair:{pair}"] = {
                    "name": f"ツール連携: {pair}",
                    "description": f"「{pair}」の順でツールを使用するパターン (n={count})",
                    "count": count,
                    "success_rate": round(sr, 3),
                    "tags": ["tool-chain"],
                }

        return patterns

    @staticmethod
    def _make_skill_id(pattern_key: str) -> str:
        return hashlib.sha256(pattern_key.encode()).hexdigest()[:12]

    # ═══════════════════════════════════════════════════════
    # 難易度調整 (カリキュラム制御)
    # ═══════════════════════════════════════════════════════
    def adjust_difficulty(
        self, recommended: DifficultyLevel, current_rate: float
    ) -> Dict[str, Any]:
        """
        推奨難易度に基づいて環境を調整。
        成功率 >80%: 抽象的指示（難易度↑）
        成功率 <20%: 具体的指示（難易度↓）
        """
        old = self.current_difficulty
        self.current_difficulty = recommended

        adjustment = {
            "old_difficulty": old.value,
            "new_difficulty": recommended.value,
            "success_rate": round(current_rate, 4),
            "changed": old != recommended,
            "instruction_hint": self._difficulty_to_instruction_hint(recommended),
            "timestamp": datetime.now().isoformat(),
        }

        self._difficulty_history.append(adjustment)
        return adjustment

    @staticmethod
    def _difficulty_to_instruction_hint(level: DifficultyLevel) -> str:
        """難易度レベルに応じた指示スタイルのヒント"""
        hints = {
            DifficultyLevel.CONCRETE: (
                "具体的に指示: 変更対象のファイル名、関数名、行番号を明示。"
                "例: 「src/utils.py の parse_date() 関数を修正して」"
            ),
            DifficultyLevel.GUIDED: (
                "ガイド付き: 方針と対象範囲を示すが詳細は任せる。"
                "例: 「日付パーサーにタイムゾーン対応を追加して」"
            ),
            DifficultyLevel.STANDARD: (
                "標準: 目的を示し、実装方法はエージェント判断。"
                "例: 「日付処理の国際化対応をして」"
            ),
            DifficultyLevel.ABSTRACT: (
                "抽象的: ゴールのみ。設計判断を含めて任せる。"
                "例: 「この機能のバグを直して」"
            ),
        }
        return hints.get(level, hints[DifficultyLevel.STANDARD])

    # ═══════════════════════════════════════════════════════
    # MEMORY.md 更新
    # ═══════════════════════════════════════════════════════
    def update_memory_md(self, force: bool = False) -> Dict[str, Any]:
        """
        スキルをMEMORY.mdに自動反映する。
        Claude Code / Cursor のコンテキストとして次回タスクに影響。
        """
        if not self.auto_apply and not force:
            return {"skipped": True, "reason": "auto_apply disabled"}

        if not self.skills:
            return {"skipped": True, "reason": "no skills"}

        # MEMORY.md の生成
        content = self._generate_memory_content()

        try:
            self.memory_md_path.parent.mkdir(parents=True, exist_ok=True)

            # 既存内容の保持 (RLAnything セクションのみ更新)
            existing = ""
            if self.memory_md_path.exists():
                existing = self.memory_md_path.read_text(encoding="utf-8")

            marker_start = "<!-- rl_anything:start -->"
            marker_end = "<!-- rl_anything:end -->"

            new_section = f"{marker_start}\n{content}\n{marker_end}"

            if marker_start in existing:
                # 既存セクションを置換
                pattern = re.compile(
                    re.escape(marker_start) + r".*?" + re.escape(marker_end),
                    re.DOTALL,
                )
                updated = pattern.sub(new_section, existing)
            else:
                # 末尾に追加
                updated = existing.rstrip() + "\n\n" + new_section + "\n"

            self.memory_md_path.write_text(updated, encoding="utf-8")

            return {
                "updated": True,
                "path": str(self.memory_md_path),
                "skills_written": len(self.skills),
                "difficulty": self.current_difficulty.value,
            }
        except Exception as e:
            return {"error": str(e)}

    def _generate_memory_content(self) -> str:
        """MEMORY.md 用のコンテンツを生成"""
        lines = [
            "## RLAnything 自己進化メモ",
            "",
            f"更新日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"現在の難易度: **{self.current_difficulty.value}**",
            f"蓄積スキル: {len(self.skills)} 件",
            "",
            "### 学習済みスキル (成功パターン)",
            "",
        ]

        # 成功率の高い順にソート
        sorted_skills = sorted(self.skills, key=lambda s: s.success_rate, reverse=True)
        for i, skill in enumerate(sorted_skills[:20], 1):
            lines.append(
                f"{i}. **{skill.name}** (成功率: {skill.success_rate:.0%}, "
                f"n={skill.sample_count})"
            )
            lines.append(f"   - {skill.description}")
            if skill.context_tags:
                lines.append(f"   - タグ: {', '.join(skill.context_tags)}")
            lines.append("")

        lines.append("### 推奨行動指針")
        lines.append("")
        lines.append(self._difficulty_to_instruction_hint(self.current_difficulty))
        lines.append("")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════
    # 進化サイクル一括実行
    # ═══════════════════════════════════════════════════════
    def run_evolution_cycle(
        self,
        records: List[TaskRecord],
        recommended_difficulty: DifficultyLevel,
        current_success_rate: float,
    ) -> Dict[str, Any]:
        """Phase 3 の全処理を一括実行"""
        # 1) スキル抽出
        new_skills = self.extract_skills(records)

        # 2) 難易度調整
        difficulty_result = self.adjust_difficulty(recommended_difficulty, current_success_rate)

        # 3) MEMORY.md 更新
        memory_result = self.update_memory_md()

        return {
            "new_skills": [s.to_dict() for s in new_skills],
            "total_skills": len(self.skills),
            "difficulty_adjustment": difficulty_result,
            "memory_update": memory_result,
            "timestamp": datetime.now().isoformat(),
        }

    # ═══════════════════════════════════════════════════════
    # ステート管理
    # ═══════════════════════════════════════════════════════
    def get_stats(self) -> Dict[str, Any]:
        return {
            "skills_count": len(self.skills),
            "current_difficulty": self.current_difficulty.value,
            "difficulty_changes": len(self._difficulty_history),
            "top_skills": [
                {"name": s.name, "rate": s.success_rate, "n": s.sample_count}
                for s in sorted(self.skills, key=lambda x: x.success_rate, reverse=True)[:5]
            ],
        }

    @staticmethod
    def _load_config() -> Dict[str, Any]:
        cfg_path = _DIR / "config.json"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_skills(self) -> None:
        skills_file = self._data_dir / "skills.json"
        if skills_file.exists():
            try:
                with open(skills_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    self.skills.append(Skill(**item))
            except Exception:
                pass

    def _save_skills(self) -> None:
        skills_file = self._data_dir / "skills.json"
        try:
            with open(skills_file, "w", encoding="utf-8") as f:
                json.dump(
                    [s.to_dict() for s in self.skills],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception:
            pass
