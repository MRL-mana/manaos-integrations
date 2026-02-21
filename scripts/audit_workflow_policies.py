from pathlib import Path
import sys
import importlib

yaml = importlib.import_module('yaml')


WORKFLOW_DIR = Path('.github/workflows')
REPORT_PATH = Path('artifacts/workflow-policy-audit.md')


def load_workflow(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def has_paths(trigger_value):
    return isinstance(trigger_value, dict) and bool(trigger_value.get('paths'))


def audit_file(path: Path):
    doc = load_workflow(path)
    issues = []

    concurrency = doc.get('concurrency')
    if not concurrency:
        issues.append('`concurrency` が未定義です')

    triggers = doc.get('on', doc.get(True))
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
