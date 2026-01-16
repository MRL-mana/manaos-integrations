# 🔥 ComfyUI常時起動設定完了

## ✅ 設定完了

ComfyUIをシステム起動時に自動的に起動するように設定しました。

---

## 📋 設定内容

### タスクスケジューラ設定

- **タスク名**: `ComfyUI Auto Start`
- **起動タイミング**: システム起動時
- **実行方法**: バックグラウンド（`-Background`オプション付き）
- **スクリプト**: `start_comfyui_svi.ps1`
- **再起動設定**: 失敗時に最大3回再試行（1分間隔）

---

## 🔧 設定の確認方法

### PowerShellで確認

```powershell
# タスクの確認
Get-ScheduledTask -TaskName "ComfyUI Auto Start"

# タスクの詳細確認
Get-ScheduledTask -TaskName "ComfyUI Auto Start" | Get-ScheduledTaskInfo
```

### タスクスケジューラGUIで確認

1. **タスクスケジューラを開く**
   - Windowsキー + R → `taskschd.msc` → Enter

2. **タスクを確認**
   - タスクスケジューラライブラリ → `ComfyUI Auto Start`

3. **タスクの実行**
   - 右クリック → 「実行」で手動実行可能

---

## 🚀 動作確認

### 次のシステム起動時

1. **システムを再起動**
2. **ComfyUIが自動的に起動することを確認**
   - http://localhost:8188 にアクセス
   - タスクマネージャーでpythonプロセスを確認

### 手動でテスト

```powershell
# タスクを手動で実行
Start-ScheduledTask -TaskName "ComfyUI Auto Start"

# 数秒待ってから確認
Start-Sleep -Seconds 5
Invoke-WebRequest -Uri "http://localhost:8188"
```

---

## 🔧 設定の変更・削除

### タスクを削除

```powershell
Unregister-ScheduledTask -TaskName "ComfyUI Auto Start" -Confirm:$false
```

### タスクを無効化

```powershell
Disable-ScheduledTask -TaskName "ComfyUI Auto Start"
```

### タスクを有効化

```powershell
Enable-ScheduledTask -TaskName "ComfyUI Auto Start"
```

---

## 📊 リソース使用量

### 現在の使用量

- **メモリ**: 約900MB（モデル未ロード時）
- **CPU**: アイドル時1〜5%
- **GPU**: 使用時のみ

### モデルロード時

- **メモリ**: 2GB〜8GB（モデルによる）
- **CPU**: アイドル時1〜5%、生成時50〜100%
- **GPU**: 使用時のみ

---

## 💡 注意事項

1. **システム起動時間**
   - ComfyUIの起動には数秒〜数十秒かかります
   - システム起動直後はまだ起動していない可能性があります

2. **リソース使用量**
   - メモリが16GB以上あることを推奨
   - メモリが8GB以下の場合は、必要時に起動することを推奨

3. **エラー処理**
   - 起動に失敗した場合、最大3回再試行します
   - 再試行間隔は1分です

---

## 🔥 レミ先輩のまとめ

### ✅ 設定完了
- **タスクスケジューラ**: 自動起動設定完了 ✅
- **バックグラウンド起動**: 設定完了 ✅
- **エラー処理**: 再試行設定完了 ✅

### 📋 次のステップ
1. **システムを再起動して動作確認**
2. **ComfyUIが自動的に起動することを確認**
3. **リソース使用量を監視**

---

**レミ先輩モード**: 常時起動設定完了！次のシステム起動時に自動的にComfyUIが起動します！🔥
