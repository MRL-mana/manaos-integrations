# VSCode セットアップ検証チェックリスト

VSCode対応が正しく動作するか確認するためのテストチェックリスト。

---

## ✅ 検証項目

### 1. **拡張機能の推奨表示**

#### テスト手順:
```
1. VSCode起動
2. ワークスペースを開く: C:\Users\mana4\Desktop
3. 右下の通知を確認
```

#### ✅ 期待結果:
- [ ] 「このワークスペースには推奨拡張機能があります」通知が表示される
- [ ] 「すべてインストール」ボタンが表示される
- [ ] クリックすると12個の拡張機能がインストールされる

#### 📋 推奨拡張機能リスト（12個）:
- [ ] Python (ms-python.python)
- [ ] Pylance (ms-python.vscode-pylance)
- [ ] Python Debugger (ms-python.debugpy)
- [ ] Jupyter (ms-toolsai.jupyter)
- [ ] PowerShell (ms-vscode.powershell)
- [ ] YAML (redhat.vscode-yaml)
- [ ] Markdown Lint (davidanson.vscode-markdownlint)
- [ ] Code Spell Checker (streetsidesoftware.code-spell-checker)
- [ ] GitLens (eamodio.gitlens)
- [ ] Todo Tree (gruntfuggly.todo-tree)
- [ ] Error Lens (usernamehw.errorlens)
- [ ] Even Better TOML (tamasfe.even-better-toml)

---

### 2. **ワークスペース設定の適用**

#### テスト手順:
```powershell
# PowerShellで実行
Copy-Item .vscode\settings.json.workspace .vscode\settings.json -Force
```

その後、VSCodeで:
```
Ctrl+Shift+P → "Python: Select Interpreter" → "./.venv/Scripts/python.exe"
```

#### ✅ 期待結果:
- [ ] Pythonインタープリターが正しく認識される
- [ ] `manaos_integrations`がインポートパスに追加される
- [ ] `__pycache__`フォルダがエクスプローラーから非表示になる
- [ ] Pythonファイル保存時に自動フォーマットされる

#### 確認方法:
```python
# 任意の .py ファイルで
from mrl_memory_system import something  # ← エラーが出ないか確認
```

---

### 3. **タスクの実行テスト**

#### 3-1. デフォルトビルドタスク

```
Ctrl+Shift+B
```

#### ✅ 期待結果:
- [ ] "ManaOS: すべてのサービスを起動"が実行される
- [ ] 4つのサービスが起動する
- [ ] ターミナルに起動ログが表示される
- [ ] 5秒後にヘルスチェックが実行される

---

