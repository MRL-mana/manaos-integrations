# VSCode完全対応チェックリスト

ManaOS IntegrationsのVSCode完全対応状況です。

---

## ✅ 完了項目

### 基本設定
- [x] `.vscode/tasks.json` - タスク定義（完全互換）
- [x] `.vscode/launch.json` - デバッグ設定（ManaOS専用設定追加）
- [x] `.vscode/extensions.json` - 推奨拡張機能リスト
- [x] `.vscode/settings.json.workspace` - ワークスペース設定テンプレート

### ドキュメント
- [x] `VSCODE_SETUP_GUIDE.md` - VSCode完全セットアップガイド
- [x] `VSCODE_VS_CURSOR.md` - VSCodeとCursorの比較ガイド
- [x] `README.md` - VSCodeガイドへのリンク追加

### 機能
- [x] すべてのManaOSサービスのタスク実行
- [x] ヘルスチェックタスク
- [x] 緊急停止タスク
- [x] デバッグ設定（7つのManaOS専用構成）
- [x] Python環境自動検出

---

## 🎯 使い方クイックガイド

### 1. 初回セットアップ（5分）

```powershell
# 1. ワークスペースを開く
# VSCode → File → Open Folder → C:\Users\mana4\Desktop

# 2. 推奨拡張機能をインストール
# 右下の通知 → [すべてインストール]

# 3. Python インタープリターを選択
# Ctrl+Shift+P → "Python: Select Interpreter" → "./.venv/Scripts/python.exe"

# 4. ワークスペース設定を適用
Copy-Item .vscode\settings.json.workspace .vscode\settings.json -Force
```

### 2. サービス起動

```
Ctrl+Shift+B
```

または

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: すべてのサービスを起動"
```

### 3. デバッグ実行

```
F5 → "ManaOS: Unified API Server" を選択
```

ブレークポイントを設定してステップ実行可能。

### 4. ヘルスチェック

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: サービスヘルスチェック"
```

---

## 📦 インストールされる拡張機能

### 必須（自動インストール推奨）
1. **Python** (ms-python.python)
2. **Pylance** (ms-python.vscode-pylance)
3. **Python Debugger** (ms-python.debugpy)
4. **Jupyter** (ms-toolsai.jupyter)
5. **PowerShell** (ms-vscode.powershell)

### 推奨（便利機能）
6. **YAML** (redhat.vscode-yaml)
7. **Markdown Lint** (davidanson.vscode-markdownlint)
8. **Code Spell Checker** (streetsidesoftware.code-spell-checker)
9. **GitLens** (eamodio.gitlens)
10. **Todo Tree** (gruntfuggly.todo-tree)
11. **Error Lens** (usernamehw.errorlens)
12. **Even Better TOML** (tamasfe.even-better-toml)

---

## 🐛 デバッグ構成一覧

VSCodeのデバッグパネル（`Run and Debug`）で以下が選択可能：

| 構成名 | 説明 | 用途 |
|--------|------|------|
| **ManaOS: Unified API Server** | 統合APIサーバーをデバッグ | メインサーバーの問題調査 |
| **ManaOS: MRL Memory** | MRL Memoryをデバッグ | メモリシステムの問題調査 |
| **ManaOS: Learning System** | Learning Systemをデバッグ | 学習機能の問題調査 |
| **ManaOS: LLM Routing** | LLM Routingをデバッグ | ルーティングロジックの問題調査 |
| **ManaOS: Autonomous Operations** | 自律監視システムをデバッグ | System3の動作確認 |
| **ManaOS: Health Check** | ヘルスチェックをデバッグ | チェックロジックの確認 |
| **Python: Current File** | 現在開いているファイルを実行 | 一般的なPythonスクリプト |

### デバッグ実行手順

1. ブレークポイントを設定（行番号左をクリック）
2. `F5` を押す
3. 構成を選択（初回のみ）
4. 変数を確認、ステップ実行（`F10`, `F11`）

---

## 🔧 利用可能なタスク

| タスク名 | ショートカット | 説明 |
|---------|---------------|------|
| **ManaOS: すべてのサービスを起動** | `Ctrl+Shift+B` | 4サービスを一括起動 |
| **ManaOS: サービスヘルスチェック** | - | 全サービスの健全性確認 |
| **🚨 ManaOS: 緊急停止** | - | 全サービスを強制停止 |
| **ManaOS: MRLメモリを起動** | - | MRL Memoryのみ起動 |
| **ManaOS: 学習システムを起動** | - | Learning Systemのみ起動 |
| **ManaOS: LLMルーティングを起動** | - | LLM Routingのみ起動 |
| **ManaOS: 統合APIを起動** | - | Unified APIのみ起動 |
| **ManaOS: VSCode/Cursor統合を確認** | - | 統合状態を確認 |

---

## 🎨 ワークスペース設定の内容

`.vscode/settings.json.workspace` に含まれる主要設定：

### Python関連
```jsonc
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.extraPaths": ["${workspaceFolder}/manaos_integrations"]
}
```

### ファイル除外
```jsonc
{
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/.mypy_cache": true
  }
}
```

### フォーマット設定
```jsonc
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.python"
  }
}
```

---

## 🔄 CursorからVSCodeへの移行

### ステップ1: 拡張機能
```
Cursor: Ctrl+Shift+X → インストール済み一覧を確認
VSCode: 同じ拡張機能をインストール（または .vscode/extensions.json から一括）
```

### ステップ2: タスク
タスクは自動で共有されます（`.vscode/tasks.json`）

### ステップ3: MCP設定
- CursorのMCP設定は使えません
- REST API（http://127.0.0.1:9510）経由でアクセス

---

## 📚 関連ドキュメント

- **[VSCODE_SETUP_GUIDE.md](VSCODE_SETUP_GUIDE.md)** - 完全セットアップガイド
- **[VSCODE_VS_CURSOR.md](VSCODE_VS_CURSOR.md)** - VSCode vs Cursor比較
- **[QUICKREF.md](QUICKREF.md)** - クイックリファレンス
- **[STARTUP_GUIDE.md](STARTUP_GUIDE.md)** - 起動ガイド

---

## ✨ VSCode固有の利点

### 1. 安定性
- 枯れたコードベース
- 大規模なユーザーベース
- 豊富なトラブルシューティング情報

### 2. 軽量性
- Cursorより起動が速い
- メモリ使用量が少ない
- 複数インスタンス起動に有利

### 3. 拡張機能エコシステム
- 最も豊富な拡張機能
- 企業向け拡張機能のサポート
- 標準的な開発環境

### 4. リモート開発
- SSH接続でのリモート開発
- WSL統合
- Dev Containers

---

## 🆘 トラブルシューティング

### Q: タスクが表示されない

**A:** ワークスペースルート（`C:\Users\mana4\Desktop`）を開いているか確認

```
File → Open Folder → C:\Users\mana4\Desktop を選択
```

### Q: Python インタープリターが見つからない

**A:** 仮想環境を再作成して選択

```powershell
cd C:\Users\mana4\Desktop
python -m venv .venv
```

その後、VSCodeで：
```
Ctrl+Shift+P → "Python: Select Interpreter" → "./.venv/Scripts/python.exe"
```

### Q: デバッグが起動しない

**A:** デバッグ構成を確認

```
Run and Debug パネル → 構成を選択 → F5
```

---

**最終更新**: 2026年2月7日  
**対応状況**: ✅ 完全対応  
**推奨バージョン**: VSCode 1.80+
