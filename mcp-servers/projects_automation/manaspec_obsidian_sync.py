#!/usr/bin/env python3
"""
ManaSpec × Obsidian 完全統合
仕様を自動的にMana Vaultに保存
"""

from pathlib import Path
from datetime import datetime

class ManaSpecObsidianSync:
    """Obsidian同期システム"""
    
    def __init__(self, vault_path: str = "/root/obsidian_vault"):
        self.vault_path = Path(vault_path)
        self.specs_folder = self.vault_path / "ManaSpec" / "Specs"
        self.changes_folder = self.vault_path / "ManaSpec" / "Changes"
        self.archives_folder = self.vault_path / "ManaSpec" / "Archives"
        
        # フォルダ作成
        self.specs_folder.mkdir(parents=True, exist_ok=True)
        self.changes_folder.mkdir(parents=True, exist_ok=True)
        self.archives_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"📝 Obsidian Vault: {self.vault_path}")
    
    def sync_spec(self, spec_path: Path):
        """Specを Obsidian に同期"""
        spec_name = spec_path.parent.name
        content = spec_path.read_text()
        
        # Obsidian形式に変換
        obsidian_content = self._convert_to_obsidian_format(content, spec_name, "spec")
        
        # Obsidianに保存
        output_path = self.specs_folder / f"{spec_name}.md"
        output_path.write_text(obsidian_content)
        
        print(f"✅ Spec synced: {spec_name} → {output_path}")
        return output_path
    
    def sync_change(self, change_path: Path):
        """Changeを Obsidian に同期"""
        change_name = change_path.name
        
        # proposal.mdを読み込み
        proposal_file = change_path / "proposal.md"
        tasks_file = change_path / "tasks.md"
        
        if not proposal_file.exists():
            print(f"⚠️ Proposal not found: {change_path}")
            return None
        
        proposal_content = proposal_file.read_text()
        tasks_content = tasks_file.read_text() if tasks_file.exists() else ""
        
        # 統合Obsidian文書作成
        obsidian_content = f"""---
type: manaspec-change
change_id: {change_name}
status: proposed
created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
tags: [manaspec, proposal, trinity-remi]
---

# 📋 Change: {change_name}

## Proposal

{proposal_content}

## Tasks

{tasks_content}

## Specs

"""
        
        # Spec deltasを追加
        specs_dir = change_path / "specs"
        if specs_dir.exists():
            for capability_dir in specs_dir.iterdir():
                if capability_dir.is_dir():
                    spec_file = capability_dir / "spec.md"
                    if spec_file.exists():
                        obsidian_content += f"\n### {capability_dir.name}\n\n"
                        obsidian_content += spec_file.read_text()
                        obsidian_content += "\n"
        
        # Obsidianに保存
        output_path = self.changes_folder / f"{change_name}.md"
        output_path.write_text(obsidian_content)
        
        print(f"✅ Change synced: {change_name} → {output_path}")
        return output_path
    
    def sync_archive(self, archive_path: Path):
        """Archiveを Obsidian に同期"""
        archive_name = archive_path.name
        
        # 全ファイルを収集
        content = f"""---
type: manaspec-archive
archive_id: {archive_name}
status: completed
archived: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
tags: [manaspec, archive, trinity-mina, completed]
---

# 📦 Archive: {archive_name}

## Timeline

- **Created**: {archive_name.split('-')[0]}-{archive_name.split('-')[1]}-{archive_name.split('-')[2]}
- **Archived**: {datetime.now().strftime('%Y-%m-%d')}
- **Learned by**: Mina（洞察記録AI）

"""
        
        # Proposalを追加
        proposal_file = archive_path / "proposal.md"
        if proposal_file.exists():
            content += "## Proposal\n\n" + proposal_file.read_text() + "\n\n"
        
        # Tasksを追加
        tasks_file = archive_path / "tasks.md"
        if tasks_file.exists():
            content += "## Tasks\n\n" + tasks_file.read_text() + "\n\n"
        
        # Specsを追加
        specs_dir = archive_path / "specs"
        if specs_dir.exists():
            content += "## Specifications\n\n"
            for capability_dir in specs_dir.iterdir():
                if capability_dir.is_dir():
                    spec_file = capability_dir / "spec.md"
                    if spec_file.exists():
                        content += f"### {capability_dir.name}\n\n"
                        content += spec_file.read_text() + "\n\n"
        
        # Obsidianに保存
        output_path = self.archives_folder / f"{archive_name}.md"
        output_path.write_text(content)
        
        print(f"✅ Archive synced: {archive_name} → {output_path}")
        return output_path
    
    def _convert_to_obsidian_format(self, content: str, name: str, doc_type: str) -> str:
        """Obsidian形式に変換"""
        return f"""---
type: manaspec-{doc_type}
name: {name}
synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
tags: [manaspec, {doc_type}, trinity-luna]
---

# {name}

{content}

---

**Synced from ManaSpec** | [[ManaSpec Index]]
"""
    
    def sync_all(self, openspec_path: str = "/root/openspec_test"):
        """すべての仕様をObsidianに同期"""
        openspec_dir = Path(openspec_path) / "openspec"
        
        print("\n🔄 Obsidian完全同期開始\n")
        
        # Specsを同期
        specs_dir = openspec_dir / "specs"
        if specs_dir.exists():
            for spec_dir in specs_dir.iterdir():
                if spec_dir.is_dir():
                    spec_file = spec_dir / "spec.md"
                    if spec_file.exists():
                        self.sync_spec(spec_file)
        
        # Changesを同期
        changes_dir = openspec_dir / "changes"
        if changes_dir.exists():
            for change_dir in changes_dir.iterdir():
                if change_dir.is_dir() and change_dir.name != "archive":
                    self.sync_change(change_dir)
        
        # Archivesを同期
        archive_dir = changes_dir / "archive" if changes_dir.exists() else None
        if archive_dir and archive_dir.exists():
            for archived_change in archive_dir.iterdir():
                if archived_change.is_dir():
                    self.sync_archive(archived_change)
        
        # インデックスページ作成
        self._create_index_page()
        
        print("\n✅ Obsidian同期完了")
    
    def _create_index_page(self):
        """ManaSpec Index ページを作成"""
        index_content = f"""---
type: manaspec-index
updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
tags: [manaspec, index, trinity]
---

# 🎯 ManaSpec Index

**仕様駆動開発 × Trinity統合**

## 📊 概要

- **Specs**: [[ManaSpec/Specs|仕様一覧]]
- **Changes**: [[ManaSpec/Changes|変更提案一覧]]
- **Archives**: [[ManaSpec/Archives|完了済み履歴]]

## 👭 Trinity連携

- 📋 **Remi**: Proposal作成・戦略判断
- ⚙️ **Luna**: Apply実行・実装
- 📦 **Mina**: Archive管理・学習

## 🔗 Quick Links

- [Dashboard](http://localhost:9302) - リアルタイムダッシュボード
- [API Docs](http://localhost:9301/api/manaspec/status) - REST API
- [Trinity UI](http://localhost:[port]) - Trinity統合UI

## 📅 Last Updated

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

**Powered by ManaSpec** | Auto-synced from OpenSpec
"""
        
        index_path = self.vault_path / "ManaSpec" / "Index.md"
        index_path.write_text(index_content)
        print(f"📑 Index created: {index_path}")


def main():
    """CLI実行"""
    import sys
    
    sync = ManaSpecObsidianSync()
    
    if len(sys.argv) > 1 and sys.argv[1] == "sync":
        openspec_path = sys.argv[2] if len(sys.argv) > 2 else "/root/openspec_test"
        sync.sync_all(openspec_path)
    else:
        print("Usage: manaspec_obsidian_sync.py sync [openspec_path]")
        print("\nExample:")
        print("  python3 manaspec_obsidian_sync.py sync /root/openspec_test")


if __name__ == '__main__':
    main()

