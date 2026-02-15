#!/usr/bin/env python3
"""
🎯 Intent Router - 意図分類システム
軽量LLMで入力（音声/テキスト/イベント）を分類
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
from _paths import OLLAMA_PORT

# ロガーの初期化
logger = get_service_logger("intent-router")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("IntentRouter")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("IntentRouter")

DEFAULT_OLLAMA_URL = f"http://127.0.0.1:{OLLAMA_PORT}"


class IntentType(str, Enum):
    """意図の種類"""
    CONVERSATION = "conversation"  # 会話・雑談
    TASK_EXECUTION = "task_execution"  # タスク実行
    INFORMATION_SEARCH = "information_search"  # 情報検索
    IMAGE_GENERATION = "image_generation"  # 画像生成
    CODE_GENERATION = "code_generation"  # コード生成
    SYSTEM_CONTROL = "system_control"  # システム制御
    SCHEDULING = "scheduling"  # スケジューリング
    DATA_ANALYSIS = "data_analysis"  # データ分析
    FILE_MANAGEMENT = "file_management"  # ファイル整理
    FILE_SEARCH = "file_search"  # ファイル検索
    FILE_STATUS = "file_status"  # INBOX状況確認
    DEVICE_STATUS = "device_status"  # デバイス・Pixel7 状態確認
    UNKNOWN = "unknown"  # 不明


@dataclass
class IntentResult:
    """意図分類結果"""
    intent_type: IntentType
    confidence: float  # 0.0-1.0
    entities: Dict[str, Any]  # 抽出されたエンティティ
    reasoning: str  # 分類理由
    suggested_actions: List[str]  # 推奨アクション
    timestamp: str


class IntentRouter:
    """意図分類ルーター"""

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model: str = "lfm2.5:1.2b",  # LFM 2.5: 超軽量・超高速・日本語特化
        config_path: Optional[Path] = None
    ):
        """
        初期化

        Args:
            ollama_url: Ollama API URL
            model: 使用する軽量モデル
            config_path: 設定ファイルのパス
        """
        self.ollama_url = ollama_url or DEFAULT_OLLAMA_URL
        self.model = model
        self.config_path = config_path or Path(__file__).parent / "intent_router_config.json"
        self.config = self._load_config()

        # 意図分類のプロンプトテンプレート
        self.intent_prompt_template = self.config.get(
            "intent_prompt_template",
            self._get_default_prompt_template()
        )

        # 意図のキーワードマッピング（高速分類用）
        self.keyword_mapping = self.config.get("keyword_mapping", self._get_default_keyword_mapping())

        logger.info(f"✅ Intent Router初期化完了 (モデル: {model})")

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
                        "ollama_url": {"type": str, "default": DEFAULT_OLLAMA_URL},
                        "model": {"type": str},
                        "confidence_threshold": {"type": (int, float), "default": 0.6},
                        "use_keyword_fallback": {"type": bool, "default": True}
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
            "ollama_url": DEFAULT_OLLAMA_URL,
            "model": "lfm2.5:1.2b",
            "keyword_mapping": self._get_default_keyword_mapping(),
            "intent_prompt_template": self._get_default_prompt_template(),
            "confidence_threshold": 0.6,
            "use_keyword_fallback": True
        }

    def _get_default_keyword_mapping(self) -> Dict[str, IntentType]:
        """デフォルトキーワードマッピング"""
        return {
            # 会話
            "こんにちは": IntentType.CONVERSATION,
            "おはよう": IntentType.CONVERSATION,
            "ありがとう": IntentType.CONVERSATION,
            "どうも": IntentType.CONVERSATION,
            "話": IntentType.CONVERSATION,
            "雑談": IntentType.CONVERSATION,

            # タスク実行
            "実行": IntentType.TASK_EXECUTION,
            "やって": IntentType.TASK_EXECUTION,
            "作って": IntentType.TASK_EXECUTION,
            "作成": IntentType.TASK_EXECUTION,
            "処理": IntentType.TASK_EXECUTION,
            "開始": IntentType.TASK_EXECUTION,
            "起動": IntentType.TASK_EXECUTION,

            # 情報検索
            "検索": IntentType.INFORMATION_SEARCH,
            "調べて": IntentType.INFORMATION_SEARCH,
            "探して": IntentType.INFORMATION_SEARCH,
            "確認": IntentType.INFORMATION_SEARCH,
            "見つけて": IntentType.INFORMATION_SEARCH,
            "教えて": IntentType.INFORMATION_SEARCH,

            # 画像生成
            "画像": IntentType.IMAGE_GENERATION,
            "生成": IntentType.IMAGE_GENERATION,
            "描いて": IntentType.IMAGE_GENERATION,
            "絵": IntentType.IMAGE_GENERATION,
            "イラスト": IntentType.IMAGE_GENERATION,

            # コード生成
            "コード": IntentType.CODE_GENERATION,
            "プログラム": IntentType.CODE_GENERATION,
            "実装": IntentType.CODE_GENERATION,
            "スクリプト": IntentType.CODE_GENERATION,

            # システム制御
            "再起動": IntentType.SYSTEM_CONTROL,
            "停止": IntentType.SYSTEM_CONTROL,
            "開始": IntentType.SYSTEM_CONTROL,
            "状態": IntentType.SYSTEM_CONTROL,
            "設定": IntentType.SYSTEM_CONTROL,

            # スケジューリング
            "予定": IntentType.SCHEDULING,
            "カレンダー": IntentType.SCHEDULING,
            "スケジュール": IntentType.SCHEDULING,
            "予約": IntentType.SCHEDULING,

            # データ分析
            "分析": IntentType.DATA_ANALYSIS,
            "統計": IntentType.DATA_ANALYSIS,
            "レポート": IntentType.DATA_ANALYSIS,
            "集計": IntentType.DATA_ANALYSIS,

            # ファイル整理
            "終わった": IntentType.FILE_MANAGEMENT,
            "完了": IntentType.FILE_MANAGEMENT,
            "整理": IntentType.FILE_MANAGEMENT,
            "放置": IntentType.FILE_MANAGEMENT,
            "戻して": IntentType.FILE_MANAGEMENT,
            "復元": IntentType.FILE_MANAGEMENT,

            # ファイル検索
            "探して": IntentType.FILE_SEARCH,
            "ファイル": IntentType.FILE_SEARCH,
            "見つけて": IntentType.FILE_SEARCH,

            # INBOX状況確認
            "Inboxどう": IntentType.FILE_STATUS,
            "状況": IntentType.FILE_STATUS,
            "一覧": IntentType.FILE_STATUS,
        }

    def _get_default_prompt_template(self) -> str:
        """デフォルトプロンプトテンプレート"""
        # 人格設定からプロンプトを取得
        if hasattr(self, 'current_persona') and self.current_persona:
            persona_prompt = self.current_persona.get('personality_prompt', '')
            if persona_prompt:
                return f"""{persona_prompt}

