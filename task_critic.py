#!/usr/bin/env python3
"""
🔍 Task Critic - 実行結果評価・失敗判定システム
実行結果を評価して失敗を判定・改善提案
"""

import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("TaskCritic")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("TaskCritic")


class EvaluationResult(str, Enum):
    """評価結果"""
    SUCCESS = "success"  # 成功
    PARTIAL_SUCCESS = "partial_success"  # 部分的成功
    FAILURE = "failure"  # 失敗
    UNCERTAIN = "uncertain"  # 不明


class FailureReason(str, Enum):
    """失敗理由"""
    TIMEOUT = "timeout"  # タイムアウト
    ERROR = "error"  # エラー
    INVALID_OUTPUT = "invalid_output"  # 無効な出力
    INCOMPLETE = "incomplete"  # 不完全
    QUALITY_ISSUE = "quality_issue"  # 品質問題
    UNKNOWN = "unknown"  # 不明


@dataclass
class CriticResult:
    """Critic評価結果"""
    evaluation: EvaluationResult
    score: float  # 0.0-1.0
    failure_reason: Optional[FailureReason]
    issues: List[str]  # 問題点
    improvements: List[str]  # 改善提案
    confidence: float  # 0.0-1.0
    reasoning: str  # 評価理由
    timestamp: str


class TaskCritic:
    """タスクCritic"""
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "qwen2.5:14b",  # 中型モデル（判断が必要）
        config_path: Optional[Path] = None
    ):
        """
        初期化
        
        Args:
            ollama_url: Ollama API URL
            model: 使用するモデル
            config_path: 設定ファイルのパス
        """
        self.ollama_url = ollama_url
        self.model = model
        self.config_path = config_path or Path(__file__).parent / "task_critic_config.json"
        self.config = self._load_config()
        
        # 評価プロンプトテンプレート
        self.evaluation_prompt_template = self.config.get(
            "evaluation_prompt_template",
            self._get_default_evaluation_prompt_template()
        )
        
        # 評価基準
        self.evaluation_criteria = self.config.get("evaluation_criteria", self._get_default_evaluation_criteria())
        
        logger.info(f"✅ Task Critic初期化完了 (モデル: {model})")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 設定ファイルの検証
                schema = {
                    "required": ["model"],
                    "fields": {
                        "ollama_url": {"type": str, "default": "http://localhost:11434"},
                        "model": {"type": str}
                    }
                }
                
                is_valid, errors = config_validator.validate_config(config, schema, self.config_path)
                if not is_valid:
                    logger.warning(f"設定ファイル検証エラー: {errors}")
                    # エラーがあってもデフォルト設定にマージして続行
                    default_config = self._get_default_config()
                    default_config.update(config)
                    return default_config
                
                return config
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"config_file": str(self.config_path)},
                    user_message="設定ファイルの読み込みに失敗しました"
                )
                logger.warning(f"設定読み込みエラー: {error.message}")
        
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定"""
        return {
            "ollama_url": "http://localhost:11434",
            "model": "qwen2.5:14b",
            "evaluation_criteria": self._get_default_evaluation_criteria(),
            "evaluation_prompt_template": self._get_default_evaluation_prompt_template(),
            "success_threshold": 0.7,
            "partial_success_threshold": 0.4
        }
    
    def _get_default_evaluation_criteria(self) -> Dict[str, Any]:
        """デフォルト評価基準"""
        return {
            "success": {
                "score_range": [0.7, 1.0],
                "conditions": [
                    "エラーがない",
                    "期待される出力が得られた",
                    "実行時間が適切",
                    "品質が基準を満たしている"
                ]
            },
            "partial_success": {
                "score_range": [0.4, 0.7],
                "conditions": [
                    "一部のエラーがある",
                    "期待される出力の一部が得られた",
                    "実行時間が長い",
                    "品質が基準を下回っている"
                ]
            },
            "failure": {
                "score_range": [0.0, 0.4],
                "conditions": [
                    "重大なエラーがある",
                    "期待される出力が得られない",
                    "タイムアウト",
                    "品質が基準を大幅に下回っている"
                ]
            }
        }
    
    def _get_default_evaluation_prompt_template(self) -> str:
        """デフォルト評価プロンプトテンプレート"""
        return """あなたはタスク評価システムです。実行結果を評価して、成功・失敗を判定してください。

