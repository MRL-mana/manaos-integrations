# n8n 常時起動 簡単手順

## 現在の状況
n8nは手動起動のみで、常時起動の設定がされていません。

## 最も簡単な方法: タスクスケジューラで設定

### 手順

1. **タスクスケジューラを開く**
   - Windowsキー → "タスクスケジューラ" を検索して開く

2. **基本タスクの作成**
   - 右側の「基本タスクの作成」をクリック
   - 名前: `n8n Auto Start`
   - 説明: `n8n workflow automation server`

3. **トリガーの設定**
   - 「ログオン時」を選択
   - 「次へ」

4. **操作の設定**
   - 「プログラムの開始」を選択
   - プログラム/スクリプト: `n8n`
   - 引数の追加: `start --port 5679`
   - 開始場所: `%USERPROFILE%\.n8n`
   - 「次へ」→「完了」

5. **詳細設定（オプション）**
   - 作成したタスクを右クリック → 「プロパティ」
   - 「最上位の特権で実行する」にチェック（オプション）
   - 「ユーザーがログオンしているかどうかにかかわらず実行する」を選択（オプション）

## 確認方法

```powershell
# タスクの状態確認
Get-ScheduledTask -TaskName "n8n Auto Start"

# タスクを手動実行
Start-ScheduledTask -TaskName "n8n Auto Start"

# タスクを無効化
Disable-ScheduledTask -TaskName "n8n Auto Start"

# タスクを有効化
Enable-ScheduledTask -TaskName "n8n Auto Start"
```

## 現在の起動方法（手動）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
.\start_n8n_local.ps1
```

## 注意事項

- タスクスケジューラの方法では、ログアウトするとn8nも停止する可能性があります
- 完全にバックグラウンドで常時実行したい場合は、Windowsサービスとして登録する必要があります











