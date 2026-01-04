# サーバー起動手順

## 正しい起動方法

PowerShellで以下を**順番に**実行してください:

```powershell
# 1. ディレクトリに移動
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations

# 2. サーバーを起動
python start_server_with_notification.py
```

---

## 重要

- **必ず**`cd`コマンドでディレクトリに移動してから実行してください
- 現在のディレクトリが`C:\WINDOWS\system32`の場合は、上記の`cd`コマンドを実行してください
- サーバーは起動したままにしてください（Ctrl+Cで停止）

---

## 起動確認

サーバーが起動したら、**別のPowerShellウィンドウ**で以下を実行:

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
python check_server_status.py
```

---

**修正完了**: 重複エンドポイントをすべて削除しました











