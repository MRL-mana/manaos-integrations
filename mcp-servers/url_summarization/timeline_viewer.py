#!/usr/bin/env python3
"""
タイムライン表示機能
時系列表示、ソース・ノート統合、視覚化
"""

import json
from pathlib import Path
from typing import Dict


class TimelineViewer:
    """タイムライン表示"""
    
    def __init__(self):
        self.notebooks_dir = Path("/root/url_summarization_system/data/notebooks")
    
    def get_timeline(self, notebook_id: str) -> Dict:
        """タイムライン取得"""
        try:
            notebook_file = self.notebooks_dir / f"{notebook_id}.json"
            
            if not notebook_file.exists():
                return {"success": False, "error": "ノートブックが見つかりません"}
            
            with open(notebook_file, 'r', encoding='utf-8') as f:
                notebook = json.load(f)
            
            # タイムライン作成
            timeline = []
            
            # ソース追加
            for source in notebook.get('sources', []):
                timeline.append({
                    "type": "source",
                    "title": source.get('title', ''),
                    "content": source.get('content', source.get('text', ''))[:200],
                    "timestamp": source.get('added_at', ''),
                    "url": source.get('url', '')
                })
            
            # ノート追加
            for note in notebook.get('notes', []):
                timeline.append({
                    "type": "note",
                    "title": note.get('question', 'ノート'),
                    "content": note.get('answer', ''),
                    "timestamp": note.get('created_at', '')
                })
            
            # 時系列ソート
            timeline.sort(key=lambda x: x['timestamp'])
            
            return {
                "success": True,
                "notebook_id": notebook_id,
                "timeline": timeline,
                "total_items": len(timeline)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_statistics(self, notebook_id: str) -> Dict:
        """統計情報取得"""
        try:
            notebook_file = self.notebooks_dir / f"{notebook_id}.json"
            
            if not notebook_file.exists():
                return {"success": False, "error": "ノートブックが見つかりません"}
            
            with open(notebook_file, 'r', encoding='utf-8') as f:
                notebook = json.load(f)
            
            sources = notebook.get('sources', [])
            notes = notebook.get('notes', [])
            
            # ソースタイプ別統計
            source_types = {}
            for source in sources:
                source_type = source.get('type', 'unknown')
                source_types[source_type] = source_types.get(source_type, 0) + 1
            
            # 総文字数
            total_words = sum([
                len(source.get('content', source.get('text', '')).split())
                for source in sources
            ])
            
            return {
                "success": True,
                "notebook_id": notebook_id,
                "statistics": {
                    "total_sources": len(sources),
                    "total_notes": len(notes),
                    "total_words": total_words,
                    "source_types": source_types,
                    "created_at": notebook.get('created_at', ''),
                    "updated_at": notebook.get('updated_at', '')
                }
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_timeline(self, notebook_id: str, query: str) -> Dict:
        """タイムライン検索"""
        try:
            timeline_result = self.get_timeline(notebook_id)
            
            if not timeline_result["success"]:
                return timeline_result
            
            timeline = timeline_result["timeline"]
            
            # 検索
            results = []
            for item in timeline:
                if query.lower() in item.get('title', '').lower() or \
                   query.lower() in item.get('content', '').lower():
                    results.append(item)
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total": len(results)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}

