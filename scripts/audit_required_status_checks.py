from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, cast
import importlib

import requests


yaml = importlib.import_module("yaml")
YAMLError = cast(type[BaseException], getattr(yaml, "YAMLError", ValueError))

WORKFLOW_DIR = Path('.github/workflows')
REPORT_PATH = Path('artifacts/required-checks-audit.md')


def load_yaml(path: Path) -> dict[str, Any]:
    for encoding in ('utf-8', 'utf-8-sig'):
        try:
            with path.open('r', encoding=encoding) as f:
                data = yaml.safe_load(f) or {}
                if isinstance(data, dict):
                    return cast(dict[str, Any], data)
                return {}
        except (OSError, UnicodeError, YAMLError, ValueError, TypeError):
            continue
    return {}


def normalize_triggers(doc: dict[str, Any]) -> Any:
    triggers = doc.get('on')
    if not triggers and True in doc:
        triggers = doc.get(True)
    if isinstance(triggers, str):
        return {triggers: {}}
    if isinstance(triggers, list):
        return {item: {} for item in triggers}
    return triggers


def has_pull_request_trigger(doc: dict[str, Any]) -> bool:
    triggers = normalize_triggers(doc)
    return isinstance(triggers, dict) and 'pull_request' in triggers


def collect_available_contexts() -> tuple[set[str], list[str]]:
    contexts: set[str] = set()
    warnings: list[str] = []

    if not WORKFLOW_DIR.exists():
        warnings.append('.github/workflows directory is missing')
        return contexts, warnings

    for wf in sorted(WORKFLOW_DIR.glob('*.yml')):
        doc = load_yaml(wf)
        if not doc:
            warnings.append(f'skipped unreadable workflow: {wf.as_posix()}')
            continue
        if not has_pull_request_trigger(doc):
            continue

        workflow_name = doc.get('name')
        if not isinstance(workflow_name, str) or not workflow_name.strip():
            warnings.append(f'workflow name missing: {wf.as_posix()}')
            continue

        jobs = doc.get('jobs')
        if not isinstance(jobs, dict):
            warnings.append(f'jobs section missing: {wf.as_posix()}')
            continue

        for job_id, job_def in jobs.items():
            job_name = job_id
            if isinstance(job_def, dict) and isinstance(job_def.get('name'), str):
                job_name = cast(str, job_def['name'])
            contexts.add(job_name)
            contexts.add(f'{workflow_name} / {job_name}')

    return contexts, warnings


def fetch_required_contexts() -> tuple[list[str], str | None]:
    repo = os.getenv('GITHUB_REPOSITORY')
    token = os.getenv('GITHUB_TOKEN')
    api_url = os.getenv('GITHUB_API_URL', 'https://api.github.com')
    base_ref = os.getenv('GITHUB_BASE_REF') or os.getenv('GITHUB_REF_NAME') or 'master'

    if not repo:
        return [], 'GITHUB_REPOSITORY is not set'
    if not token:
        return [], 'GITHUB_TOKEN is not set'

    url = f"{api_url}/repos/{repo}/branches/{base_ref}/protection/required_status_checks"
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
    }

    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code >= 300:
        return [], f'failed to fetch required checks: HTTP {response.status_code} {response.text}'

    payload = response.json()
    contexts = payload.get('contexts')
    if not isinstance(contexts, list):
        return [], 'required checks response has no contexts list'

    return [str(c) for c in contexts], None


def write_report(lines: list[str]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    available_contexts, warnings = collect_available_contexts()
    required_contexts, error = fetch_required_contexts()

    lines = ['# Required Status Checks Audit', '']

    if error:
        lines.append(f'- Result: ⚠️ skipped ({error})')
        lines.append('- Note: This audit requires branch protection API access via GITHUB_TOKEN.')
        if warnings:
            lines.append('')
            lines.append('## Local warnings')
            for w in warnings:
                lines.append(f'- {w}')
        write_report(lines)
        print(REPORT_PATH.as_posix())
        return 0

    missing = sorted([ctx for ctx in required_contexts if ctx not in available_contexts])

    lines.append(f'- Required contexts: {len(required_contexts)}')
    lines.append(f'- Available contexts (derived): {len(available_contexts)}')
    lines.append(f'- Missing mappings: {len(missing)}')
    lines.append('')

    if missing:
        lines.append('## Missing required contexts in workflow definitions')
        for item in missing:
            lines.append(f'- {item}')
    else:
        lines.append('## Result')
        lines.append('- ✅ All required status contexts are represented in PR workflow job names')

    if warnings:
        lines.append('')
        lines.append('## Local warnings')
        for w in warnings:
            lines.append(f'- {w}')

    write_report(lines)
    print(REPORT_PATH.as_posix())

    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
