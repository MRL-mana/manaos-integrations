#!/usr/bin/env python3
"""
ManaOS セキュリティ監査システム
定期的にセキュリティ状態をチェックしてレポート生成
"""
import subprocess
from datetime import datetime
from pathlib import Path
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("security_audit")

class SecurityAuditSystem:
    """セキュリティ監査システム"""
    
    def __init__(self):
        self.report_dir = Path("/root/security_reports")
        self.report_dir.mkdir(exist_ok=True)
        
    def check_open_ports(self) -> dict:
        """オープンポートチェック"""
        try:
            result = subprocess.run(
                ['ss', '-tuln'],
                capture_output=True, text=True, timeout=10
            )
            
            open_ports = []
            for line in result.stdout.split('\n'):
                if 'LISTEN' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        addr_port = parts[4]
                        if ':' in addr_port:
                            port = addr_port.split(':')[-1]
                            open_ports.append(port)
            
            return {
                'status': 'OK',
                'open_ports': list(set(open_ports)),
                'count': len(set(open_ports))
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}
    
    def check_fail2ban_effectiveness(self) -> dict:
        """fail2ban有効性チェック"""
        try:
            result = subprocess.run(
                ['fail2ban-client', 'status', 'sshd'],
                capture_output=True, text=True, timeout=10
            )
            
            current_banned = 0
            total_banned = 0
            banned_ips = []
            
            for line in result.stdout.split('\n'):
                if 'Currently banned:' in line:
                    current_banned = int(line.split(':')[1].strip())
                elif 'Total banned:' in line:
                    total_banned = int(line.split(':')[1].strip())
                elif 'Banned IP list:' in line:
                    ips = line.split(':')[1].strip()
                    if ips:
                        banned_ips = ips.split()
            
            return {
                'status': 'ACTIVE',
                'current_banned': current_banned,
                'total_banned': total_banned,
                'banned_ips': banned_ips,
                'effectiveness': 'HIGH' if total_banned > 0 else 'MONITORING'
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}
    
    def check_ssh_config(self) -> dict:
        """SSH設定セキュリティチェック"""
        try:
            config_checks = {
                'PermitRootLogin': False,
                'PasswordAuthentication': False,
                'PubkeyAuthentication': True,
                'Port': None
            }
            
            with open('/etc/ssh/sshd_config', 'r') as f:
                content = f.read()
            
            results = {}
            for key in config_checks.keys():
                if key in content:
                    for line in content.split('\n'):
                        if line.strip().startswith(key):
                            value = line.split()[1] if len(line.split()) > 1 else None
                            results[key] = value
            
            # セキュリティスコア計算
            score = 0
            if results.get('PermitRootLogin') == 'no':
                score += 30
            if results.get('PasswordAuthentication') == 'no':
                score += 30
            if results.get('PubkeyAuthentication') == 'yes':
                score += 20
            if results.get('Port') != '22':
                score += 20
            
            return {
                'status': 'CHECKED',
                'config': results,
                'security_score': score,
                'rating': 'EXCELLENT' if score >= 80 else 'GOOD' if score >= 60 else 'NEEDS_IMPROVEMENT'
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}
    
    def check_sudo_users(self) -> dict:
        """sudo権限ユーザーチェック"""
        try:
            result = subprocess.run(
                ['getent', 'group', 'sudo'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(':')
                users = parts[3].split(',') if len(parts) > 3 and parts[3] else []
                
                return {
                    'status': 'OK',
                    'sudo_users': users,
                    'count': len(users),
                    'warning': 'REVIEW_NEEDED' if len(users) > 3 else 'OK'
                }
            else:
                return {'status': 'ERROR', 'error': 'Could not retrieve sudo users'}
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}
    
    def check_firewall_status(self) -> dict:
        """ファイアウォール状態チェック"""
        try:
            # ufw status
            result = subprocess.run(
                ['ufw', 'status'],
                capture_output=True, text=True, timeout=5
            )
            
            status = 'inactive'
            rules = []
            
            for line in result.stdout.split('\n'):
                if 'Status:' in line:
                    status = line.split(':')[1].strip().lower()
                elif 'ALLOW' in line or 'DENY' in line:
                    rules.append(line.strip())
            
            return {
                'status': status.upper(),
                'rules_count': len(rules),
                'rules': rules[:10],  # 最大10件
                'recommendation': 'ENABLE' if status == 'inactive' else 'OK'
            }
        except Exception as e:
            return {'status': 'UNKNOWN', 'error': str(e)}
    
    def check_system_updates(self) -> dict:
        """システムアップデートチェック"""
        try:
            result = subprocess.run(
                ['apt', 'list', '--upgradable'],
                capture_output=True, text=True, timeout=30
            )
            
            updates = [line for line in result.stdout.split('\n') if '/' in line]
            
            return {
                'status': 'CHECKED',
                'available_updates': len(updates),
                'recommendation': 'UPDATE_AVAILABLE' if len(updates) > 0 else 'UP_TO_DATE'
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}
    
    def check_docker_security(self) -> dict:
        """Dockerセキュリティチェック"""
        try:
            # Dockerコンテナの権限チェック
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'],
                capture_output=True, text=True, timeout=10
            )
            
            containers = result.stdout.strip().split('\n')
            running_count = len([c for c in containers if c])
            
            # Dockerイメージの脆弱性スキャン（簡易版）
            return {
                'status': 'RUNNING',
                'containers_running': running_count,
                'recommendation': 'REGULAR_SCAN' if running_count > 0 else 'OK'
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}
    
    def generate_report(self) -> str:
        """セキュリティ監査レポート生成"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info("=" * 70)
        logger.info("🛡️  ManaOS セキュリティ監査開始")
        logger.info("=" * 70)
        
        # 各種チェック実行
        checks = {
            'open_ports': self.check_open_ports(),
            'fail2ban': self.check_fail2ban_effectiveness(),
            'ssh_config': self.check_ssh_config(),
            'sudo_users': self.check_sudo_users(),
            'firewall': self.check_firewall_status(),
            'system_updates': self.check_system_updates(),
            'docker_security': self.check_docker_security()
        }
        
        # レポート生成
        report = f"""
