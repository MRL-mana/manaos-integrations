#!/usr/bin/env python3
"""
爆速統合システム - 究極統合ダッシュボード
Ultimate Dashboard for Ultra-Fast Integration System
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List
from datetime import datetime
import subprocess
import os

class UltimateDashboard:
    """究極統合ダッシュボードクラス"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.running = False
        self.dashboard_data = {}
        self.update_interval = 3  # 3秒間隔で更新
        
    def _setup_logging(self):
        """ログ設定"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    async def start_dashboard(self):
        """ダッシュボードを開始"""
        self.logger.info("🚀 究極統合ダッシュボード起動中...")
        self.running = True
        
        # ダッシュボードタスクを開始
        await asyncio.gather(
            self._dashboard_loop(),
            self._data_collector(),
            self._status_updater()
        )
    
    async def _dashboard_loop(self):
        """メインダッシュボードループ"""
        while self.running:
            try:
                await self._display_dashboard()
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"❌ ダッシュボードループエラー: {e}")
    
    async def _display_dashboard(self):
        """ダッシュボードを表示"""
        os.system('clear')  # 画面クリア
        
        print("🚀 爆速統合システム - 究極統合ダッシュボード")
        print("=" * 80)
        print(f"🕐 更新時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # システム概要
        await self._display_system_overview()
        
        # 各統合システムの詳細
        await self._display_integration_systems()
        
        # パフォーマンス統計
        await self._display_performance_stats()
        
        # システムヘルス
        await self._display_system_health()
        
        print("=" * 80)
        print("💡 操作: Ctrl+C で終了 | 自動更新中...")
    
    async def _display_system_overview(self):
        """システム概要を表示"""
        print("📊 システム概要")
        print("-" * 40)
        
        total_systems = len(self.dashboard_data.get('integration_systems', {}))
        running_systems = sum(1 for sys in self.dashboard_data.get('integration_systems', {}).values() 
                            if sys.get('status') == 'running')
        
        print(f"🔧 統合システム数: {running_systems}/{total_systems}")
        print(f"📈 稼働率: {(running_systems/total_systems*100):.1f}%" if total_systems > 0 else "📈 稼働率: 0%")
        print(f"🔄 更新間隔: {self.update_interval}秒")
        print()
    
    async def _display_integration_systems(self):
        """統合システムの詳細を表示"""
        print("🔧 統合システム詳細")
        print("-" * 40)
        
        systems = self.dashboard_data.get('integration_systems', {})
        
        for system_name, system_info in systems.items():
            status_icon = "✅" if system_info.get('status') == 'running' else "❌"
            status_text = system_info.get('status', 'unknown')
            pid = system_info.get('pid', 'N/A')
            uptime = system_info.get('uptime', 'N/A')
            
            print(f"{status_icon} {system_name}: {status_text} (PID: {pid}, 稼働時間: {uptime})")
            
            # サブシステム情報
            subsystems = system_info.get('subsystems', {})
            if subsystems:
                for sub_name, sub_info in subsystems.items():
                    sub_status = "✅" if sub_info.get('status') == 'running' else "❌"
                    sub_pid = sub_info.get('pid', 'N/A')
                    print(f"  {sub_status} {sub_name}: PID {sub_pid}")
        
        print()
    
    async def _display_performance_stats(self):
        """パフォーマンス統計を表示"""
        print("📈 パフォーマンス統計")
        print("-" * 40)
        
        perf_stats = self.dashboard_data.get('performance_stats', {})
        
        if perf_stats:
            total_cpu = perf_stats.get('total_cpu', 0)
            total_memory = perf_stats.get('total_memory', 0)
            avg_cpu = perf_stats.get('average_cpu', 0)
            avg_memory = perf_stats.get('average_memory', 0)
            
            print(f"💻 総CPU使用率: {total_cpu:.1f}%")
            print(f"🧠 総メモリ使用率: {total_memory:.1f}%")
            print(f"📊 平均CPU使用率: {avg_cpu:.1f}%")
            print(f"📊 平均メモリ使用率: {avg_memory:.1f}%")
        else:
            print("📊 パフォーマンスデータ収集中...")
        
        print()
    
    async def _display_system_health(self):
        """システムヘルスを表示"""
        print("🏥 システムヘルス")
        print("-" * 40)
        
        health_status = self.dashboard_data.get('system_health', {})
        
        if health_status:
            overall_health = health_status.get('overall_health', 'unknown')
            health_icon = {
                'excellent': '🟢',
                'good': '🟡',
                'fair': '🟠',
                'poor': '🔴',
                'unknown': '⚪'
            }.get(overall_health, '⚪')
            
            print(f"{health_icon} 全体的なヘルス: {overall_health}")
            print(f"📊 監視対象プロセス数: {health_status.get('monitored_processes', 0)}")
            print(f"⚠️ 警告数: {health_status.get('warnings', 0)}")
            print(f"🚨 エラー数: {health_status.get('errors', 0)}")
        else:
            print("🏥 ヘルスデータ収集中...")
        
        print()
    
    async def _data_collector(self):
        """データ収集"""
        while self.running:
            try:
                await self._collect_integration_systems_data()
                await self._collect_performance_data()
                await self._collect_health_data()
                await asyncio.sleep(5)  # 5秒間隔でデータ収集
                
            except Exception as e:
                self.logger.error(f"❌ データ収集エラー: {e}")
    
    async def _collect_integration_systems_data(self):
        """統合システムのデータを収集"""
        try:
            # 実行中の統合システムを検索
            result = subprocess.run(
                ['ps', 'aux'], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                systems_data = {}
                lines = result.stdout.split('\n')
                
                for line in lines:
                    if any(keyword in line for keyword in ['mangle', 'jules', 'nano', 'google', 'ultimate']):
                        if 'python3' in line and 'grep' not in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                pid = parts[1]
                                cmd = ' '.join(parts[10:])
                                
                                # システム名を抽出
                                system_name = self._extract_system_name(cmd)
                                if system_name:
                                    systems_data[system_name] = {
                                        'status': 'running',
                                        'pid': pid,
                                        'command': cmd,
                                        'uptime': self._calculate_uptime(pid),
                                        'subsystems': await self._get_subsystems(pid)
                                    }
                
                self.dashboard_data['integration_systems'] = systems_data
                
        except Exception as e:
            self.logger.error(f"❌ 統合システムデータ収集エラー: {e}")
    
    def _extract_system_name(self, command: str) -> str:
        """コマンドからシステム名を抽出"""
        if 'mangle' in command:
            return 'Mangle統合システム'
        elif 'jules' in command:
            return 'Jules音声統合システム'
        elif 'nano' in command:
            return 'Nano Banana統合システム'
        elif 'google' in command:
            return 'Google AI Agent統合システム'
        elif 'ultimate' in command:
            return 'Ultimate統合システム'
        else:
            return None  # type: ignore
    
    def _calculate_uptime(self, pid: str) -> str:
        """プロセスの稼働時間を計算"""
        try:
            result = subprocess.run(
                ['ps', '-o', 'etime=', '-p', pid],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return 'N/A'
    
    async def _get_subsystems(self, parent_pid: str) -> Dict[str, Any]:
        """親プロセスのサブシステムを取得"""
        try:
            result = subprocess.run(
                ['ps', '--ppid', parent_pid, '-o', 'pid,comm'],
                capture_output=True,
                text=True
            )
            
            subsystems = {}
            if result.returncode == 0:
                lines = result.stdout.split('\n')[1:]  # ヘッダーを除外
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            pid = parts[0]
                            comm = parts[1]
                            subsystems[comm] = {
                                'status': 'running',
                                'pid': pid
                            }
            
            return subsystems
            
        except Exception as e:
            self.logger.error(f"❌ サブシステム取得エラー: {e}")
            return {}
    
    async def _collect_performance_data(self):
        """パフォーマンスデータを収集"""
        try:
            # システム全体のパフォーマンスを取得
            result = subprocess.run(
                ['top', '-bn1'], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                cpu_line = next((line for line in lines if '%Cpu' in line), '')
                mem_line = next((line for line in lines if 'MiB Mem' in line), '')
                
                # CPU使用率を抽出
                cpu_percent = 0
                if cpu_line:
                    try:
                        cpu_parts = cpu_line.split()
                        us_index = cpu_parts.index('us,')
                        if us_index > 0:
                            cpu_percent = float(cpu_parts[us_index - 1])
                    except:
                        pass
                
                # メモリ使用率を抽出
                mem_percent = 0
                if mem_line:
                    try:
                        mem_parts = mem_line.split()
                        total_index = mem_parts.index('total,')
                        used_index = mem_parts.index('used,')
                        if total_index > 0 and used_index > 0:
                            total_mem = float(mem_parts[total_index - 1])
                            used_mem = float(mem_parts[used_index - 1])
                            mem_percent = (used_mem / total_mem) * 100
                    except:
                        pass
                
                self.dashboard_data['performance_stats'] = {
                    'total_cpu': cpu_percent,
                    'total_memory': mem_percent,
                    'average_cpu': cpu_percent,
                    'average_memory': mem_percent
                }
                
        except Exception as e:
            self.logger.error(f"❌ パフォーマンスデータ収集エラー: {e}")
    
    async def _collect_health_data(self):
        """ヘルスデータを収集"""
        try:
            # システムヘルス情報を収集
            total_processes = len(self.dashboard_data.get('integration_systems', {}))
            running_processes = sum(1 for sys in self.dashboard_data.get('integration_systems', {}).values() 
                                  if sys.get('status') == 'running')
            
            # ヘルスレベルを計算
            if total_processes > 0:
                health_ratio = running_processes / total_processes
                if health_ratio == 1.0:
                    overall_health = 'excellent'
                elif health_ratio >= 0.8:
                    overall_health = 'good'
                elif health_ratio >= 0.6:
                    overall_health = 'fair'
                else:
                    overall_health = 'poor'
            else:
                overall_health = 'unknown'
            
            self.dashboard_data['system_health'] = {
                'overall_health': overall_health,
                'monitored_processes': total_processes,
                'running_processes': running_processes,
                'warnings': 0,  # 実際の警告数をカウント
                'errors': 0      # 実際のエラー数をカウント
            }
            
        except Exception as e:
            self.logger.error(f"❌ ヘルスデータ収集エラー: {e}")
    
    async def _status_updater(self):
        """ステータス更新"""
        while self.running:
            try:
                # ステータス更新処理
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"❌ ステータス更新エラー: {e}")
    
    async def stop(self):
        """ダッシュボードを停止"""
        self.logger.info("🛑 究極統合ダッシュボード停止中...")
        self.running = False
        await asyncio.sleep(1)  # タスク終了を待機
        self.logger.info("✅ 究極統合ダッシュボード停止完了")

async def main():
    """メイン関数"""
    print("🚀 爆速統合システム - 究極統合ダッシュボード")
    print("=" * 60)
    
    dashboard = UltimateDashboard()
    
    try:
        await dashboard.start_dashboard()
    except KeyboardInterrupt:
        print("\n🛑 ユーザーによる停止要求")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
    finally:
        await dashboard.stop()

if __name__ == "__main__":
    asyncio.run(main())


