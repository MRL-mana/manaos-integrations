"""
manaos-unified-konohaのツール一覧を抽出
"""
import re
from pathlib import Path

def extract_tools(file_path: str):
    """MCPサーバーファイルからツール定義を抽出"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Tool定義を抽出
    pattern = r'Tool\(\s*name="([^"]+)"\s*,\s*description="([^"]+)"'
    matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
    
    return matches

def main():
    file_path = "konoha_mcp_servers/archive_20251106/manaos_mcp_server.py"
    
    print("=" * 70)
    print("manaos-unified-konoha ツール一覧")
    print("=" * 70)
    print("")
    
    tools = extract_tools(file_path)
    
    # カテゴリ別に分類
    categories = {
        "ManaOS Core": [],
        "ALITA-G MCT": [],
        "画像生成": [],
        "Trinity System": [],
        "システム管理": [],
        "X280": [],
        "Evolution Shadow": [],
        "Remi Autonomy": [],
        "その他": []
    }
    
    for name, desc in tools:
        if "manaos_system" in name or "manaos_service" in name or "manaos_api" in name or "manaos_screen" in name:
            categories["ManaOS Core"].append((name, desc))
        elif "alita" in name:
            categories["ALITA-G MCT"].append((name, desc))
        elif "image" in name.lower() or "generate" in name.lower():
            categories["画像生成"].append((name, desc))
        elif "trinity" in name.lower() or "copilot" in name.lower():
            categories["Trinity System"].append((name, desc))
        elif "optimize" in name.lower() or "backup" in name.lower() or "monitor" in name.lower() or "deploy" in name.lower():
            categories["システム管理"].append((name, desc))
        elif "x280" in name.lower():
            categories["X280"].append((name, desc))
        elif "evolution" in name.lower():
            categories["Evolution Shadow"].append((name, desc))
        elif "remi" in name.lower():
            categories["Remi Autonomy"].append((name, desc))
        else:
            categories["その他"].append((name, desc))
    
    total = 0
    for category, tool_list in categories.items():
        if tool_list:
            print(f"## {category} ({len(tool_list)}個)")
            print("")
            for name, desc in tool_list:
                print(f"### {name}")
                print(f"{desc}")
                print("")
            total += len(tool_list)
    
    print("=" * 70)
    print(f"合計: {total}個のツール")
    print("=" * 70)

if __name__ == "__main__":
    main()









