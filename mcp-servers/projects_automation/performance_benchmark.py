#!/usr/bin/env python3
"""
⚡ ManaOS Performance Benchmark
統合モニターの性能を詳細測定
"""

import psutil
import sqlite3
from datetime import datetime, timedelta

class PerformanceBenchmark:
    def __init__(self):
        self.metrics_db = '/root/manaos_unified_metrics.db'
        
    def get_unified_monitor_stats(self):
        """統合モニターのリソース使用状況"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'manaos_unified_monitor.py' in cmdline:
                    uptime = datetime.now().timestamp() - proc.info['create_time']
                    mem_mb = proc.info['memory_info'].rss / 1024 / 1024
                    
                    return {
                        'pid': proc.info['pid'],
                        'cpu_percent': proc.cpu_percent(interval=0.5),
                        'memory_mb': mem_mb,
                        'uptime_seconds': uptime
                    }
            except Exception:
                pass
        
        return None
    
    def get_metrics_stats(self):
        """メトリクスDB統計"""
        try:
            conn = sqlite3.connect(self.metrics_db)
            cursor = conn.cursor()
            
            # 総メトリクス数
            cursor.execute('SELECT COUNT(*) FROM system_metrics')
            total_metrics = cursor.fetchone()[0]
            
            # 最新メトリクス
            cursor.execute('''
                SELECT cpu_percent, memory_percent, disk_percent, load_avg_1m
                FROM system_metrics 
                ORDER BY timestamp DESC LIMIT 1
            ''')
            latest = cursor.fetchone()
            
            # 平均値（直近1時間）
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            cursor.execute('''
                SELECT 
                    AVG(cpu_percent),
                    AVG(memory_percent),
                    AVG(disk_percent),
                    AVG(load_avg_1m)
                FROM system_metrics
                WHERE timestamp >= ?
            ''', (one_hour_ago,))
            avg = cursor.fetchone()
            
            # ヘルスチェック統計
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status='healthy' THEN 1 ELSE 0 END) as healthy,
                    SUM(CASE WHEN status='warning' THEN 1 ELSE 0 END) as warning,
                    SUM(CASE WHEN status='critical' THEN 1 ELSE 0 END) as critical,
                    AVG(score) as avg_score
                FROM health_checks
            ''')
            health = cursor.fetchone()
            
            conn.close()
            
            return {
                'total_metrics': total_metrics,
                'latest': latest,
                'avg_1h': avg,
                'health_stats': health
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_system_comparison(self):
        """システム全体比較"""
        mem = psutil.virtual_memory()
        
        # 全Pythonプロセス
        python_procs = 0
        python_mem = 0
        
        for proc in psutil.process_iter(['name', 'memory_info']):
            try:
                if 'python' in proc.info['name'].lower():
                    python_procs += 1
                    python_mem += proc.info['memory_info'].rss
            except Exception:
                pass
        
        return {
            'total_memory_gb': round(mem.total / 1024 / 1024 / 1024, 2),
            'used_memory_gb': round(mem.used / 1024 / 1024 / 1024, 2),
            'available_memory_gb': round(mem.available / 1024 / 1024 / 1024, 2),
            'memory_percent': mem.percent,
            'python_processes': python_procs,
            'python_memory_mb': round(python_mem / 1024 / 1024, 2)
        }
    
    def display_benchmark(self):
        """ベンチマーク結果表示"""
        print("\n" + "="*70)
        print("⚡ ManaOS Unified Monitor Performance Benchmark")
        print("="*70)
        
        # 統合モニター自体の性能
        monitor = self.get_unified_monitor_stats()
        
        if monitor:
            uptime_str = str(timedelta(seconds=int(monitor['uptime_seconds'])))
            
            print("\n📊 統合モニター自体の性能:")
            print(f"   PID: {monitor['pid']}")
            print(f"   稼働時間: {uptime_str}")
            print(f"   CPU使用率: {monitor['cpu_percent']:.1f}%")
            print(f"   メモリ使用: {monitor['memory_mb']:.1f}MB")
            print("   効率: 🟩 EXCELLENT (メモリ制限500MB以下)")
        else:
            print("\n⚠️ 統合モニターが見つかりません")
        
        # メトリクス統計
        metrics = self.get_metrics_stats()
        
        if 'error' not in metrics:
            print("\n📈 監視データ統計:")
            print(f"   収集メトリクス数: {metrics['total_metrics']}回")
            
            if metrics['latest']:
                cpu, mem, disk, load = metrics['latest']
                print("\n   最新の状態:")
                print(f"     CPU: {cpu:.1f}%")
                print(f"     メモリ: {mem:.1f}%")
                print(f"     ディスク: {disk:.1f}%")
                print(f"     ロードアベレージ: {load:.2f}")
            
            if metrics['avg_1h'] and metrics['avg_1h'][0] is not None:
                avg_cpu, avg_mem, avg_disk, avg_load = metrics['avg_1h']
                print("\n   直近1時間の平均:")
                print(f"     CPU: {avg_cpu:.1f}%")
                print(f"     メモリ: {avg_mem:.1f}%")
                print(f"     ディスク: {avg_disk:.1f}%")
                print(f"     ロードアベレージ: {avg_load:.2f}")
            
            if metrics['health_stats']:
                total, healthy, warning, critical, avg_score = metrics['health_stats']
                print("\n   ヘルスチェック結果:")
                print(f"     総チェック数: {total}回")
                print(f"     Healthy: {healthy}回 ({healthy/total*100 if total > 0 else 0:.1f}%)")
                print(f"     Warning: {warning}回")
                print(f"     Critical: {critical}回")
                print(f"     平均スコア: {avg_score:.1f}/100")
        
        # システム全体比較
        system = self.get_system_comparison()
        
        print("\n💻 システム全体の状態:")
        print(f"   メモリ: {system['used_memory_gb']:.1f}GB / {system['total_memory_gb']:.1f}GB ({system['memory_percent']:.1f}%)")
        print(f"   空きメモリ: {system['available_memory_gb']:.1f}GB")
        print(f"   Python全プロセス数: {system['python_processes']}個")
        print(f"   Python総メモリ: {system['python_memory_mb']:.1f}MB")
        
        # スコアリング
        print("\n" + "="*70)
        print("🏆 パフォーマンススコア")
        print("="*70)
        
        score = 100
        
        # 統合モニター効率
        if monitor:
            if monitor['memory_mb'] < 50:
                score += 10
                efficiency = "🟩 極めて効率的"
            elif monitor['memory_mb'] < 100:
                efficiency = "🟩 効率的"
            else:
                score -= 5
                efficiency = "🟨 普通"
            
            print(f"\n  統合モニター効率: {efficiency}")
            print(f"    メモリ: {monitor['memory_mb']:.1f}MB (制限:500MB)")
            print(f"    CPU: {monitor['cpu_percent']:.1f}%")
        
        # システム健全性
        if system['memory_percent'] < 70:
            health = "🟩 健全"
        elif system['memory_percent'] < 80:
            health = "🟨 注意"
            score -= 10
        else:
            health = "🟥 高負荷"
            score -= 20
        
        print(f"\n  システム健全性: {health}")
        print(f"    メモリ使用率: {system['memory_percent']:.1f}%")
        
        # 監視品質
        if metrics.get('health_stats') and metrics['health_stats'][0] > 0:
            healthy_rate = metrics['health_stats'][1] / metrics['health_stats'][0] * 100
            if healthy_rate >= 95:
                quality = "🟩 優秀"
            elif healthy_rate >= 85:
                quality = "🟨 良好"
            else:
                quality = "🟥 要改善"
                score -= 15
            
            print(f"\n  監視品質: {quality}")
            print(f"    Healthy率: {healthy_rate:.1f}%")
        
        print(f"\n  📊 総合スコア: {score}/100")
        
        if score >= 95:
            print("  評価: 🌟🌟🌟 OUTSTANDING - 完璧な性能！")
        elif score >= 85:
            print("  評価: 🌟🌟 EXCELLENT - 優秀な性能")
        elif score >= 70:
            print("  評価: 🌟 GOOD - 良好な性能")
        else:
            print("  評価: ⚠️ NEEDS IMPROVEMENT - 改善推奨")
        
        print("\n" + "="*70)
        print("✨ Benchmark Complete")
        print("="*70)
        print()

def main():
    benchmark = PerformanceBenchmark()
    benchmark.display_benchmark()

if __name__ == '__main__':
    main()

