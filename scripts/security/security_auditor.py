#!/usr/bin/env python3
"""
ManaOS Security Auditor - セキュリティ監査スクリプト
API認証、レート制限、環境変数管理、脆弱性スキャンを実施
"""
import os
import sys
import re
import json
from pathlib import Path
from typing import Dict, List, Set
import subprocess


class SecurityAuditor:
    """セキュリティ監査クラス"""
    
    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []
        self.passed: List[str] = []
    
    def add_issue(self, category: str, severity: str, message: str, file: str = None):  # type: ignore
        """セキュリティ問題を記録"""
        self.issues.append({
            "category": category,
            "severity": severity,
            "message": message,
            "file": file
        })
    
    def add_warning(self, category: str, message: str, file: str = None):  # type: ignore
        """警告を記録"""
        self.warnings.append({
            "category": category,
            "message": message,
            "file": file
        })
    
    def add_pass(self, message: str):
        """合格項目を記録"""
        self.passed.append(message)
    
    def check_env_files(self):
        """環境変数ファイルのセキュリティチェック"""
        print("🔍 環境変数ファイルチェック...")
        
        # .envファイルの存在確認
        env_file = self.project_dir / ".env"
        env_example = self.project_dir / ".env.example"
        
        if not env_example.exists():
            self.add_issue(
                "env_management",
                "MEDIUM",
                ".env.example ファイルが存在しません（テンプレートが必要）"
            )
        else:
            self.add_pass(".env.example ファイルが存在します")
        
        if env_file.exists():
            # .envが.gitignoreに含まれているか確認
            gitignore = self.project_dir / ".gitignore"
            if gitignore.exists():
                content = gitignore.read_text(encoding='utf-8')
                if ".env" in content:
                    self.add_pass(".env は .gitignore に含まれています")
                else:
                    self.add_issue(
                        "env_management",
                        "CRITICAL",
                        ".env ファイルが .gitignore に含まれていません（機密情報漏洩リスク）",
                        str(gitignore)
                    )
            
            # .env内の危険なパターンをチェック
            env_content = env_file.read_text(encoding='utf-8')
            dangerous_patterns = [
                (r'PASSWORD=[^#\n]+', "PASSWORD", "パスワードが平文で保存されています"),
                (r'SECRET=[^#\n]+', "SECRET", "シークレットキーが保存されています"),
                (r'API_KEY=[^#\n]+', "API_KEY", "APIキーが保存されています"),
                (r'TOKEN=[^#\n]+', "TOKEN", "トークンが保存されています")
            ]
            
            for pattern, name, desc in dangerous_patterns:
                matches = re.findall(pattern, env_content)
                if matches:
                    # デフォルト値やプレースホルダーでなければ警告
                    for match in matches:
                        if not any(placeholder in match.lower() for placeholder in 
                                 ['your_', 'change_me', 'xxxx', 'example', 'replace']):
                            self.add_warning(
                                "sensitive_data",
                                f"{name} が設定されています（定期的にローテーションを推奨）",
                                str(env_file)
                            )
                            break
    
    def check_api_authentication(self):
        """API認証の実装状況をチェック"""
        print("🔍 API認証チェック...")
        
        api_files = list(self.project_dir.glob("**/*api*.py"))
        api_files.extend(self.project_dir.glob("**/*server*.py"))
        
        auth_keywords = ['@require_auth', 'verify_api_key', 'check_authentication', 
                        'Header(None, alias="X-API-Key")', 'Bearer']
        
        files_with_auth = set()
        files_without_auth = []
        
        for file in api_files:
            if file.is_file() and "test" not in str(file).lower():
                try:
                    content = file.read_text(encoding='utf-8')
                    
                    # FastAPI/Flaskエンドポイントがあるか
                    has_endpoints = bool(re.search(r'@(app|router)\.(get|post|put|delete)', content))
                    
                    if has_endpoints:
                        has_auth = any(keyword in content for keyword in auth_keywords)
                        
                        if has_auth:
                            files_with_auth.add(str(file.relative_to(self.project_dir)))
                        else:
                            files_without_auth.append(str(file.relative_to(self.project_dir)))
                
                except Exception as e:
                    pass
        
        if files_without_auth:
            for f in files_without_auth[:5]:  # 最初の5件のみ表示
                self.add_issue(
                    "authentication",
                    "HIGH",
                    f"API認証が実装されていない可能性があります",
                    f
                )
        
        if files_with_auth:
            self.add_pass(f"{len(files_with_auth)} ファイルで認証が実装されています")
    
    def check_rate_limiting(self):
        """レート制限の実装状況をチェック"""
        print("🔍 レート制限チェック...")
        
        api_files = list(self.project_dir.glob("**/*api*.py"))
        api_files.extend(self.project_dir.glob("**/*server*.py"))
        
        rate_limit_keywords = ['RateLimiter', 'rate_limit', 'throttle', 'Limiter', 
                              '@limiter.limit']
        
        files_with_rate_limit = []
        
        for file in api_files:
            if file.is_file() and "test" not in str(file).lower():
                try:
                    content = file.read_text(encoding='utf-8')
                    if any(keyword in content for keyword in rate_limit_keywords):
                        files_with_rate_limit.append(str(file.relative_to(self.project_dir)))
                except Exception:
                    pass
        
        if files_with_rate_limit:
            self.add_pass(f"{len(files_with_rate_limit)} ファイルでレート制限が実装されています")
        else:
            self.add_warning(
                "rate_limiting",
                "レート制限が実装されていないファイルがあります（DoS攻撃リスク）"
            )
    
    def check_secrets_in_code(self):
        """コード内のハードコードされたシークレットをチェック"""
        print("🔍 ハードコードされたシークレットチェック...")
        
        py_files = list(self.project_dir.rglob("*.py"))
        
        # 除外パターン
        exclude_patterns = ['.venv', 'venv', '__pycache__', 'tests', 'test_', 
                           '.git', 'node_modules']
        
        secret_patterns = [
            (r'(password|passwd|pwd)\s*=\s*["\'](?!.*\{)[^"\']{6,}["\']', "password"),
            (r'(api[_-]?key|apikey)\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', "api_key"),
            (r'(secret[_-]?key|secretkey)\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', "secret"),
            (r'(token)\s*=\s*["\'][a-zA-Z0-9]{20,}["\']', "token"),
        ]
        
        for file in py_files:
            # 除外パターンチェック
            if any(pattern in str(file) for pattern in exclude_patterns):
                continue
            
            try:
                content = file.read_text(encoding='utf-8')
                
                for pattern, secret_type in secret_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # os.getenv や環境変数参照でなければ警告
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line_end = content.find('\n', match.end())
                        line = content[line_start:line_end if line_end != -1 else None]
                        
                        if 'os.getenv' not in line and 'os.environ' not in line:
                            self.add_issue(
                                "hardcoded_secrets",
                                "CRITICAL",
                                f"{secret_type.upper()} がハードコードされている可能性があります",
                                str(file.relative_to(self.project_dir))
                            )
            except Exception:
                pass
    
    def check_dependency_vulnerabilities(self):
        """依存パッケージの脆弱性チェック（pipyやsafetyを使用）"""
        print("🔍 依存パッケージ脆弱性チェック...")
        
        requirements_files = [
            "requirements.txt",
            "requirements-core.txt",
            "requirements-dev.txt"
        ]
        
        has_requirements = False
        for req_file in requirements_files:
            req_path = self.project_dir / req_file
            if req_path.exists():
                has_requirements = True
                
                # safety がインストールされていれば実行
                try:
                    result = subprocess.run(
                        ["safety", "check", "--file", str(req_path), "--json"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        self.add_pass(f"{req_file} に既知の脆弱性はありません")
                    else:
                        try:
                            vulnerabilities = json.loads(result.stdout)
                            for vuln in vulnerabilities[:5]:  # 最初の5件
                                self.add_issue(
                                    "dependencies",
                                    "HIGH",
                                    f"脆弱性検出: {vuln.get('package', 'Unknown')} - {vuln.get('vulnerability', 'Unknown')}",
                                    req_file
                                )
                        except:
                            pass
                
                except FileNotFoundError:
                    self.add_warning(
                        "dependencies",
                        "safety パッケージがインストールされていません（pip install safety で脆弱性チェック推奨）"
                    )
                    break
                except subprocess.TimeoutExpired:
                    self.add_warning("dependencies", f"{req_file} の脆弱性チェックがタイムアウトしました")
                except Exception as e:
                    pass
        
        if not has_requirements:
            self.add_warning("dependencies", "requirements.txt ファイルが見つかりません")
    
    def check_cors_configuration(self):
        """CORS設定のチェック"""
        print("🔍 CORS設定チェック...")
        
        api_files = list(self.project_dir.glob("**/*api*.py"))
        api_files.extend(self.project_dir.glob("**/*server*.py"))
        
        dangerous_cors = []
        
        for file in api_files:
            if file.is_file():
                try:
                    content = file.read_text(encoding='utf-8')
                    
                    # 危険なCORS設定（allow_origins=["*"]）
                    if re.search(r'allow_origins\s*=\s*\["?\*"?\]', content):
                        dangerous_cors.append(str(file.relative_to(self.project_dir)))
                
                except Exception:
                    pass
        
        if dangerous_cors:
            for f in dangerous_cors:
                self.add_issue(
                    "cors",
                    "MEDIUM",
                    "CORSで全オリジンを許可しています（本番環境では制限を推奨）",
                    f
                )
        else:
            self.add_pass("危険なCORS設定は検出されませんでした")
    
    def run_all_checks(self):
        """全セキュリティチェックを実行"""
        print("\n" + "="*70)
        print("🔒 ManaOS セキュリティ監査")
        print("="*70 + "\n")
        
        self.check_env_files()
        self.check_api_authentication()
        self.check_rate_limiting()
        self.check_secrets_in_code()
        self.check_dependency_vulnerabilities()
        self.check_cors_configuration()
        
        self.print_report()
    
    def print_report(self):
        """監査レポートを出力"""
        print("\n" + "="*70)
        print("📊 セキュリティ監査レポート")
        print("="*70)
        
        # 統計
        critical = len([i for i in self.issues if i["severity"] == "CRITICAL"])
        high = len([i for i in self.issues if i["severity"] == "HIGH"])
        medium = len([i for i in self.issues if i["severity"] == "MEDIUM"])
        
        print(f"\n✅ 合格: {len(self.passed)} 項目")
        print(f"⚠️  警告: {len(self.warnings)} 項目")
        print(f"❌ 問題: {len(self.issues)} 項目")
        
        if self.issues:
            print(f"   - 🔴 Critical: {critical}")
            print(f"   - 🟠 High: {high}")
            print(f"   - 🟡 Medium: {medium}")
        
        # Critical問題
        if critical > 0:
            print("\n" + "="*70)
            print("🔴 CRITICAL 問題（即座に対応が必要）")
            print("="*70)
            for issue in [i for i in self.issues if i["severity"] == "CRITICAL"]:
                print(f"\n[{issue['category']}]")
                print(f"  メッセージ: {issue['message']}")
                if issue.get('file'):
                    print(f"  ファイル: {issue['file']}")
        
        # High問題
        if high > 0:
            print("\n" + "="*70)
            print("🟠 HIGH 問題（早期対応が推奨）")
            print("="*70)
            for issue in [i for i in self.issues if i["severity"] == "HIGH"][:10]:
                print(f"\n[{issue['category']}]")
                print(f"  メッセージ: {issue['message']}")
                if issue.get('file'):
                    print(f"  ファイル: {issue['file']}")
        
        # 警告
        if self.warnings:
            print("\n" + "="*70)
            print("⚠️  警告（検討推奨）")
            print("="*70)
            for warning in self.warnings[:10]:
                print(f"\n[{warning['category']}]")
                print(f"  メッセージ: {warning['message']}")
                if warning.get('file'):
                    print(f"  ファイル: {warning['file']}")
        
        # スコア計算
        total_checks = len(self.passed) + len(self.warnings) + len(self.issues)
        if total_checks > 0:
            score = (len(self.passed) / total_checks) * 100
            print("\n" + "="*70)
            print(f"📈 セキュリティスコア: {score:.1f}%")
            
            if score >= 90:
                print("   評価: 🟢 優秀")
            elif score >= 70:
                print("   評価: 🟡 良好（改善の余地あり）")
            elif score >= 50:
                print("   評価: 🟠 要改善")
            else:
                print("   評価: 🔴 緊急対応が必要")
        
        print("="*70 + "\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="ManaOS セキュリティ監査スクリプト")
    parser.add_argument("--dir", default=".", help="プロジェクトディレクトリ")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    
    args = parser.parse_args()
    
    auditor = SecurityAuditor(args.dir)
    auditor.run_all_checks()
    
    if args.json:
        output = {
            "passed": auditor.passed,
            "warnings": auditor.warnings,
            "issues": auditor.issues
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
