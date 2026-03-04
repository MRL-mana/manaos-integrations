#!/usr/bin/env python3
"""
🔍 ManaSearch Nexus - AI Multi-Search System
統合検索システム: Gemini + Tavily + OpenAI + Claude
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

# 環境変数読み込み
env_file = Path("/root/.mana_vault/manaos_v3.env")
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - MANASEARCH - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# APIキー取得
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# AIモデル初期化
gemini_client = None
openai_client = None
anthropic_client = None
tavily_client = None

try:
    if GOOGLE_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_client = genai.GenerativeModel("gemini-2.0-flash-exp")
        logger.info("✅ Gemini API 初期化完了")
except Exception as e:
    logger.warning(f"⚠️ Gemini API 初期化失敗: {e}")

try:
    if OPENAI_API_KEY:
        import openai
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI API 初期化完了")
except Exception as e:
    logger.warning(f"⚠️ OpenAI API 初期化失敗: {e}")

try:
    if ANTHROPIC_API_KEY:
        import anthropic
        anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("✅ Anthropic API 初期化完了")
except Exception as e:
    logger.warning(f"⚠️ Anthropic API 初期化失敗: {e}")

try:
    if TAVILY_API_KEY:
        from tavily import TavilyClient
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        logger.info("✅ Tavily API 初期化完了")
except Exception as e:
    logger.warning(f"⚠️ Tavily API 初期化失敗: {e}")


async def search_with_gemini(query: str) -> Dict[str, Any]:
    """Gemini (Mina) で検索"""
    if not gemini_client:
        return {"error": "Gemini API not configured", "model": "mina"}

    try:
        start_time = time.time()
        response = gemini_client.generate_content(query)
        answer = response.text
        processing_time = int((time.time() - start_time) * 1000)

        return {
            "model": "mina",
            "answer": answer,
            "confidence": 0.80,
            "sources": [],
            "processing_time_ms": processing_time,
            "error": None
        }
    except Exception as e:
        logger.error(f"Gemini検索エラー: {e}")
        return {
            "model": "mina",
            "answer": "",
            "confidence": 0.0,
            "sources": [],
            "processing_time_ms": 0,
            "error": str(e)
        }


async def search_with_openai(query: str) -> Dict[str, Any]:
    """OpenAI GPT (Remi) で検索"""
    if not openai_client:
        return {"error": "OpenAI API not configured", "model": "remi"}

    try:
        start_time = time.time()
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": query}],
            max_tokens=1000
        )
        answer = response.choices[0].message.content
        processing_time = int((time.time() - start_time) * 1000)

        return {
            "model": "remi",
            "answer": answer,
            "confidence": 0.85,
            "sources": [],
            "processing_time_ms": processing_time,
            "error": None
        }
    except Exception as e:
        logger.error(f"OpenAI検索エラー: {e}")
        return {
            "model": "remi",
            "answer": "",
            "confidence": 0.0,
            "sources": [],
            "processing_time_ms": 0,
            "error": str(e)
        }


async def search_with_anthropic(query: str) -> Dict[str, Any]:
    """Anthropic Claude (Luna) で検索"""
    if not anthropic_client:
        return {"error": "Anthropic API not configured", "model": "luna"}

    try:
        start_time = time.time()
        message = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[{"role": "user", "content": query}]
        )
        answer = message.content[0].text
        processing_time = int((time.time() - start_time) * 1000)

        return {
            "model": "luna",
            "answer": answer,
            "confidence": 0.90,
            "sources": [],
            "processing_time_ms": processing_time,
            "error": None
        }
    except Exception as e:
        logger.error(f"Anthropic検索エラー: {e}")
        return {
            "model": "luna",
            "answer": "",
            "confidence": 0.0,
            "sources": [],
            "processing_time_ms": 0,
            "error": str(e)
        }


async def search_with_tavily(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Tavily Web検索"""
    if not tavily_client:
        return []

    try:
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced"
        )

        results = []
        for result in response.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("content", "")[:200],
                "relevance_score": result.get("score", 0.0)
            })

        return results
    except Exception as e:
        logger.error(f"Tavily検索エラー: {e}")
        return []


def calculate_confidence_score(ai_responses: Dict[str, Any], web_results: List[Dict]) -> float:
    """信頼スコアを計算"""
    if not ai_responses:
        return 0.0

    # AI回答の信頼度の平均
    ai_confidences = [
        resp.get("confidence", 0.0)
        for resp in ai_responses.values()
        if resp.get("error") is None
    ]

    if not ai_confidences:
        return 0.0

    ai_avg = sum(ai_confidences) / len(ai_confidences)

    # Web検索結果があると信頼度が上がる
    web_bonus = min(len(web_results) * 0.05, 0.15)

    return min(ai_avg + web_bonus, 1.0)


