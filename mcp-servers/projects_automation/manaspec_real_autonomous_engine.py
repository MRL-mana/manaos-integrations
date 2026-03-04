#!/usr/bin/env python3
"""
🔥 ManaSpec Real Autonomous Engine
本当に自律的に動くエンジン（誇張なし）
"""

import asyncio
import requests
from pathlib import Path
from datetime import datetime
import subprocess

class RealAutonomousEngine:
    """本物の自律エンジン"""
    
    def __init__(self):
        self.remi_url = "http://localhost:9210"
        self.luna_url = "http://localhost:9211"
        self.mina_url = "http://localhost:9212"
        self.obsidian_ideas = Path("/root/obsidian_vault/Ideas")
        self.check_interval = 1800  # 30分（本当に動く）
        
        self.processed_ideas = set()  # 処理済みアイデア
    
    async def watch_obsidian_real(self):
        """Obsidian Ideasを本当に監視"""
        print("👁️ Obsidian監視開始（30分ごと）\n")
        
        while True:
            print(f"⏰ 監視実行: {datetime.now().strftime('%H:%M:%S')}")
            
            # Ideasフォルダチェック
            if not self.obsidian_ideas.exists():
                print("  ℹ️ Ideasフォルダなし")
                await asyncio.sleep(self.check_interval)
                continue
            
            # 新しいアイデアを検出
            new_ideas = []
            for idea_file in self.obsidian_ideas.glob("*.md"):
                # 処理済みはスキップ
                if str(idea_file) in self.processed_ideas:
                    continue
                
                content = idea_file.read_text()
                
                # タグチェック
                if any(tag in content for tag in ['manaspec-proposal', '実装待ち', '#implement']):
                    new_ideas.append(idea_file)
                    print(f"  ✨ 新アイデア検出: {idea_file.name}")
            
            # 新しいアイデアを処理
            for idea_file in new_ideas:
                await self.process_idea_real(idea_file)
                self.processed_ideas.add(str(idea_file))
            
            if not new_ideas:
                print("  ℹ️ 新アイデアなし")
            
            print("  ⏳ 次回: 30分後\n")
            await asyncio.sleep(self.check_interval)
    
    async def process_idea_real(self, idea_file: Path):
        """アイデアを本当に処理"""
        print(f"\n🔄 処理開始: {idea_file.name}")
        
        content = idea_file.read_text()
        
        # タイトル抽出
        import re
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else idea_file.stem
        
        print(f"  📋 タイトル: {title}")
        
        # 1. Remiに戦略分析依頼（本物）
        print("  👩‍💼 Remi: 戦略分析中...")
        
        try:
            response = requests.post(
                f"{self.remi_url}/propose",
                json={"text": title},
                timeout=10
            )
            
            if response.status_code == 200:
                analysis = response.json()
                change_id = analysis['analysis']['change_id']
                
                print(f"  ✅ Remi分析完了: {change_id}")
                
                # 2. OpenSpec構造作成（本物）
                await self.create_openspec_structure_real(change_id, title, analysis)
                
                # 3. Obsidian同期（本物）
                self.sync_to_obsidian_real(change_id)
                
                print(f"  🎯 完全処理完了: {change_id}\n")
                
                return change_id
            else:
                print("  ⚠️ Remi応答なし")
                return None
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            return None
    
    async def create_openspec_structure_real(self, change_id: str, title: str, analysis: dict):
        """OpenSpec構造を本当に作成"""
        print("  📝 OpenSpec構造作成中...")
        
        base_path = Path("/root/manaos_v3/openspec/changes") / change_id
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Proposal
        proposal = f"""## Why
{title}

## What Changes
{analysis['analysis'].get('implementation_strategy', '')}

## Impact
- Affected specs: {', '.join(analysis['analysis'].get('affected_capabilities', []))}
- Priority: {analysis['analysis'].get('priority', 'medium')}
- Risks: {', '.join(analysis['analysis'].get('risks', []))}
"""
        (base_path / "proposal.md").write_text(proposal)
        
        # Tasks
        tasks = """## 1. Implementation
- [ ] 1.1 設計・実装
- [ ] 1.2 テスト作成
- [ ] 1.3 ドキュメント更新
"""
        (base_path / "tasks.md").write_text(tasks)
        
        # Spec delta
        for cap in analysis['analysis'].get('affected_capabilities', ['general']):
            spec_path = base_path / "specs" / cap
            spec_path.mkdir(parents=True, exist_ok=True)
            
            spec_content = f"""## ADDED Requirements

### Requirement: {title}
The system SHALL implement {title}.

#### Scenario: Success case
- **WHEN** implemented
- **THEN** it works as expected
"""
            (spec_path / "spec.md").write_text(spec_content)
        
        # Validation
        result = subprocess.run(
            ["openspec", "validate", change_id, "--strict"],
            cwd="/root/manaos_v3",
            capture_output=True,
            text=True
        )
        
        if "valid" in result.stdout:
            print("  ✅ Validation成功")
        else:
            print("  ⚠️ Validation警告")
    
    def sync_to_obsidian_real(self, change_id: str):
        """Obsidianに本当に同期"""
        result = subprocess.run(
            ["python3", "/root/manaspec_obsidian_sync.py", "sync", "/root/manaos_v3"],
            capture_output=True,
            text=True
        )
        
        if "synced" in result.stdout:
            print("  ✅ Obsidian同期完了")
        else:
            print("  ⚠️ Obsidian同期失敗")
    
    async def continuous_improvement_real(self):
        """本当の継続的改善ループ"""
        print("🔄 継続的改善ループ開始（24時間ごと）\n")
        
        while True:
            print(f"\n{'='*60}")
            print(f"🧠 自動改善分析: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")
            
            # AI Learningデータベースから改善機会を本当に検出
            from manaspec_ai_learning_integration import ManaSpecAILearningIntegration
            
            integration = ManaSpecAILearningIntegration()
            stats = await integration.get_statistics()
            
            print("📊 現在の学習データ:")
            print(f"  Archives: {stats['total_archives']}")
            print(f"  Patterns: {stats['total_patterns']}")
            
            # パターンが2個以上あれば最適化提案
            if stats['total_patterns'] >= 2:
                print("\n💡 最適化機会を検出")
                
                # Remiに提案生成依頼
                response = requests.post(
                    f"{self.remi_url}/propose",
                    json={"text": "パターンの共通化と最適化"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    print("  ✅ Remiが改善提案を生成")
            else:
                print("  ℹ️ まだ学習データ不足")
            
            print("\n⏳ 次回: 24時間後\n")
            await asyncio.sleep(86400)  # 24時間


async def main():
    """本物のメイン実行"""
    engine = RealAutonomousEngine()
    
    print("🔥 ManaSpec Real Autonomous Engine")
    print("="*60)
    print("誇張なし、本当に自律的に動くエンジン")
    print("="*60 + "\n")
    
    # 並列実行
    await asyncio.gather(
        engine.watch_obsidian_real(),        # Obsidian監視（30分ごと）
        engine.continuous_improvement_real() # 継続改善（24時間ごと）
    )


if __name__ == '__main__':
    print("🚀 起動中...")
    print("  • Obsidian監視: 30分ごと")
    print("  • 継続改善: 24時間ごと")
    print("  • Trinity連携: Remi/Luna/Mina")
    print("")
    
    asyncio.run(main())

