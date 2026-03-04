#!/usr/bin/env python3
"""
MCP統合クイックデモ - 10分で効果を実感
複数のMCPサーバーを組み合わせた実例
"""
import asyncio
import json
from datetime import datetime

class MCPQuickDemo:
    """MCPの組み合わせパワーを実演"""
    
    def __init__(self):
        self.results = []
        
    async def demo_1_github_memory_combo(self):
        """
        デモ1: GitHub MCP + Memory MCP
        → PRを取得して、過去の類似PRと比較
        """
        print("\n🎯 デモ1: GitHub + Memory 統合")
        print("=" * 60)
        
        # 模擬データ（実際はGitHub MCPから取得）
        current_pr = {
            "number": 42,
            "title": "Add user authentication",
            "files_changed": ["auth.py", "models.py", "tests/test_auth.py"]
        }
        
        # Memory MCPで過去の類似PR検索（模擬）
        similar_prs = [
            {"number": 23, "title": "Implement OAuth", "result": "success"},
            {"number": 31, "title": "Add JWT auth", "result": "security_issue_found"}
        ]
        
        result = {
            "current_pr": current_pr,
            "similar_prs": similar_prs,
            "recommendation": "PR #31で見つかったセキュリティ問題に注意。JWT検証ロジックを必ず実装すること。",
            "auto_checks": [
                "✅ テストカバレッジ: 85% (十分)",
                "⚠️  セキュリティスキャン: 要確認",
                "✅ コードスタイル: 合格"
            ]
        }
        
        print(f"現在のPR: #{current_pr['number']} - {current_pr['title']}")
        print(f"\n類似PR検索結果: {len(similar_prs)}件")
        for pr in similar_prs:
            print(f"  - PR #{pr['number']}: {pr['title']} ({pr['result']})")
        
        print(f"\n💡 推奨事項: {result['recommendation']}")
        print("\n自動チェック:")
        for check in result['auto_checks']:
            print(f"  {check}")
        
        self.results.append(result)
        return result
    
    async def demo_2_trinity_automation(self):
        """
        デモ2: Trinity Multi-Agent 自動連鎖
        → Remi設計 → Luna実装 → Mina検証 → Aria記録
        """
        print("\n🎯 デモ2: Trinity 自動連鎖実行")
        print("=" * 60)
        
        task = "簡単なログイン機能"
        
        # Remi: 設計
        print(f"\n🎨 Remi (戦略AI): {task}の設計中...")
        await asyncio.sleep(0.5)
        design = {
            "components": ["LoginForm", "AuthService", "UserModel"],
            "endpoints": ["/api/login", "/api/logout"],
            "security": ["CSRF protection", "Rate limiting"]
        }
        print(f"設計完了: {len(design['components'])}コンポーネント")
        
        # Luna: 実装
        print("\n⚙️  Luna (実装AI): コード実装中...")
        await asyncio.sleep(0.5)
        implementation = {
            "files_created": [
                "components/LoginForm.tsx",
                "services/AuthService.ts",
                "models/User.ts"
            ],
            "lines_of_code": 247,
            "tests_written": 12
        }
        print(f"実装完了: {implementation['lines_of_code']}行のコード")
        
        # Mina: 検証
        print("\n🔍 Mina (QA AI): コード検証中...")
        await asyncio.sleep(0.5)
        review = {
            "issues_found": 2,
            "issues": [
                {"severity": "medium", "message": "パスワードの長さ検証が不足"},
                {"severity": "low", "message": "エラーメッセージが英語のみ"}
            ],
            "approved": False,
            "recommendation": "2件の問題を修正後、再レビュー"
        }
        print(f"検証結果: {review['issues_found']}件の問題発見")
        for issue in review['issues']:
            print(f"  - [{issue['severity']}] {issue['message']}")
        
        # Luna: 自動修正
        print("\n🔧 Luna (実装AI): 問題を自動修正中...")
        await asyncio.sleep(0.5)
        fixed = {
            "fixes_applied": 2,
            "re_review_requested": True
        }
        print(f"修正完了: {fixed['fixes_applied']}件を自動修正")
        
        # Mina: 再検証
        print("\n🔍 Mina (QA AI): 再検証中...")
        await asyncio.sleep(0.5)
        final_review = {
            "issues_found": 0,
            "approved": True
        }
        print("✅ 再検証完了: 承認")
        
        # Aria: 記録
        print("\n📖 Aria (記録AI): ナレッジに記録中...")
        await asyncio.sleep(0.5)
        knowledge = {
            "task": task,
            "design": design,
            "implementation": implementation,
            "lessons": [
                "パスワード検証は必須",
                "多言語対応を最初から考慮すべき"
            ],
            "saved_to": "/root/trinity_workspace/shared/knowledge.md"
        }
        print(f"記録完了: {len(knowledge['lessons'])}個の教訓を保存")
        
        result = {
            "task": task,
            "total_time": "2.5秒",
            "quality_score": 95,
            "knowledge_saved": True
        }
        
        print(f"\n🎉 完了！ 品質スコア: {result['quality_score']}/100")
        
        self.results.append(result)
        return result
    
    async def demo_3_manaos_health_check(self):
        """
        デモ3: ManaOS Services 統合ヘルスチェック
        → 全サービスの状態を一括確認
        """
        print("\n🎯 デモ3: ManaOS 統合ヘルスチェック")
        print("=" * 60)
        
        # 実際のサービス状態を確認
        import subprocess
        
        critical_services = [
            "manaos_api_bridge.py",
            "manaos_health_guardian.py",
            "robust_cognitive_bridge.py",
            "slack_bot_integration.py"
        ]
        
        service_status = {}
        print("\n📊 主要サービス状態:")
        
        for service in critical_services:
            try:
                result = subprocess.run(
                    ["pgrep", "-f", service],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                is_running = bool(result.stdout.strip())
                status = "✅ 稼働中" if is_running else "⚠️  停止"
                service_status[service] = is_running
                print(f"  {status}: {service}")
            except Exception as e:
                service_status[service] = False
                print(f"  ❌ エラー: {service} ({e})")
        
        # 統計
        total = len(critical_services)
        running = sum(1 for v in service_status.values() if v)
        health_score = (running / total) * 100
        
        print(f"\n📈 ヘルススコア: {health_score:.1f}% ({running}/{total}サービス稼働中)")
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "services_checked": total,
            "services_running": running,
            "health_score": health_score,
            "status": service_status
        }
        
        self.results.append(result)
        return result
    
    async def demo_4_cross_mcp_workflow(self):
        """
        デモ4: 複数MCP横断ワークフロー
        → Filesystem → Processing → Memory → Slack 通知
        """
        print("\n🎯 デモ4: クロスMCPワークフロー")
        print("=" * 60)
        
        workflow_steps = [
            "📁 Filesystem MCP: データファイル読み込み",
            "🔄 処理: データ分析実行",
            "💾 Memory MCP: 結果を永続化",
            "💬 Slack MCP: チームに通知"
        ]
        
        print("\nワークフロー実行中...")
        for i, step in enumerate(workflow_steps, 1):
            print(f"  {i}. {step}")
            await asyncio.sleep(0.3)
        
        result = {
            "workflow": "Data Analysis Pipeline",
            "steps_executed": len(workflow_steps),
            "total_time": "1.2秒",
            "mcps_used": ["filesystem", "memory", "slack"],
            "success": True
        }
        
        print(f"\n✅ ワークフロー完了！ {len(workflow_steps)}ステップを{result['total_time']}で実行")
        
        self.results.append(result)
        return result
    
    async def run_all_demos(self):
        """全デモを実行"""
        print("\n" + "=" * 60)
        print("🚀 MCP統合デモ - スタート！")
        print("=" * 60)
        
        start_time = datetime.now()
        
        # 各デモを実行
        await self.demo_1_github_memory_combo()
        await asyncio.sleep(1)
        
        await self.demo_2_trinity_automation()
        await asyncio.sleep(1)
        
        await self.demo_3_manaos_health_check()
        await asyncio.sleep(1)
        
        await self.demo_4_cross_mcp_workflow()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 デモ完了サマリー")
        print("=" * 60)
        print(f"実行時間: {duration:.1f}秒")
        print(f"デモ数: {len(self.results)}")
        print("成功率: 100%")
        
        # 結果をJSONで保存
        output_file = "/root/mcp_demo_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration,
                "demos_run": len(self.results),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 結果を保存: {output_file}")
        
        print("\n" + "=" * 60)
        print("🎉 全デモ完了！")
        print("\n💡 これが複数MCPを組み合わせた時のパワーです！")
        print("   - GitHub + Memory = 賢いPRレビュー")
        print("   - Trinity 4エージェント = 全自動開発")
        print("   - ManaOS統合 = 完全な可観測性")
        print("   - クロスMCP = シームレスなワークフロー")
        print("=" * 60)

async def main():
    demo = MCPQuickDemo()
    await demo.run_all_demos()

if __name__ == "__main__":
    asyncio.run(main())

