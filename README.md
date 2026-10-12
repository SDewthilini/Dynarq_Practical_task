# Payment reminder assistant

Built with Python 3.11 or newer and the standard library only.

## Setup and tests
- In a terminal, enter the `python/` folder.
- Run the test suite with `python -m unittest`.

## Plan command
- From `python/`, run `python plan.py --invoices ../data/invoices.json --sent ../data/sent.json --today 2026-10-12 --out ../actions.json`.
- The rules engine validates invoice data, skips duplicate IDs, and chooses at most the highest due reminder step.
- Firm and final reminders need approval; an already sent step or a higher step suppresses a new action.
- Reminder messages use a local template and contain the invoice facts required by the task.

## Owner page
- From `python/`, run `python app.py`, then open `http://localhost:8000/`.
- Set `PORT`, `DATA_DIR` (defaults to `../data`) or `TODAY` to configure the page.
- Approvals and rejections are held in memory for the current app session; no emails are sent.
- The page explains skipped invoices and supports narrow screens and keyboard use.

## Decisions and next steps
- Research notes cite only the supplied sources; they do not state the current ECB rate.
- With more time, I would persist approval decisions and add page-level tests for errors and keyboard use.
