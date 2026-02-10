# config/

ManaOS Integrations の設定ファイル・スキーマ置き場。

## 構成

| ファイル | 用途 |
|----------|------|
| `ask_orchestrator_tool.json` | ask_orchestrator ツール定義 |
| `autonomy_level_config.example.json` | 自律レベル設定のサンプル |
| `autonomy_level_schema.json` | 自律レベル設定の JSON スキーマ |
| `runbooks/` | 定義済み Runbook（L4 自律実行用） |

## runbooks/

L4 で自動実行してよい「定義済み低リスク Runbook」のテンプレート集。

- `autonomy_level_config.json` の `runbooks_enabled` に ID を列挙すると実行対象
- 各 JSON: `id` / `name` / `description` / `action_class` / `steps` / `conditions` / `safety`

→ 詳細: [runbooks/README.md](runbooks/README.md)

## 環境変数

主要な設定は `.env`（env.example をコピー）で行う。本ディレクトリはツール・自律・Runbook の JSON 定義用。
