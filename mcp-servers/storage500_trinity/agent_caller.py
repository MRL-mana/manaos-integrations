#!/usr/bin/env python3
"""
Trinity Orchestrator - Agent Caller
OpenAI/Claude APIを呼び出してエージェントと通信
"""

import json
import os
import sys
from typing import Dict, Optional, Any
from enum import Enum

# 再利用モジュールを使用
sys.path.insert(0, '/root/trinity_legacy/reusable')
try:
    from api_wrapper import APIWrapper, APIProvider
    USE_API_WRAPPER = True
except ImportError:
    from openai import OpenAI
    USE_API_WRAPPER = False

from prompts import get_prompt


class AgentCaller:
    """エージェント呼び出しクラス（マルチプロバイダー対応）"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", provider: str = "openai"):
        """
        初期化
        
        Args:
            api_key: APIキー（環境変数から自動取得可能）
            model: 使用するモデル
            provider: プロバイダー（openai/claude/gemini）
        """
        self.provider = provider
        self.model = model
        
        # 再利用モジュールがあれば使う
        if USE_API_WRAPPER:
            provider_map = {
                "openai": APIProvider.OPENAI,  # type: ignore[possibly-unbound]
                "claude": APIProvider.CLAUDE,  # type: ignore[possibly-unbound]
                "anthropic": APIProvider.CLAUDE,  # type: ignore[possibly-unbound]
                "gemini": APIProvider.GEMINI,  # type: ignore[possibly-unbound]
                "google": APIProvider.GEMINI  # type: ignore[possibly-unbound]
            }
            
            api_provider = provider_map.get(provider.lower(), APIProvider.OPENAI)  # type: ignore[possibly-unbound]
            self.api_wrapper = APIWrapper(api_provider, api_key, model)  # type: ignore[possibly-unbound]
            self.use_wrapper = True
        else:
            # Fallback: OpenAI直接
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            
            self.client = OpenAI(api_key=self.api_key)  # type: ignore[possibly-unbound]
            self.use_wrapper = False
    
    def call_agent(self, role: str, action: str, **kwargs) -> Dict[str, Any]:
        """
        エージェントを呼び出す
        
        Args:
            role: remi/luna/mina
            action: plan/execute/review
            **kwargs: プロンプトに埋め込む変数
            
        Returns:
            エージェントのレスポンス（辞書）
        """
        try:
            # プロンプト取得
            prompt = get_prompt(role, action, **kwargs)
            
            # マルチプロバイダー対応
            if self.use_wrapper:
                # 再利用モジュール経由
                api_response = self.api_wrapper.chat([
                    {"role": "system", "content": "あなたはTrinity開発チームのAIエージェントです。必ずJSON形式で回答してください。"},
                    {"role": "user", "content": prompt}
                ], temperature=0.7, json_mode=(self.provider == "openai"))
                
                content = api_response["content"]
                result = json.loads(content)
                
                return {
                    "success": True,
                    "result": result,
                    "raw_response": content,
                    "usage": api_response.get("usage", {}),
                    "provider": self.provider
                }
            else:
                # OpenAI直接（Fallback）
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "あなたはTrinity開発チームのAIエージェントです。必ずJSON形式で回答してください。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                result = json.loads(content)  # type: ignore
                
                return {
                    "success": True,
                    "result": result,
                    "raw_response": content,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,  # type: ignore[union-attr]
                        "completion_tokens": response.usage.completion_tokens,  # type: ignore[union-attr]
                        "total_tokens": response.usage.total_tokens  # type: ignore[union-attr]
                    },
                    "provider": "openai"
                }
            
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON parse error: {str(e)}",
                "raw_response": content if 'content' in locals() else None  # type: ignore[possibly-unbound]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "raw_response": None
            }
    
    def call_remi_plan(self, goal: str, context: list, history_summary: str = "なし") -> Dict:
        """
        Remiにプランニングを依頼
        
        Args:
            goal: 達成目標
            context: 前提条件
            history_summary: 履歴サマリー
            
        Returns:
            プラン（辞書）
        """
        return self.call_agent(
            "remi",
            "plan",
            goal=goal,
            context=", ".join(context) if context else "なし",
            history_summary=history_summary
        )
    
    def call_remi_review(self, goal: str, artifacts: list, execution_log: str) -> Dict:
        """
        Remiにレビューを依頼
        
        Args:
            goal: 達成目標
            artifacts: 成果物リスト
            execution_log: 実行ログ
            
        Returns:
            レビュー結果（辞書）
        """
        artifacts_str = "\n".join([
            f"- {a.get('type', 'file')}: {a.get('path', 'N/A')} ({a.get('description', '')})"
            for a in artifacts
        ])
        
        return self.call_agent(
            "remi",
            "review",
            goal=goal,
            artifacts=artifacts_str or "なし",
            execution_log=execution_log or "なし"
        )
    
    def call_luna_execute(self, goal: str, step: Dict, context: list) -> Dict:
        """
        Lunaに実行を依頼
        
        Args:
            goal: 達成目標
            step: 実行するステップ
            context: コンテキスト
            
        Returns:
            実行結果（辞書）
        """
        step_str = f"""
ID: {step.get('id', 'N/A')}
Title: {step.get('title', 'N/A')}
Why: {step.get('why', 'N/A')}
Tool: {step.get('tool', 'N/A')}
Success Check: {step.get('success_check', 'N/A')}
        """.strip()
        
        return self.call_agent(
            "luna",
            "execute",
            goal=goal,
            step=step_str,
            context=", ".join(context) if context else "なし"
        )
    
    def call_mina_review(self, goal: str, artifacts: list, plan: Dict, code: str) -> Dict:
        """
        MinaにQAレビューを依頼
        
        Args:
            goal: 達成目標
            artifacts: 成果物リスト
            plan: 元のプラン
            code: 実装されたコード
            
        Returns:
            QAレビュー結果（辞書）
        """
        artifacts_str = "\n".join([
            f"- {a.get('type', 'file')}: {a.get('path', 'N/A')} ({a.get('description', '')})"
            for a in artifacts
        ])
        
        plan_str = json.dumps(plan, ensure_ascii=False, indent=2) if plan else "なし"
        
        return self.call_agent(
            "mina",
            "review",
            goal=goal,
            artifacts=artifacts_str or "なし",
            plan=plan_str,
            code=code or "なし"
        )


if __name__ == "__main__":
    # テスト
    import sys
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set")
        sys.exit(1)
    
    caller = AgentCaller()
    
    # Remiにプランニングを依頼
    print("🎯 Testing Remi Planner...")
    result = caller.call_remi_plan(
        goal="シンプルな計算機アプリを作成",
        context=["Python", "CLI"],
        history_summary="新規プロジェクト"
    )
    
    if result["success"]:
        print("✅ Success!")
        print(json.dumps(result["result"], ensure_ascii=False, indent=2))
        print(f"\n📊 Usage: {result['usage']['total_tokens']} tokens")
    else:
        print(f"❌ Error: {result['error']}")

