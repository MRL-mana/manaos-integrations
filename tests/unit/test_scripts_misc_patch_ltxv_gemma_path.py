"""tests/unit/test_scripts_misc_patch_ltxv_gemma_path.py

patch_ltxv_gemma_path.py の単体テスト
"""
import pytest

import scripts.misc.patch_ltxv_gemma_path as _mod


class TestMain:
    def test_exits_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_mod, "GEMMA_ENCODER", tmp_path / "missing.py")
        with pytest.raises(SystemExit):
            _mod.main()

    def test_no_op_when_already_patched(self, tmp_path, monkeypatch):
        f = tmp_path / "gemma_encoder.py"
        # File already contains the new line → should just return
        f.write_text(_mod.NEW_LINE + "\nother content\n", encoding="utf-8")
        monkeypatch.setattr(_mod, "GEMMA_ENCODER", f)
        _mod.main()  # should not raise

    def test_applies_patch_when_old_line_present(self, tmp_path, monkeypatch):
        f = tmp_path / "gemma_encoder.py"
        f.write_text(f"line1\n{_mod.OLD_LINE}\nline3\n", encoding="utf-8")
        monkeypatch.setattr(_mod, "GEMMA_ENCODER", f)
        _mod.main()
        content = f.read_text(encoding="utf-8")
        assert _mod.NEW_LINE in content
        assert _mod.OLD_LINE not in content
