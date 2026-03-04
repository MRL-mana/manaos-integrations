#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 External Learning Pipeline
Web検索・GitHub探索 → 要約 → Obsidian統合の自動化パイプライン
"""

import sys
import io
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import os
import json
import time
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import urllib.request
import urllib.parse

# 設定（環境変数から取得、デフォルト値あり）
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault"))
OUT_DIR = VAULT_PATH / "ManaOS" / "System" / "ExternalLearning"
INTEGRATIONS_DIR = Path(os.getenv("MANAOS_INTEGRATIONS_DIR", r"C:\Users\mana4\Desktop\manaos_integrations"))

# API設定（環境変数から取得、なければ空）
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def http_get_json(url: str, headers: Optional[Dict] = None, timeout: int = 10) -> dict:
    """Get JSON from API with error handling"""
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        print(f"  Warning: API request failed: {e}")
        return {}


def search_web_serpapi(query: str, lang: str = "en") -> List[Dict[str, Any]]:
    """Web検索（SerpAPI使用）"""
    if not SERPAPI_KEY:
        print(f"  Warning: SERPAPI_KEY not set, skipping web search")
        return []

    try:
        params = {
            "engine": "google",
            "q": query,
            "api_key": SERPAPI_KEY,
            "hl": lang,
            "num": 10
        }
        url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
        results = http_get_json(url)

        organic_results = results.get("organic_results", [])
        return [
            {
                "title": r.get("title", ""),
                "link": r.get("link", ""),
                "snippet": r.get("snippet", "")
            }
            for r in organic_results[:5]  # 上位5件
        ]
    except Exception as e:
        print(f"  Error in web search: {e}")
        return []


def search_web_fallback(query: str) -> List[Dict[str, Any]]:
    """Web検索（フォールバック：DuckDuckGo HTML scraping）"""
    try:
        # DuckDuckGoの簡易検索（APIキー不要）
        params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(params)
        results = http_get_json(url)

        # DuckDuckGoの結果を整形
        related_topics = results.get("RelatedTopics", [])
        out = []
        for topic in related_topics[:5]:
            if isinstance(topic, dict) and "Text" in topic:
                out.append({
                    "title": topic.get("Text", ""),
                    "link": topic.get("FirstURL", ""),
                    "snippet": topic.get("Text", "")
                })
        return out
    except Exception as e:
        print(f"  Error in fallback search: {e}")
        return []


def search_github(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """GitHub検索"""
    if not GITHUB_TOKEN:
        print(f"  Warning: GITHUB_TOKEN not set, skipping GitHub search")
        return []

    try:
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={max_results}"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {GITHUB_TOKEN}" if GITHUB_TOKEN else ""
        }
        results = http_get_json(url, headers=headers)

        repos = results.get("items", [])
        return [
            {
                "name": r.get("full_name", ""),
                "url": r.get("html_url", ""),
                "description": r.get("description", ""),
                "stars": r.get("stargazers_count", 0),
                "language": r.get("language", ""),
                "topics": r.get("topics", [])[:5]
            }
            for r in repos
        ]
    except Exception as e:
        print(f"  Error in GitHub search: {e}")
        return []


def generate_queries() -> List[Dict[str, str]]:
    """検索クエリを自動生成"""
    queries = [
        # 学習増強
        {"query": "AI self improvement architecture", "category": "learning", "lang": "en"},
        {"query": "system that learns from logs examples", "category": "learning", "lang": "en"},
        {"query": "background reinforcement learning python", "category": "learning", "lang": "en"},

        # バックグラウンドタスク
        {"query": "python idle scheduler example", "category": "scheduler", "lang": "en"},
        {"query": "cpu idle task python low usage", "category": "scheduler", "lang": "en"},

        # メトリクス分析
        {"query": "log pattern anomaly detection python", "category": "metrics", "lang": "en"},
        {"query": "time series metric trend identification", "category": "metrics", "lang": "en"},

        # Playbook/運用
        {"query": "log rotation backup script examples", "category": "playbook", "lang": "en"},
        {"query": "obsidian automation workflow templates", "category": "playbook", "lang": "en"},

        # 日本語クエリ
        {"query": "Python バックグラウンドタスク スケジューラ", "category": "scheduler", "lang": "ja"},
        {"query": "ログ分析 パターン検出 Python", "category": "metrics", "lang": "ja"},
    ]
    return queries


def summarize_results(web_results: List[Dict], github_results: List[Dict], query: str) -> str:
    """検索結果を要約"""
    summary_parts = []

    if web_results:
        summary_parts.append("## Web検索結果\n\n")
        for i, r in enumerate(web_results[:3], 1):  # 上位3件
            summary_parts.append(f"{i}. **{r.get('title', 'No title')}**\n")
            summary_parts.append(f"   - URL: {r.get('link', '')}\n")
            summary_parts.append(f"   - 概要: {r.get('snippet', '')[:200]}...\n\n")

    if github_results:
        summary_parts.append("## GitHub実装例\n\n")
        for i, r in enumerate(github_results[:3], 1):  # 上位3件
            summary_parts.append(f"{i}. **{r.get('name', 'No name')}** ⭐{r.get('stars', 0)}\n")
            summary_parts.append(f"   - URL: {r.get('url', '')}\n")
            summary_parts.append(f"   - 説明: {r.get('description', '')}\n")
            summary_parts.append(f"   - 言語: {r.get('language', 'N/A')}\n")
            if r.get('topics'):
                summary_parts.append(f"   - トピック: {', '.join(r.get('topics', []))}\n")
            summary_parts.append("\n")

    return "".join(summary_parts)


def extract_insights(web_results: List[Dict], github_results: List[Dict]) -> List[str]:
    """検索結果からインサイトを抽出"""
    insights = []

    # Web検索から
    for r in web_results[:3]:
        snippet = r.get("snippet", "").lower()
        if "self-improving" in snippet or "self learning" in snippet:
            insights.append("自己改善システムの実装パターンが見つかりました")
        if "reinforcement learning" in snippet:
            insights.append("強化学習による改善手法の情報があります")
        if "log analysis" in snippet or "pattern detection" in snippet:
            insights.append("ログ分析・パターン検出の手法が見つかりました")

    # GitHubから
    for r in github_results[:3]:
        desc = r.get("description", "").lower()
        topics = [t.lower() for t in r.get("topics", [])]
        if "scheduler" in desc or "scheduler" in " ".join(topics):
            insights.append("スケジューラ実装の参考リポジトリが見つかりました")
        if "learning" in desc or "learning" in " ".join(topics):
            insights.append("学習システムの実装例が見つかりました")

    return list(set(insights))  # 重複除去


def save_to_obsidian(content: str, filename: str) -> Path:
    """Obsidianにノートを保存"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    file_path = OUT_DIR / filename
    file_path.write_text(content, encoding="utf-8", newline="\n")
    return file_path


