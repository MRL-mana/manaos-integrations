# ManaOS サービス起動依存関係ドキュメント

このドキュメントでは、ManaOSサービスの起動順序と依存関係を説明します。

## 目次
1. [起動順序概要](#起動順序概要)
2. [依存関係グラフ](#依存関係グラフ)
3. [サービス詳細](#サービス詳細)
4. [起動プロファイル](#起動プロファイル)
5. [トラブルシューティング](#トラブルシューティング)

---

## 起動順序概要

ManaOSサービスは以下の階層で起動されます:

```
Layer 1 (基盤サービス) → Layer 2 (コアサービス) → Layer 3 (統合サービス) → Layer 4 (UI/オプション)
```

### 起動時間の目安

| レイヤー | 起動時間 | サービス数 |
|---------|---------|-----------|
| Layer 1 | 15-20秒 | 2-3 |
| Layer 2 | 10-15秒 | 4 |
| Layer 3 | 10-20秒 | 1-2 |
| Layer 4 | 5-10秒 | 3-5 |

**合計起動時間: 約40-65秒（フル構成の場合）**

---

## 依存関係グラフ

```
                        ┌─────────────┐
                        │   Ollama    │
                        │ (Port 11434)│
                        └──────┬──────┘
                               │
┌─────────────┐         ┌──────▼──────┐         ┌─────────────┐
│ MRL Memory  │────────▶│ LLM Routing │◀────────│  LM Studio  │
│ (Port 5105) │         │ (Port 5111) │         │ (Port 1234) │
└──────┬──────┘         └──────┬──────┘         └─────────────┘
       │                       │
       │                ┌──────▼──────┐
       │                │   Learning  │
       │                │   System    │
       │                │ (Port 5126) │
       │                └─────────────┘
       │
       ├────────────────┬───────────────┬─────────────┐
       │                │               │             │
┌──────▼──────┐  ┌──────▼──────┐  ┌────▼─────┐  ┌───▼────────┐
│   Unified   │  │   Video     │  │ ComfyUI  │  │  Gallery   │
│     API     │  │  Pipeline   │  │(8188)    │  │    API     │
│ (Port 9502) │  │ (Port 5112) │  └──────────┘  │ (Port 5559)│
└──────┬──────┘  └─────────────┘                └────────────┘
       │
       ├──────────────────┬─────────────┐
       │                  │             │
┌──────▼──────┐    ┌──────▼──────┐  ┌──▼─────────┐
│     UI      │    │  Moltbot    │  │  Pico HID  │
│ Operations  │    │   Gateway   │  │    MCP     │
│ (Port 5110) │    │ (Port 8088) │  │ (Port 5136)│
└─────────────┘    └─────────────┘  └────────────┘
```

---

## サービス詳細

### Layer 1: 基盤サービス（必須）

#### 1. MRL Memory (Port 5105)
- **依存:** なし
- **起動時間:** 3秒
- **説明:** 長期記憶とコンテキスト管理
- **起動コマンド:**
  ```powershell
  cd manaos_integrations
  python -m mrl_memory_integration
  ```

#### 2. Ollama (Port 11434) [外部]
- **依存:** なし
- **起動時間:** 15秒
- **説明:** ローカルLLM実行環境
- **起動コマンド:**
  ```powershell
  ollama serve
  ```

#### 3. LLM Routing (Port 5111)
- **依存:** なし（Ollama/LM Studioはオプション）
- **起動時間:** 5秒
- **説明:** 最適なLLMモデルを自動選択
- **起動コマンド:**
  ```powershell
  cd manaos_integrations
  python -m llm_routing_mcp_server
  ```

### Layer 2: コアサービス

#### 4. Learning System (Port 5126)
- **依存:** MRL Memory
- **起動時間:** 5秒
- **説明:** ユーザー学習パターンと最適化
- **起動コマンド:**
  ```powershell
  cd manaos_integrations
  python -m learning_system_api
  ```

#### 5. Video Pipeline (Port 5112)
- **依存:** なし（ComfyUIはオプション）
- **起動時間:** 3秒
- **説明:** 動画生成・編集パイプライン
- **起動コマンド:**
  ```powershell
  cd manaos_integrations
  python -m video_pipeline_mcp_server
  ```

#### 6. Gallery API (Port 5559)
- **依存:** なし
- **起動時間:** 5秒
- **説明:** 画像管理とギャラリー
- **起動コマンド:**
  ```powershell
  cd manaos_integrations
  python gallery_api_server.py
  ```

#### 7. ComfyUI (Port 8188) [外部]
- **依存:** なし
- **起動時間:** 20秒
- **説明:** 高品質画像生成UI
- **起動コマンド:**
  ```powershell
  # ComfyUIのインストールディレクトリで
  python main.py
  ```

### Layer 3: 統合サービス

#### 8. Unified API (Port 9502)
- **依存:** MRL Memory, LLM Routing
- **オプション依存:** Ollama, Gallery API, ComfyUI
- **起動時間:** 10秒
- **説明:** すべてのサービスを統合するメインAPI
- **起動コマンド:**
  ```powershell
  cd manaos_integrations
  py -3.10 unified_api_server.py
  ```

### Layer 4: UI/オプショナルサービス

#### 9. UI Operations (Port 5110)
- **依存:** Unified API
- **起動時間:** 5秒
- **説明:** UI自動化サービス
- **起動コマンド:**
  ```powershell
  cd manaos_integrations
  python ui_operations_api.py
  ```

#### 10. Pico HID MCP (Port 5136)
- **依存:** なし
- **起動時間:** 3秒
- **説明:** HID操作（マウス・キーボード）
- **起動コマンド:**
  ```powershell
  cd manaos_integrations
  python -m pico_hid_mcp_server
  ```

#### 11. Moltbot Gateway (Port 8088)
- **依存:** Unified API
- **起動時間:** 5秒
- **説明:** Moltbot統合ゲートウェイ
- **起動コマンド:**
  ```powershell
  cd manaos_integrations
  .\start_moltbot.ps1
  ```

---

## 起動プロファイル

### 1. Minimalプロファイル（開発用）

最小限のサービスのみ起動します。

**サービス:**
- MRL Memory
- LLM Routing
- Learning System
- Unified API

**起動時間:** 約20-25秒

**起動コマンド:**
```powershell
.\start_services_master.ps1 -Profile minimal
```

### 2. Standardプロファイル（通常使用）

一般的な使用に必要なサービスを起動します。

**サービス:**
- MRL Memory
- LLM Routing
- Learning System
- Video Pipeline
- Unified API
- Ollama
- Gallery API

**起動時間:** 約40-50秒

**起動コマンド:**
```powershell
.\start_services_master.ps1 -Profile standard
```

### 3. Fullプロファイル（完全版）

すべてのサービスを起動します。

**サービス:**
- 全サービス（11個）

**起動時間:** 約60-75秒

**起動コマンド:**
```powershell
.\start_services_master.ps1 -Profile full
```

### 4. Developmentプロファイル

開発作業に最適化されたプロファイルです。

**サービス:**
- MRL Memory
- LLM Routing
- Learning System
- Unified API
- Gallery API

**起動時間:** 約25-30秒

**起動コマンド:**
```powershell
.\start_services_master.ps1 -Profile development
```

---

## 手動起動フロー

自動起動スクリプトを使わない場合の推奨手順:

### ステップ1: 基盤サービス起動

```powershell
# ターミナル1: MRL Memory
cd C:\Users\mana4\Desktop\manaos_integrations
python -m mrl_memory_integration

# ターミナル2: LLM Routing
cd C:\Users\mana4\Desktop\manaos_integrations
python -m llm_routing_mcp_server

# ターミナル3: Ollama (別ウィンドウ)
ollama serve
```

**待機時間:** サービスが完全に起動するまで10秒待つ

### ステップ2: コアサービス起動

```powershell
# ターミナル4: Learning System
cd C:\Users\mana4\Desktop\manaos_integrations
python -m learning_system_api

# ターミナル5: Video Pipeline
cd C:\Users\mana4\Desktop\manaos_integrations
python -m video_pipeline_mcp_server

# ターミナル6: Gallery API
cd C:\Users\mana4\Desktop\manaos_integrations
python gallery_api_server.py
```

**待機時間:** 5秒

### ステップ3: 統合サービス起動

```powershell
# ターミナル7: Unified API
cd C:\Users\mana4\Desktop\manaos_integrations
py -3.10 unified_api_server.py
```

**待機時間:** 10秒

### ステップ4: オプショナルサービス起動

```powershell
# ターミナル8: UI Operations
cd C:\Users\mana4\Desktop\manaos_integrations
python ui_operations_api.py

# ターミナル9: Pico HID MCP
cd C:\Users\mana4\Desktop\manaos_integrations
python -m pico_hid_mcp_server
```

---

## トラブルシューティング

### 依存サービスが起動していない

**症状:** サービスが起動時にエラーを出す

**解決方法:**
```powershell
# 依存関係をチェック
python manaos_integrations/check_services_health.py

# 不足しているサービスを個別に起動
```

### ポート衝突

**症状:** "Address already in use" エラー

**解決方法:**
```powershell
# ポート使用状況を確認
Get-NetTCPConnection -LocalPort 9502

# プロセスを停止
Stop-Process -Id <PID> -Force

# または自動クリーンアップ
python manaos_integrations/check_and_kill_duplicate_processes.py
```

### 起動タイムアウト

**症状:** サービスが起動しない、または遅い

**解決方法:**
```powershell
# タイムアウトを延長して再試行
.\start_services_master.ps1 -Profile standard -Verbose

# ログを確認
Get-Content manaos_integrations/logs/*.log -Tail 50
```

### サービス間通信失敗

**症状:** Unified APIが他のサービスに接続できない

**解決方法:**
```python
# 設定ローダーでポートを確認
from config_loader import check_port_conflicts

conflicts = check_port_conflicts()
if conflicts:
    print(f"ポート衝突: {conflicts}")
```

---

## ヘルスチェック

### 自動ヘルスチェック

```powershell
# すべてのサービスをチェック
python manaos_integrations/check_services_health.py

# 出力例:
# ✅ MRL Memory: http://127.0.0.1:5105/health - Healthy
# ✅ LLM Routing: http://127.0.0.1:5111/health - Healthy
# ✅ Unified API: http://127.0.0.1:9502/health - Healthy
```

### 手動ヘルスチェック

```powershell
# 個別サービスをチェック
curl http://127.0.0.1:9502/health

# または
Invoke-WebRequest -Uri http://127.0.0.1:9502/health
```

---

## サービス停止

### 正しい停止順序

```powershell
# 1. オプショナルサービスを停止
Stop-Process -Name "ui_operations_api" -Force
Stop-Process -Name "pico_hid_mcp_server" -Force

# 2. Unified APIを停止
Stop-Process -Name "unified_api_server" -Force

# 3. コアサービスを停止
Stop-Process -Name "video_pipeline_mcp_server" -Force
Stop-Process -Name "gallery_api_server" -Force
Stop-Process -Name "learning_system_api" -Force

# 4. 基盤サービスを停止
Stop-Process -Name "llm_routing_mcp_server" -Force
Stop-Process -Name "mrl_memory_integration" -Force
```

### 一括停止

```powershell
# すべてのManaOSサービスを停止
.\stop_all_services.ps1

# または強制停止
python manaos_integrations/emergency_stop.py
```

---

## 推奨リソース割り当て

| サービス | CPU | メモリ | 優先度 |
|---------|-----|--------|-------|
| Ollama | 40% | 4GB | 高 |
| Unified API | 15% | 1GB | 高 |
| ComfyUI | 30% | 6GB | 中 |
| その他 | 15% | 2GB | 低 |

**推奨システムスペック:**
- CPU: 8コア以上
- RAM: 16GB以上（32GB推奨）
- GPU: VRAM 8GB以上（画像生成使用時）

---

## 関連リンク

- [スニペットガイド](./SNIPPETS_GUIDE.md)
- [MCPサーバーガイド](./MCP_SERVERS_GUIDE.md)
- [スキルとMCP統合](./SKILLS_AND_MCP_GUIDE.md)
