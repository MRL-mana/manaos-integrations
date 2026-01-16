# Step-Deep-Research 活用ガイド 📚

**実務で使うための実践的なガイド**

---

## 📖 目次

1. [クイックスタート](#クイックスタート)
2. [実用例](#実用例)
3. [よくある使い方パターン](#よくある使い方パターン)
4. [トラブルシューティング](#トラブルシューティング)
5. [カスタマイズ](#カスタマイズ)
6. [ベストプラクティス](#ベストプラクティス)

---

## クイックスタート

### 5分で始める

```bash
# 1. 設定確認
cat step_deep_research_config.json

# 2. サービス起動
python step_deep_research_service.py

# 3. 基本的な使い方の例を実行
python step_deep_research/examples/basic_usage.py

# 4. 1分チェック
python step_deep_research/examples/one_minute_check_example.py
```

詳細は `QUICK_START.md` を参照してください。

---

## 実用例

### 例1: 技術選定

**シナリオ**: RDPとTailscaleのどちらを選ぶべきか判断したい

```python
from step_deep_research.orchestrator import StepDeepResearchOrchestrator
import json

with open("step_deep_research_config.json") as f:
    config = json.load(f)

orchestrator = StepDeepResearchOrchestrator(config)

# ジョブ作成・実行
job_id = orchestrator.create_job("RDPとTailscaleを比較して")
result = orchestrator.execute_job(job_id)

# 結果確認
print(f"スコア: {result['score']}/30")
print(f"合格: {result['pass']}")
print(f"レポート: {result['report_path']}")
```

**出力**: 技術選定テンプレートが自動選択され、機能/パフォーマンス/セキュリティ/コスト比較が出力されます。

### 例2: トラブル調査

**シナリオ**: RDP接続がタイムアウトする原因を調べたい

```python
job_id = orchestrator.create_job("RDP接続がタイムアウトする原因を調べて")
result = orchestrator.execute_job(job_id)
```

**出力**: トラブル調査テンプレートが自動選択され、原因候補/切り分け手順/対処法が出力されます。

### 例3: 最新動向チェック

**シナリオ**: 2026年のWindowsの変更点を確認したい

```python
job_id = orchestrator.create_job("2026年のWindowsの変更点を調べて")
result = orchestrator.execute_job(job_id)
```

**出力**: 最新動向チェックテンプレートが自動選択され、変更点/影響分析/今やることが出力されます。

---

## よくある使い方パターン

### パターン1: キャッシュを活用

**目的**: 同じ質問を繰り返す場合、コストを削減

```python
# 1回目: 通常実行
job_id1 = orchestrator.create_job("Pythonの非同期処理について調べて")
result1 = orchestrator.execute_job(job_id1, use_cache=False)

# 2回目: キャッシュヒット（高速・低コスト）
job_id2 = orchestrator.create_job("Pythonの非同期処理について調べて")
result2 = orchestrator.execute_job(job_id2, use_cache=True)

if result2.get('cached'):
    print("✅ キャッシュヒット！高速・低コストで結果を取得")
```

### パターン2: 予算を制限

**目的**: コストを抑えたい場合

```python
# 予算を制限
config['orchestrator']['max_iterations'] = 3
config['orchestrator']['max_search_queries'] = 5
config['orchestrator']['token_budget'] = 10000

orchestrator = StepDeepResearchOrchestrator(config)
result = orchestrator.execute_job(job_id)

# 使用予算を確認
print(f"使用予算: {result['spent_budget']}")
print(f"停止理由: {result.get('stop_reason', 'completed')}")
```

### パターン3: レポートを後で確認

**目的**: レポートをファイルに保存して後で確認

```python
result = orchestrator.execute_job(job_id)

# レポートは自動保存される
report_path = result['report_path']
print(f"レポート: {report_path}")

# 手動で読み込む
with open(report_path, 'r', encoding='utf-8') as f:
    report_content = f.read()
```

---

## トラブルシューティング

### 問題1: 検索が失敗する

**症状**: 検索結果が0件、またはエラーが発生

**対処**:
- フェイルセーフが自動的に部分レポートを生成します
- `result.get('fail_safe')`で確認できます

```python
result = orchestrator.execute_job(job_id)

if result.get('fail_safe'):
    print(f"フェイルセーフ発動: {result['fail_message']}")
    print(f"部分レポート: {result['report']}")
```

### 問題2: Criticが常に不合格

**症状**: スコアが低く、常に不合格になる

**対処**:
- 引用数を増やす（`max_results_per_query`を増やす）
- より多くのソースを参照する
- Critic Guardのログを確認（`logs/step_deep_research/jobs/{job_id}.jsonl`）

### 問題3: コストが高い

**症状**: トークン使用量が多い

**対処**:
- 予算を制限（`max_iterations`, `max_search_queries`, `token_budget`）
- キャッシュを活用（`use_cache=True`）
- より具体的なクエリを使用（調査範囲を狭める）

---

## カスタマイズ

### テンプレート追加

1. `step_deep_research/templates/`に新しいテンプレートを追加
2. `template_router.py`に検出ロジックを追加

### プロンプト調整

1. `step_deep_research/prompts/`のプロンプトを編集
2. 各エージェントの動作を調整

### ルーブリック調整

1. `step_deep_research/rubric_30_items.yaml`を編集
2. 評価基準を調整

---

## ベストプラクティス

### 1. クエリの書き方

**良い例**:
- 「RDPとTailscaleを比較して」
- 「RDP接続がタイムアウトする原因を調べて」
- 「2026年のWindowsの変更点を調べて」

**悪い例**:
- 「RDPについて」（範囲が広すぎる）
- 「調べて」（何を調べるか不明確）

### 2. 予算管理

- 初回は予算を制限して動作確認
- 本番運用では適切な予算を設定
- キャッシュを活用してコスト削減

### 3. メトリクス監視

- 定期的にメトリクスを確認
- 目標値との比較
- 問題があれば早期に対処

```python
from step_deep_research.metrics_dashboard import MetricsDashboard

dashboard = MetricsDashboard()
metrics = dashboard.calculate_metrics(days=7)
print(metrics)
```

### 4. ログ確認

- ジョブログを確認（`logs/step_deep_research/jobs/{job_id}.jsonl`）
- エラーがあればログを確認
- パフォーマンス問題があればログを分析

---

## サンプルコード

詳細なサンプルコードは `step_deep_research/examples/` を参照してください：

- `basic_usage.py`: 基本的な使い方の例
- `metrics_check.py`: メトリクス確認の例
- `one_minute_check_example.py`: 1分チェックの例

---

## サポート

- **クイックスタート**: `QUICK_START.md`
- **完全版README**: `README_COMPLETE.md`
- **プロジェクトサマリー**: `PROJECT_SUMMARY.md`
- **公式ドキュメント**: `OFFICIAL_DOCUMENTATION.md`

---

**Step-Deep-Research v1.4.0**  
**実務で使える専門調査員AI** 🎉🔥

