# ManaOS 分散デプロイメントガイド

このガイドでは、ManaOSサービスを複数のデバイス間で分散させて実行する方法を説明します。

## 目次

1. [概要](#概要)
2. [アーキテクチャ例](#アーキテクチャ例)
3. [Tailscaleセットアップ](#tailscaleセットアップ)
4. [サービス配置戦略](#サービス配置戦略)
5. [設定例](#設定例)
6. [パフォーマンス最適化](#パフォーマンス最適化)
7. [トラブルシューティング](#トラブルシューティング)

---

## 概要

### 分散デプロイメントの利点

- **リソース分散**: GPU、CPU、メモリを複数マシンで効率的に活用
- **可用性向上**: 一部サービスが停止しても他のサービスは動作継続
- **スケーラビリティ**: 負荷に応じてサービスを追加可能
- **柔軟性**: デバイスの特性に応じた最適配置

### 前提条件

- 複数のデバイス（PC、サーバー、ラップトップなど）
- Tailscale（または他のVPN/ネットワーク）による接続
- 各デバイスでのPython 3.10+環境
- 基本的なネットワーク知識

---

## アーキテクチャ例

### シナリオ1: デュアルPC構成（X280 + Konoha）

#### X280 (メインPC/高性能GPU搭載)
**役割**: 画像/動画生成、LLM推論、メインデータストレージ

- ComfyUI (GPU利用)
- Ollama (LLM推論)
- LM Studio (代替LLM)
- MRL Memory Service
- Learning System
- Gallery API
- ファイルストレージ

#### Konoha (サブPC/軽量タスク)
**役割**: 補完サービス、モニタリング、軽量処理

- n8n (ワークフロー自動化)
- SearXNG (検索エンジン)
- Whisper (音声認識)
- VoiceVox (音声合成)
- TTS Services
- Remi (リモートUI)
- Evaluation UI
- バックアップタスク

### シナリオ2: 3デバイス構成（PC + ラップトップ + クラウドVM）

#### デバイスA (デスクトップPC - GPU)
- ComfyUI
- Ollama
- Stable Diffusion WebUI

#### デバイスB (ラップトップ - モバイル)
- MRL Memory (ローカルキャッシュ)
- Learning System Proxy
- クライアントアプリケーション

#### デバイスC (クラウドVM - バックエンド)
- n8n
- SearXNG
- データベース
- 永続ストレージ

---

## Tailscaleセットアップ

### 1. Tailscaleのインストール

**Windows:**
```powershell
# 公式サイトからダウンロードしてインストール
# https://tailscale.com/download/windows

# またはwingetで
winget install tailscale.tailscale
```

**Linux:**
```bash
# Ubuntu/Debian
curl -fsSL https://tailscale.com/install.sh | sh

# インストール後
sudo tailscale up
```

**macOS:**
```bash
# Homebrewで
brew install tailscale

# 起動
sudo tailscale up
```

### 2. デバイスの確認

```powershell
# Tailscale接続状態
tailscale status

# 出力例:
# 100.101.102.103  x280            user@   windows -
# 100.101.102.104  konoha          user@   windows -
```

### 3. IPアドレスの記録

各デバイスのTailscale IPアドレスをメモ:

```
X280:    100.101.102.103
Konoha:  100.101.102.104
```

### 4. 接続テスト

```powershell
# X280からKonohaへping
ping 100.101.102.104

# ポート疎通確認
Test-NetConnection -ComputerName 100.101.102.104 -Port 5678  # n8nポート
```

---

## サービス配置戦略

### GPU依存サービス（高性能PCに配置）

- **ComfyUI**: 画像生成（VRAM 8GB+推奨）
- **Ollama**: LLM推論（VRAM 6GB+推奨）
- **Stable Diffusion WebUI**: 画像生成

**設定例（X280で実行）:**
```powershell
# すべてのインターフェースでリッスン
$env:OLLAMA_HOST = "0.0.0.0:11434"
ollama serve

# ComfyUI
cd C:\AI_Tools\ComfyUI
python main.py --listen 0.0.0.0 --port 8188
```

### CPU軽量サービス（サブPCに配置）

- **n8n**: ワークフロー自動化
- **SearXNG**: 検索エンジン
- **Whisper API**: 音声認識
- **VoiceVox**: 音声合成

**設定例（Konohaで実行）:**
```powershell
# n8n
$env:N8N_HOST = "0.0.0.0"
$env:N8N_PORT = "5678"
n8n start

# SearXNG (Dockerで)
docker run -d -p 8080:8080 searxng/searxng
```

### データストレージサービス（SSD/高速ストレージ搭載PCに配置）

- **MRL Memory Service**: メモリデータベース
- **Learning System**: 学習データ
- **Gallery API**: 画像ギャラリー

---

## 設定例

### パターンA: X280でサービス実行、Konohaから利用

#### X280での設定（サービス起動側）

```powershell
# PowerShellプロファイルに追加
notepad $PROFILE
```

```powershell
# X280 - サービス起動設定
# すべてのインターフェースでリッスン

# Ollama
$env:OLLAMA_HOST = "0.0.0.0:11434"

# ファイアウォール設定（初回のみ）
New-NetFirewallRule -DisplayName "ManaOS Services" `
    -Direction Inbound -Protocol TCP `
    -LocalPort 5105,5106,5107,8188,11434 `
    -Action Allow -RemoteAddress 100.0.0.0/8

# サービス起動
cd C:\Users\mana4\Desktop\manaos_integrations
python start_vscode_cursor_services.py
```

#### Konohaでの設定（クライアント側）

```powershell
# PowerShellプロファイルに追加
notepad $PROFILE
```

```powershell
# Konoha - X280のサービスに接続
$X280_IP = "100.101.102.103"

$env:OLLAMA_URL = "http://${X280_IP}:11434"
$env:COMFYUI_URL = "http://${X280_IP}:8188"
$env:MRL_MEMORY_URL = "http://${X280_IP}:5105"
$env:LEARNING_SYSTEM_URL = "http://${X280_IP}:5106"
$env:LLM_ROUTING_URL = "http://${X280_IP}:5107"
$env:GALLERY_API_URL = "http://${X280_IP}:5120"
$env:LM_STUDIO_URL = "http://${X280_IP}:1234"

# Konoha独自のサービス（ローカル起動）
# 環境変数を設定しない = デフォルトのlocalhostを使用
# - n8n
# - SearXNG
# - Whisper
# - VoiceVox
```

### パターンB: 双方向設定（相互に利用）

#### X280の設定

```powershell
# X280 - PowerShellプロファイル
$KONOHA_IP = "100.101.102.104"

# X280で起動するサービス（環境変数なし = localhost）
# - Ollama
# - ComfyUI
# - MRL Memory
# - Learning System
# - Gallery API

# KonohaのサービスをX280から利用
$env:N8N_URL = "http://${KONOHA_IP}:5678"
$env:SEARXNG_URL = "http://${KONOHA_IP}:8080"
$env:WHISPER_URL = "http://${KONOHA_IP}:9000"
$env:VOICEVOX_URL = "http://${KONOHA_IP}:50021"
```

#### Konohaの設定

```powershell
# Konoha - PowerShellプロファイル
$X280_IP = "100.101.102.103"

# Konohaで起動するサービス（環境変数なし = localhost）
# - n8n
# - SearXNG
# - Whisper
# - VoiceVox

# X280のサービスをKonohaから利用
$env:OLLAMA_URL = "http://${X280_IP}:11434"
$env:COMFYUI_URL = "http://${X280_IP}:8188"
$env:MRL_MEMORY_URL = "http://${X280_IP}:5105"
$env:LEARNING_SYSTEM_URL = "http://${X280_IP}:5106"
$env:GALLERY_API_URL = "http://${X280_IP}:5120"
```

### パターンC: 環境別設定ファイル

#### 設定ファイルの作成

**X280用設定: `config_x280.ps1`**
```powershell
# X280 設定
$env:DEVICE_NAME = "X280"

# ローカルサービス（このマシンで起動）
# - 環境変数は設定しない（デフォルト = localhost）

# リモートサービス（Konohaから利用）
$KONOHA_IP = "100.101.102.104"
$env:N8N_URL = "http://${KONOHA_IP}:5678"
$env:SEARXNG_URL = "http://${KONOHA_IP}:8080"

Write-Host "✅ X280設定を適用しました"
```

**Konoha用設定: `config_konoha.ps1`**
```powershell
# Konoha 設定
$env:DEVICE_NAME = "Konoha"

# リモートサービス（X280で実行）
$X280_IP = "100.101.102.103"
$env:OLLAMA_URL = "http://${X280_IP}:11434"
$env:COMFYUI_URL = "http://${X280_IP}:8188"
$env:MRL_MEMORY_URL = "http://${X280_IP}:5105"
$env:LEARNING_SYSTEM_URL = "http://${X280_IP}:5106"
$env:GALLERY_API_URL = "http://${X280_IP}:5120"

# ローカルサービス（このマシンで起動）
# - 環境変数は設定しない（デフォルト = localhost）

Write-Host "✅ Konoha設定を適用しました"
```

#### 設定ファイルの使用

```powershell
# X280で
. .\config_x280.ps1
python manaos_integrations/start_vscode_cursor_services.py

# Konohaで
. .\config_konoha.ps1
python manaos_integrations/start_vscode_cursor_services.py
```

---

## パフォーマンス最適化

### 1. ネットワーク最適化

**Tailscaleでダイレクト接続を確認:**
```powershell
tailscale status

# "direct" と表示されていることを確認
# "relay" の場合は、ルーターのUPnP/NAT設定を有効化
```

### 2. サービス固有の最適化

**Ollama - モデルプリロード:**
```powershell
# よく使うモデルをメモリに常駐
ollama run llama3.2:latest ""
ollama run qwen2.5:7b ""
```

**ComfyUI - ワークフローキャッシュ:**
```python
# ComfyUI設定でモデルキャッシュを有効化
```

**MRL Memory - メモリ割り当て:**
```python
# _paths.py または環境変数で設定
MRL_MEMORY_CACHE_SIZE = 1024  # MB
```

### 3. リソース監視

**リモート監視スクリプト:**
```powershell
# X280のリソース状況をKonohaから確認
Invoke-Command -ComputerName x280 -ScriptBlock {
    Get-Process | Sort-Object CPU -Descending | Select-Object -First 5
}

# またはTailscale SSHで
tailscale ssh x280
```

---

## トラブルシューティング

### 問題: リモートサービスに接続できない

**チェックリスト:**

1. **Tailscale接続を確認**
   ```powershell
   tailscale status
   ping 100.x.x.x
   ```

2. **サービスがすべてのインターフェースでリッスンしているか**
   ```powershell
   # サーバー側で確認
   netstat -ano | Select-String "0.0.0.0:11434"
   # または
   netstat -ano | Select-String ":11434"
   ```

3. **ファイアウォールルールを確認**
   ```powershell
   Get-NetFirewallRule | Where-Object { $_.DisplayName -like "*ManaOS*" }
   ```

4. **ポート疎通テスト**
   ```powershell
   Test-NetConnection -ComputerName 100.x.x.x -Port 11434
   ```

### 問題: パフォーマンスが遅い

**原因特定:**

1. **ネットワーク遅延**
   ```powershell
   # レイテンシ確認
   ping 100.x.x.x -n 10
   
   # 継続的モニタリング
   ping 100.x.x.x -t
   ```

2. **帯域幅確認**
   ```powershell
   # iperf3でスループット測定
   # サーバー側
   iperf3 -s
   
   # クライアント側
   iperf3 -c 100.x.x.x
   ```

3. **Relayの使用を避ける**
   ```powershell
   # ダイレクト接続できない場合
   tailscale netcheck
   
   # ルーターでUPnP有効化、またはポートフォワーディング設定
   ```

### 問題: サービスが起動しない

**デバッグ手順:**

1. **ローカルで起動確認**
   ```powershell
   # まずlocalhost (127.0.0.1) で起動できるか確認
   $env:OLLAMA_URL = ""  # 環境変数をクリア
   ollama serve
   ```

2. **ポート競合を確認**
   ```powershell
   netstat -ano | Select-String ":11434"
   ```

3. **ログファイルを確認**
   ```powershell
   Get-Content logs/manaos_service_*.log -Tail 100
   ```

---

## 環境セットアップスクリプト

### 自動セットアップスクリプト

**`setup_distributed_x280.ps1`**
```powershell
# X280 分散環境セットアップスクリプト

Write-Host "🚀 X280 分散環境セットアップ開始..." -ForegroundColor Cyan

# Tailscale接続確認
Write-Host "`n1️⃣ Tailscale接続確認..."
$tailscaleStatus = tailscale status
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Tailscaleが実行されていません" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Tailscale接続OK" -ForegroundColor Green

# Konoha IP取得
$KONOHA_IP = (tailscale status | Select-String "konoha").Line -replace '^(\S+).*', '$1'
Write-Host "  Konoha IP: $KONOHA_IP" -ForegroundColor Yellow

# ファイアウォール設定
Write-Host "`n2️⃣ ファイアウォールルール設定..."
$ruleName = "ManaOS Distributed Services"
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue

if (-not $existingRule) {
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound -Protocol TCP `
        -LocalPort 5105-5110,8188,11434,1234,5120 `
        -Action Allow -RemoteAddress 100.0.0.0/8 | Out-Null
    Write-Host "✅ ファイアウォールルール作成完了" -ForegroundColor Green
} else {
    Write-Host "✅ ファイアウォールルール既存" -ForegroundColor Green
}

# 環境変数設定（Konohaのサービス）
Write-Host "`n3️⃣ 環境変数設定..."
$env:N8N_URL = "http://${KONOHA_IP}:5678"
$env:SEARXNG_URL = "http://${KONOHA_IP}:8080"
$env:WHISPER_URL = "http://${KONOHA_IP}:9000"
$env:VOICEVOX_URL = "http://${KONOHA_IP}:50021"

Write-Host "  N8N_URL: $env:N8N_URL" -ForegroundColor Yellow
Write-Host "  SEARXNG_URL: $env:SEARXNG_URL" -ForegroundColor Yellow
Write-Host "  WHISPER_URL: $env:WHISPER_URL" -ForegroundColor Yellow
Write-Host "  VOICEVOX_URL: $env:VOICEVOX_URL" -ForegroundColor Yellow

# サービス起動
Write-Host "`n4️⃣ サービス起動..."
$env:OLLAMA_HOST = "0.0.0.0:11434"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "ollama serve"

Write-Host "`n✅ X280セットアップ完了！" -ForegroundColor Green
Write-Host "  - Ollama: http://0.0.0.0:11434 (全インターフェース)" -ForegroundColor Cyan
Write-Host "  - ComfyUI: 手動で起動してください" -ForegroundColor Cyan
Write-Host "  - ManaOS統合: python start_vscode_cursor_services.py" -ForegroundColor Cyan
```

**`setup_distributed_konoha.ps1`**
```powershell
# Konoha 分散環境セットアップスクリプト

Write-Host "🚀 Konoha 分散環境セットアップ開始..." -ForegroundColor Cyan

# Tailscale接続確認
Write-Host "`n1️⃣ Tailscale接続確認..."
$tailscaleStatus = tailscale status
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Tailscaleが実行されていません" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Tailscale接続OK" -ForegroundColor Green

# X280 IP取得
$X280_IP = (tailscale status | Select-String "x280").Line -replace '^(\S+).*', '$1'
Write-Host "  X280 IP: $X280_IP" -ForegroundColor Yellow

# 環境変数設定（X280のサービス）
Write-Host "`n2️⃣ 環境変数設定..."
$env:OLLAMA_URL = "http://${X280_IP}:11434"
$env:COMFYUI_URL = "http://${X280_IP}:8188"
$env:MRL_MEMORY_URL = "http://${X280_IP}:5105"
$env:LEARNING_SYSTEM_URL = "http://${X280_IP}:5106"
$env:LLM_ROUTING_URL = "http://${X280_IP}:5107"
$env:GALLERY_API_URL = "http://${X280_IP}:5120"
$env:LM_STUDIO_URL = "http://${X280_IP}:1234"

Write-Host "  OLLAMA_URL: $env:OLLAMA_URL" -ForegroundColor Yellow
Write-Host "  COMFYUI_URL: $env:COMFYUI_URL" -ForegroundColor Yellow
Write-Host "  MRL_MEMORY_URL: $env:MRL_MEMORY_URL" -ForegroundColor Yellow
Write-Host "  GALLERY_API_URL: $env:GALLERY_API_URL" -ForegroundColor Yellow

# 接続テスト
Write-Host "`n3️⃣ X280サービスへの接続テスト..."
$services = @(
    @{Name="Ollama"; URL=$env:OLLAMA_URL},
    @{Name="ComfyUI"; URL=$env:COMFYUI_URL},
    @{Name="MRL Memory"; URL=$env:MRL_MEMORY_URL}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri $service.URL -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        Write-Host "  ✅ $($service.Name): 接続OK" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️  $($service.Name): 接続不可（サービス未起動の可能性）" -ForegroundColor Yellow
    }
}

Write-Host "`n✅ Konohaセットアップ完了！" -ForegroundColor Green
Write-Host "  - X280のサービスにリモート接続します" -ForegroundColor Cyan
Write-Host "  - Konohaローカルサービス: n8n, SearXNG など" -ForegroundColor Cyan
```

---

## まとめ

このガイドに従って:

1. ✅ Tailscaleでデバイスを接続
2. ✅ サービスを適切に配置（GPU/CPU/ストレージ）
3. ✅ 環境変数で接続先を設定
4. ✅ ファイアウォールとネットワークを構成
5. ✅ 監視とトラブルシューティング

これで、ManaOSを複数デバイスで効率的に分散実行できます！

## 関連ドキュメント

- [README.md](README.md) - プロジェクト概要
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) - 環境変数詳細
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - トラブルシューティング
