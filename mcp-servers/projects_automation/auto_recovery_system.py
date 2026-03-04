#!/usr/bin/env python3
"""
自動復旧・メンテナンスシステム
システムの健全性を監視し、問題発生時に自動復旧を実行
"""

import json
import subprocess
from datetime import datetime

class AutoRecoverySystem:
    def __init__(self):
        self.log_file = "/root/auto_recovery.log"
        self.status_file = "/root/auto_recovery_status.json"
        self.checks = []
        
    def log(self, message, level="INFO"):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    
    def run_command(self, command):
        """コマンド実行"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def check_failed_services(self):
        """失敗したサービスをチェック"""
        self.log("失敗したサービスをチェック中...")
        
        success, stdout, stderr = self.run_command(
            "systemctl list-units --type=service --state=failed --no-pager"
        )
        
        if success and stdout:
            failed_services = []
            for line in stdout.split('\n'):
                if '●' in line or 'failed' in line.lower():
                    parts = line.split()
                    if parts:
                        service_name = parts[1] if len(parts) > 1 else parts[0]
                        if service_name.endswith('.service'):
                            failed_services.append(service_name)
            
            if failed_services:
                self.log(f"⚠️ 失敗したサービス: {', '.join(failed_services)}", "WARNING")
                return {"status": "failed", "services": failed_services}
            else:
                self.log("✅ すべてのサービスが正常稼働中")
                return {"status": "ok", "services": []}
        
        return {"status": "error", "message": stderr}
    
    def recover_failed_service(self, service_name):
        """失敗したサービスの復旧"""
        self.log(f"サービス復旧を試行: {service_name}")
        
        # サービス再起動
        success, stdout, stderr = self.run_command(f"systemctl restart {service_name}")
        
        if success:
            self.log(f"✅ {service_name} 復旧成功")
            return True
        else:
            self.log(f"❌ {service_name} 復旧失敗: {stderr}", "ERROR")
            return False
    
    def check_disk_space(self):
        """ディスク使用量をチェック"""
        self.log("ディスク使用量をチェック中...")
        
        success, stdout, stderr = self.run_command("df -h / | tail -1")
        
        if success:
            parts = stdout.split()
            if len(parts) >= 5:
                usage_percent = int(parts[4].replace('%', ''))
                
                if usage_percent >= 95:
                    self.log(f"🚨 ディスク使用量が危険レベル: {usage_percent}%", "CRITICAL")
                    return {"status": "critical", "usage": usage_percent}
                elif usage_percent >= 85:
                    self.log(f"⚠️ ディスク使用量が警告レベル: {usage_percent}%", "WARNING")
                    return {"status": "warning", "usage": usage_percent}
                else:
                    self.log(f"✅ ディスク使用量正常: {usage_percent}%")
                    return {"status": "ok", "usage": usage_percent}
        
        return {"status": "error", "message": stderr}
    
    def cleanup_disk_space(self):
        """ディスク空き容量の確保"""
        self.log("ディスク空き容量を確保中...")
        
        cleanup_commands = [
            "find /tmp -type f -atime +7 -delete",  # 7日以上古い一時ファイル削除
            "find /var/log -name '*.gz' -mtime +30 -delete",  # 30日以上古いログ削除
            "docker system prune -f",  # Docker未使用リソース削除
            "apt-get autoremove -y",  # 不要なパッケージ削除
            "apt-get clean"  # パッケージキャッシュ削除
        ]
        
        for cmd in cleanup_commands:
            success, stdout, stderr = self.run_command(cmd)
            if success:
                self.log(f"✅ クリーンアップ実行: {cmd}")
            else:
                self.log(f"⚠️ クリーンアップ失敗: {cmd}", "WARNING")
    
    def check_docker_containers(self):
        """Dockerコンテナの状態をチェック"""
        self.log("Dockerコンテナをチェック中...")
        
        success, stdout, stderr = self.run_command("docker ps -a --format '{{.Names}}\t{{.Status}}'")
        
        if success:
            stopped_containers = []
            for line in stdout.split('\n'):
                if line and 'Exited' in line:
                    container_name = line.split('\t')[0]
                    stopped_containers.append(container_name)
            
            if stopped_containers:
                self.log(f"⚠️ 停止中のコンテナ: {', '.join(stopped_containers)}", "WARNING")
                return {"status": "warning", "containers": stopped_containers}
            else:
                self.log("✅ すべてのコンテナが稼働中")
                return {"status": "ok", "containers": []}
        
        return {"status": "error", "message": stderr}
    
    def restart_docker_container(self, container_name):
        """Dockerコンテナの再起動"""
        self.log(f"コンテナ再起動を試行: {container_name}")
        
        success, stdout, stderr = self.run_command(f"docker restart {container_name}")
        
        if success:
            self.log(f"✅ {container_name} 再起動成功")
            return True
        else:
            self.log(f"❌ {container_name} 再起動失敗: {stderr}", "ERROR")
            return False
    
    def check_mcp_servers(self):
        """MCPサーバーの状態をチェック"""
        self.log("MCPサーバーをチェック中...")
        
        mcp_processes = [
            "trinity_mcp_server.py",
            "unified_mcp_server.py",
            "chrome_mcp_server.py",
            "powerpoint_mcp_server.py"
        ]
        
        running = []
        stopped = []
        
        for process in mcp_processes:
            success, stdout, stderr = self.run_command(f"pgrep -f {process}")
            if success and stdout.strip():
                running.append(process)
            else:
                stopped.append(process)
        
        if stopped:
            self.log(f"⚠️ 停止中のMCPサーバー: {', '.join(stopped)}", "WARNING")
            return {"status": "warning", "running": running, "stopped": stopped}
        else:
            self.log(f"✅ すべてのMCPサーバーが稼働中 ({len(running)}個)")
            return {"status": "ok", "running": running, "stopped": []}
    
    def generate_report(self):
        """システム健全性レポート生成"""
        self.log("システム健全性レポート生成中...")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "services": self.check_failed_services(),
                "disk_space": self.check_disk_space(),
                "docker": self.check_docker_containers(),
                "mcp": self.check_mcp_servers()
            }
        }
        
        # レポート保存
        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log(f"📊 レポート保存: {self.status_file}")
        return report
    
    def auto_recovery(self):
        """自動復旧の実行"""
        self.log("=" * 60)
        self.log("自動復旧・メンテナンスシステム起動")
        self.log("=" * 60)
        
        report = self.generate_report()
        
        recovery_actions = 0
        
        # 失敗したサービスの復旧
        services_check = report["checks"]["services"]
        if services_check["status"] == "failed":
            for service in services_check["services"]:
                if self.recover_failed_service(service):
                    recovery_actions += 1
        
        # ディスク空き容量の確保
        disk_check = report["checks"]["disk_space"]
        if disk_check["status"] in ["warning", "critical"]:
            self.cleanup_disk_space()
            recovery_actions += 1
        
        # 停止中のDockerコンテナの再起動
        docker_check = report["checks"]["docker"]
        if docker_check["status"] == "warning":
            for container in docker_check["containers"][:5]:  # 最大5個まで
                if self.restart_docker_container(container):
                    recovery_actions += 1
        
        self.log("=" * 60)
        self.log(f"自動復旧完了: {recovery_actions}件の復旧アクション実行")
        self.log("=" * 60)
        
        return recovery_actions

if __name__ == "__main__":
    recovery = AutoRecoverySystem()
    recovery.auto_recovery()


