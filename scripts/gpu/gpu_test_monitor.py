#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GPU使用状況を監視しながらLLM修正を実行"""

import os
import sys
import time
import subprocess
import threading

if sys.platform == 'win32':
    import io
    sys.stdout.reconfigure(encoding='utf-8')

def monitor_gpu():
    """GPU使用状況を監視"""
    print("GPU監視を開始...")
    while True:
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                gpu_info = result.stdout.strip()
                print(f"  GPU: {gpu_info}")
            time.sleep(2)
        except Exception:
            break

def main():
    print("=" * 60)
    print("GPUモード動作確認")
    print("=" * 60)
    
    # GPU監視を開始
    monitor_thread = threading.Thread(target=monitor_gpu, daemon=True)
    monitor_thread.start()
    
    # LLM修正を実行
    print("\nLLM修正を実行中...")
    os.environ['OLLAMA_USE_GPU'] = '1'
    os.environ['MANA_OCR_USE_LARGE_MODEL'] = '1'
    
    from excel_llm_ocr_corrector import ExcelLLMOCRCorrector
    
    corrector = ExcelLLMOCRCorrector()
    start_time = time.time()
    
    result = corrector.correct_excel(
        r'c:\Users\mana4\Desktop\manaos_integrations\SKM_TEST_P1.xlsx',
        r'c:\Users\mana4\Desktop\manaos_integrations\SKM_TEST_P1_GPU_TEST.xlsx',
        verbose=True
    )
    
    elapsed = time.time() - start_time
    
    print(f"\n処理時間: {elapsed:.1f}秒")
    print(f"結果: {result}")
    print("=" * 60)

if __name__ == "__main__":
    main()
