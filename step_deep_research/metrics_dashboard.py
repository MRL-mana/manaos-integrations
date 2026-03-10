#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メトリクスダッシュボード
完成度チェックのガチ指標を計算・表示
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

from unified_logging import get_service_logger
logger = get_service_logger("metrics-dashboard")


class MetricsDashboard:
    """メトリクスダッシュボード"""
    
    def __init__(self, log_dir: str = "logs/step_deep_research/jobs"):
        """
        初期化
        
        Args:
            log_dir: ログディレクトリ
        """
        self.log_dir = Path(log_dir)
    
    def calculate_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        メトリクス計算
        
        Args:
            days: 集計期間（日数）
        
        Returns:
            メトリクス
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        
        jobs = []
        for log_file in self.log_dir.glob("*.jsonl"):
            # ログファイルからジョブ情報を読み込む
            job_data = self._load_job_data(log_file)
            if job_data:
                jobs.append(job_data)
        
        if not jobs:
            return {
                "total_jobs": 0,
                "metrics": {}
            }
        
        # メトリクス計算
        costs = []
        latencies = []
        scores = []
        pass_count = 0
        fatal_errors = 0
        citations_counts = []
        
        for job in jobs:
            # コスト
            budget = job.get("spent_budget", {})
            tokens = budget.get("tokens", {}).get("used", 0)
            if tokens > 0:
                costs.append(tokens)
            
            # レイテンシ
            time_data = budget.get("time", {})
            elapsed = time_data.get("elapsed_sec", 0)
            if elapsed > 0:
                latencies.append(elapsed)
            
            # スコア
            score = job.get("score", 0)
            if score > 0:
                scores.append(score)
            
            # 合格
            if job.get("pass", False):
                pass_count += 1
            
            # 致命エラー
            if job.get("status") == "failed" or "error" in job:
                fatal_errors += 1
            
            # 引用数
            citations_count = job.get("citations_count", 0)
            if citations_count > 0:
                citations_counts.append(citations_count)
        
        # 統計計算
        avg_cost = sum(costs) / len(costs) if costs else 0
        median_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0
        avg_score = sum(scores) / len(scores) if scores else 0
        
        total_jobs = len(jobs)
        critic_reject_rate = (total_jobs - pass_count) / total_jobs if total_jobs > 0 else 0
        fatal_error_rate = fatal_errors / total_jobs if total_jobs > 0 else 0
        
        # 引用カバレッジ（主張に引用が付いている率）
        jobs_with_citations = sum(1 for job in jobs if job.get("citations_count", 0) > 0)
        citation_coverage = jobs_with_citations / total_jobs if total_jobs > 0 else 0
        
        return {
            "total_jobs": total_jobs,
            "period_days": days,
            "metrics": {
                "avg_cost_per_request": avg_cost,
                "median_latency_sec": median_latency,
                "avg_score": avg_score,
                "critic_reject_rate": critic_reject_rate,
                "fatal_error_rate": fatal_error_rate,
                "citation_coverage": citation_coverage
            },
            "breakdown": {
                "costs": {
                    "min": min(costs) if costs else 0,
                    "max": max(costs) if costs else 0,
                    "avg": avg_cost,
                    "median": sorted(costs)[len(costs) // 2] if costs else 0
                },
                "latencies": {
                    "min": min(latencies) if latencies else 0,
                    "max": max(latencies) if latencies else 0,
                    "avg": sum(latencies) / len(latencies) if latencies else 0,
                    "median": median_latency
                },
                "scores": {
                    "min": min(scores) if scores else 0,
                    "max": max(scores) if scores else 0,
                    "avg": avg_score,
                    "median": sorted(scores)[len(scores) // 2] if scores else 0
                }
            }
        }
    
    def _load_job_data(self, log_file: Path) -> Optional[Dict[str, Any]]:  # type: ignore[name-defined]
        """
        ジョブログからデータを読み込む
        
        Args:
            log_file: ログファイル
        
        Returns:
            ジョブデータ
        """
        try:
            # JSONLの最後の行を読み込む（最終状態）
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    return None
                
                # 最後の行をパース
                last_line = lines[-1].strip()
                if not last_line:
                    return None
                
                data = json.loads(last_line)
                
                # ジョブIDをファイル名から取得
                job_id = log_file.stem
                data["job_id"] = job_id
                
                return data
                
        except Exception as e:
            logger.warning(f"Failed to load job data from {log_file}: {e}")
            return None
    
    def generate_dashboard_report(self, days: int = 7) -> str:
        """
        ダッシュボードレポート生成
        
        Args:
            days: 集計期間
        
        Returns:
            レポート（Markdown形式）
        """
        metrics = self.calculate_metrics(days)
        
        report = f"""# Step-Deep-Research メトリクスダッシュボード

**集計期間**: 過去{days}日間  
**総ジョブ数**: {metrics['total_jobs']}  
**生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 主要指標

### コスト
- **平均コスト/リクエスト**: {metrics['metrics']['avg_cost_per_request']:.0f} トークン
- **最小**: {metrics['breakdown']['costs']['min']:.0f} トークン
- **最大**: {metrics['breakdown']['costs']['max']:.0f} トークン
- **中央値**: {metrics['breakdown']['costs']['median']:.0f} トークン

### レイテンシ（体感速度）
- **中央値**: {metrics['metrics']['median_latency_sec']:.1f} 秒
- **平均**: {metrics['breakdown']['latencies']['avg']:.1f} 秒
- **最小**: {metrics['breakdown']['latencies']['min']:.1f} 秒
- **最大**: {metrics['breakdown']['latencies']['max']:.1f} 秒

### 品質
- **平均スコア**: {metrics['metrics']['avg_score']:.1f}/30
- **Critic差し戻し率**: {metrics['metrics']['critic_reject_rate']:.1%}
- **致命エラー率**: {metrics['metrics']['fatal_error_rate']:.1%}
- **引用カバレッジ**: {metrics['metrics']['citation_coverage']:.1%}

---

## 🎯 目標値との比較

| 指標 | 現在値 | 目標値 | 状態 |
|------|--------|--------|------|
| 平均コスト | {metrics['metrics']['avg_cost_per_request']:.0f} | < 30000 | {'✅' if metrics['metrics']['avg_cost_per_request'] < 30000 else '⚠️'} |
| 中央値レイテンシ | {metrics['metrics']['median_latency_sec']:.1f}秒 | < 300秒 | {'✅' if metrics['metrics']['median_latency_sec'] < 300 else '⚠️'} |
| Critic差し戻し率 | {metrics['metrics']['critic_reject_rate']:.1%} | 20-40% | {'✅' if 0.2 <= metrics['metrics']['critic_reject_rate'] <= 0.4 else '⚠️'} |
| 致命エラー率 | {metrics['metrics']['fatal_error_rate']:.1%} | < 5% | {'✅' if metrics['metrics']['fatal_error_rate'] < 0.05 else '❌'} |
| 引用カバレッジ | {metrics['metrics']['citation_coverage']:.1%} | > 90% | {'✅' if metrics['metrics']['citation_coverage'] > 0.9 else '⚠️'} |

---

## 📈 トレンド分析

（将来実装: 時系列での変化を可視化）

---

**ダッシュボード生成完了**
"""
        
        return report


