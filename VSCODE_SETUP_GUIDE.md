# VSCode セットアップガイド

ManaOS IntegrationsをVSCodeで使用するための完全セットアップガイドです。

---

## 📋 前提条件

- **VSCode**: バージョン 1.80 以上
- **Python**: 3.9 以上
- **PowerShell**: 5.1 以上（Windowsに標準搭載）

---

## 🚀 クイックセットアップ（5分）

### 1. ワークスペースを開く

```
File → Open Folder → C:\Users\mana4\Desktop を選択
```

### 2. 推奨拡張機能をインストール

VSCodeが自動的に推奨拡張機能の通知を表示します：

```
右下の通知: "このワークスペースには推奨拡張機能があります"
→ [すべてインストール] をクリック
```

または手動で：
```
Ctrl+Shift+P → "Extensions: Show Recommended Extensions"
→ 各拡張機能の [Install] をクリック
```

### 3. Python インタープリターを選択

```
Ctrl+Shift+P → "Python: Select Interpreter"
→ "./.venv/Scripts/python.exe" を選択
```

### 4. ワークスペース設定を適用

デスクトップに既にワークスペース用の設定ファイルを用意しています：

```powershell
# PowerShellで実行
cd C:\Users\mana4\Desktop
Copy-Item .vscode\settings.json.workspace .vscode\settings.json -Force
```

または手動で：
1. `.vscode/settings.json.workspace` を開く
2. すべてコピー
3. `.vscode/settings.json` に貼り付け（既存の内容を考慮）

### 5. サービスを起動

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: すべてのサービスを起動"
```

✅ セットアップ完了！

---

## 📦 推奨拡張機能の詳細

### 必須拡張機能

| 拡張機能 | 提供元 | 用途 |
|---------|--------|------|
| **Python** | Microsoft | Python開発の基本機能 |
| **Pylance** | Microsoft | Python言語サーバー（高速補完） |
| **Python Debugger** | Microsoft | Pythonデバッグ機能 |
| **Jupyter** | Microsoft | Notebookサポート |
| **PowerShell** | Microsoft | PowerShellスクリプト実行 |

### 推奨拡張機能

| 拡張機能 | 提供元 | 用途 |
|---------|--------|------|
| **YAML** | Red Hat | YAML設定ファイル編集 |
| **Markdown Lint** | David Anson | マークダウン品質チェック |
| **Code Spell Checker** | Street Side Software | スペルチェック |
| **GitLens** | GitKraken | Git履歴表示 |
| **Todo Tree** | Gruntfuggly | TODOコメント管理 |
| **Error Lens** | usernamehw | エラー表示強化 |
| **Even Better TOML** | tamasfe | TOML設定ファイル |

### インストール確認

```
Ctrl+Shift+X → 検索バーで "Python" → インストール済みか確認
```

---

## ⚙️ ワークスペース設定の説明

### `.vscode/settings.json` の主要設定

#### Python設定
```jsonc
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.extraPaths": [
    "${workspaceFolder}/manaos_integrations"
  ]
}
```

**説明:**
- 仮想環境（`.venv`）のPythonを自動使用
- 型チェックを有効化
- `manaos_integrations` をインポートパスに追加

#### ターミナル設定
```jsonc
{
  "python.terminal.activateEnvironment": true,
  "terminal.integrated.cwd": "${workspaceFolder}"
}
```

**説明:**
- ターミナル起動時に自動で仮想環境をアクティベート
- 作業ディレクトリをワークスペースルートに固定

#### ファイル除外設定
```jsonc
{
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/.mypy_cache": true
  }
}
```

**説明:**
- 不要なファイル（キャッシュなど）を非表示
- エクスプローラーがすっきり

---

## 🔧 タスク設定

### 利用可能なタスク

VSCodeのタスクランナーで以下が使用可能：

| タスク名 | 説明 | ショートカット |
|---------|------|---------------|
| **ManaOS: すべてのサービスを起動** | 4サービスを一括起動 | Ctrl+Shift+B（デフォルトビルド） |
| **ManaOS: サービスヘルスチェック** | 全サービスの健全性確認 | - |
| **🚨 ManaOS: 緊急停止** | 全サービスを強制停止 | - |
| **ManaOS: MRLメモリを起動** | MRL Memoryのみ起動 | - |
| **ManaOS: 学習システムを起動** | Learning Systemのみ起動 | - |
| **ManaOS: LLMルーティングを起動** | LLM Routingのみ起動 | - |
| **ManaOS: 統合APIを起動** | Unified APIのみ起動 | - |

### タスク実行方法

**方法1: コマンドパレット**
```
Ctrl+Shift+P → "Tasks: Run Task" → タスクを選択
```

**方法2: デフォルトビルドタスク**
```
Ctrl+Shift+B → 直接起動
```

**方法3: ターミナルから**
```powershell
# PowerShellで
cd C:\Users\mana4\Desktop\manaos_integrations
python start_vscode_cursor_services.py
```

---

## 🐍 Python環境の設定

### 仮想環境の作成（初回のみ）

```powershell
cd C:\Users\mana4\Desktop
python -m venv .venv
```

### 仮想環境のアクティベート

**PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**VSCodeターミナル:**
- 新しいターミナルを開くと自動でアクティベート

### 依存関係のインストール

```powershell
cd manaos_integrations
pip install -r requirements-core.txt
```

または全機能：
```powershell
pip install -r requirements.txt
```

---

## 🔌 MCP サーバー設定（オプション）

ManaOSのAI機能をVSCode拡張機能から使用する場合の設定です。

### VSCode用のMCP設定

VSCodeでは現在、標準的なMCPサーバー統合機能がありません。以下の方法を使用：

#### 方法1: REST API経由（推奨）

Unified API（ポート9500）経由で直接アクセス：

```powershell
# サービスを起動
Ctrl+Shift+B

