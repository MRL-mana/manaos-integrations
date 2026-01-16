# サービス起動・修復完了レポート

**作成日**: 2026-01-07

## 📊 修復内容

### 停止していたサービス

1. **n8n** (ポート5679) - ❌ inactive → ✅ active
2. **sd-webui (ComfyUI)** (ポート8188) - ❌ inactive → ✅ active  
3. **mana-intent (Intent Router)** (ポート5100) - ❌ inactive → ✅ active

## ✅ 実施した修復作業

### 1. サービス起動

以下のコマンドで各サービスを起動しました：

```powershell
# n8n起動
.\start_n8n_local.ps1

# ComfyUI起動
.\start_comfyui_local.ps1

# Intent Router起動
python intent_router.py
```

### 2. 起動確認

ポート確認結果：
- ✅ ポート5679: n8n起動中
- ✅ ポート8188: ComfyUI起動中
- ✅ ポート5100: Intent Router起動中

### 3. 常時起動設定

自動起動設定スクリプトを作成しました：
- `setup_always_running_services.ps1`

**設定内容:**
- システム起動時に自動起動
- 失敗時は最大10回再試行（1分間隔）
- バッテリー時も起動継続
- 実行時間制限なし（常時起動）

## 🔧 自動起動設定方法

### 管理者権限で実行

```powershell
# PowerShellを管理者として実行
cd C:\Users\mana4\Desktop\manaos_integrations
.\setup_always_running_services.ps1
```

### 設定されるタスク

1. **ManaOS_n8n_AlwaysRunning** - n8n自動起動
2. **ManaOS_ComfyUI_AlwaysRunning** - ComfyUI自動起動
3. **ManaOS_IntentRouter_AlwaysRunning** - Intent Router自動起動

### 確認方法

```powershell
# 設定されたタスクを確認
Get-ScheduledTask -TaskName "ManaOS_*AlwaysRunning"

# 手動で起動（テスト用）
Start-ScheduledTask -TaskName ManaOS_n8n_AlwaysRunning
Start-ScheduledTask -TaskName ManaOS_ComfyUI_AlwaysRunning
Start-ScheduledTask -TaskName ManaOS_IntentRouter_AlwaysRunning
```

## 📝 注意事項

1. **管理者権限が必要**: 自動起動設定には管理者権限が必要です
2. **ポート競合**: 既に起動しているサービスがある場合、ポート競合が発生する可能性があります
3. **リソース使用**: ComfyUIはGPUリソースを大量に使用するため、必要時のみ起動することを推奨します

## 🎯 次のステップ

1. PCを再起動して、自動起動が正常に動作するか確認
2. 各サービスのログを確認して、エラーがないかチェック
3. 必要に応じて、自動起動設定を調整

## 📚 関連ファイル

- `start_n8n_local.ps1` - n8n起動スクリプト
- `start_comfyui_local.ps1` - ComfyUI起動スクリプト
- `intent_router.py` - Intent Routerサービス
- `setup_always_running_services.ps1` - 自動起動設定スクリプト








