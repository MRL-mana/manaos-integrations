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
import types
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]  # …/manaos_integrations/

_EXTRA_PATHS = [
    _PROJECT_ROOT,
    _PROJECT_ROOT / "file_secretary",
    _PROJECT_ROOT / "scripts" / "misc",
    _PROJECT_ROOT / "scripts" / "github",
    _PROJECT_ROOT / "scripts" / "temp",
    _PROJECT_ROOT / "scripts" / "google",
    _PROJECT_ROOT / "archive" / "legacy_improved",
    _PROJECT_ROOT / "step_deep_research",
    _PROJECT_ROOT / "llm",
    _PROJECT_ROOT / "mrl_memory",
    _PROJECT_ROOT / "unified_api",  # unified_logging.get_service_logger 等
]

for _p in _EXTRA_PATHS:
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# ─────────────────────────────────────────────────────────────────────────────
# スタブ sys.modules（重い外部依存をバイパス）
# ─────────────────────────────────────────────────────────────────────────────

# manaos_complete_integration スタブ
# 本モジュールは多数の SQLite DB を初期化するため 25+ 秒かかる。
# 結合テストでの DB 接続プール競合による無限ブロックを防ぐため、
# 軽量スタブで置き換える。
if "manaos_complete_integration" not in sys.modules:
    _mci_stub = types.ModuleType("manaos_complete_integration")

    class _ManaOSCompleteIntegration:  # noqa: N801
        def __init__(self, *a, **kw):
            pass

        def is_available(self):
            return True

        def get_comprehensive_status(self):
            return {
                "integrations": {"core": True, "extended": True},
                "advanced_features": {"ai": True, "automation": True},
            }

        def get_complete_status(self):
            return {
                "core": {"status": "stub"},
                "memory_learning": {},
                "personality_autonomy_secretary": {},
            }

    _mci_stub.ManaOSCompleteIntegration = _ManaOSCompleteIntegration
    sys.modules["manaos_complete_integration"] = _mci_stub

# manaos_integration_orchestrator スタブ
# check_all_services(use_parallel=True) が ThreadPoolExecutor + HTTP 呼び出しを行い
# 単体で 66+ 秒 / 全5テストで 148+ 秒かかるためスタブで置き換える。
if "manaos_integration_orchestrator" not in sys.modules:
    _mio_stub = types.ModuleType("manaos_integration_orchestrator")

    class _ManaOSIntegrationOrchestrator:  # noqa: N801
        def __init__(self, *a, **kw):
            pass

        def check_all_services(self, use_parallel: bool = True):
            return {
                "summary": {
                    "total_services": 0,
                    "available_services": 0,
                    "availability_rate": 0.0,
                },
                "manaos_services": {},
                "integration_services": {},
            }

        def get_comprehensive_status(self):
            return {"status": "stub", "services": {}}

        def optimize_system(self):
            return {}

    _mio_stub.ManaOSIntegrationOrchestrator = _ManaOSIntegrationOrchestrator
    sys.modules["manaos_integration_orchestrator"] = _mio_stub

# manaos_service_bridge スタブ
# check_manaos_services(use_parallel=True) が HTTP 呼び出しを行い遅延するためスタブ。
if "manaos_service_bridge" not in sys.modules:
    _msb_stub = types.ModuleType("manaos_service_bridge")

    class _ManaOSServiceBridge:  # noqa: N801
        def __init__(self, *a, **kw):
            pass

        def check_manaos_services(self, use_parallel: bool = True):
            return {}

        def get_integration_status(self):
            return {"status": "stub", "services": {}}

    _msb_stub.ManaOSServiceBridge = _ManaOSServiceBridge
    sys.modules["manaos_service_bridge"] = _msb_stub

# n8n_integration スタブ
# test_scripts_misc_manaos_complete_integration.py (unit) がコレクション時に
# sys.modules.setdefault("n8n_integration", MagicMock()) を実行するため、
# 先にここでプレーンなスタブを設定してユニットテストの汚染を防ぐ。
if "n8n_integration" not in sys.modules:
    _n8n_stub = types.ModuleType("n8n_integration")

    class _N8NIntegration:  # noqa: N801
        def __init__(self, *a, **kw):
            pass

        def is_available(self) -> bool:
            return False

    _n8n_stub.N8NIntegration = _N8NIntegration
    sys.modules["n8n_integration"] = _n8n_stub
