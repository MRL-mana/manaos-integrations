# -*- coding: utf-8 -*-
"""
Stable Diffusion PyTorch環境修復スクリプト
RTX 5080向けのtorch.xpu問題を解決
"""

import subprocess
import sys
import os

def run_command(cmd, check=True):
    """コマンドを実行"""
    print(f"\n実行中: {cmd}")
    print("-" * 60)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)
    if check and result.returncode != 0:
        print(f"[ERROR] コマンドが失敗しました: {result.returncode}")
        return False
    return True

def check_torch():
    """PyTorchの状態を確認"""
    print("=" * 60)
    print("PyTorch環境確認")
    print("=" * 60)
    
    try:
        import torch
        print(f"PyTorchバージョン: {torch.__version__}")
        print(f"CUDA利用可能: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDAバージョン: {torch.version.cuda}")
            print(f"GPU数: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        
        # xpu属性の確認
        if hasattr(torch, 'xpu'):
            print("[WARNING] torch.xpuが存在します（Intel GPU関連）")
        else:
            print("[OK] torch.xpuは存在しません（正常）")
        
        return True
    except ImportError:
        print("[ERROR] PyTorchがインストールされていません")
        return False
    except Exception as e:
        print(f"[ERROR] PyTorch確認エラー: {e}")
        return False

def check_diffusers():
    """diffusersの状態を確認"""
    print("\n" + "=" * 60)
    print("diffusers確認")
    print("=" * 60)
    
    try:
        import diffusers
        print(f"diffusersバージョン: {diffusers.__version__}")
        return True
    except ImportError:
        print("[INFO] diffusersがインストールされていません")
        return False
    except Exception as e:
        print(f"[ERROR] diffusers確認エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def fix_torch():
    """PyTorch環境を修復"""
    print("\n" + "=" * 60)
    print("PyTorch環境修復")
    print("=" * 60)
    
    print("\n[1] 混ざり物を削除...")
    packages = [
        "torch", "torchvision", "torchaudio",
        "xformers", "intel-extension-for-pytorch"
    ]
    
    for pkg in packages:
        run_command(f"pip uninstall -y {pkg}", check=False)
    
    print("\n[2] pipキャッシュをクリア...")
    run_command("pip cache purge", check=False)
    
    print("\n[3] RTX 5080向けPyTorch nightly (cu128)をインストール...")
    cmd = (
        "pip install --no-cache-dir --pre torch torchvision torchaudio "
        "--index-url https://download.pytorch.org/whl/nightly/cu128"
    )
    if not run_command(cmd):
        print("[ERROR] PyTorchインストールに失敗しました")
        return False
    
    print("\n[4] 生存確認...")
    return check_torch()

def fix_diffusers():
    """diffusersを調整"""
    print("\n" + "=" * 60)
    print("diffusers調整")
    print("=" * 60)
    
    print("\n[1] 現在のdiffusersバージョンを確認...")
    check_diffusers()
    
    print("\n[2] diffusersを下げる（必要に応じて）...")
    print("   注意: まずは現在のバージョンで動作確認してください")
    
    response = input("\ndiffusersを下げますか？ (y/N): ").strip().lower()
    if response == 'y':
        cmd = 'pip install "diffusers<0.31" "accelerate<0.34"'
        return run_command(cmd)
    else:
        print("スキップしました")
        return True

def test_sd_import():
    """Stable Diffusionのインポートテスト"""
    print("\n" + "=" * 60)
    print("Stable Diffusionインポートテスト")
    print("=" * 60)
    
    try:
        print("\n[1] diffusersをインポート...")
        from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
        print("[OK] diffusersインポート成功")
        
        print("\n[2] Stable Diffusionパイプラインのインポートテスト...")
        # 実際のモデル読み込みはしない（時間がかかるため）
        print("[OK] インポートテスト完了")
        print("    実際のモデル読み込みは時間がかかるため、ここではスキップします")
        
        return True
    except AttributeError as e:
        if 'xpu' in str(e):
            print(f"[ERROR] torch.xpuエラーが発生しました: {e}")
            print("\n対処方法:")
            print("1. PyTorch nightly (cu128)が正しくインストールされているか確認")
            print("2. diffusersのバージョンを下げる（fix_diffusers()を実行）")
            return False
        else:
            print(f"[ERROR] 属性エラー: {e}")
            return False
    except ImportError as e:
        print(f"[ERROR] インポートエラー: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メイン処理"""
    print("=" * 60)
    print("Stable Diffusion PyTorch環境修復ツール")
    print("RTX 5080向け torch.xpu問題解決")
    print("=" * 60)
    
    # 現在の状態確認
    print("\n[STEP 1] 現在の環境確認")
    torch_ok = check_torch()
    diffusers_ok = check_diffusers()
    
    # エラー詳細の確認
    if not torch_ok:
        print("\n[ERROR] PyTorchが正しくインストールされていません")
        response = input("修復を実行しますか？ (y/N): ").strip().lower()
        if response == 'y':
            if not fix_torch():
                print("\n[ERROR] PyTorch修復に失敗しました")
                return
        else:
            print("修復をスキップしました")
            return
    
    # diffusersのインポートテスト
    print("\n[STEP 2] diffusersインポートテスト")
    if not test_sd_import():
        print("\n[STEP 3] diffusers調整")
        response = input("diffusersを調整しますか？ (y/N): ").strip().lower()
        if response == 'y':
            fix_diffusers()
            print("\n再度インポートテストを実行してください")
    
    print("\n" + "=" * 60)
    print("修復処理完了")
    print("=" * 60)
    print("\n次のステップ:")
    print("1. python -c \"import torch; print(torch.cuda.is_available())\" で確認")
    print("2. llama3_guru_image_generator.py で画像生成をテスト")
    print("3. まだエラーが出る場合は、エラーメッセージの最初30行と最後30行を確認")

if __name__ == "__main__":
    main()






