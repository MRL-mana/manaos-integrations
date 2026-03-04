#!/usr/bin/env python3
"""
Obsidian/Notion連携 - ナレッジ同期
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests
import shutil

class ObsidianSync:
    """Obsidian同期"""
    
    def __init__(self, vault_path: str = "/root/obsidian_vault"):
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        # フォルダ構造
        self.folders = {
            "trinity": self.vault_path / "Trinity",
            "level3": self.vault_path / "Level3",
            "learning": self.vault_path / "AI Learning",
            "daily": self.vault_path / "Daily Notes"
        }
        
        for folder in self.folders.values():
            folder.mkdir(parents=True, exist_ok=True)
    
    def sync_from_manaos(self):
        """ManaOSからObsidianへ同期"""
        print("📤 ManaOS → Obsidian 同期中...")
        
        synced_count = 0
        
        # 1. dev_qa.mdを同期
        dev_qa = Path("/root/dev_qa.md")
        if dev_qa.exists():
            target = self.folders['trinity'] / "QA_Archive.md"
            shutil.copy2(dev_qa, target)
            synced_count += 1
            print(f"  ✅ {target.name}")
        
        # 2. Level 3ドキュメント
        level3_docs = [
            "/root/LEVEL3_COMPLETE.md",
            "/root/LEVEL3_SHADOW_MODE_STARTED.md",
            "/root/PHASE1_ENHANCEMENT_COMPLETE.md"
        ]
        
        for doc_path in level3_docs:
            doc = Path(doc_path)
            if doc.exists():
                target = self.folders['level3'] / doc.name
                shutil.copy2(doc, target)
                synced_count += 1
                print(f"  ✅ {target.name}")
        
        # 3. AI Learning パターン
        learning_data = Path("/root/ai_learning_system/data/patterns.json")
        if learning_data.exists():
            with open(learning_data, 'r') as f:
                patterns = json.load(f)
            
            # Markdown化
            md_content = self._convert_patterns_to_markdown(patterns)
            target = self.folders['learning'] / "Learned_Patterns.md"
            with open(target, 'w') as f:
                f.write(md_content)
            synced_count += 1
            print(f"  ✅ {target.name}")
        
        # 4. RAG記憶
        rag_memories = Path("/root/god_mode/rag_memory/memories.jsonl")
        if rag_memories.exists():
            memories = []
            with open(rag_memories, 'r') as f:
                for line in f:
                    try:
                        memories.append(json.loads(line))
                    except IOError:
                        continue
            
            md_content = self._convert_memories_to_markdown(memories)
            target = self.folders['learning'] / "RAG_Memory_Bank.md"
            with open(target, 'w') as f:
                f.write(md_content)
            synced_count += 1
            print(f"  ✅ {target.name}")
        
        # 5. デイリーノート（今日の活動）
        daily_note = self._generate_daily_note()
        today = datetime.now().strftime("%Y-%m-%d")
        target = self.folders['daily'] / f"{today}.md"
        with open(target, 'w') as f:
            f.write(daily_note)
        synced_count += 1
        print(f"  ✅ {target.name}")
        
        print(f"\n✅ {synced_count}ファイル同期完了")
        print(f"   Vault: {self.vault_path}")
        
        return synced_count
    
    def _convert_patterns_to_markdown(self, patterns: List[Dict]) -> str:
        """パターンをMarkdown化"""
        md = "# AI Learning Patterns\n\n"
        md += f"**更新日時:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += "---\n\n"
        
        for pattern in patterns[-20:]:  # 最新20件
            md += f"## {pattern.get('pattern', 'Unknown')}\n\n"
            md += f"**頻度:** {pattern.get('frequency', 0)}回\n"
            md += f"**信頼度:** {pattern.get('confidence', 0)*100:.1f}%\n\n"
            
            if 'examples' in pattern:
                md += "**例:**\n"
                for example in pattern['examples'][:3]:
                    md += f"- {example}\n"
            
            md += "\n---\n\n"
        
        return md
    
    def _convert_memories_to_markdown(self, memories: List[Dict]) -> str:
        """記憶をMarkdown化"""
        md = "# RAG Memory Bank\n\n"
        md += f"**総記憶数:** {len(memories)}\n"
        md += f"**更新日時:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        md += "---\n\n"
        
        # カテゴリ別に整理
        by_category = {}
        for mem in memories:
            cat = mem.get('category', 'uncategorized')
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(mem)
        
        for category, mems in sorted(by_category.items()):
            md += f"## {category.replace('_', ' ').title()}\n\n"
            
            for mem in mems:
                md += f"### {mem.get('content', '')[:100]}...\n\n"
                md += f"**タグ:** {', '.join(mem.get('tags', []))}\n"
                md += f"**重要度:** {'⭐' * int(mem.get('importance', 0.5) * 5)}\n\n"
                md += f"{mem.get('content', '')}\n\n"
                md += "---\n\n"
        
        return md
    
    def _generate_daily_note(self) -> str:
        """デイリーノート生成"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        md = f"# Daily Note - {today}\n\n"
        md += "## 🚀 今日の活動\n\n"
        
        # Level 3ステータス
        try:
            from god_mode.lightweight_monitor import get_monitor
            monitor = get_monitor()
            status = monitor.get_current_status()
            
            md += "### Level 3 Status\n\n"
            md += f"- 健全性スコア: {status['health_score']}/100\n"
            md += f"- アラート: {len(status['alerts'])}件\n"
            
            processes = status['level3_processes']
            for name, running in processes.items():
                status_emoji = "✅" if running else "❌"
                md += f"- {status_emoji} {name}\n"
            
            md += "\n"
        except Exception:
            pass
        
        # 思考ログサマリー
        try:
            from god_mode.thinking_audit_system import get_audit_system
            audit = get_audit_system()
            report = audit.generate_report(days=1)
            
            md += "### 思考ログサマリー\n\n"
            md += "```\n" + report + "\n```\n\n"
        except Exception:
            pass
        
        md += "## 📝 メモ\n\n"
        md += "- \n\n"
        
        md += "## ✅ TODO\n\n"
        md += "- [ ] \n\n"
        
        return md

