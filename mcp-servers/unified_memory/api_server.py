#!/usr/bin/env python3
"""
🚀 Unified Memory System - REST API Server
Phase 1: すぐに使えるAPIサーバー

起動: python3 api_server.py
アクセス: http://localhost:8800
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
from datetime import datetime

from core.unified_memory_api import UnifiedMemoryAPI

app = FastAPI(
    title="🧠 Unified Memory System API",
    description="Mana統合記憶システム - 全記憶を統一的に扱うAPI",
    version="1.0.0 (MEGA EVOLUTION Phase 1)"
)

# グローバルAPI instance
memory_api = UnifiedMemoryAPI()


# ==================== Request/Response Models ====================

class StoreRequest(BaseModel):
    content: str = Field(..., description="保存する内容")
    title: Optional[str] = Field(None, description="タイトル")
    importance: int = Field(5, ge=1, le=10, description="重要度 (1-10)")
    tags: Optional[List[str]] = Field(None, description="タグリスト")
    category: Optional[str] = Field(None, description="カテゴリ")
    metadata: Optional[Dict[str, Any]] = Field(None, description="追加メタデータ")


class SearchFilters(BaseModel):
    importance_min: Optional[int] = Field(None, description="最低重要度")
    category: Optional[str] = Field(None, description="カテゴリフィルター")
    date_from: Optional[str] = Field(None, description="開始日時")
    sources: Optional[List[str]] = Field(None, description="検索対象システム")


# ==================== API Endpoints ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """ダッシュボードHTML"""
    stats = await memory_api.get_stats()
    
    html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 Unified Memory System</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
        }}
        .container {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            color: #333;
        }}
        h1 {{
            text-align: center;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #999;
            margin-bottom: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            color: #fff;
        }}
        .stat-number {{
            font-size: 48px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .api-section {{
            margin-top: 40px;
        }}
        .endpoint {{
            background: #f8f9fa;
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }}
        .method {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 5px;
            font-weight: bold;
            margin-right: 10px;
        }}
        .get {{ background: #28a745; color: #fff; }}
        .post {{ background: #007bff; color: #fff; }}
        code {{
            background: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 Unified Memory System</h1>
        <p class="subtitle">MEGA EVOLUTION Phase 1 - 全記憶統合システム</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{stats['total_memories']}</div>
                <div class="stat-label">総記憶数</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['sources'].get('ai_learning', {}).get('count', 0)}</div>
                <div class="stat-label">AI Learning</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['sources'].get('obsidian', {}).get('count', 0)}</div>
                <div class="stat-label">Obsidian</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats['sources'].get('context_memory', {}).get('count', 0)}</div>
                <div class="stat-label">会話履歴</div>
            </div>
        </div>
        
        <div class="api-section">
            <h2>📡 API Endpoints</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/search</code>
                <p>全システム横断検索</p>
                <small>例: <code>/api/search?q=X280&limit=10</code></small>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <code>/api/store</code>
                <p>スマート保存（重要度に応じて自動振り分け）</p>
                <small>ボディ: <code>{{"content": "...", "importance": 8}}</code></small>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/api/stats</code>
                <p>統計情報取得</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <code>/docs</code>
                <p>Swagger UI（対話的APIドキュメント）</p>
            </div>
        </div>
        
        <div class="footer">
            <p>⏱️ 最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>🚀 できる女子たちの総力戦！</p>
        </div>
    </div>
</body>
</html>
    """
    return html


@app.get("/api/stats")
async def get_stats(force_refresh: bool = Query(False, description="キャッシュを無視")):
    """
    統計情報取得
    
    Returns:
        全システムの統計情報
    """
    return await memory_api.get_stats(force_refresh=force_refresh)


@app.get("/api/search")
async def search(
    q: str = Query(..., description="検索クエリ"),
    limit: int = Query(20, ge=1, le=100, description="各システムからの最大結果数"),
    importance_min: Optional[int] = Query(None, description="最低重要度"),
    category: Optional[str] = Query(None, description="カテゴリフィルター"),
    sources: Optional[str] = Query(None, description="検索対象（カンマ区切り）")
):
    """
    全システム横断検索
    
    Args:
        q: 検索クエリ
        limit: 各システムからの最大結果数
        importance_min: 最低重要度フィルター
        category: カテゴリフィルター
        sources: 検索対象システム（例: "ai_learning,obsidian"）
        
    Returns:
        統合検索結果
    """
    filters = {}
    
    if importance_min:
        filters['importance_min'] = importance_min
    
    if category:
        filters['category'] = category
    
    if sources:
        filters['sources'] = [s.strip() for s in sources.split(',')]
    
    return await memory_api.unified_search(q, limit=limit, filters=filters)


@app.post("/api/store")
async def store(request: StoreRequest):
    """
    スマート保存
    
    重要度に応じて自動振り分け:
    - importance >= 8: 全システムに保存（超重要）
    - importance >= 5: AI Learning + Trinity（重要）
    - importance < 5: AI Learningのみ（通常）
    
    Args:
        request: 保存リクエスト
        
    Returns:
        保存結果
    """
    return await memory_api.smart_store(
        content=request.content,
        title=request.title,
        importance=request.importance,
        tags=request.tags,
        category=request.category,
        metadata=request.metadata
    )


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "service": "Unified Memory System",
        "version": "1.0.0 (MEGA EVOLUTION Phase 1)",
        "timestamp": datetime.now().isoformat()
    }


# ==================== 起動 ====================

if __name__ == '__main__':
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║       🧠 UNIFIED MEMORY SYSTEM - API SERVER                    ║
║       Phase 1: 全記憶統合システム起動                          ║
║                                                                ║
║       できる女子たちの総力戦！ 🔥                              ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

🚀 起動中...

アクセス:
  Dashboard : http://localhost:8800
  API Docs  : http://localhost:8800/docs
  Stats     : http://localhost:8800/api/stats
  
API使用例:
  検索 : curl "http://localhost:8800/api/search?q=X280"
  保存 : curl -X POST http://localhost:8800/api/store \\
         -H "Content-Type: application/json" \\
         -d '{"content": "テスト", "importance": 8}'

Press Ctrl+C to stop
    """)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8800,
        log_level="info"
    )

