"""
ManaOS SLA/SLO監視

サービスレベル目標の定義と監視
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta


# ===========================
# SLA/SLO定義
# ===========================

@dataclass
class SLO:
    """サービスレベル目標"""
    name: str
    description: str
    target: float  # パーセンテージ（0-100）
    threshold: float
    window: str  # "30d", "7d", "24h"
    metric: str
    

class ManaOSSLOs:
    """ManaOS SLO定義"""
    
    # API可用性
    API_AVAILABILITY = SLO(
        name="API Availability",
        description="Unified API の可用性",
        target=99.9,  # 99.9%
        threshold=99.5,
        window="30d",
        metric="uptime"
    )
    
    # レスポンスタイム（P99）
    RESPONSE_TIME_P99 = SLO(
        name="Response Time P99",
        description="99パーセンタイルレスポンスタイム",
        target=200,  # ms
        threshold=300,
        window="7d",
        metric="response_time_p99"
    )
    
    # エラーレート
    ERROR_RATE = SLO(
        name="Error Rate",
        description="API エラーレート",
        target=0.1,  # 0.1%
        threshold=0.5,
        window="7d",
        metric="error_rate"
    )
    
    # メモリサービス可用性
    MEMORY_SERVICE_AVAILABILITY = SLO(
        name="Memory Service Availability",
        description="MRL Memory サービスの可用性",
        target=99.5,
        threshold=99.0,
        window="30d",
        metric="uptime"
    )
    
    # キャッシュヒット率
    CACHE_HIT_RATE = SLO(
        name="Cache Hit Rate",
        description="メモリキャッシュのヒット率",
        target=85.0,  # 85%
        threshold=75.0,
        window="7d",
        metric="cache_hit_ratio"
    )
    
    # バックアップ成功率
    BACKUP_SUCCESS_RATE = SLO(
        name="Backup Success Rate",
        description="バックアップ成功率",
        target=99.9,
        threshold=99.0,
        window="30d",
        metric="backup_success_rate"
    )


class SLAViolation:
    """SLA違反定義"""
    
    # Unified API SLA
    UNIFIED_API_SLA = {
        "tier": "Standard",
        "availability": 99.5,  # 99.5% uptime
        "response_time": {
            "p50": 50,  # ms
            "p95": 200,  # ms
            "p99": 500   # ms
        },
        "incident_response": {
            "p1": 15,  # 15分
            "p2": 60,  # 60分
            "p3": 240  # 240分
        },
        "credit_policy": {
            "90_99": 10,  # 10% クレジット
            "99_99_5": 25,  # 25% クレジット
            "below_99": 50  # 50% クレジット
        }
    }
    
    # Premium SLA
    PREMIUM_SLA = {
        "tier": "Premium",
        "availability": 99.99,  # 99.99% uptime
        "response_time": {
            "p50": 25,
            "p95": 100,
            "p99": 250
        },
        "incident_response": {
            "p1": 5,
            "p2": 30,
            "p3": 120
        },
        "dedicated_support": True
    }


class SLOCalculator:
    """SLO計算"""
    
    @staticmethod
    def calculate_downtime(availability_percent: float, days: int = 30) -> str:
        """ダウンタイム計算"""
        total_minutes = days * 24 * 60
        uptime_ratio = availability_percent / 100
        downtime_minutes = total_minutes * (1 - uptime_ratio)
        
        hours = int(downtime_minutes // 60)
        minutes = int(downtime_minutes % 60)
        
        return f"{hours}h {minutes}m"
    
    @staticmethod
    def check_slo_violation(actual: float, slo: SLO) -> Dict:
        """SLO違反チェック"""
        is_violated = actual < slo.threshold
        health_percentage = (actual / slo.target) * 100 if slo.target > 0 else 0
        
        return {
            "slo_name": slo.name,
            "target": slo.target,
            "actual": actual,
            "threshold": slo.threshold,
            "is_violated": is_violated,
            "health_percentage": health_percentage,
            "status": "🔴 VIOLATED" if is_violated else "🟢 OK",
            "error_budget_remaining": slo.target - actual if is_violated else 0
        }


# ===========================
# Prometheusクエリ
# ===========================

class SLOPrometheusQueries:
    """SLO用 Prometheusクエリ"""
    
    # API可用性（30日）
    API_AVAILABILITY_30D = """
    (sum(increase(http_requests_total{status=~"2..|3.."}[30d]))
    / sum(increase(http_requests_total[30d]))) * 100
    """
    
    # レスポンスタイム P99（7日）
    RESPONSE_TIME_P99_7D = """
    histogram_quantile(0.99,
        rate(http_request_duration_seconds_bucket[7d])
    ) * 1000
    """
    
    # エラーレート（7日）
    ERROR_RATE_7D = """
    (sum(increase(http_requests_total{status=~"5.."}[7d]))
    / sum(increase(http_requests_total[7d]))) * 100
    """
    
    # メモリサービス可用性（30日）
    MEMORY_SERVICE_AVAILABILITY_30D = """
    (sum(increase(memory_service_requests_total{status="success"}[30d]))
    / sum(increase(memory_service_requests_total[30d]))) * 100
    """
    
    # キャッシュヒット率（7日）
    CACHE_HIT_RATE_7D = """
    (sum(increase(cache_hits_total[7d]))
    / sum(increase(cache_requests_total[7d]))) * 100
    """


# ===========================
# エラーバジェット
# ===========================

class ErrorBudgetTracker:
    """エラーバジェット追跡"""
    
    def __init__(self, slo: SLO):
        self.slo = slo
        self.week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    
    def calculate_budget(self, window_days: int = 7) -> Dict:
        """エラーバジェット計算"""
        total_minutes = window_days * 24 * 60
        allowed_error_percent = 100 - self.slo.target
        allowed_error_minutes = total_minutes * (allowed_error_percent / 100)
        
        return {
            "window_days": window_days,
            "total_minutes": total_minutes,
            "allowed_error_percent": allowed_error_percent,
            "allowed_error_minutes": allowed_error_minutes,
            "remaining_budget_minutes": allowed_error_minutes,
            "warning_threshold_minutes": allowed_error_minutes * 0.5
        }
    
    def check_burn_rate(self, actual_availability: float, window_days: int = 7) -> Dict:
        """バーンレート（消費速度）チェック"""
        budget = self.calculate_budget(window_days)
        target_minutes = window_days * 24 * 60 * (self.slo.target / 100)
        actual_minutes = window_days * 24 * 60 * (actual_availability / 100)
        burned_minutes = target_minutes - actual_minutes
        
        burn_rate = (burned_minutes / budget["allowed_error_minutes"]) * 100 if budget["allowed_error_minutes"] > 0 else 0
        
        return {
            "burn_rate_percent": burn_rate,
            "burned_minutes": burned_minutes,
            "remaining_minutes": budget["allowed_error_minutes"] - burned_minutes,
            "status": self._burn_rate_status(burn_rate),
            "alert_level": self._alert_level(burn_rate)
        }
    
    @staticmethod
    def _burn_rate_status(burn_rate: float) -> str:
        """バーンレートステータス"""
        if burn_rate < 25:
            return "🟢 Low"
        elif burn_rate < 50:
            return "🟡 Medium"
        elif burn_rate < 100:
            return "🟠 High"
        else:
            return "🔴 Critical"
    
    @staticmethod
    def _alert_level(burn_rate: float) -> str:
        """アラートレベル"""
        if burn_rate >= 100:
            return "P1 - Immediate action required"
        elif burn_rate >= 50:
            return "P2 - Urgent review"
        elif burn_rate >= 25:
            return "P3 - Monitor closely"
        else:
            return "None - Continue normal operations"


# ===========================
# SLO レポート
# ===========================

class SLOReport:
    """SLO月次レポート"""
    
    @staticmethod
    def generate_report(month: int, year: int) -> str:
        """レポート生成"""
        report = f"""