class NotionSync:
    """Notion同期"""
    
    def __init__(self):
        self.config_file = Path("/root/.mana_vault/notion_config.json")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """設定読み込み"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "api_token": "",
            "database_id": "",
            "enabled": False
        }
    
    def is_enabled(self) -> bool:
        """有効かチェック"""
        return self.config.get('enabled', False) and self.config.get('api_token', '')
    
    def sync_to_notion(self, title: str, content: str, tags: List[str] = None) -> Optional[str]:
        """Notionへ同期"""
        if not self.is_enabled():
            print("⚠️  Notion未設定（スキップ）")
            return None
        
        headers = {
            "Authorization": f"Bearer {self.config['api_token']}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        data = {
            "parent": {"database_id": self.config['database_id']},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": title}}]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": content[:2000]}}]
                    }
                }
            ]
        }
        
        if tags:
            data["properties"]["Tags"] = {
                "multi_select": [{"name": tag} for tag in tags]
            }
        
        try:
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return response.json().get('id')
        except Exception as e:
            print(f"❌ Notion同期失敗: {e}")
            return None

# テスト実行
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("📚 Obsidian/Notion連携 - デモ実行")
    print("=" * 70)
    
    # Obsidian同期
    print("\n[Obsidian同期]")
    obsidian = ObsidianSync()
    count = obsidian.sync_from_manaos()
    
    print("\n✅ Obsidian Vault作成完了")
    print(f"   場所: {obsidian.vault_path}")
    print(f"   ファイル数: {count}")
    
    # Notion設定チェック
    print("\n[Notion設定]")
    notion = NotionSync()
    if notion.is_enabled():
        print("✅ Notion設定済み")
    else:
        print("⚠️  Notion未設定")
        print("\n設定方法:")
        print("1. Notion Integration作成: https://www.notion.so/my-integrations")
        print("2. Database作成してIntegrationを接続")
        print("3. 設定ファイル作成:")
        print(f"   mkdir -p {notion.config_file.parent}")
        print(f'   echo \'{{"api_token": "YOUR_TOKEN", "database_id": "YOUR_DB_ID", "enabled": true}}\' > {notion.config_file}')
    
    print("\n" + "=" * 70)
    print("✅ デモ完了")
    print("=" * 70)

