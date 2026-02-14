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


def iter_nodes(xml_text: str):
    # Cheap XML scanning: good enough for UIAutomator dumps.
    for match in re.finditer(r"<node\b[^>]*>", xml_text):
        tag = match.group(0)
        yield tag


def get_attr(tag: str, name: str) -> str | None:
    match = re.search(rf"\b{name}=\"([^\"]*)\"", tag)
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("xml_path")
    parser.add_argument("--resource-id", default=None)
    parser.add_argument("--text-contains", default=None)
    parser.add_argument("--content-desc-contains", default=None)
    parser.add_argument("--package", default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args()

    xml_text = open(args.xml_path, "r", encoding="utf-8").read()

    def matches(tag: str) -> bool:
        if args.resource_id is not None:
            if get_attr(tag, "resource-id") != args.resource_id:
                return False
        if args.package is not None:
            if get_attr(tag, "package") != args.package:
                return False
        if args.text_contains is not None:
            text = get_attr(tag, "text") or ""
            if args.text_contains.lower() not in text.lower():
                return False
        if args.content_desc_contains is not None:
            cd = get_attr(tag, "content-desc") or ""
            if args.content_desc_contains.lower() not in cd.lower():
                return False
        return True

    for tag in iter_nodes(xml_text):
        if not matches(tag):
            continue
        bounds_str = get_attr(tag, "bounds")
        if not bounds_str:
            continue
        bounds = parse_bounds(bounds_str)
        x, y = bounds.center

        if args.format == "json":
            print(
                json.dumps(
                    {
                        "resource_id": get_attr(tag, "resource-id"),
                        "text": get_attr(tag, "text"),
                        "content_desc": get_attr(tag, "content-desc"),
                        "package": get_attr(tag, "package"),
                        "bounds": {
                            "left": bounds.left,
                            "top": bounds.top,
                            "right": bounds.right,
                            "bottom": bounds.bottom,
                            "center": {"x": x, "y": y},
                            "raw": bounds_str,
                        },
                    },
                    ensure_ascii=False,
                )
            )
            return 0

        print(f"{x} {y} {bounds_str}")
        return 0

    print("NOT_FOUND", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
