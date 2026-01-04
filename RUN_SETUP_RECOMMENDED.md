# 標準構成（推奨）自動起動設定の実行方法

## 正しい実行方法

### 方法1: フルパスで実行（推奨）

```powershell
# 管理者権限でPowerShellを開いて
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
& ".\setup_recommended_autostart.ps1"
```

### 方法2: フルパスを指定

```powershell
& "C:\Users\mana4\OneDrive\Desktop\manaos_integrations\setup_recommended_autostart.ps1"
```

### 方法3: 実行ポリシーを一時的に変更（必要に応じて）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup_recommended_autostart.ps1
```

---

## ワンライナー（コピペ用）

```powershell
cd C:\Users\mana4\OneDrive\Desktop\manaos_integrations; & ".\setup_recommended_autostart.ps1"
```

---

## 注意事項

- **必ず管理者権限でPowerShellを開いてください**
- スクリプトは `&` を使って実行してください
- 実行ポリシーが `Bypass` の場合は問題ありません











