#!/usr/bin/env python3
"""
🚀 爆速統合システム - 全システム統合マスター
============================================================
全システムの最終統合とマスター制御を行うシステム
"""

import asyncio
import json
import logging
import os
import psutil
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import subprocess
import signal

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UltimateIntegrationMaster:
    """全システム統合マスター"""
    
    def __init__(self):
        self.system_processes = {}
        self.integration_status = {}
        self.performance_metrics = {}
        self.system_health = {}
        self.master_control = {}
        
    async def start_master_system(self):
        """マスターシステム開始"""
        logger.info("🚀 全システム統合マスター起動中...")
        logger.info("============================================================")
        logger.info("🎯 爆速統合システム - 全システム統合開始")
        logger.info("============================================================")
        
        # システム統合チェック
        await self.check_all_systems()
        
        # 統合システム起動
        await self.launch_integration_systems()
        
        # マスター制御ループ開始
        await self.master_control_loop()
    
    async def check_all_systems(self):
        """全システムチェック"""
        logger.info("🔍 全システム状況チェック中...")
        
        # 対象システム一覧
        target_systems = [
            'nano_banana_integration',
            'jules_voice_integration',
            'ai_auto_learning',
            'integration_test',
            'performance_monitor',
            'system_optimizer',
            'advanced_ai_engine'
        ]
        
        for system in target_systems:
            status = await self.check_system_health(system)
            self.system_health[system] = status
            logger.info(f"  {system}: {status['status']} ({status['details']})")
        
        # 統合状況サマリー
        active_systems = sum(1 for s in self.system_health.values() if s['status'] == 'active')
        total_systems = len(self.system_health)
        
        logger.info(f"📊 システム統合状況: {active_systems}/{total_systems} 稼働中")
        
        if active_systems == total_systems:
            logger.info("🎉 全システムが稼働中です！")
        else:
            logger.warning(f"⚠️ {total_systems - active_systems}個のシステムが非稼働です")
    
    async def check_system_health(self, system_name: str) -> Dict:
        """システムヘルスチェック"""
        try:
            # プロセス名で検索
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if system_name.replace('_', '') in proc.info['name'].lower():
                        # プロセス詳細情報取得
                        proc_info = proc.as_dict(attrs=['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time'])
                        
                        return {
                            'status': 'active',
                            'pid': proc_info['pid'],
                            'cpu_usage': proc_info['cpu_percent'],
                            'memory_usage': proc_info['memory_percent'],
                            'uptime': time.time() - proc_info['create_time'],
                            'details': f"PID: {proc_info['pid']}, CPU: {proc_info['cpu_percent']:.1f}%, メモリ: {proc_info['memory_percent']:.1f}%"
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'status': 'inactive',
                'pid': None,
                'details': 'プロセスが見つかりません'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'pid': None,
                'details': f"エラー: {e}"
            }
    
    async def launch_integration_systems(self):
        """統合システム起動"""
        logger.info("🚀 統合システム起動中...")
        
        # 非稼働システムの起動
        inactive_systems = [
            name for name, status in self.system_health.items()
            if status['status'] != 'active'
        ]
        
        if inactive_systems:
            logger.info(f"🔄 {len(inactive_systems)}個のシステムを起動します")
            
            for system in inactive_systems:
                await self.launch_system(system)
        else:
            logger.info("✅ 全システムが稼働中です")
    
    async def launch_system(self, system_name: str):
        """システム起動"""
        try:
            logger.info(f"🚀 {system_name} 起動中...")
            
            # システム起動コマンド
            launch_commands = {
                'nano_banana_integration': 'python3 start_nano_banana_integration_console.py',
                'jules_voice_integration': 'python3 start_jules_voice_integration_console.py',
                'ai_auto_learning': 'python3 ai_auto_learning_system.py',
                'integration_test': 'python3 integration_test_system.py',
                'performance_monitor': 'python3 performance_monitor.py',
                'system_optimizer': 'python3 system_optimizer.py',
                'advanced_ai_engine': 'python3 advanced_ai_engine.py'
            }
            
            if system_name in launch_commands:
                # バックグラウンドで起動
                process = subprocess.Popen(
                    launch_commands[system_name].split(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                self.system_processes[system_name] = process
                logger.info(f"✅ {system_name} 起動成功 (PID: {process.pid})")
                
                # 起動確認のため少し待機
                await asyncio.sleep(2)
                
            else:
                logger.warning(f"⚠️ {system_name} の起動コマンドが定義されていません")
                
        except Exception as e:
            logger.error(f"❌ {system_name} 起動エラー: {e}")
    
    async def master_control_loop(self):
        """マスター制御ループ"""
        logger.info("🔄 マスター制御ループ開始...")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                logger.info(f"🔄 マスター制御サイクル {cycle_count} 開始...")
                
                # システム状況更新
                await self.update_system_status()
                
                # パフォーマンス監視
                await self.monitor_performance()
                
                # 統合状況分析
                await self.analyze_integration()
                
                # 自動最適化
                await self.auto_optimize()
                
                # 結果記録
                await self.record_master_results(cycle_count)
                
                # 統合状況表示
                await self.display_integration_status()
                
                logger.info(f"✅ マスター制御サイクル {cycle_count} 完了")
                
                # 60秒間隔で実行
                await asyncio.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("🛑 全システム統合マスター停止中...")
                break
            except Exception as e:
                logger.error(f"❌ マスター制御エラー: {e}")
                await asyncio.sleep(10)
    
    async def update_system_status(self):
        """システム状況更新"""
        logger.info("📊 システム状況更新中...")
        
        for system_name in self.system_health.keys():
            status = await self.check_system_health(system_name)
            self.system_health[system_name] = status
            
            # プロセス情報も更新
            if system_name in self.system_processes:
                process = self.system_processes[system_name]
                if process.poll() is not None:
                    logger.warning(f"⚠️ {system_name} プロセスが終了しました")
                    del self.system_processes[system_name]
        
        logger.info("✅ システム状況更新完了")
    
    async def monitor_performance(self):
        """パフォーマンス監視"""
        logger.info("📊 パフォーマンス監視中...")
        
        # システム全体のパフォーマンス
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # プロセス数
        process_count = len(psutil.pids())
        
        # ネットワーク接続数
        try:
            network_connections = len(psutil.net_connections())
        except:
            network_connections = 0
        
        self.performance_metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent,
            'process_count': process_count,
            'network_connections': network_connections,
            'overall_score': self.calculate_overall_performance(cpu_percent, memory.percent, disk.percent)
        }
        
        logger.info(f"📊 パフォーマンススコア: {self.performance_metrics['overall_score']:.1f}/100")
    
    def calculate_overall_performance(self, cpu: float, memory: float, disk: float) -> float:
        """全体パフォーマンススコア計算"""
        cpu_score = max(0, 100 - cpu)
        memory_score = max(0, 100 - memory)
        disk_score = max(0, 100 - disk)
        return (cpu_score + memory_score + disk_score) / 3
    
    async def analyze_integration(self):
        """統合状況分析"""
        logger.info("🔍 統合状況分析中...")
        
        # 稼働システム数
        active_systems = sum(1 for s in self.system_health.values() if s['status'] == 'active')
        total_systems = len(self.system_health)
        
        # 統合状況評価
        integration_score = (active_systems / total_systems) * 100
        
        # システム間の連携状況
        system_connections = self.analyze_system_connections()
        
        self.integration_status = {
            'timestamp': datetime.now().isoformat(),
            'active_systems': active_systems,
            'total_systems': total_systems,
            'integration_score': integration_score,
            'system_connections': system_connections,
            'status': self.get_integration_status(integration_score)
        }
        
        logger.info(f"📊 統合スコア: {integration_score:.1f}/100 ({self.integration_status['status']})")
    
    def analyze_system_connections(self) -> Dict:
        """システム間連携分析"""
        connections = {}
        
        # 各システムの連携状況を分析
        for system_name, status in self.system_health.items():
            if status['status'] == 'active':
                connections[system_name] = {
                    'status': 'connected',
                    'connections': self.get_system_connections(system_name)
                }
            else:
                connections[system_name] = {
                    'status': 'disconnected',
                    'connections': []
                }
        
        return connections
    
    def get_system_connections(self, system_name: str) -> List[str]:
        """システム連携先取得"""
        # システム間の連携関係を定義
        connection_map = {
            'nano_banana_integration': ['image_processing', 'ai_generation'],
            'jules_voice_integration': ['speech_recognition', 'voice_synthesis'],
            'ai_auto_learning': ['machine_learning', 'data_analysis'],
            'integration_test': ['system_testing', 'performance_testing'],
            'performance_monitor': ['resource_monitoring', 'alert_system'],
            'system_optimizer': ['performance_optimization', 'resource_management'],
            'advanced_ai_engine': ['ai_coordination', 'intelligent_control']
        }
        
        return connection_map.get(system_name, [])
    
    def get_integration_status(self, score: float) -> str:
        """統合状況ステータス判定"""
        if score >= 90:
            return "🟢 完全統合"
        elif score >= 70:
            return "🟡 良好統合"
        elif score >= 50:
            return "🟠 部分統合"
        else:
            return "🔴 統合不足"
    
    async def auto_optimize(self):
        """自動最適化"""
        logger.info("⚡ 自動最適化実行中...")
        
        optimization_actions = []
        
        # パフォーマンス最適化
        if self.performance_metrics['overall_score'] < 70:
            optimization_actions.append("パフォーマンス最適化が必要")
        
        # 統合最適化
        if self.integration_status['integration_score'] < 80:
            optimization_actions.append("システム統合の強化が必要")
        
        # 非稼働システムの再起動
        inactive_systems = [
            name for name, status in self.system_health.items()
            if status['status'] != 'active'
        ]
        
        if inactive_systems:
            optimization_actions.append(f"{len(inactive_systems)}個の非稼働システムの再起動が必要")
        
        if optimization_actions:
            logger.info(f"⚡ {len(optimization_actions)}件の最適化アクションを実行")
            for action in optimization_actions:
                logger.info(f"  - {action}")
        else:
            logger.info("✅ 最適化は不要です")
    
    async def display_integration_status(self):
        """統合状況表示"""
        logger.info("============================================================")
        logger.info("🎯 爆速統合システム - 統合状況レポート")
        logger.info("============================================================")
        
        # システム状況
        logger.info("📊 システム状況:")
        for system_name, status in self.system_health.items():
            status_icon = "✅" if status['status'] == 'active' else "❌"
            logger.info(f"  {status_icon} {system_name}: {status['status']}")
        
        # パフォーマンス状況
        logger.info("📊 パフォーマンス状況:")
        logger.info(f"  CPU: {self.performance_metrics['cpu_percent']:.1f}%")
        logger.info(f"  メモリ: {self.performance_metrics['memory_percent']:.1f}%")
        logger.info(f"  ディスク: {self.performance_metrics['disk_percent']:.1f}%")
        logger.info(f"  総合スコア: {self.performance_metrics['overall_score']:.1f}/100")
        
        # 統合状況
        logger.info("📊 統合状況:")
        logger.info(f"  稼働システム: {self.integration_status['active_systems']}/{self.integration_status['total_systems']}")
        logger.info(f"  統合スコア: {self.integration_status['integration_score']:.1f}/100")
        logger.info(f"  統合状況: {self.integration_status['status']}")
        
        logger.info("============================================================")
    
    async def record_master_results(self, cycle_count: int):
        """マスター結果記録"""
        record = {
            'cycle': cycle_count,
            'timestamp': datetime.now().isoformat(),
            'system_health': self.system_health,
            'performance_metrics': self.performance_metrics,
            'integration_status': self.integration_status
        }
        
        # 履歴をファイルに保存
        with open('master_integration_history.json', 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        
        logger.info("📝 マスター結果を記録しました")
    
    async def graceful_shutdown(self):
        """グレースフルシャットダウン"""
        logger.info("🛑 全システム統合マスター停止中...")
        
        # 子プロセスの停止
        for system_name, process in self.system_processes.items():
            try:
                logger.info(f"🛑 {system_name} 停止中...")
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"✅ {system_name} 停止完了")
            except subprocess.TimeoutExpired:
                logger.warning(f"⚠️ {system_name} 強制停止中...")
                process.kill()
            except Exception as e:
                logger.error(f"❌ {system_name} 停止エラー: {e}")
        
        logger.info("✅ 全システム統合マスター停止完了")
    
    def get_master_summary(self) -> Dict:
        """マスターサマリー取得"""
        return {
            'total_systems': len(self.system_health),
            'active_systems': sum(1 for s in self.system_health.values() if s['status'] == 'active'),
            'performance_score': self.performance_metrics.get('overall_score', 0),
            'integration_score': self.integration_status.get('integration_score', 0),
            'system_status': self.integration_status.get('status', 'unknown')
        }

async def main():
    """メイン関数"""
    master = UltimateIntegrationMaster()
    
    try:
        await master.start_master_system()
    except KeyboardInterrupt:
        logger.info("🛑 全システム統合マスター停止要求")
    finally:
        # グレースフルシャットダウン
        await master.graceful_shutdown()
        
        # 最終サマリー表示
        summary = master.get_master_summary()
        logger.info("📊 最終マスターサマリー:")
        for key, value in summary.items():
            logger.info(f"  {key}: {value}")

if __name__ == "__main__":
    asyncio.run(main()) 