# System 3 外部情報収集パイプライン セットアップガイド

**作成日**: 2026-01-05  
**状態**: 実装完了・設定必要

---

## ✅ 実装完了内容

### 1. Web検索エージェント
- **SerpAPI統合**: APIキー設定で有効化
- **DuckDuckGo fallback**: APIキー不要（制限あり）

### 2. GitHub探索モジュール
- **GitHub API統合**: 動作確認済み
- **リポジトリ検索・実装例収集**: 動作中

### 3. 要約エンジン
- **検索結果の自動要約**: 実装済み
- **インサイト抽出**: 実装済み

### 4. Obsidian統合
- **自動ノート生成**: 実装済み
- **カテゴリ別整理**: 実装済み

### 5. 深夜バッチスケジューラ
- **毎日03:00自動実行**: 登録済み

---

## 🔧 セットアップ手順

### Step 1: SERPAPI_KEYの設定（Web検索を有効化）

#### 方法1: 環境変数として設定（推奨）

**PowerShell（現在のセッションのみ）:**
```powershell
$env:SERPAPI_KEY = "your_serpapi_key_here"
```

**PowerShell（永続的）:**
```powershell
[System.Environment]::SetEnvironmentVariable("SERPAPI_KEY", "your_serpapi_key_here", "User")
```

**Windows環境変数設定（GUI）:**
1. Windowsキー → 「環境変数」を検索
2. 「環境変数を編集」を開く
3. 「ユーザー環境変数」で「新規」をクリック
4. 変数名: `SERPAPI_KEY`
5. 変数値: あなたのSerpAPIキー
6. OKをクリック

#### 方法2: スクリプト内で設定（非推奨）

`system3_external_learning.py`の先頭に追加：
```python
import os
os.environ["SERPAPI_KEY"] = "your_serpapi_key_here"
```

**⚠️ 注意**: この方法はセキュリティリスクがあります。環境変数を使用してください。

#### SerpAPIキーの取得方法

1. https://serpapi.com/ にアクセス
2. アカウントを作成（無料プランあり）
3. ダッシュボードからAPIキーを取得

---

### Step 2: GITHUB_TOKENの設定（GitHub検索を強化）

**PowerShell（永続的）:**
```powershell
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN", "your_github_token_here", "User")
```

**GitHubトークンの取得方法:**
1. https://github.com/settings/tokens にアクセス
2. 「Generate new token (classic)」をクリック
3. スコープ: `public_repo` にチェック
4. トークンを生成してコピー

**⚠️ 注意**: トークンは一度しか表示されません。安全に保管してください。

---

### Step 3: 生成レポートの確認

**レポートの場所:**
```
C:\Users\mana4\Documents\Obsidian Vault\ManaOS\System\ExternalLearning\System3_ExternalLearning_YYYY-MM-DD.md
```

**Obsidianで確認:**
1. Obsidianを開く
2. `ManaOS/System/ExternalLearning/` フォルダを開く
3. 最新のレポートファイルを確認

**レポートの内容:**
- Web検索結果（上位5件）
- GitHub実装例（上位5件）
- 要約とインサイト
- System 3学習への提案

---

### Step 4: System 3への統合

#### 4-1. レポートから有用な情報を抽出

**手動統合（推奨）:**
1. レポートをObsidianで開く
2. 有用な実装例や手法を確認
3. System 3のコードに反映

**自動統合（将来実装予定）:**
- レポートをRAGシステムに取り込み
- System 3が自動的に学習
- 実装パターンを自動適用

#### 4-2. 学習システムへの統合

**現在の統合方法:**
- レポートはObsidianに保存
- Learning System APIがObsidianを参照可能
- 手動でLearning Systemに記録

**将来の自動統合:**
- レポート生成時に自動的にLearning Systemに記録
- RAGシステムに自動取り込み
- System 3が自動的に学習

---

## 📊 動作確認

### テスト実行

```powershell
python system3_external_learning.py
```

### 期待される出力

```
System 3 External Learning Pipeline - 2026-01-05 XX:XX:XX
============================================================

[1/11] Searching: AI self improvement architecture
  Category: learning, Language: en
  Web results: 5
  GitHub results: 5

...

✅ External Learningレポートを生成しました: ...
   検索クエリ数: 11
   結果あり: 6
```

### スケジュールタスク確認

```powershell
Get-ScheduledTask -TaskName "System3_External_Learning"
```

---

## 🔍 トラブルシューティング

### Web検索が動作しない

**症状**: `Web results: 0`

**原因**: SERPAPI_KEYが設定されていない、または無効

**対処**:
1. 環境変数を確認: `$env:SERPAPI_KEY`
2. SerpAPIキーが正しいか確認
3. DuckDuckGo fallbackが動作するか確認（APIキー不要）

### GitHub検索が動作しない

**症状**: `GitHub results: 0`

**原因**: GITHUB_TOKENが設定されていない、またはレート制限

**対処**:
1. 環境変数を確認: `$env:GITHUB_TOKEN`
2. GitHubトークンが有効か確認
3. レート制限を確認（1時間あたり60リクエスト）

### レポートが生成されない

**症状**: レポートファイルが見つからない

**対処**:
1. スクリプトを手動実行してエラーを確認
2. Obsidian Vaultのパスが正しいか確認
3. 書き込み権限があるか確認

---

## 📝 次のステップ

### 短期（1週間以内）

1. ✅ SERPAPI_KEYを設定してWeb検索を有効化
2. ✅ 生成されたレポートをObsidianで確認
3. ✅ 有用な情報をSystem 3に手動統合

### 中期（1ヶ月以内）

1. レポートから自動的にLearning Systemに記録
2. RAGシステムに自動取り込み
3. System 3が自動的に学習

### 長期（3ヶ月以内）

1. 外部情報から自動的に実装パターンを抽出
2. System 3が自動的にコード改善を提案
3. 完全自動化された学習ループ

---

## 🎯 まとめ

**現在の状態:**
- ✅ 実装完了
- ✅ スケジュール登録済み
- ⚠️ SERPAPI_KEY設定が必要（Web検索を有効化）
- ✅ GitHub検索は動作中
- ✅ レポート生成は動作中

**次のアクション:**
1. SERPAPI_KEYを設定
2. 生成されたレポートを確認
3. 有用な情報をSystem 3に統合

**System 3は外部から自動的に学習し、知識を進化させます！**





















