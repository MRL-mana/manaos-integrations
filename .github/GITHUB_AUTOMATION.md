# GitHub Automation Guide

## What is automated

- PR auto labels by changed files (`pr-auto-label.yml`)
- PR size labels + split warning (`pr-size-label.yml`)
- PR description quality check (`pr-description-check.yml`)
- Auto reviewer assignment (`auto-assign-reviewer.yml`)
- Label synchronization (`sync-labels.yml`)
- Stale issue/PR cleanup (`stale.yml`)
- Dependabot updates (`dependabot.yml`)
- Draft release notes (`release-drafter.yml`)
- Workflow lint (`actionlint.yml`)

## First-time setup

1. Run `Sync Repository Labels` workflow once from Actions tab.
2. Open a test PR and confirm:
   - labels are attached automatically,
   - reviewer is requested,
   - size label is attached,
   - `needs-info` is added/removed according to PR template sections.

## Troubleshooting

- If labels are missing, run `Sync Repository Labels` manually.
- If reviewer is not assigned, verify `.github/auto_assign.yml` usernames.
- If release draft is not updated, check `Release Drafter` workflow permissions.
