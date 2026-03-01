#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal file-secretary rule engine with audit logging."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


@dataclass
class Rule:
    name: str
    match: dict[str, Any]
    action: dict[str, Any]


def load_rules(path: Path) -> tuple[list[Rule], dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)
    if not isinstance(loaded, dict):
        raise ValueError("rules root must be mapping")

    rules_raw = loaded.get("rules", [])
    if not isinstance(rules_raw, list):
        raise ValueError("rules must be list")

    parsed: list[Rule] = []
    for item in rules_raw:
        if not isinstance(item, dict):
            continue
        match_raw = item.get("match")
        action_raw = item.get("action")
        match_data: dict[str, Any] = (
            match_raw if isinstance(match_raw, dict) else {}
        )
        action_data: dict[str, Any] = (
            action_raw if isinstance(action_raw, dict) else {"type": "none"}
        )
        parsed.append(
            Rule(
                name=str(item.get("name") or "unnamed_rule"),
                match=match_data,
                action=action_data,
            )
        )

    defaults = loaded.get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}

    return parsed, defaults


def to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def file_matches(rule: Rule, file_path: Path) -> bool:
    match = rule.match
    filename = file_path.name
    lower_filename = filename.lower()

    ext_rules = [item.lower() for item in to_list(match.get("extension"))]
    if ext_rules:
        if file_path.suffix.lower() not in ext_rules:
            return False

    contains_rules = [
        item.lower()
        for item in to_list(match.get("filename_contains"))
    ]
    if contains_rules:
        if not any(token in lower_filename for token in contains_rules):
            return False

    max_size = match.get("max_size_bytes")
    if max_size is not None:
        try:
            max_size_int = int(max_size)
        except (TypeError, ValueError):
            return False
        if file_path.stat().st_size > max_size_int:
            return False

    return True


def pick_rule(rules: list[Rule], file_path: Path) -> Rule | None:
    for rule in rules:
        if file_matches(rule, file_path):
            return rule
    return None


def safe_target_path(inbox: Path, target: str, filename: str) -> Path:
    target_dir = Path(target)
    if not target_dir.is_absolute():
        target_dir = inbox / target_dir
    target_dir = target_dir.resolve()
    inbox_resolved = inbox.resolve()
    if os.path.commonpath([
        str(target_dir),
        str(inbox_resolved),
    ]) != str(inbox_resolved):
        raise ValueError(f"target escapes inbox: {target}")
    return target_dir / filename


def append_audit(log_path: Path, record: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def apply_action(
    inbox: Path,
    file_path: Path,
    action: dict[str, Any],
    dry_run: bool,
) -> tuple[str, str | None, str]:
    action_type = str(action.get("type") or "none").lower()
    if action_type == "none":
        return "none", None, "SKIP"

    if action_type == "move":
        target = str(action.get("target") or "").strip()
        if not target:
            return "move", None, "FAIL: missing target"
        destination = safe_target_path(inbox, target, file_path.name)
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(destination))
        return "move", str(destination), "OK"

    if action_type == "rename":
        new_name = str(action.get("new_name") or "").strip()
        if not new_name:
            return "rename", None, "FAIL: missing new_name"
        destination = safe_target_path(inbox, ".", new_name)
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            file_path.rename(destination)
        return "rename", str(destination), "OK"

    if action_type == "tag":
        tag_value = str(action.get("tag") or "").strip()
        if not tag_value:
            return "tag", None, "FAIL: missing tag"
        return "tag", tag_value, "OK"

    return action_type, None, f"FAIL: unsupported action {action_type}"


def iter_files(inbox: Path) -> list[Path]:
    return [
        path
        for path in inbox.iterdir()
        if path.is_file()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox", required=True)
    parser.add_argument(
        "--rules",
        default="config/file_secretary_rules.yaml",
    )
    parser.add_argument(
        "--audit-log",
        default="logs/file_secretary_audit.jsonl",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    inbox = Path(args.inbox).resolve()
    if not inbox.exists() or not inbox.is_dir():
        print(f"inbox not found: {inbox}", file=sys.stderr)
        return 1

    try:
        rules, defaults = load_rules(Path(args.rules))
    except (OSError, ValueError, yaml.YAMLError) as exception:
        print(f"failed to load rules: {exception}", file=sys.stderr)
        return 1

    default_action = defaults.get("action", "none")
    audit_path = Path(args.audit_log)

    summary = {
        "processed": 0,
        "errors": 0,
        "skipped": 0,
        "dry_run": args.dry_run,
    }

    files = iter_files(inbox)
    for file_path in files:
        matched = pick_rule(rules, file_path)
        if matched is None:
            matched = Rule(
                name="default",
                match={},
                action={"type": default_action},
            )

        action_name = str(matched.action.get("type") or "none")
        target: str | None = None
        result = "SKIP"

        try:
            action_name, target, result = apply_action(
                inbox,
                file_path,
                matched.action,
                args.dry_run,
            )
        except (OSError, ValueError) as exception:
            result = f"FAIL: {exception}"

        timestamp = (
            dt.datetime.now(dt.UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        record = {
            "timestamp": timestamp,
            "rule": matched.name,
            "file": file_path.name,
            "action": action_name,
            "target": target,
            "result": result,
            "dry_run": args.dry_run,
        }
        append_audit(audit_path, record)

        if result == "OK":
            summary["processed"] += 1
        elif result.startswith("FAIL"):
            summary["errors"] += 1
        else:
            summary["skipped"] += 1

        print(json.dumps(record, ensure_ascii=False))

    print(json.dumps({"summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
