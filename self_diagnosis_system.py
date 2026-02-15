#!/usr/bin/env python3
"""
🔍 ManaOS 自己診断システム
システムの自動診断、問題の検出、改善提案の生成
"""

import json
import psutil
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_service_logger("self-diagnosis-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SelfDiagnosisSystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("SelfDiagnosisSystem")


@dataclass
class DiagnosisIssue:
    """診断問題"""
    issue_id: str
    issue_type: str  # "performance", "resource", "configuration", "security", "stability"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    component: str
    detected_at: str
    recommendations: List[str]
    status: str  # "detected", "investigating", "resolved"


class SelfDiagnosisSystem:
    """自己診断システム"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path or Path(__file__).parent / "self_diagnosis_config.json"
        self.config = self._load_config()
        
        # 診断履歴
        self.diagnosis_history: List[Dict[str, Any]] = []
        self.diagnosis_storage = Path("diagnosis_history.json")
        self._load_diagnosis_history()
        
        # 検出された問題
        self.issues: List[DiagnosisIssue] = []
        self.issues_storage = Path("diagnosis_issues.json")
        self._load_issues()
        
        logger.info("✅ Self Diagnosis System初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"設定読み込みエラー: {e}")
        
        return {
            "enable_auto_diagnosis": True,
            "diagnosis_interval_minutes": 60,
            "enable_health_checks": True,
            "enable_performance_analysis": True,
            "enable_resource_analysis": True,
            "enable_configuration_analysis": True
        }
    
    def _load_diagnosis_history(self):
        """診断履歴を読み込む"""
        if self.diagnosis_storage.exists():
            try:
                with open(self.diagnosis_storage, 'r', encoding='utf-8') as f:
                    self.diagnosis_history = json.load(f)
            except Exception as e:
                logger.warning(f"診断履歴読み込みエラー: {e}")
    
    def _save_diagnosis_history(self):
        """診断履歴を保存"""
        try:
            # 最新100件のみ保存
            recent_history = self.diagnosis_history[-100:]
            with open(self.diagnosis_storage, 'w', encoding='utf-8') as f:
                json.dump(recent_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"診断履歴保存エラー: {e}")
    
    def _load_issues(self):
        """検出された問題を読み込む"""
        if self.issues_storage.exists():
            try:
                with open(self.issues_storage, 'r', encoding='utf-8') as f:
                    issues_data = json.load(f)
                    self.issues = [
                        DiagnosisIssue(**item) for item in issues_data
                    ]
            except Exception as e:
                logger.warning(f"問題読み込みエラー: {e}")
    
    def _save_issues(self):
        """検出された問題を保存"""
        try:
            issues_data = [asdict(issue) for issue in self.issues[-100:]]
            with open(self.issues_storage, 'w', encoding='utf-8') as f:
                json.dump(issues_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"問題保存エラー: {e}")
    
    def diagnose_system(self) -> Dict[str, Any]:
        """
        システム全体を診断
        
        Returns:
            診断結果
        """
        if not self.config.get("enable_auto_diagnosis", True):
            return {"skipped": True, "reason": "自動診断が無効です"}
        
        diagnosis_result = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "issues": [],
            "recommendations": []
        }
        
        # ヘルスチェック
        if self.config.get("enable_health_checks", True):
            health_checks = self._check_health()
            diagnosis_result["checks"]["health"] = health_checks
        
        # パフォーマンス分析
        if self.config.get("enable_performance_analysis", True):
            performance_analysis = self._analyze_performance()
            diagnosis_result["checks"]["performance"] = performance_analysis
        
        # リソース分析
        if self.config.get("enable_resource_analysis", True):
            resource_analysis = self._analyze_resources()
            diagnosis_result["checks"]["resources"] = resource_analysis
        
        # 設定分析
        if self.config.get("enable_configuration_analysis", True):
            config_analysis = self._analyze_configuration()
            diagnosis_result["checks"]["configuration"] = config_analysis
        
        # 問題の検出
        issues = self._detect_issues(diagnosis_result)
        diagnosis_result["issues"] = issues
        
        # 推奨事項の生成
        recommendations = self._generate_recommendations(diagnosis_result)
        diagnosis_result["recommendations"] = recommendations
        
        # 診断履歴に記録
        self.diagnosis_history.append(diagnosis_result)
        self._save_diagnosis_history()
        
        return diagnosis_result
    
    def _check_health(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        health_status = {
            "overall": "healthy",
            "components": {}
        }
        
        # CPUヘルス
        cpu_percent = psutil.cpu_percent(interval=1)
        health_status["components"]["cpu"] = {
            "status": "healthy" if cpu_percent < 90 else "warning" if cpu_percent < 95 else "critical",
            "usage_percent": cpu_percent
        }
        
        # メモリヘルス
        memory = psutil.virtual_memory()
        health_status["components"]["memory"] = {
            "status": "healthy" if memory.percent < 85 else "warning" if memory.percent < 95 else "critical",
            "usage_percent": memory.percent,
            "available_gb": memory.available / (1024**3)
        }
        
        # ディスクヘルス
        disk = psutil.disk_usage('/')
        health_status["components"]["disk"] = {
            "status": "healthy" if disk.percent < 85 else "warning" if disk.percent < 95 else "critical",
            "usage_percent": disk.percent,
            "free_gb": disk.free / (1024**3)
        }
        
        # 全体ステータスの決定
        component_statuses = [c["status"] for c in health_status["components"].values()]
        if "critical" in component_statuses:
            health_status["overall"] = "critical"
        elif "warning" in component_statuses:
            health_status["overall"] = "warning"
        
        return health_status
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """パフォーマンス分析"""
        analysis = {
            "metrics": {},
            "bottlenecks": []
        }
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        analysis["metrics"]["cpu_percent"] = cpu_percent
        
        # メモリ使用率
        memory = psutil.virtual_memory()
        analysis["metrics"]["memory_percent"] = memory.percent
        
        # ディスクI/O
        disk_io = psutil.disk_io_counters()
        if disk_io:
            analysis["metrics"]["disk_read_mb"] = disk_io.read_bytes / (1024**2)
            analysis["metrics"]["disk_write_mb"] = disk_io.write_bytes / (1024**2)
        
        # ネットワークI/O
        net_io = psutil.net_io_counters()
        if net_io:
            analysis["metrics"]["network_sent_mb"] = net_io.bytes_sent / (1024**2)
            analysis["metrics"]["network_recv_mb"] = net_io.bytes_recv / (1024**2)
        
        # ボトルネックの検出
        if cpu_percent > 90:
            analysis["bottlenecks"].append({
                "component": "cpu",
                "severity": "high",
                "description": f"CPU使用率が高い: {cpu_percent}%"
            })
        
        if memory.percent > 90:
            analysis["bottlenecks"].append({
                "component": "memory",
                "severity": "high",
                "description": f"メモリ使用率が高い: {memory.percent}%"
            })
        
        return analysis
    
    def _analyze_resources(self) -> Dict[str, Any]:
        """リソース分析"""
        analysis = {
            "resource_usage": {},
            "warnings": []
        }
        
        # CPUリソース
        cpu_percent = psutil.cpu_percent(interval=1)
        analysis["resource_usage"]["cpu"] = {
            "current": cpu_percent,
            "threshold": 85,
            "status": "ok" if cpu_percent < 85 else "warning"
        }
        
        # メモリリソース
        memory = psutil.virtual_memory()
        analysis["resource_usage"]["memory"] = {
            "current": memory.percent,
            "threshold": 85,
            "status": "ok" if memory.percent < 85 else "warning",
            "available_gb": memory.available / (1024**3)
        }
        
        # ディスクリソース
        disk = psutil.disk_usage('/')
        analysis["resource_usage"]["disk"] = {
            "current": disk.percent,
            "threshold": 85,
            "status": "ok" if disk.percent < 85 else "warning",
            "free_gb": disk.free / (1024**3)
        }
        
        # 警告の生成
        if cpu_percent > 85:
            analysis["warnings"].append({
                "type": "high_cpu_usage",
                "message": f"CPU使用率が高い: {cpu_percent}%"
            })
        
        if memory.percent > 85:
            analysis["warnings"].append({
                "type": "high_memory_usage",
                "message": f"メモリ使用率が高い: {memory.percent}%"
            })
        
        if disk.percent > 85:
            analysis["warnings"].append({
                "type": "low_disk_space",
                "message": f"ディスク使用率が高い: {disk.percent}%"
            })
        
        return analysis
    
    def _analyze_configuration(self) -> Dict[str, Any]:
        """設定分析"""
        analysis = {
            "config_files": [],
            "issues": []
        }
        
        # 主要設定ファイルの確認
        config_files = [
            "manaos_integration_config.json",
            "comprehensive_self_capabilities_config.json",
            "self_evolution_config.json",
            "self_protection_config.json",
            "self_management_config.json"
        ]
        
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    analysis["config_files"].append({
                        "file": config_file,
                        "status": "valid",
                        "size_kb": config_path.stat().st_size / 1024
                    })
                except Exception as e:
                    analysis["config_files"].append({
                        "file": config_file,
                        "status": "invalid",
                        "error": str(e)
                    })
                    analysis["issues"].append({
                        "type": "invalid_config",
                        "file": config_file,
                        "message": f"設定ファイルが無効: {e}"
                    })
            else:
                analysis["config_files"].append({
                    "file": config_file,
                    "status": "missing"
                })
                analysis["issues"].append({
                    "type": "missing_config",
                    "file": config_file,
                    "message": "設定ファイルが見つかりません"
                })
        
        return analysis
    
    def _detect_issues(self, diagnosis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """問題を検出"""
        issues = []
        
        # ヘルスチェックから問題を検出
        if "health" in diagnosis_result.get("checks", {}):
            health = diagnosis_result["checks"]["health"]
            if health.get("overall") == "critical":
                issue = DiagnosisIssue(
                    issue_id=f"health_critical_{int(time.time())}",
                    issue_type="stability",
                    severity="critical",
                    description="システムヘルスがクリティカル状態です",
                    component="system",
                    detected_at=datetime.now().isoformat(),
                    recommendations=["リソース使用率を確認してください", "不要なプロセスを終了してください"],
                    status="detected"
                )
                issues.append(asdict(issue))
                self.issues.append(issue)
        
        # パフォーマンスから問題を検出
        if "performance" in diagnosis_result.get("checks", {}):
            performance = diagnosis_result["checks"]["performance"]
            bottlenecks = performance.get("bottlenecks", [])
            for bottleneck in bottlenecks:
                issue = DiagnosisIssue(
                    issue_id=f"bottleneck_{int(time.time())}",
                    issue_type="performance",
                    severity=bottleneck.get("severity", "medium"),
                    description=bottleneck.get("description", ""),
                    component=bottleneck.get("component", "unknown"),
                    detected_at=datetime.now().isoformat(),
                    recommendations=["パフォーマンス最適化を検討してください"],
                    status="detected"
                )
                issues.append(asdict(issue))
                self.issues.append(issue)
        
        # 設定から問題を検出
        if "configuration" in diagnosis_result.get("checks", {}):
            config = diagnosis_result["checks"]["configuration"]
            config_issues = config.get("issues", [])
            for config_issue in config_issues:
                issue = DiagnosisIssue(
                    issue_id=f"config_{int(time.time())}",
                    issue_type="configuration",
                    severity="medium",
                    description=config_issue.get("message", ""),
                    component=config_issue.get("file", "unknown"),
                    detected_at=datetime.now().isoformat(),
                    recommendations=["設定ファイルを確認してください"],
                    status="detected"
                )
                issues.append(asdict(issue))
                self.issues.append(issue)
        
        self._save_issues()
        
        return issues
    
    def _generate_recommendations(self, diagnosis_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """推奨事項を生成"""
        recommendations = []
        
        # リソース関連の推奨事項
        if "resources" in diagnosis_result.get("checks", {}):
            resources = diagnosis_result["checks"]["resources"]
            warnings = resources.get("warnings", [])
            for warning in warnings:
                if warning["type"] == "high_cpu_usage":
                    recommendations.append({
                        "type": "resource_optimization",
                        "priority": "high",
                        "message": "CPU使用率が高いため、不要なプロセスの終了や負荷分散を検討してください"
                    })
                elif warning["type"] == "high_memory_usage":
                    recommendations.append({
                        "type": "resource_optimization",
                        "priority": "high",
                        "message": "メモリ使用率が高いため、キャッシュのクリアやメモリリークの確認を検討してください"
                    })
                elif warning["type"] == "low_disk_space":
                    recommendations.append({
                        "type": "resource_optimization",
                        "priority": "medium",
                        "message": "ディスク容量が不足しています。不要なファイルの削除を検討してください"
                    })
        
        # パフォーマンス関連の推奨事項
        if "performance" in diagnosis_result.get("checks", {}):
            performance = diagnosis_result["checks"]["performance"]
            bottlenecks = performance.get("bottlenecks", [])
            if bottlenecks:
                recommendations.append({
                    "type": "performance_optimization",
                    "priority": "high",
                    "message": f"{len(bottlenecks)}個のボトルネックが検出されました。パフォーマンス最適化を検討してください"
                })
        
        return recommendations
    
    def get_diagnosis_summary(self) -> Dict[str, Any]:
        """
        診断サマリーを取得
        
        Returns:
            診断サマリー
        """
        recent_diagnoses = [
            d for d in self.diagnosis_history
            if datetime.fromisoformat(d["timestamp"]) > datetime.now() - timedelta(days=7)
        ]
        
        issue_counts = {}
        for issue in self.issues:
            issue_type = issue.issue_type
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        return {
            "total_diagnoses": len(recent_diagnoses),
            "total_issues": len(self.issues),
            "issue_counts": issue_counts,
            "recent_issues": [asdict(issue) for issue in self.issues[-10:]],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        return {
            "diagnosis_history_count": len(self.diagnosis_history),
            "issues_count": len(self.issues),
            "config": self.config,
            "diagnosis_summary": self.get_diagnosis_summary(),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    system = SelfDiagnosisSystem()
    
    # テスト: システム診断
    result = system.diagnose_system()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # テスト: 状態取得
    status = system.get_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()








