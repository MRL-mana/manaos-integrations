# 他のサービス・システム 本番運用状態

**確認日時**: 2025-01-28  
**最終更新**: 2025-01-28（統合・本番運用設定完了）

---

## ✅ 本番運用中

### 1. ManaOS統合サービス（23サービス）
- **状態**: ✅ 全23サービス正常動作（100%）
- **自動起動**: ✅ Windows Task Scheduler設定済み
- **監視**: ✅ Service Monitor（ポート5111）起動中
- **統合**: ✅ start_all_services.ps1に統合済み
- **含まれるサービス**: Core 11 + Phase 1 2 + Phase 2 3 + Phase 3 3 + SSOT 2 + Unified API 1 + Service Monitor 1

### 2. Unified API Server（統合APIサーバー）
- **ポート**: 9500
- **状態**: ✅ 統合済み・起動可能
- **自動起動**: ✅ start_all_services.ps1に統合済み
- **用途**: 外部システム統合API（ComfyUI、Google Drive、CivitAI等）
- **ファイル**: `manaos_integrations/unified_api_server.py`
- **統合日**: 2025-01-28

### 3. n8n（ワークフローエンジン）
- **ポート**: 5678
- **状態**: ✅ 動作中
- **自動起動**: ✅ Windows Task Scheduler設定済み（ManaOS_n8n）
- **用途**: ワークフロー自動化
- **設定スクリプト**: `setup_external_services_autostart.ps1`

### 4. Ollama（ローカルLLM）
- **ポート**: 11434
- **状態**: ✅ 動作中
- **自動起動**: ✅ Windows Task Scheduler設定済み（ManaOS_Ollama）
- **常時起動**: ✅ 設定済み（システム起動時自動起動、停止時自動再起動最大10回、バッテリー時も継続）
- **用途**: LLM推論エンジン（Intent Router、Task Planner、Task Critic、RAG Memory、LLM最適化、Content Generationで使用）
- **設定スクリプト**: `setup_external_services_autostart.ps1`
- **起動確認スクリプト**: `ensure_ollama_running.ps1`

---

## ⚠️ 本番運用未設定（必要時に手動起動）

### 5. ComfyUI（画像生成）
- **ポート**: 8188
- **状態**: ⚠️ 未起動
- **自動起動**: ❌ 未設定（必要時に起動）
- **用途**: Stable Diffusion画像生成
- **起動スクリプト**: `start_comfyui_local.ps1`
- **備考**: GPUリソースを大量に使用するため、必要時に手動起動

### 6. Mana Screen Sharing（画面共有）
- **ポート**: 5008
- **状態**: ⚠️ 未起動
- **自動起動**: ❌ 未設定（必要時に起動）
- **用途**: ブラウザベース画面共有・リモート操作
- **備考**: 必要時に手動起動する想定（サーバー側に配置されている可能性）

---

## 📋 統合・本番運用設定完了

### ✅ 完了した設定（2025-01-28）

1. **Unified API Server**
   - ✅ start_all_services.ps1に統合済み
   - ✅ 自動起動設定済み（ManaOS統合サービス経由）

2. **n8n / Ollama**
   - ✅ 自動起動設定スクリプト作成済み
   - ✅ Windows Task Scheduler設定済み
   - **設定方法**: `.\setup_external_services_autostart.ps1`（管理者権限で実行）

### ⚠️ 手動起動（必要時のみ）

3. **ComfyUI**
   - 必要時に `.\start_comfyui_local.ps1` で起動
   - GPUリソースを大量に使用するため、自動起動は推奨しない

4. **Mana Screen Sharing**
   - 必要時に手動起動（サーバー側に配置されている可能性）

---

## 🔧 自動起動設定方法

### 初回設定（管理者権限で実行）

```powershell
# PowerShellを管理者として実行
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations

# ManaOS全サービス（Unified API Server含む）の自動起動設定
.\setup_autostart.ps1

# n8n / Ollamaの自動起動設定
.\setup_external_services_autostart.ps1
```

### 設定確認

```powershell
# ManaOS全サービスの自動起動確認
Get-ScheduledTask -TaskName "ManaOS_*" | Format-Table TaskName, State

# n8n / Ollamaの自動起動確認
Get-ScheduledTask -TaskName "ManaOS_n8n", "ManaOS_Ollama" | Format-Table TaskName, State
```

### 手動起動（必要時）

```powershell
# ComfyUI起動（必要時）
.\start_comfyui_local.ps1

# 全サービス起動（Unified API Server含む）
.\start_all_services.ps1
```

---

## 📊 まとめ

**本番運用中**: 5システム（ManaOS 23サービス、Unified API Server、n8n、Ollama、Service Monitor）  
**手動起動（必要時）**: 2システム（ComfyUI、Mana Screen Sharing）

**統合状況**:
- ✅ Unified API Server: start_all_services.ps1に統合済み
- ✅ Service Monitor: start_all_services.ps1に統合済み（2025-01-28追加）
- ✅ n8n: 自動起動設定済み（ManaOS_n8n）
- ✅ Ollama: 自動起動設定済み（ManaOS_Ollama、常時起動設定済み）
- ⚠️ ComfyUI: 必要時に手動起動（GPUリソース使用のため）
- ⚠️ Mana Screen Sharing: 必要時に手動起動

**設定完了**: 2025-01-28  
**最終更新**: 2025-01-28（Service Monitor追加）

