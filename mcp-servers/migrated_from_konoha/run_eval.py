#!/usr/bin/env python3
"""
評価スイート実行
RAG一貫性、人格整合、回帰テストを実行
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent

# オプショナルインポート
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import torch
    import bitsandbytes as bnb
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class EvaluationSuite:
    """評価スイート"""

    def __init__(self, model_path: str, knowledge_base: str):
        self.model_path = model_path
        self.kb_path = Path(knowledge_base)
        self.results = {}
        self.model = None
        self.tokenizer = None
        self.embedding_model = None

        # モデル読み込み
        if TRANSFORMERS_AVAILABLE and Path(model_path).exists():
            self._load_model()

        # 埋め込みモデル読み込み
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')  # type: ignore[possibly-unbound]
            except Exception:
                pass

    def _load_model(self):
        """モデル読み込み"""
        try:
            print("📦 モデル読み込み中...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)  # type: ignore[possibly-unbound]
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            bnb_config = bnb.config.BitsAndBytesConfig(  # type: ignore[attr-defined, possibly-unbound]
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16  # type: ignore[possibly-unbound]
            )

            self.model = AutoModelForCausalLM.from_pretrained(  # type: ignore[possibly-unbound]
                self.model_path,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True
            )

            # Adapter読み込み
            adapter_path = Path(self.model_path)
            if adapter_path.is_dir() and (adapter_path / "adapter_config.json").exists():
                self.model = PeftModel.from_pretrained(self.model, self.model_path)  # type: ignore[possibly-unbound]

            print("✅ モデル読み込み完了")
        except Exception as e:
            print(f"⚠️ モデル読み込み失敗: {e}")

    def _query_model(self, prompt: str) -> str:
        """モデルにクエリ"""
        if not self.model or not self.tokenizer:
            return ""

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

            with torch.no_grad():  # type: ignore[possibly-unbound]
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            if prompt in response:
                response = response.split(prompt)[-1].strip()
            return response
        except Exception:
            return ""

    def _extract_links(self, text: str) -> List[str]:
        """テキストからリンクを抽出（[[term]]形式）"""
        pattern = r'\[\[([^\]]+)\]\]'
        return re.findall(pattern, text)

    def _extract_paths(self, text: str) -> List[str]:
        """テキストからパスを抽出（memory/...形式）"""
        pattern = r'(memory/[^\s\)]+)'
        return re.findall(pattern, text)

    def eval_rag_consistency(self) -> Dict:
        """RAG一貫性評価"""
        print("📊 RAG一貫性評価...")

        # テストケース
        test_cases = [
            {
                "question": "在庫管理について教えて",
                "expected_paths": ["memory/episodic", "memory/decision"],
                "expected_links": ["在庫管理"]
            },
            {
                "question": "最近の決定事項は？",
                "expected_paths": ["memory/decision"],
                "expected_links": []
            }
        ]

        results = []
        for case in test_cases:
            prompt = f"質問: {case['question']}\n\n応答:"
            response = self._query_model(prompt)

            # リンクとパスを抽出
            actual_paths = self._extract_paths(response)
            actual_links = self._extract_links(response)

            # 一貫性スコア計算
            path_score = 0.0
            if case['expected_paths']:
                matched = sum(1 for p in case['expected_paths'] if any(p in ap for ap in actual_paths))
                path_score = matched / len(case['expected_paths'])

            link_score = 0.0
            if case['expected_links']:
                matched = sum(1 for l in case['expected_links'] if l in actual_links)
                link_score = matched / len(case['expected_links'])

            consistency = (path_score + link_score) / 2.0 if (case['expected_paths'] or case['expected_links']) else 0.0

            result = {
                "question": case["question"],
                "expected_paths": case["expected_paths"],
                "actual_paths": actual_paths,
                "expected_links": case["expected_links"],
                "actual_links": actual_links,
                "consistency": consistency
            }
            results.append(result)

        score = sum(r["consistency"] for r in results) / len(results) if results else 0.0

        return {
            "score": score,
            "results": results,
            "status": "pass" if score >= 0.8 else "fail"
        }

    def eval_factual(self) -> Dict:
        """事実性評価"""
        print("📊 事実性評価...")

        # 引用外の断言を減点
        test_cases = [
            {
                "question": "プロジェクトの進捗は？",
                "require_citation": True
            }
        ]

        results = []
        for case in test_cases:
            prompt = f"質問: {case['question']}\n\n応答:"
            response = self._query_model(prompt)

            # 引用があるかチェック
            has_citation = bool(self._extract_paths(response) or self._extract_links(response))

            # 断言的な表現をチェック
            assertions = re.findall(r'(確実に|必ず|絶対に|間違いなく)', response)
            assertion_penalty = min(len(assertions) * 0.2, 1.0)

            score = 0.0
            if case['require_citation']:
                if has_citation:
                    score = 1.0 - assertion_penalty
                else:
                    score = 0.3 - assertion_penalty
            else:
                score = 1.0 - assertion_penalty

            score = max(0.0, min(1.0, score))

            results.append({
                "question": case["question"],
                "has_citation": has_citation,
                "assertions": len(assertions),
                "score": score
            })

        avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0

        return {
            "score": avg_score,
            "results": results,
            "status": "pass" if avg_score >= 0.7 else "fail"
        }

    def eval_task_success(self) -> Dict:
        """タスク成功評価"""
        print("📊 タスク成功評価...")

        # ToDo抽出→期限→依存の3点セット
        test_cases = [
            {
                "instruction": "タスクを整理して",
                "expected": ["todo", "deadline", "dependencies"]
            }
        ]

        results = []
        for case in test_cases:
            prompt = f"指示: {case['instruction']}\n\n応答:"
            response = self._query_model(prompt)

            # ToDo抽出
            has_todo = bool(re.search(r'(TODO|ToDo|タスク|todo)', response, re.IGNORECASE))

            # 期限抽出
            has_deadline = bool(re.search(r'(期限|締切|deadline|due)', response, re.IGNORECASE))

            # 依存関係抽出
            has_dependencies = bool(re.search(r'(依存|dependent|prerequisite)', response, re.IGNORECASE))

            score = 0.0
            if "todo" in case['expected'] and has_todo:
                score += 0.33
            if "deadline" in case['expected'] and has_deadline:
                score += 0.33
            if "dependencies" in case['expected'] and has_dependencies:
                score += 0.34

            results.append({
                "instruction": case["instruction"],
                "has_todo": has_todo,
                "has_deadline": has_deadline,
                "has_dependencies": has_dependencies,
                "score": score
            })

        avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0

        return {
            "score": avg_score,
            "results": results,
            "status": "pass" if avg_score >= 0.7 else "fail"
        }

    def eval_persona_alignment(self) -> Dict:
        """人格整合評価"""
        print("📊 人格整合評価...")

        # 口調・根拠提示・Decision優先の遵守率
        test_cases = [
            {
                "question": "どうすればいい？",
                "check_tone": True,
                "check_evidence": True,
                "check_decision": True
            }
        ]

        results = []
        for case in test_cases:
            prompt = f"質問: {case['question']}\n\n応答:"
            response = self._query_model(prompt)

            # 口調チェック（清楚系・親しみやすい）
            tone_score = 0.0
            if re.search(r'(です|ます|ね|よ|だよ)', response):
                tone_score += 0.5
            if not re.search(r'(です|ます)', response):
                tone_score -= 0.2
            tone_score = max(0.0, min(1.0, tone_score))

            # 根拠提示チェック
            evidence_score = 0.0
            if self._extract_paths(response) or self._extract_links(response):
                evidence_score += 0.5
            if re.search(r'(参照|参考|根拠|理由)', response):
                evidence_score += 0.5

            # Decision優先チェック
            decision_score = 0.0
            if re.search(r'(decision|決定|DECISION)', response, re.IGNORECASE):
                decision_score = 1.0

            total_score = (tone_score + evidence_score + decision_score) / 3.0

            results.append({
                "question": case["question"],
                "tone_score": tone_score,
                "evidence_score": evidence_score,
                "decision_score": decision_score,
                "score": total_score
            })

        avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0

        return {
            "score": avg_score,
            "results": results,
            "status": "pass" if avg_score >= 0.6 else "fail"
        }

    def eval_preference_match(self) -> Dict:
        """好み一致評価"""
        print("📊 好み一致評価...")

        # 過去の"👍回答"に近いか（埋め込み距離）
        if not self.embedding_model:
            return {
                "score": 0.0,
                "status": "not_implemented",
                "message": "埋め込みモデルが利用できません"
            }

        # 参考回答（過去の良い回答例）
        reference_responses = [
            "清楚系ギャルの口調で、根拠を提示しながら回答します。",
            "Decision を参照して、具体的な提案をします。"
        ]

        test_cases = [
            {
                "question": "どうすればいい？",
                "response": self._query_model(f"質問: どうすればいい？\n\n応答:")
            }
        ]

        results = []
        for case in test_cases:
            response_embedding = self.embedding_model.encode(case["response"])

            similarities = []
            for ref in reference_responses:
                ref_embedding = self.embedding_model.encode(ref)
                import numpy as np
                similarity = np.dot(response_embedding, ref_embedding) / (
                    np.linalg.norm(response_embedding) * np.linalg.norm(ref_embedding)
                )
                similarities.append(float(similarity))

            score = max(similarities) if similarities else 0.0

            results.append({
                "question": case["question"],
                "max_similarity": score,
                "score": score
            })

        avg_score = sum(r["score"] for r in results) / len(results) if results else 0.0

        return {
            "score": avg_score,
            "results": results,
            "status": "pass" if avg_score >= 0.6 else "fail"
        }

    def run_all(self) -> Dict:
        """全評価実行"""
        print("🧪 評価スイート実行開始...")

        self.results = {
            "timestamp": datetime.now().isoformat(),
            "model_path": self.model_path,
            "knowledge_base": str(self.kb_path),
            "evaluations": {
                "rag_consistency": self.eval_rag_consistency(),
                "factual": self.eval_factual(),
                "task_success": self.eval_task_success(),
                "persona_alignment": self.eval_persona_alignment(),
                "preference_match": self.eval_preference_match()
            }
        }

        # 総合スコア
        scores = [
            eval_result.get("score", 0.0)
            for eval_result in self.results["evaluations"].values()
            if isinstance(eval_result, dict) and "score" in eval_result
        ]
        self.results["overall_score"] = sum(scores) / len(scores) if scores else 0.0

        return self.results

    def save_results(self, output_path: str):
        """結果を保存"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"✅ 結果保存: {output_file}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="評価スイート実行")
    parser.add_argument("--model", required=True, help="モデルパス")
    parser.add_argument("--suite", default="./eval/suites", help="評価スイートディレクトリ")
    parser.add_argument("--kb", default="./manaos-knowledge", help="ナレッジベースパス")
    parser.add_argument("--out", default="./eval/results/eval_result.json", help="出力ファイル")
    args = parser.parse_args()

    suite = EvaluationSuite(args.model, args.kb)
    results = suite.run_all()
    suite.save_results(args.out)

    print("\n📊 評価結果:")
    print(f"   総合スコア: {results['overall_score']:.2%}")
    for name, result in results["evaluations"].items():
        if isinstance(result, dict) and "score" in result:
            print(f"   {name}: {result['score']:.2%} ({result.get('status', 'unknown')})")


if __name__ == "__main__":
    main()