#### 3-2. ヘルスチェックタスク

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: サービスヘルスチェック"
```

#### ✅ 期待結果:
- [ ] 全サービスのヘルスチェックが実行される
- [ ] 各サービスの状態が表示される（OK/ERROR）
- [ ] リトライ機能が動作する（失敗時）

---

#### 3-3. 個別サービスタスク

```
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: MRLメモリを起動"
```

#### ✅ 期待結果:
- [ ] MRL Memoryサービスのみが起動する
- [ ] ポート5103で待ち受ける
- [ ] エラーが発生しない

同様に以下も確認:
- [ ] "ManaOS: 学習システムを起動" (ポート5104)
- [ ] "ManaOS: LLMルーティングを起動" (ポート5111)
- [ ] "ManaOS: 統合APIを起動" (ポート9500)

---

#### 3-4. 緊急停止タスク

```
Ctrl+Shift+P → "Tasks: Run Task" → "🚨 ManaOS: 緊急停止"
```

#### ✅ 期待結果:
- [ ] 確認プロンプトが表示される
- [ ] "yes"と入力すると全サービスが停止する
- [ ] プロセスが正常に終了する

---

### 4. **デバッグ構成のテスト**

#### 4-1. Unified API Server

```
1. manaos_integrations/unified_api_mcp_server.py を開く
2. 任意の行にブレークポイントを設定（行番号左クリック）
3. F5 → "ManaOS: Unified API Server"
```

#### ✅ 期待結果:
- [ ] デバッグが開始される
- [ ] ポート9500でサービスが起動する
- [ ] ブレークポイントで停止する（該当行が実行された場合）
- [ ] 変数ウォッチが機能する
- [ ] ステップ実行（F10, F11）が機能する

---

#### 4-2. その他のサービス

同様に以下のデバッグ構成もテスト:

- [ ] "ManaOS: MRL Memory" (ポート5103)
- [ ] "ManaOS: Learning System" (ポート5104)
- [ ] "ManaOS: LLM Routing" (ポート5111)
- [ ] "ManaOS: Autonomous Operations"
- [ ] "ManaOS: Health Check"

---

#### 4-3. Current File

```
1. 任意のPythonファイルを開く
2. F5 → "Python: Current File"
```

#### ✅ 期待結果:
- [ ] 開いているファイルが実行される
- [ ] 統合ターミナルに出力される
- [ ] PYTHONPATHが正しく設定される（manaos_integrationsをインポート可能）

---

### 5. **スニペットのテスト**

#### 5-1. 基本的なスニペット

```python
# 新規 test_snippet.py ファイルを作成
manaos_health [Tab]
```

#### ✅ 期待結果:
- [ ] ヘルスチェックエンドポイントのコードが展開される
- [ ] プレースホルダーが表示される（`service_name`, `version`）
- [ ] Tabキーで次のプレースホルダーに移動できる
- [ ] Shift+Tabで前のプレースホルダーに戻れる

---

#### 5-2. すべてのスニペット

以下のスニペットが正しく動作するか確認:

- [ ] `manaos_health` - ヘルスチェックエンドポイント
- [ ] `manaos_init` - サービス初期化（60行展開）
- [ ] `manaos_mcp_tool` - MCPツール定義
- [ ] `manaos_error` - エラーハンドリング
- [ ] `manaos_endpoint` - REST APIエンドポイント
- [ ] `manaos_autonomous` - 自律チェック関数
- [ ] `manaos_test` - テストケース
- [ ] `manaos_config` - 設定ローダー

---

### 6. **ドキュメントの確認**

#### 6-1. リンクの動作確認

```
README.md を開く → 各ドキュメントリンクをクリック
```

#### ✅ 期待結果:
- [ ] すべてのリンクが正しく開く
- [ ] 404エラーが発生しない

#### 確認するドキュメント:
- [ ] QUICKREF.md
- [ ] VSCODE_SETUP_GUIDE.md
- [ ] VSCODE_VS_CURSOR.md
- [ ] VSCODE_CHECKLIST.md
- [ ] SNIPPETS_GUIDE.md
- [ ] STARTUP_GUIDE.md
- [ ] SYSTEM3_GUIDE.md
- [ ] EMERGENCY_STOP_GUIDE.md

---

#### 6-2. ドキュメント内容の確認

各ドキュメントを開いて確認:

- [ ] コードブロックが正しくレンダリングされる
- [ ] 表が正しく表示される
- [ ] 見出し階層が適切
- [ ] リンクが機能する

---

### 7. **統合テスト**

#### シナリオ: 新規サービスの作成とデバッグ

```python
# 1. 新規ファイル作成
# test_new_service.py

# 2. スニペットでテンプレート展開
manaos_init [Tab]
Test Service [Tab]
テスト機能 [Tab]
データ取得 [Tab]
Test API [Tab]
TEST_PORT [Tab]
5999 [Tab]

# 3. ブレークポイント設定（health関数内）

# 4. デバッグ実行
# F5 → "Python: Current File"

