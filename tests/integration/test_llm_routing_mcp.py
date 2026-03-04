"""
llm-routing MCPサーバーのインポートテスト
"""
import sys
import os

workspace_path = os.path.dirname(os.path.abspath(__file__))
if workspace_path not in sys.path:
    sys.path.insert(0, workspace_path)

print(f"Workspace path: {workspace_path}")
print()

try:
    print("1. Importing llm_routing_mcp_server.server...")
    from llm_routing_mcp_server.server import app, main
    print("   [OK] llm_routing_mcp_server.server imported")
    print(f"   Server name: {app.name if app else 'None'}")
    print(f"   Main function: {main}")
except Exception as e:
    print(f"   [ERROR] Import failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("Test completed.")














