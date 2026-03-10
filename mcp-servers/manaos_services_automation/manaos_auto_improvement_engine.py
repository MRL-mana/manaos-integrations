#!/usr/bin/env python3
"""
🚀 ManaOS Auto Improvement Engine
システム全体を自動分析して改善提案を生成し、Slack/Telegram/LINEに通知

機能:
- Docker/システムサービス/プロセス/ディスク/メモリの自動分析
- AI機能・MCPサーバー・セキュリティの改善提案
- Slack/Telegram/LINE Notify への自動通知
- Web APIサーバー（ポート9300）
- 定期実行対応（cron/systemd）
"""

import os
import sys
import json
import subprocess
import psutil
import docker
import requests
from datetime import datetime
from typing import Dict, Any
from flask import Flask, jsonify
import logging
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/logs/auto_improvement_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask アプリ
app = Flask(__name__)

# 通知設定
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
LINE_NOTIFY_TOKEN = os.getenv('LINE_NOTIFY_TOKEN', '')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')

class SystemAnalyzer:
    """システム分析クラス"""
    
    def __init__(self):
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Docker client initialization failed: {e}")
    
    def analyze_docker_containers(self) -> Dict[str, Any]:
        """Dockerコンテナを分析"""
        if not self.docker_client:
            return {"status": "error", "message": "Docker not available"}
        
        try:
            containers = self.docker_client.containers.list(all=True)
            running = [c for c in containers if c.status == 'running']
            stopped = [c for c in containers if c.status != 'running']
            
            # リソース使用状況
            resource_issues = []
            for container in running:
                try:
                    stats = container.stats(stream=False)
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \  # type: ignore[index]
                               stats['precpu_stats']['cpu_usage']['total_usage']  # type: ignore[index]
                    system_delta = stats['cpu_stats']['system_cpu_usage'] - \  # type: ignore[index]
                                  stats['precpu_stats']['system_cpu_usage']  # type: ignore[index]
                    cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
                    
                    mem_usage = stats['memory_stats']['usage']  # type: ignore[index]
                    mem_limit = stats['memory_stats']['limit']  # type: ignore[index]
                    mem_percent = (mem_usage / mem_limit) * 100.0
                    
                    if cpu_percent > 80:
                        resource_issues.append(f"⚠️ {container.name}: CPU {cpu_percent:.1f}%")
                    if mem_percent > 80:
                        resource_issues.append(f"⚠️ {container.name}: Memory {mem_percent:.1f}%")
                except Exception:
                    pass
            
            return {
                "total": len(containers),
                "running": len(running),
                "stopped": len(stopped),
                "resource_issues": resource_issues,
                "containers": [{"name": c.name, "status": c.status, "image": c.image.tags[0] if c.image.tags else "unknown"} for c in running]  # type: ignore[union-attr]
            }
        except Exception as e:
            logger.error(f"Docker analysis error: {e}")
            return {"status": "error", "message": str(e)}
    
    def analyze_systemd_services(self) -> Dict[str, Any]:
        """Systemdサービスを分析"""
        try:
            result = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"],
                capture_output=True, text=True, timeout=10
            )
            
            manaos_services = []
            for line in result.stdout.split('\n'):
                if 'mana' in line.lower() or 'trinity' in line.lower():
                    parts = line.split()
                    if parts:
                        manaos_services.append(parts[0])
            
            # 失敗したサービスを確認
            failed_result = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--state=failed", "--no-pager"],
                capture_output=True, text=True, timeout=10
            )
            failed_services = []
            for line in failed_result.stdout.split('\n'):
                if line.strip() and 'UNIT' not in line:
                    parts = line.split()
                    if parts:
                        failed_services.append(parts[0])
            
            return {
                "manaos_services": manaos_services,
                "manaos_count": len(manaos_services),
                "failed_services": failed_services,
                "failed_count": len(failed_services)
            }
        except Exception as e:
            logger.error(f"Systemd analysis error: {e}")
            return {"status": "error", "message": str(e)}
    
    def analyze_system_resources(self) -> Dict[str, Any]:
        """システムリソースを分析"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            issues = []
            if cpu_percent > 80:
                issues.append(f"⚠️ CPU使用率が高い: {cpu_percent}%")
            if memory.percent > 80:
                issues.append(f"⚠️ メモリ使用率が高い: {memory.percent}%")
            if disk.percent > 80:
                issues.append(f"⚠️ ディスク使用率が高い: {disk.percent}%")
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "issues": issues
            }
        except Exception as e:
            logger.error(f"Resource analysis error: {e}")
            return {"status": "error", "message": str(e)}
    
    def analyze_ai_processes(self) -> Dict[str, Any]:
        """AI関連プロセスを分析"""
        try:
            ai_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if any(keyword in cmdline.lower() for keyword in ['python', 'trinity', 'mana', 'ai', 'llm', 'gpu']):
                        if 'python' in cmdline.lower():
                            ai_processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cmdline': cmdline[:100],
                                'cpu_percent': proc.info['cpu_percent'],
                                'memory_percent': proc.info['memory_percent']
                            })
                except Exception:
                    pass
            
            return {
                "count": len(ai_processes),
                "processes": ai_processes[:10]  # Top 10
            }
        except Exception as e:
            logger.error(f"AI process analysis error: {e}")
            return {"status": "error", "message": str(e)}
    
    def check_security_status(self) -> Dict[str, Any]:
        """セキュリティ状態をチェック"""
        try:
            security_checks = {
                "firewall": subprocess.run(["ufw", "status"], capture_output=True, text=True).returncode == 0,
                "fail2ban": subprocess.run(["systemctl", "is-active", "fail2ban"], capture_output=True, text=True).stdout.strip() == "active",
                "ssl_certs": Path("/root/.mana_vault").exists(),
                "nginx": subprocess.run(["systemctl", "is-active", "nginx"], capture_output=True, text=True).stdout.strip() == "active"
            }
            
            issues = []
            if not security_checks["firewall"]:
                issues.append("⚠️ ファイアウォールが無効")
            if not security_checks["fail2ban"]:
                issues.append("⚠️ Fail2banが停止")
            
            return {
                "checks": security_checks,
                "issues": issues,
                "score": sum(security_checks.values()) * 25
            }
        except Exception as e:
            logger.error(f"Security check error: {e}")
            return {"status": "error", "message": str(e)}

class ImprovementEngine:
    """改善提案エンジン"""
    
    def __init__(self):
        self.analyzer = SystemAnalyzer()
    
    def generate_improvements(self) -> Dict[str, Any]:
        """改善提案を生成"""
        logger.info("Generating improvement suggestions...")
        
        # 全分析を実行
        docker_analysis = self.analyzer.analyze_docker_containers()
        systemd_analysis = self.analyzer.analyze_systemd_services()
        resource_analysis = self.analyzer.analyze_system_resources()
        ai_analysis = self.analyzer.analyze_ai_processes()
        security_analysis = self.analyzer.check_security_status()
        
        # 改善提案を生成
        improvements = []
        priority_score = 0
        
        # Docker関連
        if docker_analysis.get("stopped", 0) > 0:
            improvements.append({
                "category": "Docker",
                "priority": "medium",
                "title": f"停止中のコンテナ {docker_analysis['stopped']}個",
                "description": "不要なコンテナを削除するか、必要なら再起動してください",
                "command": "docker ps -a | grep Exited"
            })
            priority_score += 30
        
        if docker_analysis.get("resource_issues"):
            improvements.append({
                "category": "Docker",
                "priority": "high",
                "title": "リソース使用率が高いコンテナ",
                "description": "\n".join(docker_analysis["resource_issues"]),
                "command": "docker stats --no-stream"
            })
            priority_score += 50
        
        # Systemd関連
        if systemd_analysis.get("failed_count", 0) > 0:
            improvements.append({
                "category": "Systemd",
                "priority": "high",
                "title": f"失敗したサービス {systemd_analysis['failed_count']}個",
                "description": f"サービス: {', '.join(systemd_analysis.get('failed_services', [])[:3])}",
                "command": "systemctl --failed"
            })
            priority_score += 60
        
        # システムリソース関連
        for issue in resource_analysis.get("issues", []):
            improvements.append({
                "category": "System Resources",
                "priority": "high",
                "title": "システムリソース警告",
                "description": issue,
                "command": "htop"
            })
            priority_score += 40
        
        # ディスク容量の提案
        if resource_analysis.get("disk_percent", 0) > 70:
            improvements.append({
                "category": "Storage",
                "priority": "medium",
                "title": "ディスク容量の最適化",
                "description": f"ディスク使用率 {resource_analysis['disk_percent']:.1f}%。ログやキャッシュのクリーンアップを推奨",
                "command": "du -sh /root/logs/* | sort -h | tail -10"
            })
            priority_score += 35
        
        # AI関連
        if ai_analysis.get("count", 0) > 15:
            improvements.append({
                "category": "AI Processes",
                "priority": "low",
                "title": "AI関連プロセスの最適化",
                "description": f"{ai_analysis['count']}個のAI関連プロセスが実行中。統合を検討してください",
                "command": "ps aux | grep python | wc -l"
            })
            priority_score += 20
        
        # セキュリティ関連
        for issue in security_analysis.get("issues", []):
            improvements.append({
                "category": "Security",
                "priority": "critical",
                "title": "セキュリティ警告",
                "description": issue,
                "command": "systemctl status fail2ban ufw"
            })
            priority_score += 80
        
        # 一般的な提案
        improvements.append({
            "category": "General",
            "priority": "low",
            "title": "定期メンテナンス",
            "description": "apt update/upgrade、ログローテーション、バックアップの確認を推奨",
            "command": "sudo apt update && sudo apt list --upgradable"
        })
        
        # MCPサーバーの活用提案
        improvements.append({
            "category": "MCP Enhancement",
            "priority": "medium",
            "title": "MCPサーバーの活用を拡大",
            "description": "Byterover MCP、AI Learning System、ManaOS Trinity MCPをさらに活用して自動化を強化",
            "command": "cat ~/.config/cursor/mcp.json | jq '.mcpServers | keys'"
        })
        
        # AI機能の強化提案
        improvements.append({
            "category": "AI Enhancement",
            "priority": "medium",
            "title": "AI機能のアップグレード",
            "description": "LLMモデルの更新、RAG機能の追加、ベクトルDB統合を検討",
            "command": "pip list | grep -E 'transformers|langchain|chromadb'"
        })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_improvements": len(improvements),
            "priority_score": priority_score,
            "overall_health": "excellent" if priority_score < 50 else "good" if priority_score < 100 else "needs_attention",
            "improvements": sorted(improvements, key=lambda x: {"critical": 4, "high": 3, "medium": 2, "low": 1}[x["priority"]], reverse=True),
            "analysis": {
                "docker": docker_analysis,
                "systemd": systemd_analysis,
                "resources": resource_analysis,
                "ai_processes": ai_analysis,
                "security": security_analysis
            }
        }

class NotificationManager:
    """通知管理クラス"""
    
    @staticmethod
    def format_message(improvements_data: Dict[str, Any]) -> str:
        """メッセージをフォーマット"""
        msg = "🚀 *ManaOS 自動改善レポート*\n"
        msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        msg += f"🏥 総合健康度: {improvements_data['overall_health'].upper()}\n"
        msg += f"📊 優先度スコア: {improvements_data['priority_score']}\n"
        msg += f"💡 提案数: {improvements_data['total_improvements']}\n\n"
        
        # 重要度の高い提案を表示
        high_priority = [imp for imp in improvements_data['improvements'] if imp['priority'] in ['critical', 'high']]
        if high_priority:
            msg += "⚠️ *重要な改善提案:*\n"
            for imp in high_priority[:5]:
                priority_emoji = "🔴" if imp['priority'] == 'critical' else "🟠"
                msg += f"{priority_emoji} [{imp['category']}] {imp['title']}\n"
                msg += f"   {imp['description']}\n\n"
        
        # システム状態のサマリー
        analysis = improvements_data['analysis']
        msg += "📈 *システム状態:*\n"
        
        if 'docker' in analysis and isinstance(analysis['docker'], dict):
            msg += f"🐳 Docker: {analysis['docker'].get('running', 0)}/{analysis['docker'].get('total', 0)} 稼働中\n"
        
        if 'systemd' in analysis and isinstance(analysis['systemd'], dict):
            msg += f"⚙️ ManaOSサービス: {analysis['systemd'].get('manaos_count', 0)}個稼働中\n"
        
        if 'resources' in analysis and isinstance(analysis['resources'], dict):
            res = analysis['resources']
            msg += f"💻 CPU: {res.get('cpu_percent', 0):.1f}% | RAM: {res.get('memory_percent', 0):.1f}% | Disk: {res.get('disk_percent', 0):.1f}%\n"
        
        if 'security' in analysis and isinstance(analysis['security'], dict):
            msg += f"🔒 セキュリティスコア: {analysis['security'].get('score', 0)}/100\n"
        
        return msg
    
    @staticmethod
    def send_to_telegram(message: str) -> bool:
        """Telegramに送信"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("Telegram credentials not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram notification error: {e}")
            return False
    
    @staticmethod
    def send_to_line(message: str) -> bool:
        """LINE Notifyに送信"""
        if not LINE_NOTIFY_TOKEN:
            logger.warning("LINE Notify token not configured")
            return False
        
        try:
            url = "https://notify-api.line.me/api/notify"
            headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
            data = {"message": message}
            response = requests.post(url, headers=headers, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"LINE notification error: {e}")
            return False
    
    @staticmethod
    def send_to_slack(message: str) -> bool:
        """Slackに送信"""
        if not SLACK_WEBHOOK_URL:
            logger.warning("Slack webhook URL not configured")
            return False
        
        try:
            data = {"text": message}
            response = requests.post(SLACK_WEBHOOK_URL, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Slack notification error: {e}")
            return False
    
    @classmethod
    def send_all(cls, improvements_data: Dict[str, Any]) -> Dict[str, bool]:
        """全チャネルに送信"""
        message = cls.format_message(improvements_data)
        
        results = {
            "telegram": cls.send_to_telegram(message),
            "line": cls.send_to_line(message),
            "slack": cls.send_to_slack(message)
        }
        
        logger.info(f"Notification results: {results}")
        return results

# Flask API エンドポイント
@app.route('/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/analyze', methods=['GET'])
def analyze():
    """システム分析を実行"""
    try:
        engine = ImprovementEngine()
        improvements = engine.generate_improvements()
        return jsonify(improvements)
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/analyze-and-notify', methods=['POST'])
def analyze_and_notify():
    """システム分析して通知"""
    try:
        engine = ImprovementEngine()
        improvements = engine.generate_improvements()
        
        # 通知を送信
        notification_results = NotificationManager.send_all(improvements)
        
        return jsonify({
            "improvements": improvements,
            "notifications": notification_results
        })
    except Exception as e:
        logger.error(f"Analysis and notify error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/notify-test', methods=['POST'])
def notify_test():
    """通知テスト"""
    try:
        test_message = "🧪 ManaOS 自動改善エンジン - 通知テスト\n\n✅ システムは正常に動作しています！"
        
        results = {
            "telegram": NotificationManager.send_to_telegram(test_message),
            "line": NotificationManager.send_to_line(test_message),
            "slack": NotificationManager.send_to_slack(test_message)
        }
        
        return jsonify({"test_results": results})
    except Exception as e:
        logger.error(f"Notify test error: {e}")
        return jsonify({"error": str(e)}), 500

def run_once():
    """一度だけ実行（コマンドライン用）"""
    logger.info("Running improvement analysis (one-time)...")
    
    engine = ImprovementEngine()
    improvements = engine.generate_improvements()
    
    # コンソールに表示
    print("\n" + "="*80)
    print("🚀 ManaOS 自動改善レポート")
    print("="*80)
    print(json.dumps(improvements, indent=2, ensure_ascii=False))
    print("="*80 + "\n")
    
    # 通知を送信
    notification_results = NotificationManager.send_all(improvements)
    print(f"📤 通知結果: {notification_results}\n")
    
    # ファイルに保存
    report_file = f"/root/logs/improvement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(improvements, f, indent=2, ensure_ascii=False)
    print(f"📄 レポート保存: {report_file}\n")
    
    return improvements

if __name__ == "__main__":
    import sys
    
    # ログディレクトリを確認
    os.makedirs('/root/logs', exist_ok=True)
    
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        # 一度だけ実行
        run_once()
    else:
        # Webサーバーとして起動
        logger.info("Starting ManaOS Auto Improvement Engine API server on port 9300...")
        app.run(host='0.0.0.0', port=9300, debug=os.getenv("DEBUG", "False").lower() == "true")








