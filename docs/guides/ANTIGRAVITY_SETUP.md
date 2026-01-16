# 🛠️ Antigravity セットアップガイド

**最終更新**: 2026-01-06  
**目的**: Antigravityの起動方法を設定

---

## 🎯 Antigravityの起動方法

Antigravityは**必要なときだけ起動**するツールです。  
起動方法は3つあります：

1. **Webアプリ**（推奨）
2. **デスクトップアプリ**
3. **コマンドライン**

---

## 📋 セットアップ手順

### STEP 1: 起動方法を選択

#### 方法1: Webアプリ（推奨）

```powershell
# 環境変数を設定
[Environment]::SetEnvironmentVariable('ANTIGRAVITY_URL', 'https://antigravity.ai', 'User')

# 実際のURLに置き換えてください
# 例: https://app.antigravity.ai
# 例: http://localhost:3000（ローカルで起動している場合）
```

#### 方法2: デスクトップアプリ

```powershell
# 環境変数を設定
[Environment]::SetEnvironmentVariable('ANTIGRAVITY_PATH', 'C:\path\to\antigravity.exe', 'User')

# 実際のパスに置き換えてください
# 例: C:\Users\mana4\AppData\Local\Programs\antigravity\antigravity.exe
```

#### 方法3: コマンドライン

```powershell
# Antigravityがコマンドライン対応している場合
# PATHに設定されている必要があります
antigravity --version
```

---

### STEP 2: 起動スクリプトを実行

```powershell
.\start_antigravity.ps1
```

これでAntigravityが起動します。

---

## 🚀 使い方

### 1. Antigravityを起動

```powershell
.\start_antigravity.ps1
```

### 2. プロンプトを選択

`antigravity_prompts.md` から適切なプロンプトを選択：
- MOC再構築
- 記事化
- YAML一括編集

### 3. ノートを貼り付け

1. Obsidianで関連ノートを複数選択
2. 内容をコピー
3. Antigravityに貼り付け

### 4. 実行して結果を取得

### 5. 結果をObsidianに保存

```python
from manaos_obsidian_integration import ObsidianNotebookLMAntigravityIntegration

integration = ObsidianNotebookLMAntigravityIntegration()
integration.save_antigravity_result(
    content="再構築された内容",
    title="テーマ名",
    output_type="moc"  # or "article"
)
```

---

## 🔧 設定確認

現在の設定を確認：

```powershell
# 環境変数を確認
[Environment]::GetEnvironmentVariable('ANTIGRAVITY_URL', 'User')
[Environment]::GetEnvironmentVariable('ANTIGRAVITY_PATH', 'User')
```

---

## 📝 ショートカット作成（オプション）

### デスクトップショートカット

1. **デスクトップで右クリック**
   - 「新規作成」→「ショートカット」

2. **項目の場所**
   ```
   powershell.exe -ExecutionPolicy Bypass -File "C:\Users\mana4\Desktop\manaos_integrations\start_antigravity.ps1"
   ```

3. **名前**
   ```
   Antigravity起動
   ```

### スタートメニューに追加（オプション）

```powershell
# ショートカットをスタートメニューにコピー
$shortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Antigravity起動.lnk"
$targetPath = "powershell.exe"
$arguments = "-ExecutionPolicy Bypass -File `"$PSScriptRoot\start_antigravity.ps1`""

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.Arguments = $arguments
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Save()
```

---

## 🎯 起動タイミング

### ✅ 起動すべきとき

- **MOCを作りたいとき**
  - 関連ノートが5個以上たまった
  - テーマが明確になってきた

- **記事化したいとき**
  - 学習ログが一定量たまった
  - 振り返りをまとめたい
  - 思考メモを整理したい

- **YAML編集したいとき**
  - 複数ノートのタグを一括追加
  - メタデータを一括編集

### ❌ 起動不要なとき

- **毎日の記録時**（Obsidianで十分）
- **週次分析時**（NotebookLMで十分）
- **常時監視**（ManaOSが担当）

---

## 🔄 完全フロー

```
【アウトプット時】
関連ノートを複数選択
  ↓
.\start_antigravity.ps1 を実行
  ↓
Antigravityが起動
  ↓
プロンプトを選択（antigravity_prompts.md）
  ↓
ノートを貼り付け
  ↓
実行
  ↓
結果を取得
  ↓
Obsidianに保存（manaos_obsidian_integration.py）
  ↓
Antigravityを閉じる
```

---

## 🐛 トラブルシューティング

### Antigravityが起動しない

1. **環境変数を確認**
   ```powershell
   [Environment]::GetEnvironmentVariable('ANTIGRAVITY_URL', 'User')
   [Environment]::GetEnvironmentVariable('ANTIGRAVITY_PATH', 'User')
   ```

2. **URL/パスが正しいか確認**
   - Webアプリの場合: ブラウザで直接開けるか確認
   - デスクトップアプリの場合: ファイルが存在するか確認

3. **手動で起動**
   - ブラウザで直接URLを開く
   - または、デスクトップアプリを直接起動

---

## 🎉 完了！

これでAntigravityの起動設定が完了しました。

**Antigravityは「知識加工工場」。必要なときだけ起動して、作業完了後は閉じる。**

---




















