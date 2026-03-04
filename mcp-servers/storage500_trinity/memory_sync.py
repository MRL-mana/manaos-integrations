#!/usr/bin/env python3
"""
Memory Sync - Trinity記憶統合システム

Obsidian、Notion、ManaVaultから記憶を統合し、
各AIエージェントの記憶層に同期します。

使用方法:
    python3 memory_sync.py --sync all
    python3 memory_sync.py --sync obsidian
    python3 memory_sync.py --sync notion
    python3 memory_sync.py --sync vault
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sqlite3


class MemorySync:
    """記憶統合システム"""
    
    def __init__(self, workspace_path: str = "/root/trinity_workspace"):
        self.workspace = Path(workspace_path)
        self.shared_dir = self.workspace / "shared"
        self.memory_dir = self.shared_dir / "memory"
        
        # 外部ソースのパス
        self.obsidian_path = Path("/root/obsidian_vault")
        self.notion_cache = Path("/root/.notion_cache")
        self.mana_vault = Path("/root/.mana_vault")
        
        # 統計
        self.stats = {
            'obsidian_imported': 0,
            'notion_imported': 0,
            'vault_imported': 0,
            'total_items': 0,
            'errors': []
        }
        
    def sync_all(self):
        """全ソースから同期"""
        print("=== Memory Sync: ALL ===")
        
        self.sync_obsidian()
        self.sync_notion()
        self.sync_vault()
        
        self._save_sync_report()
        self._print_report()
        
    def sync_obsidian(self):
        """Obsidianから同期"""
        print("\n[1/3] Syncing from Obsidian...")
        
        if not self.obsidian_path.exists():
            print(f"  ⚠️  Obsidian vault not found: {self.obsidian_path}")
            self.stats['errors'].append("Obsidian vault not found")
            return
            
        try:
            # .mdファイルを検索
            md_files = list(self.obsidian_path.rglob("*.md"))
            
            for md_file in md_files:
                # dev_qa.mdは特別扱い
                if md_file.name == "dev_qa.md":
                    self._import_dev_qa(md_file)
                else:
                    self._import_markdown(md_file, source='obsidian')
                    
            self.stats['obsidian_imported'] = len(md_files)
            print(f"  ✅ Imported {len(md_files)} notes from Obsidian")
            
        except Exception as e:
            error_msg = f"Obsidian sync error: {e}"
            print(f"  ❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            
    def sync_notion(self):
        """Notionから同期"""
        print("\n[2/3] Syncing from Notion...")
        
        # Notion APIキーの確認
        notion_key_file = self.mana_vault / "notion_api_key"
        if not notion_key_file.exists():
            print(f"  ⚠️  Notion API key not found")
            self.stats['errors'].append("Notion API key not found")
            return
            
        try:
            # Notionキャッシュから読み込み
            if self.notion_cache.exists():
                cache_files = list(self.notion_cache.glob("*.json"))
                
                for cache_file in cache_files:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._import_notion_data(data)
                        
                self.stats['notion_imported'] = len(cache_files)
                print(f"  ✅ Imported {len(cache_files)} items from Notion cache")
            else:
                print(f"  ⚠️  Notion cache not found: {self.notion_cache}")
                self.stats['errors'].append("Notion cache not found")
                
        except Exception as e:
            error_msg = f"Notion sync error: {e}"
            print(f"  ❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            
    def sync_vault(self):
        """ManaVaultから同期"""
        print("\n[3/3] Syncing from ManaVault...")
        
        if not self.mana_vault.exists():
            print(f"  ⚠️  ManaVault not found: {self.mana_vault}")
            self.stats['errors'].append("ManaVault not found")
            return
            
        try:
            # Vault内の重要ファイルを検索
            important_files = [
                'api_keys.json',
                'system_config.json',
                'service_credentials.json'
            ]
            
            imported = 0
            for filename in important_files:
                vault_file = self.mana_vault / filename
                if vault_file.exists():
                    # メタデータのみインポート（機密情報は除外）
                    self._import_vault_metadata(vault_file)
                    imported += 1
                    
            self.stats['vault_imported'] = imported
            print(f"  ✅ Imported {imported} metadata from ManaVault")
            
        except Exception as e:
            error_msg = f"Vault sync error: {e}"
            print(f"  ❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            
    def _import_dev_qa(self, md_file: Path):
        """dev_qa.mdを特別にインポート"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Q&Aセクションを抽出
            qa_entries = self._parse_qa_markdown(content)
            
            # Minaの記憶層に保存
            mina_memory = self.memory_dir / "mina_qa_memory.json"
            
            if mina_memory.exists():
                with open(mina_memory, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            else:
                existing_data = {'entries': []}
                
            # 新しいエントリを追加
            existing_data['entries'].extend(qa_entries)
            existing_data['last_updated'] = datetime.now().isoformat()
            
            with open(mina_memory, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"  ⚠️  dev_qa import error: {e}")
            
    def _parse_qa_markdown(self, content: str) -> List[Dict]:
        """Q&Aマークダウンをパース"""
        entries = []
        lines = content.split('\n')
        
        current_entry = {}
        in_question = False
        in_answer = False
        
        for line in lines:
            if line.startswith('**質問**:'):
                current_entry = {'question': line.replace('**質問**:', '').strip()}
                in_question = True
                in_answer = False
            elif line.startswith('**回答**:'):
                in_question = False
                in_answer = True
                current_entry['answer'] = line.replace('**回答**:', '').strip()
            elif line.startswith('**タグ**:'):
                in_question = False
                in_answer = False
                tags = line.replace('**タグ**:', '').strip()
                current_entry['tags'] = [t.strip() for t in tags.split() if t.startswith('#')]
                if current_entry:
                    entries.append(current_entry)
                    current_entry = {}
            elif in_question and line.strip():
                current_entry['question'] = current_entry.get('question', '') + ' ' + line.strip()
            elif in_answer and line.strip():
                current_entry['answer'] = current_entry.get('answer', '') + ' ' + line.strip()
                
        return entries
        
    def _import_markdown(self, md_file: Path, source: str):
        """一般的なマークダウンファイルをインポート"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Ariaのナレッジベースに追加
            aria_memory = self.memory_dir / "aria_knowledge.json"
            
            if aria_memory.exists():
                with open(aria_memory, 'r', encoding='utf-8') as f:
                    knowledge = json.load(f)
            else:
                knowledge = {'documents': []}
                
            document = {
                'source': source,
                'filename': md_file.name,
                'path': str(md_file),
                'content': content[:1000],  # 最初の1000文字のみ
                'imported_at': datetime.now().isoformat()
            }
            
            knowledge['documents'].append(document)
            knowledge['last_updated'] = datetime.now().isoformat()
            
            with open(aria_memory, 'w', encoding='utf-8') as f:
                json.dump(knowledge, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"  ⚠️  Markdown import error ({md_file.name}): {e}")
            
    def _import_notion_data(self, data: Dict):
        """Notionデータをインポート"""
        # Lunaのタスク層に統合
        luna_memory = self.memory_dir / "luna_tasks.json"
        
        if luna_memory.exists():
            with open(luna_memory, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
        else:
            tasks = {'tasks': []}
            
        # Notionページをタスクとして追加
        if 'properties' in data:
            task = {
                'source': 'notion',
                'title': data.get('properties', {}).get('title', 'Untitled'),
                'content': str(data.get('properties', {})),
                'imported_at': datetime.now().isoformat()
            }
            tasks['tasks'].append(task)
            
        tasks['last_updated'] = datetime.now().isoformat()
        
        with open(luna_memory, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
            
    def _import_vault_metadata(self, vault_file: Path):
        """Vaultメタデータをインポート（機密情報除外）"""
        # Remiの推論層に統合
        remi_memory = self.memory_dir / "remi_system_knowledge.json"
        
        if remi_memory.exists():
            with open(remi_memory, 'r', encoding='utf-8') as f:
                knowledge = json.load(f)
        else:
            knowledge = {'system_info': []}
            
        # ファイル名とメタデータのみ記録（内容は読まない）
        metadata = {
            'filename': vault_file.name,
            'exists': True,
            'imported_at': datetime.now().isoformat()
        }
        
        knowledge['system_info'].append(metadata)
        knowledge['last_updated'] = datetime.now().isoformat()
        
        with open(remi_memory, 'w', encoding='utf-8') as f:
            json.dump(knowledge, f, indent=2, ensure_ascii=False)
            
    def _save_sync_report(self):
        """同期レポートを保存"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'total_imported': (
                self.stats['obsidian_imported'] +
                self.stats['notion_imported'] +
                self.stats['vault_imported']
            )
        }
        
        report_file = self.memory_dir / "sync_report_latest.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # アーカイブにもコピー
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = self.memory_dir / f"sync_report_{timestamp}.json"
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
    def _print_report(self):
        """レポートを表示"""
        print("\n" + "="*50)
        print("Memory Sync Report:")
        print(f"- Obsidian notes imported: {self.stats['obsidian_imported']}")
        print(f"- Notion tasks integrated: {self.stats['notion_imported']}")
        print(f"- ManaVault records linked: {self.stats['vault_imported']}")
        
        if self.stats['errors']:
            print(f"\nWarnings/Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                print(f"  - {error}")
                
        print("\nStatus: COMPLETE ✅")
        print("="*50)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='Trinity Memory Sync System')
    parser.add_argument('--sync', 
                       choices=['all', 'obsidian', 'notion', 'vault'],
                       default='all',
                       help='Sync source (default: all)')
    
    args = parser.parse_args()
    
    syncer = MemorySync()
    
    if args.sync == 'all':
        syncer.sync_all()
    elif args.sync == 'obsidian':
        syncer.sync_obsidian()
        syncer._print_report()
    elif args.sync == 'notion':
        syncer.sync_notion()
        syncer._print_report()
    elif args.sync == 'vault':
        syncer.sync_vault()
        syncer._print_report()


if __name__ == '__main__':
    main()



