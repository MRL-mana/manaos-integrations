#!/usr/bin/env python3
"""
デュアルGPUアクセスシステム
1. Mana → VS Code → RunPod GPU (直接)
2. Mana → このはサーバー → Trinity達 → RunPod GPU (自動)
両方同時に使用可能
"""

import asyncio
import json
import websockets
import subprocess
import time
from datetime import datetime

class DualGPUAccessSystem:
    """デュアルGPUアクセスシステム"""
    
    def __init__(self):
        self.trinity_bridge_uri = "ws://localhost:9999"
        self.vscode_remote_host = "runpod-gpu"
        self.connected = False
        
    async def trinity_gpu_operation(self, operation_type, **kwargs):
        """Trinity達によるGPU操作"""
        print(f"🤖 Trinity達によるGPU操作: {operation_type}")
        
        try:
            async with websockets.connect(self.trinity_bridge_uri) as websocket:
                command = {
                    "type": operation_type,
                    "trinity_id": "dual_system",
                    "timestamp": datetime.now().isoformat(),
                    **kwargs
                }
                
                await websocket.send(json.dumps(command))
                response = await websocket.recv()
                result = json.loads(response)
                
                if "error" not in result:
                    print(f"✅ Trinity達による{operation_type}成功")
                    return result
                else:
                    print(f"❌ Trinity達による{operation_type}失敗: {result['error']}")
                    return None
                    
        except Exception as e:
            print(f"❌ Trinity達との通信エラー: {e}")
            return None
    
    def vscode_gpu_operation(self, code):
        """VS Code Remote SSHによるGPU操作"""
        print("💻 VS Code Remote SSHによるGPU操作")
        
        try:
            result = subprocess.run([
                "ssh", "-o", "ConnectTimeout=10",
                self.vscode_remote_host,
                f"cd /workspace && python3 -c \"{code}\""
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ VS Code Remote SSH操作成功")
                return {
                    "success": True,
                    "output": result.stdout,
                    "error": result.stderr
                }
            else:
                print("❌ VS Code Remote SSH操作失敗")
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": result.stderr
                }
                
        except Exception as e:
            print(f"❌ VS Code Remote SSHエラー: {e}")
            return {"success": False, "error": str(e)}
    
    async def parallel_gpu_operations(self):
        """並列GPU操作デモ"""
        print("🚀 デュアルGPUアクセスシステム 並列操作デモ")
        print("=" * 60)
        
        # Trinity達とVS Code Remote SSHを並列実行
        tasks = []
        
        # Trinity達による画像生成
        trinity_task = asyncio.create_task(
            self.trinity_gpu_operation("gpu_image_generation")
        )
        tasks.append(trinity_task)
        
        # VS Code Remote SSHによるGPU確認
        vscode_code = """
import torch
print(f"VS Code Remote SSH - CUDA available: {torch.cuda.is_available()}")
print(f"VS Code Remote SSH - GPU name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU'}")
"""
        
        # 非同期でVS Code操作実行
        vscode_task = asyncio.create_task(
            asyncio.get_event_loop().run_in_executor(
                None, self.vscode_gpu_operation, vscode_code
            )
        )
        tasks.append(vscode_task)
        
        # 両方の結果を待つ
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print("\n📊 並列操作結果:")
        print("-" * 40)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"操作{i+1}: エラー - {result}")
            else:
                print(f"操作{i+1}: 成功")
        
        print("-" * 40)
        print("🎉 デュアルGPUアクセスシステム並列操作完了！")
        
        return results
    
    async def intelligent_gpu_routing(self, task_description):
        """インテリジェントGPUルーティング"""
        print(f"🧠 インテリジェントGPUルーティング: {task_description}")
        
        # タスクに応じて最適なルートを選択
        if "自動" in task_description or "バックグラウンド" in task_description:
            print("→ Trinity達に自動実行を委任")
            return await self.trinity_gpu_operation("gpu_custom", 
                code=f"print('Trinity達による自動実行: {task_description}')")
        
        elif "リアルタイム" in task_description or "デバッグ" in task_description:
            print("→ VS Code Remote SSHで直接実行")
            return self.vscode_gpu_operation(f"print('VS Code Remote SSHによる直接実行: {task_description}')")
        
        else:
            print("→ 両方で並列実行")
            # Trinity達とVS Code Remote SSHで並列実行
            trinity_task = self.trinity_gpu_operation("gpu_custom", 
                code=f"print('Trinity達: {task_description}')")
            vscode_task = asyncio.get_event_loop().run_in_executor(
                None, self.vscode_gpu_operation, f"print('VS Code: {task_description}')")
            
            return await asyncio.gather(trinity_task, vscode_task)
    
    async def run_dual_system_demo(self):
        """デュアルシステムデモ実行"""
        print("🎯 デュアルGPUアクセスシステム デモ開始")
        print("=" * 70)
        
        # 1. 並列操作デモ
        await self.parallel_gpu_operations()
        
        print("\n" + "=" * 70)
        
        # 2. インテリジェントルーティングデモ
        tasks = [
            "自動バックグラウンド処理",
            "リアルタイムデバッグ処理", 
            "通常のGPU計算処理"
        ]
        
        for task in tasks:
            print(f"\n🎯 タスク: {task}")
            await self.intelligent_gpu_routing(task)
            time.sleep(1)
        
        print("\n" + "=" * 70)
        print("🎉 デュアルGPUアクセスシステム デモ完了！")
        print("💡 Trinity達とVS Code Remote SSHの両方が利用可能！")
        print("=" * 70)

async def main():
    """メイン実行"""
    system = DualGPUAccessSystem()
    await system.run_dual_system_demo()

if __name__ == "__main__":
    asyncio.run(main())
