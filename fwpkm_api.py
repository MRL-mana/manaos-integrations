#!/usr/bin/env python3
"""
FWPKM統合API
REST API + Python API
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from typing import Dict, Any, Optional
from pathlib import Path
import os
import uuid

from fwpkm_integration import UnifiedMemorySystem

# 統一モジュールのインポート
try:
    from manaos_logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# グローバルインスタンス
fwpkm_system: Optional[UnifiedMemorySystem] = None


def init_fwpkm_system():
    """FWPKMシステムを初期化"""
    global fwpkm_system
    if fwpkm_system is None:
        config_path = Path(__file__).parent / "fwpkm_config.yaml"
        fwpkm_system = UnifiedMemorySystem(config_path=config_path)
        logger.info("✅ FWPKMシステムを初期化しました")
    return fwpkm_system


@app.route('/health', methods=['GET'])
def health():
    """ヘルスチェック"""
    return jsonify({
        "status": "healthy",
        "service": "FWPKM Integration API"
    })


@app.route('/api/fwpkm/process', methods=['POST'])
def process_long_text():
    """
    長文をチャンク処理してメモリを更新
    
    Request Body:
    {
        "text": "長文テキスト...",
        "session_id": "session_123",
        "model": "qwen2.5:14b",
        "options": {
            "chunk_size": 2048,
            "use_long_term": true,
            "use_short_term": true
        }
    }
    """
    try:
        data = request.get_json() or {}
        text = data.get("text", "")
        session_id = data.get("session_id", str(uuid.uuid4()))
        model = data.get("model", "qwen2.5:14b")
        options = data.get("options", {})
        
        if not text:
            return jsonify({"error": "text is required"}), 400
        
        system = init_fwpkm_system()
        
        # 長文を処理
        results = []
        for result in system.process_long_text(
            text=text,
            model=model,
            session_id=session_id,
            use_memory=options.get("use_long_term", True) or options.get("use_short_term", True)
        ):
            results.append({
                "chunk_index": result["chunk_index"],
                "chunk_length": result["chunk_length"],
                "slots_updated": result["update_info"].slots_updated,
                "memory_state": result["update_info"].memory_state,
                "processing_time": result["update_info"].processing_time
            })
        
        return jsonify({
            "session_id": session_id,
            "results": results,
            "total_chunks": len(results)
        })
    
    except Exception as e:
        logger.error(f"長文処理エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/fwpkm/memory/<session_id>', methods=['GET'])
def get_session_memory(session_id: str):
    """
    セッションのメモリ状態を取得
    
    Query Parameters:
    - include_long_term: 長期記憶を含めるか（デフォルト: true）
    - include_short_term: 短期記憶を含めるか（デフォルト: true）
    """
    try:
        include_long_term = request.args.get("include_long_term", "true").lower() == "true"
        include_short_term = request.args.get("include_short_term", "true").lower() == "true"
        
        system = init_fwpkm_system()
        
        # セッション状態を取得
        session_state = system.get_session_memory_state(session_id)
        
        # 長期記憶を取得（オプション）
        if include_long_term:
            # 実装: 長期記憶の取得
            pass
        
        return jsonify(session_state)
    
    except Exception as e:
        logger.error(f"メモリ状態取得エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/fwpkm/search', methods=['POST'])
def search_memory():
    """
    メモリから検索
    
    Request Body:
    {
        "query": "検索クエリ",
        "session_id": "session_123",
        "scope": "all"  # "all", "long_term", "short_term"
    }
    """
    try:
        data = request.get_json() or {}
        query = data.get("query", "")
        session_id = data.get("session_id")
        scope = data.get("scope", "all")
        
        if not query:
            return jsonify({"error": "query is required"}), 400
        
        system = init_fwpkm_system()
        
        # メモリから検索
        results = system.search_memory(
            query=query,
            session_id=session_id,
            scope=scope
        )
        
        return jsonify(results)
    
    except Exception as e:
        logger.error(f"メモリ検索エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/fwpkm/review', methods=['POST'])
def apply_review_effect():
    """
    復習効果を適用
    
    Request Body:
    {
        "text": "復習するテキスト",
        "session_id": "session_123",
        "review_count": 2
    }
    """
    try:
        data = request.get_json() or {}
        text = data.get("text", "")
        session_id = data.get("session_id", str(uuid.uuid4()))
        review_count = data.get("review_count", 1)
        
        if not text:
            return jsonify({"error": "text is required"}), 400
        
        system = init_fwpkm_system()
        
        # 復習効果を適用
        result = system.apply_review_effect(
            text=text,
            session_id=session_id,
            review_count=review_count
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"復習効果適用エラー: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/fwpkm/update_hierarchy', methods=['POST'])
def update_memory_hierarchy():
    """
    メモリ階層を更新
    
    Request Body:
    {
        "content": "コンテンツ",
        "importance": 0.8,
        "session_id": "session_123"
    }
    """
    try:
        data = request.get_json() or {}
        content = data.get("content", "")
        importance = data.get("importance", 0.5)
        session_id = data.get("session_id", str(uuid.uuid4()))
        
        if not content:
            return jsonify({"error": "content is required"}), 400
        
        system = init_fwpkm_system()
        
        # メモリ階層を更新
        system.update_memory_hierarchy(
            content=content,
            importance=importance,
            session_id=session_id
        )
        
        return jsonify({
            "status": "success",
            "message": "メモリ階層を更新しました"
        })
    
    except Exception as e:
        logger.error(f"メモリ階層更新エラー: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5104))
    logger.info(f"🚀 FWPKM統合API起動中... (ポート: {port})")
    init_fwpkm_system()
    app.run(host='0.0.0.0', port=port, debug=os.getenv("DEBUG", "False").lower() == "true")
