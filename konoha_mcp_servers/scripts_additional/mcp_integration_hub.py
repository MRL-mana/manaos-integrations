#!/usr/bin/env python3
"""
MCP Integration Hub
全MCPサーバーを統合し、相互連携を実現する中央ハブ
"""

import asyncio
import json
import subprocess
import httpx
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class MCPIntegrationHub:
    """全MCPを統合管理するハブ"""
    
    def __init__(self):
        self.ai_learning_data_dir = Path("/root/ai_learning_system/data")
        self.trinity_workspace = Path("/root/trinity_workspace")
        self.manaos_services = {
            "api_bridge": "http://localhost:7000",
            "unified_api_gateway": "http://localhost:8009",
            "slack_bot": "http://localhost:5555",
            "screen_sharing": "http://localhost:5008"
        }
        self.integration_log = Path("/root/logs/mcp_integration_hub.log")
        self.integration_log.parent.mkdir(exist_ok=True)
    
    def log(self, message: str):
        """ログ出力"""
        timestamp = datetime.now().isoformat()
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        with open(self.integration_log, 'a') as f:
            f.write(log_message + "\n")
    
    # ========================================
    # AI Learning MCP 統合
    # ========================================
    
    async def ai_learn_pattern(self, pattern: str, pattern_type: str = "general", 
                               context: Dict = None, confidence: float = 0.8):
        """AI Learning MCPにパターンを学習させる"""
        self.log(f"AI Learning: パターン学習開始 - {pattern}")
        
        patterns_file = self.ai_learning_data_dir / "learned_patterns.json"
        
        with open(patterns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        new_pattern = {
            "id": f"pattern_{datetime.now().timestamp()}",
            "timestamp": datetime.now().isoformat(),
            "type": pattern_type,
            "pattern": pattern,
            "context": context or {},
            "frequency": 1,
            "confidence": confidence
        }
        
        # 重複チェック
        existing = next((p for p in data['patterns'] 
                        if p['pattern'] == pattern and p['type'] == pattern_type), None)
        
        if existing:
            existing['frequency'] += 1
            existing['confidence'] = min(1.0, existing['confidence'] + 0.05)
            existing['lastSeen'] = datetime.now().isoformat()
            result = {"action": "updated", "pattern": existing}
        else:
            data['patterns'].append(new_pattern)
            result = {"action": "created", "pattern": new_pattern}
        
        data['lastUpdated'] = datetime.now().isoformat()
        
        with open(patterns_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.log(f"AI Learning: パターン学習完了 - {result['action']}")
        return result
    
    async def ai_search_patterns(self, query: str = None, pattern_type: str = None, 
                                 min_confidence: float = 0.0, limit: int = 10):
        """AI Learning MCPからパターンを検索"""
        self.log(f"AI Learning: パターン検索 - query={query}, type={pattern_type}")
        
        patterns_file = self.ai_learning_data_dir / "learned_patterns.json"
        
        with open(patterns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = data['patterns']
        
        # フィルタリング
        if pattern_type:
            results = [p for p in results if p.get('type') == pattern_type]
        if min_confidence:
            results = [p for p in results if p.get('confidence', 0) >= min_confidence]
        if query:
            results = [p for p in results if query.lower() in p.get('pattern', '').lower()]
        
        # スコアでソート
        results = sorted(results, key=lambda p: p.get('frequency', 1) * p.get('confidence', 0.5), reverse=True)
        
        self.log(f"AI Learning: パターン検索完了 - {len(results)}件")
        return {
            "total": len(results),
            "patterns": results[:limit]
        }
    
    # ========================================
    # Trinity統合（ファイルベース）
    # ========================================
    
    async def trinity_get_tasks(self):
        """Trinityのタスクリストを取得"""
        tasks_file = self.trinity_workspace / "shared" / "tasks.json"
        
        if not tasks_file.exists():
            return {"tasks": []}
        
        with open(tasks_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    async def trinity_add_task(self, title: str, description: str = "", 
                              assigned_to: str = "Luna", priority: str = "medium"):
        """Trinityに新しいタスクを追加"""
        self.log(f"Trinity: タスク追加 - {title}")
        
        tasks_file = self.trinity_workspace / "shared" / "tasks.json"
        tasks_file.parent.mkdir(parents=True, exist_ok=True)
        
        if tasks_file.exists():
            with open(tasks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {"tasks": []}
        
        new_task = {
            "id": f"task_{datetime.now().timestamp()}",
            "title": title,
            "description": description,
            "status": "todo",
            "assigned_to": assigned_to,
            "priority": priority,
            "created_at": datetime.now().isoformat()
        }
        
        data['tasks'].append(new_task)
        
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.log(f"Trinity: タスク追加完了 - ID: {new_task['id']}")
        return new_task
    
    async def trinity_update_task_status(self, task_id: str, new_status: str):
        """Trinityのタスク状態を更新"""
        self.log(f"Trinity: タスク更新 - {task_id} -> {new_status}")
        
        tasks_file = self.trinity_workspace / "shared" / "tasks.json"
        
        with open(tasks_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        task = next((t for t in data['tasks'] if t['id'] == task_id), None)
        
        if task:
            task['status'] = new_status
            task['updated_at'] = datetime.now().isoformat()
            
            with open(tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.log("Trinity: タスク更新完了")
            return task
        else:
            self.log(f"Trinity: タスクが見つかりません - {task_id}")
            return None
    
    # ========================================
    # ManaOS Services統合
    # ========================================
    
    async def manaos_get_service_status(self, service_name: str):
        """ManaOSサービスの状態を取得"""
        self.log(f"ManaOS: サービス状態確認 - {service_name}")
        
        try:
            result = subprocess.run(
                ["pgrep", "-f", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            is_running = bool(result.stdout.strip())
            
            return {
                "service": service_name,
                "status": "running" if is_running else "stopped",
                "pid": result.stdout.strip() if is_running else None
            }
        except Exception as e:
            self.log(f"ManaOS: サービス状態確認エラー - {e}")
            return {
                "service": service_name,
                "status": "error",
                "error": str(e)
            }
    
    async def manaos_api_call(self, api_name: str, endpoint: str, 
                             method: str = "GET", data: Dict = None):
        """ManaOS APIを呼び出し"""
        self.log(f"ManaOS: API呼び出し - {api_name}/{endpoint}")
        
        base_url = self.manaos_services.get(api_name)
        if not base_url:
            return {"error": f"Unknown API: {api_name}"}
        
        url = f"{base_url}/{endpoint.lstrip('/')}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    response = await client.post(url, json=data or {})
                elif method == "PUT":
                    response = await client.put(url, json=data or {})
                elif method == "DELETE":
                    response = await client.delete(url)
                
                self.log(f"ManaOS: API呼び出し完了 - status={response.status_code}")
                
                return {
                    "status_code": response.status_code,
                    "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                }
        except Exception as e:
            self.log(f"ManaOS: API呼び出しエラー - {e}")
            return {
                "error": str(e)
            }
    
    # ========================================
    # 統合ワークフロー
    # ========================================
    
    async def workflow_code_review(self, file_path: str):
        """
        統合ワークフロー: コードレビュー
        AI Learning MCPで過去のパターンを検索 → Trinityでタスク作成
        """
        self.log(f"ワークフロー開始: コードレビュー - {file_path}")
        
        # 1. ファイル読み込み
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return {"error": f"ファイル読み込みエラー: {e}"}
        
        # 2. AI Learning MCPで類似コードパターンを検索
        patterns = await self.ai_search_patterns(query="code review", pattern_type="code")
        
        # 3. 簡易チェック
        issues = []
        if 'TODO' in code or 'FIXME' in code:
            issues.append("未完了のコメントがあります")
        if len(code.split('\n')) > 500:
            issues.append("ファイルが長すぎます")
        
        # 4. Trinityにタスク作成
        if issues:
            task = await self.trinity_add_task(
                title=f"コードレビュー: {Path(file_path).name}",
                description=f"問題点: {', '.join(issues)}",
                assigned_to="Mina",
                priority="high" if len(issues) > 2 else "medium"
            )
        else:
            task = None
        
        # 5. パターンを学習
        review_pattern = f"コードレビュー完了: {len(issues)}個の問題"
        await self.ai_learn_pattern(
            pattern=review_pattern,
            pattern_type="workflow",
            context={"file": file_path, "issues_count": len(issues)},
            confidence=0.85
        )
        
        result = {
            "file": file_path,
            "lines": len(code.split('\n')),
            "issues": issues,
            "similar_patterns": len(patterns['patterns']),
            "trinity_task": task['id'] if task else None,
            "status": "needs_review" if issues else "approved"
        }
        
        self.log(f"ワークフロー完了: コードレビュー - {result['status']}")
        return result
    
    async def workflow_auto_pr_review(self, pr_title: str, pr_files: List[str]):
        """
        統合ワークフロー: GitHub PR自動レビュー
        Memory検索（模擬） → AI Learning検索 → Trinity統合
        """
        self.log(f"ワークフロー開始: PR自動レビュー - {pr_title}")
        
        # 1. AI Learning MCPで類似PRパターンを検索
        patterns = await self.ai_search_patterns(query="PR", pattern_type="workflow")
        
        # 2. 各ファイルをレビュー
        file_reviews = []
        for file_path in pr_files:
            if Path(file_path).exists():
                review = await self.workflow_code_review(file_path)
                file_reviews.append(review)
        
        # 3. 総合判定
        total_issues = sum(len(r.get('issues', [])) for r in file_reviews)
        
        # 4. Trinityにタスク作成
        if total_issues > 0:
            task = await self.trinity_add_task(
                title=f"PR修正: {pr_title}",
                description=f"{len(pr_files)}ファイル中{total_issues}個の問題",
                assigned_to="Luna",
                priority="high"
            )
        else:
            task = None
        
        # 5. パターンを学習
        await self.ai_learn_pattern(
            pattern=f"PR自動レビュー: {total_issues}個の問題",
            pattern_type="workflow",
            context={"pr": pr_title, "files": len(pr_files)},
            confidence=0.9
        )
        
        result = {
            "pr_title": pr_title,
            "files_reviewed": len(file_reviews),
            "total_issues": total_issues,
            "file_reviews": file_reviews,
            "trinity_task": task['id'] if task else None,
            "recommendation": "要修正" if total_issues > 0 else "承認可能",
            "similar_patterns": len(patterns['patterns'])
        }
        
        self.log(f"ワークフロー完了: PR自動レビュー - {result['recommendation']}")
        return result
    
    # ========================================
    # ステータス・統計
    # ========================================
    
    async def get_integration_status(self):
        """統合ハブの全体状態を取得"""
        self.log("統合ステータス取得")
        
        # AI Learning MCP状態
        ai_learning_status = await self.manaos_get_service_status("ai_learning")
        
        # パターン統計
        patterns = await self.ai_search_patterns(limit=1000)
        
        # Trinityタスク統計
        trinity_tasks = await self.trinity_get_tasks()
        task_stats = {
            "total": len(trinity_tasks.get('tasks', [])),
            "by_status": {}
        }
        for task in trinity_tasks.get('tasks', []):
            status = task.get('status', 'unknown')
            task_stats['by_status'][status] = task_stats['by_status'].get(status, 0) + 1
        
        # ManaOSサービス状態
        manaos_services = {}
        for service_key in ["api_bridge", "slack_bot", "screen_sharing"]:
            service_status = await self.manaos_get_service_status(service_key)
            manaos_services[service_key] = service_status['status']
        
        return {
            "timestamp": datetime.now().isoformat(),
            "ai_learning_mcp": ai_learning_status,
            "ai_patterns": {
                "total": patterns['total'],
                "top_patterns": patterns['patterns'][:5]
            },
            "trinity": task_stats,
            "manaos_services": manaos_services,
            "integration_hub_version": "1.0.0"
        }

# ========================================
# CLI インターフェース
# ========================================

async def main():
    hub = MCPIntegrationHub()
    
    print("\n" + "=" * 60)
    print("🎯 MCP Integration Hub - 起動")
    print("=" * 60)
    
    # ステータス表示
    status = await hub.get_integration_status()
    print("\n📊 統合ステータス:")
    print(f"   AI Learning MCP: {status['ai_learning_mcp']['status']}")
    print(f"   学習済みパターン: {status['ai_patterns']['total']}個")
    print(f"   Trinityタスク: {status['trinity']['total']}個")
    print(f"   ManaOSサービス: {len([s for s in status['manaos_services'].values() if s == 'running'])}/{len(status['manaos_services'])} 稼働中")
    
    # デモワークフロー実行
    print("\n🚀 デモワークフロー実行")
    print("=" * 60)
    
    # 1. コードレビューワークフロー
    print("\n1️⃣ コードレビューワークフロー")
    review_result = await hub.workflow_code_review("/root/mcp_quick_demo.py")
    print(f"   ファイル: {review_result['file']}")
    print(f"   行数: {review_result['lines']}")
    print(f"   問題: {len(review_result['issues'])}個")
    print(f"   判定: {review_result['status']}")
    
    # 2. PR自動レビューワークフロー
    print("\n2️⃣ PR自動レビューワークフロー")
    pr_result = await hub.workflow_auto_pr_review(
        pr_title="MCP統合機能追加",
        pr_files=["/root/mcp_integration_hub.py", "/root/mcp_quick_demo.py"]
    )
    print(f"   PR: {pr_result['pr_title']}")
    print(f"   レビュー済みファイル: {pr_result['files_reviewed']}個")
    print(f"   総問題数: {pr_result['total_issues']}個")
    print(f"   推奨: {pr_result['recommendation']}")
    
    # 最終ステータス
    print("\n" + "=" * 60)
    print("✅ MCP Integration Hub - デモ完了")
    print("=" * 60)
    print(f"\nログ: {hub.integration_log}")
    print("\n💡 使い方:")
    print("   hub = MCPIntegrationHub()")
    print("   await hub.workflow_code_review('path/to/file.py')")
    print("   await hub.ai_learn_pattern('新しいパターン')")
    print("   await hub.get_integration_status()")

if __name__ == "__main__":
    asyncio.run(main())

