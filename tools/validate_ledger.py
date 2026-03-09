#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate services_ledger.yaml against:
- OpenAPI endpoints (optional, if Unified API is reachable)
- README references (optional lightweight checks)

Exit code:
0 = OK
1 = Validation failed
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    print("Missing dependency: pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import requests
except ImportError:
    requests = None


@dataclass
class ServiceRef:
    name: str
    group: str
    port: int | None
    url: str | None
    enabled: bool
    depends_on: List[str]
    tier: int = 0
    start_cmd: str | None = None


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def parse_services(ledger: Dict[str, Any]) -> Dict[str, ServiceRef]:
    services: Dict[str, ServiceRef] = {}

    def add_group(group_name: str) -> None:
        group = ledger.get(group_name, {}) or {}
        for service_name, config in group.items():
            if not isinstance(config, dict):
                raise ValueError(f"{group_name}.{service_name} must be a dict")

            port = config.get("port")
            url = config.get("url")
            enabled = bool(config.get("enabled", False))
            depends_on = config.get("depends_on") or []

            if not isinstance(depends_on, list):
                raise ValueError(f"{group_name}.{service_name}.depends_on must be a list")
            if port is not None and not isinstance(port, int):
                raise ValueError(f"{group_name}.{service_name}.port must be int")
            if url is not None and not isinstance(url, str):
                raise ValueError(f"{group_name}.{service_name}.url must be str")

            tier_raw = config.get("tier", 2 if group_name == "optional" else 1)
            if not isinstance(tier_raw, int):
                raise ValueError(f"{group_name}.{service_name}.tier must be int")

            services[service_name] = ServiceRef(
                name=service_name,
                group=group_name,
                port=port,
                url=url,
                enabled=enabled,
                depends_on=[str(dep) for dep in depends_on],
                tier=tier_raw,
                start_cmd=config.get("start_cmd"),
            )

    add_group("core")
    add_group("optional")
    return services


def validate_basic(services: Dict[str, ServiceRef]) -> List[str]:
    errors: List[str] = []

    used_ports: Dict[int, str] = {}
    for service in services.values():
        if service.port is None:
            continue
        # skip port-conflict check for virtual services (start_cmd=null means
        # they are sub-routes co-hosted inside another service's process)
        if service.start_cmd is None:
            continue
        if service.port in used_ports:
            errors.append(
                f"Port conflict: {service.port} used by "
                f"{used_ports[service.port]} and {service.name}"
            )
        else:
            used_ports[service.port] = service.name

    for service in services.values():
        for dependency in service.depends_on:
            if dependency not in services:
                errors.append(
                    f"Unknown depends_on: {service.name} depends on "
                    f"'{dependency}' which is not defined in ledger"
                )

    required_core_services = ["memory", "learning", "llm_routing", "unified_api"]
    for service_name in required_core_services:
        if service_name not in services:
            errors.append(f"Missing core service '{service_name}' in ledger")
        elif services[service_name].group != "core":
            errors.append(
                f"Service '{service_name}' must be under core, "
                f"but found under {services[service_name].group}"
            )

    for service in services.values():
        if service.enabled and service.port is None and not service.url:
            errors.append(
                f"Enabled service '{service.name}' has neither port nor url "
                f"(set enabled: false or provide port/url)"
            )

    return errors


def validate_tier_integrity(services: Dict[str, ServiceRef]) -> List[str]:
    """tier 整合性チェック。

    ルール:
    1. core サービス (tier 0/1) が optional サービス (tier 2) に依存してはいけない
    2. 依存先の tier が依存元の tier 以上は許容しない
       (例: tier-0 サービスが tier-1/2 に依存するのは不変)
    """
    errors: List[str] = []
    for service in services.values():
        for dep_name in service.depends_on:
            dep = services.get(dep_name)
            if dep is None:
                continue  # already caught by validate_basic
            # core should not depend on optional
            if service.group == "core" and dep.group == "optional":
                errors.append(
                    f"Tier violation: core service '{service.name}' depends on "
                    f"optional service '{dep_name}' (optional services are not guaranteed)"
                )
            # depender tier must be >= dependency tier (low number = higher priority)
            if service.tier < dep.tier:
                errors.append(
                    f"Tier violation: '{service.name}' (tier {service.tier}) depends on "
                    f"'{dep_name}' (tier {dep.tier}) - higher-priority service "
                    f"should not depend on lower-priority service"
                )
    return errors


def fetch_openapi(
    openapi_url: str,
    timeout: float = 3.0,
    api_key: str | None = None,
) -> Dict[str, Any] | None:
    if requests is None:
        return None
    try:
        headers = {"X-API-Key": api_key} if api_key else None
        response = requests.get(openapi_url, timeout=timeout, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as exception:
        eprint(f"[WARN] Could not fetch OpenAPI from {openapi_url}: {exception}")
        return None


def validate_openapi(
    services: Dict[str, ServiceRef],
    openapi: Dict[str, Any],
    require_paths: List[str],
) -> List[str]:
    errors: List[str] = []
    paths = openapi.get("paths", {}) or {}
    if not isinstance(paths, dict):
        return ["OpenAPI 'paths' is not a dict"]

    for required_path in require_paths:
        if required_path not in paths:
            errors.append(f"OpenAPI missing required path: {required_path}")

    unified_api = services.get("unified_api")
    if unified_api and not unified_api.enabled:
        errors.append("unified_api is not enabled in ledger but OpenAPI validation was requested")

    return errors


def validate_readme(readme_path: str) -> List[str]:
    errors: List[str] = []
    if not os.path.exists(readme_path):
        return errors

    text = open(readme_path, "r", encoding="utf-8").read()

    if "unified_api_server.py" in text:
        errors.append(
            "README still mentions 'unified_api_server.py' "
            "(should reference current structure)"
        )

    if re.search(r"services_ledger\.ya?ml", text) is None:
        errors.append("README does not mention services_ledger.yaml (SSOT reference missing)")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", default="config/services_ledger.yaml")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--check-openapi", action="store_true")
    parser.add_argument("--openapi-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--require-path", action="append", default=[])
    args = parser.parse_args()

    try:
        ledger = load_yaml(args.ledger)
        services = parse_services(ledger)
    except Exception as exception:
        eprint(f"❌ Failed to load or parse ledger: {exception}")
        return 1

    errors: List[str] = []
    errors += validate_basic(services)
    errors += validate_tier_integrity(services)
    errors += validate_readme(args.readme)

    if args.check_openapi:
        unified_api = services.get("unified_api")
        openapi_url = args.openapi_url
        if openapi_url is None and unified_api is not None:
            if unified_api.url:
                openapi_url = unified_api.url.rstrip("/") + "/openapi.json"
            elif unified_api.port:
                openapi_url = f"http://127.0.0.1:{unified_api.port}/openapi.json"

        if not openapi_url:
            errors.append("OpenAPI check requested but openapi-url could not be determined")
        else:
            openapi = fetch_openapi(openapi_url, api_key=args.api_key)
            if openapi is None:
                errors.append(f"Failed to fetch OpenAPI from {openapi_url}")
            else:
                require_paths = args.require_path or ["/health", "/openapi.json"]
                errors += validate_openapi(services, openapi, require_paths=require_paths)

    if errors:
        eprint("❌ Ledger validation failed:")
        for error in errors:
            eprint(" -", error)
        return 1

    print("✅ Ledger validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