# PowerShellでAPI確認
Invoke-RestMethod http://127.0.0.1:9500/health
```

VSCode拡張機能から `http://127.0.0.1:9500` を使用してAPIを呼び出せます。

#### 方法2: 独自拡張機能の開発

VSCodeのTask Providerやコードアクションとして統合する方法：

**参考:**
- [VSCode Extension API](https://code.visualstudio.com/api)
- Task Provider実装
- Language Server Protocol

---

## 🎨 テーマとUI設定

### ManaOS推奨テーマ

```
Ctrl+K Ctrl+T → テーマを選択
```

**推奨:**
- **Dark+** (デフォルト) - 目に優しいダークテーマ
- **Monokai** - コントラスト高め
- **GitHub Dark** - GitHubと統一感

### アイコンテーマ

```
File → Preferences → File Icon Theme
```

**推奨:**
- **Seti (Visual Studio Code)** - 多様なファイルタイプ対応

---

## 🔍 デバッグ設定

### Python デバッグ設定

`.vscode/launch.json` を作成済み（まだない場合）:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/manaos_integrations"
      }
    },
    {
      "name": "Python: Unified API Server",
      "type": "python",
      "request": "launch",
      "module": "unified_api_server",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/manaos_integrations"
    }
  ]
}
```

### デバッグ実行

1. ブレークポイントを設定（行番号左をクリック）
2. `F5` または Run and Debug パネルから起動
3. 変数の値を確認、ステップ実行

---

## 📝 キーボードショートカット

### ManaOS固有

| 操作 | ショートカット |
|------|---------------|
| サービス起動 | `Ctrl+Shift+B` |
| タスク選択 | `Ctrl+Shift+P` → "Tasks: Run Task" |
| ターミナル | `Ctrl+J` |
| コマンドパレット | `Ctrl+Shift+P` |

### VSCode標準（よく使う）

| 操作 | ショートカット |
|------|---------------|
| ファイル検索 | `Ctrl+P` |
| シンボル検索 | `Ctrl+Shift+O` |
| 全体検索 | `Ctrl+Shift+F` |
| 置換 | `Ctrl+H` |
| コメントトグル | `Ctrl+/` |
| フォーマット | `Shift+Alt+F` |
| 定義へ移動 | `F12` |
| 参照を検索 | `Shift+F12` |

---

## 🐛 トラブルシューティング

### Python インタープリターが見つからない

**症状:** "Python interpreter not found"

**対処:**
```powershell
# 仮想環境を再作成
cd C:\Users\mana4\Desktop
Remove-Item -Recurse -Force .venv
python -m venv .venv

# 依存関係を再インストール
.\.venv\Scripts\Activate.ps1
cd manaos_integrations
pip install -r requirements-core.txt
```

その後、VSCodeで再選択：
```
Ctrl+Shift+P → "Python: Select Interpreter" → "./.venv/Scripts/python.exe"
```

### タスクが実行できない

**症状:** "No task to run found"

**対処:**
1. `.vscode/tasks.json` が存在するか確認
2. ワークスペースルート（`C:\Users\mana4\Desktop`）を開いているか確認
3. VSCodeを再起動

### 拡張機能がインストールできない

**症状:** インストールがタイムアウトする

**対処:**
```powershell
# プロキシ設定（必要な場合）
code --install-extension ms-python.python

# または手動でダウンロード
# https://marketplace.visualstudio.com/items?itemName=ms-python.python
```

### ターミナルで仮想環境がアクティベートされない

**症状:** ターミナルで `(venv)` が表示されない

**対処:**
```powershell
# 実行ポリシーを確認
Get-ExecutionPolicy

# 必要に応じて変更（管理者権限）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

その後VSCodeを再起動。

---

## 📚 関連ドキュメント

- **[クイックリファレンス](../QUICKREF.md)** - 最もよく使うコマンド
- **[起動ガイド](../STARTUP_GUIDE.md)** - 詳細な起動手順
- **[System3ガイド](../SYSTEM3_GUIDE.md)** - 自律運用システム
- **[緊急停止ガイド](../EMERGENCY_STOP_GUIDE.md)** - トラブル時の対処

---

## 🆘 さらにサポートが必要な場合

1. **ログを確認**: `manaos_integrations/logs/`
2. **ヘルスチェック実行**: `Ctrl+Shift+P` → "ManaOS: サービスヘルスチェック"
3. **GitHub Issues**: バグ報告や機能要望

---

**最終更新**: 2026年2月7日  
**対象バージョン**: VSCode 1.80+  
**プラットフォーム**: Windows 10/11
