# SERPAPI_KEY設定ガイド

**作成日**: 2026-01-05  
**目的**: System 3外部情報収集パイプラインのWeb検索機能を有効化

---

## 📋 設定方法

### 方法1: PowerShellで直接設定（推奨）

**永続的な設定（推奨）:**
```powershell
[System.Environment]::SetEnvironmentVariable('SERPAPI_KEY', 'your_key_here', 'User')
```

**現在のセッションにも反映:**
```powershell
$env:SERPAPI_KEY = 'your_key_here'
```

**確認:**
```powershell
$env:SERPAPI_KEY
```

---

### 方法2: Windows環境変数設定（GUI）

1. **Windowsキー** → 「**環境変数**」を検索
2. 「**環境変数を編集**」を開く
3. 「**ユーザー環境変数**」セクションで「**新規**」をクリック
4. **変数名**: `SERPAPI_KEY`
5. **変数値**: あなたのSerpAPIキー
6. **OK**をクリック

**注意**: 設定後、PowerShellを再起動する必要があります。

---

### 方法3: スクリプトで設定（APIキーを引数で指定）

```powershell
.\setup_serpapi_key.ps1 -ApiKey 'your_key_here'
```

---

## 🔑 SerpAPIキーの取得方法

1. **https://serpapi.com/** にアクセス
2. **アカウントを作成**（無料プランあり）
   - 無料プラン: 100検索/月
   - 有料プラン: より多くの検索が可能
3. **ダッシュボードにログイン**
4. **APIキーを取得**
   - ダッシュボードの「API Key」セクションからコピー

---

## ✅ 設定確認

**PowerShellで確認:**
```powershell
$env:SERPAPI_KEY
```

**設定されていれば、APIキーが表示されます。**

**設定されていなければ、何も表示されません。**

---

## 🧪 テスト実行

**設定後、外部学習パイプラインをテスト実行:**
```powershell
python system3_external_learning.py
```

**期待される動作:**
- `Web results: 5` など、Web検索結果が表示される
- レポートにWeb検索結果が含まれる

**SERPAPI_KEYが設定されていない場合:**
- `Web results: 0` と表示される
- DuckDuckGo fallbackが使用される（制限あり）

---

## 📝 注意事項

1. **APIキーの管理**
   - APIキーは機密情報です
   - Gitにコミットしないでください
   - 環境変数として管理することを推奨

2. **無料プランの制限**
   - 100検索/月
   - レート制限あり

3. **設定の反映**
   - 環境変数を設定した後、PowerShellを再起動する必要がある場合があります
   - または、`$env:SERPAPI_KEY = 'your_key'`で現在のセッションに反映

---

## 🎯 次のステップ

1. ✅ SERPAPI_KEYを設定
2. ✅ テスト実行で動作確認
3. ✅ 毎日03:00の自動実行でWeb検索が有効化される

**System 3の外部情報収集パイプラインが完全に動作します！**





















