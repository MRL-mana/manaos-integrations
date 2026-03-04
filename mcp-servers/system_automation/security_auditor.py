#!/usr/bin/env python3
"""
セキュリティ監査システム
セキュリティチェック、脆弱性スキャン、コンプライアンス確認
"""

import subprocess
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityAuditor:
    """セキュリティ監査システム"""
    
    def __init__(self, base_path: str = "/root"):
        self.base_path = Path(base_path)
        self.config_path = self.base_path / ".security_config.json"
        self.report_path = self.base_path / "security_audit_report.json"
        
        self.default_config = {
            "enabled": True,
            "checks": {
                "file_permissions": True,
                "weak_passwords": True,
                "open_ports": True,
                "ssl_certificates": True,
                "firewall": True,
                "suspicious_files": True,
                "api_keys": True,
                "log_files": True
            },
            "severity_levels": {
                "critical": 10,
                "high": 7,
                "medium": 4,
                "low": 1
            }
        }
        
        self.config = self.load_config()
        
    def load_config(self) -> dict:
        """設定を読み込む"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"設定読み込みエラー: {e}")
                return self.default_config
        return self.default_config
    
    def save_config(self):
        """設定を保存"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def check_file_permissions(self) -> List[Dict]:
        """ファイル権限チェック"""
        logger.info("🔍 ファイル権限チェック中...")
        
        issues = []
        
        # 重要なファイルの権限チェック
        critical_files = [
            "/etc/passwd",
            "/etc/shadow",
            "/etc/hosts",
            "/root/.ssh/authorized_keys",
            "/root/.bashrc"
        ]
        
        for file_path in critical_files:
            path = Path(file_path)
            if path.exists():
                stat = path.stat()
                mode = oct(stat.st_mode)[-3:]
                
                # 権限が緩すぎる場合
                if mode in ["666", "777", "664", "775"]:
                    issues.append({
                        "type": "file_permission",
                        "severity": "high",
                        "file": file_path,
                        "permission": mode,
                        "message": f"ファイル権限が緩すぎます: {mode}"
                    })
        
        logger.info(f"✅ ファイル権限チェック完了: {len(issues)}件の問題")
        return issues
    
    def check_weak_passwords(self) -> List[Dict]:
        """弱いパスワードチェック"""
        logger.info("🔍 弱いパスワードチェック中...")
        
        issues = []
        
        # パスワードファイルをチェック
        passwd_file = Path("/etc/passwd")
        if passwd_file.exists():
            with open(passwd_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(':')
                    if len(parts) >= 2:
                        username = parts[0]
                        # パスワードが設定されていない
                        if parts[1] == '':
                            issues.append({
                                "type": "weak_password",
                                "severity": "critical",
                                "user": username,
                                "message": f"ユーザー {username} にパスワードが設定されていません"
                            })
        
        logger.info(f"✅ 弱いパスワードチェック完了: {len(issues)}件の問題")
        return issues
    
    def check_open_ports(self) -> List[Dict]:
        """開いているポートチェック"""
        logger.info("🔍 開いているポートチェック中...")
        
        issues = []
        
        try:
            # netstatまたはssコマンドでポートを確認
            result = subprocess.run(
                ["ss", "-tuln"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # ヘッダーをスキップ
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        state = parts[0]
                        local_addr = parts[4]
                        
                        # リスニングポートをチェック
                        if state == "LISTEN":
                            # 外部からアクセス可能なポート
                            if ":0.0.0.0:" in local_addr or ":::0" in local_addr:
                                port = local_addr.split(':')[-1]
                                
                                # 危険なポート
                                dangerous_ports = ["22", "80", "443", "3306", "5432", "6379", "27017"]
                                if port in dangerous_ports:
                                    issues.append({
                                        "type": "open_port",
                                        "severity": "medium",
                                        "port": port,
                                        "address": local_addr,
                                        "message": f"ポート {port} が外部からアクセス可能です"
                                    })
        
        except Exception as e:
            logger.error(f"ポートチェックエラー: {e}")
        
        logger.info(f"✅ 開いているポートチェック完了: {len(issues)}件の問題")
        return issues
    
    def check_ssl_certificates(self) -> List[Dict]:
        """SSL証明書チェック"""
        logger.info("🔍 SSL証明書チェック中...")
        
        issues = []
        
        # 証明書ファイルをチェック
        cert_dirs = [
            "/etc/ssl/certs",
            "/etc/letsencrypt/live"
        ]
        
        for cert_dir in cert_dirs:
            path = Path(cert_dir)
            if path.exists():
                for cert_file in path.glob("*.pem"):
                    try:
                        result = subprocess.run(
                            ["openssl", "x509", "-in", str(cert_file), "-noout", "-dates"],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        if result.returncode == 0:
                            # 有効期限をチェック
                            for line in result.stdout.split('\n'):
                                if 'notAfter' in line:
                                    # TODO: 有効期限の解析とチェック
                                    pass
                    
                    except Exception as e:
                        logger.error(f"証明書チェックエラー {cert_file}: {e}")
        
        logger.info(f"✅ SSL証明書チェック完了: {len(issues)}件の問題")
        return issues
    
    def check_firewall(self) -> List[Dict]:
        """ファイアウォールチェック"""
        logger.info("🔍 ファイアウォールチェック中...")
        
        issues = []
        
        try:
            # ufwの状態をチェック
            result = subprocess.run(
                ["ufw", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                if "Status: inactive" in result.stdout:
                    issues.append({
                        "type": "firewall",
                        "severity": "critical",
                        "message": "ファイアウォールが無効です"
                    })
        
        except Exception:
            # ufwがインストールされていない場合
            issues.append({
                "type": "firewall",
                "severity": "medium",
                "message": "ファイアウォールが設定されていません"
            })
        
        logger.info(f"✅ ファイアウォールチェック完了: {len(issues)}件の問題")
        return issues
    
    def check_suspicious_files(self) -> List[Dict]:
        """怪しいファイルチェック"""
        logger.info("🔍 怪しいファイルチェック中...")
        
        issues = []
        
        # 怪しいファイル名のパターン
        suspicious_patterns = [
            "*backdoor*",
            "*trojan*",
            "*virus*",
            "*malware*",
            ".hidden",
            "*.exe",
            "*.bat",
            "*.cmd"
        ]
        
        for pattern in suspicious_patterns:
            for file_path in self.base_path.glob(pattern):
                if file_path.is_file():
                    issues.append({
                        "type": "suspicious_file",
                        "severity": "high",
                        "file": str(file_path),
                        "message": f"怪しいファイルが検出されました: {file_path.name}"
                    })
        
        logger.info(f"✅ 怪しいファイルチェック完了: {len(issues)}件の問題")
        return issues
    
    def check_api_keys(self) -> List[Dict]:
        """APIキーの漏洩チェック"""
        logger.info("🔍 APIキー漏洩チェック中...")
        
        issues = []
        
        # APIキーのパターン
        api_key_patterns = [
            (r'sk-[a-zA-Z0-9]{32,}', "OpenAI API Key"),
            (r'AIza[0-9A-Za-z-_]{35}', "Google API Key"),
            (r'AKIA[0-9A-Z]{16}', "AWS Access Key"),
            (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
            (r'xox[baprs]-[a-zA-Z0-9-]{10,}', "Slack Token"),
            (r'xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}', "Slack Token (full)")
        ]
        
        # チェック対象のファイル
        check_extensions = ['.py', '.js', '.json', '.env', '.txt', '.md', '.sh']
        
        for ext in check_extensions:
            for file_path in self.base_path.rglob(f'*{ext}'):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            for pattern, key_type in api_key_patterns:
                                if re.search(pattern, content):
                                    issues.append({
                                        "type": "api_key_leak",
                                        "severity": "critical",
                                        "file": str(file_path),
                                        "key_type": key_type,
                                        "message": f"{key_type} が検出されました: {file_path.name}"
                                    })
                                    break
                    
                    except Exception as e:
                        logger.error(f"ファイル読み込みエラー {file_path}: {e}")
        
        logger.info(f"✅ APIキー漏洩チェック完了: {len(issues)}件の問題")
        return issues
    
    def check_log_files(self) -> List[Dict]:
        """ログファイルチェック"""
        logger.info("🔍 ログファイルチェック中...")
        
        issues = []
        
        # ログディレクトリ
        log_dirs = [
            "/var/log",
            "/root/logs"
        ]
        
        for log_dir in log_dirs:
            path = Path(log_dir)
            if path.exists():
                for log_file in path.rglob("*.log"):
                    try:
                        # ファイルサイズチェック
                        size_mb = log_file.stat().st_size / (1024 * 1024)
                        
                        if size_mb > 100:  # 100MB以上
                            issues.append({
                                "type": "log_file_size",
                                "severity": "low",
                                "file": str(log_file),
                                "size_mb": round(size_mb, 2),
                                "message": f"ログファイルが大きすぎます: {size_mb:.2f} MB"
                            })
                        
                        # エラーログをチェック
                        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()[-100:]  # 最後の100行
                            
                            error_count = sum(1 for line in lines if 'error' in line.lower() or 'exception' in line.lower())
                            
                            if error_count > 10:
                                issues.append({
                                    "type": "log_errors",
                                    "severity": "medium",
                                    "file": str(log_file),
                                    "error_count": error_count,
                                    "message": f"多数のエラーが検出されました: {error_count}件"
                                })
                    
                    except Exception as e:
                        logger.error(f"ログファイルチェックエラー {log_file}: {e}")
        
        logger.info(f"✅ ログファイルチェック完了: {len(issues)}件の問題")
        return issues
    
    def run_full_audit(self) -> Dict:
        """フル監査実行"""
        logger.info("=" * 60)
        logger.info("🔒 セキュリティ監査開始")
        logger.info("=" * 60)
        
        all_issues = []
        
        # 各チェックを実行
        if self.config["checks"]["file_permissions"]:
            all_issues.extend(self.check_file_permissions())
        
        if self.config["checks"]["weak_passwords"]:
            all_issues.extend(self.check_weak_passwords())
        
        if self.config["checks"]["open_ports"]:
            all_issues.extend(self.check_open_ports())
        
        if self.config["checks"]["ssl_certificates"]:
            all_issues.extend(self.check_ssl_certificates())
        
        if self.config["checks"]["firewall"]:
            all_issues.extend(self.check_firewall())
        
        if self.config["checks"]["suspicious_files"]:
            all_issues.extend(self.check_suspicious_files())
        
        if self.config["checks"]["api_keys"]:
            all_issues.extend(self.check_api_keys())
        
        if self.config["checks"]["log_files"]:
            all_issues.extend(self.check_log_files())
        
        # 結果を集計
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_issues": len(all_issues),
            "by_severity": {
                "critical": len([i for i in all_issues if i["severity"] == "critical"]),
                "high": len([i for i in all_issues if i["severity"] == "high"]),
                "medium": len([i for i in all_issues if i["severity"] == "medium"]),
                "low": len([i for i in all_issues if i["severity"] == "low"])
            },
            "by_type": {},
            "issues": all_issues,
            "security_score": self.calculate_security_score(all_issues)
        }
        
        # タイプ別集計
        for issue in all_issues:
            issue_type = issue["type"]
            report["by_type"][issue_type] = report["by_type"].get(issue_type, 0) + 1
        
        # レポート保存
        with open(self.report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info("=" * 60)
        logger.info("✅ セキュリティ監査完了")
        logger.info(f"   総問題数: {report['total_issues']}")
        logger.info(f"   セキュリティスコア: {report['security_score']}/100")
        logger.info("=" * 60)
        
        return report
    
    def calculate_security_score(self, issues: List[Dict]) -> int:
        """セキュリティスコア計算"""
        score = 100
        
        for issue in issues:
            severity = issue["severity"]
            penalty = self.config["severity_levels"].get(severity, 0)
            score -= penalty
        
        return max(0, score)


def main():
    """メイン実行"""
    auditor = SecurityAuditor()
    
    print("=" * 60)
    print("🔒 セキュリティ監査システム")
    print("=" * 60)
    
    print("\n📊 監査設定:")
    for check, enabled in auditor.config["checks"].items():
        status = "✅" if enabled else "❌"
        print(f"  {status} {check}")
    
    print("\n実行する操作を選択:")
    print("  1. フル監査実行")
    print("  2. ファイル権限チェック")
    print("  3. 弱いパスワードチェック")
    print("  4. 開いているポートチェック")
    print("  5. APIキー漏洩チェック")
    print("  0. 終了")
    
    choice = input("\n選択 (0-5): ").strip()
    
    if choice == "1":
        print("\n🔒 フル監査実行中...")
        report = auditor.run_full_audit()
        
        print("\n📊 監査結果:")
        print(f"  総問題数: {report['total_issues']}")
        print(f"  セキュリティスコア: {report['security_score']}/100")
        print("\n  重大度別:")
        for severity, count in report['by_severity'].items():
            if count > 0:
                print(f"    {severity}: {count}件")
        
        # 重大な問題を表示
        critical_issues = [i for i in report['issues'] if i['severity'] in ['critical', 'high']]
        if critical_issues:
            print("\n⚠️  重大な問題:")
            for issue in critical_issues[:5]:
                print(f"    [{issue['severity'].upper()}] {issue['message']}")
    
    elif choice == "2":
        issues = auditor.check_file_permissions()
        print(f"\n✅ ファイル権限チェック完了: {len(issues)}件")
    
    elif choice == "3":
        issues = auditor.check_weak_passwords()
        print(f"\n✅ 弱いパスワードチェック完了: {len(issues)}件")
    
    elif choice == "4":
        issues = auditor.check_open_ports()
        print(f"\n✅ 開いているポートチェック完了: {len(issues)}件")
    
    elif choice == "5":
        issues = auditor.check_api_keys()
        print(f"\n✅ APIキー漏洩チェック完了: {len(issues)}件")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

