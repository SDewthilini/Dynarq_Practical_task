// Payment reminder rules engine. Run from typescript/ with `npm run plan -- ...`.
import { readFileSync, writeFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

export type Step = "friendly" | "firm" | "final";
export interface Invoice {
  id: string; customer?: string; email?: string; amount: number; currency: string;
  due_date: string; paid_date?: string | null;
}
export interface Action {
  invoice_id: string; step: Step; needs_approval: boolean; days_overdue: number; message: string;
}
export interface Skipped { invoice_id: string; reason: string }
export interface Plan { today: string; actions: Action[]; skipped: Skipped[] }

const steps: Step[] = ["friendly", "firm", "final"];
const thresholds: Record<Step, number> = { friendly: 3, firm: 10, final: 24 };

export function isRealDate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

function dayNumber(date: string): number {
  const [year, month, day] = date.split("-").map(Number);
  return Date.UTC(year, month - 1, day) / 86_400_000;
}

function money(currency: string, amount: number): string {
  return `${currency} ${amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function message(invoice: Invoice, step: Step, days: number): string {
  const name = invoice.customer || "Customer";
  const amount = money(invoice.currency, invoice.amount);
  if (step === "friendly") {
    return `Hello ${name}, this is a friendly reminder that invoice ${invoice.id} for ${amount}, due on ${invoice.due_date}, is ${days} days overdue. Please arrange payment when convenient. Thank you.`;
  }
  if (step === "firm") {
    return `Dear ${name}, invoice ${invoice.id} for ${amount}, due on ${invoice.due_date}, is ${days} days overdue. Please arrange payment as soon as possible. Regards.`;
  }
  return `Dear ${name}, our records show invoice ${invoice.id} for ${amount}, due on ${invoice.due_date}, is ${days} days overdue. Please arrange payment promptly. Regards.`;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validInvoiceId(value: unknown): value is string { return typeof value === "string"; }

/** Return a deterministic plan. Bad rows without a text id cannot be represented in skipped output. */
export function buildPlan(invoices: unknown[], sent: unknown[], today: string): Plan {
  if (!isRealDate(today)) throw new Error(`Invalid --today date: ${today}. Expected a real date in YYYY-MM-DD format.`);
  const rows = invoices.filter(isObject);
  const counts = new Map<string, number>();
  for (const row of rows) if (validInvoiceId(row.id)) counts.set(row.id, (counts.get(row.id) || 0) + 1);
  const sentSteps = new Map<string, Set<Step>>();
  for (const entry of sent) {
    if (!isObject(entry) || !validInvoiceId(entry.invoice_id) || !steps.includes(entry.step as Step)) continue;
    const set = sentSteps.get(entry.invoice_id) || new Set<Step>();
    set.add(entry.step as Step);
    sentSteps.set(entry.invoice_id, set);
  }

  const actions: Action[] = [];
  const skipped: Skipped[] = [];
  const skippedIds = new Set<string>();
  for (const row of rows) {
    if (!validInvoiceId(row.id)) continue;
    const id = row.id;
    let reason: string | undefined;
    if ((counts.get(id) || 0) > 1) reason = "duplicate_id";
    else if (typeof row.amount !== "number" || !Number.isFinite(row.amount) || row.amount <= 0) reason = "invalid_amount";
    else if (row.due_date === undefined || row.due_date === null || row.due_date === "") reason = "missing_due_date";
    else if (!isRealDate(row.due_date)) reason = "invalid_due_date";
    else if (row.paid_date !== undefined && row.paid_date !== null && (!isRealDate(row.paid_date) || row.paid_date > today)) reason = "invalid_paid_date";
    if (reason) {
      if (!skippedIds.has(id)) { skipped.push({ invoice_id: id, reason }); skippedIds.add(id); }
      continue;
    }
    if (typeof row.paid_date === "string") continue;
    const due = row.due_date as string;
    const days = dayNumber(today) - dayNumber(due);
    if (days < thresholds.friendly) continue;
    const step: Step = days >= thresholds.final ? "final" : days >= thresholds.firm ? "firm" : "friendly";
    const prior = sentSteps.get(id) || new Set<Step>();
    const stepIndex = steps.indexOf(step);
    if (steps.slice(stepIndex).some((candidate) => prior.has(candidate))) continue;
    const invoice: Invoice = {
      id, customer: typeof row.customer === "string" ? row.customer : undefined,
      email: typeof row.email === "string" ? row.email : undefined,
      amount: row.amount as number, currency: typeof row.currency === "string" ? row.currency : "",
      due_date: due,
    };
    actions.push({ invoice_id: id, step, needs_approval: step !== "friendly", days_overdue: days, message: message(invoice, step, days) });
  }
  const byId = (a: { invoice_id: string }, b: { invoice_id: string }) => a.invoice_id < b.invoice_id ? -1 : a.invoice_id > b.invoice_id ? 1 : 0;
  actions.sort(byId); skipped.sort(byId);
  return { today, actions, skipped };
}

export function readJson(path: string): unknown {
  const parsed: unknown = JSON.parse(readFileSync(path, "utf-8"));
  return parsed;
}

function main(): void {
  try {
    const { values } = parseArgs({ options: {
      invoices: { type: "string" }, sent: { type: "string" }, today: { type: "string" }, out: { type: "string" },
    } });
    if (!values.invoices || !values.sent || !values.today || !values.out) {
      console.error("Usage: npm run plan -- --invoices FILE --sent FILE --today YYYY-MM-DD --out FILE");
      process.exitCode = 2; return;
    }
    const invoices = readJson(values.invoices);
    const sent = readJson(values.sent);
    if (!Array.isArray(invoices) || !Array.isArray(sent)) throw new Error("Input files must each contain a JSON array.");
    const plan = buildPlan(invoices, sent, values.today);
    writeFileSync(values.out, JSON.stringify(plan, null, 2) + "\n", "utf-8");
  } catch (error) {
    console.error(`Could not create plan: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) main();
