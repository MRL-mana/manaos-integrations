"""
Unit tests for scripts/misc/extract_uia_bounds.py
（純粋な Python ユーティリティ - 外部依存なし）
"""
import pytest
from scripts.misc.extract_uia_bounds import Bounds, parse_bounds, iter_nodes, get_attr


class TestBounds:
    def test_center_calculation(self):
        b = Bounds(left=100, top=200, right=300, bottom=400)
        assert b.center == (200, 300)

    def test_center_odd_dimensions(self):
        b = Bounds(left=0, top=0, right=101, bottom=51)
        assert b.center == (50, 25)

    def test_equality(self):
        b1 = Bounds(left=10, top=20, right=30, bottom=40)
        b2 = Bounds(left=10, top=20, right=30, bottom=40)
        assert b1 == b2

    def test_immutable(self):
        b = Bounds(0, 0, 100, 100)
        with pytest.raises((AttributeError, TypeError)):
            b.left = 99  # type: ignore


class TestParseBounds:
    def test_parses_valid_bounds(self):
        b = parse_bounds("[10,20][300,400]")
        assert b == Bounds(left=10, top=20, right=300, bottom=400)

    def test_handles_whitespace(self):
        b = parse_bounds("  [0,0][1920,1080]  ")
        assert b.right == 1920
        assert b.bottom == 1080

    def test_raises_on_invalid_format(self):
        with pytest.raises(ValueError):
            parse_bounds("invalid")

    def test_raises_on_partial_bounds(self):
        with pytest.raises(ValueError):
            parse_bounds("[10,20]")

    def test_zero_bounds(self):
        b = parse_bounds("[0,0][0,0]")
        assert b.center == (0, 0)


class TestIterNodes:
    def test_yields_node_tags(self):
        xml = '<node resource-id="a" bounds="[0,0][100,100]"></node>'
        tags = list(iter_nodes(xml))
        assert len(tags) == 1
        assert 'resource-id="a"' in tags[0]

    def test_yields_multiple_nodes(self):
        xml = (
            '<node resource-id="a" bounds="[0,0][10,10]">'
            '<node resource-id="b" bounds="[10,10][20,20]"></node>'
            '</node>'
        )
        tags = list(iter_nodes(xml))
        assert len(tags) == 2

    def test_empty_xml_yields_nothing(self):
        assert list(iter_nodes("<hierarchy></hierarchy>")) == []


class TestGetAttr:
    def test_returns_attribute_value(self):
        tag = '<node resource-id="com.example:id/button" text="OK">'
        assert get_attr(tag, "resource-id") == "com.example:id/button"
        assert get_attr(tag, "text") == "OK"

    def test_returns_none_when_missing(self):
        tag = '<node resource-id="foo">'
        assert get_attr(tag, "bounds") is None

    def test_handles_empty_attribute_value(self):
        tag = '<node text="" resource-id="x">'
        assert get_attr(tag, "text") == ""
