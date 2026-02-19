# GitHub Workflow Runbook

## Purpose

This runbook defines the recommended manual execution order and triage flow for GitHub Actions in this repository.

## Manual dispatch priority

Use this order when validating production readiness after major changes:

1. `Sync Repository Labels` (`sync-labels.yml`)
2. `Actionlint` (`actionlint.yml`)
3. `Workflow Health Report` (`workflow-health-report.yml`)
4. `Dependency Review` (`dependency-review.yml`) via PR check
5. `CodeQL` (`codeql.yml`)
6. `OpenSSF Scorecard` (`scorecard.yml`)
7. `CI/CD Pipeline` (`ci.yml`)
8. `Tests` (`tests.yml`)
9. `Release Drafter` (`release-drafter.yml`)

## PR validation checklist

- PR labels are assigned automatically (`pr-auto-label.yml`)
- Size label is assigned (`pr-size-label.yml`)
- Reviewer is requested (`auto-assign-reviewer.yml`)
- PR body sections are complete (`pr-description-check.yml`)

## Incident triage

### If critical pipelines fail

Critical pipelines:

- `ci.yml`
- `tests.yml`
- `codeql.yml`
- `dependency-review.yml`

Actions:

1. Check the first failed job and failing step.
2. Fix reproducible issues in branch and re-run failed jobs.
3. If failure is external/transient, re-run once.
4. If still failing due to upstream outage, document in PR and proceed with risk note.
5. Re-run `workflow-health-report.yml` to confirm overall status recovery.

### If non-critical automation fails

Non-critical pipelines:

- `release-drafter.yml`
- `stale.yml`
- `scorecard.yml`
- `actionlint.yml` (when only summary/reporting fails)

Actions:

1. Confirm no impact on build/test/security gates.
2. Re-run workflow once.
3. Open maintenance issue if recurring > 3 times.

## Recovery plan (minimum safe state)

If automation becomes unstable, maintain this minimum set enabled:

- `ci.yml`
- `tests.yml`
- `codeql.yml`
- `dependency-review.yml`

Then restore in this order:

1. `actionlint.yml`
2. `sync-labels.yml`
3. `pr-auto-label.yml`
4. `pr-size-label.yml`
5. `release-drafter.yml`
6. `scorecard.yml`
7. `stale.yml`
