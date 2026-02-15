# 🚨 ManaOS 緊急停止システム

## 📋 概要

**最後の手段**として、すべてのManaOSサービスを一括停止するツールです。

⚠️ **重要**: 通常は `Ctrl+C` でサービスを停止してください。このツールは以下の場合のみ使用:

- サービスが応答しなくなった
- `Ctrl+C` で停止できない
- プロセスが残留している
- システムが不安定になった

## 🚀 使用方法

### 方法1: VSCode/Cursorタスク（推奨）

```
Ctrl+Shift+P → "Tasks: Run Task" → "🚨 ManaOS: 緊急停止"
```

### 方法2: コマンドライン

```powershell
cd C:\Users\mana4\Desktop\manaos_integrations
python emergency_stop.py
```

## 🔍 動作の流れ

1. **プロセス検索**: ManaOS関連のPythonプロセスを検索
2. **確認**: 停止対象のプロセスリストを表示
3. **ユーザー確認**: `yes` と入力して確認
4. **穏やかな停止**: まず通常の方法で終了を試みる
5. **強制終了**: 必要に応じて強制終了
6. **結果表示**: 停止されたプロセス数を表示

## 📊 実行例

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🚨 ManaOS 緊急停止システム 🚨                   ║
║                                                              ║
║  すべてのManaOS関連プロセスを停止します                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

2026-02-07 18:10:00 [    INFO] ManaOS関連プロセスを検索中...
2026-02-07 18:10:01 [ WARNING] ⚠️ 4個のプロセスが見つかりました:
  PID 12728: ...unified_api_server
  PID 16472: ...llm_routing_mcp_server.server
  PID 10224: ...learning_system_api
  PID 38268: ...mrl_memory_integration

⚠️ これらのプロセスをすべて停止します。よろしいですか？
続行するには 'yes' と入力してください: yes

2026-02-07 18:10:05 [    INFO] プロセスを停止中...
2026-02-07 18:10:05 [    INFO] プロセスを停止中: PID=12728, Name=python
2026-02-07 18:10:06 [    INFO] ✅ プロセス 12728 を停止しました
...

✅ 緊急停止が完了しました
   停止したプロセス数: 4
```

## 🛡️ 安全機能

### 確認プロンプト

- デフォルトで確認を求める
- 'yes' と明示的に入力しない限り実行しない
- キャンセル可能（`Ctrl+C` または 'no'）

### 段階的停止

1. **穏やかな停止**: `Stop-Process` で通常終了
2. **待機**: 1秒間プロセスの終了を確認
3. **強制終了**: まだ動いている場合のみ `-Force` オプション使用

### ログ記録

- すべての操作をログ出力
- 停止成功/失敗を明確に区別
- タイムスタンプ付き

## ⚙️ 停止対象

以下のキーワードを含むPythonプロセスを対象:

- `mrl_memory`
- `learning_system`
- `llm_routing`
- `unified_api`
- `autonomous_operations`
- `start_vscode_cursor_services`

## 🔧 トラブルシューティング

### プロセスが見つからない

```powershell
# 手動でプロセスを確認
Get-Process python | Where-Object { $_.CommandLine -like "*manaos*" }

# または
Get-Process python
```

### 停止に失敗する

1. **管理者権限で実行**:
   - VSCodeを管理者として実行
   - PowerShellを管理者として実行

2. **タスクマネージャーで手動停止**:
   ```
   Ctrl+Shift+Esc → [詳細] タブ → python.exe を選択 → [タスクの終了]
   ```

3. **システム再起動** (最終手段):
   ```powershell
   Restart-Computer -Force
   ```

### スクリプトが実行できない

```powershell
# Python環境を確認
python --version

# スクリプトの場所を確認
Get-Item C:\Users\mana4\Desktop\manaos_integrations\emergency_stop.py
```

## 📝 使用シナリオ

### シナリオ1: サービスが応答しない

**症状**: Unified APIがリクエストに応答しない

**対処**:
```powershell
# 1. まずヘルスチェック
python check_services_health.py

# 2. 問題が続く場合は緊急停止
python emergency_stop.py

# 3. 再起動
python start_vscode_cursor_services.py
```

### シナリオ2: プロセスが残留している

**症状**: 前回の起動プロセスがまだ動いている

**対処**:
```powershell
# 緊急停止で古いプロセスをクリーンアップ
python emergency_stop.py

# 新規起動
python start_vscode_cursor_services.py
```

### シナリオ3: ポート競合

**症状**: "Address already in use" エラー

**対処**:
```powershell
# 1. ポート使用状況を確認
netstat -ano | findstr ":9510 :5103 :5104 :5111"

# 2. ManaOSプロセスを停止
python emergency_stop.py

# 3. それでもポートが使用中なら、手動で停止
Stop-Process -Id <PID>
```

## 🆘 サポート

問題が解決しない場合:

1. ログファイルを確認
2. タスクマネージャーでプロセスを確認
3. システムイベントログを確認
4. 必要に応じてシステムを再起動

---

**最終更新**: 2026年2月7日  
**安全レベル**: 高（確認プロンプト付き）  
**推奨度**: 緊急時のみ使用
