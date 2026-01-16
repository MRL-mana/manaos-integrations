# 🚀 OH MY OPENCODE 次のステップ

## ✅ 現在の状態

- ✅ OpenRouter APIキー設定完了
- ✅ 環境変数設定完了
- ✅ .envファイル更新完了
- ✅ 設定ファイル（oh_my_opencode_config.yaml）確認済み
- ✅ 統合APIサーバー統合済み

---

## 🎯 次のステップ

### 1. 統合APIサーバーを起動

**方法A: PowerShellスクリプトを使用（推奨）**

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
.\start_oh_my_opencode_test.ps1
```

**方法B: 手動で起動**

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python unified_api_server.py
```

---

### 2. 動作確認

**方法A: テストスクリプトを使用**

```powershell
# 別のPowerShellウィンドウで実行
cd C:\Users\mana4\Desktop\manaos_integrations
python test_oh_my_opencode_integration.py
```

**方法B: curlで直接テスト**

```powershell
# ヘルスチェック
curl http://localhost:9500/health

# OH MY OPENCODE実行テスト
curl -X POST http://localhost:9500/api/oh_my_opencode/execute `
  -H "Content-Type: application/json" `
  -d '{\"task_description\": \"PythonでHello Worldを出力するコードを生成してください\", \"mode\": \"normal\", \"task_type\": \"code_generation\"}'
```

**方法C: ブラウザで確認**

- ヘルスチェック: http://localhost:9500/health
- 統合状態: http://localhost:9500/api/integrations/status

---

### 3. 実際のタスクを実行

統合APIサーバーが起動したら、以下のようなタスクを実行できます：

#### 例1: 簡単なコード生成

```powershell
curl -X POST http://localhost:9500/api/oh_my_opencode/execute `
  -H "Content-Type: application/json" `
  -d '{
    \"task_description\": \"PythonでFizzBuzzプログラムを作成してください\",
    \"mode\": \"normal\",
    \"task_type\": \"code_generation\"
  }'
```

#### 例2: コードレビュー

```powershell
curl -X POST http://localhost:9500/api/oh_my_opencode/execute `
  -H "Content-Type: application/json" `
  -d '{
    \"task_description\": \"以下のコードをレビューしてください: [コードをここに貼り付け]\",
    \"mode\": \"normal\",
    \"task_type\": \"code_review\"
  }'
```

#### 例3: Trinity統合を使用

```powershell
curl -X POST http://localhost:9500/api/oh_my_opencode/execute `
  -H "Content-Type: application/json" `
  -d '{
    \"task_description\": \"REST APIの設計をしてください\",
    \"mode\": \"normal\",
    \"task_type\": \"architecture_design\",
    \"use_trinity\": true
  }'
```

---

## 📊 利用可能なモードとタスクタイプ

### 実行モード（mode）

- `normal`: 通常モード（コスト最適化）
- `ultra_work`: Ultra Workモード（品質優先、承認が必要）

### タスクタイプ（task_type）

- `specification`: 仕様策定
- `complex_bug`: 難解バグ
- `architecture_design`: 初期アーキ設計
- `code_generation`: コード生成
- `code_review`: コードレビュー
- `refactoring`: リファクタリング
- `general`: 一般タスク

---

## 🔍 トラブルシューティング

### APIキーが認識されない

1. **新しいPowerShellウィンドウを開く**
   - 環境変数の変更を反映するため

2. **環境変数の確認**
   ```powershell
   [System.Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY', 'User')
   ```

3. **.envファイルの確認**
   ```powershell
   Get-Content .env | Select-String "OPENROUTER_API_KEY"
   ```

### 統合APIサーバーが起動しない

1. **ポート9500が使用中か確認**
   ```powershell
   netstat -ano | findstr :9500
   ```

2. **依存関係の確認**
   ```powershell
   pip install flask flask-cors python-dotenv pyyaml httpx
   ```

3. **ログを確認**
   - 統合APIサーバーのコンソール出力を確認

### OH MY OPENCODEが初期化されない

1. **モジュールの確認**
   ```powershell
   python -c "from oh_my_opencode_integration import OHMyOpenCodeIntegration; print('OK')"
   ```

2. **設定ファイルの確認**
   - `oh_my_opencode_config.yaml`が正しく設定されているか確認

3. **APIキーの確認**
   - OpenRouter APIキーが正しく設定されているか確認

---

## 📝 参考ドキュメント

- **クイックスタート**: `OH_MY_OPENCODE_QUICK_START.md`
- **プロバイダ設定**: `OH_MY_OPENCODE_PROVIDER_SETUP.md`
- **APIキー設定**: `OH_MY_OPENCODE_API_KEY_SETUP_CORRECTED.md`
- **統合状況**: `OH_MY_OPENCODE_INTEGRATION_STATUS.md`

---

## 🎉 準備完了！

すべての設定が完了しました。統合APIサーバーを起動して、OH MY OPENCODEの動作を確認してください！

**最終更新:** 2024年12月
