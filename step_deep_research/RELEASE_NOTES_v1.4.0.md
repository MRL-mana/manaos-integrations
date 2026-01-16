# Release Notes: Step-Deep-Research v1.4.0

**リリース日**: 2025-01-28  
**バージョン**: 1.4.0  
**コードネーム**: "価値フェーズ"

---

## 🎉 このリリースについて

**Step-Deep-Research v1.4.0**は、「価値を取りに行くフェーズ」として、実務で即座に使える専門テンプレートと完成度確認機能を追加しました。

このバージョンで、**「完成品」としての体裁が整いました**。

---

## ✨ 新機能

### 1. 専門テンプレート3本

用途に応じて自動選択される専門テンプレートを追加：

#### 技術選定テンプレ

**キーワード**: 比較、選定、どちら、どっち、どれ、選択、メリデメ

**出力セクション**:
- 比較対象
- 機能/パフォーマンス/セキュリティ/コスト比較
- 推奨選択と理由
- 注意点・リスク
- 導入前の確認事項

**例**: 「RDPとTailscaleを比較して」

#### トラブル調査テンプレ

**キーワード**: エラー、問題、不具合、動かない、失敗、原因、対処

**出力セクション**:
- 症状/環境/再現条件
- 原因候補と根拠
- 切り分け手順
- 対処法（推奨/代替）
- 予防策

**例**: 「RDP接続がタイムアウトする原因を調べて」

#### 最新動向チェックテンプレ

**キーワード**: 最新、新機能、変更点、アップデート、動向、2026、2025

**出力セクション**:
- 変更点・アップデート
- 新機能・新仕様
- 非推奨・廃止予定
- 影響分析
- 今やること
- 不確実性の扱い

**例**: 「2026年のWindowsの変更点を調べて」

### 2. テンプレート自動選択

`TemplateRouter`がクエリから自動的にテンプレートタイプを検出し、適切なテンプレートを選択します。

### 3. 1分チェック

完成度確認の自動化スクリプトを追加：

- キャッシュが効くか
- 不明な情報を適切に処理できるか
- Critic Guardが動作しているか
- メトリクスが可視化されているか
- 次アクションが含まれているか

**使い方**:
```bash
python step_deep_research/one_minute_check.py
```

---

## 🔧 変更点

### Writer

- テンプレートタイプに応じた動的コンテンツ生成を実装
- `create_report()`メソッドに`user_query`パラメータを追加
- テンプレート別のヘルパーメソッドを追加

### Orchestrator

- `execute_job()`メソッドで`user_query`をWriterに渡すように変更

---

## 📁 追加ファイル

```
step_deep_research/
├── template_router.py                    # テンプレートルーター
├── one_minute_check.py                   # 1分チェック
├── templates/
│   ├── technical_selection_template.md   # 技術選定テンプレ
│   ├── troubleshooting_template.md       # トラブル調査テンプレ
│   └── latest_trends_template.md         # 最新動向テンプレ
├── CHANGELOG.md                          # 変更履歴
├── VERSION                               # バージョン情報
├── OFFICIAL_DOCUMENTATION.md             # 公式ドキュメント
└── RELEASE_NOTES_v1.4.0.md              # このファイル
```

---

## 🎯 このバージョンで実現した価値

### 即戦力ルート

- ✅ 3つの専門テンプレートで実務特化
- ✅ Intent Router経由で自動切替
- ✅ 使うたびに「うわ便利」になる設計

### 完成度

- ✅ 完全なドキュメント（README_COMPLETE.md）
- ✅ バージョン管理（CHANGELOG.md, VERSION）
- ✅ 公式認定（OFFICIAL_DOCUMENTATION.md）

---

## 📊 統計

- **追加ファイル数**: 7
- **追加コード行数**: 約500行
- **新機能数**: 3
- **変更モジュール数**: 2

---

## 🚀 アップグレード方法

v1.3.0からv1.4.0へのアップグレードは、**後方互換性があります**。

特別な移行作業は不要です。新しいファイルを追加するだけです。

```bash
# 新しいファイルを追加
git add step_deep_research/template_router.py
git add step_deep_research/one_minute_check.py
git add step_deep_research/templates/*.md
git add step_deep_research/CHANGELOG.md
git add step_deep_research/VERSION
git add step_deep_research/OFFICIAL_DOCUMENTATION.md
git add step_deep_research/RELEASE_NOTES_v1.4.0.md

# 設定ファイルの更新は不要
```

---

## 🐛 既知の問題

現在、既知の問題はありません。

---

## 🙏 謝辞

このバージョンの開発にあたり、ManaOSコミュニティのフィードバックとサポートに感謝します。

---

## 📝 次のステップ

### 短期（1-2週間）

- 社内ナレッジ統合強化
- カスタムテンプレート追加機能
- ダッシュボード可視化改善

### 中期（1-2ヶ月）

- Critic二段化（構造×内容）
- 失敗ログから自動カリキュラム再生成
- 収益化ルート（API提供、月額サービス）

---

**Step-Deep-Research v1.4.0**  
**「完成品」としての体裁が整いました** 🎉🔥

