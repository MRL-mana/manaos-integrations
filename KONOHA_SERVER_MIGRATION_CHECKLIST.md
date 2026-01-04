# このはサーバー移行チェックリスト

**作成日**: 2025-01-28  
**目的**: このはサーバーからローカル環境への移行時に必要な再設定項目の確認

---

## 📊 移行状況サマリー

- **移行元**: このはサーバー（100.93.120.33）
- **移行先**: ローカル環境（Windows PC）
- **再設定が必要な項目**: 多数

---

## ⚠️ 必須再設定項目

### 1. n8n統合

#### このはサーバーのn8n
- **URL**: `http://100.93.120.33:5678`
- **状態**: リモートサーバーで稼働中
- **APIキー**: このはサーバー用のAPIキーが必要

#### ローカルのn8n（新規設定が必要）
- **URL**: `http://localhost:5678` または `http://localhost:5679`
- **状態**: ローカルで起動する場合は新規インストール・設定が必要
- **APIキー**: ローカルで新規作成が必要

**設定手順**:
1. ローカルでn8nを起動
2. Web UIからAPIキーを作成
3. MCP設定ファイル（`~/.cursor/mcp.json`）を更新
4. Cursorを再起動

**参考ファイル**:
- `N8N_LOCAL_SETUP.md`
- `n8n_mcp_server/APIキー設定手順.md`
- `n8n_mcp_server/CURSOR_MCP_SETUP.md`

---

### 2. 環境変数（.envファイル）

#### このはサーバーで設定されていた可能性のある環境変数

**必須項目**:
- `GITHUB_TOKEN` - ✅ 設定済み
- `CIVITAI_API_KEY` - ⚠️ 未設定（このはサーバーから取得が必要）
- `OPENAI_API_KEY` - ⚠️ 未設定（Mem0統合用）
- `SLACK_WEBHOOK_URL` - ⚠️ 未設定
- `SLACK_VERIFICATION_TOKEN` - ⚠️ 未設定
- `ROWS_API_KEY` - ⚠️ 未設定

**設定済み項目**:
- `GOOGLE_DRIVE_CREDENTIALS` - ✅ 設定済み
- `GOOGLE_DRIVE_TOKEN` - ✅ 設定済み
- `OBSIDIAN_VAULT_PATH` - ✅ 設定済み
- `OLLAMA_URL` - ✅ 設定済み
- `OLLAMA_MODEL` - ✅ 設定済み

**確認方法**:
```powershell
# このはサーバーで環境変数を確認
ssh konoha
cat /root/.env
# または
env | grep -E "(API|TOKEN|KEY|SECRET)"
```

---

### 3. 設定ファイルのパス更新

#### OneDriveからDesktopへの移行

**更新が必要なファイル**:
- ✅ `manaos_unified_mcp_server/add_to_cursor_mcp.ps1` - 完了
- ✅ `svi_mcp_server/add_to_cursor_mcp.ps1` - 完了
- ✅ `n8n_mcp_server/add_to_cursor_mcp.ps1` - 完了
- ✅ `import_n8n_via_ssh.ps1` - 完了
- ✅ `n8n_mcp_server/verify_connection.ps1` - 完了

**参考**: `SETTINGS_MIGRATION_SUMMARY.md`

---

### 4. Cursor MCP設定

#### MCP設定ファイルの更新

**ファイルパス**: `%USERPROFILE%\.cursor\mcp.json`

**更新が必要な項目**:
- n8n MCPサーバーのパス（OneDrive → Desktop）
- n8n APIキー（このはサーバー用 → ローカル用）
- n8n URL（`http://100.93.120.33:5678` → `http://localhost:5678`）

**更新方法**:
```powershell
# 自動更新スクリプトを実行
cd C:\Users\mana4\Desktop\manaos_integrations
.\update_mcp_settings.ps1
```

---

### 5. このはサーバー固有の設定

#### SSH接続設定

**このはサーバーへの接続**:
- **IP**: 100.93.120.33
- **状態**: Tailscale経由で接続可能
- **用途**: n8n、その他のサービスへのアクセス

**確認が必要な項目**:
- SSH鍵の設定
- Tailscale接続の確認
- このはサーバー上のサービスの状態確認

---

### 6. データベースファイル

#### 移行済みデータベース

**このはサーバーから移行済み**:
- ✅ `auth.db` - 認証情報
- ✅ `content_generation.db` - コンテンツ生成履歴
- ✅ `cost_tracking.db` - コスト追跡
- ✅ `metrics.db` - メトリクス
- ✅ `rag_memory.db` - RAGメモリ
- ✅ `revenue_tracker.db` - 収益追跡
- ✅ `secretary_system.db` - 秘書システム
- ✅ `task_queue.db` - タスクキュー

