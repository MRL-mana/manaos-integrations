#!/usr/bin/env python3
"""
RunPod WebSocket Bridge
WebSocket経由でRunPodとリアルタイム通信する
"""

import asyncio
import websockets
import json
import subprocess
from datetime import datetime

class RunPodWebSocketBridge:
    def __init__(self):
        self.clients = set()
        self.runpod_connection = None
        self.is_connected = False
        
    async def register_client(self, websocket, path):
        """クライアント登録"""
        self.clients.add(websocket)
        print(f"✅ クライアント接続: {websocket.remote_address}")
        
        try:
            await websocket.send(json.dumps({
                "type": "connection",
                "message": "RunPod WebSocket Bridge接続完了",
                "timestamp": datetime.now().isoformat()
            }))
            
            # RunPodへの接続確認
            await self.check_runpod_connection()
            
            async for message in websocket:
                await self.handle_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"❌ クライアント切断: {websocket.remote_address}")
    
    async def check_runpod_connection(self):
        """RunPod接続確認"""
        try:
            # RunPodのWeb Terminal経由で接続確認
            result = subprocess.run([
                'curl', '-s', 'http://213.181.111.2:19123'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                self.is_connected = True
                await self.broadcast({
                    "type": "runpod_status",
                    "connected": True,
                    "message": "RunPod Web Terminal接続確認"
                })
            else:
                self.is_connected = False
                await self.broadcast({
                    "type": "runpod_status", 
                    "connected": False,
                    "message": "RunPod Web Terminal接続失敗"
                })
                
        except Exception as e:
            print(f"❌ RunPod接続確認エラー: {e}")
            self.is_connected = False
    
    async def handle_message(self, websocket, message):
        """メッセージ処理"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "gpu_status":
                await self.get_gpu_status(websocket)
            elif message_type == "gpu_execute":
                await self.execute_gpu_code(websocket, data.get("code", ""))
            elif message_type == "ping":
                await websocket.send(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }))
            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"未知のメッセージタイプ: {message_type}"
                }))
                
        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "無効なJSON形式"
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"メッセージ処理エラー: {str(e)}"
            }))
    
    async def get_gpu_status(self, websocket):
        """GPU状態取得"""
        try:
            # Web Terminal経由でGPU状態確認
            gpu_code = '''
import torch
import json

status = {
    "cuda_available": torch.cuda.is_available(),
    "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    "gpu_memory": f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB" if torch.cuda.is_available() else None
}

print(json.dumps(status))
'''
            
            # Web Terminal経由で実行（実際の実装では別の方法が必要）
            result = await self.execute_via_web_terminal(gpu_code)
            
            await websocket.send(json.dumps({
                "type": "gpu_status",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }))
            
        except Exception as e:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"GPU状態取得エラー: {str(e)}"
            }))
    
    async def execute_gpu_code(self, websocket, code):
        """GPUコード実行"""
        try:
            # Web Terminal経由でコード実行
            result = await self.execute_via_web_terminal(code)
            
            await websocket.send(json.dumps({
                "type": "gpu_execute_result",
                "data": result,
                "timestamp": datetime.now().isoformat()
            }))
            
        except Exception as e:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"GPUコード実行エラー: {str(e)}"
            }))
    
    async def execute_via_web_terminal(self, code):
        """Web Terminal経由でコード実行（シミュレーション）"""
        # 実際の実装では、Web TerminalのAPIやスクレイピングが必要
        # ここではシミュレーション
        return {
            "success": True,
            "output": "Web Terminal経由での実行結果（シミュレーション）",
            "error": ""
        }
    
    async def broadcast(self, message):
        """全クライアントにブロードキャスト"""
        if self.clients:
            disconnected = set()
            for client in self.clients:
                try:
                    await client.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(client)
            
            # 切断されたクライアントを削除
            self.clients -= disconnected
    
    async def run_server(self, host="0.0.0.0", port=8765):
        """WebSocketサーバー起動"""
        print(f"🚀 WebSocketサーバー起動: ws://{host}:{port}")
        
        async with websockets.serve(self.register_client, host, port):
            print("✅ WebSocketサーバー稼働中")
            print("📡 接続URL: ws://213.181.111.2:8765")
            
            # 定期的なRunPod状態確認
            while True:
                await asyncio.sleep(30)  # 30秒ごと
                await self.check_runpod_connection()

def main():
    """メイン実行"""
    print("🌉 RunPod WebSocket Bridge")
    print("=" * 40)
    
    bridge = RunPodWebSocketBridge()
    
    try:
        asyncio.run(bridge.run_server())
    except KeyboardInterrupt:
        print("\n🛑 WebSocketサーバー停止")
    except Exception as e:
        print(f"❌ サーバーエラー: {e}")

if __name__ == "__main__":
    main()