あなたは意図分類システムです。ユーザーの入力から意図を分類してください。

利用可能な意図タイプ:
- conversation: 会話・雑談
- task_execution: タスク実行（実行、作って、処理など）
- information_search: 情報検索（検索、調べて、確認など）
- image_generation: 画像生成（画像、生成、描いてなど）
- code_generation: コード生成（コード、実装、プログラムなど）
- system_control: システム制御（再起動、停止、設定など）
- scheduling: スケジューリング（予定、カレンダー、予約など）
- data_analysis: データ分析（分析、統計、レポートなど）
- file_management: ファイル整理（終わった、完了、整理、戻してなど）
- file_search: ファイル検索（探して、ファイル、見つけてなど）
- file_status: INBOX状況確認（Inboxどう、状況、一覧など）
- unknown: 不明

ユーザー入力: {input}

以下のJSON形式で回答してください:
{{
    "intent_type": "意図タイプ",
    "confidence": 0.0-1.0の信頼度,
    "entities": {{"key": "value"}},
    "reasoning": "分類理由",
    "suggested_actions": ["アクション1", "アクション2"]
}}""".replace("{input}", "{input}")

    def _classify_with_keywords(self, text: str) -> Optional[IntentResult]:
        """キーワードベースの高速分類"""
        text_lower = text.lower()

        # キーワードマッチング
        matches = {}
        for keyword, intent_type in self.keyword_mapping.items():
            if keyword in text_lower:
                if intent_type not in matches:
                    matches[intent_type] = []
                matches[intent_type].append(keyword)

        if not matches:
            return None

        # 最も多くマッチした意図を選択
        best_intent = max(matches.items(), key=lambda x: len(x[1]))
        intent_type_str, matched_keywords = best_intent
        try:
            intent_type_enum = IntentType(intent_type_str)
        except ValueError:
            intent_type_enum = IntentType.UNKNOWN

        confidence = min(0.9, 0.5 + len(matched_keywords) * 0.1)

        return IntentResult(
            intent_type=intent_type_enum,
            confidence=confidence,
            entities={"matched_keywords": matched_keywords},
            reasoning=f"キーワードマッチング: {', '.join(matched_keywords)}",
            suggested_actions=self._get_suggested_actions(intent_type_enum),
            timestamp=datetime.now().isoformat()
        )

    def _classify_with_llm(self, text: str) -> IntentResult:
        """LLMベースの分類"""
        # テンプレートの{input}を実際のテキストに置換（安全に）
        # まず{input}だけを一時的なプレースホルダーに置換
        import re
        prompt = re.sub(r'\{input\}', '__INPUT_PLACEHOLDER__', self.intent_prompt_template)
        prompt = prompt.replace('__INPUT_PLACEHOLDER__', text)

        try:
            timeout = timeout_config.get("llm_call", 30.0)
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # 低い温度で一貫性を保つ
                        "num_predict": 500
                    }
                },
                timeout=timeout
            )

            if response.status_code != 200:
                error = error_handler.handle_exception(
                    Exception(f"LLM分類失敗: HTTP {response.status_code}"),
                    context={"service": "Ollama", "url": self.ollama_url, "model": self.model},
                    user_message="意図分類に失敗しました"
                )
                logger.warning(f"LLM分類失敗: {error.message}")
                return self._fallback_classification(text)

            result_text = response.json().get("response", "")

            # JSONを抽出
            try:
                # JSON部分を抽出
                json_start = result_text.find("{")
                json_end = result_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = result_text[json_start:json_end]
                    result_data = json.loads(json_str)
                else:
                    return self._fallback_classification(text)
            except json.JSONDecodeError as e:
                error = error_handler.handle_exception(
                    e,
                    context={"service": "IntentRouter", "method": "_classify_with_llm"},
                    user_message="分類結果の解析に失敗しました"
                )
                logger.warning(f"JSON解析失敗、フォールバック分類を使用: {error.message}")
                return self._fallback_classification(text)

            # IntentResultに変換
            intent_type_str = result_data.get("intent_type", "unknown")
            try:
                intent_type = IntentType(intent_type_str)
            except ValueError:
                intent_type = IntentType.UNKNOWN

            return IntentResult(
                intent_type=intent_type,
                confidence=float(result_data.get("confidence", 0.5)),
                entities=result_data.get("entities", {}),
                reasoning=result_data.get("reasoning", ""),
                suggested_actions=result_data.get("suggested_actions", []),
                timestamp=datetime.now().isoformat()
            )

        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"service": "Ollama", "url": self.ollama_url, "model": self.model},
                user_message="意図分類サービスへの接続に失敗しました"
            )
            logger.error(f"LLM分類エラー: {error.message}")
            return self._fallback_classification(text)

    def _fallback_classification(self, text: str) -> IntentResult:
        """フォールバック分類"""
        return IntentResult(
            intent_type=IntentType.UNKNOWN,
            confidence=0.3,
            entities={},
            reasoning="分類に失敗しました",
            suggested_actions=[],
            timestamp=datetime.now().isoformat()
        )

    def _get_suggested_actions(self, intent_type: IntentType) -> List[str]:
        """意図タイプに基づく推奨アクション"""
        action_map = {
            IntentType.CONVERSATION: ["会話を続ける", "雑談モードに切り替え"],
            IntentType.TASK_EXECUTION: ["タスクを実行", "実行計画を作成"],
            IntentType.INFORMATION_SEARCH: ["RAG検索を実行", "情報を取得"],
            IntentType.IMAGE_GENERATION: ["画像生成ワークフローを実行", "プロンプトを最適化"],
            IntentType.CODE_GENERATION: ["コード生成を実行", "コードレビューを実行"],
            IntentType.SYSTEM_CONTROL: ["システム状態を確認", "制御コマンドを実行"],
            IntentType.SCHEDULING: ["カレンダーを確認", "予定を作成"],
            IntentType.DATA_ANALYSIS: ["データを分析", "レポートを生成"],
            IntentType.FILE_MANAGEMENT: ["ファイル整理を実行", "File Secretary APIを呼び出し"],
            IntentType.FILE_SEARCH: ["ファイル検索を実行", "File Secretary APIを呼び出し"],
            IntentType.FILE_STATUS: ["INBOX状況を取得", "File Secretary APIを呼び出し"],
            IntentType.DEVICE_STATUS: ["デバイス状態を取得", "Pixel 7 リソースを取得", "統合API /api/devices/status を呼び出し"],
            IntentType.UNKNOWN: ["詳細を確認", "ユーザーに質問"]
        }
        return action_map.get(intent_type, [])

    def classify(
        self,
        input_text: str,
        use_keyword_fallback: Optional[bool] = None,
        use_llm: bool = True
    ) -> IntentResult:
        """
        入力テキストを分類

        Args:
            input_text: 分類するテキスト
            use_keyword_fallback: キーワードフォールバックを使用するか（Noneの場合は設定から取得）
            use_llm: LLMを使用するか

        Returns:
            IntentResult: 分類結果
        """
        if not input_text or not input_text.strip():
            return IntentResult(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                entities={},
                reasoning="入力が空です",
                suggested_actions=[],
                timestamp=datetime.now().isoformat()
            )

        # キーワードベースの高速分類を試行
        if use_keyword_fallback is None:
            use_keyword_fallback = self.config.get("use_keyword_fallback", True)

        if use_keyword_fallback:
            keyword_result = self._classify_with_keywords(input_text)
            if keyword_result and keyword_result.confidence >= self.config.get("confidence_threshold", 0.6):
                logger.info(f"✅ キーワード分類成功: {keyword_result.intent_type.value} (信頼度: {keyword_result.confidence:.2f})")
                return keyword_result

        # LLMベースの分類
        if use_llm:
            llm_result = self._classify_with_llm(input_text)
            logger.info(f"✅ LLM分類完了: {llm_result.intent_type.value} (信頼度: {llm_result.confidence:.2f})")
            return llm_result

        # フォールバック
        return self._fallback_classification(input_text)

    def classify_batch(self, inputs: List[str]) -> List[IntentResult]:
        """複数の入力を一括分類"""
        return [self.classify(text) for text in inputs]

    def save_config(self) -> None:
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 設定保存完了: {self.config_path}")
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"config_file": str(self.config_path)},
                user_message="設定ファイルの保存に失敗しました"
            )
            logger.error(f"設定保存エラー: {error.message}")


# Flask APIサーバー
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# グローバルルーターインスタンス
router = None

def init_router() -> 'IntentRouter':
    """ルーターを初期化"""
    global router
    if router is None:
        router = IntentRouter()
    return router

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Intent Router"})

@app.route('/api/classify', methods=['POST'])
def classify_endpoint():
    """意図分類エンドポイント"""
    try:
        data = request.get_json() or {}
        input_text = data.get("text", "")

        if not input_text:
            error = error_handler.handle_exception(
                ValueError("text is required"),
                context={"endpoint": "/api/classify"},
                user_message="入力テキストが必要です"
            )
            return jsonify(error.to_json_response()), 400

        router = init_router()
        result = router.classify(input_text)

        return jsonify(asdict(result))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/classify"},
            user_message="意図分類エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/classify/batch', methods=['POST'])
def classify_batch_endpoint():
    """一括分類エンドポイント"""
    try:
        data = request.get_json() or {}
        inputs = data.get("texts", [])

        if not inputs:
            error = error_handler.handle_exception(
                ValueError("texts is required"),
                context={"endpoint": "/api/classify/batch"},
                user_message="入力テキストリストが必要です"
            )
            return jsonify(error.to_json_response()), 400

        router = init_router()
        results = router.classify_batch(inputs)

        return jsonify({
            "results": [asdict(r) for r in results]
        })
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/classify/batch"},
            user_message="一括分類エンドポイントでエラーが発生しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """設定を取得"""
    router = init_router()
    return jsonify(router.config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """設定を更新"""
    router = init_router()
    new_config = request.get_json() or {}
    router.config.update(new_config)
    router.save_config()
    return jsonify({"status": "updated", "config": router.config})


if __name__ == '__main__':
    import sys

    # コマンドライン引数で直接分類
    if len(sys.argv) > 1:
        router = IntentRouter()
        text = " ".join(sys.argv[1:])
        result = router.classify(text)
        print(f"\n🎯 分類結果:")
        print(f"  意図: {result.intent_type.value}")
        print(f"  信頼度: {result.confidence:.2f}")
        print(f"  理由: {result.reasoning}")
        print(f"  推奨アクション: {', '.join(result.suggested_actions)}")
    else:
        # APIサーバーとして起動
        port = int(os.getenv("PORT", 5100))
        logger.info(f"🎯 Intent Router起動中... (ポート: {port})")
        init_router()
        app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
