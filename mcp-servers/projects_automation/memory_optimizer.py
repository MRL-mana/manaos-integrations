#!/usr/bin/env python3
"""
💾 ManaOS Memory Optimizer
不要プロセスを特定して整理
"""

import psutil
from datetime import datetime

class MemoryOptimizer:
    def __init__(self):
        self.cleanup_candidates = []
        
    def find_zombie_processes(self):
        """長期実行中の不要プロセスを検出"""
        print("🔍 不要プロセスを検索中...\n")
        
        # 不要な可能性があるプロセスパターン
        patterns = [
            'simple_trinity_test.py',
            'simple_multi_model_server.py', 
            'claude_desktop_mcp_server_fixed.py',
            'mana_revenue_launcher.py',
            'mana_learning_enhancer.py'
        ]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                
                for pattern in patterns:
                    if pattern in cmdline:
                        uptime_hours = (datetime.now().timestamp() - proc.info['create_time']) / 3600
                        self.cleanup_candidates.append({
                            'pid': proc.info['pid'],
                            'name': pattern,
                            'memory_mb': proc.info['memory_percent'] * psutil.virtual_memory().total / 100 / 1024 / 1024,
                            'uptime_hours': uptime_hours
                        })
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return self.cleanup_candidates
    
    def display_candidates(self):
        """クリーンアップ候補を表示"""
        if not self.cleanup_candidates:
            print("✨ 不要プロセスは見つかりませんでした！")
            return
        
        print("📊 クリーンアップ候補:\n")
        total_memory = 0
        
        for i, proc in enumerate(self.cleanup_candidates, 1):
            print(f"  {i}. PID {proc['pid']}: {proc['name']}")
            print(f"     メモリ: {proc['memory_mb']:.1f}MB | 稼働時間: {proc['uptime_hours']:.1f}時間")
            total_memory += proc['memory_mb']
        
        print(f"\n💾 解放可能メモリ: {total_memory:.1f}MB")
        
    def cleanup(self, force=False):
        """プロセスをクリーンアップ"""
        if not self.cleanup_candidates:
            return 0
        
        cleaned = 0
        for proc in self.cleanup_candidates:
            try:
                p = psutil.Process(proc['pid'])
                p.terminate()
                cleaned += 1
                print(f"  ✅ 終了: {proc['name']} (PID {proc['pid']})")
            except Exception:
                pass
        
        return cleaned

def main():
    print("💾 ManaOS Memory Optimizer\n")
    
    optimizer = MemoryOptimizer()
    
    # メモリ使用状況
    mem = psutil.virtual_memory()
    print("📊 現在のメモリ使用状況:")
    print(f"   総容量: {mem.total/1024/1024/1024:.1f}GB")
    print(f"   使用中: {mem.used/1024/1024/1024:.1f}GB ({mem.percent}%)")
    print(f"   空き: {mem.available/1024/1024/1024:.1f}GB\n")
    
    # 不要プロセス検出
    candidates = optimizer.find_zombie_processes()
    optimizer.display_candidates()
    
    # クリーンアップ実行
    if candidates:
        print("\n🧹 クリーンアップを実行中...")
        cleaned = optimizer.cleanup(force=True)
        print(f"\n✅ {cleaned}個のプロセスを終了しました")
        
        # 最適化後のメモリ状況
        mem_after = psutil.virtual_memory()
        saved = mem.used - mem_after.used
        print(f"💾 解放されたメモリ: {saved/1024/1024:.1f}MB")
    
    print("\n✨ Memory Optimizer 完了！")

if __name__ == '__main__':
    main()

