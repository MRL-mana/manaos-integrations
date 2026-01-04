#!/usr/bin/env python3
"""
🎭 ManaOS 人格システム
「清楚系ギャル」ペルソナの実装・管理
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from flask import Flask, jsonify, request
from flask_cors import CORS

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PersonalitySystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("PersonalitySystem")


class PersonalityTrait(str, Enum):
    """人格特性"""
    PURE = "pure"  # 清楚
    FRIENDLY = "friendly"  # フレンドリー
    CASUAL = "casual"  # カジュアル
    PROFESSIONAL = "professional"  # プロフェッショナル
    HUMOROUS = "humorous"  # ユーモア


@dataclass
class PersonalityProfile:
    """人格プロフィール"""
    name: str
    traits: List[PersonalityTrait]
    tone: str  # 話し方のトーン
    response_style: str  # 応答スタイル
    greeting_patterns: List[str]  # 挨拶パターン
    conversation_starters: List[str]  # 会話の始め方
    personality_prompt: str  # LLM用プロンプト
    created_at: str
    updated_at: str


class PersonalitySystem:
    """人格システム"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path or Path(__file__).parent / "personality_config.json"
        self.config = self._load_config()
        
        # デフォルト人格プロフィール（清楚系ギャル）
        self.default_persona = self._create_default_persona()
        
        # 現在の人格プロフィール
        self.current_persona = self._load_persona() or self.default_persona
        
        logger.info(f"✅ Personality System初期化完了 (人格: {self.current_persona.name})")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 設定ファイルの検証
                schema = {
                    "required": [],
                    "fields": {
                        "default_persona": {"type": str, "default": "pure_gal"},
                        "enable_personality": {"type": bool, "default": True}
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
            "default_persona": "pure_gal",
            "enable_personality": True,
            "persona_storage_path": "persona_profiles.json"
        }
    
    def _create_default_persona(self) -> PersonalityProfile:
        """デフォルト人格プロフィールを作成（清楚系ギャル）"""
        return PersonalityProfile(
            name="pure_gal",
            traits=[PersonalityTrait.PURE, PersonalityTrait.FRIENDLY, PersonalityTrait.CASUAL],
            tone="清楚でフレンドリー、でもカジュアル",
            response_style="報告時は事実のみを淡々と伝える。会話・雑談では普通に話す。",
            greeting_patterns=[
                "こんにちは！",
                "おはよう！",
                "お疲れさま！"
            ],
            conversation_starters=[
                "今日は何する？",
                "調子どう？",
                "何か手伝えることある？"
            ],
            personality_prompt="""あなたは「清楚系ギャル」のペルソナです。

【基本性格】
- 清楚でフレンドリー、でもカジュアル
- 報告時は事実のみを淡々と伝える（誇張表現を厳禁）
- 会話・雑談では普通に話す
- 過度に丁寧な忖度表現は避ける

【話し方のルール】
- 報告時：「完璧に」「素晴らしい」「最高の」などの形容詞は使わない
- 報告時：事実のみを淡々と伝える
- 会話時：普通に話してOK
- ユーザーは「Mana」と呼ぶ（「san」は付けない）

【例】
報告: 「Phase 2.2完了しました。16/16サービスに統一モジュールを適用しました。」
会話: 「調子どう？何か手伝えることある？」""",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
    
    def _load_persona(self) -> Optional[PersonalityProfile]:
        """人格プロフィールを読み込む"""
        storage_path = Path(self.config.get("persona_storage_path", "persona_profiles.json"))
        if storage_path.exists():
            try:
                with open(storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    current_persona_name = self.config.get("default_persona", "pure_gal")
                    persona_data = data.get("profiles", {}).get(current_persona_name)
                    if persona_data:
                        return PersonalityProfile(**persona_data)
            except Exception as e:
                error = error_handler.handle_exception(
                    e,
                    context={"storage_path": str(storage_path)},
                    user_message="人格プロフィールの読み込みに失敗しました"
                )
                logger.warning(f"人格プロフィール読み込みエラー: {error.message}")
        return None
    
    def _save_persona(self):
        """人格プロフィールを保存"""
        storage_path = Path(self.config.get("persona_storage_path", "persona_profiles.json"))
        try:
            if storage_path.exists():
                with open(storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {"profiles": {}}
            
            data["profiles"][self.current_persona.name] = asdict(self.current_persona)
            data["profiles"][self.current_persona.name]["updated_at"] = datetime.now().isoformat()
            
            with open(storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error = error_handler.handle_exception(
                e,
                context={"storage_path": str(storage_path)},
                user_message="人格プロフィールの保存に失敗しました"
            )
            logger.error(f"人格プロフィール保存エラー: {error.message}")
    
    def get_personality_prompt(self) -> str:
        """人格プロンプトを取得"""
        return self.current_persona.personality_prompt
    
    def apply_personality_to_prompt(self, base_prompt: str, context: Optional[str] = None) -> str:
        """
        プロンプトに人格を適用
        
        Args:
            base_prompt: ベースプロンプト
            context: コンテキスト（会話/報告など）
        
        Returns:
            人格が適用されたプロンプト
        """
        if not self.config.get("enable_personality", True):
            return base_prompt
        
        # コンテキストに応じて人格プロンプトを調整
        if context == "report":
            # 報告時は事実のみを伝えるスタイル
            personality_instruction = "報告時は事実のみを淡々と伝えてください。誇張表現は使わないでください。"
        elif context == "conversation":
            # 会話時は普通に話す
            personality_instruction = "会話では普通に話してください。"
        else:
            personality_instruction = self.current_persona.personality_prompt
        
        return f"""{personality_instruction}

{base_prompt}"""
    
    def get_current_persona(self) -> Dict[str, Any]:
        """現在の人格プロフィールを取得"""
        return asdict(self.current_persona)
    
    def update_persona(self, updates: Dict[str, Any]) -> PersonalityProfile:
        """
        人格プロフィールを更新
        
        Args:
            updates: 更新内容
        
        Returns:
            更新された人格プロフィール
        """
        persona_dict = asdict(self.current_persona)
        persona_dict.update(updates)
        persona_dict["updated_at"] = datetime.now().isoformat()
        
        # 型変換
        if "traits" in updates:
            persona_dict["traits"] = [PersonalityTrait(t) if isinstance(t, str) else t for t in updates["traits"]]
        
        self.current_persona = PersonalityProfile(**persona_dict)
        self._save_persona()
        
        logger.info(f"✅ 人格プロフィール更新完了: {self.current_persona.name}")
        return self.current_persona


# Flask APIサーバー
app = Flask(__name__)
CORS(app)

# グローバル人格システムインスタンス
personality_system = None

def init_personality_system():
    """人格システムを初期化"""
    global personality_system
    if personality_system is None:
        personality_system = PersonalitySystem()
    return personality_system

@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "service": "Personality System"})

@app.route('/api/persona', methods=['GET'])
def get_persona():
    """現在の人格プロフィールを取得"""
    try:
        system = init_personality_system()
        persona = system.get_current_persona()
        return jsonify(persona)
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/persona"},
            user_message="人格プロフィールの取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/persona/prompt', methods=['GET'])
def get_personality_prompt():
    """人格プロンプトを取得"""
    try:
        system = init_personality_system()
        prompt = system.get_personality_prompt()
        return jsonify({"prompt": prompt})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/persona/prompt"},
            user_message="人格プロンプトの取得に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/persona/apply', methods=['POST'])
def apply_personality():
    """プロンプトに人格を適用"""
    try:
        data = request.get_json() or {}
        base_prompt = data.get("prompt", "")
        context = data.get("context")
        
        if not base_prompt:
            error = error_handler.handle_exception(
                ValueError("prompt is required"),
                context={"endpoint": "/api/persona/apply"},
                user_message="プロンプトが必要です"
            )
            return jsonify(error.to_json_response()), 400
        
        system = init_personality_system()
        enhanced_prompt = system.apply_personality_to_prompt(base_prompt, context)
        
        return jsonify({"enhanced_prompt": enhanced_prompt})
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/persona/apply"},
            user_message="人格適用に失敗しました"
        )
        return jsonify(error.to_json_response()), 500

@app.route('/api/persona', methods=['POST'])
def update_persona():
    """人格プロフィールを更新"""
    try:
        data = request.get_json() or {}
        
        system = init_personality_system()
        updated_persona = system.update_persona(data)
        
        return jsonify(asdict(updated_persona))
    except Exception as e:
        error = error_handler.handle_exception(
            e,
            context={"endpoint": "/api/persona"},
            user_message="人格プロフィールの更新に失敗しました"
        )
        return jsonify(error.to_json_response()), 500


if __name__ == '__main__':
    import sys
    # WindowsのコンソールエンコーディングをUTF-8に設定
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    port = int(os.getenv("PORT", 5123))
    logger.info(f"Personality System起動中... (ポート: {port})")
    init_personality_system()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")

