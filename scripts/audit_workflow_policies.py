from pathlib import Path
import sys
import importlib
from typing import Any, cast

yaml = importlib.import_module('yaml')
YAMLError = cast(type[BaseException], getattr(yaml, 'YAMLError', ValueError))


WORKFLOW_DIR = Path('.github/workflows')
REPORT_PATH = Path('artifacts/workflow-policy-audit.md')
ALLOW_MISSING_PR_PATHS = {
    'actionlint.yml',
    'dependency-review.yml',
    'lint.yml',
    'tests.yml',
    'validate-ledger.yml',
    'workflow-policy-audit.yml',
}


def load_workflow(path: Path):
    for encoding in ('utf-8', 'utf-8-sig'):
        try:
            with path.open('r', encoding=encoding) as f:
                try:
                    return yaml.safe_load(f) or {}
                except (YAMLError, ValueError, TypeError) as exc:
                    return {"__parse_error__": str(exc)}
        except (OSError, UnicodeError):
            continue

    try:
        raw = path.read_text(encoding='utf-8', errors='replace')
        try:
            return yaml.safe_load(raw) or {}
        except (YAMLError, ValueError, TypeError) as exc:
            return {"__parse_error__": str(exc)}
    except (OSError, UnicodeError) as exc:
        return {"__parse_error__": str(exc)}


def has_paths(trigger_value):
    return isinstance(trigger_value, dict) and bool(trigger_value.get('paths'))


def audit_file(path: Path):
    doc = load_workflow(path)
    issues = []

    if isinstance(doc, dict) and doc.get("__parse_error__"):
        issues.append(f"YAML parse failed: {doc['__parse_error__']}")
        return issues

    concurrency = doc.get('concurrency')
    if not concurrency:
        issues.append('`concurrency` が未定義です')

    doc_any = cast(Any, doc)
    triggers = doc_any.get('on')
    if not triggers and True in doc_any:
        triggers = doc_any.get(True)
    if not triggers:
        issues.append('`on` トリガーが未定義です')
        return issues

    if isinstance(triggers, str):
        triggers = {triggers: {}}

    if isinstance(triggers, list):
        triggers = {item: {} for item in triggers}

    if isinstance(triggers, dict):
        if 'push' in triggers and not has_paths(triggers.get('push')):
            issues.append('`on.push.paths` が未定義です')
        if (
            'pull_request' in triggers
            and path.name not in ALLOW_MISSING_PR_PATHS
            and not has_paths(triggers.get('pull_request'))
        ):
            issues.append('`on.pull_request.paths` が未定義です')

    return issues


def main():
    if not WORKFLOW_DIR.exists():
        print('.github/workflows が見つかりません')
        return 1

    files = sorted(WORKFLOW_DIR.glob('*.yml'))
    if not files:
        print('監査対象の workflow がありません')
        return 0

    violations = {}
    for wf in files:
        issues = audit_file(wf)
        if issues:
            violations[wf.as_posix()] = issues

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = ['# Workflow Policy Audit', '']
    lines.append(f'- Checked: {len(files)} workflows')
    lines.append(f'- Violations: {len(violations)}')
    lines.append('')

    if violations:
        lines.append('## Violations')
        for wf, issues in violations.items():
            lines.append(f'- {wf}')
            for issue in issues:
                lines.append(f'  - {issue}')
    else:
        lines.append('## Result')
        lines.append('- ✅ すべてのワークフローがポリシーに準拠しています')

    REPORT_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(REPORT_PATH.as_posix())

    return 1 if violations else 0


if __name__ == '__main__':
    sys.exit(main())
