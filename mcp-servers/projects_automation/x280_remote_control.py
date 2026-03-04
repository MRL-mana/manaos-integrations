#!/usr/bin/env python3
"""
🖥️ X280 Remote Control System
Telegramから直接X280を操作

機能:
- リモートコマンド実行
- ファイル転送
- システム情報取得
- アプリケーション起動
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class X280RemoteControl:
    """X280リモート制御システム"""
    
    def __init__(self):
        # SSH接続情報
        self.ssh_host = "x280"  # ~/.ssh/configで設定済み
        self.ssh_user = "mana"
        self.tailscale_ip = "100.127.121.20"
        
        # セキュリティ: 許可されたコマンドのみ
        self.allowed_commands = {
            'dir': 'ディレクトリ一覧',
            'systeminfo': 'システム情報',
            'tasklist': 'プロセス一覧',
            'diskusage': 'ディスク使用量'
        }
        
        logger.info("🖥️ X280 Remote Control initialized")
    
    async def execute_command(self, command_type: str, args: str = "") -> Dict[str, Any]:
        """
        X280でコマンドを実行
        
        Args:
            command_type: コマンド種類
            args: 追加引数
        
        Returns:
            実行結果
        """
        logger.info(f"🖥️ Executing on X280: {command_type}")
        
        if command_type not in self.allowed_commands:
            return {
                'success': False,
                'output': f"許可されていないコマンドです。\n\n利用可能: {', '.join(self.allowed_commands.keys())}",
                'error': 'Command not allowed'
            }
        
        # コマンドマッピング
        command_map = {
            'dir': f'dir C:\\Users\\{self.ssh_user}',
            'systeminfo': 'systeminfo | findstr /C:"OS" /C:"メモリ" /C:"プロセッサ"',
            'tasklist': 'tasklist /FI "STATUS eq running" | findstr /V "Image"',
            'diskusage': 'wmic logicaldisk get caption,freespace,size'
        }
        
        if args:
            command_map['dir'] = f'dir {args}'
        
        windows_command = command_map.get(command_type, '')
        
        try:
            # SSH経由で実行
            ssh_cmd = f'ssh {self.ssh_host} "{windows_command}"'
            
            process = await asyncio.create_subprocess_shell(
                ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            
            output = stdout.decode('cp932', errors='ignore').strip()
            error = stderr.decode('cp932', errors='ignore').strip()
            
            if process.returncode == 0 and output:
                logger.info("  ✅ Command executed successfully")
                
                return {
                    'success': True,
                    'output': output,
                    'command': command_type,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.warning(f"  ⚠️ Command failed: {error}")
                
                return {
                    'success': False,
                    'output': error or "コマンド実行に失敗しました",
                    'error': error
                }
        
        except asyncio.TimeoutError:
            return {
                'success': False,
                'output': "コマンドがタイムアウトしました（30秒）",
                'error': 'Timeout'
            }
        
        except Exception as e:
            logger.error(f"  ❌ X280 command failed: {e}")
            
            return {
                'success': False,
                'output': f"接続に失敗しました: {str(e)}",
                'error': str(e)
            }
    
    async def get_system_info(self) -> Dict[str, Any]:
        """X280のシステム情報を取得"""
        result = await self.execute_command('systeminfo')
        
        if result['success']:
            return {
                'available': True,
                'info': result['output'],
                'timestamp': result['timestamp']
            }
        else:
            return {
                'available': False,
                'error': result.get('error', 'Unknown error')
            }
    
    async def check_disk_usage(self) -> Dict[str, Any]:
        """ディスク使用量を確認"""
        result = await self.execute_command('diskusage')
        
        if result['success']:
            return {
                'available': True,
                'usage': result['output'],
                'timestamp': result['timestamp']
            }
        else:
            return {
                'available': False,
                'error': result.get('error', 'Unknown error')
            }
    
    def parse_natural_command(self, text: str) -> Optional[Dict[str, str]]:
        """自然言語からコマンドを抽出"""
        text_lower = text.lower()
        
        # ディレクトリ一覧
        if 'ディレクトリ' in text or 'フォルダ' in text or 'ファイル一覧' in text:
            return {'command': 'dir', 'args': ''}
        
        # システム情報
        if 'システム情報' in text or 'スペック' in text:
            return {'command': 'systeminfo', 'args': ''}
        
        # プロセス一覧
        if 'プロセス' in text or 'タスク一覧' in text or 'アプリ一覧' in text:
            return {'command': 'tasklist', 'args': ''}
        
        # ディスク使用量
        if 'ディスク' in text or '容量' in text or 'ストレージ' in text:
            return {'command': 'diskusage', 'args': ''}
        
        return None


# テスト用
async def test_x280_control():
    """X280制御のテスト"""
    control = X280RemoteControl()
    
    print("\n" + "="*60)
    print("🖥️ X280 Remote Control - Test")
    print("="*60)
    
    # テスト1: 自然言語解析
    print("\n📝 Test 1: Natural language parsing")
    
    test_texts = [
        "X280のディレクトリを見せて",
        "X280のシステム情報を教えて",
        "X280のディスク容量を確認して"
    ]
    
    for text in test_texts:
        parsed = control.parse_natural_command(text)
        if parsed:
            print(f"  ✅ '{text}'")
            print(f"     → {parsed['command']}")
    
    # テスト2: 実際のコマンド実行（接続可能な場合）
    print("\n📝 Test 2: Check X280 availability")
    
    result = await control.execute_command('dir', 'C:\\Users\\mana')
    
    if result['success']:
        print("  ✅ X280 is available")
        print(f"     Output (first 200 chars): {result['output'][:200]}...")
    else:
        print(f"  ⚠️ X280 not available: {result.get('error', 'Unknown')}")


if __name__ == '__main__':
    asyncio.run(test_x280_control())



