import assert from "node:assert/strict";
import { test } from "node:test";
import { buildPlan, isRealDate } from "../src/plan";

const invoice = (id: string, due_date: string, extra: Record<string, unknown> = {}) => ({
  id, customer: "Example Ltd", amount: 1250, currency: "EUR", due_date, paid_date: null, ...extra,
});

test("empty input gives an empty plan", () => {
  assert.deepEqual(buildPlan([], [], "2026-10-12"), { today: "2026-10-12", actions: [], skipped: [] });
});

test("selects the highest reached step, with valid amounts and message facts", () => {
  const plan = buildPlan([
    invoice("INV-3", "2026-10-02"), invoice("INV-1", "2026-10-09"), invoice("INV-2", "2026-09-18"),
  ], [], "2026-10-12");
  assert.deepEqual(plan.actions.map(({ invoice_id, step, days_overdue, needs_approval }) => ({ invoice_id, step, days_overdue, needs_approval })), [
    { invoice_id: "INV-1", step: "friendly", days_overdue: 3, needs_approval: false },
    { invoice_id: "INV-2", step: "final", days_overdue: 24, needs_approval: true },
    { invoice_id: "INV-3", step: "firm", days_overdue: 10, needs_approval: true },
  ]);
  assert.match(plan.actions[0].message, /Example Ltd.*INV-1.*EUR 1,250\.00.*2026-10-09.*3 days overdue/);
  assert.equal(plan.actions[1].message, "Dear Example Ltd, our records show invoice INV-2 for EUR 1,250.00, due on 2026-09-18, is 24 days overdue. Please arrange payment promptly. Regards.");
});

test("already sent this or a higher step suppresses the action", () => {
  const plan = buildPlan([invoice("a", "2026-09-30"), invoice("b", "2026-09-30"), invoice("c", "2026-09-30")], [
    { invoice_id: "a", step: "firm" }, { invoice_id: "b", step: "final" }, { invoice_id: "missing", step: "friendly" }, { invoice_id: "c", step: "unknown" },
  ], "2026-10-12");
  assert.deepEqual(plan.actions.map((a) => a.invoice_id), ["c"]);
  assert.equal(plan.actions[0].step, "firm");
});

test("validation follows the specified precedence and reports duplicate once", () => {
  const plan = buildPlan([
    invoice("dup", "", { amount: 0 }), invoice("dup", "2026-01-01"), invoice("bad-amount", "", { amount: true }),
    invoice("missing", "", { due_date: null }), invoice("bad-date", "2026-02-30"), invoice("bad-paid", "2026-01-01", { paid_date: "" }),
    invoice("future-paid", "2026-01-01", { paid_date: "2026-10-13" }),
  ], [], "2026-10-12");
  assert.deepEqual(plan.skipped, [
    { invoice_id: "bad-amount", reason: "invalid_amount" }, { invoice_id: "bad-date", reason: "invalid_due_date" },
    { invoice_id: "bad-paid", reason: "invalid_paid_date" }, { invoice_id: "dup", reason: "duplicate_id" },
    { invoice_id: "future-paid", reason: "invalid_paid_date" }, { invoice_id: "missing", reason: "missing_due_date" },
  ]);
});

test("paid invoices, not-yet-due invoices, and due-today invoices have no action", () => {
  assert.deepEqual(buildPlan([
    invoice("paid", "2026-09-01", { paid_date: "2026-10-12" }), invoice("future", "2026-10-20"), invoice("today", "2026-10-12"),
  ], [], "2026-10-12").actions, []);
});

test("date validation rejects impossible dates and accepts leap day", () => {
  assert.equal(isRealDate("2024-02-29"), true);
  assert.equal(isRealDate("2026-02-29"), false);
  assert.equal(isRealDate("30/09/2026"), false);
  assert.throws(() => buildPlan([], [], "2026-02-30"), /Invalid --today date/);
});

test("sorts ids by plain text rather than numeric value", () => {
  const plan = buildPlan([invoice("INV-99", "2026-10-01"), invoice("INV-100", "2026-10-01")], [], "2026-10-12");
  assert.deepEqual(plan.actions.map((a) => a.invoice_id), ["INV-100", "INV-99"]);
});
