#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System 3 External Learning Integration
外部学習レポートをSystem 3のLearning Systemに自動統合
"""

import sys
import io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import os
from pathlib import Path
from datetime import datetime, date, timedelta
import json
import urllib.request
from typing import Dict, List, Any, Optional
import re

# 設定（環境変数から取得、デフォルト値あり）
VAULT_PATH = Path(os.getenv("OBSIDIAN_VAULT_PATH", r"C:\Users\mana4\Documents\Obsidian Vault"))
EXTERNAL_LEARNING_DIR = VAULT_PATH / "ManaOS" / "System" / "ExternalLearning"
LEARNING_SYSTEM_URL = "http://localhost:5126"
RAG_MEMORY_URL = "http://localhost:5103"  # RAG Memory API


def http_post_json(url: str, data: Dict[str, Any], timeout: int = 10) -> Optional[Dict[str, Any]]:
    """POST JSON to API"""
    try:
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        print(f"  Warning: API request failed: {e}")
        return None


def http_get_json(url: str, timeout: int = 10) -> Dict[str, Any]:
    """Get JSON from API"""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def parse_external_learning_report(md_file: Path) -> List[Dict[str, Any]]:
    """外部学習レポートをパースして学習データを抽出"""
    if not md_file.exists():
        return []

    try:
        content = md_file.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Error reading file: {e}")
        return []

    learnings = []

    # GitHub実装例から学習（複数のパターンに対応）
    # パターン1: "## GitHub実装例"
    # パターン2: "## GitHub実装例"（英語）
    github_patterns = [
        r'## GitHub実装例\n\n(.*?)(?=\n##|\n---|\Z)',
        r'## GitHub Implementation Examples\n\n(.*?)(?=\n##|\n---|\Z)',
        r'## GitHub.*?\n\n(.*?)(?=\n##|\n---|\Z)',
    ]

    for pattern in github_patterns:
        github_section = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if github_section:
            github_text = github_section.group(1)
            # リポジトリ情報を抽出（複数のパターン）
            repo_patterns = [
                r'\*\*([^\*]+)\*\*.*?URL: (https://github\.com/[^\s]+)',
                r'(\d+)\.\s*\*\*([^\*]+)\*\*.*?URL: (https://github\.com/[^\s]+)',
                r'https://github\.com/([^\s/]+/[^\s/]+)',
            ]

            for repo_pattern in repo_patterns:
                repos = re.findall(repo_pattern, github_text)
                for match in repos[:10]:  # 上位10件
                    if isinstance(match, tuple):
                        if len(match) == 3:  # パターン2
                            repo_name = match[1]
                            repo_url = match[2]
                        elif len(match) == 2:  # パターン1
                            repo_name = match[0]
                            repo_url = match[1]
                        else:
                            continue
                    else:  # パターン3
                        repo_url = f"https://github.com/{match}"
                        repo_name = match.split('/')[-1]

                    learnings.append({
                        "type": "github_repository",
                        "source": "external_learning",
                        "title": repo_name,
                        "url": repo_url,
                        "category": "implementation_example",
                        "timestamp": datetime.now().isoformat()
                    })

            if learnings:
                break

    # Web検索結果から学習
    web_patterns = [
        r'## Web検索結果\n\n(.*?)(?=\n##|\n---|\Z)',
        r'## Web Search Results\n\n(.*?)(?=\n##|\n---|\Z)',
    ]

    for pattern in web_patterns:
        web_section = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if web_section:
            web_text = web_section.group(1)
            # URLを抽出（複数のパターン）
            url_patterns = [
                r'URL: (https?://[^\s]+)',
                r'- URL: (https?://[^\s]+)',
                r'(https?://[^\s]+)',
            ]

            for url_pattern in url_patterns:
                urls = re.findall(url_pattern, web_text)
                for url in urls[:10]:  # 上位10件
                    if url.startswith('http'):
                        learnings.append({
                            "type": "web_article",
                            "source": "external_learning",
                            "url": url,
                            "category": "research",
                            "timestamp": datetime.now().isoformat()
                        })

            if any(l.get("type") == "web_article" for l in learnings):
                break

    # インサイトから学習
    insights_patterns = [
        r'### Key Insights\n\n(.*?)(?=\n###|\n---|\Z)',
        r'### インサイト\n\n(.*?)(?=\n###|\n---|\Z)',
    ]

    for pattern in insights_patterns:
        insights_section = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if insights_section:
            insights_text = insights_section.group(1)
            # インサイトを抽出
            insight_pattern = r'- (.+?)(?=\n-|\n\n|\Z)'
            insights = re.findall(insight_pattern, insights_text)
            for insight in insights:
                insight_clean = insight.strip()
                if len(insight_clean) > 10:  # 最小長さチェック
                    learnings.append({
                        "type": "insight",
                        "source": "external_learning",
                        "content": insight_clean,
                        "category": "learning",
                        "timestamp": datetime.now().isoformat()
                    })

            if any(l.get("type") == "insight" for l in learnings):
                break

    # 重複除去（URLベース）
    seen_urls = set()
    unique_learnings = []
    for learning in learnings:
        url = learning.get("url") or learning.get("content", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_learnings.append(learning)
        elif not url:
            unique_learnings.append(learning)

    return unique_learnings


def record_to_learning_system(learnings: List[Dict[str, Any]]) -> int:
    """Learning Systemに記録"""
    recorded = 0

    for learning in learnings:
        try:
            # Learning System APIに記録
            result = http_post_json(
                f"{LEARNING_SYSTEM_URL}/api/record",
                {
                    "action": f"external_learning_{learning['type']}",
                    "context": {
                        "source": learning.get("source", "external_learning"),
                        "category": learning.get("category", "unknown"),
                        "url": learning.get("url", ""),
                        "title": learning.get("title", ""),
                        "content": learning.get("content", "")
                    },
                    "result": {
                        "status": "success",
                        "learning_id": learning.get("url") or learning.get("content", "")[:50]
                    }
                }
            )

            if result:
                recorded += 1
        except Exception as e:
            print(f"  Warning: Failed to record learning: {e}")

    return recorded


def add_to_rag_system(learnings: List[Dict[str, Any]]) -> int:
    """RAGシステムに追加"""
    added = 0

    for learning in learnings:
        try:
            # 学習データをRAGシステムに追加
            content_parts = []

            if learning.get("title"):
                content_parts.append(f"タイトル: {learning['title']}")
            if learning.get("url"):
                content_parts.append(f"URL: {learning['url']}")
            if learning.get("content"):
                content_parts.append(f"内容: {learning['content']}")

            content = "\n".join(content_parts)
            if not content:
                continue

            # RAG Memory APIに追加
            result = http_post_json(
                f"{RAG_MEMORY_URL}/api/add",
                {
                    "content": content,
                    "importance_score": 0.7,  # 外部学習は重要度を高めに設定
                    "metadata": {
                        "source": learning.get("source", "external_learning"),
                        "type": learning.get("type", "unknown"),
                        "category": learning.get("category", "unknown"),
                        "timestamp": learning.get("timestamp", datetime.now().isoformat())
                    }
                }
            )

            if result:
                added += 1
        except Exception as e:
            print(f"  Warning: Failed to add to RAG system: {e}")

    return added


def main():
    """Main function"""
    today = date.today().isoformat()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"System 3 External Learning Integration - {now}")
    print("=" * 60)

    # 最新のレポートを取得
    report_file = EXTERNAL_LEARNING_DIR / f"System3_ExternalLearning_{today}.md"

    if not report_file.exists():
        print(f"\n⚠️  レポートが見つかりません: {report_file}")
        print("   外部学習パイプラインが実行されるまで待ってください。")
        return None

    print(f"\n[1] レポートを読み込み中: {report_file.name}")

    # レポートをパース
    learnings = parse_external_learning_report(report_file)
    print(f"   抽出された学習データ: {len(learnings)}件")

    if not learnings:
        print("\n⚠️  学習データが見つかりませんでした")
        return None

    # Learning Systemに記録
    print(f"\n[2] Learning Systemに記録中...")
    recorded = record_to_learning_system(learnings)
    print(f"   記録完了: {recorded}/{len(learnings)}件")

    # RAGシステムに追加
    print(f"\n[3] RAGシステムに追加中...")
    rag_added = add_to_rag_system(learnings)
    print(f"   追加完了: {rag_added}/{len(learnings)}件")

    # 統合完了マークを追加
    integration_mark = f"\n\n---\n\n**統合完了**: {now}\n"
    try:
        content = report_file.read_text(encoding="utf-8")
        if "統合完了" not in content:
            content += integration_mark
            report_file.write_text(content, encoding="utf-8")
            print(f"\n✅ レポートに統合完了マークを追加しました")
    except Exception as e:
        print(f"\n⚠️  レポート更新エラー: {e}")

    print(f"\n✅ 統合完了:")
    print(f"   - Learning System: {recorded}件記録")
    print(f"   - RAGシステム: {rag_added}件追加")

    return {"learning_system": recorded, "rag_system": rag_added}


if __name__ == "__main__":
    try:
        result = main()
        if result is not None:
            if isinstance(result, dict):
                print(f"\n✅ 完了:")
                print(f"   - Learning System: {result.get('learning_system', 0)}件")
                print(f"   - RAGシステム: {result.get('rag_system', 0)}件")
            else:
                print(f"\n✅ 完了: {result}件記録")
        else:
            print(f"\n⚠️  完了（データなし）")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
