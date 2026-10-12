import unittest

from plan import build_plan, is_real_date


def invoice(invoice_id, due_date, **extra):
    row = {
        "id": invoice_id, "customer": "Example Ltd", "amount": 1250,
        "currency": "EUR", "due_date": due_date, "paid_date": None,
    }
    row.update(extra)
    return row


class PlanTests(unittest.TestCase):
    def test_empty_input_gives_empty_plan(self):
        self.assertEqual(build_plan([], [], "2026-10-12"), {
            "today": "2026-10-12", "actions": [], "skipped": [],
        })

    def test_selects_highest_step_and_messages_contain_invoice_facts(self):
        plan = build_plan([
            invoice("INV-3", "2026-10-02"), invoice("INV-1", "2026-10-09"),
            invoice("INV-2", "2026-09-18"),
        ], [], "2026-10-12")
        self.assertEqual([
            (a["invoice_id"], a["step"], a["needs_approval"], a["days_overdue"])
            for a in plan["actions"]
        ], [
            ("INV-1", "friendly", False, 3), ("INV-2", "final", True, 24),
            ("INV-3", "firm", True, 10),
        ])
        self.assertEqual(plan["actions"][1]["message"],
            "Dear Example Ltd, our records show invoice INV-2 for EUR 1,250.00, "
            "due on 2026-09-18, is 24 days overdue. Please arrange payment promptly. Regards.")

    def test_sent_current_or_higher_step_suppresses_action(self):
        rows = [invoice(name, "2026-09-30") for name in ("a", "b", "c")]
        sent = [
            {"invoice_id": "a", "step": "firm"}, {"invoice_id": "b", "step": "final"},
            {"invoice_id": "unknown", "step": "friendly"}, {"invoice_id": "c", "step": "other"},
        ]
        plan = build_plan(rows, sent, "2026-10-12")
        self.assertEqual([a["invoice_id"] for a in plan["actions"]], ["c"])
        self.assertEqual(plan["actions"][0]["step"], "firm")

    def test_validation_precedence_and_duplicate_once(self):
        plan = build_plan([
            invoice("dup", "", amount=0), invoice("dup", "2026-01-01"),
            invoice("bad-amount", "", amount=True), invoice("missing", None),
            invoice("bad-date", "2026-02-30"), invoice("bad-paid", "2026-01-01", paid_date=""),
            invoice("future-paid", "2026-01-01", paid_date="2026-10-13"),
        ], [], "2026-10-12")
        self.assertEqual(plan["skipped"], [
            {"invoice_id": "bad-amount", "reason": "invalid_amount"},
            {"invoice_id": "bad-date", "reason": "invalid_due_date"},
            {"invoice_id": "bad-paid", "reason": "invalid_paid_date"},
            {"invoice_id": "dup", "reason": "duplicate_id"},
            {"invoice_id": "future-paid", "reason": "invalid_paid_date"},
            {"invoice_id": "missing", "reason": "missing_due_date"},
        ])

    def test_paid_and_not_yet_due_invoices_have_no_action(self):
        plan = build_plan([
            invoice("paid", "2026-09-01", paid_date="2026-10-12"),
            invoice("future", "2026-10-20"), invoice("today", "2026-10-12"),
        ], [], "2026-10-12")
        self.assertEqual(plan["actions"], [])

    def test_real_date_validation_and_invalid_today(self):
        self.assertTrue(is_real_date("2024-02-29"))
        self.assertFalse(is_real_date("2026-02-29"))
        self.assertFalse(is_real_date("30/09/2026"))
        with self.assertRaisesRegex(ValueError, "Invalid --today date"):
            build_plan([], [], "2026-02-30")

    def test_ids_sort_in_plain_text_order(self):
        result = build_plan([invoice("INV-99", "2026-10-01"), invoice("INV-100", "2026-10-01")], [], "2026-10-12")
        self.assertEqual([a["invoice_id"] for a in result["actions"]], ["INV-100", "INV-99"])


if __name__ == "__main__":
    unittest.main()
