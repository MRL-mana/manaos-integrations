# 🚀 Obsidian × NotebookLM × Antigravity × ManaOS 完全セットアップガイド

**最終更新**: 2026-01-06  
**状態**: 完全実装・動作確認済み

---

## 🎯 全体像

```
【現実の行動・思考】
        ↓
   Obsidian（母艦）
  ─ 記録 / ログ / 構想 ─
        ↓
 NotebookLM（分析AI）
  ─ 気づき / 傾向 / 因果 ─
        ↓
 Antigravity（再構築AI）
  ─ 記事化 / MOC / 道具化 ─
        ↓
     ManaOS
  ─ 記憶 / 自動化 / 収益 ─
```

---

## 📋 セットアップ手順

### STEP 1: 一括セットアップ実行

```powershell
.\setup_full_integration.ps1
```

これで以下が自動実行されます：
- ✅ Obsidianテンプレートの配置
- ✅ 今日のデイリーノート作成
- ✅ 統合テスト実行
- ✅ 環境変数確認

---

### STEP 2: n8nワークフローのインポート

1. **n8nを開く**
   ```
   http://localhost:5678
   ```

2. **ワークフローをインポート**
   - Workflows → Import from File
   - `n8n_workflows/obsidian_notebooklm_weekly.json` を選択
   - 認証情報を設定（Obsidian、Slack）
   - ワークフローを有効化

3. **動作確認**
   - 毎週日曜22時に自動実行
   - 直近14日のDailyノートを取得
   - NotebookLM用の入力ファイルを作成
   - Slackに通知

---

### STEP 3: 環境変数の設定

```powershell
# Obsidian Vaultパス
[Environment]::SetEnvironmentVariable('OBSIDIAN_VAULT_PATH', 'C:\Users\mana4\Documents\Obsidian Vault', 'User')

# ManaOS Orchestrator URL
[Environment]::SetEnvironmentVariable('ORCHESTRATOR_URL', 'http://localhost:5106', 'User')

# Slack Webhook URL（オプション）
[Environment]::SetEnvironmentVariable('SLACK_WEBHOOK_URL', 'https://hooks.slack.com/services/...', 'User')
```

---

## 🎨 使い方

### 毎日: Obsidianで記録

1. **Daily/YYYY-MM-DD.md を開く**
   - テンプレートが自動で作成されている

2. **箇条書きで埋める**
   - 体調: ◎△×
   - ひとこと: 1行でOK
   - 思考メモ: 箇条書きでOK
   - 行動ログ: 簡潔に

3. **完璧を目指さない**
   - 空白あってもOK
   - 考えずに放り込む

---

### 週1回: NotebookLMで分析

1. **自動準備（日曜22時）**
   - n8nワークフローが自動実行
   - `Review/YYYY-MM-DD-notebooklm-input.md` が作成される
   - Slackに通知が来る

2. **NotebookLMで分析**
   - NotebookLMを開く
   - `Review/YYYY-MM-DD-notebooklm-input.md` を投入
   - 質問テンプレート（`notebooklm_question_templates.md`）を使用
   - 4つの質問を順番に実行

3. **結果を保存**
   ```python
   python manaos_obsidian_integration.py
   # または手動で Review/YYYY-MM-DD-notebooklm-result.md に保存
   ```

---

### アウトプット時: Antigravityで再構築

1. **関連ノートを選択**
   - Obsidianで複数のノートを選択
   - 内容をコピー

2. **Antigravityで実行**
   - Antigravityを開く
   - プロンプト（`antigravity_prompts.md`）を選択
   - ノートを貼り付け
   - 実行

3. **結果を保存**
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

## 🔧 ファイル構成

```
manaos_integrations/
├── obsidian_manaos_template.md          # Obsidianテンプレート集
├── notebooklm_question_templates.md    # NotebookLM質問テンプレート
├── antigravity_prompts.md              # Antigravityプロンプト集
├── manaos_architecture_latest.md      # ManaOS全体アーキテクチャ図
├── setup_obsidian_templates.py         # Obsidianテンプレート配置スクリプト
├── manaos_obsidian_integration.py      # 統合スクリプト
├── setup_full_integration.ps1         # 一括セットアップスクリプト
└── n8n_workflows/
    └── obsidian_notebooklm_weekly.json # 週次分析ワークフロー
```

---

## 📚 参考ドキュメント

- **Obsidianテンプレート**: `obsidian_manaos_template.md`
- **NotebookLM質問**: `notebooklm_question_templates.md`
- **Antigravityプロンプト**: `antigravity_prompts.md`
- **ManaOSアーキテクチャ**: `manaos_architecture_latest.md`

---

## 🎯 重要ルール（再掲）

1. **完璧を目指さない**
2. **箇条書きでOK**
3. **空白あってもOK**
4. **考えずに放り込む**

**ManaOSが後で整理してくれる。**

---

## 🔄 自動化フロー

```
【毎日】
Obsidianで記録
  ↓
Daily/YYYY-MM-DD.md

【週1回（日曜22時）】
n8nワークフロー自動実行
  ↓
直近14日のDailyノート取得
  ↓
NotebookLM用入力ファイル作成
  ↓
Slack通知
  ↓
NotebookLMで分析（手動）
  ↓
結果をObsidianに保存
  ↓
ManaOSの記憶システムに登録

【アウトプット時】
関連ノートを選択
  ↓
Antigravityで再構築
  ↓
MOC/記事化
  ↓
Obsidianに保存
  ↓
ManaOSの記憶システムに登録
```

---

## 🐛 トラブルシューティング

### Obsidian Vaultが見つからない

```powershell
# 環境変数を確認
[Environment]::GetEnvironmentVariable('OBSIDIAN_VAULT_PATH', 'User')

# 設定されていない場合は設定
[Environment]::SetEnvironmentVariable('OBSIDIAN_VAULT_PATH', 'C:\Users\mana4\Documents\Obsidian Vault', 'User')
```

### n8nワークフローが動かない

1. **n8nが起動しているか確認**
   ```
   http://localhost:5678
   ```

2. **ワークフローが有効化されているか確認**
   - n8n UIでワークフローを開く
   - 右上の「Active」トグルがONになっているか

3. **認証情報が設定されているか確認**
   - Obsidian API認証情報
   - Slack Webhook URL

### NotebookLMで分析できない

1. **入力ファイルが作成されているか確認**
   ```
   Review/YYYY-MM-DD-notebooklm-input.md
   ```

2. **Dailyノートが存在するか確認**
   ```
   Daily/YYYY-MM-DD.md
   ```

---

## 🎉 完了！

これで「Obsidian → NotebookLM → Antigravity → ManaOS」の完全統合が完了しました。

**全部使う。役割を混ぜない。完璧を目指さない。**

---




