def generate_summary(ai_responses: Dict[str, Any], web_results: List[Dict]) -> str:
    """統合回答を生成（Machi統合エンジン）"""
    if not ai_responses:
        return "回答を取得できませんでした。"

    # エラーがない回答のみを使用
    valid_responses = [
        resp for resp in ai_responses.values()
        if resp.get("error") is None and resp.get("answer")
    ]

    if not valid_responses:
        return "すべてのAIで回答を取得できませんでした。"

    # 最も信頼度の高い回答をベースに
    best_response = max(
        valid_responses, key=lambda x: x.get("confidence", 0.0))
    summary = best_response.get("answer", "")

    # 他の回答の重要な情報を追加
    for resp in valid_responses:
        if resp != best_response:
            answer = resp.get("answer", "")
            if len(answer) > 100:
                summary += f"\n\n別の見解: {answer[:200]}..."

    return summary


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェック"""
    status = {
        "remi": "configured" if openai_client else "not configured",
        "luna": "configured" if anthropic_client else "not configured",
        "mina": "configured" if gemini_client else "not configured",
        "tavily": "configured" if tavily_client else "not configured",
        "status": "healthy" if (gemini_client or openai_client or anthropic_client) else "degraded"
    }
    return jsonify(status)


@app.route("/search", methods=["POST"])
def search():
    """検索エンドポイント"""
    try:
        data = request.get_json() or {}
        query = data.get("query", "")
        options = data.get("options", {})

        if not query:
            return jsonify({"error": "query is required"}), 400

        use_web = options.get("web_search", True)
        models = options.get("ai_models", ["remi", "luna", "mina"])
        max_results = options.get("max_results", 5)

        start_time = time.time()

        # 並列でAI検索実行（新しいイベントループを作成）
        tasks = []
        if "remi" in models:
            tasks.append(search_with_openai(query))
        if "luna" in models:
            tasks.append(search_with_anthropic(query))
        if "mina" in models:
            tasks.append(search_with_gemini(query))

        # 新しいイベントループを作成して実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Web検索
            web_results = []
            if use_web:
                web_results = loop.run_until_complete(
                    search_with_tavily(query, max_results))

            # AI検索結果取得
            ai_results = loop.run_until_complete(
                asyncio.gather(*tasks)) if tasks else []
        finally:
            loop.close()

        # 結果を辞書に変換
        ai_responses = {}
        for result in ai_results:
            if isinstance(result, dict) and "model" in result:
                ai_responses[result["model"]] = result

        # 統合処理
        summary = generate_summary(ai_responses, web_results)
        confidence_score = calculate_confidence_score(
            ai_responses, web_results)

        total_time = int((time.time() - start_time) * 1000)

        # レスポンス構築
        response = {
            "query": query,
            "summary": summary,
            "ai_responses": ai_responses,
            "web_results": web_results,
            "consensus": "複数のAIが一致した見解" if len(ai_responses) > 1 else "",
            "differences": "各AIの見解に差異あり" if len(ai_responses) > 1 else "",
            "confidence_score": confidence_score,
            "citations": [
                {"id": str(i+1), "url": r.get("url", ""),
                 "title": r.get("title", "")}
                for i, r in enumerate(web_results[:5])
            ],
            "timestamp": datetime.now().isoformat(),
            "total_processing_time_ms": total_time
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"検索エラー: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# WebUIテンプレート
WEBUI_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔍 ManaSearch Nexus</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            text-align: center;
            color: #667eea;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
        }
        button {
            padding: 15px 30px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
        }
        button:hover { background: #5568d3; }
        .options {
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .option-group {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .results {
            margin-top: 30px;
        }
        .result-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .confidence {
            display: inline-block;
            padding: 5px 15px;
            background: #50C878;
            color: white;
            border-radius: 20px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 18px;
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 ManaSearch Nexus</h1>
        <div class="search-box">
            <input type="text" id="query" placeholder="質問を入力...">
            <button onclick="search()">検索</button>
        </div>
        <div class="options">
            <div class="option-group">
                <label><input type="checkbox" id="remi" checked> Remi</label>
                <label><input type="checkbox" id="luna" checked> Luna</label>
                <label><input type="checkbox" id="mina" checked> Mina</label>
            </div>
            <div class="option-group">
                <label><input type="checkbox" id="web" checked> Web検索を含める</label>
            </div>
        </div>
        <div id="results" class="results"></div>
    </div>
    <script>
        async function search() {
            const query = document.getElementById('query').value;
            if (!query) return;

            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<div class="loading">検索中...</div>';

            const models = [];
            if (document.getElementById('remi').checked) models.push('remi');
            if (document.getElementById('luna').checked) models.push('luna');
            if (document.getElementById('mina').checked) models.push('mina');

            try {
                const response = await fetch('/search', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        query: query,
                        options: {
                            web_search: document.getElementById('web').checked,
                            ai_models: models
                        }
                    })
                });

                const data = await response.json();

                let html = `
                    <div class="result-card">
                        <div class="confidence">信頼スコア: ${(data.confidence_score * 100).toFixed(0)}%</div>
                        <h2>📝 統合回答</h2>
                        <p>${data.summary.replace(/\\n/g, '<br>')}</p>
                    </div>
                `;

                if (data.ai_responses) {
                    html += '<h3>🤖 各AIの回答</h3>';
                    for (const [model, resp] of Object.entries(data.ai_responses)) {
                        if (resp.error) continue;
                        html += `
                            <div class="result-card">
                                <h4>${model.toUpperCase()}</h4>
                                <p>${resp.answer.replace(/\\n/g, '<br>')}</p>
                            </div>
                        `;
                    }
                }

                if (data.web_results && data.web_results.length > 0) {
                    html += '<h3>🌐 Web検索結果</h3>';
                    data.web_results.forEach(r => {
                        html += `
                            <div class="result-card">
                                <h4><a href="${r.url}" target="_blank">${r.title}</a></h4>
                                <p>${r.snippet}</p>
                            </div>
                        `;
                    });
                }

                resultsDiv.innerHTML = html;
            } catch (error) {
                resultsDiv.innerHTML = `<div class="result-card" style="background:#ffebee;color:#c62828;">
                    <h3>エラー</h3><p>${error.message}</p>
                </div>`;
            }
        }

        document.getElementById('query').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') search();
        });
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    """WebUI"""
    return render_template_string(WEBUI_TEMPLATE)


if __name__ == "__main__":
    logger.info("🚀 ManaSearch Nexus 起動 (ポート: 9111)")
    app.run(host="0.0.0.0", port=9111, debug=False)
