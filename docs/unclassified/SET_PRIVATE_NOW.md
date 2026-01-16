# ⚠️ 重要: リポジトリをプライベートに変更してください

現在、リポジトリが**公開**になっています。すぐにプライベートに変更してください。

## 🔒 プライベートに変更する手順

### 方法1: GitHubのWebインターフェース（推奨）

1. **リポジトリの設定ページにアクセス**
   ```
   https://github.com/MRL-mana/manaos-integrations/settings
   ```

2. **下にスクロールして「Danger Zone」セクションを見つける**

3. **「Change repository visibility」をクリック**

4. **「Change to private」を選択**

5. **確認ダイアログでリポジトリ名を入力して確認**

6. **「I understand, change repository visibility」をクリック**

### 方法2: GitHub CLI（コマンドライン）

```bash
gh repo edit MRL-mana/manaos-integrations --visibility private --accept-visibility-change-consequences
```

## ✅ 変更後の確認

変更後、以下で確認できます:

```bash
python verify_repo_setup.py
```

または、GitHubのリポジトリページで確認:
- リポジトリ名の横に「Private」と表示されていればOK

## 📋 確認事項

変更後、以下を確認してください:

- [ ] リポジトリがプライベートになっている
- [ ] `.env`ファイルがコミットされていない
- [ ] 認証情報がコードに含まれていない

---

**すぐにプライベートに変更してください！** 🔒






















