# よくある質問（FAQ）

ManaOS Integrations + VSCode/Cursorの使用に関するよくある質問と回答集。

---

## 📋 目次

- [セットアップ](#セットアップ)
- [サービス起動](#サービス起動)
- [トラブルシューティング](#トラブルシューティング)
- [VSCode vs Cursor](#vscode-vs-cursor)
- [デバッグ](#デバッグ)
- [パフォーマンス](#パフォーマンス)
- [セキュリティ](#セキュリティ)

---

## セットアップ

### Q1: 初回セットアップで何をすべきですか？

**A:** 5分クイックセットアップを実行してください：

```powershell
# 1. ワークスペースを開く
# VSCode → File → Open Folder → manaos_integrations

# 2. 推奨拡張機能をインストール
# 右下の通知 → [すべてインストール]

# 3. Python インタープリターを選択
# Ctrl+Shift+P → "Python: Select Interpreter" → "../.venv/Scripts/python.exe"

# 4. ワークスペース設定を適用
Copy-Item .vscode\settings.json.workspace .vscode\settings.json -Force

# 5. サービス起動
# Ctrl+Shift+B
```

詳細: [VSCODE_SETUP_GUIDE.md](VSCODE_SETUP_GUIDE.md)

---

### Q2: Python仮想環境をどこに作成すべきですか？

**A:** リポジトリの親フォルダ（Desktop）に作成してください：

```powershell
cd C:\Users\mana4\Desktop
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r manaos_integrations\requirements-core.txt
```

理由: すべてのManaOSプロジェクトで同じ環境を共有できます。

---

### Q3: 拡張機能が推奨されません

**A:** 以下を確認：

1. ワークスペースルート（`manaos_integrations`フォルダ）を開いているか
2. `.vscode/extensions.json`が存在するか
3. VSCodeを再起動

```powershell
# VSCode再起動
Ctrl+Shift+P → "Developer: Reload Window"
```

---

## サービス起動

### Q4: サービスが起動しません

**A:** 段階的に確認：

```powershell
# 1. Python環境確認
python --version  # 3.11以上

# 2. 依存関係確認
pip install -r requirements-core.txt

# 3. 個別サービスをテスト起動
python -m mrl_memory_integration
# → エラーメッセージを確認

# 4. ポート競合確認
netstat -ano | findstr "9502 5105 5126 5111"
# → すでに使用されている場合は停止
```

詳細: [STARTUP_GUIDE.md](STARTUP_GUIDE.md#トラブルシューティング)

---

### Q5: サービスが「起動したまま」応答しない

**A:** ヘルスチェックで状態確認：

```powershell
# タスクから実行
Ctrl+Shift+P → "Tasks: Run Task" → "ManaOS: サービスヘルスチェック"

# または直接実行
cd manaos_integrations
python check_services_health.py
```

すべてエラーの場合は緊急停止して再起動：

```
Ctrl+Shift+P → "Tasks: Run Task" → "🚨 ManaOS: 緊急停止"
→ "yes" と入力
→ Ctrl+Shift+B で再起動
```

---

### Q6: 特定のサービスだけ起動したい

**A:** 個別タスクを使用：

```
Ctrl+Shift+P → "Tasks: Run Task" →
  - "ManaOS: MRLメモリを起動"
  - "ManaOS: 学習システムを起動"
  - "ManaOS: LLMルーティングを起動"
  - "ManaOS: 統合APIを起動"
```

または、PowerShellで直接：

```powershell
python -m mrl_memory_integration     # ポート5105
python -m learning_system_api        # ポート5126
python -m llm_routing_mcp_server     # ポート5111
python -m unified_api_server         # ポート9502
```

---

## トラブルシューティング

### Q7: `ModuleNotFoundError: No module named 'XXX'`

**A:** 依存関係を再インストール：

```powershell
cd C:\Users\mana4\Desktop
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r manaos_integrations\requirements-core.txt
```

それでも解決しない場合は、環境を再作成：

```powershell
deactivate
Remove-Item .venv -Recurse -Force
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r manaos_integrations\requirements-core.txt
```

---

### Q8: `Address already in use` エラー

**A:** すでにサービスが起動しています。停止してから再起動：

```powershell
# 1. 緊急停止
Ctrl+Shift+P → "Tasks: Run Task" → "🚨 ManaOS: 緊急停止"

# 2. プロセス確認（念のため）
Get-Process python | Where-Object {$_.Path -like "*mana*"}

# 3. 強制終了（必要な場合のみ）
Get-Process python | Where-Object {$_.Path -like "*mana*"} | Stop-Process -Force

# 4. 再起動
Ctrl+Shift+B
```

---

### Q9: VSCodeでタスクが見つからない

**A:** VSCodeがワークスペースルートを正しく認識しているか確認：

```
# 左下のステータスバーを確認
# 表示:「manaos_integrations」であるべき

# 違う場合は、再度開く
File → Open Folder → C:\Users\mana4\Desktop\manaos_integrations
```

---

### Q10: タスクが実行されるが何も起こらない

**A:** ターミナル出力を確認：

```
View → Terminal  # または Ctrl+`
```

エラーメッセージがあれば該当部分を修正。

バックグラウンドタスク（サービス起動）は、別のターミナルで起動します：
- ターミナルタブを切り替えて確認
- 複数の `pwsh` タブがあるはず

---

## VSCode vs Cursor

### Q11: VSCodeとCursorのどちらを使うべきですか？

**A:** 用途による：

| 用途 | 推奨 | 理由 |
|------|------|------|
| **初心者** | VSCode | 安定性、ドキュメント豊富 |
| **AI支援コーディング** | Cursor | AI機能ネイティブ、MCP統合 |
| **デバッグ重視** | VSCode | 軽量、高速 |
| **複数プロジェクト同時** | VSCode | メモリ効率良好 |
| **最新AI機能** | Cursor | GPT-4, Claude統合 |

詳細: [VSCODE_VS_CURSOR.md](VSCODE_VS_CURSOR.md)

---

### Q12: VSCodeとCursorを両方使えますか？

**A:** はい！設定は共有されます：

- **共有**: `.vscode/`フォルダ（タスク、デバッグ、拡張機能推奨）
- **個別**: MCP設定（CursorはMCP native、VSCodeはREST API）

ワークフロー例:
1. **Cursor**: コード生成、リファクタリング（AI支援）
2. **VSCode**: デバッグ、パフォーマンスプロファイリング

---

### Q13: CursorのMCP設定をVSCodeで使えますか？

**A:** いいえ。アプローチが異なります：

**Cursor:**
```json
// mcp.json
{
  "mcpServers": {
    "manaos": {
      "command": "python",
      "args": ["-m", "unified_api_mcp_server"]
    }
  }
}
```

**VSCode:**
```python
# REST API経由でアクセス
import requests
response = requests.get("http://127.0.0.1:9502/api/mcp/tools")
```

詳細: [VSCODE_VS_CURSOR.md#MCP統合](VSCODE_VS_CURSOR.md#mcp統合の違い)

---

## デバッグ

### Q14: デバッグが起動しない

**A:** チェックリスト：

1. **Python拡張機能がインストール済みか**
   ```
   Ctrl+Shift+X → "Python" で検索 → インストール済み確認
   ```

2. **Pythonインタープリターが選択されているか**
   ```
   Ctrl+Shift+P → "Python: Select Interpreter"
   → "../.venv/Scripts/python.exe" を選択
   ```

3. **launch.jsonが存在するか**
   ```
   .vscode/launch.json ファイルを確認
   ```

4. **正しいデバッグ構成を選択しているか**
   ```
   F5 → ドロップダウンから構成選択
   ```

---

### Q15: ブレークポイントで停止しない

**A:** 以下を確認：

1. **ブレークポイントが有効になっているか**
   - 赤丸が表示されているか（行番号左）
   - 灰色の場合は、そのコードパスが実行されていない

2. **デバッグモードで起動しているか**
   - `F5`（デバッグ）を使用
   - `Ctrl+F5`（デバッグなし実行）ではない

3. **該当コードが実行されるか**
   - ログで確認
   - 手前にprintデバッグを追加

---

### Q16: 変数の値が見えない

**A:** デバッグパネルを確認：

```
1. ブレークポイントで停止
2. 左サイドバー → "Run and Debug" アイコン
3. "VARIABLES" セクション展開
   - Locals: ローカル変数
   - Globals: グローバル変数
```

ウォッチ式を追加:
```
"WATCH" セクション → "+" → 式を入力（例: `user.name`）
```

---

### Q17: デバッグが遅い

**A:** 最適化手順：

1. **不要なブレークポイントを削除**
2. **条件付きブレークポイントを使用**
   ```
   右クリック → "Edit Breakpoint" → 条件入力（例: `x > 100`）
   ```
3. **ログポイントを使用（停止せず出力）**
   ```
   右クリック → "Add Logpoint" → メッセージ入力
   ```

---

## パフォーマンス

### Q18: サービスが遅い・重い

**A:** パフォーマンスチェック：

```powershell
# 1. System3自律監視の統計を確認
# 起動ログに表示される

# 2. 個別サービスの応答時間を測定
Measure-Command { Invoke-RestMethod http://127.0.0.1:9502/health }
Measure-Command { Invoke-RestMethod http://127.0.0.1:5105/health }

# 3. メモリ使用量を確認
Get-Process python | Select-Object Name, CPU, WorkingSet64 | Format-Table
```

対策:
- 不要なサービスは停止
- ログレベルを下げる（DEBUG → INFO）
- 定期的にメモリをクリーンアップ

---

### Q19: VSCodeが重い

**A:** 軽量化設定：

```json
// settings.json
{
  "python.analysis.diagnosticMode": "openFilesOnly",
  "python.analysis.indexing": false,
  "files.watcherExclude": {
    "**/__pycache__/**": true,
    "**/node_modules/**": true
  },
  "search.exclude": {
    "**/__pycache__": true,
    "**/.*": true
  }
}
```

拡張機能を減らす:
- 使っていない拡張機能を無効化
- 必須のみインストール

---

### Q20: 起動が遅い

**A:** 起動時間を短縮：

1. **サービスを段階的に起動**
   ```
   # 必要なサービスだけ起動
   python -m unified_api_server  # 統合APIのみ
   ```

2. **System3自律監視を無効化**
   ```python
   # start_vscode_cursor_services.py
   monitor_services(enable_autonomous=False)  # 開発中は無効
   ```

3. **ヘルスチェックのリトライ回数を減らす**
   ```python
   # check_services_health.py
   check_all_services(retry_count=1)  # 3 → 1
   ```

---

## セキュリティ

### Q21: APIキーをどこに保存すべきですか？

**A:** `.env`ファイル（gitignore済み）：

```env
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MANAOS_SECRET_KEY=your-secret-key
```

**絶対にコミットしないこと！**

`.gitignore`に含まれていることを確認：
```
cat .gitignore | findstr ".env"
```

---

### Q22: ポート9502が外部に公開されますか？

**A:** いいえ。デフォルトでローカルのみ（`127.0.0.1`）：

```python
# unified_api_server.py
uvicorn.run(app, host="127.0.0.1", port=9502)
#                      ^^^^^^^^^^^
#                      ローカルのみ
```

外部公開したい場合（VPNなど）:
```python
uvicorn.run(app, host="0.0.0.0", port=9502)  # すべてのNICで待ち受け
```

ただし、認証なしなので**推奨しません**。

---

### Q23: パスワードやトークンがログに出力されます

**A:** ログ設定を修正：

```python
# ログ出力前にサニタイズ
sensitive_fields = ["password", "token", "api_key", "secret"]

def sanitize_log(data):
    for field in sensitive_fields:
        if field in data:
            data[field] = "***REDACTED***"
    return data

logger.info(f"Request: {sanitize_log(request_data)}")
```

---

## その他

### Q24: スニペットが動作しない

**A:** トラブルシューティング：

1. **Python拡張機能が有効か確認**
2. **スニペットファイルが正しい場所にあるか**
   ```
   .vscode/python.code-snippets
   ```
3. **VSCodeを再起動**
   ```
   Ctrl+Shift+P → "Developer: Reload Window"
   ```
4. **手動でスニペット一覧を表示**
   ```
   Ctrl+Space → "manaos" で絞り込み
   ```

詳細: [SNIPPETS_GUIDE.md](SNIPPETS_GUIDE.md#トラブルシューティング)

---

### Q25: 検証スクリプトでエラーが出ます

**A:** PowerShell実行ポリシーを確認：

```powershell
# 現在のポリシー確認
Get-ExecutionPolicy

# RemoteSigned に変更（管理者権限）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

その後、再実行：
```powershell
.\validation_script.ps1
```

---

### Q26: GitHubにプッシュできません

**A:** 認証とリモート設定を確認：

```powershell
# 1. リモートURL確認
git remote -v

# 2. 認証情報を更新
git config --global credential.helper wincred

# 3. プッシュ
git push origin master
```

SSHを使用している場合:
```powershell
# SSH鍵が設定されているか確認
ssh -T git@github.com
```

---

## 📚 関連ドキュメント

- **[VSCODE_SETUP_GUIDE.md](VSCODE_SETUP_GUIDE.md)** - 完全セットアップ
- **[VSCODE_CHECKLIST.md](VSCODE_CHECKLIST.md)** - 対応チェックリスト
- **[STARTUP_GUIDE.md](STARTUP_GUIDE.md)** - サービス起動ガイド
- **[SYSTEM3_GUIDE.md](SYSTEM3_GUIDE.md)** - 自律監視システム
- **[EMERGENCY_STOP_GUIDE.md](EMERGENCY_STOP_GUIDE.md)** - 緊急停止手順

---

## 💡 まだ質問がありますか？

1. **GitHub Issues**: [MRL-mana/manaos-integrations/issues](https://github.com/MRL-mana/manaos-integrations/issues)
2. **ドキュメント検索**: `Ctrl+Shift+F` で全ドキュメントを検索
3. **ログを確認**: `manaos_integrations/logs/` フォルダ

---

**最終更新**: 2026年2月7日  
**対象バージョン**: ManaOS Integrations v1.0+
