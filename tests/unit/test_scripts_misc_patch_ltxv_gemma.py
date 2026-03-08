"""
Unit tests for scripts/misc/patch_ltxv_gemma_encoder.py and
scripts/misc/patch_ltxv_gemma_path.py
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


# ─── patch_ltxv_gemma_encoder ──────────────────────────────────────────────────
from scripts.misc.patch_ltxv_gemma_encoder import (
    main as encoder_main,
    OLD_LINE as ENC_OLD,
    NEW_LINE as ENC_NEW,
)


class TestPatchLtxvGemmaEncoder:
    def _make_encoder_py(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "gemma_encoder.py"
        p.write_text(content, encoding="utf-8")
        return p

    def _patch_path(self, tmp_path: Path):
        encoder_py = tmp_path / "gemma_encoder.py"
        return patch(
            "scripts.misc.patch_ltxv_gemma_encoder.GEMMA_ENCODER",
            encoder_py,
        )

    def test_exits_1_when_file_missing(self, tmp_path: Path):
        """ファイルが存在しない場合 sys.exit(1)"""
        with self._patch_path(tmp_path):
            with pytest.raises(SystemExit) as exc:
                encoder_main()
        assert exc.value.code == 1

    def test_returns_when_already_patched(self, tmp_path: Path):
        """既にパッチ済みなら正常終了（例外なし）"""
        content = f"# gemma\n{ENC_NEW}\n"
        self._make_encoder_py(tmp_path, content)
        with self._patch_path(tmp_path):
            encoder_main()  # should not raise

    def test_exits_1_when_old_line_missing(self, tmp_path: Path):
        """OLD_LINE が見つからない場合 sys.exit(1)"""
        self._make_encoder_py(tmp_path, "# no old line here\n")
        with self._patch_path(tmp_path):
            with pytest.raises(SystemExit) as exc:
                encoder_main()
        assert exc.value.code == 1

    def test_patches_file_successfully(self, tmp_path: Path):
        """OLD_LINE → NEW_LINE に置換され、バックアップも作成"""
        content = f"# gemma_encoder.py\n{ENC_OLD}\n# end\n"
        enc_py = self._make_encoder_py(tmp_path, content)
        with self._patch_path(tmp_path):
            encoder_main()
        new_content = enc_py.read_text(encoding="utf-8")
        assert ENC_NEW in new_content
        assert ENC_OLD not in new_content
        # backup should exist
        backup = enc_py.with_suffix(".gemma_encoder.py.bak")
        assert backup.exists()


# ─── patch_ltxv_gemma_path ────────────────────────────────────────────────────
from scripts.misc.patch_ltxv_gemma_path import (
    main as path_main,
    OLD_LINE as PATH_OLD,
    NEW_LINE as PATH_NEW,
)


class TestPatchLtxvGemmaPath:
    def _make_encoder_py(self, tmp_path: Path, content: str) -> Path:
        p = tmp_path / "gemma_encoder.py"
        p.write_text(content, encoding="utf-8")
        return p

    def _patch_path(self, tmp_path: Path):
        encoder_py = tmp_path / "gemma_encoder.py"
        return patch(
            "scripts.misc.patch_ltxv_gemma_path.GEMMA_ENCODER",
            encoder_py,
        )

    def test_exits_1_when_file_missing(self, tmp_path: Path):
        with self._patch_path(tmp_path):
            with pytest.raises(SystemExit) as exc:
                path_main()
        assert exc.value.code == 1

    def test_returns_when_already_patched(self, tmp_path: Path):
        content = f"# gemma\n{PATH_NEW}\n"
        self._make_encoder_py(tmp_path, content)
        with self._patch_path(tmp_path):
            path_main()  # should not raise

    def test_exits_1_when_old_line_missing(self, tmp_path: Path):
        self._make_encoder_py(tmp_path, "# no old line\n")
        with self._patch_path(tmp_path):
            with pytest.raises(SystemExit) as exc:
                path_main()
        assert exc.value.code == 1

    def test_patches_file_successfully(self, tmp_path: Path):
        content = f"# gemma_encoder.py\n{PATH_OLD}\n# end\n"
        enc_py = self._make_encoder_py(tmp_path, content)
        with self._patch_path(tmp_path):
            path_main()
        new_content = enc_py.read_text(encoding="utf-8")
        assert PATH_NEW in new_content
        assert PATH_OLD not in new_content
