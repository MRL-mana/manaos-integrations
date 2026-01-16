# 🔥 ComfyUI常時起動設定（手動設定ガイド）

## 📋 設定方法

### 方法1: PowerShellスクリプトで設定（推奨）

1. **PowerShellを管理者として実行**
   - Windowsキー → 「PowerShell」を検索
   - 右クリック → 「管理者として実行」

2. **スクリプトを実行**
   ```powershell
   cd C:\Users\mana4\Desktop\manaos_integrations
   .\setup_comfyui_auto_start.ps1
   ```

3. **確認**
   - タスクが正しく登録されたことを確認
   - 次のシステム起動時に自動的に起動します

---

### 方法2: タスクスケジューラGUIで手動設定

1. **タスクスケジューラを開く**
   - Windowsキー + R → `taskschd.msc` → Enter

2. **基本タスクの作成**
   - 右側の「基本タスクの作成」をクリック
   - 名前: `ComfyUI Auto Start`
   - 説明: `ComfyUI自動起動（システム起動時にバックグラウンドで起動）`

3. **トリガーの設定**
   - 「タスクの開始時期」: 「コンピューターの起動時」を選択

4. **操作の設定**
   - 「操作」: 「プログラムの開始」を選択
   - プログラム/スクリプト: `PowerShell.exe`
   - 引数の追加: `-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File "C:\Users\mana4\Desktop\manaos_integrations\start_comfyui_svi.ps1" -Background`
   - 開始: `C:\Users\mana4\Desktop\manaos_integrations`

5. **条件の設定**
   - 「コンピューターが AC 電源で動作している場合のみタスクを開始する」のチェックを外す
   - 「バッテリーで動作している場合でもタスクを開始する」にチェック

6. **設定の確認**
   - 「完了」をクリック

---

## 🔧 設定の確認

### PowerShellで確認

```powershell
# タスクの確認
Get-ScheduledTask -TaskName "ComfyUI Auto Start"

# タスクの詳細確認
Get-ScheduledTask -TaskName "ComfyUI Auto Start" | Get-ScheduledTaskInfo
```

### タスクスケジューラGUIで確認

1. タスクスケジューラを開く
2. タスクスケジューラライブラリ → `ComfyUI Auto Start` を確認

---

## 🚀 動作確認

### 手動でテスト

```powershell
# タスクを手動で実行
Start-ScheduledTask -TaskName "ComfyUI Auto Start"

# 数秒待ってから確認
Start-Sleep -Seconds 10
Invoke-WebRequest -Uri "http://localhost:8188"
```

### システム再起動後

1. システムを再起動
2. 数秒〜数十秒待つ
3. http://localhost:8188 にアクセスして確認

---

## 🔧 設定の変更・削除

### タスクを削除

```powershell
# PowerShell（管理者権限）
Unregister-ScheduledTask -TaskName "ComfyUI Auto Start" -Confirm:$false
```

### タスクを無効化

```powershell
# PowerShell（管理者権限）
Disable-ScheduledTask -TaskName "ComfyUI Auto Start"
```

### タスクを有効化

```powershell
# PowerShell（管理者権限）
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

### ✅ 設定方法
- **方法1**: PowerShellスクリプトで設定（推奨）
- **方法2**: タスクスケジューラGUIで手動設定

### 📋 次のステップ
1. **管理者権限でPowerShellを実行**
2. **setup_comfyui_auto_start.ps1 を実行**
3. **システムを再起動して動作確認**

---

**レミ先輩モード**: 管理者権限で実行すれば確実に設定できます！🔥
