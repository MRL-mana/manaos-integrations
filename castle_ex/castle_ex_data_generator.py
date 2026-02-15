#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CASTLE-EXフレームワーク: 学習データ生成ツール

7層構造（Layer 0-6）に基づくJSONLデータ生成機能
推論×感情×文脈の3軸統合データ生成
"""

import sys
import json
import random
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError, TypeError):
        pass


class CastleEXDataGenerator:
    """CASTLE-EXフレームワークに基づく学習データ生成器"""

    def __init__(self, random_seed: int = 42):
        """初期化"""
        random.seed(random_seed)
        # レミ先輩推奨のLayer配分（logic-onlyを30%前後に）
        self.layer_distribution = {
            0: 0.08,  # 公理層
            1: 0.16,  # 操作層（少し上げる）
            2: 0.08,  # 関係層
            3: 0.12,  # 感情基礎層
            4: 0.12,  # 文脈基礎層
            5: 0.22,  # 因果層（増やす）
            6: 0.22,  # 統合層（増やす）
        }

        # error_typeの最小セット（6-10個に固定）
        self.error_types = [
            "logic_error",  # 結論が間違い
            "missing_reason",  # 理由なし
            "emotion_mismatch",  # 空気読めない
            "context_miss",  # 状況無視
            "overconfident",  # 根拠ない断定
            "unsafe_action",  # 危険な提案（秘書運用に効く）
        ]

        # 重複検知用（正規化ハッシュ）
        self.seen_hashes = set()

        # reject統計用
        self.reject_stats = {"total_generated": 0, "total_rejected": 0, "reject_reasons": {}}

        # 可変スロット辞書（レミ先輩推奨）
        self.slots = {
            # 強差分（必須）
            "time": [
                "06:10",
                "07:25",
                "08:40",
                "09:15",
                "10:30",
                "11:45",
                "12:20",
                "13:35",
                "14:50",
                "15:05",
                "16:20",
                "17:35",
                "18:50",
                "19:15",
                "20:30",
                "21:45",
                "22:10",
                "23:25",
            ],
            "n": [str(i) for i in range(1, 13)],  # 1〜12
            "n2": [str(i) for i in range(0, 8)],  # 0〜7（変化後の値）
            "pct": [f"+{i}%" for i in range(5, 36, 5)],  # +5%〜+35%
            "money": [f"{i}円" for i in range(500, 12001, 500)],  # 500〜12000円
            "temp": [f"{i}℃" for i in range(-2, 36)],  # -2〜35℃
            "minutes": [str(i) for i in range(5, 61, 5)],  # 5〜60分
            # 文脈（ManaOS）
            "place": [
                "レジ前",
                "洗車機前",
                "ピット",
                "電話対応",
                "給油機前",
                "店舗内",
                "駐車場",
                "オイル交換エリア",
            ],
            "situation": [
                "混雑",
                "人手不足",
                "雨",
                "夜間",
                "連休",
                "平日",
                "朝ラッシュ",
                "夕方ラッシュ",
                "深夜",
                "早朝",
            ],
            "task": [
                "給油",
                "洗車",
                "タイヤ空気圧",
                "オイル交換",
                "クレーム対応",
                "会計",
                "商品説明",
                "誘導",
                "清掃",
            ],
            "role": [
                "新人",
                "ベテラン",
                "常連客",
                "初来店",
                "高齢者",
                "家族連れ",
                "ビジネスマン",
                "学生",
            ],
            # 感情
            "emotion": [
                "怒り",
                "不安",
                "焦り",
                "安心",
                "嬉しい",
                "落ち込み",
                "困惑",
                "緊張",
                "疲れ",
                "満足",
            ],
            "intensity": ["小", "中", "大"],
            # オブジェクト（Layer 0-2用）
            "obj": [
                "犬",
                "猫",
                "車",
                "セルフ",
                "レギュラー",
                "😊",
                "😢",
                "🔧",
                "夜勤",
                "給油",
                "洗車",
                "オイル",
                "タイヤ",
                "エンジン",
                "ブレーキ",
            ],
            "other_obj": [
                "猫",
                "犬",
                "バイク",
                "ハイオク",
                "洗車",
                "😢",
                "😊",
                "🔨",
                "日勤",
                "洗車",
                "給油",
                "エンジン",
                "タイヤ",
                "オイル",
                "ブレーキ",
            ],
            # フレーズ（Layer 1用）
            "phrase1": [
                "怒る",
                "忙しい",
                "迷惑",
                "疲れた",
                "嬉しい",
                "悲しい",
                "不安",
                "焦る",
                "困る",
                "イライラする",
                "腹が立つ",
                "手が離せない",
                "立て込んでる",
                "やめてほしい",
            ],
            "phrase2": [
                "イライラする",
                "手が離せない",
                "困る",
                "クタクタ",
                "幸せ",
                "つらい",
                "心配",
                "急ぐ",
                "悩む",
                "腹が立つ",
                "怒る",
                "立て込んでる",
                "忙しい",
                "迷惑",
            ],
        }

    def fill_slots(self, template: str) -> str:
        """テンプレートのスロットを埋める（レミ先輩推奨：可変スロット化）"""
        import re

        result = template
        # {slot_name} を辞書からランダムに選択して置換
        slot_pattern = r"\{(\w+)\}"
        matches = re.findall(slot_pattern, template)
        for slot_name in matches:
            if slot_name in self.slots:
                value = random.choice(self.slots[slot_name])
                result = result.replace(f"{{{slot_name}}}", value, 1)
        return result

    def fill_slots_shared(
        self, *templates: str, slot_dict: Optional[Dict[str, List[str]]] = None
    ) -> List[str]:
        """
        複数テンプレートで同じスロット値を共有して埋める（Layer 2 ペアリング崩壊防止）。
        slot_dict を渡すとその辞書のみを参照（Layer 2 の l2_* 名前空間用）。
        """
        import re

        slot_pattern = r"\{(\w+)\}"
        slot_names = set()
        for t in templates:
            slot_names.update(re.findall(slot_pattern, t))
        source = slot_dict if slot_dict is not None else self.slots
        mapping = {}
        for name in slot_names:
            if name in source:
                mapping[name] = random.choice(source[name])
        results = []
        for t in templates:
            r = t
            for name, value in mapping.items():
                r = r.replace(f"{{{name}}}", value, 1)
            results.append(r)
        return results

    def generate_layer_0_data(self, count: int) -> List[Dict]:
        """Layer 0: 公理層データ生成（可変スロット化）"""
        data = []

        # 同一性（スロット化）
        identity_templates = [
            "{obj} = {obj} ?",
            "{n} = {n} ?",
            "{time} = {time} ?",
        ]

        # 差異（スロット化）
        difference_templates = [
            "{obj} = {other_obj} ?",
            "{n} = {n2} ?",
            "{place} = {task} ?",
        ]

        # 負例（logic_error）
        error_templates = [
            ("{obj} = {other_obj} ?", "同じ。"),  # 間違い
            ("{n} = {n2} ?", "同じ。"),  # 間違い（n != n2）
        ]

        positive_count = int(count * 0.7)
        negative_count = count - positive_count

        # 正例生成
        for _ in range(positive_count):
            if random.random() < 0.5:
                # 同一性
                template = random.choice(identity_templates)
                question = self.fill_slots(template)
                answer = "同じ。"
            else:
                # 差異
                template = random.choice(difference_templates)
                question = self.fill_slots(template)
                answer = "違う。"

            data.append(
                {
                    "layer": 0,
                    "axes": ["logic"],
                    "positive": True,
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    "type": "axiom",
                }
            )

        # 負例生成
        for _ in range(negative_count):
            template, wrong_answer = random.choice(error_templates)
            question = self.fill_slots(template)
            data.append(
                {
                    "layer": 0,
                    "axes": ["logic"],
                    "positive": False,
                    "error_type": "logic_error",
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": wrong_answer},
                    ],
                    "type": "axiom_error",
                }
            )

        return data

    def generate_layer_1_data(self, count: int) -> List[Dict]:
        """Layer 1: 操作層データ生成（可変スロット化、語彙・同義語変換含む）"""
        data = []

        # 同義語（スロット化）
        synonym_templates = [
            ("{phrase1} と {phrase2} は同じ意味？", "はい。だいたい同じ意味です。"),
            ("{phrase1} = {phrase2} ?", "はい。似た意味です。"),
        ]

        # 反義語（スロット化）
        antonym_templates = [
            ("{phrase1} ↔ ?", "{phrase2}"),
        ]

        # 算術（スロット化）
        arithmetic_templates = [
            ("{n} + {n2} = ?", lambda n, n2: str(int(n) + int(n2))),
            ("{n} - {n2} = ?", lambda n, n2: str(max(0, int(n) - int(n2)))),
        ]

        # 論理
        logical_templates = [
            ("真 AND 真 = ?", "真"),
            ("真 OR 偽 = ?", "真"),
        ]

        # 負例（context_miss: 文脈次第を無視）
        error_templates = [
            ("{phrase1} と {phrase2} は同じ意味？", "絶対同じ。"),  # 文脈次第を無視
        ]

        positive_count = int(count * 0.8)
        negative_count = count - positive_count

        # 正例生成
        for _ in range(positive_count):
            template_type = random.choice(["synonym", "antonym", "arithmetic", "logical"])

            if template_type == "synonym":
                template, answer_template = random.choice(synonym_templates)
                question = self.fill_slots(template)
                answer = self.fill_slots(answer_template)
            elif template_type == "antonym":
                template, answer_template = random.choice(antonym_templates)
                question = self.fill_slots(template)
                # 反義語のペアを取得
                idx = random.randint(
                    0, min(len(self.slots["phrase1"]), len(self.slots["phrase2"])) - 1
                )
                phrase1 = self.slots["phrase1"][idx]
                phrase2 = self.slots["phrase2"][idx]
                question = question.replace("{phrase1}", phrase1)
                answer = phrase2
            elif template_type == "arithmetic":
                template, answer_func = random.choice(arithmetic_templates)
                question = self.fill_slots(template)
                # 数値を抽出して計算
                n = random.choice(self.slots["n"])
                n2 = random.choice(self.slots["n2"])
                question = question.replace("{n}", n).replace("{n2}", n2)
                answer = answer_func(n, n2)
            else:  # logical
                template, answer = random.choice(logical_templates)
                question = template

            data.append(
                {
                    "layer": 1,
                    "axes": ["logic"],
                    "positive": True,
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    "type": "operation",
                }
            )

        # 負例生成
        for _ in range(negative_count):
            template, wrong_answer = random.choice(error_templates)
            question = self.fill_slots(template)
            answer = wrong_answer
            data.append(
                {
                    "layer": 1,
                    "axes": ["logic"],
                    "positive": False,
                    "error_type": "context_miss",
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    "type": "operation_error",
                }
            )

        return data

    def generate_layer_2_data(self, count: int) -> List[Dict]:
        """Layer 2: 関係層データ生成（スロット化）。l2_* 名前空間で他層とスロット衝突を防止。"""
        data = []

        # スロット辞書に追加（他層と共有するキーはそのまま用意）
        if "category" not in self.slots:
            self.slots["category"] = [
                "動物",
                "感情",
                "作業",
                "文脈",
                "場所",
                "時間",
                "物",
                "人",
                "接客",
                "安全",
                "整備",
                "清掃",
                "事務",
            ]
        if "part" not in self.slots:
            self.slots["part"] = [
                "タイヤ",
                "エンジン",
                "ブレーキ",
                "オイル",
                "給油ノズル",
                "洗車機",
                "レジ",
                "ピット",
            ]
        if "whole" not in self.slots:
            self.slots["whole"] = ["車", "作業", "店舗", "システム", "感情", "文脈", "時間", "空間"]
        if "attr" not in self.slots:
            self.slots["attr"] = ["色", "大きさ", "役割", "優先度", "重要度", "危険度", "難易度"]
        if "value" not in self.slots:
            self.slots["value"] = ["赤", "大きい", "重要", "高い", "低い", "難しい", "簡単"]
        if "a" not in self.slots:
            self.slots["a"] = ["給油", "洗車", "タイヤ空気圧", "オイル交換", "会計"]
        if "b" not in self.slots:
            self.slots["b"] = ["洗車", "給油", "オイル交換", "タイヤ空気圧", "クレーム対応"]
        if "metric" not in self.slots:
            self.slots["metric"] = ["早い", "重要", "簡単", "危険", "効率的"]

        # Layer 2 専用名前空間（v1.2 で他タスクの {item} 等と衝突しないように）
        layer2_slots = {
            "l2_obj": self.slots.get("obj", self.slots["part"]),
            "l2_category": self.slots["category"],
            "l2_part": self.slots["part"],
            "l2_whole": self.slots["whole"],
            "l2_attr": self.slots["attr"],
            "l2_value": self.slots["value"],
            "l2_a": self.slots["a"],
            "l2_b": self.slots["b"],
            "l2_metric": self.slots["metric"],
            "l2_role": self.slots["role"],
            "l2_task": self.slots["task"],
        }

        # 分類（l2_* のみ使用）
        classification_templates = [
            ("{l2_obj} は {l2_category}？", "はい。{l2_obj}は{l2_category}の一種です。"),
        ]
        part_whole_templates = [
            ("{l2_part} は {l2_whole} の一部？", "はい。{l2_part}は{l2_whole}に含まれます。"),
        ]
        # 答えに l2_obj と l2_attr を含める（バリデータの必須語条件を通す）
        attribute_templates = [
            ("{l2_obj} の {l2_attr} は？", "{l2_obj}の{l2_attr}は{l2_value}です。"),
        ]
        # 答えに l2_a と l2_b の両方を含める（バリデータの A/B 両方要求を通す）
        comparison_templates = [
            (
                "{l2_a} と {l2_b}、どっちが{l2_metric}？",
                "{l2_a}と{l2_b}では{l2_a}の方が{l2_metric}です。",
            ),
        ]
        # 答えに l2_role と「仕事」を含める（バリデータの必須語条件を通す）
        correspondence_templates = [
            ("{l2_role} の仕事は？", "{l2_role}の仕事は{l2_task}です。"),
        ]
        # 答えに必ず l2_task / l2_category を含める（バリデータの必須語条件を通す）
        manaos_relation_templates = [
            ("{l2_task} は {l2_category}？", "はい。{l2_task}は{l2_category}の一種です。"),
            (
                "{l2_task} は {l2_category} に入る？",
                "はい。{l2_task}は{l2_category}に含まれます。/いいえ。{l2_task}は{l2_category}ではありません。",
            ),
        ]

        all_templates = (
            [("classification", classification_templates)]
            + [("part_whole", part_whole_templates)]
            + [("attribute", attribute_templates)]
            + [("comparison", comparison_templates)]
            + [("correspondence", correspondence_templates)]
            + [("manaos_relation", manaos_relation_templates)]
        )

        for _ in range(count):
            template_type, templates = random.choice(all_templates)
            template, answer_template = random.choice(templates)
            # 問いと答えで同じスロット値を共有（layer2_slots のみ参照で他層と衝突しない）
            question, answer = self.fill_slots_shared(
                template, answer_template, slot_dict=layer2_slots
            )
            # stratified split で同一テンプレ・同一ペアが train/eval に分離しないように付与
            pair_id = hashlib.md5((question + answer).encode("utf-8")).hexdigest()[:12]

            data.append(
                {
                    "layer": 2,
                    "axes": ["logic"],
                    "positive": True,
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    "type": "relation",
                    "template_id": f"l2_{template_type}",
                    "pair_id": pair_id,
                }
            )

        return data

    def generate_layer_2_v11(self, count_per_template: int = 80) -> List[Dict]:
        """
        v1.1 用 Layer 2: 3テンプレ × 各80件（正40 + 負40）= 240件。
        負例は「反転・差し替え」のみ（脱線なし）。バリデータ必須語は満たす。
        """
        data = []
        # スロット準備（generate_layer_2_data と同様）
        if "category" not in self.slots:
            self.slots["category"] = [
                "動物",
                "感情",
                "作業",
                "文脈",
                "場所",
                "時間",
                "物",
                "人",
                "接客",
                "安全",
                "整備",
                "清掃",
                "事務",
            ]
        if "part" not in self.slots:
            self.slots["part"] = [
                "タイヤ",
                "エンジン",
                "ブレーキ",
                "オイル",
                "給油ノズル",
                "洗車機",
                "レジ",
                "ピット",
            ]
        if "whole" not in self.slots:
            self.slots["whole"] = ["車", "作業", "店舗", "システム", "感情", "文脈", "時間", "空間"]
        if "attr" not in self.slots:
            self.slots["attr"] = ["色", "大きさ", "役割", "優先度", "重要度", "危険度", "難易度"]
        if "value" not in self.slots:
            self.slots["value"] = ["赤", "大きい", "重要", "高い", "低い", "難しい", "簡単"]
        if "a" not in self.slots:
            self.slots["a"] = ["給油", "洗車", "タイヤ空気圧", "オイル交換", "会計"]
        if "b" not in self.slots:
            self.slots["b"] = ["洗車", "給油", "オイル交換", "タイヤ空気圧", "クレーム対応"]
        if "metric" not in self.slots:
            self.slots["metric"] = ["早い", "重要", "簡単", "危険", "効率的"]

        layer2_slots = {
            "l2_part": self.slots["part"],
            "l2_whole": self.slots["whole"],
            "l2_obj": self.slots.get("obj", self.slots["part"]),
            "l2_attr": self.slots["attr"],
            "l2_value": self.slots["value"],
            "l2_a": self.slots["a"],
            "l2_b": self.slots["b"],
            "l2_metric": self.slots["metric"],
        }

        half = count_per_template // 2  # 40

        # 1) part_whole: 正例=はい＋含まれる / 負例=いいえ＋含まれない（yes/no反転）
        tpl_pw_q = "{l2_part} は {l2_whole} の一部？"
        tpl_pw_pos = "はい。{l2_part}は{l2_whole}に含まれます。"
        tpl_pw_neg = "いいえ。{l2_part}は{l2_whole}に含まれません。"
        for _ in range(half):
            q, a = self.fill_slots_shared(tpl_pw_q, tpl_pw_pos, slot_dict=layer2_slots)
            pair_id = hashlib.md5((q + a).encode("utf-8")).hexdigest()[:12]
            data.append(
                {
                    "layer": 2,
                    "axes": ["logic"],
                    "positive": True,
                    "messages": [
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": a},
                    ],
                    "type": "relation",
                    "template_id": "l2_part_whole",
                    "pair_id": pair_id,
                }
            )
        for _ in range(half):
            q, a = self.fill_slots_shared(tpl_pw_q, tpl_pw_neg, slot_dict=layer2_slots)
            pair_id = hashlib.md5((q + a).encode("utf-8")).hexdigest()[:12]
            data.append(
                {
                    "layer": 2,
                    "axes": ["logic"],
                    "positive": False,
                    "error_type": "logic_error",
                    "messages": [
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": a},
                    ],
                    "type": "relation",
                    "template_id": "l2_part_whole",
                    "pair_id": pair_id,
                }
            )

        # 2) attribute: 正例=正しいvalue / 負例=value差し替え（近いが違う）
        tpl_attr_q = "{l2_obj} の {l2_attr} は？"
        tpl_attr_a = "{l2_obj}の{l2_attr}は{l2_value}です。"
        for _ in range(half):
            q, a = self.fill_slots_shared(tpl_attr_q, tpl_attr_a, slot_dict=layer2_slots)
            pair_id = hashlib.md5((q + a).encode("utf-8")).hexdigest()[:12]
            data.append(
                {
                    "layer": 2,
                    "axes": ["logic"],
                    "positive": True,
                    "messages": [
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": a},
                    ],
                    "type": "relation",
                    "template_id": "l2_attribute",
                    "pair_id": pair_id,
                }
            )
        for _ in range(half):
            q, a_pos = self.fill_slots_shared(tpl_attr_q, tpl_attr_a, slot_dict=layer2_slots)
            # 負例: 別の value に差し替え。「はXです」の X のみ正規表現で置換（重要度の「重要」を壊さない）
            vals = list(layer2_slots["l2_value"])
            cur_val = next((v for v in vals if v in a_pos), vals[0])
            other_vals = [v for v in vals if v != cur_val]
            wrong_val = random.choice(other_vals) if other_vals else cur_val
            a_neg = re.sub(r"は(.+?)です\.?$", "は" + wrong_val + "です。", a_pos, count=1)
            if a_neg == a_pos:
                a_neg = a_pos.replace("は" + cur_val + "です", "は" + wrong_val + "です", 1)
            pair_id = hashlib.md5((q + a_neg).encode("utf-8")).hexdigest()[:12]
            data.append(
                {
                    "layer": 2,
                    "axes": ["logic"],
                    "positive": False,
                    "error_type": "logic_error",
                    "messages": [
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": a_neg},
                    ],
                    "type": "relation",
                    "template_id": "l2_attribute",
                    "pair_id": pair_id,
                }
            )

        # 3) comparison: 正例=Aの方が / 負例=勝者反転（Bの方が）
        tpl_cmp_q = "{l2_a} と {l2_b}、どっちが{l2_metric}？"
        tpl_cmp_pos = "{l2_a}と{l2_b}では{l2_a}の方が{l2_metric}です。"
        tpl_cmp_neg = "{l2_a}と{l2_b}では{l2_b}の方が{l2_metric}です。"
        for _ in range(half):
            q, a = self.fill_slots_shared(tpl_cmp_q, tpl_cmp_pos, slot_dict=layer2_slots)
            pair_id = hashlib.md5((q + a).encode("utf-8")).hexdigest()[:12]
            data.append(
                {
                    "layer": 2,
                    "axes": ["logic"],
                    "positive": True,
                    "messages": [
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": a},
                    ],
                    "type": "relation",
                    "template_id": "l2_comparison",
                    "pair_id": pair_id,
                }
            )
        for _ in range(half):
            q, a = self.fill_slots_shared(tpl_cmp_q, tpl_cmp_neg, slot_dict=layer2_slots)
            pair_id = hashlib.md5((q + a).encode("utf-8")).hexdigest()[:12]
            data.append(
                {
                    "layer": 2,
                    "axes": ["logic"],
                    "positive": False,
                    "error_type": "logic_error",
                    "messages": [
                        {"role": "user", "content": q},
                        {"role": "assistant", "content": a},
                    ],
                    "type": "relation",
                    "template_id": "l2_comparison",
                    "pair_id": pair_id,
                }
            )

        return data

    def generate_layer2_lora_bulk(
        self,
        n_attribute: int = 400,
        n_comparison: int = 400,
        n_part_whole: int = 150,
    ) -> List[Dict]:
        """
        Layer2 専用 LoRA 用データを設計通りに量産。
        - l2_attribute: 「常識とズラした」値で「データで決まる」を叩き込む（正例のみ）
        - l2_comparison: A正解/B正解を50:50で「データが正解」を叩き込む（正例のみ）
        - l2_part_whole: 抽象語で yes/no 両方（正例のみ）
        既存の fill_slots_shared + messages 形式でそのまま JSONL 出力可。
        """
        data = []

        # 対象オブジェクト（属性・部分の候補）
        objs = [
            "タイヤ", "エンジン", "ブレーキ", "オイル", "給油ノズル", "洗車機", "レジ", "ピット",
            "車", "洗車", "給油", "オイル交換", "夜勤", "猫", "😢",
        ]
        # 属性→「常識とズラす」値の対応（重要度→低い、危険度→低い/中、大きさ→小さい、色→青/黒 等）
        attr_to_values: Dict[str, List[str]] = {
            "重要度": ["低い", "無視できる", "中"],
            "危険度": ["低い", "中", "簡単"],
            "優先度": ["低い", "無視できる", "小さい"],
            "大きさ": ["小さい", "中", "赤"],
            "役割": ["簡単", "補助", "低い"],
            "難易度": ["簡単", "低い", "中"],
            "色": ["青", "黒", "低い"],
        }
        attrs = list(attr_to_values.keys())

        # 1) l2_attribute: 300〜500件（正例のみ）
        tpl_attr_q = "{l2_obj} の {l2_attr} は？"
        tpl_attr_a = "{l2_obj}の{l2_attr}は{l2_value}です。"
        for _ in range(n_attribute):
            obj = random.choice(objs)
            attr = random.choice(attrs)
            value = random.choice(attr_to_values[attr])
            slot_dict = {
                "l2_obj": [obj],
                "l2_attr": [attr],
                "l2_value": [value],
            }
            q, a = self.fill_slots_shared(tpl_attr_q, tpl_attr_a, slot_dict=slot_dict)
            pair_id = hashlib.md5((q + a).encode("utf-8")).hexdigest()[:12]
            data.append({
                "layer": 2,
                "axes": ["logic"],
                "positive": True,
                "messages": [
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": a},
                ],
                "type": "relation",
                "template_id": "l2_attribute",
                "pair_id": pair_id,
            })

        # 2) l2_comparison: 300〜500件、A正解:B正解=50:50（正例のみ）
        a_list = ["給油", "洗車", "タイヤ空気圧", "オイル交換", "会計", "クレーム対応", "点検", "清掃"]
        b_list = [x for x in a_list if x != "会計"]  # 重複なしペア用
        metrics = ["早い", "遅い", "重要", "危険", "安全", "効率的", "簡単", "難しい"]
        tpl_cmp_q = "{l2_a} と {l2_b}、どっちが{l2_metric}？"
        tpl_cmp_a = "{l2_a}と{l2_b}では{l2_winner}の方が{l2_metric}です。"
        for _ in range(n_comparison):
            a_val = random.choice(a_list)
            b_val = random.choice([x for x in b_list if x != a_val] or a_list)
            metric = random.choice(metrics)
            winner = random.choice([a_val, b_val])  # 50:50
            slot_dict = {
                "l2_a": [a_val],
                "l2_b": [b_val],
                "l2_metric": [metric],
                "l2_winner": [winner],
            }
            q, a = self.fill_slots_shared(tpl_cmp_q, tpl_cmp_a, slot_dict=slot_dict)
            pair_id = hashlib.md5((q + a).encode("utf-8")).hexdigest()[:12]
            data.append({
                "layer": 2,
                "axes": ["logic"],
                "positive": True,
                "messages": [
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": a},
                ],
                "type": "relation",
                "template_id": "l2_comparison",
                "pair_id": pair_id,
            })

        # 3) l2_part_whole: 100〜200件、yes/no 両方（正例のみ）
        parts = ["タイヤ", "エンジン", "ブレーキ", "給油ノズル", "洗車機", "レジ", "オイル", "ピット"]
        wholes = ["車", "システム", "文脈", "空間", "店舗", "作業", "管理", "構成", "感情", "時間"]
        tpl_pw_q = "{l2_part} は {l2_whole} の一部？"
        tpl_pw_yes = "はい。{l2_part}は{l2_whole}に含まれます。"
        tpl_pw_no = "いいえ。{l2_part}は{l2_whole}に含まれません。"
        for _ in range(n_part_whole):
            part = random.choice(parts)
            whole = random.choice(wholes)
            use_yes = random.choice([True, False])  # 50:50
            slot_dict = {"l2_part": [part], "l2_whole": [whole]}
            q, a = self.fill_slots_shared(
                tpl_pw_q, tpl_pw_yes if use_yes else tpl_pw_no, slot_dict=slot_dict
            )
            pair_id = hashlib.md5((q + a).encode("utf-8")).hexdigest()[:12]
            data.append({
                "layer": 2,
                "axes": ["logic"],
                "positive": True,
                "messages": [
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": a},
                ],
                "type": "relation",
                "template_id": "l2_part_whole",
                "pair_id": pair_id,
            })

        return data

    def generate_layer_3_data(self, count: int) -> List[Dict]:
        """Layer 3: 感情基礎層データ生成（axis_evidence追加）"""
        data = []

        # 感情認識（スロット化、axis_evidence付き）
        emotion_recognition_templates = [
            (
                "今{emotion}。どう声かけすればいい？",
                "共感→状況確認→一手提案。{emotion}への配慮が必要。",
            ),
            (
                "{role}が{emotion}している。対応は？",
                "共感し、状況を確認。{emotion}への配慮が必要。",
            ),
        ]

        # 感情分類（スロット化、axis_evidence付き）
        emotion_classification_templates = [
            ("{emotion}、{emotion}、{emotion} → 共通点は？", "ポジティブ感情。快の状態。"),
            ("{emotion}、{emotion}、{emotion} → 共通点は？", "ネガティブ感情。不快の状態。"),
        ]

        # 感情遷移（スロット化、axis_evidence付き）
        emotion_transition_templates = [
            ("{emotion} → {time}経つ → ?", "和らぐ。または受容に変化。"),
            ("{emotion} → 深呼吸する → ?", "冷静になる。感情調整の効果。"),
        ]

        all_templates = (
            emotion_recognition_templates
            + emotion_classification_templates
            + emotion_transition_templates
        )

        for _ in range(count):
            template, answer_template = random.choice(all_templates)
            question = self.fill_slots(template)
            answer = self.fill_slots(answer_template)

            # axis_evidenceを生成
            emotion = random.choice(self.slots["emotion"])
            axis_evidence = {"emotion": [f"{emotion}への共感が必要", "感情の識別・分類・遷移"]}

            data.append(
                {
                    "layer": 3,
                    "axes": ["emotion"],
                    "positive": True,
                    "axis_evidence": axis_evidence,
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    "type": "emotion_base",
                }
            )

        return data

    def generate_layer_4_data(self, count: int) -> List[Dict]:
        """Layer 4: 文脈基礎層データ生成（axis_evidence追加）。l4_* 名前空間でペアリング崩壊防止。"""
        data = []

        # Layer 4 専用名前空間（他層とスロット衝突防止）
        layer4_slots = {
            "l4_role": self.slots["role"],
            "l4_situation": self.slots["situation"],
            "l4_place": self.slots["place"],
            "l4_emotion": self.slots["emotion"],
        }

        relationship_context_templates = [
            (
                "「やばい」って言われた。{l4_role}から、{l4_situation}だとどういう意味？",
                "良い/悪いの可能性説明。{l4_role}と{l4_situation}で意味が変わる。",
            ),
        ]
        situation_context_templates = [
            (
                "「大丈夫」({l4_place}で、{l4_role}から) → 意味は？",
                "強がりの可能性。本当は不安や痛みがあるかもしれない。",
            ),
            ("沈黙（{l4_situation}中）→ 意味は？", "同意、反対、または考え中。追加情報が必要。"),
        ]
        non_verbal_context_templates = [
            ("「いいよ」({l4_emotion}で) → 真意は？", "本当に良い。同意している。"),
        ]

        all_templates = (
            relationship_context_templates
            + situation_context_templates
            + non_verbal_context_templates
        )

        for _ in range(count):
            template, answer_template = random.choice(all_templates)
            question, answer = self.fill_slots_shared(
                template, answer_template, slot_dict=layer4_slots
            )
            place = random.choice(self.slots["place"])
            role = random.choice(self.slots["role"])
            situation = random.choice(self.slots["situation"])
            axis_evidence = {
                "context": [
                    f"{place}という文脈での解釈",
                    f"{role}という関係性",
                    f"{situation}という状況",
                ]
            }
            data.append(
                {
                    "layer": 4,
                    "axes": ["context"],
                    "positive": True,
                    "axis_evidence": axis_evidence,
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    "type": "context_base",
                }
            )
        return data

    def generate_layer_5_data(self, count: int) -> List[Dict]:
        """Layer 5: 因果層データ生成（3軸統合、state遷移含む）"""
        data = []

        # 感情的因果（正例、スロット化）- state遷移を観測可能な変化に
        emotional_causal_positive_templates = [
            {
                "state0_template": "{situation}、感情:{emotion}",
                "action": "勉強する",
                "state1_template": "模試の正答率 {pct}、感情:自信",
                "question_template": "{situation}({emotion}) → 勉強する → ?",
                "answer_template": "模試の正答率が{pct}向上し、自信が回復。失敗が動機となり成長につながる。",
                "axes": ["logic", "emotion"],
            },
            {
                "state0_template": "批判された、感情:{emotion}",
                "action": "冷静に聞く",
                "state1_template": "対話が{minutes}分継続、解決策が{n}つ出た、感情:安心",
                "question_template": "批判された({emotion}) → 冷静に聞く → ?",
                "answer_template": "対話が{minutes}分継続し、解決策が{n}つ出た(安心/理解)。感情調整により良い結果。",
                "axes": ["logic", "emotion", "context"],
            },
        ]

        # 3軸統合因果（正例、スロット化）- state遷移を観測可能な変化に
        integrated_causal_positive_templates = [
            {
                "state0_template": "{situation}、感情:{emotion}",
                "action": "頻出問題に絞って復習",
                "state1_template": "模試の正答率 {pct}、感情:安心",
                "question_template": "{situation}だけど{emotion}。何を優先すべき？",
                "answer_template": "{emotion}があるのは自然。今は頻出問題に絞って復習すると効率的です。模試で正答率が{pct}向上すれば自信につながります。",
                "axes": ["logic", "emotion", "context"],
            },
            {
                "state0_template": "{place}で{role}が忙しそう、{situation}、感情:{emotion}",
                "action": "「大丈夫、ありがとう」と断る",
                "state1_template": "関係悪化を回避、翌日も協力的、感情:安心",
                "question_template": "{role}が「手伝おうか？」({place}で、{situation}) → 真意と適切な対応は？",
                "answer_template": "社交辞令の可能性。本人も余裕がない。「大丈夫、ありがとう」と断るのが適切。無理に頼むと関係悪化のリスク。適切に断れば翌日も協力的な関係が保てる。",
                "axes": ["logic", "emotion", "context"],
            },
        ]

        # 負例：各種エラータイプ（分布を均す）- テンプレートを増やす
        emotional_causal_negative = [
            # emotion_mismatch（テンプレートを増やす - ユニーク供給力を上げる）
            {
                "state0": {"context": "試験に落ちた", "emotion": "悲しい"},
                "action": "反応",
                "state1": {"context": "誤った反応", "emotion": "無視"},
                "question": "試験に落ちて悲しい",
                "answer": "それは嬉しいね！次も頑張ろう！",
                "error_type": "emotion_mismatch",
                "axes": ["logic", "emotion"],
                "axis_evidence": {
                    "logic": ["原因→結果の説明が必要"],
                    "emotion": ["悲しい→励まし/共感が必要（しかし誤った反応）"],
                },
            },
            {
                "state0": {"context": "友人が転職した", "emotion": "不安"},
                "action": "反応",
                "state1": {"context": "誤った反応", "emotion": "無視"},
                "question": "友人が転職して不安",
                "answer": "それは素晴らしいね！おめでとう！",
                "error_type": "emotion_mismatch",
                "axes": ["logic", "emotion"],
                "axis_evidence": {
                    "logic": ["原因→結果の説明が必要"],
                    "emotion": ["不安→共感が必要（しかし誤った反応）"],
                },
            },
            {
                "state0": {"context": "{situation}、感情:{emotion}", "emotion": "{emotion}"},
                "action": "反応",
                "state1": {"context": "誤った反応", "emotion": "無視"},
                "question": "{situation}で{emotion}",
                "answer": "それは嬉しいね！次も頑張ろう！",
                "error_type": "emotion_mismatch",
                "axes": ["logic", "emotion"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{place}で{task}中、感情:{emotion}", "emotion": "{emotion}"},
                "action": "反応",
                "state1": {"context": "誤った反応", "emotion": "無視"},
                "question": "{place}で{task}中、{emotion}",
                "answer": "それは素晴らしいね！おめでとう！",
                "error_type": "emotion_mismatch",
                "axes": ["logic", "emotion", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {
                    "context": "{time}、{situation}、感情:{emotion}",
                    "emotion": "{emotion}",
                },
                "action": "反応",
                "state1": {"context": "誤った反応", "emotion": "無視"},
                "question": "{time}、{situation}で{emotion}",
                "answer": "それは嬉しいね！次も頑張ろう！",
                "error_type": "emotion_mismatch",
                "axes": ["logic", "emotion", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{role}が{task}中、感情:{emotion}", "emotion": "{emotion}"},
                "action": "反応",
                "state1": {"context": "誤った反応", "emotion": "無視"},
                "question": "{role}が{task}中、{emotion}",
                "answer": "それは素晴らしいね！おめでとう！",
                "error_type": "emotion_mismatch",
                "axes": ["logic", "emotion", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "緊急事態、感情:{emotion}", "emotion": "{emotion}"},
                "action": "反応",
                "state1": {"context": "誤った反応", "emotion": "無視"},
                "question": "緊急事態で{emotion}",
                "answer": "それは嬉しいね！次も頑張ろう！",
                "error_type": "emotion_mismatch",
                "axes": ["logic", "emotion"],
                "is_slot_template": True,
            },
            # missing_reason（テンプレートを増やす - ユニーク供給力を上げる）
            {
                "state0": {"context": "問題が発生", "emotion": "不安"},
                "action": "対応",
                "state1": {"context": "結論のみ", "emotion": "不安"},
                "question": "問題が発生して不安",
                "answer": "大丈夫です。",
                "error_type": "missing_reason",
                "axes": ["logic", "emotion"],
                "axis_evidence": {
                    "logic": ["理由なし（結論のみ）"],
                    "emotion": ["不安→励まし/共感が必要"],
                },
            },
            {
                "state0": {"context": "重要な決定", "emotion": "緊張"},
                "action": "判断",
                "state1": {"context": "結論のみ", "emotion": "緊張"},
                "question": "重要な決定をしなければならない",
                "answer": "問題ありません。",
                "error_type": "missing_reason",
                "axes": ["logic", "emotion"],
                "axis_evidence": {
                    "logic": ["理由なし（結論のみ）"],
                    "emotion": ["緊張→説明が必要"],
                },
            },
            {
                "state0": {"context": "{situation}", "emotion": "{emotion}"},
                "action": "対応",
                "state1": {"context": "結論のみ", "emotion": "{emotion}"},
                "question": "{situation}で{emotion}",
                "answer": "大丈夫です。",
                "error_type": "missing_reason",
                "axes": ["logic", "emotion"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{place}で{task}中", "emotion": "{emotion}"},
                "action": "判断",
                "state1": {"context": "結論のみ", "emotion": "{emotion}"},
                "question": "{place}で{task}中、{emotion}",
                "answer": "問題ありません。",
                "error_type": "missing_reason",
                "axes": ["logic", "emotion", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "緊急事態", "emotion": "{emotion}"},
                "action": "対応",
                "state1": {"context": "結論のみ", "emotion": "{emotion}"},
                "question": "緊急事態で{emotion}",
                "answer": "大丈夫です。",
                "error_type": "missing_reason",
                "axes": ["logic", "emotion"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{time}、{situation}", "emotion": "{emotion}"},
                "action": "判断",
                "state1": {"context": "結論のみ", "emotion": "{emotion}"},
                "question": "{time}、{situation}で{emotion}",
                "answer": "問題ありません。",
                "error_type": "missing_reason",
                "axes": ["logic", "emotion", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{role}が{task}中", "emotion": "{emotion}"},
                "action": "対応",
                "state1": {"context": "結論のみ", "emotion": "{emotion}"},
                "question": "{role}が{task}中、{emotion}",
                "answer": "大丈夫です。",
                "error_type": "missing_reason",
                "axes": ["logic", "emotion", "context"],
                "is_slot_template": True,
            },
            # overconfident
            {
                "state0": {"context": "会議中", "emotion": "緊張"},
                "action": "発言",
                "state1": {"context": "誤った判断", "emotion": "混乱"},
                "question": "会議中で緊張している",
                "answer": "絶対に正しい。間違いない。",
                "error_type": "overconfident",
                "axes": ["logic", "context"],
                "axis_evidence": {"logic": ["根拠ない断定"], "context": ["会議という状況での判断"]},
            },
            {
                "state0": {"context": "重要な判断", "emotion": "不安"},
                "action": "発言",
                "state1": {"context": "誤った判断", "emotion": "混乱"},
                "question": "重要な判断をしなければならない",
                "answer": "間違いなく正しいです。絶対にこれが最適解です。",
                "error_type": "overconfident",
                "axes": ["logic", "context"],
                "axis_evidence": {
                    "logic": ["根拠ない断定（過剰な自信）"],
                    "context": ["重要な判断という状況での不適切な確信"],
                },
            },
            # context_miss
            {
                "state0": {"context": "状況判断が必要", "emotion": "不安"},
                "action": "判断",
                "state1": {"context": "誤った判断", "emotion": "混乱"},
                "question": "状況判断が必要",
                "answer": "大丈夫です。",
                "error_type": "context_miss",
                "axes": ["logic", "context"],
                "axis_evidence": {
                    "logic": ["論理は合ってるが文脈を無視"],
                    "context": ["状況を無視した判断"],
                },
            },
            {
                "state0": {"context": "緊急事態", "emotion": "焦り"},
                "action": "対応",
                "state1": {"context": "誤った対応", "emotion": "混乱"},
                "question": "緊急事態が発生している",
                "answer": "通常通り対応します。",
                "error_type": "context_miss",
                "axes": ["logic", "context"],
                "axis_evidence": {
                    "logic": ["論理は合ってるが文脈を無視"],
                    "context": ["緊急事態という状況を無視"],
                },
            },
            # unsafe_action
            {
                "state0": {"context": "クレーム対応中", "emotion": "困惑"},
                "action": "対応",
                "state1": {"context": "危険な対応", "emotion": "不安"},
                "question": "クレーム対応中、客が激怒している",
                "answer": "お客様、落ち着いてください。こちらに非はありません。",
                "error_type": "unsafe_action",
                "axes": ["logic", "emotion", "context"],
                "axis_evidence": {
                    "logic": ["論理は合ってるが提案が危険"],
                    "emotion": ["感情は読めてるが対応が不適切"],
                    "context": ["クレーム対応という状況での判断ミス"],
                },
            },
            {
                "state0": {"context": "危険な作業", "emotion": "不安"},
                "action": "提案",
                "state1": {"context": "危険な提案", "emotion": "恐怖"},
                "question": "危険な作業をしなければならない",
                "answer": "安全装置なしで進めましょう。",
                "error_type": "unsafe_action",
                "axes": ["logic", "context"],
                "axis_evidence": {
                    "logic": ["論理は合ってるが提案が危険"],
                    "context": ["危険な作業という状況での判断ミス"],
                },
            },
            # logic_error（スロットテンプレート追加 - ユニーク供給力を上げる）
            {
                "state0": {"context": "問題発生", "emotion": "困惑"},
                "action": "判断",
                "state1": {"context": "誤った結論", "emotion": "混乱"},
                "question": "問題が発生している",
                "answer": "問題はありません。",
                "error_type": "logic_error",
                "axes": ["logic"],
                "axis_evidence": {"logic": ["結論が間違い"]},
            },
            {
                "state0": {"context": "{situation}、問題発生", "emotion": "{emotion}"},
                "action": "判断",
                "state1": {"context": "誤った結論", "emotion": "混乱"},
                "question": "{situation}で問題が発生している、{emotion}",
                "answer": "問題はありません。",
                "error_type": "logic_error",
                "axes": ["logic"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{place}で{task}中、問題発生", "emotion": "{emotion}"},
                "action": "判断",
                "state1": {"context": "誤った結論", "emotion": "混乱"},
                "question": "{place}で{task}中、問題が発生している、{emotion}",
                "answer": "問題はありません。",
                "error_type": "logic_error",
                "axes": ["logic", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{time}、{situation}、問題発生", "emotion": "{emotion}"},
                "action": "判断",
                "state1": {"context": "誤った結論", "emotion": "混乱"},
                "question": "{time}、{situation}で問題が発生している、{emotion}",
                "answer": "問題はありません。",
                "error_type": "logic_error",
                "axes": ["logic", "context"],
                "is_slot_template": True,
            },
            # context_miss（スロットテンプレート追加 - ユニーク供給力を上げる）
            {
                "state0": {"context": "{situation}、状況判断が必要", "emotion": "{emotion}"},
                "action": "判断",
                "state1": {"context": "誤った判断", "emotion": "混乱"},
                "question": "{situation}で状況判断が必要、{emotion}",
                "answer": "大丈夫です。",
                "error_type": "context_miss",
                "axes": ["logic", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{place}で{task}中、緊急事態", "emotion": "{emotion}"},
                "action": "対応",
                "state1": {"context": "誤った対応", "emotion": "混乱"},
                "question": "{place}で{task}中、緊急事態が発生している、{emotion}",
                "answer": "通常通り対応します。",
                "error_type": "context_miss",
                "axes": ["logic", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {
                    "context": "{time}、{situation}、状況判断が必要",
                    "emotion": "{emotion}",
                },
                "action": "判断",
                "state1": {"context": "誤った判断", "emotion": "混乱"},
                "question": "{time}、{situation}で状況判断が必要、{emotion}",
                "answer": "大丈夫です。",
                "error_type": "context_miss",
                "axes": ["logic", "context"],
                "is_slot_template": True,
            },
            # unsafe_action（スロットテンプレート追加 - ユニーク供給力を上げる）
            {
                "state0": {"context": "{place}で{task}中、客が{emotion}", "emotion": "{emotion}"},
                "action": "対応",
                "state1": {"context": "危険な対応", "emotion": "不安"},
                "question": "{place}で{task}中、客が{emotion}",
                "answer": "お客様、落ち着いてください。こちらに非はありません。",
                "error_type": "unsafe_action",
                "axes": ["logic", "emotion", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{time}、{situation}、{role}が{task}中", "emotion": "不安"},
                "action": "提案",
                "state1": {"context": "危険な提案", "emotion": "恐怖"},
                "question": "{time}、{situation}で{role}が{task}中",
                "answer": "安全装置なしで進めましょう。",
                "error_type": "unsafe_action",
                "axes": ["logic", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "緊急事態、{place}で{task}中", "emotion": "{emotion}"},
                "action": "対応",
                "state1": {"context": "危険な対応", "emotion": "恐怖"},
                "question": "緊急事態、{place}で{task}中、{emotion}",
                "answer": "通常通り対応します。",
                "error_type": "unsafe_action",
                "axes": ["logic", "emotion", "context"],
                "is_slot_template": True,
            },
            # overconfident（スロットテンプレート追加 - ユニーク供給力を上げる）
            {
                "state0": {"context": "{situation}、感情:{emotion}", "emotion": "{emotion}"},
                "action": "発言",
                "state1": {"context": "誤った判断", "emotion": "混乱"},
                "question": "{situation}で{emotion}",
                "answer": "絶対に正しい。間違いない。",
                "error_type": "overconfident",
                "axes": ["logic", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{place}で{task}中、感情:{emotion}", "emotion": "{emotion}"},
                "action": "判断",
                "state1": {"context": "誤った判断", "emotion": "混乱"},
                "question": "{place}で{task}中、{emotion}",
                "answer": "間違いなく正しいです。絶対にこれが最適解です。",
                "error_type": "overconfident",
                "axes": ["logic", "context"],
                "is_slot_template": True,
            },
            {
                "state0": {"context": "{time}、重要な判断、感情:{emotion}", "emotion": "{emotion}"},
                "action": "発言",
                "state1": {"context": "誤った判断", "emotion": "混乱"},
                "question": "{time}、重要な判断をしなければならない、{emotion}",
                "answer": "他の選択肢は考えなくて良いです。これが唯一の正解です。",
                "error_type": "overconfident",
                "axes": ["logic", "context"],
                "is_slot_template": True,
            },
        ]

        # hard negative（わざと難しい負例）
        hard_negative_templates = [
            {
                "state0": {"context": "クレーム対応中、客が怒っている", "emotion": "困惑"},
                "action": "反応",
                "state1": {"context": "表面的には共感したが危険", "emotion": "不安"},
                "question": "クレーム対応中、客が激怒している",
                "answer": "お気持ちお察しします。でも、こちらとしては一切の責任を負えません。",
                "error_type": "unsafe_action",
                "axes": ["logic", "emotion", "context"],
                "axis_evidence": {
                    "logic": ["共感はしてるが提案が危険"],
                    "emotion": ["感情は読めてるが対応が不適切"],
                    "context": ["クレーム対応という状況での判断ミス"],
                },
                "is_hard_negative": True,
            },
            {
                "state0": {"context": "重要な判断", "emotion": "不安"},
                "action": "発言",
                "state1": {"context": "誤った判断", "emotion": "混乱"},
                "question": "重要な判断をしなければならない",
                "answer": "間違いなく正しいです。絶対にこれが最適解です。他の選択肢は考えなくて良いです。",
                "error_type": "overconfident",
                "axes": ["logic", "context"],
                "axis_evidence": {
                    "logic": ["根拠ない断定（過剰な自信）"],
                    "context": ["重要な判断という状況での不適切な確信"],
                },
                "is_hard_negative": True,
            },
        ]

        # レミ先輩推奨: 負例率30%
        positive_count = int(count * 0.7)
        negative_count = count - positive_count

        # 正例生成（スロット化テンプレートを使用）
        all_positive_templates = (
            emotional_causal_positive_templates + integrated_causal_positive_templates
        )

        for _ in range(positive_count):
            template = random.choice(all_positive_templates)
            # スロットを埋める
            state0_str = self.fill_slots(template["state0_template"])
            state1_str = self.fill_slots(template["state1_template"])
            question = self.fill_slots(template["question_template"])
            answer = self.fill_slots(template["answer_template"])

            # axis_evidenceを生成
            emotion = random.choice(self.slots["emotion"])
            situation = random.choice(self.slots["situation"])
            place = random.choice(self.slots["place"])
            axis_evidence = {
                "logic": ["原因→結果の説明が必要", "行動→結果の因果"],
                "emotion": [f"{emotion}→励まし/共感が必要", "感情がポジティブに遷移"],
                "context": [f"{situation}という状況での判断", f"{place}という文脈"],
            }
            # axesに応じてaxis_evidenceを調整
            if "context" not in template["axes"]:
                axis_evidence.pop("context", None)

            item = {
                "layer": 5,
                "axes": template["axes"],
                "positive": True,
                "state0": {
                    "context": state0_str.split("、")[0] if "、" in state0_str else state0_str,
                    "emotion": emotion,
                },
                "action": template["action"],
                "state1": {
                    "context": state1_str.split("、")[0] if "、" in state1_str else state1_str,
                    "emotion": "自信" if "自信" in state1_str else "安心",
                },
                "axis_evidence": axis_evidence,
                "messages": [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ],
                "type": "causal",
            }
            data.append(item)

        # 負例の分布を均す（error_type枠埋め方式に変更）
        # レミ先輩推奨: hard negativeは負例の5%（全体の1.5%）
        hard_negative_count = max(1, int(negative_count * 0.05))
        normal_negative_count = negative_count - hard_negative_count

        # error_type枠埋め方式：各error_typeにクォータを設定（unsafe_actionを少し厚く）
        # 目標: 最小/最大 > 0.7 を達成
        error_type_quota = {
            "unsafe_action": max(1, int(normal_negative_count * 0.20)),  # 20%（厚め）
            "context_miss": max(1, int(normal_negative_count * 0.17)),  # 17%
            "logic_error": max(1, int(normal_negative_count * 0.17)),  # 17%
            "overconfident": max(1, int(normal_negative_count * 0.16)),  # 16%
            "emotion_mismatch": max(1, int(normal_negative_count * 0.15)),  # 15%
            "missing_reason": max(1, int(normal_negative_count * 0.15)),  # 15%
        }

        # 合計がnormal_negative_countになるように調整
        allocated_total = sum(error_type_quota.values())
        if allocated_total != normal_negative_count:
            diff = normal_negative_count - allocated_total
            # 差を均等に分配（最小値を維持）
            for i in range(abs(diff)):
                error_type = list(error_type_quota.keys())[i % len(error_type_quota)]
                if diff > 0:
                    error_type_quota[error_type] += 1
                else:
                    error_type_quota[error_type] = max(1, error_type_quota[error_type] - 1)

        # デバッグ: error_type_quotaを確認
        min_quota = min(error_type_quota.values())
        max_quota = max(error_type_quota.values())
        min_max_ratio = min_quota / max_quota if max_quota > 0 else 0
        print(f"[デバッグ] error_type_quota: {error_type_quota}, 最小/最大={min_max_ratio:.2f}")

        # 各error_typeのテンプレートを準備
        error_type_templates = {}
        for error_type in self.error_types:
            matching = [t for t in emotional_causal_negative if t.get("error_type") == error_type]
            if not matching:
                matching = emotional_causal_negative  # フォールバック
            error_type_templates[error_type] = matching

        # 各error_typeを枠埋め方式で生成（スロットテンプレート対応）
        # error_type_quotaを満たすまで生成を繰り返す
        error_type_generated = {etype: 0 for etype in self.error_types}

        for error_type in self.error_types:
            target_count = error_type_quota.get(error_type, 0)
            if target_count <= 0:
                continue

            templates = error_type_templates[error_type]
            if not templates:
                print(f"[WARN] {error_type}のテンプレートが空です")
                continue

            # クォータを満たすまで生成（最大リトライ回数あり）
            max_retries = target_count * 5  # 重複を考慮して5倍まで
            retry_count = 0

            while error_type_generated[error_type] < target_count and retry_count < max_retries:
                retry_count += 1
                template = random.choice(templates)

                # スロットテンプレートの場合、スロットを埋める
                if template.get("is_slot_template", False):
                    state0_str = self.fill_slots(template["state0"]["context"])
                    state1_str = (
                        self.fill_slots(template["state1"]["context"])
                        if "state1" in template
                        else "誤った反応"
                    )
                    question = self.fill_slots(template["question"])
                    answer = template["answer"]  # 固定の誤回答

                    emotion = random.choice(self.slots["emotion"])
                    axis_evidence = {
                        "logic": (
                            ["理由なし（結論のみ）"]
                            if error_type == "missing_reason"
                            else ["原因→結果の説明が必要"]
                        ),
                        "emotion": (
                            [f"{emotion}→励まし/共感が必要（しかし誤った反応）"]
                            if error_type == "emotion_mismatch"
                            else [f"{emotion}→励まし/共感が必要"]
                        ),
                    }
                    if "context" in template["axes"]:
                        situation = random.choice(self.slots["situation"])
                        place = random.choice(self.slots["place"])
                        axis_evidence["context"] = [f"{situation}という状況", f"{place}という文脈"]

                    # unsafe_actionとoverconfidentの特別処理
                    if error_type == "unsafe_action":
                        axis_evidence["logic"] = ["論理は合ってるが提案が危険"]
                        axis_evidence["context"] = [f"{place}という状況での判断ミス"]
                    elif error_type == "overconfident":
                        axis_evidence["logic"] = ["根拠ない断定（過剰な自信）"]
                        axis_evidence["context"] = ["重要な判断という状況での不適切な確信"]

                    item = {
                        "layer": 5,
                        "axes": template["axes"],
                        "positive": False,
                        "error_type": error_type,
                        "state0": {
                            "context": (
                                state0_str.split("、")[0] if "、" in state0_str else state0_str
                            ),
                            "emotion": emotion,
                        },
                        "action": template["action"],
                        "state1": {
                            "context": state1_str,
                            "emotion": "無視" if error_type == "emotion_mismatch" else emotion,
                        },
                        "axis_evidence": axis_evidence,
                        "messages": [
                            {"role": "user", "content": question},
                            {"role": "assistant", "content": answer},
                        ],
                        "type": "causal_error",
                    }
                else:
                    # 通常テンプレート
                    item = {
                        "layer": 5,
                        "axes": template["axes"],
                        "positive": False,
                        "error_type": error_type,
                        "state0": template["state0"],
                        "action": template["action"],
                        "state1": template["state1"],
                        "axis_evidence": template.get("axis_evidence", {}),
                        "messages": [
                            {"role": "user", "content": template["question"]},
                            {"role": "assistant", "content": template["answer"]},
                        ],
                        "type": "causal_error",
                    }
                data.append(item)
                error_type_generated[error_type] += 1

            # デバッグ: 各error_typeの生成数を確認
            if error_type_generated[error_type] < target_count:
                print(
                    f"[WARN] {error_type}: 目標{target_count}件に対して{error_type_generated[error_type]}件のみ生成（不足: {target_count - error_type_generated[error_type]}件）"
                )

        # レミ先輩推奨: hard negativeはLayer 5に20%、Layer 6に80%
        # Layer 5のhard negative（20%）
        layer5_hard_count = max(0, int(hard_negative_count * 0.2))
        for i in range(layer5_hard_count):
            template = random.choice(hard_negative_templates)
            item = {
                "layer": 5,
                "axes": template["axes"],
                "positive": False,
                "error_type": template["error_type"],
                "is_hard_negative": True,
                "state0": template["state0"],
                "action": template["action"],
                "state1": template["state1"],
                "axis_evidence": template.get("axis_evidence", {}),
                "messages": [
                    {"role": "user", "content": template["question"]},
                    {"role": "assistant", "content": template["answer"]},
                ],
                "type": "causal_error_hard",
            }
            data.append(item)

        # Layer 6のhard negativeはgenerate_layer_6_dataで処理

        return data

    def generate_layer_6_data(self, count: int) -> List[Dict]:
        """Layer 6: 統合層データ生成（3軸完全統合）。l6_* 名前空間でペアリング崩壊防止。"""
        data = []

        # Layer 6 専用名前空間（他層とスロット衝突防止、問いと答えで同一値を共有）
        layer6_slots = {
            "l6_time": self.slots["time"],
            "l6_place": self.slots["place"],
            "l6_role": self.slots["role"],
            "l6_task": self.slots["task"],
            "l6_emotion": self.slots["emotion"],
            "l6_situation": self.slots["situation"],
            "l6_minutes": self.slots["minutes"],
            "l6_n": self.slots["n"],
        }

        # 複合状況分析（スロット化）
        complex_analysis_templates = [
            (
                "{l6_time}、{l6_place}で{l6_role}が{l6_task}中。客が{l6_emotion}。どう対応？",
                "共感（{l6_emotion}）→優先順位（{l6_task}）→現場制約（{l6_place}）を考慮。解決策{l6_n}個提示。対話{l6_minutes}分継続。",
            ),
        ]

        # 多者間ダイナミクス（スロット化）
        multi_agent_dynamics_templates = [
            (
                "{l6_role}({l6_emotion})が{l6_task}中、{l6_role}が見ている → 行動予測は？",
                "介入を避ける可能性が高い。{l6_emotion}があり対立に巻き込まれたくない。沈黙または話題変更を試みるかも。",
            ),
        ]

        # 反事実的推論（スロット化）
        counterfactual_reasoning_templates = [
            (
                "もし{l6_time}、{l6_emotion}せずに冷静に対応していたら → 結果は？",
                "対話が{l6_minutes}分継続し、建設的な解決に至った可能性。感情的反応が選択肢を狭めた。",
            ),
        ]

        # メタ認知的判断（スロット化）
        meta_cognitive_templates = [
            (
                "{l6_situation}で判断するには情報が足りない → 適切な対応は？",
                "追加情報を収集する。推測で行動せず、確認を取る。不確実性を認めることが正しい判断。",
            ),
            (
                "{l6_place}で{l6_role}の言葉と非言語が矛盾している → 適切な対応は？",
                "非言語を優先しつつ、直接確認を取る。「{l6_emotion}に見えるけど、本当に大丈夫？」など。",
            ),
        ]

        all_templates = (
            complex_analysis_templates
            + multi_agent_dynamics_templates
            + counterfactual_reasoning_templates
            + meta_cognitive_templates
        )

        # ManaOS向け秘書タスク（Layer 6に追加）
        manaos_tasks = [
            {
                "question": "作業が詰まって焦ってる。どうすればいい？",
                "answer": "焦る気持ちはわかります。まず優先順位を整理しましょう。緊急度と重要度で分類すると効率的です。",
                "state0": {"context": "作業が詰まっている", "emotion": "焦り"},
                "action": "優先順位を整理し、感情ケアを提供",
                "state1": {"context": "タスクが整理された、優先順位が明確", "emotion": "安心"},
                "axis_evidence": {
                    "logic": ["原因→結果の説明が必要", "整理→効率化の因果"],
                    "emotion": ["焦り→感情ケアが必要", "感情が焦りから安心に遷移"],
                    "context": ["作業が詰まっているという状況での判断"],
                },
            },
            {
                "question": "クレーム対応中、客が激怒している。どう対応すべき？",
                "answer": "まずはお客様の気持ちを受け止めます。その後、具体的な解決策を提示しましょう。感情的にならず、冷静に対応することが重要です。",
                "state0": {"context": "クレーム対応中、客が激怒", "emotion": "困惑"},
                "action": "感情を受け止め、冷静に解決策を提示",
                "state1": {"context": "クレームが解決、関係が修復", "emotion": "安心"},
                "axis_evidence": {
                    "logic": ["原因→結果の説明が必要", "適切な対応→解決の因果"],
                    "emotion": ["困惑→感情調整が必要", "感情が困惑から安心に遷移"],
                    "context": ["クレーム対応という状況での判断"],
                },
            },
        ]

        # レミ先輩推奨: Layer 6のhard negativeは80%（残りは通常データ）
        # 負例率30%なので、Layer 6の負例 = count * 0.3
        # hard negative = 負例の5% = count * 0.3 * 0.05 = count * 0.015
        # ただし、hard negativeの80%がLayer 6なので、Layer 6のhard negative = count * 0.015 * 0.8
        layer6_negative_count = int(count * 0.3)
        layer6_hard_negative_count = max(
            1, int(layer6_negative_count * 0.05 * 0.8)
        )  # hard negativeの80%
        normal_count = int(count * 0.7)  # 正例
        manaos_count = int(count * 0.2)  # ManaOSタスク（正例に含む）

        for _ in range(normal_count):
            template, answer_template = random.choice(all_templates)
            question, answer = self.fill_slots_shared(
                template, answer_template, slot_dict=layer6_slots
            )

            # state遷移情報を生成（観測可能な変化）
            n = random.choice(self.slots["n"])
            n2 = random.choice(self.slots["n2"])
            minutes = random.choice(self.slots["minutes"])
            place = random.choice(self.slots["place"])
            emotion = random.choice(self.slots["emotion"])
            task = random.choice(self.slots["task"])

            data.append(
                {
                    "layer": 6,
                    "axes": ["logic", "emotion", "context"],  # 必ず3軸
                    "positive": True,
                    "state0": {"context": f"{place}で{task}中", "emotion": emotion},
                    "action": "適切な対応",
                    "state1": {
                        "context": f"解決策{n}個提示、対話{minutes}分継続",
                        "emotion": "安心",
                    },
                    "axis_evidence": {
                        "logic": ["複合状況の分析", "優先順位の判断"],
                        "emotion": ["感情状態の考慮", f"{emotion}への共感"],
                        "context": ["状況に応じた判断", f"{place}という現場制約"],
                    },
                    "messages": [
                        {"role": "user", "content": question},
                        {"role": "assistant", "content": answer},
                    ],
                    "type": "integration",
                }
            )

        # ManaOS向けタスクを追加
        for _ in range(manaos_count):
            template = random.choice(manaos_tasks)
            data.append(
                {
                    "layer": 6,
                    "axes": ["logic", "emotion", "context"],
                    "positive": True,
                    "state0": template["state0"],
                    "action": template["action"],
                    "state1": template["state1"],
                    "axis_evidence": template.get("axis_evidence", {}),
                    "messages": [
                        {"role": "user", "content": template["question"]},
                        {"role": "assistant", "content": template["answer"]},
                    ],
                    "type": "integration_manaos",
                }
            )

        # レミ先輩推奨: Layer 6にhard negativeを追加（error_type配分: unsafe_action:40%, context_miss:30%, overconfident:30%）
        layer6_hard_negative = [
            {
                "question": "クレーム対応中、客が激怒している",
                "answer": "お客様、落ち着いてください。こちらに非はありません。",
                "error_type": "unsafe_action",
                "axis_evidence": {
                    "logic": ["論理は合ってるが提案が危険"],
                    "emotion": ["感情は読めてるが対応が不適切"],
                    "context": ["クレーム対応という状況での判断ミス"],
                },
            },
            {
                "question": "重要な判断をしなければならない",
                "answer": "間違いなく正しいです。絶対にこれが最適解です。他の選択肢は考えなくて良いです。",
                "error_type": "overconfident",
                "axis_evidence": {
                    "logic": ["根拠ない断定（過剰な自信）"],
                    "context": ["重要な判断という状況での不適切な確信"],
                },
            },
            {
                "question": "作業が詰まって焦ってる",
                "answer": "優先順位を整理しましょう。",
                "error_type": "context_miss",
                "axis_evidence": {
                    "logic": ["論理は合ってるが文脈を無視"],
                    "emotion": ["感情（焦り）への配慮がない"],
                    "context": ["作業が詰まっているという状況を無視"],
                },
            },
        ]

        # error_type配分: unsafe_action:40%, context_miss:30%, overconfident:30%
        unsafe_action_count = max(1, int(layer6_hard_negative_count * 0.4))
        context_miss_count = max(1, int(layer6_hard_negative_count * 0.3))
        overconfident_count = layer6_hard_negative_count - unsafe_action_count - context_miss_count

        # unsafe_action
        unsafe_templates = [t for t in layer6_hard_negative if t["error_type"] == "unsafe_action"]
        for _ in range(unsafe_action_count):
            template = random.choice(unsafe_templates if unsafe_templates else layer6_hard_negative)
            data.append(
                {
                    "layer": 6,
                    "axes": ["logic", "emotion", "context"],
                    "positive": False,
                    "error_type": template["error_type"],
                    "is_hard_negative": True,
                    "axis_evidence": template.get("axis_evidence", {}),
                    "messages": [
                        {"role": "user", "content": template["question"]},
                        {"role": "assistant", "content": template["answer"]},
                    ],
                    "type": "integration_error_hard",
                }
            )

        # context_miss
        context_miss_templates = [
            t for t in layer6_hard_negative if t["error_type"] == "context_miss"
        ]
        for _ in range(context_miss_count):
            template = random.choice(
                context_miss_templates if context_miss_templates else layer6_hard_negative
            )
            data.append(
                {
                    "layer": 6,
                    "axes": ["logic", "emotion", "context"],
                    "positive": False,
                    "error_type": template["error_type"],
                    "is_hard_negative": True,
                    "axis_evidence": template.get("axis_evidence", {}),
                    "messages": [
                        {"role": "user", "content": template["question"]},
                        {"role": "assistant", "content": template["answer"]},
                    ],
                    "type": "integration_error_hard",
                }
            )

        # overconfident
        overconfident_templates = [
            t for t in layer6_hard_negative if t["error_type"] == "overconfident"
        ]
        for _ in range(overconfident_count):
            template = random.choice(
                overconfident_templates if overconfident_templates else layer6_hard_negative
            )
            data.append(
                {
                    "layer": 6,
                    "axes": ["logic", "emotion", "context"],
                    "positive": False,
                    "error_type": template["error_type"],
                    "is_hard_negative": True,
                    "axis_evidence": template.get("axis_evidence", {}),
                    "messages": [
                        {"role": "user", "content": template["question"]},
                        {"role": "assistant", "content": template["answer"]},
                    ],
                    "type": "integration_error_hard",
                }
            )

        return data

    def normalize_message(self, message: str, for_hash: bool = True) -> str:
        """メッセージを正規化（重複検知用）

        for_hash=True: 重複判定用（数字・固有名詞を残す）
        for_hash=False: 完全正規化（将来的な使用）
        """
        import re

        # 空白・句読点・全角半角を正規化（数字・固有名詞は残す）
        normalized = message.strip()
        # 連続する空白を1つに
        normalized = re.sub(r"\s+", " ", normalized)
        # 全角空白を半角に
        normalized = normalized.replace("　", " ")

        # レミ先輩推奨: 数字や固有名詞は残す（重複判定の精度向上）
        # 絵文字は残す（感情表現の違いを区別）
        # 注: 極端な正規化（数字削除、名詞置換など）は行わない

        return normalized

    def get_message_hash(self, messages: List[Dict]) -> str:
        """messagesの正規化ハッシュを取得"""
        import hashlib

        # messagesを正規化してハッシュ
        normalized_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = self.normalize_message(msg.get("content", ""))
            normalized_messages.append(f"{role}:{content}")
        messages_str = "|".join(normalized_messages)
        return hashlib.md5(messages_str.encode("utf-8")).hexdigest()

    def deduplicate_data(self, all_data: List[Dict]) -> List[Dict]:
        """重複データを除去（正規化ハッシュで、目標: 重複率 < 3%）"""
        seen_hashes = set()
        unique_data = []
        duplicate_count = 0

        for item in all_data:
            messages = item.get("messages", [])
            if not messages:
                continue

            msg_hash = self.get_message_hash(messages)
            if msg_hash not in seen_hashes:
                seen_hashes.add(msg_hash)
                unique_data.append(item)
            else:
                duplicate_count += 1

        total = len(all_data)
        duplicate_ratio = duplicate_count / total if total > 0 else 0

        if duplicate_count > 0:
            print(
                f"  重複除去: {duplicate_count}件を削除（重複率: {duplicate_ratio:.1%}、残り: {len(unique_data)}件）"
            )
            if duplicate_ratio > 0.03:
                print(f"  警告: 重複率が3%を超えています（目標: <3%）")

        return unique_data

    def generate_dataset_stats(self, all_data: List[Dict]) -> Dict[str, Any]:
        """データ分布レポート生成"""
        from collections import Counter

        stats = {
            "total": len(all_data),
            "by_layer": {},
            "by_axes": Counter(),
            "axes_combinations": Counter(),
            "positive_negative": {"positive": 0, "negative": 0},
            "error_type_distribution": Counter(),
            "layer_error_type_cross": {},  # layer×error_typeクロス集計
            "axes_avg_token_length": {},  # axes組み合わせ×平均トークン長
            "avg_token_length": {"user": 0, "assistant": 0},
            "axis_evidence_coverage": {"with_evidence": 0, "without_evidence": 0},
            "duplicate_messages": [],  # 重複検知用（messagesのハッシュ）
        }

        total_user_tokens = 0
        total_assistant_tokens = 0
        message_hashes = Counter()  # 重複検知用

        for item in all_data:
            layer = item.get("layer")
            axes = item.get("axes", [])
            positive = item.get("positive", True)
            error_type = item.get("error_type")
            axis_evidence = item.get("axis_evidence", {})

            # 層別統計
            if layer not in stats["by_layer"]:
                stats["by_layer"][layer] = {"total": 0, "positive": 0, "negative": 0}
            stats["by_layer"][layer]["total"] += 1
            if positive:
                stats["by_layer"][layer]["positive"] += 1
            else:
                stats["by_layer"][layer]["negative"] += 1

            # 軸別統計
            for axis in axes:
                stats["by_axes"][axis] += 1

            # 軸の組み合わせ統計
            axes_key = ",".join(sorted(axes))
            stats["axes_combinations"][axes_key] += 1

            # 正例/負例統計
            if positive:
                stats["positive_negative"]["positive"] += 1
            else:
                stats["positive_negative"]["negative"] += 1
                if error_type:
                    stats["error_type_distribution"][error_type] += 1

            # layer×error_typeクロス集計
            if not positive and error_type:
                key = f"layer_{layer}_error_{error_type}"
                if key not in stats["layer_error_type_cross"]:
                    stats["layer_error_type_cross"][key] = 0
                stats["layer_error_type_cross"][key] += 1

            # トークン長統計（簡易版：文字数）
            messages = item.get("messages", [])
            if messages:
                user_content = messages[0].get("content", "")
                assistant_content = messages[-1].get("content", "")
                user_len = len(user_content)
                assistant_len = len(assistant_content)
                total_user_tokens += user_len
                total_assistant_tokens += assistant_len

                # axes組み合わせ×平均トークン長
                axes_key = ",".join(sorted(axes))
                if axes_key not in stats["axes_avg_token_length"]:
                    stats["axes_avg_token_length"][axes_key] = {"user": [], "assistant": []}
                stats["axes_avg_token_length"][axes_key]["user"].append(user_len)
                stats["axes_avg_token_length"][axes_key]["assistant"].append(assistant_len)

            # 重複検知（messagesのハッシュ）
            import hashlib

            messages_str = json.dumps(messages, sort_keys=True, ensure_ascii=False)
            msg_hash = hashlib.md5(messages_str.encode("utf-8")).hexdigest()
            message_hashes[msg_hash] += 1
            if message_hashes[msg_hash] > 1:
                stats["duplicate_messages"].append(
                    {
                        "hash": msg_hash,
                        "count": message_hashes[msg_hash],
                        "layer": layer,
                    }
                )

            # axis_evidenceカバレッジ
            if axis_evidence:
                stats["axis_evidence_coverage"]["with_evidence"] += 1
            else:
                stats["axis_evidence_coverage"]["without_evidence"] += 1

        # 平均トークン長
        if len(all_data) > 0:
            stats["avg_token_length"]["user"] = total_user_tokens / len(all_data)
            stats["avg_token_length"]["assistant"] = total_assistant_tokens / len(all_data)

        # Counterをdictに変換
        stats["by_axes"] = dict(stats["by_axes"])
        stats["axes_combinations"] = dict(stats["axes_combinations"])
        stats["error_type_distribution"] = dict(stats["error_type_distribution"])

        # axes×平均トークン長を計算
        for axes_key in stats["axes_avg_token_length"]:
            user_lens = stats["axes_avg_token_length"][axes_key]["user"]
            assistant_lens = stats["axes_avg_token_length"][axes_key]["assistant"]
            stats["axes_avg_token_length"][axes_key] = {
                "user_avg": sum(user_lens) / len(user_lens) if user_lens else 0,
                "assistant_avg": sum(assistant_lens) / len(assistant_lens) if assistant_lens else 0,
                "count": len(user_lens),
            }

        # 重複メッセージの重複を除去（最初の1件だけ残す）
        unique_duplicates = {}
        for dup in stats["duplicate_messages"]:
            if dup["hash"] not in unique_duplicates:
                unique_duplicates[dup["hash"]] = dup
        stats["duplicate_messages"] = list(unique_duplicates.values())
        stats["duplicate_count"] = len([h for h in message_hashes.values() if h > 1])

        return stats

    def generate_dataset(
        self,
        total_count: int,
        output_path: str,
        target_unique: Optional[int] = None,
        existing_data: Optional[List[Dict]] = None,
        target_negative_ratio: Optional[float] = None,
        target_layer2_count: Optional[int] = None,
        target_error_type_min_max_ratio: Optional[float] = None,
    ) -> Dict[str, Any]:
        """全層データセット生成（目標件数に達するまで生成を回す）"""
        print("=" * 60)
        print("CASTLE-EX 学習データ生成")
        print("=" * 60)

        # 既存データがある場合はそれをベースにする
        if existing_data:
            all_data = existing_data.copy()
            print(f"既存データ: {len(all_data)}件を保持")
            print(f"追加生成目標: {total_count - len(all_data)}件")

            # 既存データの統計
            existing_negative = sum(1 for item in all_data if not item.get("positive", True))
            existing_positive = len(all_data) - existing_negative
            existing_negative_ratio = existing_negative / len(all_data) if len(all_data) > 0 else 0

            print(
                f"既存: positive={existing_positive}, negative={existing_negative} ({existing_negative_ratio:.1%})"
            )

            # 目標負例率が指定されている場合、追加生成で調整
            if target_negative_ratio:
                target_total_negative = int(len(all_data) * target_negative_ratio)
                additional_negative_needed = max(0, target_total_negative - existing_negative)
                print(
                    f"目標負例率: {target_negative_ratio:.1%} → 追加負例必要: {additional_negative_needed}件"
                )
        else:
            all_data = []
            print(f"総データ数目標: {total_count}")

        # 目標ユニーク数が指定されていない場合は、total_countの75%を目標とする
        if target_unique is None:
            target_unique = int(total_count * 0.75)
            if existing_data:
                target_unique = max(target_unique, len(all_data))

        if target_unique:
            print(f"ユニーク目標: {target_unique}以上")

        layer_counts = {}
        max_iterations = 10  # 最大10回までリトライ
        iteration = 0

        # 各層のデータ数計算（負例枠埋めモードの前に計算）
        # まず、基本のremaining_countを計算（既存データがある場合はそれを除く）
        base_remaining = total_count - len(all_data) if existing_data else total_count

        # Layer 2を先に計算（target_layer2_countが指定されている場合）
        if target_layer2_count:
            existing_layer2 = (
                sum(1 for item in all_data if item.get("layer") == 2) if existing_data else 0
            )
            layer2_needed = max(0, target_layer2_count - existing_layer2)
            layer_counts[2] = layer2_needed
            print(
                f"Layer 2: 既存{existing_layer2}件 → 目標{target_layer2_count}件（追加必要: {layer2_needed}件）"
            )
            if layer2_needed > 0:
                base_remaining = max(0, base_remaining - layer2_needed)
        else:
            # Layer 2も通常比率で計算
            layer_counts[2] = max(0, int(base_remaining * self.layer_distribution[2]))

        # 他の層のデータ数計算（Layer 2を除く、またはLayer 2がtargetで指定されていない場合）
        for layer, ratio in self.layer_distribution.items():
            if layer == 2 and target_layer2_count:
                continue  # Layer 2は既に計算済み
            count = max(0, int(base_remaining * ratio))
            layer_counts[layer] = count

        # デバッグ: layer_countsを確認
        print(f"\n[デバッグ] layer_counts: {layer_counts}")

        # remaining_countを負例枠埋めモード用に更新（後で調整される）
        remaining_count = base_remaining

        # 各層のデータ生成
        generation_methods = {
            0: self.generate_layer_0_data,
            1: self.generate_layer_1_data,
            2: self.generate_layer_2_data,
            3: self.generate_layer_3_data,
            4: self.generate_layer_4_data,
            5: self.generate_layer_5_data,
            6: self.generate_layer_6_data,
        }

        layer_names = {
            0: "公理層",
            1: "操作層",
            2: "関係層",
            3: "感情基礎層",
            4: "文脈基礎層",
            5: "因果層",
            6: "統合層",
        }

        # 負例枠埋めモード（target_negative_ratioが指定されている場合）
        if target_negative_ratio and existing_data:
            # 目標負例数を計算（最終的なtotal_countベース）
            target_total_negative = int(total_count * target_negative_ratio)
            existing_negative = sum(1 for item in all_data if not item.get("positive", True))
            additional_negative_needed = max(0, target_total_negative - existing_negative)

            if additional_negative_needed > 0:
                print(
                    f"\n[負例枠埋めモード] 追加負例: {additional_negative_needed}件を生成（既存: {existing_negative}件 → 目標: {target_total_negative}件）"
                )

                # 既存データと重複しないものだけ追加するループ
                existing_hashes = {
                    self.get_message_hash(item.get("messages", [])) for item in all_data
                }
                new_negative = []
                negative_generation_iterations = 0
                max_negative_iterations = 20  # 最大20回までリトライ

                while (
                    len(new_negative) < additional_negative_needed
                    and negative_generation_iterations < max_negative_iterations
                ):
                    negative_generation_iterations += 1
                    # Layer 5の負例を生成（必要数の3倍を生成して重複除去）
                    batch_size = min(
                        (additional_negative_needed - len(new_negative)) * 3, remaining_count * 2
                    )
                    if batch_size <= 0:
                        break

                    negative_batch = self.generate_layer_5_data(batch_size)
                    negative_batch = [
                        item for item in negative_batch if not item.get("positive", True)
                    ]

                    # 重複除去
                    negative_batch = self.deduplicate_data(negative_batch)

                    # 既存データと重複しないものだけ追加
                    for item in negative_batch:
                        if len(new_negative) >= additional_negative_needed:
                            break
                        msg_hash = self.get_message_hash(item.get("messages", []))
                        if msg_hash not in existing_hashes:
                            new_negative.append(item)
                            existing_hashes.add(msg_hash)

                    if len(new_negative) >= additional_negative_needed:
                        break

                all_data.extend(new_negative)
                current_negative = sum(1 for item in all_data if not item.get("positive", True))
                current_ratio = current_negative / len(all_data) if len(all_data) > 0 else 0
                print(
                    f"  負例追加: {len(new_negative)}件（累計負例: {current_negative}件、負例率: {current_ratio:.1%}、目標: {target_total_negative}件）"
                )

                # まだ目標に届いていない場合は追加生成を続ける
                if current_negative < target_total_negative:
                    additional_needed = target_total_negative - current_negative
                    print(f"  追加負例が必要: {additional_needed}件（継続生成）")

                # 残りの枠を正例で埋める（Layer 5から減らす）
                remaining_count = remaining_count - len(new_negative)
                layer_counts[5] = max(0, layer_counts[5] - len(new_negative))

        # 目標件数に達するまで生成を回す
        # Layer 2の生成数を保持（負例追加で減らさない）
        layer2_target = layer_counts.get(2, 0)
        existing_layer2_before = sum(1 for item in all_data if item.get("layer") == 2)
        if layer2_target > 0:
            print(
                f"\n[Layer 2特別処理] 目標: {layer2_target}件（既存: {existing_layer2_before}件、追加必要: {layer2_target - existing_layer2_before}件）"
            )
            # Layer 2の生成数を強制的に設定（他の処理で上書きされないように）
            layer_counts[2] = layer2_target

            # Layer 2を優先的に生成（生成ループの前に実行）
            layer2_needed = layer2_target - existing_layer2_before
            if layer2_needed > 0:
                print(f"\n[Layer 2優先生成] {layer2_needed}件を生成開始...")
                existing_hashes = {
                    self.get_message_hash(item.get("messages", [])) for item in all_data
                }
                layer2_generated = 0
                layer2_max_retries = layer2_needed * 5  # 重複を考慮して5倍まで
                layer2_retry_count = 0

                while layer2_generated < layer2_needed and layer2_retry_count < layer2_max_retries:
                    layer2_retry_count += 1
                    # Layer 2のデータを生成
                    layer2_batch = self.generate_layer_2_data(
                        min(layer2_needed - layer2_generated + 10, layer2_needed * 2)
                    )

                    # 重複除去
                    layer2_batch = self.deduplicate_data(layer2_batch)

                    # 既存データと重複しないものだけ追加
                    for item in layer2_batch:
                        if layer2_generated >= layer2_needed:
                            break
                        msg_hash = self.get_message_hash(item.get("messages", []))
                        if msg_hash not in existing_hashes:
                            all_data.append(item)
                            existing_hashes.add(msg_hash)
                            layer2_generated += 1

                    if layer2_generated >= layer2_needed:
                        break

                print(f"  [OK] Layer 2: {layer2_generated}件生成（目標: {layer2_needed}件）")
                if layer2_generated < layer2_needed:
                    print(
                        f"  [WARN] Layer 2: 目標に届きませんでした（生成: {layer2_generated}件、不足: {layer2_needed - layer2_generated}件）"
                    )

        while len(all_data) < target_unique and iteration < max_iterations:
            iteration += 1
            print(f"\n--- 生成サイクル {iteration} ---")

            cycle_data = []
            # Layer 2を優先的に処理（目標数に達するまで生成を続ける）
            if layer2_target > 0:
                existing_layer2 = sum(1 for item in all_data if item.get("layer") == 2)
                layer2_count = max(0, layer2_target - existing_layer2)
                if layer2_count > 0:
                    print(
                        f"\nLayer 2 ({layer_names[2]}) 生成中... (既存: {existing_layer2}件、目標: {layer2_target}件、追加必要: {layer2_count}件)"
                    )
                    try:
                        layer2_data = generation_methods[2](layer2_count)
                        cycle_data.extend(layer2_data)
                        print(f"  [OK] {len(layer2_data)}件生成（目標: {layer2_count}件）")
                        self.reject_stats["total_generated"] += len(layer2_data)
                    except Exception as e:
                        print(f"  [ERROR] Layer 2生成エラー: {e}")
                        import traceback

                        traceback.print_exc()
                        self.reject_stats["total_rejected"] += layer2_count
                        if "生成エラー" not in self.reject_stats["reject_reasons"]:
                            self.reject_stats["reject_reasons"]["生成エラー"] = 0
                        self.reject_stats["reject_reasons"]["生成エラー"] += layer2_count

            # 他の層を処理（Layer 2は除外）
            for layer in sorted(generation_methods.keys()):
                if layer == 2:  # Layer 2は既に処理済み
                    continue
                count = layer_counts.get(layer, 0)
                if count <= 0:
                    continue  # 生成数が0以下の場合はスキップ
                print(f"\nLayer {layer} ({layer_names[layer]}) 生成中... (目標: {count}件)")
                try:
                    layer_data = generation_methods[layer](count)
                    cycle_data.extend(layer_data)
                    print(f"  [OK] {len(layer_data)}件生成（目標: {count}件）")
                    self.reject_stats["total_generated"] += len(layer_data)
                except Exception as e:
                    print(f"  [ERROR] Layer {layer}生成エラー: {e}")
                    import traceback

                    traceback.print_exc()
                    self.reject_stats["total_rejected"] += count
                    if "生成エラー" not in self.reject_stats["reject_reasons"]:
                        self.reject_stats["reject_reasons"]["生成エラー"] = 0
                    self.reject_stats["reject_reasons"]["生成エラー"] += count

            # 重複除去（正規化ハッシュで）
            cycle_data = self.deduplicate_data(cycle_data)

            # 既存データと重複しないものだけ追加
            existing_hashes = {self.get_message_hash(item.get("messages", [])) for item in all_data}
            new_items = []
            duplicate_examples = []  # デバッグ用：重複の例を保存（最大5件）

            for item in cycle_data:
                msg_hash = self.get_message_hash(item.get("messages", []))
                if msg_hash not in existing_hashes:
                    new_items.append(item)
                    existing_hashes.add(msg_hash)
                else:
                    self.reject_stats["total_rejected"] += 1
                    if "重複" not in self.reject_stats["reject_reasons"]:
                        self.reject_stats["reject_reasons"]["重複"] = 0
                    self.reject_stats["reject_reasons"]["重複"] += 1

                    # デバッグ用：重複の例を保存（最初の5件）
                    if len(duplicate_examples) < 5:
                        duplicate_examples.append(
                            {
                                "messages": item.get("messages", []),
                                "hash": msg_hash,
                                "layer": item.get("layer"),
                                "type": item.get("type", "unknown"),
                            }
                        )

            # 重複の例をreject統計に追加（デバッグ用）
            if duplicate_examples:
                self.reject_stats["duplicate_examples"] = duplicate_examples

            all_data.extend(new_items)
            print(f"  新規追加: {len(new_items)}件（累計: {len(all_data)}件）")

            if len(all_data) >= target_unique:
                print(f"\n[OK] 目標ユニーク数 {target_unique} に到達しました")
                break

        if len(all_data) < target_unique:
            print(
                f"\n[WARN] 目標ユニーク数 {target_unique} に到達できませんでした（現在: {len(all_data)}件）"
            )

        # 最終的な重複除去（念のため）
        all_data = self.deduplicate_data(all_data)

        # error_type分布の調整（target_error_type_min_max_ratioが指定されている場合）
        if target_error_type_min_max_ratio and target_error_type_min_max_ratio > 0:
            print(f"\n[error_type分布調整] 目標最小/最大比: {target_error_type_min_max_ratio:.2f}")

            # 現在のerror_type分布を計算
            error_type_counts = {}
            for item in all_data:
                if not item.get("positive", True):
                    error_type = item.get("error_type")
                    if error_type:
                        error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

            if error_type_counts:
                max_count = max(error_type_counts.values())
                min_count = min(error_type_counts.values())
                current_ratio = min_count / max_count if max_count > 0 else 0

                print(
                    f"  現在: 最小={min_count}件、最大={max_count}件、最小/最大={current_ratio:.2f}"
                )

                if current_ratio < target_error_type_min_max_ratio:
                    # 目標最小数を計算
                    target_min = int(max_count * target_error_type_min_max_ratio)
                    print(
                        f"  目標最小数: {target_min}件（最大{max_count}件の{target_error_type_min_max_ratio:.1%}）"
                    )

                    # 不足しているerror_typeを特定
                    existing_hashes = {
                        self.get_message_hash(item.get("messages", [])) for item in all_data
                    }
                    additional_negative = []

                    # error_type別のテンプレートを準備（generate_layer_5_dataの内部定義を再利用）
                    # emotional_causal_negativeの定義を参照するため、一時的にgenerate_layer_5_dataを呼び出して構造を確認
                    # 実際には、generate_layer_5_data内のemotional_causal_negativeを直接参照できないため、
                    # generate_layer_5_dataを呼び出して該当error_typeを抽出する方法を使う

                    for error_type, current_count in error_type_counts.items():
                        if current_count < target_min:
                            needed = target_min - current_count
                            print(
                                f"  {error_type}: {current_count}件 → {target_min}件（+{needed}件必要）"
                            )

                            # 特定のerror_typeを直接生成する
                            # generate_layer_5_dataを大量に呼び出して該当error_typeを抽出
                            max_retries = needed * 20  # 重複を考慮して20倍まで
                            retry_count = 0
                            generated = 0

                            while generated < needed and retry_count < max_retries:
                                retry_count += 1

                                # バッチ生成（必要数の10倍を生成して該当error_typeを抽出）
                                # error_typeの出現率を考慮して、より多くのデータを生成
                                batch_size = min(needed - generated + 300, needed * 20)
                                batch = self.generate_layer_5_data(batch_size)

                                # 該当error_typeの負例だけを抽出
                                batch = [
                                    item
                                    for item in batch
                                    if not item.get("positive", True)
                                    and item.get("error_type") == error_type
                                ]

                                if not batch:
                                    # 該当error_typeが生成されなかった場合は、さらに大きなバッチで再試行
                                    if retry_count % 10 == 0:
                                        print(
                                            f"    [リトライ {retry_count}] {error_type}が見つかりません。より大きなバッチで再試行..."
                                        )
                                    continue

                                # 重複除去
                                batch = self.deduplicate_data(batch)

                                # 既存データと重複しないものだけ追加
                                for item in batch:
                                    if generated >= needed:
                                        break
                                    msg_hash = self.get_message_hash(item.get("messages", []))
                                    if msg_hash not in existing_hashes:
                                        additional_negative.append(item)
                                        existing_hashes.add(msg_hash)
                                        generated += 1

                                if generated >= needed:
                                    break

                                # 進捗表示（10回ごと）
                                if retry_count % 10 == 0:
                                    print(
                                        f"    [進捗] {generated}/{needed}件生成済み（リトライ: {retry_count}回）"
                                    )

                            print(f"    → {generated}件追加（目標: {needed}件）")

                    if additional_negative:
                        all_data.extend(additional_negative)
                        print(f"  [OK] error_type分布調整: {len(additional_negative)}件追加")

                        # 調整後の分布を確認
                        error_type_counts_after = {}
                        for item in all_data:
                            if not item.get("positive", True):
                                error_type = item.get("error_type")
                                if error_type:
                                    error_type_counts_after[error_type] = (
                                        error_type_counts_after.get(error_type, 0) + 1
                                    )

                        if error_type_counts_after:
                            max_after = max(error_type_counts_after.values())
                            min_after = min(error_type_counts_after.values())
                            ratio_after = min_after / max_after if max_after > 0 else 0
                            print(
                                f"  調整後: 最小={min_after}件、最大={max_after}件、最小/最大={ratio_after:.2f}"
                            )

        # シャッフル
        random.shuffle(all_data)

        # JSONL形式で保存
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for item in all_data:
                # 拡張JSONL形式：メタデータを含める
                output_item = {
                    "layer": item.get("layer"),
                    "axes": item.get("axes", []),
                    "positive": item.get("positive", True),
                    "messages": item["messages"],
                }
                # state遷移情報がある場合は追加
                if "state0" in item:
                    output_item["state0"] = item["state0"]
                if "action" in item:
                    output_item["action"] = item["action"]
                if "state1" in item:
                    output_item["state1"] = item["state1"]
                # axis_evidenceがある場合は追加
                if "axis_evidence" in item:
                    output_item["axis_evidence"] = item["axis_evidence"]
                # 負例の場合、error_typeを追加
                if not item.get("positive", True) and "error_type" in item:
                    output_item["error_type"] = item["error_type"]
                f.write(json.dumps(output_item, ensure_ascii=False) + "\n")

        # reject統計を保存
        reject_stats_file = output_file.parent / f"{output_file.stem}_reject_stats.json"
        with open(reject_stats_file, "w", encoding="utf-8") as f:
            json.dump(self.reject_stats, f, ensure_ascii=False, indent=2)
        print(f"\n[OK] reject統計を保存: {reject_stats_file}")

        # データ分布レポート生成
        stats_file = output_file.parent / f"{output_file.stem}_stats.json"
        dataset_stats = self.generate_dataset_stats(all_data)
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(dataset_stats, f, ensure_ascii=False, indent=2)

        print(f"データ分布レポート: {stats_file}")

        # 統計情報
        stats = {
            "total": len(all_data),
            "by_layer": {
                layer: len([d for d in all_data if d["layer"] == layer]) for layer in range(7)
            },
            "by_type": {},
        }

        for item in all_data:
            item_type = item.get("type", "unknown")
            stats["by_type"][item_type] = stats["by_type"].get(item_type, 0) + 1

        print("\n" + "=" * 60)
        print("生成完了")
        print("=" * 60)
        print(f"出力ファイル: {output_path}")
        print(f"総データ数: {stats['total']}")
        layer_names = {
            0: "公理層",
            1: "操作層",
            2: "関係層",
            3: "感情基礎層",
            4: "文脈基礎層",
            5: "因果層",
            6: "統合層",
        }

        print("\n層別内訳:")
        for layer, count in sorted(stats["by_layer"].items()):
            print(f"  Layer {layer} ({layer_names.get(layer, '不明')}): {count}件")

        return stats


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="CASTLE-EX学習データ生成ツール")
    parser.add_argument(
        "--count", type=int, default=2000, help="生成するデータ数（目標、デフォルト: 2000）"
    )
    parser.add_argument(
        "--target-unique",
        type=int,
        default=None,
        help="目標ユニーク数（指定しない場合はcount*0.75）",
    )
    parser.add_argument(
        "--existing", type=str, default=None, help="既存データファイル（追加生成モード）"
    )
    parser.add_argument(
        "--target-negative-ratio",
        type=float,
        default=None,
        help="目標負例率（既存データがある場合に有効）",
    )
    parser.add_argument(
        "--target-layer2-count",
        type=int,
        default=None,
        help="目標Layer2件数（既存データがある場合に有効）",
    )
    parser.add_argument(
        "--target-error-type-ratio",
        type=float,
        default=None,
        help="目標error_type最小/最大比（0.7推奨）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="castle_ex_dataset.jsonl",
        help="出力ファイルパス（デフォルト: castle_ex_dataset.jsonl）",
    )
    parser.add_argument("--seed", type=int, default=42, help="ランダムシード（デフォルト: 42）")

    args = parser.parse_args()

    generator = CastleEXDataGenerator(random_seed=args.seed)

    # 既存データの読み込み
    existing_data = None
    if args.existing:
        from pathlib import Path

        existing_file = Path(args.existing)
        if existing_file.exists():
            with open(existing_file, "r", encoding="utf-8") as f:
                existing_data = [json.loads(line) for line in f if line.strip()]
            print(f"既存データを読み込み: {len(existing_data)}件")
        else:
            print(f"警告: 既存データファイルが見つかりません: {args.existing}")

    stats = generator.generate_dataset(
        args.count,
        args.output,
        target_unique=args.target_unique,
        existing_data=existing_data,
        target_negative_ratio=args.target_negative_ratio,
        target_layer2_count=args.target_layer2_count,
        target_error_type_min_max_ratio=args.target_error_type_ratio,
    )

    print("\n[OK] データ生成が完了しました")


if __name__ == "__main__":
    main()