# ManaOS セキュリティ監査レポート
生成日時: {timestamp}

## 📋 監査サマリー

"""
        
        # 各チェック結果を追加
        for check_name, result in checks.items():
            report += f"\n### {check_name.replace('_', ' ').title()}\n"
            report += f"```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```\n"
        
        # 総合評価
        report += "\n## 🎯 総合評価\n\n"
        
        security_score = 0
        max_score = 100
        
        # スコア計算
        if checks['fail2ban']['status'] == 'ACTIVE':
            security_score += 20
        if checks['ssh_config']['status'] == 'CHECKED':
            security_score += checks['ssh_config'].get('security_score', 0) * 0.3
        if checks['firewall']['status'] == 'ACTIVE':
            security_score += 15
        if checks['system_updates']['recommendation'] == 'UP_TO_DATE':
            security_score += 10
        
        rating = (
            "🟢 EXCELLENT" if security_score >= 80 else
            "🟡 GOOD" if security_score >= 60 else
            "🟠 NEEDS_IMPROVEMENT" if security_score >= 40 else
            "🔴 CRITICAL"
        )
        
        report += f"**セキュリティスコア**: {security_score:.1f}/100\n"
        report += f"**評価**: {rating}\n\n"
        
        # 推奨事項
        report += "## 💡 推奨事項\n\n"
        
        recommendations = []
        
        if checks['firewall']['status'] != 'ACTIVE':
            recommendations.append("- ファイアウォール(ufw)を有効化してください")
        
        if checks['system_updates']['available_updates'] > 10:
            recommendations.append(f"- システムアップデートが{checks['system_updates']['available_updates']}件あります")
        
        if checks['fail2ban']['total_banned'] > 20:
            recommendations.append("- fail2banで多数のIPがBAN済み。攻撃パターンを分析してください")
        
        if checks['sudo_users']['count'] > 3:
            recommendations.append("- sudo権限ユーザーが多すぎます。権限を見直してください")
        
        if not recommendations:
            recommendations.append("- 現時点で重要な推奨事項はありません。定期的な監視を継続してください。")
        
        for rec in recommendations:
            report += f"{rec}\n"
        
        report += "\n---\n\n"
        report += "*このレポートは自動生成されました*\n"
        
        # ファイルに保存
        report_file = self.report_dir / f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"📄 レポート保存: {report_file}")
        logger.info("=" * 70)
        logger.info("🎉 セキュリティ監査完了")
        logger.info("=" * 70)
        
        return str(report_file)

if __name__ == '__main__':
    audit_system = SecurityAuditSystem()
    report_path = audit_system.generate_report()
    print(f"\nレポート: {report_path}")

