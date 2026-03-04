#!/usr/bin/env python3
"""
🌟 Trinity Ultimate Integration - 究極の統合システム
全てのTrinityシステムを統合管理
"""

import json
import logging
import sys
import subprocess
from pathlib import Path
from typing import Dict, List

# Trinity Supercharge統合をインポート
sys.path.insert(0, '/root/mana_ai_ecosystem')
from trinity_supercharge_integration import TrinitySuperchargeIntegration

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('TrinityUltimateIntegration')

class TrinityUltimateIntegration:
    """Trinity究極統合システム"""
    
    def __init__(self):
        # Supercharge統合を継承
        self.supercharge = TrinitySuperchargeIntegration()
        
        # 既存Trinityシステム
        self.legacy_systems = {
            # 会話・コミュニケーション
            "conversation_api": {
                "name": "💬 Trinity会話API",
                "description": "トリニティとの自然な会話",
                "script": "/root/trinity_conversation_api.py",
                "port": 8083,
                "category": "conversation",
                "auto_start": False
            },
            "conversation_launcher": {
                "name": "🗣️ Trinity会話ランチャー",
                "description": "会話システム統合起動",
                "script": "/root/trinity_conversation_launcher.py",
                "category": "conversation",
                "auto_start": False
            },
            
            # 画面共有・リモート
            "screen_sharing": {
                "name": "📺 Mana画面共有システム",
                "description": "リアルタイム30FPS画面共有・録画",
                "script": "/root/trinity_automation/archive/mana_screen_sharing.py",
                "port": 5008,
                "category": "remote",
                "auto_start": True
            },
            "remote_desktop": {
                "name": "🖥️ Trinityリモートデスクトップ",
                "description": "リモートデスクトップ接続",
                "script": "/root/trinity_remote_desktop.py",
                "category": "remote",
                "auto_start": False
            },
            
            # ファイル・データ管理
            "file_uploader": {
                "name": "📤 Trinityファイルアップローダー",
                "description": "ファイルアップロード・管理",
                "script": "/root/trinity_file_uploader.py",
                "category": "files",
                "auto_start": False
            },
            "google_services": {
                "name": "☁️ Trinity Google Services",
                "description": "Google Drive連携サービス",
                "script": "/root/trinity_google_services.py",
                "category": "files",
                "auto_start": False
            },
            
            # AI・学習システム
            "ai_learning": {
                "name": "🧠 AI Learning System",
                "description": "AI学習・知識蓄積システム",
                "script": "/root/ai_learning_system/ai_learning_server.py",
                "port": 8765,
                "category": "ai",
                "auto_start": False
            },
            "vision_assistant": {
                "name": "👁️ Trinity Vision Assistant",
                "description": "画像認識・分析アシスタント",
                "script": "/root/trinity_vision_assistant.py",
                "category": "ai",
                "auto_start": False
            },
            
            # 知識管理
            "chatgpt_knowledge": {
                "name": "📚 ChatGPT Knowledge Importer",
                "description": "ChatGPT会話インポート",
                "script": "/root/chatgpt_knowledge_importer.py",
                "category": "knowledge",
                "auto_start": False
            },
            
            # モニタリング
            "trinity_monitor": {
                "name": "📊 Trinity Monitor",
                "description": "システム統合モニタリング",
                "script": "/root/trinity_monitor.py",
                "category": "monitoring",
                "auto_start": False
            },
            
            # チャット
            "mobile_chat": {
                "name": "📱 Ultimate Mobile Chat",
                "description": "モバイル対応チャットサーバー",
                "script": "/root/ultimate_mobile_chat_server.py",
                "port": 8084,
                "category": "conversation",
                "auto_start": False
            }
        }
        
        # 全システム統合
        self.all_systems = {
            **self._convert_supercharge_to_systems(),
            **self.legacy_systems
        }
        
        logger.info("🌟 Trinity Ultimate Integration 初期化完了")
        logger.info(f"   Supercharge機能: {len(self.supercharge.services)}個")
        logger.info(f"   既存Trinity機能: {len(self.legacy_systems)}個")
        logger.info(f"   合計: {len(self.all_systems)}個の機能を統合")
    
    def _convert_supercharge_to_systems(self) -> Dict:
        """Superchargeサービスをシステム形式に変換"""
        converted = {}
        for service_id, service in self.supercharge.services.items():
            converted[f"sc_{service_id}"] = {
                "name": service['name'],
                "description": service['description'],
                "script": f"/root/trinity_automation/{service['command']}",
                "port": service.get('port'),
                "category": f"supercharge_{service['category']}",
                "auto_start": service_id in ['unified_dashboard', 'smart_scheduler', 
                                             'file_watcher', 'secure_api', 'analytics_dashboard']
            }
        return converted
    
    def get_system_status(self, system_id: str) -> Dict:
        """システムステータス取得"""
        if system_id not in self.all_systems:
            return {"error": "System not found"}
        
        system = self.all_systems[system_id]
        
        try:
            # スクリプト名からプロセス検索
            script_name = Path(system['script']).name
            result = subprocess.run(
                ['pgrep', '-f', script_name],
                capture_output=True,
                text=True
            )
            is_running = bool(result.stdout.strip())
            pids = result.stdout.strip().split('\n') if is_running else []
            
            status = {
                "system_id": system_id,
                "name": system['name'],
                "description": system['description'],
                "category": system['category'],
                "status": "running" if is_running else "stopped",
                "script": system['script'],
                "pids": pids
            }
            
            if 'port' in system and system['port']:
                status['port'] = system['port']
                status['url'] = f"http://localhost:{system['port']}"
                status['external_url'] = f"http://163.44.120.49:{system['port']}"
                status['tailscale_url'] = f"http://100.93.120.33:{system['port']}"
            
            return status
        except Exception as e:
            return {"error": str(e)}
    
    def get_all_systems_status(self) -> List[Dict]:
        """全システムステータス"""
        return [self.get_system_status(sid) for sid in self.all_systems.keys()]
    
    def get_categories(self) -> Dict[str, List[str]]:
        """カテゴリ別システム一覧"""
        categories = {}
        for system_id, system in self.all_systems.items():
            category = system['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(system_id)
        return categories
    
    def get_web_services(self) -> List[Dict]:
        """全Webサービス一覧"""
        web_services = []
        for system_id, system in self.all_systems.items():
            if 'port' in system and system['port']:
                status = self.get_system_status(system_id)
                web_services.append({
                    "system_id": system_id,
                    "name": system['name'],
                    "port": system['port'],
                    "status": status.get('status', 'unknown'),
                    "url": f"http://localhost:{system['port']}",
                    "external_url": f"http://163.44.120.49:{system['port']}",
                    "tailscale_url": f"http://100.93.120.33:{system['port']}"
                })
        return sorted(web_services, key=lambda x: x['port'])
    
    def start_system(self, system_id: str) -> Dict:
        """システム起動"""
        if system_id not in self.all_systems:
            return {"success": False, "error": "System not found"}
        
        system = self.all_systems[system_id]
        script_path = Path(system['script'])
        
        if not script_path.exists():
            return {"success": False, "error": f"Script not found: {script_path}"}
        
        try:
            # 既に起動中かチェック
            status = self.get_system_status(system_id)
            if status.get('status') == 'running':
                return {"success": False, "error": "Already running"}
            
            # 起動
            cmd = ['python3', str(script_path)]
            
            # 特定のシステムに引数追加
            if 'smart_scheduler' in system_id:
                cmd.append('--run')
            elif 'file_watcher' in system_id:
                cmd.append('--run')
            elif 'voice_assistant' in system_id:
                cmd.append('--listen')
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(script_path.parent)
            )
            
            logger.info(f"✅ {system['name']} 起動 (PID: {process.pid})")
            return {
                "success": True,
                "message": f"{system['name']} を起動しました",
                "pid": process.pid
            }
        except Exception as e:
            logger.error(f"❌ {system['name']} 起動エラー: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_system(self, system_id: str) -> Dict:
        """システム停止"""
        if system_id not in self.all_systems:
            return {"success": False, "error": "System not found"}
        
        system = self.all_systems[system_id]
        
        try:
            script_name = Path(system['script']).name
            result = subprocess.run(
                ['pkill', '-f', script_name],
                capture_output=True
            )
            
            logger.info(f"⏹️ {system['name']} 停止")
            return {
                "success": True,
                "message": f"{system['name']} を停止しました"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_all_auto_systems(self) -> Dict:
        """自動起動対象のシステムを全て起動"""
        results = []
        for system_id, system in self.all_systems.items():
            if system.get('auto_start', False):
                result = self.start_system(system_id)
                results.append({
                    "system_id": system_id,
                    "name": system['name'],
                    "result": result
                })
        
        return {
            "total": len(results),
            "results": results
        }
    
    def get_dashboard_data(self) -> Dict:
        """ダッシュボード用データ"""
        all_status = self.get_all_systems_status()
        categories = self.get_categories()
        web_services = self.get_web_services()
        
        running_count = sum(1 for s in all_status if s.get('status') == 'running')
        
        return {
            "summary": {
                "total_systems": len(self.all_systems),
                "running": running_count,
                "stopped": len(self.all_systems) - running_count,
                "supercharge_features": len(self.supercharge.services),
                "legacy_systems": len(self.legacy_systems)
            },
            "categories": categories,
            "all_systems": all_status,
            "web_services": web_services,
            "quick_access": {
                "dashboards": [
                    {"name": "統合ダッシュボード", "url": "http://163.44.120.49:5009"},
                    {"name": "分析ダッシュボード", "url": "http://163.44.120.49:5011"},
                    {"name": "画面共有システム", "url": "http://163.44.120.49:5008"}
                ],
                "apis": [
                    {"name": "セキュアAPI", "url": "http://163.44.120.49:5010"},
                    {"name": "Trinity会話API", "url": "http://163.44.120.49:8083"}
                ]
            }
        }

# グローバルインスタンス
_ultimate_integration = None

def get_ultimate_integration():
    """統合インスタンスを取得"""
    global _ultimate_integration
    if _ultimate_integration is None:
        _ultimate_integration = TrinityUltimateIntegration()
    return _ultimate_integration

def main():
    """メイン処理"""
    integration = TrinityUltimateIntegration()
    
    if "--dashboard" in sys.argv:
        data = integration.get_dashboard_data()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    elif "--status" in sys.argv:
        status = integration.get_all_systems_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif "--web" in sys.argv:
        web = integration.get_web_services()
        print(json.dumps(web, indent=2, ensure_ascii=False))
    
    elif "--categories" in sys.argv:
        categories = integration.get_categories()
        print(json.dumps(categories, indent=2, ensure_ascii=False))
    
    elif "--start-all" in sys.argv:
        print("🚀 自動起動システムを起動中...")
        result = integration.start_all_auto_systems()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    else:
        print("""
🌟 Trinity Ultimate Integration - 究極の統合システム

全Trinityシステムを統合管理：
  • Trinity Supercharge (10機能)
  • 既存Trinityシステム (11システム)
  • 合計21の機能・システム

使い方:
  --dashboard     ダッシュボード用データ
  --status        全システムステータス
  --web           Webサービス一覧
  --categories    カテゴリ別一覧
  --start-all     自動起動システムを全て起動

Pythonから:
  from trinity_ultimate_integration import get_ultimate_integration
  integration = get_ultimate_integration()
  integration.start_system('screen_sharing')
        """)

if __name__ == "__main__":
    main()


