"""
tests/integration/conftest.py
integration テストスイートの sys.path 設定

各テストファイルが `from file_secretary_db import ...` や
`from brave_search_integration import ...` のようにプロジェクト内モジュールを
インポートできるよう、必要なパスを sys.path に追加する。

追加パス:
  - PROJECT_ROOT:          manaos_integrations/ ルート
  - file_secretary/:       FileSecretaryDB, GoogleDriveIndexer 等
  - scripts/misc/:         BraveSearchIntegration 等
  - step_deep_research/:   StepDeepResearch 関連
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # …/manaos_integrations/

_EXTRA_PATHS = [
    _PROJECT_ROOT,
    _PROJECT_ROOT / "file_secretary",
    _PROJECT_ROOT / "scripts" / "misc",
    _PROJECT_ROOT / "scripts" / "github",
    _PROJECT_ROOT / "step_deep_research",
    _PROJECT_ROOT / "llm",
    _PROJECT_ROOT / "mrl_memory",
    _PROJECT_ROOT / "unified_api",  # unified_logging.get_service_logger 等
]

for _p in _EXTRA_PATHS:
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)
