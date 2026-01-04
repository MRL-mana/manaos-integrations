"""
セキュリティ監視システム
自動監視と保護
"""

import json
import hashlib
import hmac
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

import requests


class SecurityMonitor:
    """セキュリティ監視システム"""
    
    def __init__(self, secret_key: str = "manaos-secret-key"):
        """
        初期化
        
        Args:
            secret_key: シークレットキー
        """
        self.secret_key = secret_key
        self.failed_attempts = deque(maxlen=100)
        self.suspicious_activities = []
        self.blocked_ips = set()
        self.allowed_ips = set()
        self.storage_path = Path("security_monitor_state.json")
        self._load_state()
    
    def _load_state(self):
        """状態を読み込み"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.failed_attempts = deque(state.get("failed_attempts", []), maxlen=100)
                    self.suspicious_activities = state.get("suspicious_activities", [])[-100:]
                    self.blocked_ips = set(state.get("blocked_ips", []))
                    self.allowed_ips = set(state.get("allowed_ips", []))
            except:
                self.failed_attempts = deque(maxlen=100)
                self.suspicious_activities = []
                self.blocked_ips = set()
                self.allowed_ips = set()
        else:
            self.failed_attempts = deque(maxlen=100)
            self.suspicious_activities = []
            self.blocked_ips = set()
            self.allowed_ips = set()
    
    def _save_state(self):
        """状態を保存"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "failed_attempts": list(self.failed_attempts),
                    "suspicious_activities": self.suspicious_activities[-100:],
                    "blocked_ips": list(self.blocked_ips),
                    "allowed_ips": list(self.allowed_ips),
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"状態保存エラー: {e}")
    
    def generate_hmac(self, data: str) -> str:
        """
        HMACを生成
        
        Args:
            data: データ
            
        Returns:
            HMAC文字列
        """
        return hmac.new(
            self.secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_hmac(self, data: str, signature: str) -> bool:
        """
        HMACを検証
        
        Args:
            data: データ
            signature: 署名
            
        Returns:
            検証成功時True
        """
        expected_signature = self.generate_hmac(data)
        return hmac.compare_digest(expected_signature, signature)
    
    def record_failed_attempt(self, ip: str, reason: str):
        """
        失敗試行を記録
        
        Args:
            ip: IPアドレス
            reason: 理由
        """
        attempt = {
            "ip": ip,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        self.failed_attempts.append(attempt)
        
        # 5回以上失敗した場合はブロック
        recent_failures = [a for a in self.failed_attempts if a["ip"] == ip]
        if len(recent_failures) >= 5:
            self.block_ip(ip, "複数の失敗試行")
        
        self._save_state()
    
    def block_ip(self, ip: str, reason: str):
        """
        IPをブロック
        
        Args:
            ip: IPアドレス
            reason: 理由
        """
        self.blocked_ips.add(ip)
        
        activity = {
            "type": "ip_blocked",
            "ip": ip,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        
        self.suspicious_activities.append(activity)
        self._save_state()
    
    def unblock_ip(self, ip: str):
        """
        IPのブロックを解除
        
        Args:
            ip: IPアドレス
        """
        self.blocked_ips.discard(ip)
        self._save_state()
    
    def is_ip_blocked(self, ip: str) -> bool:
        """
        IPがブロックされているか確認
        
        Args:
            ip: IPアドレス
            
        Returns:
            ブロックされている場合True
        """
        return ip in self.blocked_ips
    
    def is_ip_allowed(self, ip: str) -> bool:
        """
        IPが許可されているか確認
        
        Args:
            ip: IPアドレス
            
        Returns:
            許可されている場合True
        """
        return ip in self.allowed_ips
    
    def check_request_security(
        self,
        ip: str,
        endpoint: str,
        method: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        リクエストのセキュリティをチェック
        
        Args:
            ip: IPアドレス
            endpoint: エンドポイント
            method: HTTPメソッド
            headers: ヘッダー
            
        Returns:
            チェック結果
        """
        result = {
            "allowed": True,
            "reasons": []
        }
        
        # IPブロックチェック
        if self.is_ip_blocked(ip):
            result["allowed"] = False
            result["reasons"].append("IPがブロックされています")
            return result
        
        # 許可リストチェック
        if self.allowed_ips and not self.is_ip_allowed(ip):
            result["allowed"] = False
            result["reasons"].append("IPが許可リストにありません")
            return result
        
        # 疑わしいエンドポイントチェック
        suspicious_endpoints = ["/admin", "/root", "/etc"]
        if any(sus in endpoint for sus in suspicious_endpoints):
            result["allowed"] = False
            result["reasons"].append("疑わしいエンドポイントへのアクセス")
            self.record_failed_attempt(ip, f"疑わしいエンドポイント: {endpoint}")
        
        # レート制限チェック
        recent_attempts = [
            a for a in self.failed_attempts
            if a["ip"] == ip and
            datetime.fromisoformat(a["timestamp"]) > datetime.now() - timedelta(minutes=1)
        ]
        if len(recent_attempts) > 10:
            result["allowed"] = False
            result["reasons"].append("レート制限を超過")
            self.block_ip(ip, "レート制限超過")
        
        return result
    
    def scan_for_vulnerabilities(self) -> List[Dict[str, Any]]:
        """
        脆弱性をスキャン
        
        Returns:
            脆弱性のリスト
        """
        vulnerabilities = []
        
        # デフォルト認証情報チェック
        default_credentials = [
            ("admin", "admin"),
            ("root", "root"),
            ("user", "password")
        ]
        
        # 古い依存関係チェック
        # 実際の実装では、requirements.txtを解析して古いバージョンを検出
        
        # 設定ファイルのセキュリティチェック
        # 実際の実装では、設定ファイルを解析して問題を検出
        
        return vulnerabilities
    
    def get_security_status(self) -> Dict[str, Any]:
        """セキュリティ状態を取得"""
        return {
            "blocked_ips_count": len(self.blocked_ips),
            "allowed_ips_count": len(self.allowed_ips),
            "failed_attempts_count": len(self.failed_attempts),
            "suspicious_activities_count": len(self.suspicious_activities),
            "recent_failures": list(self.failed_attempts)[-10:],
            "recent_activities": self.suspicious_activities[-10:],
            "timestamp": datetime.now().isoformat()
        }


def main():
    """テスト用メイン関数"""
    print("セキュリティ監視システムテスト")
    print("=" * 60)
    
    monitor = SecurityMonitor()
    
    # HMAC生成・検証テスト
    print("\nHMAC生成・検証テスト:")
    data = "test data"
    signature = monitor.generate_hmac(data)
    print(f"  データ: {data}")
    print(f"  署名: {signature}")
    print(f"  検証: {monitor.verify_hmac(data, signature)}")
    
    # リクエストセキュリティチェック
    print("\nリクエストセキュリティチェック:")
    result = monitor.check_request_security(
        ip="192.168.1.100",
        endpoint="/api/test",
        method="GET",
        headers={}
    )
    print(f"  結果: {result}")
    
    # 状態を表示
    status = monitor.get_security_status()
    print(f"\nセキュリティ状態:")
    print(f"  ブロックされたIP数: {status['blocked_ips_count']}")
    print(f"  失敗試行数: {status['failed_attempts_count']}")


if __name__ == "__main__":
    main()




















