# Step-Deep-Research クイックスタートガイド 🚀

**5分で始める専門調査員AI**

---

## 1. セットアップ（初回のみ）

### 前提条件

- ManaOSがインストール済み
- Ollamaが起動している（`http://127.0.0.1:11434`）
- SearXNGが起動している（`http://127.0.0.1:8080`、オプション）

### 設定確認

```bash
# 設定ファイルを確認
cat step_deep_research_config.json

# サービス起動
python step_deep_research_service.py
# または
.\start_step_deep_research.ps1
```

---

## 2. 基本的な使い方

### Pythonから使う

```python
from step_deep_research.orchestrator import StepDeepResearchOrchestrator
import json

# 設定読み込み
with open("step_deep_research_config.json") as f:
    config = json.load(f)

# オーケストレーター初期化
orchestrator = StepDeepResearchOrchestrator(config)

# ジョブ作成
job_id = orchestrator.create_job("RDPとTailscaleを比較して")

# 実行
result = orchestrator.execute_job(job_id)

# 結果確認
print(f"スコア: {result['score']}/30")
print(f"合格: {result['pass']}")
print(f"レポート: {result['report']}")
print(f"レポートパス: {result['report_path']}")
```

### API経由で使う

```bash
# ジョブ作成
curl -X POST http://127.0.0.1:5121/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"query": "RDPとTailscaleを比較して"}'

# レスポンス例
# {"job_id": "abc123", "status": "created"}

# ジョブ実行
curl -X POST http://127.0.0.1:5121/api/jobs/abc123/execute

# ジョブ状態確認
curl http://127.0.0.1:5121/api/jobs/abc123
```

---

## 3. 実用例

### 例1: 技術選定

```python
# 「RDPとTailscaleを比較して」
job_id = orchestrator.create_job("RDPとTailscaleを比較して")
result = orchestrator.execute_job(job_id)

# → technical_selection_template が自動選択される
# → 機能/パフォーマンス/セキュリティ/コスト比較が出力される
```

### 例2: トラブル調査

```python
# 「RDP接続がタイムアウトする原因を調べて」
job_id = orchestrator.create_job("RDP接続がタイムアウトする原因を調べて")
result = orchestrator.execute_job(job_id)

# → troubleshooting_template が自動選択される
# → 原因候補/切り分け手順/対処法が出力される
```

### 例3: 最新動向チェック

```python
# 「2026年のWindowsの変更点を調べて」
job_id = orchestrator.create_job("2026年のWindowsの変更点を調べて")
result = orchestrator.execute_job(job_id)

# → latest_trends_template が自動選択される
# → 変更点/影響分析/今やることが出力される
```

---

## 4. よくある使い方パターン

### パターン1: キャッシュを活用

```python
# 1回目: 通常実行
job_id1 = orchestrator.create_job("Pythonの非同期処理について調べて")
result1 = orchestrator.execute_job(job_id1, use_cache=False)

# 2回目: キャッシュヒット（高速・低コスト）
job_id2 = orchestrator.create_job("Pythonの非同期処理について調べて")
result2 = orchestrator.execute_job(job_id2, use_cache=True)

# result2['cached'] == True でキャッシュヒット確認
```

### パターン2: 予算を制限

```python
# 設定で予算を制限
config['orchestrator']['max_iterations'] = 5
config['orchestrator']['max_search_queries'] = 10
config['orchestrator']['token_budget'] = 20000

orchestrator = StepDeepResearchOrchestrator(config)
result = orchestrator.execute_job(job_id)

# 使用予算を確認
print(result['spent_budget'])
print(result['stop_reason'])
```

### パターン3: レポートをファイルに保存

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

## 5. トラブルシューティング

### 問題1: 検索が失敗する

```python
# フェイルセーフが自動的に部分レポートを生成
result = orchestrator.execute_job(job_id)

if result.get('fail_safe'):
    print(f"フェイルセーフ発動: {result['fail_message']}")
    print(f"部分レポート: {result['report']}")
```

### 問題2: Criticが常に不合格

```python
# Critic Guardのログを確認
# logs/step_deep_research/jobs/{job_id}.jsonl を確認

# 引用数を増やす
# → 検索結果を増やす（max_results_per_queryを増やす）
# → より多くのソースを参照する
```

### 問題3: コストが高い

```python
# 予算を制限
config['orchestrator']['max_iterations'] = 3
config['orchestrator']['max_search_queries'] = 5
config['orchestrator']['token_budget'] = 10000

# キャッシュを活用
result = orchestrator.execute_job(job_id, use_cache=True)
```

---

## 6. 完成度確認

### 1分チェック

```bash
python step_deep_research/one_minute_check.py
```

**チェック項目**:
- ✅ キャッシュが効く
- ✅ 不明な情報を適切に処理
- ✅ Critic Guardが動作
- ✅ メトリクスが可視化
- ✅ 次アクションが含まれる

### メトリクス確認

```python
from step_deep_research.metrics_dashboard import MetricsDashboard

dashboard = MetricsDashboard()
metrics = dashboard.calculate_metrics(days=7)
print(f"平均コスト: {metrics['metrics']['avg_cost_per_request']:.0f} トークン")
print(f"中央値レイテンシ: {metrics['metrics']['median_latency_sec']:.1f} 秒")
print(f"合格率: {1 - metrics['metrics']['critic_reject_rate']:.1%}")
```

---

## 7. 次のステップ

### 実務で使う

1. **技術選定**: 「AとBを比較して」→ 導入判断まで
2. **トラブル調査**: 「エラーの原因を調べて」→ 対処法まで
3. **最新動向**: 「最新の変更点を調べて」→ 今やることまで

### カスタマイズ

1. **テンプレート追加**: `step_deep_research/templates/`に追加
2. **プロンプト調整**: `step_deep_research/prompts/`を編集
3. **ルーブリック調整**: `step_deep_research/rubric_30_items.yaml`を編集

---

## 8. サポート

- **ドキュメント**: `README_COMPLETE.md`
- **プロジェクトサマリー**: `PROJECT_SUMMARY.md`
- **変更履歴**: `CHANGELOG.md`
- **公式ドキュメント**: `OFFICIAL_DOCUMENTATION.md`

---

**Step-Deep-Research v1.4.0**  
**すぐに使える専門調査員AI** 🎉🔥

