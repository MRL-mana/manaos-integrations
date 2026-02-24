import argparse
import json
import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)


_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def parse_bounds(bounds_str: str) -> Bounds:
    match = _BOUNDS_RE.fullmatch(bounds_str.strip())
    if not match:
        raise ValueError(f"Invalid bounds: {bounds_str!r}")
    left, top, right, bottom = (int(match.group(i)) for i in range(1, 5))
    return Bounds(left=left, top=top, right=right, bottom=bottom)


def extract_bounds_from_uia_xml(xml_text: str, resource_id: str) -> str | None:
    pattern = re.compile(
        rf'resource-id="{re.escape(resource_id)}"[^>]*bounds="([^"]+)"',
        re.IGNORECASE,
    )
    match = pattern.search(xml_text)
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "xml_path",
        help="Path to UIAutomator dump XML pulled from device",
    )
    parser.add_argument(
        "--resource-id",
        default="ch.rmy.android.http_shortcuts:id/widget_base",
        help="resource-id attribute to locate",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
    )

    args = parser.parse_args()

    try:
        xml_text = open(args.xml_path, "r", encoding="utf-8").read()
    except Exception as exc:
        print(f"READ_ERROR: {exc}", file=sys.stderr)
        return 1

    bounds_str = extract_bounds_from_uia_xml(xml_text, args.resource_id)
    if not bounds_str:
        print("NOT_FOUND", file=sys.stderr)
        return 2

    try:
        bounds = parse_bounds(bounds_str)
    except Exception as exc:
        print(f"BAD_BOUNDS: {exc}", file=sys.stderr)
        return 3

    x, y = bounds.center

    if args.format == "json":
        print(
            json.dumps(
                {
                    "resource_id": args.resource_id,
                    "bounds": {
                        "left": bounds.left,
                        "top": bounds.top,
                        "right": bounds.right,
                        "bottom": bounds.bottom,
                        "center": {"x": x, "y": y},
                    },
                },
                ensure_ascii=False,
            )
        )
        return 0

    print(f"{x} {y} {bounds_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
