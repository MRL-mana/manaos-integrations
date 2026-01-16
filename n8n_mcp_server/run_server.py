"""
n8n MCPサーバーを実行するラッパースクリプト
PYTHONPATHの問題を回避するため、明示的にパスを設定してから実行
"""
import sys
import os

# ワークスペースパスを取得（このスクリプトの親ディレクトリの親ディレクトリ）
workspace_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# sys.pathに追加
if workspace_path not in sys.path:
    sys.path.insert(0, workspace_path)

# 環境変数も設定（念のため）
os.environ.setdefault('PYTHONPATH', workspace_path)

# モジュールをインポートして実行
if __name__ == "__main__":
    from n8n_mcp_server.server import server
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    asyncio.run(main())