def main():
    """Main function"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"System 3 External Learning Pipeline - {now}")
    print("=" * 60)

    queries = generate_queries()
    all_results = []

    for i, q_info in enumerate(queries, 1):
        query = q_info["query"]
        category = q_info["category"]
        lang = q_info.get("lang", "en")

        print(f"\n[{i}/{len(queries)}] Searching: {query}")
        print(f"  Category: {category}, Language: {lang}")

        # Web検索
        web_results = []
        if SERPAPI_KEY:
            web_results = search_web_serpapi(query, lang)
        else:
            web_results = search_web_fallback(query)

        print(f"  Web results: {len(web_results)}")

        # GitHub検索
        github_results = search_github(query)
        print(f"  GitHub results: {len(github_results)}")

        if web_results or github_results:
            all_results.append({
                "query": query,
                "category": category,
                "lang": lang,
                "web_results": web_results,
                "github_results": github_results
            })

        # APIレート制限対策
        time.sleep(1)

    # 結果をまとめてObsidianに保存
    if all_results:
        md_content = []
        md_content.append(f"# System 3 External Learning\n\n")
        md_content.append(f"**生成**: {now}  \n")
        md_content.append(f"**Autonomy Level**: Level 1（内部メンテナンス限定）\n\n")
        md_content.append(f"---\n\n")

        # カテゴリ別に整理
        by_category = {}
        for result in all_results:
            cat = result["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(result)

        # カテゴリごとにセクション作成
        for category, results in by_category.items():
            md_content.append(f"## 📚 {category.upper()}\n\n")

            for result in results:
                query = result["query"]
                md_content.append(f"### Query: {query}\n\n")

                summary = summarize_results(
                    result["web_results"],
                    result["github_results"],
                    query
                )
                md_content.append(summary)

                insights = extract_insights(
                    result["web_results"],
                    result["github_results"]
                )
                if insights:
                    md_content.append("### Key Insights\n\n")
                    for insight in insights:
                        md_content.append(f"- {insight}\n")
                    md_content.append("\n")

                md_content.append("---\n\n")

        # System 3学習への提案
        md_content.append("## 🧠 System 3 Learn\n\n")
        md_content.append("### 実装候補\n\n")
        md_content.append("- Web検索結果から実装パターンを抽出\n")
        md_content.append("- GitHub実装例を参考にコード改善\n")
        md_content.append("- 最新の研究・手法をSystem 3に統合\n\n")

        md_content.append("### 次のアクション\n\n")
        md_content.append("- [ ] 検索結果をレビュー\n")
        md_content.append("- [ ] 有用な実装例を特定\n")
        md_content.append("- [ ] System 3への統合を検討\n\n")

        # ファイル保存
        filename = f"System3_ExternalLearning_{today}.md"
        file_path = save_to_obsidian("".join(md_content), filename)

        print(f"\n✅ External Learningレポートを生成しました: {file_path}")
        print(f"   検索クエリ数: {len(queries)}")
        print(f"   結果あり: {len(all_results)}")

        # System 3への自動統合
        print(f"\n[6] System 3への自動統合中...")
        try:
            from system3_external_learning_integration import main as integrate_main
            integrate_main()
        except ImportError:
            print("  ⚠️  統合モジュールが見つかりません（スキップ）")
        except Exception as e:
            print(f"  ⚠️  統合エラー: {e}")
    else:
        print("\n⚠️ 検索結果がありませんでした")

    return str(file_path) if all_results else None


if __name__ == "__main__":
    try:
        result = main()
        if result:
            print(f"\n✅ 完了: {result}")
        else:
            print(f"\n⚠️ 完了（結果なし）")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
