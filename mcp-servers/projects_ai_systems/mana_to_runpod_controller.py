#!/usr/bin/env python3
"""
Mana → このはサーバー → Trinity達 → RunPod GPU
Manaの指示でTrinity達がRunPod GPUを操作するシステム
"""

import asyncio
import json
import websockets
import time
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ManaRunPodController:
    """Mana → Trinity達 → RunPod GPU コントローラー"""
    
    def __init__(self):
        self.trinity_bridge_uri = "ws://localhost:9999"
        self.connected = False
    
    async def connect_to_trinity(self):
        """Trinity達との接続"""
        try:
            self.websocket = await websockets.connect(self.trinity_bridge_uri)
            self.connected = True
            logger.info("✅ Trinity達との接続成功")
            return True
        except Exception as e:
            logger.error(f"❌ Trinity達との接続失敗: {e}")
            return False
    
    async def send_command_to_trinity(self, command_type, **kwargs):
        """Trinity達にコマンド送信"""
        if not self.connected:
            if not await self.connect_to_trinity():
                return None
        
        command = {
            "type": command_type,
            "trinity_id": "mana_controller",
            "timestamp": time.time(),
            **kwargs
        }
        
        try:
            await self.websocket.send(json.dumps(command))
            response = await self.websocket.recv()
            result = json.loads(response)
            
            logger.info(f"📨 Trinity達からの応答: {command_type}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Trinity達へのコマンド送信失敗: {e}")
            return None
    
    async def mana_gpu_status(self):
        """Mana指示: GPU状態確認"""
        print("🔥 Mana指示: GPU状態確認開始")
        print("=" * 50)
        
        result = await self.send_command_to_trinity("gpu_status")
        
        if result and "error" not in result:
            print("✅ GPU状態確認成功")
            print(f"GPU情報: {result.get('gpu_info', 'N/A')}")
            print(f"接続中のTrinity: {result.get('connected_trinities', 0)}個")
        else:
            print(f"❌ GPU状態確認失敗: {result.get('error', 'Unknown error') if result else 'Connection failed'}")
        
        return result
    
    async def mana_generate_images(self, batch_size=4):
        """Mana指示: 画像生成"""
        print("🎨 Mana指示: 画像生成開始")
        print("=" * 50)
        
        result = await self.send_command_to_trinity(
            "gpu_image_generation",
            batch_size=batch_size,
            description=f"Mana指示による{batch_size}枚の画像生成"
        )
        
        if result and "error" not in result:
            print("✅ 画像生成成功")
            if "result" in result and "output" in result["result"]:
                output = result["result"]["output"]
                print("📊 生成結果:")
                print("-" * 40)
                # 重要な行のみ表示
                lines = output.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['生成', '時間', '完了', 'success', 'generation', 'time']):
                        print(f"  {line}")
                print("-" * 40)
        else:
            print(f"❌ 画像生成失敗: {result.get('error', 'Unknown error') if result else 'Connection failed'}")
        
        return result
    
    async def mana_deep_learning(self, epochs=50):
        """Mana指示: 深層学習"""
        print("🧠 Mana指示: 深層学習開始")
        print("=" * 50)
        
        result = await self.send_command_to_trinity(
            "gpu_deep_learning",
            epochs=epochs,
            description=f"Mana指示による{epochs}エポックの深層学習"
        )
        
        if result and "error" not in result:
            print("✅ 深層学習成功")
            if "result" in result and "output" in result["result"]:
                output = result["result"]["output"]
                print("📊 学習結果:")
                print("-" * 40)
                lines = output.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['学習', '時間', '損失', '完了', 'learning', 'loss', 'time']):
                        print(f"  {line}")
                print("-" * 40)
        else:
            print(f"❌ 深層学習失敗: {result.get('error', 'Unknown error') if result else 'Connection failed'}")
        
        return result
    
    async def mana_transformers(self, text="Hello from Mana through Trinity to RunPod GPU!"):
        """Mana指示: Transformers実行"""
        print("🤖 Mana指示: Transformers実行開始")
        print("=" * 50)
        
        result = await self.send_command_to_trinity(
            "gpu_transformers",
            text=text,
            description=f"Mana指示によるTransformers実行: {text}"
        )
        
        if result and "error" not in result:
            print("✅ Transformers実行成功")
            if "result" in result and "output" in result["result"]:
                output = result["result"]["output"]
                print("📊 実行結果:")
                print("-" * 40)
                lines = output.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in ['推論', '時間', '完了', 'inference', 'time', 'success']):
                        print(f"  {line}")
                print("-" * 40)
        else:
            print(f"❌ Transformers実行失敗: {result.get('error', 'Unknown error') if result else 'Connection failed'}")
        
        return result
    
    async def mana_custom_code(self, code):
        """Mana指示: カスタムコード実行"""
        print("💻 Mana指示: カスタムコード実行開始")
        print("=" * 50)
        
        result = await self.send_command_to_trinity(
            "gpu_custom",
            code=code,
            description="Mana指示によるカスタムコード実行"
        )
        
        if result and "error" not in result:
            print("✅ カスタムコード実行成功")
            if "result" in result and "output" in result["result"]:
                output = result["result"]["output"]
                print("📊 実行結果:")
                print("-" * 40)
                print(output[:500] + "..." if len(output) > 500 else output)
                print("-" * 40)
        else:
            print(f"❌ カスタムコード実行失敗: {result.get('error', 'Unknown error') if result else 'Connection failed'}")
        
        return result
    
    async def run_mana_demo(self):
        """Mana完全デモ実行"""
        print("🚀 Mana → このはサーバー → Trinity達 → RunPod GPU デモ開始")
        print("=" * 70)
        
        # GPU状態確認
        await self.mana_gpu_status()
        
        # 画像生成
        await self.mana_generate_images(batch_size=6)
        
        # 深層学習
        await self.mana_deep_learning(epochs=30)
        
        # Transformers
        await self.mana_transformers()
        
        # カスタムコード
        custom_code = """
import torch
print("🎉 Mana → Trinity → RunPod GPU カスタムコード実行！")
device = torch.device('cuda')
x = torch.randn(100, 100).to(device)
y = torch.mm(x, x.t())
print(f"GPU計算結果: {y.shape}")
print("✅ Mana指示によるカスタムコード完了！")
"""
        await self.mana_custom_code(custom_code)
        
        print("\n" + "=" * 70)
        print("🎉 Mana → このはサーバー → Trinity達 → RunPod GPU デモ完了！")
        print("💡 Manaの指示でTrinity達がRunPod GPUを操作しました！")
        print("=" * 70)
    
    async def close(self):
        """接続終了"""
        if self.connected:
            await self.websocket.close()
            self.connected = False

async def main():
    """メイン実行"""
    controller = ManaRunPodController()
    
    try:
        await controller.run_mana_demo()
    finally:
        await controller.close()

if __name__ == "__main__":
    asyncio.run(main())