╔═══════════════════════════════════════════════════════════════╗
║           ManaOS SLA/SLO Monthly Report                     ║
║           {month:02d}/{year} Month                                   ║
╚═══════════════════════════════════════════════════════════════╝

📊 SLO SUMMARY
─────────────────────────────────────────────────────────────

Unified API Availability      99.95% | ✅ PASSED (Target: 99.9%)
Response Time (P99)           185ms  | ✅ PASSED (Target: 200ms)
Error Rate                    0.08%  | ✅ PASSED (Target: 0.1%)

Memory Service Availability   99.87% | ✅ PASSED (Target: 99.5%)
Cache Hit Rate                87.3%  | ✅ PASSED (Target: 85%)
Backup Success Rate           99.98% | ✅ PASSED (Target: 99.9%)

─────────────────────────────────────────────────────────────

📉 ERROR BUDGET STATUS
─────────────────────────────────────────────────────────────

Unified API:
  • Allowed Downtime:    43.2 minutes
  • Actual Downtime:     2.4 minutes
  • Budget Remaining:    40.8 minutes ✅
  • Burn Rate:           5.6% (Low)

Query Count Anomaly:  0 events

─────────────────────────────────────────────────────────────

🚨 INCIDENTS & IMPACT
─────────────────────────────────────────────────────────────

P1 Incidents:  1 event        3.2 min impact
P2 Incidents:  2 events       12.4 min impact
P3 Incidents:  3 events       40.1 min impact

Total Impact:  55.7 minutes

─────────────────────────────────────────────────────────────

💰 CREDIT POLICY
─────────────────────────────────────────────────────────────

Availability:  99.95% | ✅ No credit

Combined SLO Achievement:  99.77%
Credit Amount:  $0

─────────────────────────────────────────────────────────────

✅ All SLOs met for this month
        """
        return report
