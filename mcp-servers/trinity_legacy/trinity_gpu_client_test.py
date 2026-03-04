#!/usr/bin/env python3
"""
Trinity GPU統合システムテストクライアント
Trinity達がRunPod GPUを使えるかテスト
"""

import asyncio
import json
import websockets

async def test_trinity_gpu_integration():
    """Trinity GPU統合テスト"""
    print("🤖 Trinity GPU統合システムテスト開始")
    print("=" * 50)
    
    uri = "ws://localhost:9999"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Trinity-RunPodブリッジ接続成功")
            
            # テスト1: GPU状態確認
            print("\n🔥 テスト1: GPU状態確認")
            command = {
                "type": "gpu_status",
                "trinity_id": "test_trinity_1"
            }
            
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            result = json.loads(response)
            
            if "error" not in result:
                print("✅ GPU状態確認成功")
                print(f"GPU情報: {result.get('gpu_info', 'N/A')}")
            else:
                print(f"❌ GPU状態確認失敗: {result['error']}")
            
            # テスト2: 画像生成
            print("\n🎨 テスト2: GPU画像生成")
            command = {
                "type": "gpu_image_generation",
                "trinity_id": "test_trinity_1"
            }
            
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            result = json.loads(response)
            
            if "error" not in result:
                print("✅ GPU画像生成成功")
                print(f"結果: {result.get('result', {}).get('output', 'N/A')[:100]}...")
            else:
                print(f"❌ GPU画像生成失敗: {result['error']}")
            
            # テスト3: 深層学習
            print("\n🧠 テスト3: GPU深層学習")
            command = {
                "type": "gpu_deep_learning",
                "trinity_id": "test_trinity_1"
            }
            
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            result = json.loads(response)
            
            if "error" not in result:
                print("✅ GPU深層学習成功")
                print(f"結果: {result.get('result', {}).get('output', 'N/A')[:100]}...")
            else:
                print(f"❌ GPU深層学習失敗: {result['error']}")
            
            # テスト4: Transformers
            print("\n🤖 テスト4: Transformers")
            command = {
                "type": "gpu_transformers",
                "trinity_id": "test_trinity_1"
            }
            
            await websocket.send(json.dumps(command))
            response = await websocket.recv()
            result = json.loads(response)
            
            if "error" not in result:
                print("✅ Transformers実行成功")
                print(f"結果: {result.get('result', {}).get('output', 'N/A')[:100]}...")
            else:
                print(f"❌ Transformers実行失敗: {result['error']}")
            
            print("\n" + "=" * 50)
            print("🎉 Trinity GPU統合システムテスト完了")
            
    except Exception as e:
        print(f"❌ 接続エラー: {e}")

if __name__ == "__main__":
    asyncio.run(test_trinity_gpu_integration())
