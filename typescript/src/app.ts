// Owner's one-page dashboard. Run from typescript/ with `npm run app`.
import { createServer } from "node:http";
import { buildPlan, readJson, type Plan } from "./plan";

const PORT = Number(process.env.PORT || "8000");
const DATA_DIR = process.env.DATA_DIR || "../data";
const TODAY = process.env.TODAY || localToday();
const decisions = new Map<string, "approved" | "rejected">();

function localToday(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]!);
}
function page(plan: Plan, invoices: Array<Record<string, unknown>>): string {
  const actions = plan.actions.length ? plan.actions.map((action) => {
    const invoice = invoices.find((row) => row.id === action.invoice_id);
    const decision = decisions.get(action.invoice_id);
    const approval = action.needs_approval
      ? decision ? `<p class="decision" role="status">${decision === "approved" ? "Approved" : "Rejected"}</p>`
        : `<form method="post" action="/decision"><input type="hidden" name="invoice_id" value="${escapeHtml(action.invoice_id)}"><button name="decision" value="approved">Approve</button><button class="secondary" name="decision" value="rejected">Reject</button></form>`
      : '<p class="badge">No approval needed</p>';
    return `<article class="card"><div class="card-head"><div><p class="eyebrow">${escapeHtml(action.step)} reminder</p><h3>${escapeHtml(invoice?.customer || "Customer")}</h3></div><span class="badge">${action.days_overdue} days overdue</span></div><p><strong>Invoice:</strong> ${escapeHtml(action.invoice_id)} &nbsp; <strong>Amount:</strong> ${escapeHtml(invoice?.currency)} ${Number(invoice?.amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p><p class="message">${escapeHtml(action.message)}</p>${approval}</article>`;
  }).join("") : '<div class="empty"><h3>You are all caught up</h3><p>No reminders need action today.</p></div>';
  const reasonText: Record<string, string> = {
    duplicate_id: "This invoice ID appears more than once.", invalid_amount: "The amount is missing or is not a positive number.",
    missing_due_date: "The due date is missing.", invalid_due_date: "The due date is not a valid calendar date.",
    invalid_paid_date: "The paid date is invalid or is after today.",
  };
  const skipped = plan.skipped.length ? `<ul class="skipped">${plan.skipped.map((row) => `<li><strong>${escapeHtml(row.invoice_id)}:</strong> ${escapeHtml(reasonText[row.reason] || "This invoice has invalid data.")}</li>`).join("")}</ul>` : '<p class="muted">No invoices were skipped.</p>';
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Payment reminders</title><style>
    :root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;color:#172a31;background:#f4f7f6;font-synthesis:none}*{box-sizing:border-box}body{margin:0}header{background:#143b3b;color:#fff;padding:32px max(20px,calc((100vw - 960px)/2))}header p{margin:0;color:#cce0dc}main{max-width:960px;padding:28px 20px 60px;margin:auto}.summary{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 28px}.stat{background:#fff;border:1px solid #dce6e2;border-radius:12px;padding:14px 18px;min-width:130px}.stat strong{display:block;font-size:1.35rem}.stat span,.muted{color:#5b6d6b;font-size:.92rem}h1{margin:0 0 8px;font-size:clamp(1.7rem,5vw,2.4rem)}h2{margin:30px 0 14px;font-size:1.25rem}.card,.empty,.error{background:#fff;border:1px solid #dce6e2;border-radius:14px;padding:20px;margin:12px 0;box-shadow:0 3px 12px #143b3b0a}.card-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.card h3{margin:4px 0;font-size:1.1rem}.eyebrow{text-transform:uppercase;letter-spacing:.09em;font-weight:700;font-size:.72rem;color:#287164;margin:0}.badge{display:inline-block;border-radius:999px;background:#e8f3ef;color:#175b4c;padding:6px 10px;font-size:.83rem;font-weight:650}.card p{line-height:1.55}.message{border-left:3px solid #8db7aa;padding:8px 12px;background:#f7faf9}.decision{color:#175b4c;font-weight:700}form{display:flex;gap:10px;flex-wrap:wrap}button{font:inherit;font-weight:650;border:0;border-radius:8px;padding:10px 16px;background:#176b58;color:white;cursor:pointer}button.secondary{background:#fff;color:#344c4a;border:1px solid #9aadaa}button:hover{filter:brightness(.94)}button:focus-visible{outline:3px solid #e4a72c;outline-offset:3px}.empty{padding:26px}.empty h3{margin-top:0}.skipped{padding-left:22px}.skipped li{padding:7px 0}.error{border-color:#e5b5ab;background:#fff8f6;color:#772d22}footer{margin-top:32px;color:#5b6d6b;font-size:.88rem}@media(max-width:480px){header{padding:25px 20px}main{padding:22px 14px 40px}.card{padding:16px}.card-head{display:block}.card-head .badge{margin-top:8px}.card p strong{display:inline}}
    </style></head><body><header><h1>Payment reminders</h1><p>Daily accounts overview · ${escapeHtml(plan.today)}</p></header><main><div class="summary"><div class="stat"><strong>${plan.actions.length}</strong><span>reminders to review</span></div><div class="stat"><strong>${plan.actions.filter((a) => a.needs_approval).length}</strong><span>need approval</span></div><div class="stat"><strong>${plan.skipped.length}</strong><span>invoices skipped</span></div></div><h2>Today's plan</h2>${actions}<h2>Invoices to check</h2>${skipped}<footer>Approvals are recorded for this app session. No messages are sent.</footer></main></body></html>`;
}

createServer(async (req, res) => {
  if (req.method === "POST" && req.url === "/decision") {
    let body = "";
    for await (const chunk of req) body += chunk;
    const form = new URLSearchParams(body);
    const invoiceId = form.get("invoice_id") || "";
    const decision = form.get("decision");
    if (invoiceId && (decision === "approved" || decision === "rejected")) decisions.set(invoiceId, decision);
    res.writeHead(303, { Location: "/" }); res.end(); return;
  }
  if (req.method !== "GET" || req.url !== "/") {
    res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" }); res.end("Not found"); return;
  }
  try {
    const invoices = readJson(`${DATA_DIR}/invoices.json`);
    const sent = readJson(`${DATA_DIR}/sent.json`);
    if (!Array.isArray(invoices) || !Array.isArray(sent)) throw new Error("Both data files must contain JSON arrays.");
    const plan = buildPlan(invoices, sent, TODAY);
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" }); res.end(page(plan, invoices as Array<Record<string, unknown>>));
  } catch (error) {
    const reason = escapeHtml(error instanceof Error ? error.message : String(error));
    res.writeHead(503, { "Content-Type": "text/html; charset=utf-8" });
    res.end(`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Payment reminders unavailable</title><body style="font:16px system-ui;max-width:700px;margin:12vh auto;padding:24px;color:#243b3b"><h1>We could not load today's plan</h1><p>Check that the invoice data files are available and valid, then restart or refresh the page.</p><p><strong>Details:</strong> ${reason}</p></body></html>`);
  }
}).listen(PORT, () => console.log(`Serving on http://localhost:${PORT}/`));
