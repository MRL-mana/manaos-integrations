#!/usr/bin/env python3
"""
Security Audit Enhanced
拡張セキュリティ監査システム
"""

import os
import re
import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityAuditEnhanced:
    def __init__(self):
        self.audit_db = "/root/security_audit.db"
        self.report_path = "/root/security_audit_reports"
        os.makedirs(self.report_path, exist_ok=True)
        
        self.init_database()
        
        # 除外パス（スキャン不要）
        self.exclude_paths = [
            "/root/node_modules",
            "/root/.git",
            "/root/.cursor-server",
            "/root/.cache",
            "/root/snap"
        ]
        
        # 機密情報パターン
        self.sensitive_patterns = {
            "api_key": r'(api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})',
            "secret": r'(secret|password|passwd)\s*[=:]\s*["\']?([^\s"\';]+)',
            "token": r'(token|bearer)\s*[=:]\s*["\']?([a-zA-Z0-9_\-\.]{20,})',
            "aws": r'(AKIA[0-9A-Z]{16})',
            "google_api": r'AIza[0-9A-Za-z\-_]{35}',
            "private_key": r'-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----'
        }
        
        logger.info("🔐 Security Audit Enhanced 初期化完了")
    
    def init_database(self):
        """データベース初期化"""
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        # 監査結果テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_date TEXT,
                security_score INTEGER,
                critical_issues INTEGER,
                high_issues INTEGER,
                medium_issues INTEGER,
                low_issues INTEGER,
                findings TEXT,
                recommendations TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 検出された機密情報テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensitive_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER,
                file_path TEXT,
                pattern_type TEXT,
                line_number INTEGER,
                severity TEXT,
                resolved BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ポート監視テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS port_monitoring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER,
                port INTEGER,
                service TEXT,
                is_authenticated BOOLEAN,
                is_public BOOLEAN,
                risk_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def scan_sensitive_files(self) -> List[Dict[str, Any]]:
        """機密情報ファイルスキャン"""
        findings = []
        
        logger.info("機密情報ファイルをスキャン中...")
        
        # スキャン対象のファイルパターン
        scan_patterns = [
            "*.env",
            "*credentials*.json",
            "*token*",
            "*secret*",
            "*.key",
            "*.pem"
        ]
        
        for pattern in scan_patterns:
            try:
                result = subprocess.run(
                    f"find /root -name '{pattern}' -type f 2>/dev/null | head -50",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                files = result.stdout.strip().split('\n')
                for filepath in files:
                    if not filepath or any(ex in filepath for ex in self.exclude_paths):
                        continue
                    
                    # Vault内は除外
                    if "/.mana_vault/" in filepath:
                        continue
                    
                    # ファイルの内容をチェック
                    try:
                        with open(filepath, 'r', errors='ignore') as f:
                            content = f.read(10000)  # 最初の10KB
                            
                        for pattern_name, pattern in self.sensitive_patterns.items():
                            matches = re.findall(pattern, content, re.I)
                            if matches:
                                findings.append({
                                    "file": filepath,
                                    "pattern_type": pattern_name,
                                    "matches": len(matches),
                                    "severity": "high" if pattern_name in ["api_key", "secret", "aws"] else "medium"
                                })
                                
                    except Exception as e:
                        logger.debug(f"ファイル読み込みエラー: {filepath} - {e}")
                        
            except Exception as e:
                logger.error(f"スキャンエラー ({pattern}): {e}")
        
        logger.info(f"機密情報ファイル: {len(findings)}件検出")
        return findings
    
    def check_port_security(self) -> List[Dict[str, Any]]:
        """ポートセキュリティチェック"""
        ports = []
        
        logger.info("公開ポートをチェック中...")
        
        try:
            result = subprocess.run(
                "netstat -tlnp 2>/dev/null | grep LISTEN || ss -tlnp | grep LISTEN",
                shell=True,
                capture_output=True,
                text=True
            )
            
            lines = result.stdout.strip().split('\n')
            for line in lines:
                # ポート番号を抽出
                match = re.search(r'0\.0\.0\.0:(\d+)|:::(\d+)', line)
                if not match:
                    continue
                
                port = int(match.group(1) or match.group(2))
                
                # サービス名を取得
                service_match = re.search(r'(\d+)/(\S+)', line)
                service = service_match.group(2) if service_match else "unknown"
                
                # リスクレベル判定
                risk_level = "low"
                is_authenticated = False
                
                # 既知の安全なポート
                safe_ports = {
                    9200: "ManaOS Orchestrator",
                    9201: "ManaOS Intention",
                    9202: "ManaOS Policy",
                    9203: "ManaOS Actuator",
                    9204: "ManaOS Ingestor",
                    9205: "ManaOS Insight",
                    5008: "Screen Sharing"
                }
                
                if port in safe_ports:
                    is_authenticated = True
                    risk_level = "low"
                elif port < 1024:
                    risk_level = "medium"
                elif port in [8888, 8000, 3000, 5000]:
                    risk_level = "high"  # 一般的な開発ポート
                else:
                    risk_level = "medium"
                
                ports.append({
                    "port": port,
                    "service": service,
                    "is_authenticated": is_authenticated,
                    "is_public": True,
                    "risk_level": risk_level
                })
                
        except Exception as e:
            logger.error(f"ポートチェックエラー: {e}")
        
        logger.info(f"公開ポート: {len(ports)}個検出")
        return ports
    
    def check_vault_integrity(self) -> Dict[str, Any]:
        """Vault整合性チェック"""
        vault_path = Path("/root/.mana_vault")
        
        if not vault_path.exists():
            return {
                "status": "error",
                "message": "Vault not found"
            }
        
        # パーミッションチェック
        stat = vault_path.stat()
        permissions = oct(stat.st_mode)[-3:]
        
        # ファイル数チェック
        files = list(vault_path.glob("*"))
        
        status = "ok" if permissions == "700" else "warning"
        
        return {
            "status": status,
            "permissions": permissions,
            "file_count": len(files),
            "message": "Vault OK" if status == "ok" else f"Permissions should be 700, got {permissions}"
        }
    
    def check_environment_variables(self) -> List[Dict[str, Any]]:
        """環境変数チェック"""
        findings = []
        
        logger.info("環境変数をチェック中...")
        
        # .bashrc, .profile などをチェック
        env_files = [
            "/root/.bashrc",
            "/root/.profile",
            "/root/.bash_profile"
        ]
        
        for filepath in env_files:
            if not os.path.exists(filepath):
                continue
            
            try:
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                
                for i, line in enumerate(lines, 1):
                    # export されたAPIキーなどを検出
                    if re.search(r'export\s+\w+[_-]?(API[_-]?KEY|SECRET|TOKEN|PASSWORD)', line, re.I):
                        findings.append({
                            "file": filepath,
                            "line": i,
                            "content": line.strip(),
                            "severity": "high"
                        })
                        
            except Exception as e:
                logger.error(f"ファイル読み込みエラー: {filepath} - {e}")
        
        logger.info(f"環境変数問題: {len(findings)}件検出")
        return findings
    
    def calculate_security_score(self, findings: Dict[str, Any]) -> int:
        """セキュリティスコア計算"""
        score = 100
        
        # 機密情報ファイル
        score -= min(len(findings.get("sensitive_files", [])) * 5, 30)
        
        # ポート問題
        high_risk_ports = [p for p in findings.get("ports", []) if p["risk_level"] == "high"]
        score -= min(len(high_risk_ports) * 10, 30)
        
        # 環境変数問題
        score -= min(len(findings.get("env_vars", [])) * 5, 20)
        
        # Vault問題
        if findings.get("vault", {}).get("status") != "ok":
            score -= 15
        
        return max(score, 0)
    
    def generate_recommendations(self, findings: Dict[str, Any]) -> List[str]:
        """推奨事項生成"""
        recommendations = []
        
        # 機密情報ファイル
        if findings.get("sensitive_files"):
            recommendations.append("🔒 機密情報ファイルをVaultに移動してください")
            recommendations.append("📝 古い認証情報ファイルを削除してください")
        
        # ポート
        high_risk_ports = [p for p in findings.get("ports", []) if p["risk_level"] == "high"]
        if high_risk_ports:
            recommendations.append(f"🔐 {len(high_risk_ports)}個の高リスクポートに認証を追加してください")
        
        # 環境変数
        if findings.get("env_vars"):
            recommendations.append("🗝️ 環境変数からAPIキーを削除してください")
        
        # Vault
        if findings.get("vault", {}).get("status") != "ok":
            recommendations.append("🛡️ Vaultのパーミッションを700に設定してください")
        
        return recommendations
    
    def run_audit(self) -> Dict[str, Any]:
        """セキュリティ監査実行"""
        logger.info("=" * 60)
        logger.info("🔐 セキュリティ監査を開始")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 各種チェック実行
        findings = {
            "sensitive_files": self.scan_sensitive_files(),
            "ports": self.check_port_security(),
            "vault": self.check_vault_integrity(),
            "env_vars": self.check_environment_variables()
        }
        
        # スコア計算
        security_score = self.calculate_security_score(findings)
        
        # 推奨事項生成
        recommendations = self.generate_recommendations(findings)
        
        # 問題の深刻度分類
        critical_issues = len([f for f in findings["sensitive_files"] if f["severity"] == "critical"])
        high_issues = len([f for f in findings["sensitive_files"] if f["severity"] == "high"])
        medium_issues = len([f for f in findings["sensitive_files"] if f["severity"] == "medium"])
        low_issues = len([f for f in findings["sensitive_files"] if f["severity"] == "low"])
        
        # データベースに保存
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_results 
            (audit_date, security_score, critical_issues, high_issues, medium_issues, low_issues, findings, recommendations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            start_time.isoformat(),
            security_score,
            critical_issues,
            high_issues,
            medium_issues,
            low_issues,
            json.dumps(findings),
            json.dumps(recommendations)
        ))
        
        audit_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # レポート生成
        report = {
            "audit_id": audit_id,
            "audit_date": start_time.isoformat(),
            "duration_seconds": duration,
            "security_score": security_score,
            "status": self._get_status_from_score(security_score),
            "issues": {
                "critical": critical_issues,
                "high": high_issues,
                "medium": medium_issues,
                "low": low_issues,
                "total": critical_issues + high_issues + medium_issues + low_issues
            },
            "findings": findings,
            "recommendations": recommendations
        }
        
        # レポートファイル保存
        report_file = os.path.join(
            self.report_path, 
            f"security_audit_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info("=" * 60)
        logger.info(f"✅ セキュリティ監査完了: {duration:.2f}秒")
        logger.info(f"📊 セキュリティスコア: {security_score}/100")
        logger.info(f"📄 レポート: {report_file}")
        logger.info("=" * 60)
        
        return report
    
    def _get_status_from_score(self, score: int) -> str:
        """スコアからステータスを取得"""
        if score >= 90:
            return "EXCELLENT"
        elif score >= 75:
            return "GOOD"
        elif score >= 60:
            return "FAIR"
        elif score >= 40:
            return "POOR"
        else:
            return "CRITICAL"
    
    def print_report(self, report: Dict[str, Any]):
        """レポート表示"""
        print("\n" + "=" * 60)
        print("🔐 セキュリティ監査レポート")
        print("=" * 60)
        print(f"\n📅 監査日時: {report['audit_date']}")
        print(f"⏱️  所要時間: {report['duration_seconds']:.2f}秒")
        print(f"\n📊 セキュリティスコア: {report['security_score']}/100 ({report['status']})")
        
        print("\n📋 検出された問題:")
        print(f"   🔴 Critical: {report['issues']['critical']}件")
        print(f"   🟠 High:     {report['issues']['high']}件")
        print(f"   🟡 Medium:   {report['issues']['medium']}件")
        print(f"   🟢 Low:      {report['issues']['low']}件")
        print(f"   📊 合計:     {report['issues']['total']}件")
        
        print("\n🔍 詳細:")
        print(f"   📁 機密情報ファイル: {len(report['findings']['sensitive_files'])}件")
        print(f"   🔌 公開ポート: {len(report['findings']['ports'])}個")
        print(f"   🗝️  環境変数問題: {len(report['findings']['env_vars'])}件")
        print(f"   🛡️  Vault状態: {report['findings']['vault']['status']}")
        
        if report['recommendations']:
            print("\n💡 推奨事項:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        print("\n" + "=" * 60)

def main():
    auditor = SecurityAuditEnhanced()
    report = auditor.run_audit()
    auditor.print_report(report)

if __name__ == "__main__":
    main()


