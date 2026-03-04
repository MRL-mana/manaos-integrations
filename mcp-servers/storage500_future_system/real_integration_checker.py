#!/usr/bin/env python3
"""
🔍 実際の統合状況チェッカー
Obsidian、Notion、その他システムの実際の統合状況を確認
"""

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@dataclass
class IntegrationStatus:
    """統合状況"""
    system_name: str
    status: str
    last_check: str
    details: Dict[str, Any]

class RealIntegrationChecker:
    """実際の統合状況チェッカー"""
    
    def __init__(self):
        self.is_running = False
        self.integration_statuses = {}
        
        # 統合システムの定義
        self.integration_systems = {
            'obsidian_notion_mirror': {
                'name': 'Obsidian-Notion Mirror',
                'script_path': 'obsidian_notion_mirror_lightweight.py',
                'config_path': 'mirror_config.yaml',
                'status': 'unknown'
            },
            'git_sync': {
                'name': 'Git Sync',
                'repo_path': '/mnt/storage/future_system',
                'status': 'unknown'
            },
            'cloud_sync': {
                'name': 'Cloud Sync',
                'sync_path': '/mnt/storage',
                'status': 'unknown'
            },
            'mcp_server': {
                'name': 'MCP Server',
                'script_path': 'start_mcp_server_improved.sh',
                'status': 'unknown'
            },
            'advanced_systems': {
                'name': 'Advanced Systems',
                'scripts': [
                    'lightweight_quantum_system.py',
                    'ultimate_integration_system.py',
                    'future_ai_orchestrator.py',
                    'transcendence_system.py',
                    'cosmic_unification_system.py'
                ],
                'status': 'unknown'
            }
        }
    
    async def initialize(self):
        """システム初期化"""
        logger.info("🔍 実際の統合状況チェッカー初期化中...")
        self.is_running = True
        logger.info("✅ 統合状況チェッカー準備完了")
    
    async def check_file_exists(self, file_path: str) -> bool:
        """ファイル存在チェック"""
        try:
            return os.path.exists(file_path)
        except Exception:
            return False
    
    async def check_process_running(self, process_name: str) -> bool:
        """プロセス実行状況チェック"""
        try:
            result = subprocess.run(['pgrep', '-f', process_name], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    async def check_git_status(self, repo_path: str) -> Dict[str, Any]:
        """Git状況チェック"""
        try:
            # Gitリポジトリかどうかチェック
            git_dir = os.path.join(repo_path, '.git')
            if not os.path.exists(git_dir):
                return {'status': 'not_git_repo', 'details': 'Gitリポジトリではありません'}
            
            # 最新のコミット情報取得
            result = subprocess.run(['git', 'log', '-1', '--oneline'], 
                                  cwd=repo_path, capture_output=True, text=True)
            
            if result.returncode == 0:
                last_commit = result.stdout.strip()
                return {
                    'status': 'active',
                    'last_commit': last_commit,
                    'details': 'Git同期が正常に動作しています'
                }
            else:
                return {'status': 'error', 'details': 'Gitコマンドエラー'}
                
        except Exception as e:
            return {'status': 'error', 'details': f'Gitチェックエラー: {str(e)}'}
    
    async def check_obsidian_notion_mirror(self) -> Dict[str, Any]:
        """Obsidian-Notion Mirror状況チェック"""
        try:
            script_path = 'obsidian_notion_mirror_lightweight.py'
            config_path = 'mirror_config.yaml'
            
            script_exists = await self.check_file_exists(script_path)
            config_exists = await self.check_file_exists(config_path)
            process_running = await self.check_process_running('obsidian_notion_mirror')
            
            if script_exists and config_exists:
                if process_running:
                    return {
                        'status': 'active',
                        'script_exists': True,
                        'config_exists': True,
                        'process_running': True,
                        'details': 'Obsidian-Notion Mirrorが正常に動作しています'
                    }
                else:
                    return {
                        'status': 'inactive',
                        'script_exists': True,
                        'config_exists': True,
                        'process_running': False,
                        'details': 'スクリプトは存在しますが、プロセスが実行されていません'
                    }
            else:
                return {
                    'status': 'not_configured',
                    'script_exists': script_exists,
                    'config_exists': config_exists,
                    'process_running': False,
                    'details': 'Obsidian-Notion Mirrorが設定されていません'
                }
                
        except Exception as e:
            return {'status': 'error', 'details': f'Mirrorチェックエラー: {str(e)}'}
    
    async def check_advanced_systems(self) -> Dict[str, Any]:
        """高度なシステム状況チェック"""
        try:
            scripts = [
                'lightweight_quantum_system.py',
                'ultimate_integration_system.py',
                'future_ai_orchestrator.py',
                'transcendence_system.py',
                'cosmic_unification_system.py'
            ]
            
            script_statuses = {}
            running_count = 0
            
            for script in scripts:
                exists = await self.check_file_exists(script)
                running = await self.check_process_running(script.replace('.py', ''))
                script_statuses[script] = {'exists': exists, 'running': running}
                if running:
                    running_count += 1
            
            if running_count > 0:
                return {
                    'status': 'active',
                    'scripts_total': len(scripts),
                    'scripts_running': running_count,
                    'script_statuses': script_statuses,
                    'details': f'{running_count}/{len(scripts)}個の高度なシステムが動作中です'
                }
            else:
                return {
                    'status': 'inactive',
                    'scripts_total': len(scripts),
                    'scripts_running': 0,
                    'script_statuses': script_statuses,
                    'details': '高度なシステムが動作していません'
                }
                
        except Exception as e:
            return {'status': 'error', 'details': f'高度システムチェックエラー: {str(e)}'}
    
    async def check_all_integrations(self):
        """すべての統合状況チェック"""
        logger.info("🔍 統合状況チェック開始")
        
        # Obsidian-Notion Mirrorチェック
        mirror_status = await self.check_obsidian_notion_mirror()
        self.integration_statuses['obsidian_notion_mirror'] = IntegrationStatus(
            system_name='Obsidian-Notion Mirror',
            status=mirror_status['status'],
            last_check=datetime.now().isoformat(),
            details=mirror_status
        )
        
        # Git同期チェック
        git_status = await self.check_git_status('/mnt/storage/future_system')
        self.integration_statuses['git_sync'] = IntegrationStatus(
            system_name='Git Sync',
            status=git_status['status'],
            last_check=datetime.now().isoformat(),
            details=git_status
        )
        
        # 高度なシステムチェック
        advanced_status = await self.check_advanced_systems()
        self.integration_statuses['advanced_systems'] = IntegrationStatus(
            system_name='Advanced Systems',
            status=advanced_status['status'],
            last_check=datetime.now().isoformat(),
            details=advanced_status
        )
        
        # MCP Serverチェック
        mcp_running = await self.check_process_running('mcp_server')
        mcp_status = {
            'status': 'active' if mcp_running else 'inactive',
            'process_running': mcp_running,
            'details': 'MCP Serverが動作中です' if mcp_running else 'MCP Serverが停止中です'
        }
        self.integration_statuses['mcp_server'] = IntegrationStatus(
            system_name='MCP Server',
            status=mcp_status['status'],
            last_check=datetime.now().isoformat(),
            details=mcp_status
        )
    
    async def display_integration_dashboard(self):
        """統合状況ダッシュボード表示"""
        logger.info("=" * 100)
        logger.info("🔍 実際の統合状況ダッシュボード")
        logger.info("=" * 100)
        
        for system_key, status in self.integration_statuses.items():
            status_icon = "✅" if status.status == 'active' else "❌" if status.status == 'inactive' else "⚠️"
            
            logger.info(f"{status_icon} {status.system_name}:")
            logger.info(f"   状態: {status.status}")
            logger.info(f"   最終チェック: {status.last_check}")
            
            if 'details' in status.details:
                logger.info(f"   詳細: {status.details['details']}")
            
            # 詳細情報の表示
            if 'script_exists' in status.details:
                logger.info(f"   スクリプト存在: {'✅' if status.details['script_exists'] else '❌'}")
            if 'config_exists' in status.details:
                logger.info(f"   設定存在: {'✅' if status.details['config_exists'] else '❌'}")
            if 'process_running' in status.details:
                logger.info(f"   プロセス実行: {'✅' if status.details['process_running'] else '❌'}")
            if 'scripts_running' in status.details:
                logger.info(f"   実行中システム: {status.details['scripts_running']}/{status.details['scripts_total']}")
            
            logger.info("-" * 50)
        
        logger.info("=" * 100)
    
    async def continuous_integration_checking(self):
        """継続的統合状況チェック"""
        logger.info("🔄 継続的統合状況チェック開始")
        
        cycle_count = 0
        
        while self.is_running:
            try:
                # 統合状況チェック
                await self.check_all_integrations()
                
                cycle_count += 1
                
                # 定期的なダッシュボード表示
                if cycle_count % 3 == 0:
                    await self.display_integration_dashboard()
                
                await asyncio.sleep(30)  # 30秒間隔
                
            except KeyboardInterrupt:
                logger.info("⏹️ 継続的統合状況チェック停止")
                break
            except Exception as e:
                logger.error(f"❌ エラー: {e}")
                await asyncio.sleep(35)
    
    async def cleanup(self):
        """クリーンアップ"""
        self.is_running = False
        logger.info("🧹 実際の統合状況チェッカークリーンアップ完了")

async def main():
    """メイン実行"""
    checker = RealIntegrationChecker()
    
    try:
        await checker.initialize()
        
        # 初期統合状況チェック
        await checker.check_all_integrations()
        await checker.display_integration_dashboard()
        
        # 継続的統合状況チェック開始
        await checker.continuous_integration_checking()
        
    except KeyboardInterrupt:
        logger.info("⏹️ システム停止要求")
    finally:
        await checker.cleanup()

if __name__ == "__main__":
    asyncio.run(main()) 