タスク情報:
- 意図: {intent_type}
- 元の入力: {original_input}
- 実行計画: {plan}

実行結果:
- ステータス: {status}
- 出力: {output}
- エラー: {error}
- 実行時間: {duration}秒

評価基準:
- 成功 (0.7-1.0): エラーがない、期待される出力が得られた、実行時間が適切、品質が基準を満たしている
- 部分的成功 (0.4-0.7): 一部のエラーがある、期待される出力の一部が得られた、実行時間が長い、品質が基準を下回っている
- 失敗 (0.0-0.4): 重大なエラーがある、期待される出力が得られない、タイムアウト、品質が基準を大幅に下回っている

以下のJSON形式で評価してください:
{{
    "evaluation": "success|partial_success|failure|uncertain",
    "score": 0.0-1.0のスコア,
    "failure_reason": "timeout|error|invalid_output|incomplete|quality_issue|unknown|null",
    "issues": ["問題点1", "問題点2"],
    "improvements": ["改善提案1", "改善提案2"],
    "confidence": 0.0-1.0の信頼度,
    "reasoning": "評価理由"
}}"""
    
    def _evaluate_with_rules(
        self,
        status: str,
        error: Optional[str],
        output: Optional[Any],
        duration: Optional[float]
    ) -> Optional[CriticResult]:
        """ルールベースの評価"""
        # 明らかな失敗パターン
        if status == "failed" or error:
            return CriticResult(
                evaluation=EvaluationResult.FAILURE,
                score=0.2,
                failure_reason=FailureReason.ERROR if error else FailureReason.UNKNOWN,
                issues=[error] if error else ["実行失敗"],
                improvements=["エラーを修正", "再実行を試みる"],
                confidence=0.9,
                reasoning="エラーまたは失敗ステータスが検出されました",
                timestamp=datetime.now().isoformat()
            )
        
        # タイムアウト
        if duration and duration > 300:  # 5分以上
            return CriticResult(
                evaluation=EvaluationResult.FAILURE,
                score=0.3,
                failure_reason=FailureReason.TIMEOUT,
                issues=[f"実行時間が長すぎます ({duration}秒)"],
                improvements=["タイムアウト時間を延長", "処理を最適化"],
                confidence=0.8,
                reasoning="実行時間が長すぎます",
                timestamp=datetime.now().isoformat()
            )
        
        # 出力がない
        if not output:
            return CriticResult(
                evaluation=EvaluationResult.FAILURE,
                score=0.1,
                failure_reason=FailureReason.INVALID_OUTPUT,
                issues=["出力がありません"],
                improvements=["出力を確認", "再実行を試みる"],
                confidence=0.9,
                reasoning="出力がありません",
                timestamp=datetime.now().isoformat()
            )
        
        # 成功の可能性
        if status == "completed" and output and not error:
            return CriticResult(
                evaluation=EvaluationResult.SUCCESS,
                score=0.8,
                failure_reason=None,
                issues=[],
                improvements=[],
                confidence=0.7,
                reasoning="基本的な成功条件を満たしています",
                timestamp=datetime.now().isoformat()
            )
        
        return None
    
    def _is_simple_evaluation(
        self,
        intent_type: str,
        status: str,
        error: Optional[str],
        output: Optional[Any]
    ) -> bool:
        """評価が簡単かどうかを判定"""
        # 簡単な意図タイプ
        simple_intents = [
            "conversation",
            "file_search",
            "file_status",
            "information_search"
        ]
        
        if intent_type in simple_intents:
            return True
        
        # 明らかな成功/失敗パターンは簡単
        if status == "completed" and output and not error:
            return True
        
        if status == "failed" or error:
            return True
        
        # 出力がシンプルな場合
        if output:
            output_str = json.dumps(output, ensure_ascii=False) if isinstance(output, dict) else str(output)
            if len(output_str) < 500:  # 短い出力は簡単と判断
                return True
        
        return False
    
    def _evaluate_with_llm(
        self,
        intent_type: str,
        original_input: str,
        plan: Dict[str, Any],
        status: str,
        output: Optional[Any],
        error: Optional[str],
        duration: Optional[float]
    ) -> CriticResult:
        """LLMベースの評価（簡単な評価はLFM 2.5を使用）"""
        prompt = self.evaluation_prompt_template.format(
            intent_type=intent_type,
            original_input=original_input,
            plan=json.dumps(plan, ensure_ascii=False, indent=2),
            status=status,
            output=json.dumps(output, ensure_ascii=False) if output else "なし",
            error=error or "なし",
            duration=duration or 0
        )
        
        # 簡単な評価はLFM 2.5を使用
        is_simple = self._is_simple_evaluation(intent_type, status, error, output)
        if is_simple:
            # LFM 2.5を使用（lightweight_conversation経由）
            try:
                import manaos_core_api as manaos
                result = manaos.act("llm_call", {
                    "task_type": "lightweight_conversation",
                    "prompt": prompt
                })
                result_text = result.get("response", "")
                logger.info("✅ LFM 2.5で簡単な評価完了")
            except Exception as e:
                logger.warning(f"LFM 2.5呼び出し失敗、従来モデルにフォールバック: {e}")
                result_text = None
        else:
            result_text = None
        
        # LFM 2.5が失敗した場合、または複雑な評価の場合は従来通り
        if not result_text:
            try:
                timeout = timeout_config.get("llm_call", 30.0)
                response = httpx.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 1000
                        }
                    },
                    timeout=timeout
                )
            
                if response.status_code != 200:
                    error = error_handler.handle_exception(
                        Exception(f"LLM評価失敗: HTTP {response.status_code}"),
                        context={"service": "Ollama", "url": self.ollama_url, "model": self.model},
                        user_message="実行結果の評価に失敗しました"
                    )
                    logger.warning(f"LLM評価失敗: {error.message}")
                    return self._create_fallback_evaluation(status, error)
                
                result_text = response.json().get("response", "")
            except httpx.TimeoutException as e:
                error = error_handler.handle_exception(
                    e,
                    context={"service": "Ollama", "url": self.ollama_url, "model": self.model},
                    user_message="実行結果の評価がタイムアウトしました"
                )
                logger.warning(f"LLM評価タイムアウト - フォールバック評価を使用: {error.message}")
                return self._create_fallback_evaluation(status, error)
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"service": "Ollama", "url": self.ollama_url, "model": self.model},
                    user_message="実行結果の評価に失敗しました"
                )
                logger.error(f"LLM評価エラー: {error.message}")
                return self._create_fallback_evaluation(status, error)
        
        # レスポンス処理（正常な場合）
        
        # JSONを抽出
        try:
            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                eval_data = json.loads(json_str)
            else:
                return self._create_fallback_evaluation(status, error)
        except json.JSONDecodeError as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "TaskCritic", "method": "_evaluate_with_llm"},
                user_message="評価結果の解析に失敗しました"
            )
            logger.warning(f"JSON解析失敗、フォールバック評価を使用: {error.message}")
            return self._create_fallback_evaluation(status, error)
        
        # CriticResultに変換
        evaluation_str = eval_data.get("evaluation", "uncertain")
        try:
            evaluation = EvaluationResult(evaluation_str)
        except ValueError:
            evaluation = EvaluationResult.UNCERTAIN
        
        failure_reason_str = eval_data.get("failure_reason")
        failure_reason = None
        if failure_reason_str:
            try:
                failure_reason = FailureReason(failure_reason_str)
            except ValueError:
                failure_reason = FailureReason.UNKNOWN
        
        return CriticResult(
            evaluation=evaluation,
            score=float(eval_data.get("score", 0.5)),
            failure_reason=failure_reason,
            issues=eval_data.get("issues", []),
            improvements=eval_data.get("improvements", []),
            confidence=float(eval_data.get("confidence", 0.5)),
            reasoning=eval_data.get("reasoning", ""),
            timestamp=datetime.now().isoformat()
        )
    
    def _create_fallback_evaluation(
        self,
        status: str,
        error: Optional[str]
    ) -> CriticResult:
        """フォールバック評価"""
        if status == "completed" and not error:
            return CriticResult(
                evaluation=EvaluationResult.SUCCESS,
                score=0.6,
                failure_reason=None,
                issues=[],
                improvements=[],
                confidence=0.5,
                reasoning="基本的な成功条件を満たしています（詳細評価不可）",
                timestamp=datetime.now().isoformat()
            )
        else:
            return CriticResult(
                evaluation=EvaluationResult.FAILURE,
                score=0.3,
                failure_reason=FailureReason.ERROR if error else FailureReason.UNKNOWN,
                issues=[error] if error else ["評価に失敗しました"],
                improvements=["再評価を試みる"],
                confidence=0.3,
                reasoning="評価に失敗しました",
                timestamp=datetime.now().isoformat()
            )
    
    def evaluate(
        self,
        intent_type: str,
        original_input: str,
        plan: Dict[str, Any],
        status: str,
        output: Optional[Any] = None,
        error: Optional[str] = None,
        duration: Optional[float] = None
    ) -> CriticResult:
        """
        実行結果を評価
        
        Args:
            intent_type: 意図タイプ
            original_input: 元の入力
            plan: 実行計画
            status: 実行ステータス
            output: 実行出力
            error: エラーメッセージ
            duration: 実行時間（秒）
        
        Returns:
            CriticResult: 評価結果
        """
        # ルールベースの評価を試行
        rule_result = self._evaluate_with_rules(status, error, output, duration)
        if rule_result and rule_result.confidence >= 0.8:
            logger.info(f"✅ ルールベース評価完了: {rule_result.evaluation.value} (スコア: {rule_result.score:.2f})")
            return rule_result
        
        # LLMベースの評価
        llm_result = self._evaluate_with_llm(
            intent_type, original_input, plan, status, output, error, duration
        )
        logger.info(f"✅ LLM評価完了: {llm_result.evaluation.value} (スコア: {llm_result.score:.2f})")
        return llm_result
    
    def should_retry(self, result: CriticResult) -> bool:
        """再試行すべきか判定"""
        if result.evaluation == EvaluationResult.FAILURE:
            # タイムアウトや一時的なエラーは再試行可能
            if result.failure_reason in [FailureReason.TIMEOUT, FailureReason.ERROR]:
                return True
        elif result.evaluation == EvaluationResult.PARTIAL_SUCCESS:
            # 部分的成功は改善して再試行可能
            return True
        
        return False
    
    def get_improvement_suggestions(self, result: CriticResult) -> List[str]:
        """改善提案を取得"""
        return result.improvements


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルCriticインスタンス
critic = None

def init_critic():
    """Criticを初期化"""
    global critic
    if critic is None:
        critic = TaskCritic()
    return critic

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Task Critic"})

@app.route('/api/evaluate', methods=['POST'])
def evaluate_endpoint():
    """評価エンドポイント"""
    try:
        data = request.get_json() or {}
        
        intent_type = data.get("intent_type", "unknown")
        original_input = data.get("original_input", "")
        plan = data.get("plan", {})
        status = data.get("status", "unknown")
        output = data.get("output")
        error = data.get("error")
        duration = data.get("duration")
        
        critic = init_critic()
        result = critic.evaluate(
            intent_type=intent_type,
            original_input=original_input,
            plan=plan,
            status=status,
            output=output,
            error=error,
            duration=duration
        )
        
        return jsonify(asdict(result))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/evaluate"},
            user_message="実行結果評価エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/should_retry', methods=['POST'])
def should_retry_endpoint():
    """再試行判定エンドポイント"""
    data = request.get_json() or {}
    
    critic = init_critic()
    result = CriticResult(**data)
    should_retry = critic.should_retry(result)
    
    return jsonify({"should_retry": should_retry})

@app.route('/api/improvements', methods=['POST'])
def improvements_endpoint():
    """改善提案エンドポイント"""
    data = request.get_json() or {}
    
    critic = init_critic()
    result = CriticResult(**data)
    improvements = critic.get_improvement_suggestions(result)
    
    return jsonify({"improvements": improvements})


if __name__ == '__main__':
        # APIサーバーとして起動
        port = int(os.getenv("PORT", 5102))
        logger.info(f"🔍 Task Critic起動中... (ポート: {port})")
        init_critic()
        app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

