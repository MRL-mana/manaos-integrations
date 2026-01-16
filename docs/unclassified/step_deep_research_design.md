# ManaOS版 Step-Deep-Research：完全設計図

**作成日**: 2025-01-28  
**バージョン**: 1.0.0  
**状態**: 設計完了（実装準備完了）

---

## 📋 目次

1. [ディレクトリ構成](#ディレクトリ構成)
2. [JSON/YAMLスキーマ](#jsonyamlスキーマ)
3. [疑似コード（実装テンプレート）](#疑似コード実装テンプレート)
4. [統合ポイント](#統合ポイント)
5. [MVP実装ロードマップ](#mvp実装ロードマップ)

---

## 📁 ディレクトリ構成

```
manaos_integrations/
├── step_deep_research/                    # 新規ディレクトリ
│   ├── __init__.py
│   ├── orchestrator.py                    # (A) Orchestrator（司令塔）
│   ├── planner.py                         # (B) Planner Agent（計画係）
│   ├── research_loop.py                   # (C) Research Loop（調査ループ）
│   │   ├── searcher.py                    # (C1) Searcher（検索係）
│   │   ├── reader.py                      # (C2) Reader（要点抽出係）
│   │   ├── verifier.py                    # (C3) Verifier（検証係）
│   │   └── writer.py                      # (C4) Writer（報告書係）
│   ├── critic.py                          # (D) Critic（採点AI）
│   ├── rubric.py                          # ルーブリック定義
│   ├── schemas.py                         # データスキーマ定義
│   └── utils.py                           # ユーティリティ
│
├── step_deep_research_config.json         # 設定ファイル
├── step_deep_research_schemas.yaml        # YAMLスキーマ定義
│
└── logs/
    └── step_deep_research/                # ログ保存先
        ├── jobs/                          # ジョブログ（JSONL）
        ├── reports/                       # 生成レポート
        └── artifacts/                    # 中間成果物
```

---

## 📄 JSON/YAMLスキーマ

### 1. 設定ファイル: `step_deep_research_config.json`

```json
{
  "service_id": "5120",
  "service_name": "Step Deep Research",
  "version": "1.0.0",
  
  "orchestrator": {
    "max_budget_tokens": 50000,
    "max_search_queries": 20,
    "max_time_minutes": 60,
    "checkpoint_interval_seconds": 30,
    "retry_strategy": {
      "max_retries": 3,
      "retry_delay_seconds": 5,
      "backoff_multiplier": 2.0
    }
  },
  
  "planner": {
    "ollama_url": "http://localhost:11434",
    "model": "llama3.2:3b",
    "max_todo_items": 15,
    "planning_prompt_template": "planner_prompt.txt"
  },
  
  "research_loop": {
    "max_iterations": 10,
    "iteration_timeout_seconds": 300,
    
    "searcher": {
      "sources": ["web", "rag", "docs", "pdf"],
      "max_results_per_query": 10,
      "web_search_provider": "searxng",
      "searxng_url": "http://localhost:8080",
      "rag_api_url": "http://localhost:5103"
    },
    
    "reader": {
      "ollama_url": "http://localhost:11434",
      "model": "llama3.2:3b",
      "max_chunk_size": 2000,
      "extraction_prompt_template": "reader_prompt.txt"
    },
    
    "verifier": {
      "ollama_url": "http://localhost:11434",
      "model": "llama3.2:3b",
      "contradiction_threshold": 0.7,
      "verification_prompt_template": "verifier_prompt.txt"
    },
    
    "writer": {
      "ollama_url": "http://localhost:11434",
      "model": "qwen2.5:7b",
      "report_template": "report_template.md",
      "citation_format": "markdown"
    }
  },
  
  "critic": {
    "ollama_url": "http://localhost:11434",
    "model": "llama3.2:3b",
    "rubric_file": "rubric_20_items.yaml",
    "min_pass_score": 14,
    "max_iterations": 3,
    "critic_prompt_template": "critic_prompt.txt"
  },
  
  "trinity_integration": {
    "remi_role": ["planner", "writer"],
    "luna_role": ["searcher", "reader"],
    "mina_role": ["verifier", "critic_assistant"]
  },
  
  "memory_integration": {
    "rag_api_url": "http://localhost:5103",
    "auto_save_reports": true,
    "auto_save_failures": true,
    "learning_data_path": "logs/step_deep_research/learning_data/"
  }
}
```

### 2. Planner出力スキーマ: `planner_output_schema.yaml`

```yaml
goal: string                    # 調査目標
success_criteria:              # 成功条件
  - criterion: string
    priority: "high" | "medium" | "low"
    measurable: boolean

todo:                          # タスクリスト
  - step: string               # ステップ番号
    description: string        # タスク説明
    tool: "search" | "rag" | "docs" | "pdf" | "none"
    expected_output: string    # 期待される出力
    dependencies: [string]     # 依存タスク（step番号）
    priority: "high" | "medium" | "low"

risks:                         # リスク
  - risk: string
    mitigation: string

estimated_time_minutes: integer
estimated_cost_tokens: integer
```

### 3. Critic出力スキーマ: `critic_output_schema.yaml`

```yaml
score: integer                 # 総合スコア（0-20）
pass: boolean                  # 合格判定

rubric_scores:                 # 項目別スコア
  citations:
    score: integer             # 0-8
    details:
      - item: string
        passed: boolean
        note: string
  
  logic:
    score: integer             # 0-7
    details:
      - item: string
        passed: boolean
        note: string
  
  practicality:
    score: integer             # 0-5
    details:
      - item: string
        passed: boolean
        note: string

fail_flags: [string]          # 失敗フラグ
fix_requests: [string]         # 修正要求
```

### 4. ルーブリック定義: `rubric_20_items.yaml`

```yaml
rubric:
  version: "1.0"
  total_items: 20
  min_pass_score: 14
  
  citations:                   # 出典・引用（8項目）
    items:
      - id: "cite_001"
        name: "主要主張に出典がある"
        weight: 1
        description: "レポート内の主要な主張には必ず出典が付いている"
      
      - id: "cite_002"
        name: "引用が主張に対応している"
        weight: 1
        description: "引用された内容が主張を裏付けている"
      
      - id: "cite_003"
        name: "出典が一次情報寄り"
        weight: 1
        description: "公式ドキュメント、論文、規格書などの一次情報を優先"
      
      - id: "cite_004"
        name: "出典が少なすぎない"
        weight: 1
        description: "最低N件（N=3）以上の出典がある"
      
      - id: "cite_005"
        name: "出典が偏りすぎない"
        weight: 1
        description: "単一のソースに依存していない"
      
      - id: "cite_006"
        name: "日付が古すぎる情報に注意書き"
        weight: 1
        description: "3年以上古い情報には注意書きがある"
      
      - id: "cite_007"
        name: "推測と事実を区別"
        weight: 1
        description: "推測（inference）と事実（fact）が明確に区別されている"
      
      - id: "cite_008"
        name: "リンク切れ/参照不能なし"
        weight: 1
        description: "すべての出典が参照可能である"
  
  logic:                        # 論理・整合（7項目）
    items:
      - id: "logic_001"
        name: "結論が明確"
        weight: 1
        description: "レポートの結論が明確に述べられている"
      
      - id: "logic_002"
        name: "結論→根拠のつながりが明示"
        weight: 1
        description: "結論と根拠の論理的なつながりが明確"
      
      - id: "logic_003"
        name: "反証候補を1つ以上検討"
        weight: 1
        description: "反対意見や反証候補が検討されている"
      
      - id: "logic_004"
        name: "矛盾がない"
        weight: 1
        description: "レポート内に矛盾する記述がない"
      
      - id: "logic_005"
        name: "用語定義がブレない"
        weight: 1
        description: "同じ用語が一貫して使用されている"
      
      - id: "logic_006"
        name: "範囲（スコープ）が明確"
        weight: 1
        description: "調査範囲が明確に定義されている"
      
      - id: "logic_007"
        name: "できる/できないが曖昧じゃない"
        weight: 1
        description: "可能/不可能が明確に述べられている"
  
  practicality:                # 実務性（5項目）
    items:
      - id: "prac_001"
        name: "次アクションが書いてある"
        weight: 1
        description: "次のステップやアクションが明確"
      
      - id: "prac_002"
        name: "コスト/時間/リスクの触れ方がある"
        weight: 1
        description: "実装時のコスト、時間、リスクが触れられている"
      
      - id: "prac_003"
        name: "実装に落ちる形（手順/設定/構成）"
        weight: 1
        description: "具体的な実装手順や設定が含まれている"
      
      - id: "prac_004"
        name: "不確実性の扱いがある"
        weight: 1
        description: "不確実な部分が明示されている"
      
      - id: "prac_005"
        name: "読み手の前提（初心者/上級）を合わせてる"
        weight: 1
        description: "対象読者に合わせた説明レベル"
```

### 5. ジョブログスキーマ: `job_log_schema.json`

```json
{
  "job_id": "string",
  "created_at": "ISO8601 datetime",
  "user_query": "string",
  "status": "pending" | "planning" | "researching" | "writing" | "critiquing" | "completed" | "failed",
  
  "orchestrator": {
    "budget_used_tokens": 0,
    "budget_used_searches": 0,
    "elapsed_time_seconds": 0,
    "checkpoints": []
  },
  
  "planner": {
    "plan": {},  // planner_output_schema.yaml の内容
    "created_at": "ISO8601 datetime"
  },
  
  "research_loop": {
    "iterations": [
      {
        "iteration": 1,
        "timestamp": "ISO8601 datetime",
        "searcher": {
          "queries": ["string"],
          "results_count": 0,
          "sources": []
        },
        "reader": {
          "extracted_citations": [],
          "summaries": []
        },
        "verifier": {
          "contradictions_found": [],
          "verification_results": []
        }
      }
    ]
  },
  
  "writer": {
    "report": "string (markdown)",
    "citations": [],
    "created_at": "ISO8601 datetime"
  },
  
  "critic": {
    "iterations": [
      {
        "iteration": 1,
        "score": 0,
        "pass": false,
        "rubric_scores": {},
        "fix_requests": []
      }
    ],
    "final_score": 0,
    "final_pass": false
  },
  
  "final_report_path": "string",
  "artifacts": []
}
```

---

## 💻 疑似コード（実装テンプレート）

### 1. Orchestrator（司令塔）

```python
# step_deep_research/orchestrator.py

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import json
import uuid
from pathlib import Path

from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler

logger = get_logger(__name__)
error_handler = ManaOSErrorHandler("StepDeepResearchOrchestrator")


@dataclass
class JobBudget:
    """予算管理"""
    max_tokens: int
    max_searches: int
    max_time_minutes: int
    used_tokens: int = 0
    used_searches: int = 0
    elapsed_seconds: float = 0.0


@dataclass
class JobState:
    """ジョブ状態"""
    job_id: str
    user_query: str
    status: str = "pending"
    budget: JobBudget = field(default_factory=lambda: JobBudget(50000, 20, 60))
    checkpoints: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class StepDeepResearchOrchestrator:
    """Step-Deep-Research オーケストレーター"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.log_dir = Path("logs/step_deep_research/jobs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # コンポーネント初期化
        from .planner import PlannerAgent
        from .research_loop import ResearchLoop
        from .critic import CriticAgent
        
        self.planner = PlannerAgent(config["planner"])
        self.research_loop = ResearchLoop(config["research_loop"])
        self.critic = CriticAgent(config["critic"])
    
    def create_job(self, user_query: str) -> str:
        """ジョブ作成"""
        job_id = str(uuid.uuid4())
        job_state = JobState(
            job_id=job_id,
            user_query=user_query
        )
        
        # ログファイル作成
        log_file = self.log_dir / f"{job_id}.jsonl"
        self._save_checkpoint(job_state, log_file)
        
        logger.info(f"Job created: {job_id}")
        return job_id
    
    def execute_job(self, job_id: str) -> Dict[str, Any]:
        """ジョブ実行"""
        job_state = self._load_job(job_id)
        
        try:
            # 1. Planning
            job_state.status = "planning"
            self._save_checkpoint(job_state)
            plan = self.planner.create_plan(job_state.user_query)
            job_state.planner_output = plan
            
            # 予算チェック
            if not self._check_budget(job_state):
                raise Exception("Budget exceeded")
            
            # 2. Research Loop
            job_state.status = "researching"
            self._save_checkpoint(job_state)
            research_results = self.research_loop.execute(
                plan=plan,
                budget=job_state.budget
            )
            job_state.research_output = research_results
            
            # 3. Writing
            job_state.status = "writing"
            self._save_checkpoint(job_state)
            report = self.research_loop.writer.create_report(
                research_results=research_results,
                plan=plan
            )
            job_state.writer_output = report
            
            # 4. Critiquing
            job_state.status = "critiquing"
            self._save_checkpoint(job_state)
            critique_result = self.critic.evaluate(report)
            job_state.critic_output = critique_result
            
            # 5. 合格判定
            if critique_result["pass"]:
                job_state.status = "completed"
                self._save_final_report(job_id, report)
            else:
                # 差し戻し処理（最大3回）
                if critique_result["iteration"] < 3:
                    # Writerに修正依頼
                    fix_requests = critique_result["fix_requests"]
                    report = self.research_loop.writer.revise(
                        report=report,
                        fix_requests=fix_requests
                    )
                    # 再評価
                    critique_result = self.critic.evaluate(report)
                    job_state.critic_output = critique_result
            
            job_state.status = "completed"
            self._save_checkpoint(job_state)
            
            return {
                "job_id": job_id,
                "status": job_state.status,
                "report": report,
                "score": critique_result["score"],
                "pass": critique_result["pass"]
            }
            
        except Exception as e:
            job_state.status = "failed"
            error_handler.handle_error(e, "Job execution failed")
            self._save_checkpoint(job_state)
            raise
    
    def _check_budget(self, job_state: JobState) -> bool:
        """予算チェック"""
        budget = job_state.budget
        return (
            budget.used_tokens < budget.max_tokens and
            budget.used_searches < budget.max_searches and
            budget.elapsed_seconds < budget.max_time_minutes * 60
        )
    
    def _save_checkpoint(self, job_state: JobState, log_file: Optional[Path] = None):
        """チェックポイント保存"""
        if log_file is None:
            log_file = self.log_dir / f"{job_state.job_id}.jsonl"
        
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "status": job_state.status,
            "budget": {
                "used_tokens": job_state.budget.used_tokens,
                "used_searches": job_state.budget.used_searches,
                "elapsed_seconds": job_state.budget.elapsed_seconds
            }
        }
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")
    
    def _load_job(self, job_id: str) -> JobState:
        """ジョブ読み込み"""
        log_file = self.log_dir / f"{job_id}.jsonl"
        # 実装: JSONLから状態を復元
        # ...
        pass
    
    def _save_final_report(self, job_id: str, report: str):
        """最終レポート保存"""
        report_dir = Path("logs/step_deep_research/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = report_dir / f"{job_id}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
```

### 2. Planner Agent（計画係）

```python
# step_deep_research/planner.py

from typing import Dict, Any, List
import yaml

from manaos_logger import get_logger
from llm_optimization import LLMOptimizer

logger = get_logger(__name__)


class PlannerAgent:
    """計画作成エージェント"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm = LLMOptimizer(config["ollama_url"])
        self.model = config["model"]
        self.prompt_template = self._load_prompt_template()
    
    def create_plan(self, user_query: str) -> Dict[str, Any]:
        """調査計画作成"""
        prompt = self.prompt_template.format(user_query=user_query)
        
        response = self.llm.generate(
            model=self.model,
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000
        )
        
        # YAML形式でパース
        plan = yaml.safe_load(response)
        
        logger.info(f"Plan created: {len(plan.get('todo', []))} tasks")
        return plan
    
    def _load_prompt_template(self) -> str:
        """プロンプトテンプレート読み込み"""
        # 実装: planner_prompt.txt から読み込み
        return """
あなたは専門調査員AIの計画係です。ユーザーの調査依頼から、実行可能な調査計画を作成してください。

ユーザー依頼: {user_query}

以下のYAML形式で回答してください:

goal: 調査目標（1文で）
success_criteria:
  - criterion: 成功条件1
    priority: high
    measurable: true
  - criterion: 成功条件2
    priority: medium
    measurable: true

todo:
  - step: 1
    description: タスク説明
    tool: search|rag|docs|pdf|none
    expected_output: 期待される出力
    dependencies: []
    priority: high
  - step: 2
    description: タスク説明
    tool: search
    expected_output: 期待される出力
    dependencies: [1]
    priority: medium

risks:
  - risk: リスク説明
    mitigation: 対策

estimated_time_minutes: 60
estimated_cost_tokens: 30000
"""
```

### 3. Research Loop（調査ループ）

```python
# step_deep_research/research_loop.py

from typing import Dict, Any, List
from .searcher import Searcher
from .reader import Reader
from .verifier import Verifier
from .writer import Writer

from manaos_logger import get_logger

logger = get_logger(__name__)


class ResearchLoop:
    """調査ループ（ReAct形式）"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_iterations = config["max_iterations"]
        
        self.searcher = Searcher(config["searcher"])
        self.reader = Reader(config["reader"])
        self.verifier = Verifier(config["verifier"])
        self.writer = Writer(config["writer"])
    
    def execute(self, plan: Dict[str, Any], budget) -> Dict[str, Any]:
        """調査ループ実行"""
        results = {
            "iterations": [],
            "citations": [],
            "summaries": [],
            "contradictions": []
        }
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"Research iteration {iteration}/{self.max_iterations}")
            
            # 1. Search
            todo_items = plan.get("todo", [])
            current_todo = todo_items[iteration - 1] if iteration <= len(todo_items) else None
            
            if current_todo:
                search_results = self.searcher.search(
                    query=current_todo["description"],
                    tool=current_todo["tool"],
                    max_results=10
                )
                budget.used_searches += 1
            else:
                search_results = []
            
            # 2. Read & Extract
            citations = self.reader.extract_citations(search_results)
            summaries = self.reader.create_summaries(search_results)
            
            results["citations"].extend(citations)
            results["summaries"].extend(summaries)
            
            # 3. Verify
            contradictions = self.verifier.check_contradictions(
                citations=citations,
                summaries=summaries
            )
            results["contradictions"].extend(contradictions)
            
            # 4. 収束判定
            if self._is_converged(results, iteration):
                logger.info("Research converged")
                break
            
            results["iterations"].append({
                "iteration": iteration,
                "search_results": search_results,
                "citations": citations,
                "summaries": summaries,
                "contradictions": contradictions
            })
        
        return results
    
    def _is_converged(self, results: Dict[str, Any], iteration: int) -> bool:
        """収束判定"""
        # 実装: 十分な情報が集まったか判定
        min_citations = 5
        return len(results["citations"]) >= min_citations
```

### 4. Critic Agent（採点AI）

```python
# step_deep_research/critic.py

from typing import Dict, Any
import yaml

from manaos_logger import get_logger
from llm_optimization import LLMOptimizer
from .rubric import load_rubric

logger = get_logger(__name__)


class CriticAgent:
    """採点エージェント"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm = LLMOptimizer(config["ollama_url"])
        self.model = config["model"]
        self.rubric = load_rubric(config["rubric_file"])
        self.min_pass_score = config["min_pass_score"]
        self.prompt_template = self._load_prompt_template()
    
    def evaluate(self, report: str, iteration: int = 1) -> Dict[str, Any]:
        """レポート評価"""
        prompt = self.prompt_template.format(
            report=report,
            rubric=self.rubric
        )
        
        response = self.llm.generate(
            model=self.model,
            prompt=prompt,
            temperature=0.1,
            max_tokens=3000
        )
        
        # YAML形式でパース
        critique = yaml.safe_load(response)
        critique["iteration"] = iteration
        critique["pass"] = critique["score"] >= self.min_pass_score
        
        logger.info(f"Critique score: {critique['score']}/20, Pass: {critique['pass']}")
        return critique
    
    def _load_prompt_template(self) -> str:
        """プロンプトテンプレート読み込み"""
        return """
あなたは専門調査員AIの採点係です。以下のレポートを、提供されたルーブリックに基づいて採点してください。

レポート:
{report}

ルーブリック:
{rubric}

以下のYAML形式で回答してください:

score: 0-20の総合スコア
pass: true|false

rubric_scores:
  citations:
    score: 0-8
    details:
      - item: cite_001
        passed: true|false
        note: "評価コメント"
  
  logic:
    score: 0-7
    details:
      - item: logic_001
        passed: true|false
        note: "評価コメント"
  
  practicality:
    score: 0-5
    details:
      - item: prac_001
        passed: true|false
        note: "評価コメント"

fail_flags: ["missing_citations", "weak_conclusion_support"]
fix_requests:
  - "結論に対応する一次情報を2つ追加"
  - "反証候補を1つ入れて比較"
"""
```

---

## 🔗 統合ポイント

### 1. ManaOS既存サービスとの統合

```python
# step_deep_research/integration.py

from intent_router import IntentRouter
from rag_memory import RAGMemory
from task_queue import TaskQueue

class StepDeepResearchIntegration:
    """ManaOS統合"""
    
    def __init__(self):
        self.intent_router = IntentRouter()
        self.rag_memory = RAGMemory()
        self.task_queue = TaskQueue()
    
    def register_intent(self):
        """Intent Routerに登録"""
        self.intent_router.register(
            intent_type="deep_research",
            handler=self.handle_research_request,
            keywords=["調査", "リサーチ", "調べて", "研究"]
        )
    
    def handle_research_request(self, user_input: str):
        """調査リクエスト処理"""
        from .orchestrator import StepDeepResearchOrchestrator
        
        orchestrator = StepDeepResearchOrchestrator(self.config)
        job_id = orchestrator.create_job(user_input)
        
        # タスクキューに追加
        self.task_queue.add_task(
            task_id=job_id,
            task_type="deep_research",
            priority="high",
            handler=lambda: orchestrator.execute_job(job_id)
        )
        
        return {"job_id": job_id, "status": "queued"}
    
    def save_to_memory(self, job_id: str, report: str):
        """RAG Memoryに保存"""
        self.rag_memory.store(
            content=report,
            metadata={
                "type": "research_report",
                "job_id": job_id,
                "timestamp": datetime.now().isoformat()
            }
        )
```

### 2. Trinity System統合

```python
# step_deep_research/trinity_integration.py

class TrinityIntegration:
    """Trinity System統合"""
    
    def __init__(self):
        self.remi_roles = ["planner", "writer"]
        self.luna_roles = ["searcher", "reader"]
        self.mina_roles = ["verifier", "critic_assistant"]
    
    def route_to_agent(self, task_type: str, agent: str):
        """エージェントにルーティング"""
        if agent == "remi" and task_type in self.remi_roles:
            return True
        elif agent == "luna" and task_type in self.luna_roles:
            return True
        elif agent == "mina" and task_type in self.mina_roles:
            return True
        return False
```

---

## 🚀 MVP実装ロードマップ

### Day 1: ループが回るようにする

**目標**: Planner → Searcher → Writer → Critic → 差し戻しの基本フローを実装

**実装タスク**:
1. ✅ `orchestrator.py` の基本実装
2. ✅ `planner.py` の基本実装
3. ✅ `research_loop.py` の基本実装（Searcher, Writerのみ）
4. ✅ `critic.py` の基本実装
5. ✅ ログ保存（JSONL形式）
6. ✅ 設定ファイル読み込み

**テスト**:
- 簡単な調査依頼（例: "Pythonの非同期処理について調べて"）で動作確認

### Day 2: 引用と矛盾検出を強化

**目標**: 引用抽出の標準化と矛盾検出機能の追加

**実装タスク**:
1. ✅ `reader.py` の引用抽出機能強化
2. ✅ `verifier.py` の矛盾検出機能実装
3. ✅ 引用フォーマット標準化（Markdown形式）
4. ✅ "推測タグ"（fact/inference）の導入

**テスト**:
- 複数の情報源から引用を抽出
- 矛盾する情報の検出

### Day 3: 逆算データを作り始める

**目標**: 良いレポートから学習データを自動生成

**実装タスク**:
1. ✅ 良いレポートの自動検出
2. ✅ レポート → 依頼文の逆算
3. ✅ レポート → 計画の逆算
4. ✅ 学習データのストック（JSON形式）

**テスト**:
- 既存の良いレポートから学習データを生成

---

## 📝 次のステップ

**A）すぐ動かす**: この設計図を基に実装を開始
**B）精度から固める**: ルーブリック完全版（30項目）と差し戻しプロンプトテンプレートを先に作成

---

## 🔧 実装時の注意点

1. **既存のManaOSモジュールを活用**
   - `manaos_logger`, `manaos_error_handler`, `llm_optimization` など

2. **設定ファイルの統一**
   - 既存の `*_config.json` 形式に合わせる

3. **エラーハンドリング**
   - 予算超過、タイムアウト、LLMエラーなど

4. **ログの構造化**
   - JSONL形式で保存し、後から分析可能に

5. **Trinity System統合**
   - レミ/ルナ/ミナの役割分担を明確に

---

**設計完了！実装準備OK！** 🎉



