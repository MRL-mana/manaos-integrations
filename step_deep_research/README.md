# Step-Deep-Research: 実装ガイド

**ManaOS版 専門調査員AI**

---

## 🚀 クイックスタート

### 1. 設定確認

```bash
# 設定ファイルの確認
cat step_deep_research_config.json
```

### 2. ディレクトリ構造の確認

```
step_deep_research/
├── __init__.py          # パッケージ初期化
├── orchestrator.py       # オーケストレーター
├── planner.py            # 計画係
├── research_loop.py      # 調査ループ
│   ├── searcher.py      # 検索係
│   ├── reader.py        # 要点抽出係
│   ├── verifier.py      # 検証係
│   └── writer.py       # 報告書係
├── critic.py            # 採点AI
├── rubric.py            # ルーブリック定義
├── schemas.py           # データスキーマ
├── utils.py             # ユーティリティ
├── prompts/            # プロンプトテンプレート
│   ├── planner_prompt.txt
│   ├── reader_prompt.txt
│   ├── verifier_prompt.txt
│   └── critic_prompt.txt
└── templates/          # レポートテンプレート
    └── report_template.md
```

### 3. 実装順序（MVP）

#### Day 1: 基本フロー

1. **`schemas.py`** ✅ 完了
2. **`orchestrator.py`** - ジョブ管理とフロー制御
3. **`planner.py`** - 計画作成
4. **`research_loop.py`** - 調査ループ（Searcher, Writerのみ）
5. **`critic.py`** - 採点機能

#### Day 2: 強化機能

1. **`reader.py`** - 引用抽出強化
2. **`verifier.py`** - 矛盾検出
3. 引用フォーマット標準化

#### Day 3: 学習データ生成

1. 良いレポートの自動検出
2. 逆算データ生成
3. 学習データストック

---

## 📝 実装時の注意点

### 既存モジュールの活用

```python
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler
from llm_optimization import LLMOptimizer
```

### 設定ファイルの読み込み

```python
import json
from pathlib import Path

config_path = Path("step_deep_research_config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)
```

### ログの保存

```python
from datetime import datetime
import json

log_file = Path("logs/step_deep_research/jobs") / f"{job_id}.jsonl"
checkpoint = {
    "timestamp": datetime.now().isoformat(),
    "status": "researching",
    "budget": {"used_tokens": 1000}
}
with open(log_file, "a", encoding="utf-8") as f:
    f.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")
```

---

## 🧪 テスト例

### 簡単な調査依頼

```python
from step_deep_research.orchestrator import StepDeepResearchOrchestrator

orchestrator = StepDeepResearchOrchestrator(config)
job_id = orchestrator.create_job("Pythonの非同期処理について調べて")
result = orchestrator.execute_job(job_id)

print(f"Score: {result['score']}/20")
print(f"Pass: {result['pass']}")
```

---

## 📚 参考資料

- [設計図](../step_deep_research_design.md)
- [ルーブリック定義](./rubric_20_items.yaml)
- [スキーマ定義](./schemas.py)

---

**実装準備完了！** 🎉



