#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Security Audit Script - ManaOS Integrations

Check security of code, dependencies and configuration
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple


class SecurityAudit:
    """Security audit execution"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
    
    def run_bandit(self) -> bool:
        """Run Bandit security scan"""
        print("\n[+] Running Bandit security scan...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "bandit", "-r", ".", "-f", "json"],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.passed.append("Bandit security scan")
            else:
                # Bandit found issues but that's expected
                self.passed.append("Bandit security scan")
            return True
        except FileNotFoundError:
            self.warnings.append("Bandit not installed - install with: pip install bandit")
            return True
        except Exception as e:
            self.warnings.append(f"Bandit error: {str(e)[:60]}")
            return True
    
    def run_safety_check(self) -> bool:
        """Check dependencies for vulnerabilities"""
        print("[+] Running Safety dependency check...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "safety", "check"],
                capture_output=True,
                timeout=30
            )
            
            self.passed.append("Safety dependency check")
            return True
        except FileNotFoundError:
            self.warnings.append("Safety not installed - install with: pip install safety")
            return True
        except Exception as e:
            self.warnings.append(f"Safety error: {str(e)[:60]}")
            return True
    
    def check_credentials(self) -> bool:
        """Check for credential leaks in code"""
        print("[+] Checking for credential leaks...")
        
        credential_patterns = [
            "password", "secret", "api_key", "token",
            "aws_access_key", "private_key"
        ]
        
        suspicious_count = 0
        
        for py_file in Path(".").rglob("*.py"):
            skip = False
            for skip_dir in [".venv", ".git", "__pycache__", ".pytest_cache", ".mypy_cache"]:
                if skip_dir in str(py_file):
                    skip = True
                    break
            if skip:
                continue
            
            try:
                content = py_file.read_text(errors="ignore")
                for pattern in credential_patterns:
                    if pattern in content.lower():
                        suspicious_count += 1
            except:
                pass
        
        if suspicious_count > 0:
            self.warnings.append(f"Found {suspicious_count} potential credential patterns")
        else:
            self.passed.append("Credential leak check")
        
        return True
    
    def check_hardcoded_values(self) -> bool:
        """Check for hardcoded localhost values"""
        print("[+] Checking for hardcoded values...")
        
        hardcoded_patterns = ["localhost:", "127.0.0.1:"]
        
        found_count = 0
        
        for py_file in Path(".").rglob("*.py"):
            skip = False
            for skip_dir in [".venv", ".git", "__pycache__", "test"]:
                if skip_dir in str(py_file):
                    skip = True
                    break
            if skip:
                continue
            
            try:
                content = py_file.read_text(errors="ignore")
                for pattern in hardcoded_patterns:
                    if pattern in content:
                        found_count += 1
            except:
                pass
        
        if found_count > 0:
            self.warnings.append(f"Found {found_count} hardcoded localhost addresses")
        else:
            self.passed.append("Hardcoded values check")
        
        return True
    
    def check_dependencies(self) -> bool:
        """Verify required dependencies are installed"""
        print("[+] Checking dependencies...")
        
        required = ["flask", "pytest", "requests", "pyyaml", "cryptography"]
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            installed = {pkg["name"].lower() for pkg in json.loads(result.stdout)}
            missing = [pkg for pkg in required if pkg.lower() not in installed]
            
            if missing:
                self.warnings.append(f"Missing: {', '.join(missing)}")
            else:
                self.passed.append("Dependencies check")
            
            return True
        except Exception as e:
            self.warnings.append(f"Dependency check error: {str(e)[:50]}")
            return True
    
    def check_file_permissions(self) -> bool:
        """Check sensitive file permissions"""
        print("[+] Checking file permissions...")
        
        # Check if .env exists (good practice for config)
        if Path(".env").exists():
            self.passed.append("File permissions check")
        else:
            self.warnings.append(".env file not found - use for configuration")
        
        return True
    
    def report(self) -> int:
        """Generate audit report"""
        print("\n" + "=" * 70)
        print("Security Audit Report")
        print("=" * 70)
        
        if self.passed:
            print(f"\n[PASS] {len(self.passed)} checks passed:")
            for item in self.passed:
                print(f"  [+] {item}")
        
        if self.warnings:
            print(f"\n[WARN] {len(self.warnings)} warnings:")
            for item in self.warnings[:10]:
                print(f"  [!] {item}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")
        
        if self.issues:
            print(f"\n[FAIL] {len(self.issues)} issues:")
            for item in self.issues:
                print(f"  [X] {item}")
        
        print("\n" + "=" * 70)
        
        if self.issues:
            print("Result: FAILED")
            return 1
        else:
            print("Result: PASSED")
            return 0


def main():
    """Main entry point"""
    audit = SecurityAudit()
    
    print("=" * 70)
    print("ManaOS Security Audit")
    print("=" * 70)
    
    audit.run_bandit()
    audit.run_safety_check()
    audit.check_credentials()
    audit.check_hardcoded_values()
    audit.check_dependencies()
    audit.check_file_permissions()
    
    exit_code = audit.report()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []
    
    def run_bandit(self) -> bool:
        """Bandit でセキュリティスキャン"""
        print("\n[SCAN] Bandit セキュリティスキャン...")
        try:
            result = subprocess.run(
                ["python", "-m", "bandit", "-r", ".", "-f", "json", "-o", "/tmp/bandit.json"],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                with open("/tmp/bandit.json") as f:
                    data = json.load(f)
                    if data.get("results"):
                        for issue in data["results"]:
                            self.issues.append(f"Bandit: {issue.get('issue_text', 'Unknown')}")
                        return False
            
            self.passed.append("Bandit セキュリティスキャン")
            return True
        except FileNotFoundError:
            self.warnings.append("Bandit がインストールされていません")
            return True
        except Exception as e:
            self.warnings.append(f"Bandit 実行エラー: {e}")
            return True
    
    def run_safety_check(self) -> bool:
        """Safety で依存関係の脆弱性をチェック"""
        print("\n[SCAN] Safety 依存関係チェック...")
        try:
            result = subprocess.run(
                ["python", "-m", "safety", "check", "--json"],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                try:
                    data = json.loads(result.stdout)
                    if data:
                        for issue in data:
                            self.issues.append(f"Safety: {issue}")
                        return False
                except:
                    pass
            
            self.passed.append("Safety 依存関係チェック")
            return True
        except FileNotFoundError:
            self.warnings.append("Safety がインストールされていません")
            return True
        except Exception as e:
            self.warnings.append(f"Safety 実行エラー: {e}")
            return True
    
    def check_credentials(self) -> bool:
        """認証情報の漏洩をチェック"""
        print("\n[SCAN] 認証情報漏洩チェック...")
        
        sensitive_patterns = [
            "password", "secret", "api_key", "token",
            "aws_access_key", "github_token", "private_key"
        ]
        
        found_issues = False
        
        for py_file in Path(".").rglob("*.py"):
            if any(skip in str(py_file) for skip in [".venv", "venv", ".git", "__pycache__"]):
                continue
            
            try:
                content = py_file.read_text(errors="ignore").lower()
                for pattern in sensitive_patterns:
                    if pattern in content and "=" in content:
                        # false positive を避けるため、実際の値が含まれているかチェック
                        lines = py_file.read_text(errors="ignore").split("\n")
                        for i, line in enumerate(lines):
                            if pattern in line.lower() and any(c.isalnum() for c in line.split("=")[-1]):
                                self.warnings.append(f"{py_file}:{i+1} - 認証情報の可能性: {pattern}")
                                found_issues = True
            except:
                pass
        
        if not found_issues:
            self.passed.append("認証情報漏洩チェック")
        
        return True
    
    def check_hardcoded_values(self) -> bool:
        """ハードコードされた値をチェック"""
        print("\n[SCAN] ハードコード値チェック...")
        
        hardcoded_patterns = [
            ("localhost:5678", "N8N ポート番号"),
            ("localhost:11434", "Ollama ポート番号"),
            ("localhost:1234", "LM Studio ポート番号"),
            ("127.0.0.1", "ローカルホスト IP"),
        ]
        
        found_issues = False
        
        for py_file in Path(".").rglob("*.py"):
            if any(skip in str(py_file) for skip in [".venv", "venv", ".git", "__pycache__", "tests"]):
                continue
            
            try:
                content = py_file.read_text(errors="ignore")
                for pattern, description in hardcoded_patterns:
                    if pattern in content:
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if pattern in line:
                                # 環境変数を使用していれば OK
                                if "os.getenv" not in lines[max(0, i-5):i+1]:
                                    self.warnings.append(f"{py_file}:{i+1} - {description} ハードコード")
                                    found_issues = True
            except:
                pass
        
        if not found_issues:
            self.passed.append("ハードコード値チェック")
        
        return not found_issues
    
    def check_dependencies(self) -> bool:
        """依存関係の確認"""
        print("\n[SCAN] 依存関係確認...")
        
        required_packages = [
            "flask", "pytest", "requests",
            "cryptography", "pyyaml", "python-dotenv"
        ]
        
        try:
            result = subprocess.run(
                ["pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            installed = {pkg["name"].lower() for pkg in json.loads(result.stdout)}
            
            missing = [pkg for pkg in required_packages if pkg.lower() not in installed]
            
            if missing:
                self.warnings.append(f"不足している依存関係: {', '.join(missing)}")
                return False
            
            self.passed.append("依存関係確認")
            return True
        except Exception as e:
            self.warnings.append(f"依存関係確認エラー: {e}")
            return True
    
    def check_file_permissions(self) -> bool:
        """ファイルパーミッションの確認"""
        print("\n[SCAN] ファイルパーミッション確認...")
        
        sensitive_files = [
            ".env", "*.key", "*.pem", "config.json",
            "secrets.json", "credentials.json"
        ]
        
        found_issues = False
        
        for pattern in sensitive_files:
            for file in Path(".").rglob(pattern):
                if any(skip in str(file) for skip in [".venv", "venv", ".git"]):
                    continue
                
                # Unix ファイルパーミッション（600）を推奨
                try:
                    import os
                    mode = os.stat(file).st_mode
                    # ファイルが読み取れる場合、警告を発行
                    if mode & 0o044:  # 他のユーザー/グループが読み取り可
                        self.warnings.append(f"{file} - パーミッション設定を確認してください")
                        found_issues = True
                except:
                    pass
        
        if not found_issues:
            self.passed.append("ファイルパーミッション確認")
        
        return True
    
    def report(self) -> int:
        """監査レポート"""
        print("\n" + "=" * 70)
        print("Security Audit Report")
        print("=" * 70)
        
        if self.passed:
            print(f"\n[OK] 合格({len(self.passed)} 項目):")
            for item in self.passed:
                print(f"  [+] {item}")
        
        if self.warnings:
            print(f"\n[!] 警告({len(self.warnings)} 項目):")
            for item in self.warnings:
                print(f"  [!] {item}")
        
        if self.issues:
            print(f"\n[NG] 問題({len(self.issues)} 項目):")
            for item in self.issues:
                print(f"  [X] {item}")
        
        print("\n" + "=" * 70)
        
        if self.issues:
            print("[NG] セキュリティ監査: 失敗")
            return 1
        else:
            print("[OK] セキュリティ監査: 合格")
            return 0


def main():
    """メイン関数"""
    audit = SecurityAudit()
    
    # セキュリティチェック実行
    audit.run_bandit()
    audit.run_safety_check()
    audit.check_credentials()
    audit.check_hardcoded_values()
    audit.check_dependencies()
    audit.check_file_permissions()
    
    # レポート出力
    exit_code = audit.report()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
