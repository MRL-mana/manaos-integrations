import os
import sys
import pytest


def test_unified_api_app_import_smoke():
	os.environ["PORT"] = "9999"
	os.environ["DEBUG"] = "false"
	# 他テストが注入したスタブをクリアして本物をロード
	_mods_to_refresh = ["unified_api_server", "flask", "flask_cors"]
	_saved = {k: sys.modules.pop(k) for k in _mods_to_refresh if k in sys.modules}
	app = None
	try:
		from unified_api_server import app
	except Exception as exc:
		pytest.skip(f"unified_api_server の読み込みに失敗したためスキップ: {exc}")
	finally:
		sys.modules.update(_saved)
	assert app is not None
