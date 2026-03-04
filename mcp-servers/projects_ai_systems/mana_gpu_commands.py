#!/usr/bin/env python3
"""
Mana GPU コマンドライン
Manaが簡単にRunPod GPUを操作できるコマンド集
"""

import asyncio
import json
import websockets
import sys

class ManaGPUCommands:
    """Mana GPU コマンドライン"""
    
    def __init__(self):
        self.trinity_bridge_uri = "ws://localhost:9999"
        self.connected = False
    
    async def connect_to_trinity(self):
        """Trinity達との接続"""
        try:
            self.websocket = await websockets.connect(self.trinity_bridge_uri)
            self.connected = True
            print("✅ Trinity達と接続中...")
            return True
        except Exception as e:
            print(f"❌ Trinity達との接続失敗: {e}")
            return False
    
    async def send_command(self, command_type, **kwargs):
        """Trinity達にコマンド送信"""
        if not self.connected:
            if not await self.connect_to_trinity():
                return None
        
        command = {
            "type": command_type,
            "trinity_id": "mana_commands",
            **kwargs
        }
        
        try:
            await self.websocket.send(json.dumps(command))
            response = await self.websocket.recv()
            return json.loads(response)
        except Exception as e:
            print(f"❌ コマンド送信失敗: {e}")
            return None
    
    async def gpu_status(self):
        """GPU状態確認"""
        print("🔥 GPU状態確認中...")
        result = await self.send_command("gpu_status")
        
        if result and "error" not in result:
            print("✅ GPU状態確認完了")
            return True
        else:
            print("❌ GPU状態確認失敗")
            return False
    
    async def generate_images(self, count=4):
        """画像生成"""
        print(f"🎨 {count}枚の画像生成中...")
        result = await self.send_command("gpu_image_generation", batch_size=count)
        
        if result and "error" not in result:
            print(f"✅ {count}枚の画像生成完了")
            return True
        else:
            print("❌ 画像生成失敗")
            return False
    
    async def deep_learning(self, epochs=50):
        """深層学習"""
        print(f"🧠 {epochs}エポックの深層学習中...")
        result = await self.send_command("gpu_deep_learning", epochs=epochs)
        
        if result and "error" not in result:
            print(f"✅ {epochs}エポックの深層学習完了")
            return True
        else:
            print("❌ 深層学習失敗")
            return False
    
    async def transformers(self):
        """Transformers実行"""
        print("🤖 Transformers実行中...")
        result = await self.send_command("gpu_transformers")
        
        if result and "error" not in result:
            print("✅ Transformers実行完了")
            return True
        else:
            print("❌ Transformers実行失敗")
            return False
    
    async def custom_code(self, code):
        """カスタムコード実行"""
        print("💻 カスタムコード実行中...")
        result = await self.send_command("gpu_custom", code=code)
        
        if result and "error" not in result:
            print("✅ カスタムコード実行完了")
            return True
        else:
            print("❌ カスタムコード実行失敗")
            return False
    
    async def close(self):
        """接続終了"""
        if self.connected:
            await self.websocket.close()

def print_help():
    """ヘルプ表示"""
    print("🚀 Mana GPU コマンドライン")
    print("=" * 50)
    print("使用方法:")
    print("  python3 mana_gpu_commands.py <コマンド> [オプション]")
    print("")
    print("コマンド:")
    print("  status                    GPU状態確認")
    print("  images [枚数]            画像生成 (デフォルト: 4枚)")
    print("  learning [エポック]      深層学習 (デフォルト: 50エポック)")
    print("  transformers             Transformers実行")
    print("  demo                     全機能デモ実行")
    print("  help                     このヘルプを表示")
    print("")
    print("例:")
    print("  python3 mana_gpu_commands.py status")
    print("  python3 mana_gpu_commands.py images 8")
    print("  python3 mana_gpu_commands.py learning 100")
    print("  python3 mana_gpu_commands.py demo")

async def run_command(command, args):
    """コマンド実行"""
    mana = ManaGPUCommands()
    
    try:
        if command == "status":
            await mana.gpu_status()
        elif command == "images":
            count = int(args[0]) if args else 4
            await mana.generate_images(count)
        elif command == "learning":
            epochs = int(args[0]) if args else 50
            await mana.deep_learning(epochs)
        elif command == "transformers":
            await mana.transformers()
        elif command == "demo":
            print("🚀 Mana GPU デモ開始")
            print("=" * 40)
            await mana.gpu_status()
            await mana.generate_images(6)
            await mana.deep_learning(30)
            await mana.transformers()
            print("🎉 デモ完了！")
        else:
            print(f"❌ 不明なコマンド: {command}")
            print_help()
    finally:
        await mana.close()

def main():
    """メイン実行"""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    args = sys.argv[2:] if len(sys.argv) > 2 else []
    
    if command == "help":
        print_help()
        return
    
    asyncio.run(run_command(command, args))

if __name__ == "__main__":
    main()
