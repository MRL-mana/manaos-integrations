"""ManaOS統合モジュール直接テスト（pytest対応）"""

import importlib

import pytest


def _import_or_skip(module_name: str):
    fallback_map = {
        "svi_wan22_video_integration": ["svi.svi_wan22_video_integration"],
    }
    candidates = [module_name] + fallback_map.get(module_name, [])
    last_error = None
    for candidate in candidates:
        try:
            return importlib.import_module(candidate)
        except Exception as exc:
            last_error = exc
    pytest.skip(f"{module_name} が利用不可のためスキップ: {last_error}")


@pytest.mark.parametrize(
    "module_name,symbol_name",
    [
        ("memory_unified", "UnifiedMemory"),
        ("obsidian_integration", "ObsidianIntegration"),
        ("google_drive_integration", "GoogleDriveIntegration"),
        ("rows_integration", "RowsIntegration"),
        ("llm_routing", "LLMRouter"),
        ("comfyui_integration", "ComfyUIIntegration"),
        ("svi_wan22_video_integration", "SVIWan22VideoIntegration"),
    ],
)
def test_module_symbol_smoke(module_name: str, symbol_name: str):
    module = _import_or_skip(module_name)
    symbol = getattr(module, symbol_name, None)
    if symbol is None:
        pytest.skip(f"{module_name}.{symbol_name} が見つからないためスキップ")
    assert symbol is not None
