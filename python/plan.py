"""Payment reminder rules engine. Run from python/ with ``python plan.py ...``."""

import argparse
import json
import math
import re
import sys
from datetime import date

STEPS = ("friendly", "firm", "final")
THRESHOLDS = {"friendly": 3, "firm": 10, "final": 24}


def is_real_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def make_message(invoice, step, days):
    name = invoice.get("customer") or "Customer"
    amount = f'{invoice["currency"]} {invoice["amount"]:,.2f}'
    if step == "friendly":
        return (f"Hello {name}, this is a friendly reminder that invoice {invoice['id']} for {amount}, "
                f"due on {invoice['due_date']}, is {days} days overdue. Please arrange payment when convenient. Thank you.")
    if step == "firm":
        return (f"Dear {name}, invoice {invoice['id']} for {amount}, due on {invoice['due_date']}, is {days} days overdue. "
                "Please arrange payment as soon as possible. Regards.")
    return (f"Dear {name}, our records show invoice {invoice['id']} for {amount}, due on {invoice['due_date']}, "
            f"is {days} days overdue. Please arrange payment promptly. Regards.")


def build_plan(invoices, sent, today):
    """Return today's plan, validating rows in the required precedence order."""
    if not is_real_date(today):
        raise ValueError(f"Invalid --today date: {today}. Expected a real date in YYYY-MM-DD format.")

    rows = [row for row in invoices if isinstance(row, dict)]
    id_counts = {}
    for row in rows:
        if isinstance(row.get("id"), str):
            id_counts[row["id"]] = id_counts.get(row["id"], 0) + 1

    sent_steps = {}
    for item in sent:
        if (isinstance(item, dict) and isinstance(item.get("invoice_id"), str)
                and item.get("step") in STEPS):
            sent_steps.setdefault(item["invoice_id"], set()).add(item["step"])

    actions, skipped = [], []
    skipped_ids = set()
    for row in rows:
        invoice_id = row.get("id")
        # The input contract specifies that each invoice has a text id.
        if not isinstance(invoice_id, str):
            continue
        reason = None
        amount = row.get("amount")
        if id_counts.get(invoice_id, 0) > 1:
            reason = "duplicate_id"
        elif isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount <= 0:
            reason = "invalid_amount"
        elif row.get("due_date") is None or row.get("due_date") == "":
            reason = "missing_due_date"
        elif not is_real_date(row.get("due_date")):
            reason = "invalid_due_date"
        elif row.get("paid_date") is not None and (
            not is_real_date(row.get("paid_date")) or row["paid_date"] > today
        ):
            reason = "invalid_paid_date"

        if reason:
            if invoice_id not in skipped_ids:
                skipped.append({"invoice_id": invoice_id, "reason": reason})
                skipped_ids.add(invoice_id)
            continue

        if row.get("paid_date") is not None:
            continue
        due = date.fromisoformat(row["due_date"])
        days = (date.fromisoformat(today) - due).days
        if days < THRESHOLDS["friendly"]:
            continue
        step = "final" if days >= THRESHOLDS["final"] else "firm" if days >= THRESHOLDS["firm"] else "friendly"
        step_index = STEPS.index(step)
        already_sent = sent_steps.get(invoice_id, set())
        if any(candidate in already_sent for candidate in STEPS[step_index:]):
            continue

        actions.append({
            "invoice_id": invoice_id,
            "step": step,
            "needs_approval": step != "friendly",
            "days_overdue": days,
            "message": make_message(row, step, days),
        })

    actions.sort(key=lambda item: item["invoice_id"])
    skipped.sort(key=lambda item: item["invoice_id"])
    return {"today": today, "actions": actions, "skipped": skipped}


def read_json(path):
    with open(path, encoding="utf-8") as source:
        return json.load(source)


def main():
    parser = argparse.ArgumentParser(description="Plan today's payment reminders.")
    parser.add_argument("--invoices", required=True, help="path to invoices.json")
    parser.add_argument("--sent", required=True, help="path to sent.json")
    parser.add_argument("--today", required=True, help="date as YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="path to write the plan JSON")
    args = parser.parse_args()
    try:
        invoices = read_json(args.invoices)
        sent = read_json(args.sent)
        if not isinstance(invoices, list) or not isinstance(sent, list):
            raise ValueError("Input files must each contain a JSON array.")
        result = build_plan(invoices, sent, args.today)
        with open(args.out, "w", encoding="utf-8") as output:
            json.dump(result, output, indent=2, ensure_ascii=False)
            output.write("\n")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not create plan: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
