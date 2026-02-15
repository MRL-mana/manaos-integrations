#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎭 ManaOS 人格システム（強化版）
予測的応答・学習連携・動的人格調整
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler, ErrorCategory, ErrorSeverity

# 最適化モジュールのインポート
from unified_cache_system import get_unified_cache
from config_cache import get_config_cache
from learning_system_enhanced import LearningSystemEnhanced

# ロガーの初期化
logger = get_logger(__name__)

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("PersonalitySystemEnhanced")

# キャッシュシステムの取得
cache_system = get_unified_cache()
config_cache = get_config_cache()


class PersonalitySystemEnhanced:
    """人格システム（強化版）"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        from personality_system import PersonalitySystem
        
        # 基本システム
        self.base_system = PersonalitySystem(config_path)
        
        # 学習システム
        self.learning = LearningSystemEnhanced()
        
        # 使用パターン
        self.usage_patterns = {}
        
        logger.info(f"✅ Personality System Enhanced初期化完了")
    
    def get_personality_response(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        人格を反映した応答を生成（予測的）
        
        Args:
            user_message: ユーザーメッセージ
            context: コンテキスト
        
        Returns:
            人格を反映した応答
        """
        persona = self.base_system.get_current_persona()
        
        # 予測的応答スタイルを決定
        predicted_style = self._predict_response_style(user_message, context)
        
        # 応答を生成
        response = {
            "message": user_message,
            "personality": {
                "name": persona.name,
                "tone": persona.tone,
                "response_style": predicted_style
            },
            "personality_prompt": persona.personality_prompt,
            "timestamp": datetime.now().isoformat()
        }
        
        # 使用パターンを記録
        self.learning.record_usage(
            action="personality_response",
            context={"message": user_message, "context": context},
            result=response
        )
        
        return response
    
    def _predict_response_style(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        応答スタイルを予測
        
        Args:
            user_message: ユーザーメッセージ
            context: コンテキスト
        
        Returns:
            予測された応答スタイル
        """
        # メッセージのタイプを判定
        message_lower = user_message.lower()
        
        # 報告系のメッセージ
        if any(keyword in message_lower for keyword in ["報告", "完了", "結果", "状態"]):
            return "報告時は事実のみを淡々と伝える"
        
        # 質問系のメッセージ
        if any(keyword in message_lower for keyword in ["？", "?", "どう", "何", "なぜ"]):
            return "会話・雑談では普通に話す"
        
        # デフォルト
        return "会話・雑談では普通に話す"
    
    def adapt_personality(
        self,
        user_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ユーザーフィードバックに基づいて人格を適応
        
        Args:
            user_feedback: ユーザーフィードバック
        
        Returns:
            適応結果
        """
        persona = self.base_system.get_current_persona()
        
        # フィードバックを分析
        feedback_type = user_feedback.get("type", "neutral")
        feedback_content = user_feedback.get("content", "")
        
        # 学習システムに記録
        self.learning.record_usage(
            action="personality_feedback",
            context={"feedback": user_feedback},
            result={"status": "recorded"}
        )
        
        # 適応（簡易実装）
        adaptations = []
        
        if feedback_type == "positive":
            adaptations.append("ユーザーが好むスタイルを維持")
        elif feedback_type == "negative":
            adaptations.append("応答スタイルの調整を検討")
        
        return {
            "personality": persona.name,
            "adaptations": adaptations,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_personality_stats(self) -> Dict[str, Any]:
        """人格統計情報を取得"""
        persona = self.base_system.get_current_persona()
        
        # 学習統計を取得
        learning_stats = self.learning.get_optimization_suggestions()
        
        return {
            "current_persona": {
                "name": persona.name,
                "traits": [t.value for t in persona.traits],
                "tone": persona.tone
            },
            "usage_stats": {
                "total_responses": sum(
                    len(records) for records in self.learning.usage_patterns.values()
                    if "personality" in records[0].get("action", "")
                ) if self.learning.usage_patterns else 0
            },
            "learning_suggestions": learning_stats,
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("人格システム（強化版）テスト")
    print("=" * 60)
    
    personality = PersonalitySystemEnhanced()
    
    # 応答を生成
    response = personality.get_personality_response("調子どう？")
    print(f"応答: {response['personality']['response_style']}")
    
    # 統計情報を取得
    stats = personality.get_personality_stats()
    print(f"\n統計情報:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()






















