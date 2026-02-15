"""
統一記憶システム（UnifiedMemory）
Obsidianを母艦として、入力・出力を統一フォーマットで管理
"""

import os
import json
from manaos_logger import get_logger, get_service_logger
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

logger = get_service_logger("memory-unified")
# Obsidian統合をインポート
try:
    from obsidian_integration import ObsidianIntegration
    OBSIDIAN_AVAILABLE = True
except ImportError:
    OBSIDIAN_AVAILABLE = False
    logger.warning("Obsidian統合が利用できません")


class ObsidianError(Exception):
    """Obsidian関連のエラー"""
    pass


class UnifiedMemory:
    """統一記憶システム（Obsidianを母艦として）"""
    
    # 入力フォーマットタイプ
    INPUT_TYPES = ["conversation", "memo", "research", "system"]
    
    # 出力フォーマットタイプ
    OUTPUT_TYPES = ["summary", "judgment", "action", "learning"]
    
    def __init__(self, vault_path: Optional[str] = None, cache_dir: Optional[str] = None):
        """
        初期化
        
        Args:
            vault_path: Obsidian Vaultのパス（Noneの場合は環境変数から取得）
            cache_dir: ローカルキャッシュディレクトリ（Noneの場合はデフォルト）
        """
        # Obsidian Vaultパス
        if vault_path is None:
            vault_path = os.getenv(
                "OBSIDIAN_VAULT_PATH",
                str(Path.home() / "Documents" / "Obsidian Vault"),
            )
        
        self.vault_path = Path(vault_path)
        
        # ローカルキャッシュディレクトリ
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "data" / "memory_cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Obsidian統合
        self.obsidian = None
        if OBSIDIAN_AVAILABLE:
            try:
                self.obsidian = ObsidianIntegration(str(self.vault_path))
                if not self.obsidian.is_available():
                    logger.warning(f"Obsidian Vaultが見つかりません: {self.vault_path}")
                    self.obsidian = None
            except Exception as e:
                logger.warning(f"Obsidian統合の初期化エラー: {e}")
                self.obsidian = None
        
        # メモリフォーマット仕様
        self.memory_format = {
            "input": {
                "type": "conversation|memo|research|system",
                "timestamp": "ISO8601",
                "content": "string",
                "metadata": "dict"
            },
            "output": {
                "type": "summary|judgment|action|learning",
                "timestamp": "ISO8601",
                "content": "string",
                "metadata": "dict",
                "source": "input_id"
            }
        }
    
    def _format_content(
        self,
        content: Dict[str, Any],
        format_type: str
    ) -> Dict[str, Any]:
        """
        コンテンツを統一フォーマットに変換
        
        Args:
            content: コンテンツ
            format_type: フォーマットタイプ
        
        Returns:
            統一フォーマットのコンテンツ
        """
        formatted = {
            "id": str(uuid.uuid4()),
            "type": format_type,
            "timestamp": datetime.now().isoformat(),
            "content": content.get("content", str(content)),
            "metadata": content.get("metadata", {})
        }
        
        # 入力タイプの場合
        if format_type in self.INPUT_TYPES:
            formatted["input_type"] = format_type
        
        # 出力タイプの場合
        if format_type in self.OUTPUT_TYPES:
            formatted["output_type"] = format_type
            formatted["source"] = content.get("source", "")
        
        return formatted
    
    def _save_to_obsidian(self, formatted_content: Dict[str, Any]) -> Optional[str]:
        """
        Obsidianに保存
        
        Args:
            formatted_content: 統一フォーマットのコンテンツ
        
        Returns:
            ノートID（成功時）、None（失敗時）
        """
        if not self.obsidian:
            raise ObsidianError("Obsidianが利用できません")
        
        try:
            # フォーマットタイプに応じてフォルダを決定
            format_type = formatted_content.get("type", "system")
            folder = self._get_folder_for_type(format_type)
            
            # タイトルを生成
            title = self._generate_title(formatted_content)
            
            # コンテンツをMarkdown形式に変換
            content_md = self._format_to_markdown(formatted_content)
            
            # タグを生成
            tags = self._generate_tags(formatted_content)
            
            # ノートを作成
            note_path = self.obsidian.create_note(
                title=title,
                content=content_md,
                tags=tags,
                folder=folder
            )
            
            if note_path:
                logger.info(f"Obsidianに保存: {note_path}")
                return formatted_content["id"]
            else:
                raise ObsidianError("ノートの作成に失敗しました")
        
        except Exception as e:
            logger.error(f"Obsidian保存エラー: {e}")
            raise ObsidianError(f"Obsidian保存エラー: {e}")
    
    def _save_to_local_cache(self, formatted_content: Dict[str, Any]) -> str:
        """
        ローカルキャッシュに保存（失敗時の退避）
        
        Args:
            formatted_content: 統一フォーマットのコンテンツ
        
        Returns:
            キャッシュID
        """
        cache_id = formatted_content["id"]
        cache_file = self.cache_dir / f"{cache_id}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(formatted_content, f, ensure_ascii=False, indent=2)
            
            logger.info(f"ローカルキャッシュに保存: {cache_file}")
            return cache_id
        
        except Exception as e:
            logger.error(f"ローカルキャッシュ保存エラー: {e}")
            raise
    
    def _get_folder_for_type(self, format_type: str) -> str:
        """フォーマットタイプに応じたフォルダ名を取得"""
        folder_map = {
            "conversation": "Conversations",
            "memo": "Memos",
            "research": "Research",
            "system": "System",
            "summary": "Summaries",
            "judgment": "Judgments",
            "action": "Actions",
            "learning": "Learning"
        }
        return folder_map.get(format_type, "Misc")
    
    def _generate_title(self, formatted_content: Dict[str, Any]) -> str:
        """タイトルを生成"""
        format_type = formatted_content.get("type", "system")
        timestamp = formatted_content.get("timestamp", "")
        date_str = timestamp[:10] if timestamp else datetime.now().strftime("%Y-%m-%d")
        
        content_preview = formatted_content.get("content", "")[:50]
        
        title_map = {
            "conversation": f"会話 {date_str}",
            "memo": f"メモ {date_str}",
            "research": f"リサーチ {date_str}",
            "system": f"システム {date_str}",
            "summary": f"要約 {date_str}",
            "judgment": f"判断 {date_str}",
            "action": f"アクション {date_str}",
            "learning": f"学習 {date_str}"
        }
        
        return title_map.get(format_type, f"{format_type} {date_str}")
    
    def _format_to_markdown(self, formatted_content: Dict[str, Any]) -> str:
        """統一フォーマットをMarkdownに変換"""
        lines = []
        
        # メタデータ
        metadata = formatted_content.get("metadata", {})
        if metadata:
            lines.append("## メタデータ")
            for key, value in metadata.items():
                lines.append(f"- **{key}**: {value}")
            lines.append("")
        
        # コンテンツ
        lines.append("## コンテンツ")
        lines.append(formatted_content.get("content", ""))
        lines.append("")
        
        # ソース（出力タイプの場合）
        if "source" in formatted_content:
            lines.append(f"## ソース")
            lines.append(f"ID: {formatted_content['source']}")
            lines.append("")
        
        # タイムスタンプ
        lines.append(f"## タイムスタンプ")
        lines.append(formatted_content.get("timestamp", ""))
        
        return "\n".join(lines)
    
    def _generate_tags(self, formatted_content: Dict[str, Any]) -> List[str]:
        """タグを生成"""
        tags = ["ManaOS", "UnifiedMemory"]
        
        format_type = formatted_content.get("type", "")
        if format_type:
            tags.append(format_type)
        
        # メタデータからタグを抽出
        metadata = formatted_content.get("metadata", {})
        if "tags" in metadata:
            tags.extend(metadata["tags"])
        
        return tags
    
    def store(
        self,
        content: Dict[str, Any],
        format_type: str = "auto"
    ) -> str:
        """
        記憶への保存（入口が1個）
        
        Args:
            content: コンテンツ
            format_type: フォーマットタイプ（"auto"の場合は自動判定）
        
        Returns:
            メモリID
        """
        # フォーマットタイプの自動判定
        if format_type == "auto":
            format_type = self._detect_format_type(content)
        
        # 統一フォーマットに変換
        formatted = self._format_content(content, format_type)
        
        # Obsidianに保存を試みる
        try:
            memory_id = self._save_to_obsidian(formatted)
            logger.info(f"[Remember] {format_type}: {memory_id}")
            return memory_id
        
        except ObsidianError:
            # 失敗時はローカルキャッシュに退避
            logger.warning("Obsidian保存失敗、ローカルキャッシュに退避")
            try:
                cache_id = self._save_to_local_cache(formatted)
                # イベント発行（通知）
                try:
                    import manaos_core_api as manaos
                    manaos.emit(
                        "memory_fallback",
                        {
                            "reason": "obsidian_failed",
                            "memory_id": cache_id,
                            "format_type": format_type
                        },
                        "important"
                    )
                except Exception:
                    pass
                return cache_id
            except Exception as e:
                logger.error(f"ローカルキャッシュ保存も失敗: {e}")
                raise
    
    def _detect_format_type(self, content: Dict[str, Any]) -> str:
        """フォーマットタイプを自動判定"""
        content_str = str(content).lower()
        
        if "conversation" in content_str or "会話" in content_str:
            return "conversation"
        elif "memo" in content_str or "メモ" in content_str:
            return "memo"
        elif "research" in content_str or "リサーチ" in content_str:
            return "research"
        elif "summary" in content_str or "要約" in content_str:
            return "summary"
        elif "judgment" in content_str or "判断" in content_str:
            return "judgment"
        elif "action" in content_str or "アクション" in content_str:
            return "action"
        elif "learning" in content_str or "学習" in content_str:
            return "learning"
        else:
            return "system"
    
    def recall(
        self,
        query: str,
        scope: str = "all",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        記憶からの検索（出口が1個）
        
        Args:
            query: 検索クエリ
            scope: スコープ（"all", "today", "week", "month"）
            limit: 取得件数
        
        Returns:
            検索結果のリスト
        """
        results = []
        
        # Obsidianから検索（タイムアウトで保護）
        if self.obsidian:
            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError

                timeout_sec = float(os.getenv("OBSIDIAN_SEARCH_TIMEOUT_SEC", "3"))
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(self.obsidian.search_notes, query)
                try:
                    obsidian_results = future.result(timeout=timeout_sec)
                except TimeoutError:
                    future.cancel()
                    logger.warning("Obsidian検索がタイムアウトしました。ローカルキャッシュのみで応答します")
                    obsidian_results = []
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)

                # 統一フォーマットに変換
                for note_path in obsidian_results[:limit]:
                    try:
                        # Pathオブジェクトから内容を読み込む
                        if isinstance(note_path, Path):
                            try:
                                content_str = note_path.read_text(encoding="utf-8")
                            except Exception:
                                content_str = self.obsidian.read_note(note_path.name)
                            if content_str:
                                # フロントマターを解析して辞書形式に変換
                                note_dict = self._parse_note_content(note_path, content_str)
                                formatted = self._note_to_unified_format(note_dict)
                                if formatted and self._is_in_scope(formatted.get("timestamp", ""), scope):
                                    results.append(formatted)
                    except Exception as e:
                        logger.warning(f"ノート処理エラー ({note_path}): {e}")

            except Exception as e:
                logger.warning(f"Obsidian検索エラー: {e}")
        
        # ローカルキャッシュから検索（タイムアウトで保護）
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError

            cache_timeout = float(os.getenv("LOCAL_CACHE_SEARCH_TIMEOUT_SEC", "2"))
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(self._search_local_cache, query, scope, limit)
            try:
                cache_results = future.result(timeout=cache_timeout)
                results.extend(cache_results)
            except TimeoutError:
                future.cancel()
                logger.warning("ローカルキャッシュ検索がタイムアウトしました")
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
        except Exception as e:
            logger.warning(f"ローカルキャッシュ検索エラー: {e}")
        
        # 重複除去とソート
        results = self._deduplicate_and_sort(results, query)
        
        logger.info(f"[Recall] query: {query}, results: {len(results)}")
        return results[:limit]
    
    def _is_in_scope(self, timestamp_str: str, scope: str) -> bool:
        """スコープに合致するか判定"""
        if scope == "all":
            return True

        if not timestamp_str:
            return False

        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except (ValueError, TypeError):
            return False

        delta = datetime.now() - timestamp
        if scope == "today":
            return delta.days <= 0
        if scope == "week":
            return delta.days <= 7
        if scope == "month":
            return delta.days <= 30

        return True
    
    def _parse_note_content(self, path: Path, content: str) -> Dict[str, Any]:
        """ノート内容からメタデータを抽出して辞書化"""
        import yaml
        import re
        
        note_dict = {
            "path": str(path),
            "title": path.stem,
            "content": content,
            "tags": [],
            "frontmatter": {}
        }
        
        # フロントマターの抽出
        frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if frontmatter_match:
            try:
                frontmatter_str = frontmatter_match.group(1)
                # 単純なYAML解析（PyYAMLがない場合への備えとして簡易パーサーも検討すべきだが、今回は標準入出力の前提で）
                # ここでは簡易的に処理
                frontmatter = {}
                for line in frontmatter_str.split('\n'):
                    if ':' in line:
                        key, val = line.split(':', 1)
                        key = key.strip()
                        val = val.strip().strip('"\'')
                        if val.startswith('[') and val.endswith(']'):
                             # リストの簡易パース
                             val = [v.strip().strip('"\'') for v in val[1:-1].split(',')]
                        frontmatter[key] = val
                note_dict["frontmatter"] = frontmatter
                
                # コンテンツからフロントマターを除去
                note_dict["content"] = content[len(frontmatter_match.group(0)):]
            except Exception as e:
                logger.warning(f"フロントマター解析エラー: {e}")
        
        return note_dict

    def _note_to_unified_format(self, note: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Obsidianノートを統一フォーマットに変換"""
        try:
            frontmatter = note.get("frontmatter", {})
            return {
                "id": frontmatter.get("id", str(uuid.uuid4())),
                "type": frontmatter.get("type", "system"),
                "timestamp": frontmatter.get("created", datetime.now().isoformat()),
                "content": note.get("content", ""),
                "metadata": {
                    "title": note.get("title", ""),
                    "tags": note.get("tags", []),
                    "path": note.get("path", "")
                }
            }
        except Exception as e:
            logger.warning(f"ノート変換エラー: {e}")
            return None
    
    def _search_local_cache(
        self,
        query: str,
        scope: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """ローカルキャッシュから検索"""
        results = []
        query_lower = query.lower()
        
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    
                    # クエリで検索
                    content_str = str(content).lower()
                    if query_lower in content_str:
                        # スコープでフィルタ
                        if scope != "all":
                            timestamp_str = content.get("timestamp", "")
                            if timestamp_str:
                                try:
                                    timestamp = datetime.fromisoformat(timestamp_str)
                                    delta = datetime.now() - timestamp
                                    
                                    if scope == "today" and delta.days > 0:
                                        continue
                                    elif scope == "week" and delta.days > 7:
                                        continue
                                    elif scope == "month" and delta.days > 30:
                                        continue
                                except (ValueError, KeyError):
                                    pass
                        
                        results.append(content)
                        if len(results) >= limit:
                            break
                
                except Exception as e:
                    continue
        
        except Exception as e:
            logger.error(f"ローカルキャッシュ検索エラー: {e}")
        
        return results
    
    def _deduplicate_and_sort(
        self,
        results: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """重複除去とソート"""
        # IDで重複除去
        seen_ids = set()
        unique_results = []
        
        for result in results:
            result_id = result.get("id", "")
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)
        
        # タイムスタンプでソート（新しい順）
        unique_results.sort(
            key=lambda x: x.get("timestamp", ""),
            reverse=True
        )
        
        return unique_results


# 使用例
if __name__ == "__main__":
    memory = UnifiedMemory()
    
    # 記憶への保存
    memory_id = memory.store({
        "content": "今日はいい天気でした。",
        "metadata": {"source": "conversation"}
    }, format_type="conversation")
    print(f"保存完了: {memory_id}")
    
    # 記憶からの検索
    results = memory.recall("天気", scope="all", limit=5)
    print(f"検索結果: {len(results)}件")
    for result in results:
        print(f"  - {result.get('content', '')[:50]}...")


















