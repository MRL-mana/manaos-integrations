#!/usr/bin/env python3
"""
GPU自動統合システム
GPUとつなげたら自動で使うようにするシステム
"""

import asyncio
import json
import subprocess
import time
from datetime import datetime
import os
import signal
import sys

class GPUAutoIntegration:
    """GPU自動統合システム"""
    
    def __init__(self):
        self.gpu_available = False
        self.gpu_info = {}
        self.auto_tasks = []
        self.monitoring = False
        
    async def check_gpu_connection(self):
        """GPU接続確認"""
        try:
            # nvidia-smiでGPU確認
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout.strip():
                self.gpu_available = True
                gpu_data = result.stdout.strip().split(', ')
                self.gpu_info = {
                    "name": gpu_data[0],
                    "memory_gb": int(gpu_data[1]) / 1024,
                    "timestamp": datetime.now().isoformat()
                }
                print(f"🔥 GPU検出: {self.gpu_info['name']} ({self.gpu_info['memory_gb']:.1f}GB)")
                return True
            else:
                self.gpu_available = False
                print("❌ GPU未検出")
                return False
                
        except Exception as e:
            print(f"❌ GPU確認エラー: {e}")
            self.gpu_available = False
            return False
    
    async def auto_setup_gpu_environment(self):
        """GPU環境の自動セットアップ"""
        if not self.gpu_available:
            return False
            
        print("🚀 GPU環境自動セットアップ開始")
        
        # 作業ディレクトリ作成
        os.makedirs('/workspace/gpu_projects', exist_ok=True)
        os.makedirs('/workspace/auto_results', exist_ok=True)
        
        # PyTorch確認
        try:
            import torch
            if torch.cuda.is_available():
                print(f"✅ PyTorch GPU: {torch.__version__}")
                print(f"🔥 GPU Device: {torch.cuda.get_device_name(0)}")
                return True
            else:
                print("❌ PyTorch GPU未対応")
                return False
        except ImportError:
            print("❌ PyTorch未インストール")
            return False
    
    async def auto_gpu_performance_test(self):
        """GPU性能自動テスト"""
        if not self.gpu_available:
            return
            
        print("🚀 GPU性能自動テスト開始")
        
        try:
            import torch
            
            # GPU性能テスト
            start_time = time.time()
            size = 1000
            x = torch.randn(size, size).cuda()
            y = torch.randn(size, size).cuda()
            z = torch.mm(x, y)
            end_time = time.time()
            
            performance_data = {
                "timestamp": datetime.now().isoformat(),
                "matrix_size": f"{size}x{size}",
                "computation_time_ms": (end_time - start_time) * 1000,
                "gpu_memory_used_gb": torch.cuda.memory_allocated(0) / 1024**3,
                "gpu_utilization": True
            }
            
            # 結果をファイルに保存
            with open('/workspace/auto_results/gpu_performance.json', 'w') as f:
                json.dump(performance_data, f, indent=2)
            
            print(f"✅ GPU性能テスト完了: {performance_data['computation_time_ms']:.1f}ms")
            print(f"🔥 GPU Memory使用: {performance_data['gpu_memory_used_gb']:.2f}GB")
            
        except Exception as e:
            print(f"❌ GPU性能テストエラー: {e}")
    
    async def auto_gpu_demo_project(self):
        """GPU活用デモプロジェクト自動実行"""
        if not self.gpu_available:
            return
            
        print("🎨 GPU活用デモ自動実行開始")
        
        try:
            import torch
            import torch.nn as nn
            
            # 簡単なニューラルネットワーク
            class SimpleNet(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.fc = nn.Linear(100, 10)
                    
                def forward(self, x):
                    return self.fc(x)
            
            # モデル作成・学習
            model = SimpleNet().cuda()
            optimizer = torch.optim.Adam(model.parameters())
            criterion = nn.CrossEntropyLoss()
            
            # ダミーデータで学習
            start_time = time.time()
            for epoch in range(5):
                data = torch.randn(32, 100).cuda()
                target = torch.randint(0, 10, (32,)).cuda()
                
                optimizer.zero_grad()
                output = model(data)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
                
                if epoch % 2 == 0:
                    print(f"   Epoch {epoch}: Loss = {loss.item():.4f}")
            
            end_time = time.time()
            
            demo_results = {
                "timestamp": datetime.now().isoformat(),
                "training_time_ms": (end_time - start_time) * 1000,
                "gpu_memory_used_gb": torch.cuda.memory_allocated(0) / 1024**3,
                "final_loss": loss.item(),
                "status": "success"
            }
            
            # 結果をファイルに保存
            with open('/workspace/auto_results/gpu_demo_results.json', 'w') as f:
                json.dump(demo_results, f, indent=2)
            
            print(f"✅ GPUデモ完了: {demo_results['training_time_ms']:.1f}ms")
            print(f"🔥 Final Loss: {demo_results['final_loss']:.4f}")
            
        except Exception as e:
            print(f"❌ GPUデモエラー: {e}")
    
    async def auto_monitor_gpu_usage(self):
        """GPU使用率自動監視"""
        if not self.gpu_available:
            return
            
        print("📊 GPU使用率自動監視開始")
        
        while self.monitoring:
            try:
                # GPU使用率取得
                result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', 
                                       '--format=csv,noheader,nounits'], 
                                      capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    gpu_data = result.stdout.strip().split(', ')
                    gpu_util = int(gpu_data[0])
                    memory_used = int(gpu_data[1])
                    memory_total = int(gpu_data[2])
                    memory_percent = (memory_used / memory_total) * 100
                    
                    monitor_data = {
                        "timestamp": datetime.now().isoformat(),
                        "gpu_utilization": gpu_util,
                        "memory_used_mb": memory_used,
                        "memory_total_mb": memory_total,
                        "memory_percent": memory_percent
                    }
                    
                    # 監視データをファイルに保存
                    with open('/workspace/auto_results/gpu_monitor.json', 'w') as f:
                        json.dump(monitor_data, f, indent=2)
                    
                    if gpu_util > 0:
                        print(f"🔥 GPU使用率: {gpu_util}% | Memory: {memory_percent:.1f}%")
                
                await asyncio.sleep(10)  # 10秒間隔で監視
                
            except Exception as e:
                print(f"❌ GPU監視エラー: {e}")
                await asyncio.sleep(30)  # エラー時は30秒待機
    
    async def auto_integration_workflow(self):
        """GPU自動統合ワークフロー"""
        print("🤖 GPU自動統合ワークフロー開始")
        print("=" * 50)
        
        # 1. GPU接続確認
        if await self.check_gpu_connection():
            # 2. GPU環境セットアップ
            if await self.auto_setup_gpu_environment():
                # 3. GPU性能テスト
                await self.auto_gpu_performance_test()
                
                # 4. GPU活用デモ
                await self.auto_gpu_demo_project()
                
                # 5. GPU監視開始
                self.monitoring = True
                print("📊 GPU監視開始（バックグラウンド実行）")
                
                # 監視タスクをバックグラウンドで実行
                asyncio.create_task(self.auto_monitor_gpu_usage())
                
                print("✅ GPU自動統合完了！")
                print("🤖 GPUが自動で使えるようになりました！")
                
                # 統合完了データを保存
                integration_data = {
                    "timestamp": datetime.now().isoformat(),
                    "gpu_info": self.gpu_info,
                    "status": "integrated",
                    "monitoring": True,
                    "auto_tasks": ["performance_test", "demo_project", "usage_monitor"]
                }
                
                with open('/workspace/auto_results/gpu_integration.json', 'w') as f:
                    json.dump(integration_data, f, indent=2)
                
                return True
            else:
                print("❌ GPU環境セットアップ失敗")
                return False
        else:
            print("❌ GPU接続確認失敗")
            return False
    
    async def stop_monitoring(self):
        """監視停止"""
        self.monitoring = False
        print("📊 GPU監視停止")

async def main():
    """メイン関数"""
    gpu_auto = GPUAutoIntegration()
    
    # シグナルハンドラー設定
    def signal_handler(signum, frame):
        print("\n🛑 停止シグナル受信")
        asyncio.create_task(gpu_auto.stop_monitoring())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # GPU自動統合実行
        success = await gpu_auto.auto_integration_workflow()
        
        if success:
            print("\n🎉 GPU自動統合システム稼働中！")
            print("💡 停止するには Ctrl+C を押してください")
            
            # メインループ（監視継続）
            while True:
                await asyncio.sleep(1)
        else:
            print("❌ GPU自動統合失敗")
            
    except KeyboardInterrupt:
        print("\n🛑 ユーザーによる停止")
    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        await gpu_auto.stop_monitoring()
        print("✅ GPU自動統合システム停止")

if __name__ == "__main__":
    asyncio.run(main())










