#!/usr/bin/env python3
"""
🌐 Trinity MCP Server - Trinityシステム専用MCPインターフェース
CursorからTrinityシステムにアクセスするためのMCPサーバー
"""

import asyncio
import logging
import requests
from datetime import datetime
from typing import Dict, Any

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('TrinityMCP')

class TrinityMCPServer:
    """Trinity MCP Server"""
    
    def __init__(self):
        self.trinity_ports = {
            'secretary': 5007,
            'secure_api': 5010,
            'analytics': 5011,
            'screen_sharing': 5008,
            'runpod_gpu': 5009
        }
        self.base_urls = {
            port: f'http://localhost:{port}' 
            for port in self.trinity_ports.values()
        }
        logger.info("🌐 Trinity MCP Server 初期化完了")
    
    async def trinity_secretary_chat(self, message: str, user_id: str = "mana") -> Dict[str, Any]:
        """Trinity秘書システムとチャット"""
        try:
            url = f"{self.base_urls[self.trinity_ports['secretary']]}/api/ai-secretary/chat"
            payload = {"message": message, "user_id": user_id}
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return {"success": True, "response": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Secretary chat error: {e}")
            return {"success": False, "error": str(e)}
    
    async def trinity_secretary_status(self) -> Dict[str, Any]:
        """Trinity秘書システムのステータス確認"""
        try:
            url = f"{self.base_urls[self.trinity_ports['secretary']]}/api/status"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "status": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Secretary status error: {e}")
            return {"success": False, "error": str(e)}
    
    async def google_calendar_events(self, max_results: int = 10) -> Dict[str, Any]:
        """Googleカレンダーの予定を取得"""
        try:
            url = f"{self.base_urls[self.trinity_ports['secretary']]}/api/google/calendar/events"
            params = {"max_results": max_results}
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return {"success": True, "events": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Google Calendar error: {e}")
            return {"success": False, "error": str(e)}
    
    async def gmail_messages(self, max_results: int = 10, query: str = "") -> Dict[str, Any]:
        """Gmailのメッセージを取得"""
        try:
            url = f"{self.base_urls[self.trinity_ports['secretary']]}/api/google/gmail/messages"
            params = {"max_results": max_results, "query": query}
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return {"success": True, "messages": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Gmail error: {e}")
            return {"success": False, "error": str(e)}
    
    async def google_drive_files(self, max_results: int = 20) -> Dict[str, Any]:
        """Google Driveのファイル一覧を取得"""
        try:
            url = f"{self.base_urls[self.trinity_ports['secretary']]}/api/google/drive/files"
            params = {"max_results": max_results}
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return {"success": True, "files": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Google Drive error: {e}")
            return {"success": False, "error": str(e)}
    
    async def google_services_status(self) -> Dict[str, Any]:
        """Google Services全体のステータス確認"""
        try:
            url = f"{self.base_urls[self.trinity_ports['secretary']]}/api/google/status"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "status": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Google Services status error: {e}")
            return {"success": False, "error": str(e)}
    
    async def screen_sharing_status(self) -> Dict[str, Any]:
        """Mana Screen Sharing Systemのステータス確認"""
        try:
            url = f"{self.base_urls[self.trinity_ports['screen_sharing']]}/api/status"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "status": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Screen Sharing status error: {e}")
            return {"success": False, "error": str(e)}
    
    async def command_center_status(self) -> Dict[str, Any]:
        """ManaOS Command Centerのステータス確認"""
        try:
            # Command Centerは別のポートで動いている可能性
            url = "http://localhost:5000/api/command_center/status"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return {"success": True, "status": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Command Center status error: {e}")
            return {"success": False, "error": str(e)}
    
    async def x280_execute_command(self, command: str, use_powershell: bool = True) -> Dict[str, Any]:
        """X280でコマンドを実行"""
        try:
            url = f"{self.base_urls[self.trinity_ports['secretary']]}/api/x280/execute"
            payload = {"command": command, "use_powershell": use_powershell}
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return {"success": True, "result": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"X280 command execution error: {e}")
            return {"success": False, "error": str(e)}
    
    async def x280_system_info(self) -> Dict[str, Any]:
        """X280のシステム情報を取得"""
        try:
            url = f"{self.base_urls[self.trinity_ports['secretary']]}/api/x280/system_info"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                return {"success": True, "system_info": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"X280 system info error: {e}")
            return {"success": False, "error": str(e)}
    
    async def manaos_system_overview(self) -> Dict[str, Any]:
        """ManaOS/Trinity全システムの概要を取得"""
        try:
            # 複数のシステムの状態を確認
            systems_status = {}
            
            # 各サービスの正しいエンドポイントをチェック
            service_endpoints = {
                'secretary': '/api/status',
                'secure_api': '/api/health', 
                'analytics': '/api/analytics',
                'screen_sharing': '/api/status',
                'runpod_gpu': '/trinity/health'
            }
            
            for service_name, port in self.trinity_ports.items():
                try:
                    endpoint = service_endpoints.get(service_name, '/api/status')
                    url = f"{self.base_urls[port]}{endpoint}"
                    response = requests.get(url, timeout=5)
                    systems_status[service_name] = {
                        "status": "online" if response.status_code == 200 else "offline",
                        "port": port,
                        "endpoint": endpoint
                    }
                except:
                    systems_status[service_name] = {
                        "status": "offline",
                        "port": port,
                        "endpoint": service_endpoints.get(service_name, '/api/status')
                    }
            
            return {
                "success": True,
                "systems": systems_status,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System overview error: {e}")
            return {"success": False, "error": str(e)}

# MCP Server実装
def main():
    """メイン関数"""
    server = TrinityMCPServer()
    
    async def run_server():
        logger.info("🚀 Trinity MCP Server 起動中...")
        
        # システム状態確認
        overview = await server.manaos_system_overview()
        logger.info(f"📊 システム概要: {overview}")
        
        # サーバーを継続実行
        while True:
            await asyncio.sleep(60)  # 1分ごとにチェック
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("🛑 Trinity MCP Server 停止")
    except Exception as e:
        logger.error(f"❌ Trinity MCP Server エラー: {e}")

if __name__ == "__main__":
    main()
