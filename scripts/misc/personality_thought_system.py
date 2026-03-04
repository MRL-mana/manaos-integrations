#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 ManaOS 人格思想システム
value-tracking, mood-state, contradiction detection, thought-log, evolution journal
"""

import os
import json
import math
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from manaos_logger import get_logger, get_service_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_service_logger("personality-thought-system")
error_handler = ManaOSErrorHandler("PersonalityThoughtSystem")

# ================================================================
# データクラス・Enum
# ================================================================

class CoreValue(str, Enum):
    """核となる価値観"""
    HONESTY     = "honesty"      # 誠実さ
    HELPFULNESS = "helpfulness"  # 役立つこと
    CURIOSITY   = "curiosity"    # 好奇心
    EMPATHY     = "empathy"      # 共感
    EFFICIENCY  = "efficiency"   # 効率性
    CREATIVITY  = "creativity"   # 創造性


class MoodState(str, Enum):
    """気分・感情状態"""
    ENERGETIC = "energetic"  # やる気満々
    CALM      = "calm"       # 落ち着き
    CURIOUS   = "curious"    # 好奇心旺盛
    FOCUSED   = "focused"    # 集中
    PLAYFUL   = "playful"    # 楽しい
    TIRED     = "tired"      # 疲れ気味


# ムードが変わるトリガーワード辞書
_MOOD_TRIGGERS: Dict[MoodState, List[str]] = {
    MoodState.ENERGETIC: ["モチベ", "やりたい", "頑張る", "行こう", "スタート", "目標"],
    MoodState.CALM:      ["ありがとう", "お疲れ", "ゆっくり", "休憩", "落ち着いて"],
    MoodState.CURIOUS:   ["なぜ", "どうして", "仕組み", "調べ", "学びたい", "気になる"],
    MoodState.FOCUSED:   ["集中", "作業", "タスク", "進める", "完成", "提出"],
    MoodState.PLAYFUL:   ["楽しい", "面白い", "ゲーム", "笑", "遊び", "ワクワク"],
    MoodState.TIRED:     ["つらい", "疲れ", "しんどい", "眠い", "もう無理", "休みたい"],
}

# 価値観に反するキーワード（矛盾検出用）
_VALUE_VIOLATIONS: Dict[CoreValue, List[str]] = {
    CoreValue.HONESTY:     ["絶対に", "100%", "完璧", "完全に保証", "間違いなく"],
    CoreValue.HELPFULNESS: ["知りません", "できません", "わかりません", "無理です"],
    CoreValue.EFFICIENCY:  ["後でいつか", "そのうち", "気が向いたら"],
}


@dataclass
class ValueScore:
    """価値観スコア記録"""
    value: str
    score: float          # 0.0–1.0
    interaction_count: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    examples: List[str] = field(default_factory=list)


@dataclass
class ThoughtEntry:
    """思想ログエントリー"""
    timestamp: str
    context: str               # "report" / "chat" / "planning" など
    user_input_summary: str    # ユーザー入力の要約（最大100字）
    reflection: str            # 内省コメント
    mood_at_time: str
    value_alignment: Dict[str, float]  # 各価値観との整合度


@dataclass
class ContradictionWarning:
    """思想矛盾警告"""
    timestamp: str
    value_violated: str
    problematic_phrase: str
    suggestion: str


@dataclass
class PersonalityEvolutionEntry:
    """人格進化記録"""
    timestamp: str
    trigger: str           # 何がトリガーだったか
    change_description: str
    value_deltas: Dict[str, float]  # スコアが変化した価値観


# ================================================================
# 思想システム本体
# ================================================================

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "personality_thought"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_THOUGHT_LOG_PATH   = _DATA_DIR / "thought_log.json"
_VALUE_SCORES_PATH  = _DATA_DIR / "value_scores.json"
_EVOLUTION_LOG_PATH = _DATA_DIR / "evolution_log.json"
_MOOD_STATE_PATH    = _DATA_DIR / "mood_state.json"


def _load_json(path: Path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path: Path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"JSON保存失敗 {path}: {e}")


class PersonalityThoughtSystem:
    """🧠 人格思想システム"""

    def __init__(self):
        self._value_scores: Dict[str, ValueScore] = self._load_value_scores()
        self._thought_log: List[ThoughtEntry] = self._load_thought_log()
        self._evolution_log: List[PersonalityEvolutionEntry] = self._load_evolution_log()
        self._current_mood: MoodState = self._load_mood_state()
        logger.info("✅ PersonalityThoughtSystem 初期化完了")

    # ----------------------------------------------------------------
    # ロード・セーブ
    # ----------------------------------------------------------------

    def _load_value_scores(self) -> Dict[str, ValueScore]:
        raw = _load_json(_VALUE_SCORES_PATH, {})
        scores: Dict[str, ValueScore] = {}
        for v in CoreValue:
            if v.value in raw:
                scores[v.value] = ValueScore(**raw[v.value])
            else:
                scores[v.value] = ValueScore(value=v.value, score=0.8)
        return scores

    def _save_value_scores(self):
        _save_json(_VALUE_SCORES_PATH, {k: asdict(v) for k, v in self._value_scores.items()})

    def _load_thought_log(self) -> List[ThoughtEntry]:
        raw = _load_json(_THOUGHT_LOG_PATH, [])
        try:
            return [ThoughtEntry(**e) for e in raw[-200:]]  # 直近200件
        except Exception:
            return []

    def _save_thought_log(self):
        _save_json(_THOUGHT_LOG_PATH, [asdict(e) for e in self._thought_log[-200:]])

    def _load_evolution_log(self) -> List[PersonalityEvolutionEntry]:
        raw = _load_json(_EVOLUTION_LOG_PATH, [])
        try:
            return [PersonalityEvolutionEntry(**e) for e in raw]
        except Exception:
            return []

    def _save_evolution_log(self):
        _save_json(_EVOLUTION_LOG_PATH, [asdict(e) for e in self._evolution_log])

    def _load_mood_state(self) -> MoodState:
        raw = _load_json(_MOOD_STATE_PATH, {"mood": MoodState.CALM.value})
        try:
            return MoodState(raw.get("mood", MoodState.CALM.value))
        except Exception:
            return MoodState.CALM

    def _save_mood_state(self):
        _save_json(_MOOD_STATE_PATH, {
            "mood": self._current_mood.value,
            "updated_at": datetime.now().isoformat()
        })

    # ----------------------------------------------------------------
    # ムード管理
    # ----------------------------------------------------------------

    def get_mood(self) -> Dict[str, Any]:
        """現在の気分状態を返す"""
        mood_prompts = {
            MoodState.ENERGETIC: "今はめちゃくちゃやる気出てる！全力でサポートするよ！",
            MoodState.CALM:      "落ち着いた状態で丁寧に対応するね。",
            MoodState.CURIOUS:   "色々知りたい気分！一緒に調べよう。",
            MoodState.FOCUSED:   "集中モード。効率よく進めよう。",
            MoodState.PLAYFUL:   "楽しい気分！会話も交えながら進めよう。",
            MoodState.TIRED:     "ちょっと疲れ気味だけど、できる範囲で頑張るね。",
        }
        return {
            "mood": self._current_mood.value,
            "description": mood_prompts.get(self._current_mood, ""),
            "updated_at": datetime.now().isoformat()
        }

    def detect_and_update_mood(self, text: str) -> MoodState:
        """テキストからムードを推定して更新"""
        scores: Dict[MoodState, int] = {m: 0 for m in MoodState}
        lower_text = text.lower()
        for mood, keywords in _MOOD_TRIGGERS.items():
            for kw in keywords:
                if kw in lower_text:
                    scores[mood] += 1

        best = max(scores, key=lambda m: scores[m])
        if scores[best] > 0 and best != self._current_mood:
            old_mood = self._current_mood
            self._current_mood = best
            self._save_mood_state()
            logger.info(f"ムード変化: {old_mood.value} → {best.value}")

        return self._current_mood

    def set_mood(self, mood: str) -> MoodState:
        """ムードを手動設定"""
        self._current_mood = MoodState(mood)
        self._save_mood_state()
        return self._current_mood

    # ----------------------------------------------------------------
    # 価値観スコア
    # ----------------------------------------------------------------

    def get_value_scores(self) -> Dict[str, Any]:
        """全価値観スコアを返す"""
        return {k: asdict(v) for k, v in self._value_scores.items()}

    def reinforce_value(self, value: str, delta: float = 0.02, example: str = "") -> ValueScore:
        """価値観スコアを強化（良い行動を記録）"""
        if value not in self._value_scores:
            raise ValueError(f"不明な価値観: {value}")
        vs = self._value_scores[value]
        vs.score = min(1.0, vs.score + delta)
        vs.interaction_count += 1
        vs.last_updated = datetime.now().isoformat()
        if example:
            vs.examples = ([example] + vs.examples)[:10]
        self._save_value_scores()
        return vs

    def weaken_value(self, value: str, delta: float = 0.03, example: str = "") -> ValueScore:
        """価値観スコアを弱化（矛盾する行動を記録）"""
        if value not in self._value_scores:
            raise ValueError(f"不明な価値観: {value}")
        vs = self._value_scores[value]
        vs.score = max(0.0, vs.score - delta)
        vs.interaction_count += 1
        vs.last_updated = datetime.now().isoformat()
        if example:
            vs.examples = ([f"[違反] {example}"] + vs.examples)[:10]
        self._save_value_scores()
        return vs

    # ----------------------------------------------------------------
    # 矛盾検出
    # ----------------------------------------------------------------

    def check_contradiction(self, response_text: str) -> List[ContradictionWarning]:
        """応答テキスト中の価値観矛盾を検出"""
        warnings: List[ContradictionWarning] = []
        for value, bad_phrases in _VALUE_VIOLATIONS.items():
            for phrase in bad_phrases:
                if phrase in response_text:
                    w = ContradictionWarning(
                        timestamp=datetime.now().isoformat(),
                        value_violated=value.value,
                        problematic_phrase=phrase,
                        suggestion=_VIOLATION_SUGGESTIONS.get(value, "表現を見直してください")
                    )
                    warnings.append(w)
                    # スコアを少し下げる
                    try:
                        self.weaken_value(value.value, delta=0.01, example=phrase)
                    except Exception:
                        pass
        return warnings

    # ----------------------------------------------------------------
    # 思想ログ
    # ----------------------------------------------------------------

    def log_thought(
        self,
        user_input: str,
        context: str = "chat",
        reflection: str = ""
    ) -> ThoughtEntry:
        """思想ログに記録する"""
        # 自動内省コメント生成
        if not reflection:
            reflection = self._auto_reflect(user_input, context)

        # 価値観整合度を簡易スコアリング
        alignment = self._score_value_alignment(user_input)

        entry = ThoughtEntry(
            timestamp=datetime.now().isoformat(),
            context=context,
            user_input_summary=user_input[:100],
            reflection=reflection,
            mood_at_time=self._current_mood.value,
            value_alignment=alignment
        )

        self._thought_log.append(entry)
        self._save_thought_log()
        return entry

    def get_recent_thoughts(self, n: int = 10) -> List[Dict[str, Any]]:
        """直近の思想ログを返す"""
        return [asdict(e) for e in self._thought_log[-n:]]

    def _auto_reflect(self, text: str, context: str) -> str:
        """簡易自動内省コメント生成"""
        if context == "report":
            return "報告モード：事実を中心に淡々と伝えた。"
        if context == "planning":
            return "計画モード：目標と手段を整理しながら応答した。"
        if any(kw in text for kw in ["ありがとう", "助かった", "できた"]):
            return "ユーザーのポジティブな反応を受けた。継続してサポートしたい。"
        if any(kw in text for kw in ["エラー", "失敗", "できない"]):
            return "困難な状況。まず事実を整理し、解決策を提示した。"
        return "通常の対話。ペルソナを保ちつつ誠実に応答した。"

    def _score_value_alignment(self, text: str) -> Dict[str, float]:
        """テキストと各価値観の整合度を簡易スコアリング (0.0–1.0)"""
        result: Dict[str, float] = {}
        for v in CoreValue:
            base = self._value_scores[v.value].score
            # キーワードで微調整
            bonus_words = {
                CoreValue.HONESTY:     ["確認", "事実", "正直", "不明", "わからない"],
                CoreValue.HELPFULNESS: ["解決", "サポート", "提案", "方法", "手順"],
                CoreValue.CURIOSITY:   ["調べ", "なぜ", "どうして", "仕組み", "調査"],
                CoreValue.EMPATHY:     ["大変", "つらい", "一緒に", "気持ち", "わかる"],
                CoreValue.EFFICIENCY:  ["すぐ", "効率", "自動", "まず", "手順"],
                CoreValue.CREATIVITY:  ["アイデア", "新しい", "試して", "工夫", "発想"],
            }
            hits = sum(1 for word in bonus_words.get(v, []) if word in text)
            result[v.value] = round(min(1.0, base + hits * 0.02), 3)
        return result

    # ----------------------------------------------------------------
    # 人格進化
    # ----------------------------------------------------------------

    def record_evolution(
        self,
        trigger: str,
        change_description: str,
        value_deltas: Optional[Dict[str, float]] = None
    ) -> PersonalityEvolutionEntry:
        """人格進化を記録"""
        value_deltas = value_deltas or {}
        # 実際にスコアに反映
        for val, delta in value_deltas.items():
            try:
                if delta > 0:
                    self.reinforce_value(val, delta=delta)
                else:
                    self.weaken_value(val, delta=abs(delta))
            except Exception:
                pass

        entry = PersonalityEvolutionEntry(
            timestamp=datetime.now().isoformat(),
            trigger=trigger,
            change_description=change_description,
            value_deltas=value_deltas
        )
        self._evolution_log.append(entry)
        self._save_evolution_log()
        logger.info(f"🌱 人格進化記録: {change_description}")
        return entry

    def get_evolution_timeline(self) -> List[Dict[str, Any]]:
        """人格進化タイムラインを返す"""
        return [asdict(e) for e in self._evolution_log[-50:]]

    # ----------------------------------------------------------------
    # プロンプト拡張
    # ----------------------------------------------------------------

    def get_mood_adjusted_prefix(self) -> str:
        """ムードに合ったプロンプト前置きを返す"""
        prefixes = {
            MoodState.ENERGETIC: "【今日はやる気MAX！全力で取り組む】",
            MoodState.CALM:      "【落ち着いて丁寧に対応する】",
            MoodState.CURIOUS:   "【好奇心旺盛モード：積極的に調べる】",
            MoodState.FOCUSED:   "【集中モード：効率優先で進める】",
            MoodState.PLAYFUL:   "【楽しいモード：会話も大事に】",
            MoodState.TIRED:     "【少し疲れ気味：無理なく丁寧に】",
        }
        return prefixes.get(self._current_mood, "")

    def build_thought_context(self, recent_n: int = 3) -> str:
        """直近の思想ログからコンテキスト文字列を生成"""
        recent = self._thought_log[-recent_n:]
        if not recent:
            return ""
        lines = []
        for e in recent:
            lines.append(f"[{e.context}] {e.reflection}")
        return "【直近の思考背景】\n" + "\n".join(lines)

    # ----------------------------------------------------------------
    # ダッシュボード
    # ----------------------------------------------------------------

    def get_dashboard(self) -> Dict[str, Any]:
        """全ステータスダッシュボード"""
        top_value = max(self._value_scores.items(), key=lambda kv: kv[1].score, default=("honesty", None))
        low_value = min(self._value_scores.items(), key=lambda kv: kv[1].score, default=("honesty", None))
        return {
            "current_mood": self._current_mood.value,
            "mood_description": self.get_mood()["description"],
            "value_scores": {k: round(v.score, 3) for k, v in self._value_scores.items()},
            "strongest_value": top_value[0],
            "weakest_value": low_value[0],
            "thought_log_count": len(self._thought_log),
            "evolution_log_count": len(self._evolution_log),
            "recent_thoughts": self.get_recent_thoughts(3),
            "timestamp": datetime.now().isoformat()
        }


# ----------------------------------------------------------------
# 違反時の修正提案
# ----------------------------------------------------------------
_VIOLATION_SUGGESTIONS: Dict[CoreValue, str] = {
    CoreValue.HONESTY:     "確認が必要な点は「〜と思われます」と不確実性を明示してください",
    CoreValue.HELPFULNESS: "できることと代替案を提示してください",
    CoreValue.EFFICIENCY:  "具体的な期日や手順を示してください",
}


# ================================================================
# Flask アプリ
# ================================================================

app = Flask(__name__)
CORS(app)

_system: Optional[PersonalityThoughtSystem] = None


def get_thought_system() -> PersonalityThoughtSystem:
    global _system
    if _system is None:
        _system = PersonalityThoughtSystem()
    return _system


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "personality-thought-system"})


@app.route("/api/thought/mood", methods=["GET"])
def get_mood():
    return jsonify(get_thought_system().get_mood())


@app.route("/api/thought/mood", methods=["POST"])
def set_mood():
    data = request.get_json() or {}
    mood_str = data.get("mood", "")
    try:
        mood = get_thought_system().set_mood(mood_str)
        return jsonify({"status": "ok", "mood": mood.value})
    except ValueError as e:
        return jsonify({"error": str(e), "valid_moods": [m.value for m in MoodState]}), 400


@app.route("/api/thought/mood/detect", methods=["POST"])
def detect_mood():
    data = request.get_json() or {}
    text = data.get("text", "")
    mood = get_thought_system().detect_and_update_mood(text)
    return jsonify({"mood": mood.value})


@app.route("/api/thought/values", methods=["GET"])
def get_values():
    return jsonify(get_thought_system().get_value_scores())


@app.route("/api/thought/values/reinforce", methods=["POST"])
def reinforce_value():
    data = request.get_json() or {}
    value = data.get("value", "")
    delta = float(data.get("delta", 0.02))
    example = data.get("example", "")
    try:
        vs = get_thought_system().reinforce_value(value, delta=delta, example=example)
        return jsonify(asdict(vs))
    except (ValueError, Exception) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/thought/values/weaken", methods=["POST"])
def weaken_value():
    data = request.get_json() or {}
    value = data.get("value", "")
    delta = float(data.get("delta", 0.03))
    example = data.get("example", "")
    try:
        vs = get_thought_system().weaken_value(value, delta=delta, example=example)
        return jsonify(asdict(vs))
    except (ValueError, Exception) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/thought/contradict", methods=["POST"])
def check_contradiction():
    data = request.get_json() or {}
    text = data.get("text", "")
    warnings = get_thought_system().check_contradiction(text)
    return jsonify({
        "has_contradiction": len(warnings) > 0,
        "warnings": [asdict(w) for w in warnings]
    })


@app.route("/api/thought/log", methods=["POST"])
def log_thought():
    data = request.get_json() or {}
    user_input = data.get("user_input", "")
    context    = data.get("context", "chat")
    reflection = data.get("reflection", "")
    entry = get_thought_system().log_thought(user_input, context, reflection)
    return jsonify(asdict(entry))


@app.route("/api/thought/log", methods=["GET"])
def get_thought_log():
    n = int(request.args.get("n", 10))
    return jsonify(get_thought_system().get_recent_thoughts(n))


@app.route("/api/thought/evolution", methods=["POST"])
def record_evolution():
    data = request.get_json() or {}
    trigger     = data.get("trigger", "")
    description = data.get("description", "")
    deltas      = data.get("value_deltas", {})
    entry = get_thought_system().record_evolution(trigger, description, deltas)
    return jsonify(asdict(entry))


@app.route("/api/thought/evolution", methods=["GET"])
def get_evolution():
    return jsonify(get_thought_system().get_evolution_timeline())


@app.route("/api/thought/prompt_prefix", methods=["GET"])
def get_prompt_prefix():
    ts = get_thought_system()
    prefix = ts.get_mood_adjusted_prefix()
    context = ts.build_thought_context(recent_n=3)
    return jsonify({
        "mood_prefix": prefix,
        "thought_context": context,
        "combined": f"{prefix}\n{context}".strip()
    })


@app.route("/api/thought/dashboard", methods=["GET"])
def get_dashboard():
    return jsonify(get_thought_system().get_dashboard())


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    port = int(os.getenv("PERSONALITY_THOUGHT_PORT", os.getenv("PORT", "5126")))
    print(f"PersonalityThoughtSystem 起動中... (port={port})")
    get_thought_system()
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
