"""
Obsidian統合モジュール
ノート管理の自動化
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import re


class ObsidianIntegration:
    """Obsidian統合クラス"""
    
    def __init__(self, vault_path: str):
        """
        初期化
        
        Args:
            vault_path: Obsidian Vaultのパス
        """
        self.vault_path = Path(vault_path)
        self.notes_dir = self.vault_path / "Notes"  # デフォルトのノートディレクトリ
        
        # 一般的なObsidianディレクトリ構造を確認
        if not self.notes_dir.exists():
            # ルートディレクトリをノートディレクトリとして使用
            self.notes_dir = self.vault_path
    
    def is_available(self) -> bool:
        """
        Obsidian Vaultが利用可能かチェック
        
        Returns:
            利用可能な場合True
        """
        return self.vault_path.exists() and self.vault_path.is_dir()
    
    def create_note(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        folder: Optional[str] = None
    ) -> Optional[Path]:
        """
        ノートを作成
        
        Args:
            title: ノートタイトル
            content: ノート内容
            tags: タグのリスト（オプション）
            folder: フォルダ名（オプション）
            
        Returns:
            作成されたノートのパス（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            # フォルダを決定
            target_dir = self.notes_dir
            if folder:
                target_dir = self.notes_dir / folder
                target_dir.mkdir(parents=True, exist_ok=True)
            
            # ファイル名を安全にする
            safe_title = self._sanitize_filename(title)
            file_path = target_dir / f"{safe_title}.md"
            
            # タグを追加
            if tags:
                tag_line = " ".join([f"#{tag}" for tag in tags])
                content = f"{tag_line}\n\n{content}"
            
            # フロントマターを追加（オプション）
            frontmatter = {
                "title": title,
                "created": datetime.now().isoformat(),
                "tags": tags or []
            }
            
            frontmatter_str = "---\n"
            for key, value in frontmatter.items():
                if isinstance(value, list):
                    frontmatter_str += f"{key}: {json.dumps(value)}\n"
                else:
                    frontmatter_str += f"{key}: {value}\n"
            frontmatter_str += "---\n\n"
            
            # ノートを書き込み
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter_str)
                f.write(content)
            
            print(f"ノート作成完了: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"ノート作成エラー: {e}")
            return None
    
    def read_note(self, note_path: str) -> Optional[Dict[str, Any]]:
        """
        ノートを読み込み
        
        Args:
            note_path: ノートのパス（相対または絶対）
            
        Returns:
            ノート情報の辞書（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            note_path_obj = Path(note_path)
            if not note_path_obj.is_absolute():
                note_path_obj = self.vault_path / note_path_obj
            
            if not note_path_obj.exists():
                return None
            
            with open(note_path_obj, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # フロントマターを解析
            frontmatter = {}
            body = content
            
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_str = parts[1]
                    body = parts[2].strip()
                    
                    # シンプルなフロントマター解析
                    for line in frontmatter_str.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip()
                            value = value.strip()
                            try:
                                frontmatter[key] = json.loads(value)
                            except:
                                frontmatter[key] = value
            
            return {
                "path": str(note_path_obj),
                "title": frontmatter.get("title", note_path_obj.stem),
                "content": body,
                "frontmatter": frontmatter,
                "tags": frontmatter.get("tags", [])
            }
            
        except Exception as e:
            print(f"ノート読み込みエラー: {e}")
            return None
    
    def search_notes(
        self,
        query: str,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        ノートを検索
        
        Args:
            query: 検索クエリ
            folder: 検索するフォルダ（オプション）
            tags: 検索するタグ（オプション）
            
        Returns:
            ノート情報のリスト
        """
        if not self.is_available():
            return []
        
        try:
            search_dir = self.notes_dir
            if folder:
                search_dir = self.notes_dir / folder
            
            if not search_dir.exists():
                return []
            
            results = []
            query_lower = query.lower()
            
            # マークダウンファイルを検索
            for md_file in search_dir.rglob("*.md"):
                try:
                    note = self.read_note(str(md_file))
                    if not note:
                        continue
                    
                    # クエリで検索
                    if query_lower in note["content"].lower() or query_lower in note["title"].lower():
                        # タグフィルタ
                        if tags:
                            note_tags = note.get("tags", [])
                            if not any(tag in note_tags for tag in tags):
                                continue
                        
                        results.append(note)
                        
                except Exception as e:
                    continue
            
            return results
            
        except Exception as e:
            print(f"ノート検索エラー: {e}")
            return []
    
    def update_note(
        self,
        note_path: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        ノートを更新
        
        Args:
            note_path: ノートのパス
            content: 新しい内容（オプション）
            title: 新しいタイトル（オプション）
            tags: 新しいタグ（オプション）
            
        Returns:
            成功時True
        """
        if not self.is_available():
            return False
        
        try:
            note = self.read_note(note_path)
            if not note:
                return False
            
            # 更新
            if content is not None:
                note["content"] = content
            
            if title is not None:
                note["title"] = title
                note["frontmatter"]["title"] = title
            
            if tags is not None:
                note["tags"] = tags
                note["frontmatter"]["tags"] = tags
            
            # ファイル名変更が必要な場合
            note_path_obj = Path(note["path"])
            if title and title != note_path_obj.stem:
                new_path = note_path_obj.parent / f"{self._sanitize_filename(title)}.md"
                note_path_obj = new_path
            
            # ノートを再作成
            return self.create_note(
                note["title"],
                note["content"],
                note["tags"],
                folder=note_path_obj.parent.name if note_path_obj.parent != self.notes_dir else None
            ) is not None
            
        except Exception as e:
            print(f"ノート更新エラー: {e}")
            return False
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        ファイル名を安全にする
        
        Args:
            filename: ファイル名
            
        Returns:
            安全なファイル名
        """
        # 危険な文字を削除
        safe_name = re.sub(r'[<>:"/\\|?*]', '', filename)
        # 先頭・末尾の空白とドットを削除
        safe_name = safe_name.strip('. ')
        return safe_name
    
    def get_all_tags(self) -> List[str]:
        """
        すべてのタグを取得
        
        Returns:
            タグのリスト
        """
        if not self.is_available():
            return []
        
        tags = set()
        
        try:
            for md_file in self.notes_dir.rglob("*.md"):
                note = self.read_note(str(md_file))
                if note:
                    tags.update(note.get("tags", []))
        except:
            pass
        
        return sorted(list(tags))


def main():
    """テスト用メイン関数"""
    print("Obsidian統合テスト")
    print("=" * 50)
    
    # デフォルトのVaultパス（環境変数から取得可能）
    vault_path = os.getenv("OBSIDIAN_VAULT_PATH", "C:/Users/mana4/Documents/Obsidian Vault")
    
    obsidian = ObsidianIntegration(vault_path)
    
    if not obsidian.is_available():
        print(f"Obsidian Vaultが見つかりません: {vault_path}")
        print("環境変数 OBSIDIAN_VAULT_PATH を設定するか、vault_pathを指定してください。")
        return
    
    print(f"Obsidian Vault: {vault_path}")
    
    # ノート作成テスト
    print("\nノート作成テスト:")
    note_path = obsidian.create_note(
        title="ManaOS統合テスト",
        content="これはManaOSからの自動生成ノートです。\n\nテスト内容。",
        tags=["ManaOS", "テスト", "自動化"]
    )
    
    if note_path:
        print(f"ノート作成成功: {note_path}")
        
        # ノート読み込みテスト
        note = obsidian.read_note(str(note_path))
        if note:
            print(f"タイトル: {note['title']}")
            print(f"タグ: {note['tags']}")
    
    # タグ一覧取得
    tags = obsidian.get_all_tags()
    print(f"\n利用可能なタグ数: {len(tags)}")


if __name__ == "__main__":
    main()





















