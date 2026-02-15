#!/usr/bin/env python3
"""
🛡️ ManaOS 自己保護システム
セキュリティ脅威の自動検知、自動防御機能
"""

import json
import time
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import deque

# 統一モジュールのインポート
from manaos_logger import get_logger
from manaos_error_handler import ManaOSErrorHandler
from manaos_timeout_config import get_timeout_config
from manaos_config_validator import ConfigValidator

# ロガーの初期化
logger = get_service_logger("self-protection-system")

# エラーハンドラーの初期化
error_handler = ManaOSErrorHandler("SelfProtectionSystem")

# タイムアウト設定の取得
timeout_config = get_timeout_config()

# 設定ファイル検証の初期化
config_validator = ConfigValidator("SelfProtectionSystem")


@dataclass
class SecurityThreat:
    """セキュリティ脅威"""
    threat_id: str
    threat_type: str  # "unauthorized_access", "malicious_code", "data_breach", "dos"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    source: str
    detected_at: str
    status: str  # "detected", "blocked", "investigating", "resolved"
    actions_taken: List[str]


class SelfProtectionSystem:
    """自己保護システム"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.config_path = config_path or Path(__file__).parent / "self_protection_config.json"
        self.config = self._load_config()
        
        # 脅威履歴
        self.threats: List[SecurityThreat] = []
        self.threats_storage = Path("security_threats.json")
        self._load_threats()
        
        # アクセスパターン
        self.access_patterns: deque = deque(maxlen=1000)
        
        # ブロックリスト
        self.blocked_ips: set = set()
        self.blocked_patterns: List[str] = []
        
        # コールバック関数
        self.on_threat_detected = None
        
        logger.info("✅ Self Protection System初期化完了")
    
    def _load_config(self) -> Dict[str, Any]:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"設定読み込みエラー: {e}")
        
        return {
            "enable_threat_detection": True,
            "enable_auto_block": True,
            "enable_pattern_learning": True,
            "max_failed_attempts": 5,
            "block_duration_minutes": 60
        }
    
    def _load_threats(self):
        """脅威履歴を読み込む"""
        if self.threats_storage.exists():
            try:
                with open(self.threats_storage, 'r', encoding='utf-8') as f:
                    threats_data = json.load(f)
                    self.threats = [
                        SecurityThreat(**item) for item in threats_data
                    ]
            except Exception as e:
                logger.warning(f"脅威履歴読み込みエラー: {e}")
    
    def _save_threats(self):
        """脅威履歴を保存"""
        try:
            threats_data = [asdict(threat) for threat in self.threats[-100:]]
            with open(self.threats_storage, 'w', encoding='utf-8') as f:
                json.dump(threats_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"脅威履歴保存エラー: {e}")
    
    def detect_threat(self, request_data: Dict[str, Any]) -> Optional[SecurityThreat]:
        """
        脅威を検知
        
        Args:
            request_data: リクエストデータ
            
        Returns:
            検知された脅威（検知されない場合はNone）
        """
        if not self.config.get("enable_threat_detection", True):
            return None
        
        # IPアドレスの取得
        ip_address = request_data.get("ip_address", "unknown")
        
        # アクセスパターンを記録
        self.access_patterns.append({
            "ip": ip_address,
            "timestamp": datetime.now().isoformat(),
            "path": request_data.get("path", ""),
            "method": request_data.get("method", "")
        })
        
        # ブロックリストチェック
        if ip_address in self.blocked_ips:
            threat = SecurityThreat(
                threat_id=f"blocked_{int(time.time())}",
                threat_type="unauthorized_access",
                severity="high",
                description=f"ブロック済みIPからのアクセス: {ip_address}",
                source=ip_address,
                detected_at=datetime.now().isoformat(),
                status="blocked",
                actions_taken=["access_blocked"]
            )
            self.threats.append(threat)
            self._save_threats()
            return threat
        
        # 異常なアクセスパターンの検出
        recent_accesses = [
            acc for acc in self.access_patterns
            if acc["ip"] == ip_address
            and datetime.fromisoformat(acc["timestamp"]) > datetime.now() - timedelta(minutes=5)
        ]
        
        if len(recent_accesses) > self.config.get("max_failed_attempts", 5):
            threat = SecurityThreat(
                threat_id=f"dos_{int(time.time())}",
                threat_type="dos",
                severity="medium",
                description=f"異常なアクセス頻度: {ip_address}",
                source=ip_address,
                detected_at=datetime.now().isoformat(),
                status="detected",
                actions_taken=[]
            )
            
            # 自動ブロック
            if self.config.get("enable_auto_block", True):
                self.block_ip(ip_address)
                threat.actions_taken.append("auto_blocked")
                threat.status = "blocked"
            
            self.threats.append(threat)
            self._save_threats()
            return threat
        
        # 悪意のあるパターンの検出
        path = request_data.get("path", "")
        if any(pattern in path.lower() for pattern in ["../", "..\\", "cmd", "exec", "eval"]):
            threat = SecurityThreat(
                threat_id=f"malicious_{int(time.time())}",
                threat_type="malicious_code",
                severity="high",
                description=f"悪意のあるパスパターン: {path}",
                source=ip_address,
                detected_at=datetime.now().isoformat(),
                status="detected",
                actions_taken=[]
            )
            
            # 自動ブロック
            if self.config.get("enable_auto_block", True):
                self.block_ip(ip_address)
                threat.actions_taken.append("auto_blocked")
                threat.status = "blocked"
            
            self.threats.append(threat)
            self._save_threats()
            
            # 脅威検知時にコールバックを実行
            if self.on_threat_detected:
                try:
                    self.on_threat_detected(asdict(threat))
                except Exception as e:
                    logger.warning(f"脅威検知コールバックエラー: {e}")
            
            return threat
        
        return None
    
    def block_ip(self, ip_address: str, duration_minutes: Optional[int] = None):
        """
        IPアドレスをブロック
        
        Args:
            ip_address: ブロックするIPアドレス
            duration_minutes: ブロック期間（分、Noneの場合は設定値を使用）
        """
        self.blocked_ips.add(ip_address)
        logger.warning(f"IPアドレスをブロックしました: {ip_address}")
    
    def unblock_ip(self, ip_address: str):
        """
        IPアドレスのブロックを解除
        
        Args:
            ip_address: ブロック解除するIPアドレス
        """
        self.blocked_ips.discard(ip_address)
        logger.info(f"IPアドレスのブロックを解除しました: {ip_address}")
    
    def learn_threat_pattern(self, threat: SecurityThreat):
        """
        脅威パターンを学習
        
        Args:
            threat: 脅威オブジェクト
        """
        if not self.config.get("enable_pattern_learning", True):
            return
        
        # 脅威パターンを学習（簡易版）
        # 実際の実装では、機械学習モデルを使用する
        logger.info(f"脅威パターンを学習しました: {threat.threat_type}")
    
    def get_threat_summary(self) -> Dict[str, Any]:
        """
        脅威サマリーを取得
        
        Returns:
            脅威サマリー
        """
        recent_threats = [
            threat for threat in self.threats
            if datetime.fromisoformat(threat.detected_at) > datetime.now() - timedelta(days=7)
        ]
        
        threat_counts = {}
        for threat in recent_threats:
            threat_type = threat.threat_type
            threat_counts[threat_type] = threat_counts.get(threat_type, 0) + 1
        
        return {
            "total_threats": len(recent_threats),
            "threat_counts": threat_counts,
            "blocked_ips_count": len(self.blocked_ips),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """状態を取得"""
        # 最近の脅威の分析
        recent_threats = [
            threat for threat in self.threats
            if datetime.fromisoformat(threat.detected_at) > datetime.now() - timedelta(hours=24)
        ]
        
        # 脅威検知精度の計算（簡易版）
        detected_threats = len([t for t in recent_threats if t.status in ["detected", "blocked"]])
        total_attempts = len(self.access_patterns)
        detection_rate = detected_threats / max(total_attempts, 1) if total_attempts > 0 else 0.0
        
        return {
            "threats_count": len(self.threats),
            "recent_threats_count": len(recent_threats),
            "blocked_ips_count": len(self.blocked_ips),
            "access_patterns_count": len(self.access_patterns),
            "detection_rate": detection_rate,
            "threat_detection_enabled": self.config.get("enable_threat_detection", True),
            "auto_block_enabled": self.config.get("enable_auto_block", True),
            "pattern_learning_enabled": self.config.get("enable_pattern_learning", True),
            "config": self.config,
            "threat_summary": self.get_threat_summary(),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    system = SelfProtectionSystem()
    
    # テスト: 脅威検知
    threat = system.detect_threat({
        "ip_address": "192.168.1.100",
        "path": "/api/../etc/passwd",
        "method": "GET"
    })
    
    if threat:
        print(f"脅威を検知: {threat.description}")
    
    # テスト: 状態取得
    status = system.get_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

