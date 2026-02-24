"""
拡張フェーズモジュールのインポートチェック
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("拡張フェーズモジュール インポートチェック")
print("=" * 60)

modules = [
    ("llm_routing", "LLMRouter"),
    ("memory_unified", "UnifiedMemory"),
    ("notification_hub", "NotificationHub"),
    ("secretary_routines", "SecretaryRoutines"),
    ("image_stock", "ImageStock"),
    ("manaos_core_api", "ManaOSCoreAPI")
]

for module_name, class_name in modules:
    print(f"\n[{module_name}]")
    print("-" * 60)
    try:
        module = __import__(module_name, fromlist=[class_name])
        cls = getattr(module, class_name)
        print(f"[OK] {class_name} インポート成功")
        
        # インスタンス化テスト
        try:
            if class_name == "ManaOSCoreAPI":
                instance = cls()
            else:
                instance = cls()
            print(f"[OK] {class_name} インスタンス化成功")
        except Exception as e:
            print(f"[WARN] {class_name} インスタンス化エラー: {e}")
    except ImportError as e:
        print(f"[NG] インポートエラー: {e}")
    except Exception as e:
        print(f"[NG] エラー: {e}")

print("\n" + "=" * 60)
print("チェック完了")
print("=" * 60)


















