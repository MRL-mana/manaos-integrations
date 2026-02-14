import pathlib
import re

EXT = pathlib.Path(r"C:\Users\mana4\.vscode\extensions\saoudrizwan.claude-dev-3.59.0\dist\extension.js")


def main() -> None:
    s = EXT.read_text(encoding="utf-8", errors="ignore")
    print("ext_exists", EXT.exists())
    print("len", len(s))

    needle = 'mcpSettings:"cline_mcp_settings.json"'
    idx = s.find(needle)
    print("needle_idx", idx)

    print("counts")
    for pat in [
        "cline_mcp_settings.json",
        "mcpSettings",
        "mcpServers",
        "globalStorage",
        "context.globalStorageUri",
        "context.globalStoragePath",
    ]:
        print(pat, s.count(pat))

    print("\ncontexts(cline_mcp_settings.json)")
    for i, m in enumerate(re.finditer(r"cline_mcp_settings\\.json", s)):
        start = max(0, m.start() - 220)
        end = min(len(s), m.end() + 260)
        print("---")
        print(s[start:end].replace("\n", " "))
        if i >= 2:
            break


if __name__ == "__main__":
    main()
