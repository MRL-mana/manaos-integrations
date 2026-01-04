#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重複プロセス削除スクリプト
"""

import psutil
import os
from pathlib import Path

# サービス定義
SERVICES = {
    5100: "intent_router.py",
    5101: "task_planner.py",
    5102: "task_critic.py",
    5103: "rag_memory_enhanced.py",
    5104: "task_queue_system.py",
    5105: "ui_operations_api.py",
    5106: "unified_orchestrator.py",
    5107: "task_executor_enhanced.py",
    5108: "portal_integration_api.py",
    5109: "content_generation_loop.py",
    5110: "llm_optimization.py",
    5123: "personality_system.py",
    5124: "autonomy_system.py",
    5125: "secretary_system.py",
    5126: "learning_system_api.py",
    5127: "metrics_collector.py",
    5128: "performance_dashboard.py",
}

def get_processes_on_port(port):
    """ポートを使用しているプロセスを取得"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            connections = proc.connections()
            for conn in connections:
                if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                    processes.append(proc)
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes

def kill_duplicates():
    """重複プロセスを削除"""
    base_dir = Path(__file__).parent
    
    for port, script_name in SERVICES.items():
        processes = get_processes_on_port(port)
        
        if len(processes) > 1:
            print(f"ポート {port} ({script_name}): {len(processes)}個のプロセスを検出")
            
            # スクリプトパスを含むプロセスを特定
            script_path = base_dir / script_name
            matching_procs = []
            
            for proc in processes:
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and script_path.name in ' '.join(cmdline):
                        matching_procs.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if len(matching_procs) > 1:
                # 最初のプロセスを残して、残りを終了
                keep_proc = matching_procs[0]
                kill_procs = matching_procs[1:]
                
                print(f"  PID {keep_proc.info['pid']} を保持")
                for proc in kill_procs:
                    try:
                        print(f"  PID {proc.info['pid']} を終了")
                        proc.terminate()
                        proc.wait(timeout=5)
                    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                        try:
                            proc.kill()
                        except psutil.NoSuchProcess:
                            pass
                    except psutil.AccessDenied:
                        print(f"  PID {proc.info['pid']} へのアクセスが拒否されました（管理者権限が必要）")

if __name__ == "__main__":
    print("重複プロセス削除中...")
    kill_duplicates()
    print("完了")

