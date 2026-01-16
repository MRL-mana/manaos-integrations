# 🔥 ComfyUI常時起動ガイド

## 📋 現在の状況

### ComfyUIの起動確認

- **URL**: http://localhost:8188
- **ポート**: 8188
- **ステータス**: 起動中または起動していない可能性

---

## 💡 常時起動について

### ✅ メリット

1. **即座に画像生成可能**
   - 起動待ち時間なし
   - `generate_image`ツールがすぐに使用可能

2. **安定性**
   - 起動・停止の繰り返しによる不具合を回避
   - 常に同じ状態で動作

### ❌ デメリット（リソース使用）

1. **メモリ使用量**
   - ComfyUIは通常 **2GB〜4GB** のメモリを使用
   - モデルをロードするとさらに増加（**4GB〜8GB**）

2. **GPU使用量**
   - GPUを使用する場合、常時占有される
   - 他のアプリケーションでGPUを使用する場合に影響

3. **CPU使用量**
   - アイドル時は低い（**1〜5%**）
   - 画像生成時は高い（**50〜100%**）

---

## 🔧 常時起動の設定方法

### 方法1: Windowsタスクスケジューラで自動起動

```powershell
# タスクスケジューラで自動起動を設定
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$PWD\start_comfyui_svi.ps1`" -Background" -WorkingDirectory $PWD
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "ComfyUI Auto Start" -Action $action -Trigger $trigger -Principal $principal -Settings $settings
```

### 方法2: バックグラウンドで起動

```powershell
# バックグラウンドで起動（現在のスクリプトで対応済み）
.\start_comfyui_svi.ps1 -Background
```

---

## 📊 リソース使用量の目安

### 軽量モデル（例: SD 1.5）

- **メモリ**: 2GB〜4GB
- **GPU**: 2GB〜4GB（使用時）
- **CPU**: 1〜5%（アイドル時）、50〜100%（生成時）

### 高品質モデル（例: SDXL）

- **メモリ**: 4GB〜8GB
- **GPU**: 6GB〜12GB（使用時）
- **CPU**: 1〜5%（アイドル時）、50〜100%（生成時）

---

## 🎯 推奨設定

### ✅ 常時起動がおすすめな場合

1. **メモリが16GB以上ある**
2. **GPUが8GB以上ある（またはCPUのみで問題ない）**
3. **頻繁に画像生成を行う**
4. **他の重いアプリケーションを同時に使わない**

### ❌ 常時起動がおすすめでない場合

1. **メモリが8GB以下**
2. **GPUが4GB以下**
3. **画像生成をたまにしか使わない**
4. **他の重いアプリケーションを同時に使う**

---

## 🔥 レミ先輩の推奨

### 優先度1: リソース確認

1. **メモリ使用量を確認**
   ```powershell
   Get-Process | Where-Object {$_.ProcessName -like "*python*" -or $_.ProcessName -like "*comfy*"} | Select-Object ProcessName, @{Name="Memory(MB)";Expression={[math]::Round($_.WorkingSet64 / 1MB, 2)}}
   ```

2. **GPU使用量を確認**
   - NVIDIA GPU: `nvidia-smi`
   - タスクマネージャーでGPU使用率を確認

### 優先度2: 動作確認

1. **ComfyUIが正常に動作することを確認**
   - http://localhost:8188 にアクセス
   - 画像生成をテスト

2. **リソース使用量を監視**
   - タスクマネージャーでメモリ・CPU・GPU使用率を確認
   - 問題があれば停止

---

## 💡 代替案：オンデマンド起動

常時起動が重い場合は、必要時に起動する方法もあります：

```powershell
# 画像生成が必要な時だけ起動
.\start_comfyui_svi.ps1

# 使用後は停止
# Ctrl+C で停止
```

---

**レミ先輩モード**: メモリが16GB以上あれば常時起動も可能！ただし、リソース使用量を監視して、問題があれば停止してください！🔥
