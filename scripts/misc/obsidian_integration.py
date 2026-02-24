"""
Obsidian統合モジュール（改善版）
ノート管理の自動化
ベースクラスを使用して統一モジュールを活用
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import re

# ベースクラスのインポート
from base_integration import BaseIntegration


class ObsidianIntegration(BaseIntegration):
    """Obsidian統合クラス（改善版）"""
    
    def __init__(self, vault_path: str):
        """
        初期化
        
        Args:
            vault_path: Obsidian Vaultのパス
        """
        super().__init__("Obsidian")
        self.vault_path = Path(vault_path)
        self.notes_dir = self.vault_path / "Notes"  # デフォルトのノートディレクトリ
        
        # 一般的なObsidianディレクトリ構造を確認
        if not self.notes_dir.exists():
            # ルートディレクトリをノートディレクトリとして使用
            self.notes_dir = self.vault_path
    
    def _initialize_internal(self) -> bool:
        """
        内部初期化
        
        Returns:
            初期化成功かどうか
        """
        if not self.vault_path.exists():
            self.logger.warning(f"Obsidian Vaultが見つかりません: {self.vault_path}")
            return False
        
        if not self.vault_path.is_dir():
            self.logger.warning(f"Obsidian Vaultはディレクトリではありません: {self.vault_path}")
            return False
        
        self.logger.info(f"Obsidian Vaultを初期化しました: {self.vault_path}")
        return True
    
    def _check_availability_internal(self) -> bool:
        """
        内部の利用可能性チェック
        
        Returns:
            利用可能かどうか
        """
        return self.vault_path.exists() and self.vault_path.is_dir()
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        ファイル名を安全にする
        
        Args:
            filename: 元のファイル名
            
        Returns:
            安全なファイル名
        """
        # 危険な文字を置換
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 先頭・末尾の空白とドットを削除
        filename = filename.strip(' .')
        return filename
    
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
            
            self.logger.info(f"ノート作成完了: {file_path}")
            return file_path
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"title": title[:50], "folder": folder, "action": "create_note"},
                user_message="ノートの作成に失敗しました"
            )
            self.logger.error(f"ノート作成エラー: {error.message}")
            return None
    
    def read_note(self, note_path: str) -> Optional[str]:
        """
        ノートを読み込む
        
        Args:
            note_path: ノートのパス
            
        Returns:
            ノートの内容（成功時）、None（失敗時）
        """
        if not self.is_available():
            return None
        
        try:
            file_path = self.vault_path / note_path
            if not file_path.exists():
                # 警告レベルをINFOに下げる（機能には影響なし）
                self.logger.debug(f"ノートが見つかりません（スキップ）: {note_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"note_path": note_path, "action": "read_note"},
                user_message="ノートの読み込みに失敗しました"
            )
            self.logger.error(f"ノート読み込みエラー: {error.message}")
            return None
    
    def search_notes(self, query: str, folder: Optional[str] = None) -> List[Path]:
        """
        ノートを検索
        
        Args:
            query: 検索クエリ
            folder: 検索するフォルダ（オプション）
            
        Returns:
            見つかったノートのパスのリスト
        """
        if not self.is_available():
            return []
        
        try:
            search_dir = self.notes_dir / folder if folder else self.notes_dir
            if not search_dir.exists():
                return []
            
            results = []
            query_lower = query.lower()
            
            for file_path in search_dir.rglob("*.md"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if query_lower in content.lower() or query_lower in file_path.stem.lower():
                            results.append(file_path)
                except Exception:
                    continue
            
            return results
            
        except Exception as e:
            error = self.error_handler.handle_exception(
                e,
                context={"query": query, "folder": folder, "action": "search_notes"},
                user_message="ノートの検索に失敗しました"
            )
            self.logger.error(f"ノート検索エラー: {error.message}")
            return []

