# 📊 LLMルーティングシステム 現在の状態と起動方法

**確認日時**: 2025-01-28

---

## 🔍 現在の状態

### ❌ 起動していないサービス

1. **LM Studioサーバー**
   - 状態: 停止中
   - URL: `http://localhost:1234/v1`
   - 起動方法: LM Studio → Serverタブ → Start Server

2. **拡張LLMルーティングAPI**
   - 状態: 停止中
   - URL: `http://localhost:9501/api/llm/health`
   - 起動方法: `.\start_llm_routing_api.ps1`

3. **統合APIサーバー**
   - 状態: プロセスは存在するが、APIに接続不可
   - URL: `http://localhost:9500/health`
   - プロセス数: 2つ（重複起動の可能性）

### ✅ 設定済み

- 設定ファイル: `cursor_llm_routing_config.json` ✅
- Pythonモジュール: flask, flask-cors, requests ✅
- 実装ファイル: すべて存在 ✅

### ⚠️ 常時起動未設定

- タスクスケジューラ: 未登録
- PC再起動後は手動起動が必要

---

## 🚀 起動方法

### 方法1: 手動起動（今すぐ使う）

#### ステップ1: LM Studioを起動

1. LM Studioを起動
2. 「Server」タブでモデルを選択
3. 「Start Server」をクリック
4. エンドポイント確認: `http://localhost:1234/v1`

#### ステップ2: LLMルーティングAPIを起動

```powershell
.\start_llm_routing_api.ps1
```

#### ステップ3: 統合APIサーバーを起動（必要に応じて）

```powershell
python unified_api_server.py
```

#### ステップ4: 状態確認

```powershell
.\check_running_status.ps1
```

---

### 方法2: 常時起動設定（推奨）

#### ステップ1: 常時起動設定を実行

**管理者権限でPowerShellを開いて実行**:

```powershell
.\setup_llm_routing_autostart.ps1
```

このスクリプトが以下を設定：
- LLMルーティングAPIの常時起動タスク
- 統合APIサーバーの常時起動タスク（オプション）

#### ステップ2: 設定確認

```powershell
Get-ScheduledTask -TaskName "*manaOS*"
```

#### ステップ3: 即座に起動（オプション）

```powershell
Start-ScheduledTask -TaskName "manaOS-LLM-Routing-API"
Start-ScheduledTask -TaskName "manaOS-Unified-API-Server"
```

---

## 📋 常時起動設定後の動作

### PC再起動時

1. **ログオン時**: 自動的にサービスが起動
2. **失敗時**: 最大3回再試行（1分間隔）
3. **確認**: `.\check_running_status.ps1` で状態確認

### 手動操作

```powershell
# 起動
Start-ScheduledTask -TaskName "manaOS-LLM-Routing-API"

# 停止
Stop-ScheduledTask -TaskName "manaOS-LLM-Routing-API"

# 状態確認
Get-ScheduledTask -TaskName "manaOS-LLM-Routing-API"
```

---

## 🔧 トラブルシューティング

### 統合APIサーバーが応答しない

**問題**: プロセスは存在するが、APIに接続できない

**解決方法**:

1. **重複プロセスを停止**
   ```powershell
   Get-Process -Name python | Where-Object {
       $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine
       $cmdLine -like "*unified_api_server*"
   } | Stop-Process -Force
   ```

2. **再起動**
   ```powershell
   python unified_api_server.py
   ```

### LM Studioが起動しない

**問題**: LM Studioサーバーに接続できない

**解決方法**:

1. LM Studioを起動
2. 「Server」タブで「Start Server」をクリック
3. エンドポイント確認: `http://localhost:1234/v1`

### ポートが使用中

**問題**: ポート9500または9501が使用中

**解決方法**:

```powershell
# ポート使用状況を確認
netstat -ano | findstr ":9500"
netstat -ano | findstr ":9501"

# プロセスを停止
Stop-Process -Id <PID> -Force
```

---

## 📝 次のステップ

### 今すぐ使う場合

1. ✅ LM Studioを起動
2. ✅ LLMルーティングAPIを起動: `.\start_llm_routing_api.ps1`
3. ✅ 状態確認: `.\check_running_status.ps1`

### 常時起動を設定する場合

1. ✅ 管理者権限でPowerShellを開く
2. ✅ 常時起動設定を実行: `.\setup_llm_routing_autostart.ps1`
3. ✅ PC再起動後、自動的に起動することを確認

---

## 🔗 関連ドキュメント

- `README_CURSOR_LOCAL_LLM.md` - メインREADME
- `QUICK_START_GUIDE.md` - クイックスタートガイド
- `CURSOR_LOCAL_LLM_SETUP.md` - 詳細な接続設定手順

---

**現在の状態: 一部のサービスが起動していません。上記の手順で起動してください。**



















