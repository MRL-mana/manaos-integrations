"""
Unit tests for scripts/misc/extract_widget_bounds.py
（純粋な Python ユーティリティ - 外部依存なし）
"""
import pytest
from scripts.misc.extract_widget_bounds import (
    Bounds,
    parse_bounds,
    extract_bounds_from_uia_xml,
)


class TestBounds:
    def test_center_calculation(self):
        b = Bounds(left=0, top=0, right=400, bottom=200)
        assert b.center == (200, 100)

    def test_center_with_offset(self):
        b = Bounds(left=50, top=100, right=250, bottom=300)
        assert b.center == (150, 200)

    def test_frozen(self):
        b = Bounds(0, 0, 10, 10)
        with pytest.raises((AttributeError, TypeError)):
            b.left = 5  # type: ignore


class TestParseBounds:
    def test_typical_bounds(self):
        b = parse_bounds("[100,200][300,400]")
        assert b.left == 100
        assert b.top == 200
        assert b.right == 300
        assert b.bottom == 400

    def test_raises_on_garbage(self):
        with pytest.raises(ValueError):
            parse_bounds("garbage")

    def test_whitespace_stripped(self):
        b = parse_bounds("  [10,20][30,40]  ")
        assert b.left == 10


class TestExtractBoundsFromUiaXml:
    _SAMPLE_XML = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hierarchy>'
        '<node resource-id="com.example:id/switch_widget" '
        'bounds="[540,1234][600,1290]" clickable="true"/>'
        '<node resource-id="com.other:id/button" '
        'bounds="[0,0][100,50]" clickable="false"/>'
        '</hierarchy>'
    )

    def test_finds_correct_bounds(self):
        result = extract_bounds_from_uia_xml(
            self._SAMPLE_XML, "com.example:id/switch_widget"
        )
        assert result == "[540,1234][600,1290]"

    def test_returns_none_when_not_found(self):
        result = extract_bounds_from_uia_xml(
            self._SAMPLE_XML, "com.notexist:id/widget"
        )
        assert result is None

    def test_finds_second_node(self):
        result = extract_bounds_from_uia_xml(
            self._SAMPLE_XML, "com.other:id/button"
        )
        assert result == "[0,0][100,50]"

    def test_empty_xml_returns_none(self):
        assert extract_bounds_from_uia_xml("", "any.id") is None

    def test_case_insensitive_search(self):
        xml = '<node resource-id="COM.EXAMPLE:ID/WIDGET" bounds="[1,2][3,4]"/>'
        # The regex uses re.IGNORECASE
        result = extract_bounds_from_uia_xml(xml, "COM.EXAMPLE:ID/WIDGET")
        assert result == "[1,2][3,4]"
