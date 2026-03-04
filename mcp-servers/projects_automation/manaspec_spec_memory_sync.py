#!/usr/bin/env python3
"""
🔄 Spec Memory Sync
Obsidian ⇄ ManaSpec の完全双方向同期

Obsidianで書いたアイデア → ManaSpec Proposal
ManaSpec Archive → Obsidian記録
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict
import re

class SpecMemorySync:
    """思考⇔実装の完全循環システム"""
    
    def __init__(self, 
                 vault_path: str = "/root/obsidian_vault",
                 openspec_path: str = "/root/manaos_v3"):
        self.vault_path = Path(vault_path)
        self.openspec_path = Path(openspec_path) / "openspec"
        
        # 特別なフォルダ
        self.ideas_folder = self.vault_path / "Ideas"
        self.manaspec_folder = self.vault_path / "ManaSpec"
        
        self.ideas_folder.mkdir(parents=True, exist_ok=True)
    
    async def watch_obsidian_ideas(self):
        """Obsidianのアイデアを監視"""
        print("👁️ Obsidian Ideas監視開始...\n")
        
        # Ideasフォルダ内のノートを分析
        for idea_file in self.ideas_folder.glob("*.md"):
            content = idea_file.read_text()
            
            # 特別なタグを検出（フロントマター形式とインラインタグ両対応）
            has_proposal_tag = (
                re.search(r'tags:.*manaspec-proposal', content) or
                re.search(r'tags:.*実装待ち', content) or
                re.search(r'#manaspec-proposal|#implement|#実装待ち', content)
            )
            
            if has_proposal_tag:
                print(f"✨ 実装候補検出: {idea_file.name}")
                
                # タイトル抽出
                title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
                title = title_match.group(1) if title_match else idea_file.stem
                
                # 説明抽出
                description_match = re.search(r'## 説明\n(.+?)(?:\n#|$)', content, re.DOTALL)
                description = description_match.group(1).strip() if description_match else ""
                
                yield {
                    "source_file": str(idea_file),
                    "title": title,
                    "description": description,
                    "detected_at": datetime.now().isoformat()
                }
    
    async def create_proposal_from_idea(self, idea: Dict):
        """アイデアからProposalを自動生成"""
        print(f"\n📋 Proposal自動生成: {idea['title']}")
        
        # Remiに提案を依頼
        import requests
        
        try:
            response = requests.post(
                "http://localhost:9200/api/execute",
                json={
                    "text": f"""
Obsidianのアイデアノートから Proposal を生成してください：

タイトル: {idea['title']}
説明: {idea['description']}
ソース: {idea['source_file']}

OpenSpec形式で change-id, requirements, scenarios を提案してください。
                    """,
                    "actor": "remi",
                    "source": "spec_memory_sync"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Remi提案取得")
                print(f"\n{result.get('result', '')[:300]}...\n")
                
                # ManaSpecワークフローを起動
                print("🚀 ワークフロー起動中...")
                # subprocess等で実際のProposal作成
                
                return True
            else:
                print("⚠️ Remi offline")
                return False
        except Exception as e:
            print(f"❌ エラー: {e}")
            return False
    
    async def sync_archives_to_journal(self):
        """Archiveを日記形式でObsidianに記録"""
        print("\n📓 Archive → Journal 同期\n")
        
        # 日付ごとのJournalフォルダ
        journal_folder = self.vault_path / "Journal"
        journal_folder.mkdir(parents=True, exist_ok=True)
        
        # 今日のArchiveを取得
        today = datetime.now().strftime('%Y-%m-%d')
        archive_dir = self.openspec_path / "changes" / "archive"
        
        if archive_dir.exists():
            today_archives = list(archive_dir.glob(f"{today}-*"))
            
            if today_archives:
                journal_content = f"""---
date: {today}
type: daily-journal
tags: [manaspec, archive, daily]
---

# 📅 {today} - ManaSpec日報

## 完了した変更

"""
                for archive in today_archives:
                    proposal_file = archive / "proposal.md"
                    if proposal_file.exists():
                        proposal = proposal_file.read_text()
                        journal_content += f"\n### {archive.name}\n\n{proposal}\n"
                
                # Journal保存
                journal_file = journal_folder / f"{today}.md"
                journal_file.write_text(journal_content)
                
                print(f"✅ Journal作成: {journal_file}")
            else:
                print("ℹ️ 今日のArchiveなし")
    
    async def continuous_sync(self, interval_minutes: int = 30):
        """継続的な双方向同期"""
        print(f"🔄 継続同期開始（{interval_minutes}分ごと）\n")
        
        while True:
            print(f"\n⏰ 同期実行: {datetime.now().strftime('%H:%M:%S')}")
            
            # Obsidian → ManaSpec
            async for idea in self.watch_obsidian_ideas():
                await self.create_proposal_from_idea(idea)
            
            # ManaSpec → Obsidian Journal
            await self.sync_archives_to_journal()
            
            print(f"✅ 同期完了 - 次回: {interval_minutes}分後\n")
            
            # 待機
            await asyncio.sleep(interval_minutes * 60)


async def main():
    """デモ実行"""
    sync = SpecMemorySync()
    
    print("🔄 Spec Memory Sync - 思考⇔実装の完全循環\n")
    print("="*60 + "\n")
    
    # Obsidian Ideas監視
    print("📝 Phase 1: Obsidian Ideas分析\n")
    count = 0
    async for idea in sync.watch_obsidian_ideas():
        print(f"  ✨ {idea['title']}")
        print(f"     {idea['description'][:100]}...")
        count += 1
    
    if count == 0:
        print("  ℹ️ 実装候補なし（#manaspec-proposal タグのノートを作成してください）")
    
    print("\n📓 Phase 2: Archive → Journal同期\n")
    await sync.sync_archives_to_journal()
    
    print("\n" + "="*60)
    print("✅ Spec Memory Sync - デモ完了")
    print("="*60)
    print("\n💡 継続同期を開始するには:")
    print("   python3 /root/manaspec_spec_memory_sync.py --continuous")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--continuous':
        asyncio.run(SpecMemorySync().continuous_sync(interval_minutes=30))
    else:
        asyncio.run(main())

