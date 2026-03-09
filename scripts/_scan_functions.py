#!/usr/bin/env python3
import inspect, subprocess, sys

scripts = [
    'rows_quick_start', 'set_openrouter_api_key', 'get_from_konoha_server',
    'download_civitai_favorites', 'integrate_to_manaos_complete',
    'complete_integration_test', 'integration_guide',
    'learning_memory_integration', 'manual_init_test', 'ultimate_integration',
    'resume_ultra_aggressive_v3', 'force_restart_and_generate',
    'try_restart_and_generate', 'open_generated_images',
]

for s in scripts:
    try:
        m = __import__('scripts.misc.' + s, fromlist=[s])
        funcs = [n for n, v in inspect.getmembers(m) if inspect.isfunction(v) and v.__module__ == m.__name__]
        clss = [n for n, v in inspect.getmembers(m) if inspect.isclass(v) and v.__module__ == m.__name__]
        print(f'{s}: funcs={funcs} cls={clss}')
    except Exception as e:
        print(f'{s}: FAIL [{e}]')