# 5. 別ターミナルで確認
# curl http://localhost:5999/health
```

#### ✅ 期待結果:
- [ ] サービスが起動する
- [ ] ブレークポイントで停止する
- [ ] curlでアクセスできる
- [ ] JSON応答が返る

---

## 🔧 自動検証スクリプト

PowerShellで一括検証:

```powershell
# validation_script.ps1

Write-Host "=== VSCode設定検証スクリプト ===" -ForegroundColor Cyan

# 1. 必須ファイルの存在確認
Write-Host "`n[1] 必須ファイルの確認" -ForegroundColor Yellow
$requiredFiles = @(
    ".vscode\extensions.json",
    ".vscode\settings.json.workspace",
    ".vscode\tasks.json",
    ".vscode\launch.json",
    ".vscode\python.code-snippets"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file (存在しない)" -ForegroundColor Red
    }
}

# 2. ドキュメントの存在確認
Write-Host "`n[2] ドキュメントの確認" -ForegroundColor Yellow
$docs = @(
    "manaos_integrations\README.md",
    "manaos_integrations\QUICKREF.md",
    "manaos_integrations\VSCODE_SETUP_GUIDE.md",
    "manaos_integrations\VSCODE_VS_CURSOR.md",
    "manaos_integrations\VSCODE_CHECKLIST.md",
    "manaos_integrations\SNIPPETS_GUIDE.md",
    "manaos_integrations\STARTUP_GUIDE.md",
    "manaos_integrations\SYSTEM3_GUIDE.md",
    "manaos_integrations\EMERGENCY_STOP_GUIDE.md"
)

foreach ($doc in $docs) {
    if (Test-Path $doc) {
        Write-Host "  ✅ $doc" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $doc (存在しない)" -ForegroundColor Red
    }
}

# 3. Python環境の確認
Write-Host "`n[3] Python環境の確認" -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "  ✅ Python venv存在" -ForegroundColor Green
    & .venv\Scripts\python.exe --version
} else {
    Write-Host "  ❌ Python venv が見つからない" -ForegroundColor Red
}

# 4. サービスの起動確認（ポートリスニング）
Write-Host "`n[4] サービス起動確認" -ForegroundColor Yellow
$ports = @(9500, 5111, 5104, 5103)
foreach ($port in $ports) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$port/health" -TimeoutSec 2
        Write-Host "  ✅ Port $port : $($response.status)" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  Port $port : 応答なし（サービス未起動またはエラー）" -ForegroundColor Yellow
    }
}

Write-Host "`n=== 検証完了 ===" -ForegroundColor Cyan
```

保存して実行:
```powershell
.\validation_script.ps1
```

---

## 📊 検証結果の記録

| 項目 | 状態 | メモ |
|------|------|------|
| 拡張機能推奨 | ⬜ | |
| ワークスペース設定 | ⬜ | |
| デフォルトビルドタスク | ⬜ | |
| ヘルスチェックタスク | ⬜ | |
| 個別サービスタスク | ⬜ | |
| 緊急停止タスク | ⬜ | |
| デバッグ構成（全7個） | ⬜ | |
| スニペット（全8個） | ⬜ | |
| ドキュメントリンク | ⬜ | |
| 統合テスト | ⬜ | |

✅ = 成功 / ⚠️ = 警告 / ❌ = 失敗

---

## 🆘 トラブルシューティング

### 問題: 拡張機能が推奨されない

**解決策**:
```
1. extensions.json の中身を確認
2. VSCodeを再起動
3. ワークスペースを開き直す
```

### 問題: タスクが実行されない

**解決策**:
```
1. tasks.json の構文を確認
2. Ctrl+Shift+P → "Tasks: Run Task" でリスト確認
3. ターミナルを閉じてから再実行
```

### 問題: デバッグが起動しない

**解決策**:
```
1. launch.json の構文を確認
2. Python拡張機能がインストール済みか確認
3. Pythonインタープリターが選択されているか確認
```

---

**最終更新**: 2026年2月7日  
**検証対象**: VSCode 1.80+  
**所要時間**: 約20分
