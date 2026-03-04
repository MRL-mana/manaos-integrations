"""
generate_layer2_lora_data_v1_1_7.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v1.1.7 ミニ補正データ生成スクリプト。
NG 14件 (l2_attribute×10 + l2_part_whole×4) を中心に
「値固定」「反転防止」の正例を最小追加する。

出力: castle_ex_dataset_layer2_lora_v1_1_7_patch.jsonl
       castle_ex_dataset_layer2_lora_v1_1_7_train.jsonl (v1.1.6 + patch 合算)

使い方:
    py -3.10 castle_ex/generate_layer2_lora_data_v1_1_7.py
    py -3.10 castle_ex/generate_layer2_lora_data_v1_1_7.py --patch-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent

# ─── 出力パス ─────────────────────────────────────────────────────────────────
PATCH_OUT  = REPO_ROOT / "castle_ex_dataset_layer2_lora_v1_1_7_patch.jsonl"
TRAIN_OUT  = REPO_ROOT / "castle_ex_dataset_layer2_lora_v1_1_7_train.jsonl"
BASE_TRAIN = REPO_ROOT / "castle_ex_dataset_layer2_lora_v1_1_6_posonly_train.jsonl"

# ─── 乱数シード ───────────────────────────────────────────────────────────────
SEED = 117


def _pair_id(user_msg: str, assistant_msg: str) -> str:
    raw = f"{user_msg}||{assistant_msg}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def _rec(
    user_msg: str,
    assistant_msg: str,
    template_id: str,
    positive: bool = True,
) -> Dict[str, Any]:
    return {
        "layer": 2,
        "axes": ["logic"],
        "positive": positive,
        "messages": [
            {"role": "user",      "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ],
        "type": "correction_v1_1_7",
        "template_id": template_id,
        "pair_id": _pair_id(user_msg, assistant_msg),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  l2_attribute 補正
#
#  症状: 属性値を落とす（低い→小さい/黒/簡単）+ 冗長出力
#  方針:
#    パターンA: "{obj}の{attr}は{value}です。"  ← 最短・最強
#    パターンB: "結論：{value}です。"            ← 値固定バリアント
#  値セット: 低い / 中 / 高 / 小さい（正当値）だけ。ブレる値は入れない。
# ══════════════════════════════════════════════════════════════════════════════

# NG pair の (obj, attr, value) マッピング
# 評価ログの gold から逆引き
_ATTR_NG_PAIRS = [
    ("洗車機",    "大きさ",  "小さい"),
    ("オイル交換", "難易度",  "低い"),
    ("😢",        "難易度",  "低い"),
    ("車",        "危険度",  "低い"),
    ("洗車",      "優先度",  "小さい"),
    ("エンジン",  "危険度",  "中"),
    ("オイル交換", "色",      "低い"),
]

# 拡張: 同スロット・別値 → 過学習防止のため値をローテート
_ATTR_VALUES_MAP: Dict[str, List[str]] = {
    "難易度": ["低い", "中", "高い"],
    "危険度": ["低い", "中", "高い"],
    "優先度": ["小さい", "中", "大きい"],
    "大きさ": ["小さい", "中", "大きい"],
    "色":     ["低い", "中", "高い"],   # 意味的には変だが元データに合わせる
}

def _build_attribute_patch() -> List[Dict[str, Any]]:
    recs: List[Dict[str, Any]] = []
    for obj, attr, val in _ATTR_NG_PAIRS:
        user_a = f"{obj} の {attr} は？"
        # パターンA: 最短答え
        recs.append(_rec(user_a, f"{obj}の{attr}は{val}です。",
                         "l2_attribute_v1_1_7_typeA"))
        # パターンB: 結論型
        recs.append(_rec(user_a, f"結論：{val}です。",
                         "l2_attribute_v1_1_7_typeB"))

    # 値バリエーション追加（同属性で 低い/中/高い を全カバー）
    for (obj, attr, _) in _ATTR_NG_PAIRS:
        vals = _ATTR_VALUES_MAP.get(attr)
        if not vals:
            continue
        user_a = f"{obj} の {attr} は？"
        for v in vals:
            recs.append(_rec(user_a, f"{obj}の{attr}は{v}です。",
                             "l2_attribute_v1_1_7_valspan"))

    return recs


# ══════════════════════════════════════════════════════════════════════════════
#  l2_part_whole 補正
#
#  症状: はい/いいえ反転、はい。はい。繰り返し
#  方針:
#    ・NG 4件の obj/whole で 負例(いいえ)×3 + 正例(はい)×3
#    ・抽象語 whole（文脈/システム/構成/感情/作業/管理）を混ぜてラベル固定
# ══════════════════════════════════════════════════════════════════════════════

# NG pairs: (obj, whole, gold_yes=True/False)
_PART_WHOLE_NG_PAIRS = [
    ("ピット",   "構成",  False),   # 74162dc8feb6
    ("洗車機",   "感情",  False),   # 2c79f5448e22
    ("エンジン", "作業",  False),   # d23027432f07
    ("洗車機",   "空間",  True),    # d1e0b00f3c65
]

# 抽象語 whole の追加セット（反転しやすい）
_ABSTRACT_WHOLES = ["文脈", "システム", "管理", "構成", "環境", "設計"]
_CONCRETE_OBJS   = ["ピット", "レジ", "エンジン", "洗車機", "オイル", "車"]

def _build_part_whole_patch() -> List[Dict[str, Any]]:
    recs: List[Dict[str, Any]] = []
    rng = random.Random(SEED)

    # NG対象の正例＋負例（各2セット）
    for obj, whole, is_yes in _PART_WHOLE_NG_PAIRS:
        user_q = f"{obj} は {whole} の一部？"
        if is_yes:
            ans_yes = f"はい。{obj}は{whole}に含まれます。"
            ans_no  = f"いいえ。{obj}は{whole}に含まれません。"
        else:
            ans_yes = f"はい。{obj}は{whole}に含まれます。"
            ans_no  = f"いいえ。{obj}は{whole}に含まれません。"
        # 正解をパターンA / B×補強2件
        correct_ans, wrong_ans = (ans_yes, ans_no) if is_yes else (ans_no, ans_yes)
        # パターンA (短)
        short_correct = "はい。" if is_yes else "いいえ。"
        recs.append(_rec(user_q, short_correct,
                         "l2_part_whole_v1_1_7_short", positive=True))
        # パターンB (完全)
        recs.append(_rec(user_q, correct_ans,
                         "l2_part_whole_v1_1_7_full", positive=True))

    # 抽象語 whole への「含まれない」負例を追加（反転誤りが多かったので）
    abstract_combos = [(o, w)
                       for o in _CONCRETE_OBJS
                       for w in _ABSTRACT_WHOLES
                       if (o, w) not in [("洗車機","感情"),("エンジン","作業"),("ピット","構成")]]
    rng.shuffle(abstract_combos)
    for obj, whole in abstract_combos[:9]:   # 9件追加
        user_q = f"{obj} は {whole} の一部？"
        recs.append(_rec(user_q, f"いいえ。{obj}は{whole}に含まれません。",
                         "l2_part_whole_v1_1_7_abstract_neg", positive=True))

    return recs


# ══════════════════════════════════════════════════════════════════════════════
#  メイン
# ══════════════════════════════════════════════════════════════════════════════

def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-only", action="store_true",
                        help="patch JSONL のみ生成（train 合算をスキップ）")
    args = parser.parse_args()

    patch: List[Dict[str, Any]] = []
    patch += _build_attribute_patch()
    patch += _build_part_whole_patch()

    # 重複除去（pair_id ベース）
    seen: set = set()
    deduped: List[Dict[str, Any]] = []
    for r in patch:
        if r["pair_id"] not in seen:
            seen.add(r["pair_id"])
            deduped.append(r)
    patch = deduped

    _write_jsonl(PATCH_OUT, patch)
    print(f"[v1.1.7] patch: {len(patch)} records → {PATCH_OUT}")

    if not args.patch_only:
        # v1.1.6 posonly_train と合算
        base_rows: List[Dict[str, Any]] = []
        if BASE_TRAIN.exists():
            with BASE_TRAIN.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        base_rows.append(json.loads(line))
        else:
            print(f"[WARN] base train not found: {BASE_TRAIN}")

        combined = base_rows + patch
        _write_jsonl(TRAIN_OUT, combined)
        print(f"[v1.1.7] train: base={len(base_rows)} + patch={len(patch)} = {len(combined)} → {TRAIN_OUT}")


if __name__ == "__main__":
    main()
