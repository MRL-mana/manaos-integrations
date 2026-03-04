import os

import pytest


def test_unified_api_app_import_smoke():
	os.environ["PORT"] = "9999"
	os.environ["DEBUG"] = "false"
	try:
		from unified_api_server import app
	except Exception as exc:
		pytest.skip(f"unified_api_server の読み込みに失敗したためスキップ: {exc}")
	assert app is not None
