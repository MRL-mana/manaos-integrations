# 🔑 OH MY OPENCODE APIキー設定手順

## 📋 概要

OH MY OPENCODEのAPIキーを設定して、ManaOS統合システムで使用できるようにします。

---

## 🚀 設定方法

### 方法1: PowerShellスクリプトを使用（推奨）

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\set_oh_my_opencode_api_key.ps1 -ApiKey "your_api_key_here"
```

### 方法2: 環境変数を直接設定

#### PowerShellの場合

```powershell
# 現在のセッションのみ
$env:OH_MY_OPENCODE_API_KEY = "your_api_key_here"

# 永続的に設定（ユーザー環境変数）
[System.Environment]::SetEnvironmentVariable("OH_MY_OPENCODE_API_KEY", "your_api_key_here", "User")
```

#### コマンドプロンプトの場合

```cmd
setx OH_MY_OPENCODE_API_KEY "your_api_key_here"
```

### 方法3: .envファイルに追加

プロジェクトルートに `.env` ファイルを作成（または既存のファイルに追加）：

```
OH_MY_OPENCODE_API_KEY=your_api_key_here
```

**注意:** `.env`ファイルは`.gitignore`に追加することを推奨します。

---

## 🔍 APIキーの取得方法

OH MY OPENCODEのAPIキーは、以下の方法で取得できます：

1. **OH MY OPENCODEの公式サイトにアクセス**
   - https://ohmyopencode.com （実際のURLに置き換えてください）

2. **アカウントにログイン**

3. **APIキーを生成**
   - Settings → API Keys → Create API Key
   - APIキー名を入力（例: `ManaOS Integration`）
   - 生成されたAPIキーをコピー

**重要:** APIキーは一度しか表示されないため、必ずコピーして安全な場所に保存してください。

---

## ✅ 設定確認

### 環境変数の確認

```powershell
# PowerShell
$env:OH_MY_OPENCODE_API_KEY

# コマンドプロンプト
echo %OH_MY_OPENCODE_API_KEY%
```

### 統合システムでの確認

```python
import os
api_key = os.getenv("OH_MY_OPENCODE_API_KEY")
if api_key:
    print(f"✅ APIキーが設定されています: {api_key[:10]}...")
else:
    print("❌ APIキーが設定されていません")
```

### APIサーバー起動時の確認

```bash
python unified_api_server.py
```

起動ログに以下が表示されればOK：
```
✅ OH MY OPENCODE統合モジュールを読み込みました
✅ OH MY OPENCODEを初期化しました
```

---

## 🧪 動作確認

### 1. ヘルスチェック

```bash
curl http://127.0.0.1:9502/health
```

### 2. OH MY OPENCODE実行テスト

```bash
curl -X POST http://127.0.0.1:9502/api/oh_my_opencode/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "PythonでHello Worldを出力するコードを生成してください",
    "mode": "normal",
    "task_type": "code_generation"
  }'
```

### 3. Pythonスクリプトでテスト

```python
from oh_my_opencode_integration import OHMyOpenCodeIntegration
import asyncio

async def test():
    integration = OHMyOpenCodeIntegration()
    if integration.initialize():
        print("✅ 初期化成功")
    else:
        print("❌ 初期化失敗（APIキーを確認してください）")

asyncio.run(test())
```

---

## ⚠️ トラブルシューティング

### APIキーが認識されない

1. **新しいPowerShell/コマンドプロンプトウィンドウを開く**
   - 環境変数の変更を反映するため

2. **環境変数の確認**
   ```powershell
   $env:OH_MY_OPENCODE_API_KEY
   ```

3. **統合APIサーバーを再起動**
   ```bash
   python unified_api_server.py
   ```

### エラー: "OH MY OPENCODE APIキーが設定されていません"

- 環境変数が正しく設定されているか確認
- `.env`ファイルが正しい場所にあるか確認
- 統合APIサーバーを再起動

### エラー: "OH MY OPENCODE統合が利用できません"

- `oh_my_opencode_integration.py`が正しくインポートできるか確認
- 必要な依存パッケージがインストールされているか確認
  ```bash
  pip install httpx pyyaml python-dotenv
  ```

---

## 🔒 セキュリティ注意事項

1. **APIキーをGitにコミットしない**
   - `.env`ファイルは`.gitignore`に追加
   - 環境変数を使用することを推奨

2. **APIキーを他人と共有しない**
   - 各ユーザーが個別にAPIキーを取得・設定

3. **定期的にAPIキーをローテーション**
   - セキュリティのベストプラクティス

---

## 📝 次のステップ

APIキーを設定したら：

1. ✅ **統合APIサーバーを起動**
   ```bash
   python unified_api_server.py
   ```

2. ✅ **動作確認**
   - 上記の「動作確認」セクションを参照

3. ✅ **実際の案件で使用開始**
   - `OH_MY_OPENCODE_PACKAGE_MENU.md`を参照

---

**最終更新:** 2024年12月