**状態**: データベースファイルは移行済み、設定は引き継がれます

---

### 7. 認証情報ファイル

#### Google Drive認証

**移行済み**:
- ✅ `credentials.json` - Google Drive認証情報
- ✅ `token.json` - 認証トークン

**状態**: ファイルは存在し、動作確認済み

---

## 🔧 再設定手順

### ステップ1: このはサーバーから情報を取得

```bash
# SSHでこのはサーバーに接続
ssh konoha

# 環境変数を確認
cat /root/.env
env | grep -E "(API|TOKEN|KEY|SECRET)"

# n8nの設定を確認
docker exec trinity-n8n env | grep -i api

# 設定ファイルを確認
ls -la /root/manaos_integrations/
```

### ステップ2: ローカル環境に設定を反映

#### .envファイルの更新

```powershell
# .envファイルを編集
notepad C:\Users\mana4\Desktop\manaos_integrations\.env
```

このはサーバーから取得した環境変数を追加：

```env
# このはサーバーから取得した設定
CIVITAI_API_KEY=このはサーバーから取得
OPENAI_API_KEY=このはサーバーから取得
SLACK_WEBHOOK_URL=このはサーバーから取得
SLACK_VERIFICATION_TOKEN=このはサーバーから取得
ROWS_API_KEY=このはサーバーから取得
```

#### n8n APIキーの設定

**ローカルでn8nを使用する場合**:
1. ローカルでn8nを起動
2. Web UIからAPIキーを作成
3. MCP設定ファイルを更新

**このはサーバーのn8nを継続使用する場合**:
- MCP設定ファイルの`N8N_BASE_URL`を`http://100.93.120.33:5678`のまま維持
- このはサーバーのn8nからAPIキーを取得して設定

### ステップ3: 動作確認

```powershell
# 未設定項目を確認
python check_unconfigured.py

# 統合システムの動作確認
python -c "from manaos_complete_integration import ManaOSCompleteIntegration; integration = ManaOSCompleteIntegration(); status = integration.get_complete_status(); print(status)"
```

---

## 📋 優先度別チェックリスト

### 🔴 高優先度（すぐに設定が必要）

- [ ] **n8n APIキー**: ローカルでn8nを使用する場合は新規作成
- [ ] **CivitAI APIキー**: このはサーバーから取得して設定
- [ ] **OpenAI APIキー**: Mem0統合を使用する場合に必要
- [ ] **Cursor MCP設定**: パスとAPIキーを更新

### 🟡 中優先度（必要に応じて設定）

- [ ] **Slack統合**: Webhook URLとVerification Token
- [ ] **Rows統合**: APIキー
- [ ] **決済統合**: Stripe/PayPalの設定

### 🟢 低優先度（オプション）

- [ ] **その他の統合**: 必要に応じて設定

---

## 🔍 このはサーバーからの情報取得方法

### 方法1: SSH経由で直接確認

```bash
# このはサーバーにSSH接続
ssh konoha

# 環境変数を確認
cat /root/.env
cat /root/.bashrc | grep export

# n8nの設定を確認
docker exec trinity-n8n env | grep -i api

# 設定ファイルを確認
ls -la /root/manaos_integrations/
cat /root/manaos_integrations/.env
```

### 方法2: 設定ファイルをコピー

```bash
# このはサーバーから.envファイルをコピー
scp konoha:/root/.env C:\Users\mana4\Desktop\manaos_integrations\.env.konoha

# 設定ファイルをコピー
scp -r konoha:/root/manaos_integrations/configs C:\Users\mana4\Desktop\manaos_integrations\
```

---

## 📝 注意事項

1. **APIキーとトークン**: このはサーバーから取得したAPIキーは、ローカル環境でも使用できる場合とできない場合があります
2. **n8n APIキー**: このはサーバーのn8nとローカルのn8nは別インスタンスのため、それぞれでAPIキーを作成する必要があります
3. **パス**: OneDriveからDesktopへの移行により、一部のパスが変更されています
4. **環境変数**: システム環境変数に設定されている場合は、手動で更新が必要です

---

## 🎯 次のステップ

1. **このはサーバーにSSH接続して設定を確認**
2. **必要な環境変数を取得**
3. **.envファイルに追加**
4. **n8n APIキーを設定**
5. **動作確認**

---

## 📚 参考資料

- `SETTINGS_MIGRATION_SUMMARY.md` - 設定移行のまとめ
- `UNCONFIGURED_SUMMARY.md` - 未設定項目の一覧
- `N8N_LOCAL_SETUP.md` - ローカルn8nのセットアップ
- `n8n_mcp_server/APIキー設定手順.md` - n8n APIキーの設定手順

