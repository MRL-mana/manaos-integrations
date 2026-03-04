#!/usr/bin/env python3
"""
🧠 Remi LLM Integration
本物のLLM（GPT-4/Claude）で戦略提案を生成
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn

# LLM選択
USE_GEMINI = os.getenv("GEMINI_API_KEY", "") != ""
USE_OPENAI = os.getenv("OPENAI_API_KEY", "") != ""
USE_CLAUDE = os.getenv("ANTHROPIC_API_KEY", "") != ""

if USE_GEMINI:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    client = genai.GenerativeModel('gemini-pro')
    LLM_NAME = "Gemini"
elif USE_OPENAI:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    LLM_NAME = "GPT-4"
elif USE_CLAUDE:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    LLM_NAME = "Claude"
else:
    client = None
    LLM_NAME = "Rule-based"

app = FastAPI(title=f"Remi LLM - {LLM_NAME} Powered")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProposalRequest(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None

PROPOSAL_PROMPT = """あなたはRemi（レミ）、ManaOS v3.0の戦略指令AIです。
ユーザーからの機能要望を受け取り、OpenSpec形式のProposalを生成してください。

【ユーザー要望】
{feature}

【出力形式（JSON）】
{{
  "change_id": "kebab-case形式のID（add-/update-/optimize-で始まる）",
  "affected_capabilities": ["影響を受けるcapability名のリスト"],
  "priority": "high/medium/low",
  "implementation_strategy": "実装戦略の説明",
  "requirements": [
    {{
      "name": "requirement名",
      "description": "The system SHALL ...",
      "scenarios": [
        {{
          "name": "scenario名",
          "when": "条件",
          "then": "期待結果"
        }}
      ]
    }}
  ],
  "tasks": ["実装タスク1", "実装タスク2", ...],
  "risks": ["リスク1", "リスク2", ...],
  "technical_notes": "技術的な考慮事項"
}}

【重要】
- change_idは具体的で分かりやすく
- requirementsは明確な動作を定義
- scenariosは検証可能に
- tasksは具体的な実装ステップ
- risksは現実的なリスク分析

JSON形式のみで回答してください。
"""

@app.get("/")
async def root():
    return {
        "service": "Remi LLM",
        "llm": LLM_NAME,
        "role": "戦略指令AI",
        "status": "online",
        "capabilities": ["Proposal生成", "戦略分析", "リスク評価"]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "actor": "remi",
        "llm": LLM_NAME,
        "available": client is not None
    }

@app.post("/propose")
async def propose_with_llm(request: ProposalRequest):
    """LLMを使った本物のProposal生成"""
    feature = request.text
    
    if not client:
        # Fallback to rule-based
        return _generate_rule_based(feature)
    
    try:
        if USE_GEMINI:
            # Google Gemini
            response = client.generate_content(
                PROPOSAL_PROMPT.format(feature=feature),
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    response_mime_type="application/json"
                )
            )
            
            import json
            analysis = json.loads(response.text)
            
        elif USE_OPENAI:
            # OpenAI GPT-4
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # コスト削減
                messages=[
                    {"role": "system", "content": "You are Remi, a strategic AI for spec-driven development."},
                    {"role": "user", "content": PROPOSAL_PROMPT.format(feature=feature)}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            import json
            analysis = json.loads(response.choices[0].message.content)
            
        elif USE_CLAUDE:
            # Claude
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": PROPOSAL_PROMPT.format(feature=feature)}
                ]
            )
            
            import json
            analysis = json.loads(response.content[0].text)
        
        return {
            "status": "success",
            "actor": "remi",
            "llm": LLM_NAME,
            "analysis": analysis,
            "message": f"Remi（{LLM_NAME}）が戦略分析を完了しました"
        }
        
    except Exception as e:
        print(f"❌ LLM Error: {e}")
        # Fallback
        return _generate_rule_based(feature)

def _generate_rule_based(feature: str):
    """Rule-based fallback"""
    import re
    
    words = re.findall(r'\w+', feature.lower())
    if words and words[0] not in ['add', 'update', 'optimize']:
        words.insert(0, 'add')
    change_id = '-'.join(words[:5])
    
    return {
        "status": "success",
        "actor": "remi",
        "llm": "Rule-based (Fallback)",
        "analysis": {
            "change_id": change_id,
            "affected_capabilities": ["general"],
            "priority": "medium",
            "implementation_strategy": "Standard implementation",
            "requirements": [
                {
                    "name": "Core Functionality",
                    "description": f"The system SHALL implement {feature}",
                    "scenarios": [
                        {
                            "name": "Success case",
                            "when": "feature is used",
                            "then": "it works as expected"
                        }
                    ]
                }
            ],
            "tasks": ["Design", "Implement", "Test", "Document"],
            "risks": ["Minimal risk"],
            "technical_notes": "Standard approach"
        },
        "message": "Remi（Rule-based）が分析しました（LLM未設定）"
    }

if __name__ == '__main__':
    print("🧠 Remi LLM Server starting...")
    print(f"🤖 LLM: {LLM_NAME}")
    
    if client:
        print("✅ LLM available")
    else:
        print("⚠️  LLM not configured - using rule-based fallback")
        print("\n設定方法:")
        print("  OpenAI: export OPENAI_API_KEY='sk-...'")
        print("  Claude: export ANTHROPIC_API_KEY='sk-ant-...'")
    
    print("\n🌐 Server: http://localhost:9220")
    
    uvicorn.run(app, host="0.0.0.0", port=9220)

