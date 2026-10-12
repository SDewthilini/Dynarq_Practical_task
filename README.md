# Payment reminder assistant

Built with TypeScript and Node.js; Python is not required to run this version.

## Setup
- Requires Node.js 20 or newer.
- From `typescript/`, run `npm install` once.
- Run the tests with `npm test` and check types with `npm run typecheck`.

## Plan command
- From `typescript/`, run `npm run plan -- --invoices ../data/invoices.json --sent ../data/sent.json --today 2026-10-12 --out ../actions.json`.
- The plan validates invoice dates and amounts, skips duplicate IDs, and chooses at most the highest due reminder step.
- Firm and final reminders need approval; an already sent step or a higher step suppresses a new action.
- Reminder messages use a local template and include only invoice facts required by the task.

## Owner page
- From `typescript/`, run `npm run app`, then open `http://localhost:8000/`.
- Set `PORT`, `DATA_DIR` (defaults to `../data`) or `TODAY` to configure the page.
- Approvals and rejections are held in memory for the current app session; no emails are sent.
- The page shows skipped invoices with plain language explanations and works on narrow screens and with a keyboard.

## Decisions and next steps
- Research notes cite only the supplied files; the current ECB rate is not present in those sources.
- With more time, I would persist approval decisions and add page-level tests for data errors and keyboard use.
