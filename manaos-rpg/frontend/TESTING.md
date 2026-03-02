# Frontend Testing

## Quick commands

- Local smoke test: `npm run test`
- CI-stable smoke test: `npm run test:ci`
- Full check (lint + test + build): `npm run check`

## Current smoke coverage

`src/test/app.smoke.test.jsx` covers these tabs/flows:

1. Status: header + basic meta
2. Bestiary: open/close detail modal
3. Party: service rows + alive summary
4. Map: topology + device cards
5. Skills: cheatsheet + unified status
6. Systems: overview cards
7. Quests: quest rows
8. Logs: event list rendering
9. Items: recent artifact list
10. RL: disabled-state message

## Notes

- Tests use mocked API responses in `beforeEach` to keep runs deterministic.
- `test:ci` uses `--maxWorkers=1` for stable CI behavior.
