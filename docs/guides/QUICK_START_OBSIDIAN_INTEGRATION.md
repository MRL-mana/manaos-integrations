# ⚡ 5分で始める Obsidian × NotebookLM × Antigravity × ManaOS

**目標**: 5分で完全統合を開始

---

## 🚀 STEP 1: 一括セットアップ（2分）

```powershell
.\setup_full_integration.ps1
```

これで以下が自動実行されます：
- ✅ Obsidianテンプレートの配置
- ✅ 今日のデイリーノート作成
- ✅ 統合テスト実行

---

## ✅ STEP 2: 統合状況確認（1分）

```powershell
.\check_obsidian_integration.ps1
```

確認項目：
- ✅ Obsidian Vaultパス
- ✅ テンプレートファイル
- ✅ 環境変数
- ✅ ManaOS統合

---

## 📝 STEP 3: 今日から使う（2分）

### 1. ObsidianでDailyノートを開く

```
Daily/2026-01-06.md
```

### 2. 箇条書きで埋める

- 体調: ◎△×
- ひとこと: 1行でOK
- 思考メモ: 箇条書きでOK

### 3. 保存

**これだけ！** 完璧を目指さない。

---

## 🎯 次のステップ（週1回）

### 週次分析（日曜22時に自動準備）

1. **n8nワークフローをインポート**（初回のみ）
   ```
   n8n_workflows/obsidian_notebooklm_weekly.json
   ```

2. **NotebookLMで分析**
   - `Review/YYYY-MM-DD-notebooklm-input.md` を投入
   - 質問テンプレート（`notebooklm_question_templates.md`）を使用

3. **結果を保存**
   ```python
   python manaos_obsidian_integration.py
   ```

---

## 🛠️ アウトプット時（必要なときだけ）

### Antigravityで再構築

1. **起動**
   ```powershell
   .\start_antigravity.ps1
   ```

2. **プロンプトを選択**
   - `antigravity_prompts.md` から選択

3. **ノートを貼り付け**
   - Obsidianから関連ノートをコピー

4. **実行して保存**
   ```python
   from manaos_obsidian_integration import ObsidianNotebookLMAntigravityIntegration
   integration = ObsidianNotebookLMAntigravityIntegration()
   integration.save_antigravity_result(content="...", title="...", output_type="moc")
   ```

---

## 📋 チェックリスト

### 初回セットアップ（5分）

- [ ] `.\setup_full_integration.ps1` を実行
- [ ] `.\check_obsidian_integration.ps1` で確認
- [ ] Obsidianで `Daily/2026-01-06.md` を開く
- [ ] 箇条書きで記録してみる

### 週次設定（10分）

- [ ] n8nワークフローをインポート
- [ ] 認証情報を設定（Obsidian、Slack）
- [ ] ワークフローを有効化

### 環境変数設定（2分）

```powershell
[Environment]::SetEnvironmentVariable('OBSIDIAN_VAULT_PATH', 'C:\Users\mana4\Documents\Obsidian Vault', 'User')
[Environment]::SetEnvironmentVariable('ORCHESTRATOR_URL', 'http://127.0.0.1:5106', 'User')
[Environment]::SetEnvironmentVariable('SLACK_WEBHOOK_URL', 'https://hooks.slack.com/services/...', 'User')
```

---

## 🎯 重要ルール（再掲）

1. **完璧を目指さない**
2. **箇条書きでOK**
3. **空白あってもOK**
4. **考えずに放り込む**

**ManaOSが後で整理してくれる。**

---

## 📚 参考ドキュメント

- **完全セットアップ**: `OBSIDIAN_NOTEBOOKLM_ANTIGRAVITY_SETUP.md`
- **Obsidianテンプレート**: `obsidian_manaos_template.md`
- **NotebookLM質問**: `notebooklm_question_templates.md`
- **Antigravityプロンプト**: `antigravity_prompts.md`
- **ManaOSアーキテクチャ**: `manaos_architecture_latest.md`

---

## 🐛 トラブルシューティング

### Obsidian Vaultが見つからない

```powershell
# 環境変数を確認
[Environment]::GetEnvironmentVariable('OBSIDIAN_VAULT_PATH', 'User')

# 設定されていない場合は設定
[Environment]::SetEnvironmentVariable('OBSIDIAN_VAULT_PATH', 'C:\Users\mana4\Documents\Obsidian Vault', 'User')
```

### テンプレートが作成されない

```powershell
# 手動で実行
python setup_obsidian_templates.py
```

### n8nワークフローが動かない

1. n8nが起動しているか確認: `http://127.0.0.1:5678`
2. ワークフローが有効化されているか確認
3. 認証情報が設定されているか確認

---

## 🎉 完了！

これで「Obsidian → NotebookLM → Antigravity → ManaOS」の完全統合が開始できます。

**全部使う。役割を混ぜない。完璧を目指さない。**

---




















