# Rows APIキー設定ガイド

## 📋 Rows APIキーの取得方法

### ステップ1: Rowsにログイン

1. [Rows公式サイト](https://rows.com)にアクセス
2. アカウントにログイン（アカウントがない場合は作成）

### ステップ2: APIキーを生成

1. 左側のパネル下部の**Settings**をクリック
   - ⚠️ **注意**: ワークスペースのオーナーまたは管理者のみがアクセス可能です
2. 左サイドバーから**Rows API**を選択
3. **Generate API**ボタンをクリック
4. 生成されたAPIキーをコピー
   - ⚠️ **重要**: APIキーは作成時に一度だけ表示されます
   - 安全な場所（パスワードマネージャーなど）に保存してください
   - 紛失した場合は削除して新しいキーを生成する必要があります

### ステップ3: .envファイルに設定

`.env`ファイルに以下を追加：

```bash
ROWS_API_KEY=your_rows_api_key_here
```

**例**:
```bash
ROWS_API_KEY=rows_api_xxxxxxxxxxxxxxxxxxxxx
```

### ステップ4: 設定確認

```powershell
# 設定を確認
python check_integration_status.py
```

または

```powershell
# 直接確認
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('OK' if os.getenv('ROWS_API_KEY') else 'NG')"
```

---

## 🔧 自動設定スクリプト

既にAPIキーをお持ちの場合は、以下のスクリプトで設定できます：

```powershell
# PowerShellで実行
python setup_rows_api_key.py
```

または、手動で`.env`ファイルを編集：

```powershell
notepad .env
```

---

## ✅ 設定後の確認

1. **統合システムの状態確認**:
   ```powershell
   python check_integration_status.py
   ```

2. **Rows統合のテスト**:
   ```powershell
   python test_rows_integration.py
   ```

---

## 📚 参考リンク

- [Rows API ドキュメント](https://rows.com/docs/using-rows-api)
- [Rows統合ガイド](./docs/integration/ROWS_INTEGRATION.md)
- [Rows クイックスタート](./docs/guides/ROWS_QUICK_START.md)

---

## 🎯 次のステップ

Rows APIキーを設定したら：

1. 統合APIサーバーを再起動
2. Rows統合の動作確認
3. スプレッドシート作成・データ送信のテスト

---

**作成日**: 2026-01-28  
**状態**: 設定ガイド完成

Rows APIキーを設定して、Rows統合を有効化しましょう！
