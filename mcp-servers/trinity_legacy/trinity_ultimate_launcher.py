#!/usr/bin/env python3
"""
🚀 Trinity Ultimate Launcher
全Trinityシステムを統合管理・起動

すべてのTrinityシステムを一括管理！
"""

import asyncio
import subprocess
import logging
import time
from typing import Dict, Any

# 設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class TrinityUltimateLauncher:
    """Trinity統合ランチャー"""
    
    def __init__(self):
        """初期化"""
        self.services = {
            "mobile_server": {
                "name": "Trinity Mobile Server",
                "command": "python3 /root/trinity_mobile_server.py",
                "port": 5555,
                "process": None,
                "essential": True
            },
            "health_monitor": {
                "name": "Trinity Health Monitor",
                "command": "python3 -c 'from trinity_health_monitor import TrinityHealthMonitor; import asyncio; m = TrinityHealthMonitor(); asyncio.run(m.auto_monitor_loop(300))'",
                "port": None,
                "process": None,
                "essential": False
            },
            "gdrive_backup": {
                "name": "Trinity GDrive Backup",
                "command": "python3 -c 'from trinity_gdrive_backup import TrinityGDriveBackup; import asyncio; b = TrinityGDriveBackup(); asyncio.run(b.auto_backup_loop())'",
                "port": None,
                "process": None,
                "essential": False
            }
        }
        
        self.start_time = time.time()
        
        logger.info("🚀 Trinity Ultimate Launcher initialized")
    
    def start_service(self, service_id: str) -> bool:
        """サービス起動"""
        service = self.services.get(service_id)
        if not service:
            logger.error(f"Unknown service: {service_id}")
            return False
        
        try:
            logger.info(f"🚀 Starting: {service['name']}")
            
            process = subprocess.Popen(
                service['command'],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            service['process'] = process
            time.sleep(2)  # 起動待ち
            
            if process.poll() is None:
                logger.info(f"   ✅ Started (PID: {process.pid})")
                return True
            else:
                logger.error("   ❌ Failed to start")
                return False
                
        except Exception as e:
            logger.error(f"❌ Start error: {e}")
            return False
    
    def stop_service(self, service_id: str):
        """サービス停止"""
        service = self.services.get(service_id)
        if not service or not service['process']:
            return
        
        try:
            logger.info(f"🛑 Stopping: {service['name']}")
            service['process'].terminate()
            service['process'].wait(timeout=5)
            service['process'] = None
            logger.info("   ✅ Stopped")
        except Exception as e:
            logger.error(f"❌ Stop error: {e}")
    
    def start_all(self, essential_only: bool = False):
        """全サービス起動"""
        logger.info("🚀 Starting all Trinity services...")
        
        started = 0
        failed = 0
        
        for service_id, service in self.services.items():
            if essential_only and not service.get('essential'):
                continue
            
            if self.start_service(service_id):
                started += 1
            else:
                failed += 1
        
        logger.info(f"\n📊 Startup summary: {started} started, {failed} failed")
        
        return started, failed
    
    def stop_all(self):
        """全サービス停止"""
        logger.info("🛑 Stopping all Trinity services...")
        
        for service_id in self.services:
            self.stop_service(service_id)
    
    def get_status(self) -> Dict[str, Any]:
        """ステータス取得"""
        running = []
        stopped = []
        
        for service_id, service in self.services.items():
            if service['process'] and service['process'].poll() is None:
                running.append({
                    "id": service_id,
                    "name": service['name'],
                    "pid": service['process'].pid,
                    "port": service.get('port')
                })
            else:
                stopped.append({
                    "id": service_id,
                    "name": service['name']
                })
        
        uptime = int(time.time() - self.start_time)
        
        return {
            "uptime_seconds": uptime,
            "running_count": len(running),
            "stopped_count": len(stopped),
            "running": running,
            "stopped": stopped
        }
    
    def print_status(self):
        """ステータス表示"""
        status = self.get_status()
        
        print("\n" + "="*60)
        print("🚀 Trinity Services Status")
        print("="*60)
        print(f"\n⏱️ Uptime: {status['uptime_seconds'] // 60}分")
        print(f"📊 Running: {status['running_count']}")
        print(f"💤 Stopped: {status['stopped_count']}\n")
        
        if status['running']:
            print("✅ Running Services:")
            for s in status['running']:
                port_info = f" (Port {s['port']})" if s['port'] else ""
                print(f"   - {s['name']} (PID: {s['pid']}){port_info}")
        
        if status['stopped']:
            print("\n💤 Stopped Services:")
            for s in status['stopped']:
                print(f"   - {s['name']}")
        
        print("\n" + "="*60 + "\n")


# メイン
async def main():
    """メインランチャー"""
    import sys
    
    launcher = TrinityUltimateLauncher()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start":
            launcher.start_all()
            launcher.print_status()
            
        elif command == "stop":
            launcher.stop_all()
            
        elif command == "status":
            launcher.print_status()
            
        elif command == "essential":
            launcher.start_all(essential_only=True)
            launcher.print_status()
            
        else:
            print("Usage: trinity_ultimate_launcher.py [start|stop|status|essential]")
    else:
        # インタラクティブモード
        print("""
╔══════════════════════════════════════════════════════╗
║      🚀 Trinity Ultimate Launcher                   ║
╚══════════════════════════════════════════════════════╝

Commands:
  start      - Start all services
  essential  - Start essential services only
  stop       - Stop all services
  status     - Show current status
  
Usage:
  python3 trinity_ultimate_launcher.py start
""")


if __name__ == '__main__':
    asyncio.run(main())

