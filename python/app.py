"""One-page owner dashboard. Run with ``python app.py`` from python/."""

import os
from datetime import date
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from plan import build_plan, read_json

PORT = int(os.environ.get("PORT", "8000"))
DATA_DIR = os.environ.get("DATA_DIR", "../data")
TODAY = os.environ.get("TODAY") or date.today().isoformat()
DECISIONS = {}

STYLES = """
:root{font-family:'Segoe UI',Arial,sans-serif;color:#202b35;background:#f4f3ef;font-synthesis:none;text-rendering:optimizeLegibility}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 10% 0%,#e5eee8 0,transparent 34%),#f4f3ef;min-height:100vh}
header{position:relative;overflow:hidden;background:#173f3b;color:#fff;padding:30px max(24px,calc((100vw - 1080px)/2));}
header:after{content:'';position:absolute;width:360px;height:360px;border:1px solid #ffffff20;border-radius:50%;right:7%;top:-245px;box-shadow:0 0 0 42px #ffffff0a,0 0 0 84px #ffffff08}
.topline{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:54px;position:relative;z-index:1}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;letter-spacing:.01em}.brand-mark{display:grid;place-items:center;width:34px;height:34px;background:#d4f06e;color:#173f3b;border-radius:11px;font-weight:800}
.date-pill{border:1px solid #ffffff38;background:#ffffff0d;padding:8px 12px;border-radius:999px;color:#e0e9e4;font-size:.83rem}
.hero-copy{position:relative;z-index:1;max-width:650px;padding-bottom:43px}.kicker{color:#d4f06e;font-size:.74rem;text-transform:uppercase;letter-spacing:.16em;font-weight:700;margin:0 0 13px}
h1,h2,h3,p{margin-top:0}h1,h2,h3{font-family:'Segoe UI',Arial,sans-serif}h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.08;letter-spacing:-.045em;margin-bottom:14px}.hero-copy>p:last-child{color:#d0ded8;font-size:1.03rem;line-height:1.6;margin-bottom:0}
main{max-width:1080px;padding:0 24px 64px;margin:-22px auto 0;position:relative;z-index:2}.summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:38px}
.stat{background:#fff;border:1px solid #e6e7df;border-radius:16px;padding:20px 22px;box-shadow:0 9px 28px #183d3510;display:flex;align-items:center;gap:15px}
.stat-icon{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;background:#edf4e4;color:#456b37;font-size:1.15rem}.stat:nth-child(2) .stat-icon{background:#fff0dc;color:#986319}.stat:nth-child(3) .stat-icon{background:#fbe8e1;color:#a35138}
.stat strong{display:block;font:800 1.65rem 'Segoe UI',Arial,sans-serif;letter-spacing:-.04em}.stat span{color:#77817d;font-size:.82rem}
.section-heading{display:flex;justify-content:space-between;align-items:end;gap:12px;margin-bottom:16px}.section-heading h2{font-size:1.35rem;letter-spacing:-.03em;margin:0}.section-heading p{font-size:.84rem;color:#77817d;margin:0}
.reminder-card,.empty,.skipped-panel{background:#fff;border:1px solid #e6e7df;border-radius:18px;margin:12px 0;box-shadow:0 8px 24px #183d3508}.reminder-card{padding:22px 24px;border-left:5px solid #79a94a;background:linear-gradient(105deg,#f2f7e9 0,#fff 45%)}.reminder-card[data-step='firm']{border-left-color:#d99332;background:linear-gradient(105deg,#fff5e5 0,#fff 45%)}.reminder-card[data-step='final']{border-left-color:#cf634b;background:linear-gradient(105deg,#fff0eb 0,#fff 45%)}
.card-head{display:flex;justify-content:space-between;gap:14px;align-items:flex-start}.card-title{display:flex;align-items:center;gap:12px}.avatar{flex:0 0 42px;width:42px;height:42px;border-radius:14px;background:#e8f0e9;color:#285b4e;display:grid;place-items:center;font-weight:800}.card h3{font-size:1.05rem;letter-spacing:-.02em;margin:2px 0 0}.step-label{display:inline-flex;text-transform:uppercase;letter-spacing:.1em;font-weight:800;font-size:.69rem;color:#4c7134;background:#e6f0d9;border-radius:6px;padding:5px 8px;margin:0 0 5px}.reminder-card[data-step='firm'] .step-label{color:#895a18;background:#ffebc9}.reminder-card[data-step='final'] .step-label{color:#994431;background:#fbded5}
.badge{display:inline-flex;align-items:center;border-radius:999px;background:#eff4e9;color:#4d6e37;padding:7px 11px;font-size:.79rem;font-weight:700;white-space:nowrap}.reminder-card[data-step='firm'] .badge{background:#fff0d5;color:#895a18}.reminder-card[data-step='final'] .badge{background:#fce4dc;color:#994431}
.details{display:flex;gap:9px;flex-wrap:wrap;margin:18px 0 14px}.detail-chip{border:1px solid #edf0ea;border-radius:9px;padding:8px 10px;font-size:.84rem;color:#65716c}.detail-chip strong{color:#263a34;font-weight:700}
.message{background:#f7f8f4;border-radius:0 11px 11px 0;border-left:3px solid #c8d8bd;padding:13px 15px;color:#4d5c56;font-size:.91rem;line-height:1.65;margin:14px 0 18px}
form{display:flex;gap:9px;flex-wrap:wrap}button{font:600 .87rem 'Segoe UI',Arial,sans-serif;border:0;border-radius:9px;padding:10px 15px;background:#1c5a4c;color:white;cursor:pointer;transition:transform .15s,background .15s}button:hover{background:#15493e;transform:translateY(-1px)}.reminder-card[data-step='firm'] button:not(.secondary){background:#a86e1e}.reminder-card[data-step='firm'] button:not(.secondary):hover{background:#875618}.reminder-card[data-step='final'] button:not(.secondary){background:#ad4f39}.reminder-card[data-step='final'] button:not(.secondary):hover{background:#913d2b}button.secondary{background:#fff;color:#53615b;border:1px solid #dce2da}button.secondary:hover{background:#f7f8f4}button:focus-visible{outline:3px solid #d4f06e;outline-offset:3px}.decision{display:inline-flex;color:#215946;font-weight:700;background:#edf5ef;border-radius:8px;padding:9px 12px;margin:0}
.empty{padding:38px;text-align:center;background:linear-gradient(135deg,#fff,#f7f8f3)}.empty-icon{width:54px;height:54px;margin:0 auto 14px;border-radius:18px;background:#eaf2df;color:#54743c;display:grid;place-items:center;font-size:1.45rem}.empty h3{margin-bottom:7px}.empty p,.muted{color:#77817d;margin:0}
.skipped-panel{padding:20px 24px}.skipped{list-style:none;margin:0;padding:0}.skipped li{padding:12px 0;border-bottom:1px solid #eff0eb;color:#66716c;font-size:.9rem}.skipped li:last-child{border-bottom:0}.skipped strong{color:#32443d}.reason-dot{display:inline-block;width:7px;height:7px;background:#dd9776;border-radius:50%;margin-right:9px;vertical-align:1px}
footer{margin-top:28px;text-align:center;color:#85908a;font-size:.8rem;padding:12px}
@media(max-width:680px){header{padding:24px 20px 44px}.topline{margin-bottom:39px}.hero-copy{padding-bottom:4px}main{padding:0 15px 42px;margin-top:-16px}.summary{gap:8px;margin-bottom:30px}.stat{padding:13px 10px;display:block;text-align:center;border-radius:13px}.stat-icon{width:32px;height:32px;margin:0 auto 7px;border-radius:10px}.stat strong{font-size:1.3rem}.stat span{font-size:.7rem;line-height:1.15;display:block}.section-heading{align-items:start;flex-direction:column;gap:4px}.reminder-card{padding:17px 15px;border-radius:15px}.card-head{align-items:start}.card-title{gap:9px}.avatar{width:36px;height:36px;flex-basis:36px;border-radius:12px}.badge{font-size:.72rem;padding:6px 8px}.details{gap:6px;margin:14px 0 11px}.detail-chip{font-size:.78rem;padding:7px 8px}.message{font-size:.87rem;padding:11px 12px}.skipped-panel{padding:16px}.empty{padding:30px 18px}}
@media(max-width:390px){.date-pill{font-size:.72rem;padding:7px 9px}.brand{font-size:.88rem}.summary{gap:6px}.stat{padding:12px 6px}.stat span{font-size:.65rem}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important}}
"""


def render_page(plan, invoices):
    by_id = {row.get("id"): row for row in invoices if isinstance(row, dict)}
    cards = []
    for action in plan["actions"]:
        invoice = by_id.get(action["invoice_id"], {})
        approval = "<p class='decision'>No approval needed</p>"
        if action["needs_approval"]:
            decision = DECISIONS.get(action["invoice_id"])
            if decision:
                approval = f"<p class='decision' role='status'>{escape(decision.title())}</p>"
            else:
                approval = (
                    "<form method='post' action='/decision'>"
                    f"<input type='hidden' name='invoice_id' value='{escape(action['invoice_id'], quote=True)}'>"
                    "<button name='decision' value='approved'>Approve</button>"
                    "<button class='secondary' name='decision' value='rejected'>Reject</button></form>"
                )
        amount = f"{invoice.get('currency', '')} {invoice.get('amount', 0):,.2f}"
        customer = str(invoice.get("customer", "Customer"))
        initials = "".join(part[0] for part in customer.split()[:2]).upper() or "?"
        cards.append(
            f"<article class='reminder-card' data-step='{escape(action['step'], quote=True)}'>"
            "<div class='card-head'><div class='card-title'>"
            f"<span class='avatar' aria-hidden='true'>{escape(initials)}</span><div>"
            f"<p class='step-label'>{escape(action['step'])} reminder</p>"
            f"<h3>{escape(customer)}</h3></div></div>"
            f"<span class='badge'>{action['days_overdue']} days overdue</span></div>"
            "<div class='details'>"
            f"<span class='detail-chip'>Invoice <strong>{escape(action['invoice_id'])}</strong></span>"
            f"<span class='detail-chip'>Amount <strong>{escape(amount)}</strong></span></div>"
            f"<p class='message'>{escape(action['message'])}</p>{approval}</article>"
        )
    action_html = "".join(cards) or (
        "<div class='empty'><div class='empty-icon' aria-hidden='true'>✓</div>"
        "<h3>You are all caught up</h3><p>No reminders need action today.</p></div>"
    )
    reasons = {
        "duplicate_id": "This invoice ID appears more than once.",
        "invalid_amount": "The amount is missing or is not a positive number.",
        "missing_due_date": "The due date is missing.",
        "invalid_due_date": "The due date is not a valid calendar date.",
        "invalid_paid_date": "The paid date is invalid or is after today.",
    }
    skipped_html = (
        "<div class='skipped-panel'><ul class='skipped'>" + "".join(
            f"<li><span class='reason-dot' aria-hidden='true'></span><strong>{escape(item['invoice_id'])}:</strong> "
            f"{escape(reasons.get(item['reason'], 'This invoice has invalid data.'))}</li>"
            for item in plan["skipped"]
        ) + "</ul></div>"
        if plan["skipped"] else "<p class='muted'>No invoices were skipped.</p>"
    )
    approvals = sum(
        action["needs_approval"] and action["invoice_id"] not in DECISIONS
        for action in plan["actions"]
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Payment reminders</title>
<style>{STYLES}</style></head><body><header>
<div class="topline"><div class="brand"><span class="brand-mark" aria-hidden="true">↗</span>Ledgerly</div>
<span class="date-pill">Daily overview &nbsp;|&nbsp; {escape(plan['today'])}</span></div>
<div class="hero-copy"><p class="kicker">Receivables workspace</p>
<h1>Make every follow-up<br>feel effortless.</h1>
<p>Your daily payment queue is ready. Review reminders, approve the next step, and keep every invoice moving.</p></div>
</header><main><section class="summary" aria-label="Plan summary">
<div class="stat"><div class="stat-icon" aria-hidden="true">↗</div><div><strong>{len(plan['actions'])}</strong><span>reminders to review</span></div></div>
<div class="stat"><div class="stat-icon" aria-hidden="true">◎</div><div><strong>{approvals}</strong><span>need your approval</span></div></div>
<div class="stat"><div class="stat-icon" aria-hidden="true">!</div><div><strong>{len(plan['skipped'])}</strong><span>invoices to check</span></div></div>
</section><section aria-labelledby="plan-heading"><div class="section-heading"><h2 id="plan-heading">Today's plan</h2>
<p>Sorted by invoice ID · one next step per invoice</p></div>{action_html}</section>
<section aria-labelledby="skipped-heading"><div class="section-heading"><h2 id="skipped-heading">Needs a closer look</h2>
<p>Invoices with data that needs attention</p></div>{skipped_html}</section>
<footer>Approvals stay in this session. Nothing is sent to customers.</footer></main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return
        try:
            invoices = read_json(os.path.join(DATA_DIR, "invoices.json"))
            sent = read_json(os.path.join(DATA_DIR, "sent.json"))
            if not isinstance(invoices, list) or not isinstance(sent, list):
                raise ValueError("Both data files must contain JSON arrays.")
            page = render_page(build_plan(invoices, sent, TODAY), invoices)
            self.send_response(200)
        except (OSError, ValueError) as error:
            page = (
                "<!doctype html><html lang='en'><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<title>Payment reminders unavailable</title><body style='font:16px system-ui;"
                "max-width:700px;margin:12vh auto;padding:24px;color:#243b3b'>"
                "<h1>We could not load today's plan</h1><p>Check that the invoice data files are "
                "available and valid, then refresh this page.</p><p><strong>Details:</strong> "
                f"{escape(str(error))}</p></body></html>"
            )
            self.send_response(503)
        data = page.encode("utf-8")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/decision":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        form = parse_qs(self.rfile.read(length).decode("utf-8"))
        invoice_id = form.get("invoice_id", [""])[0]
        decision = form.get("decision", [""])[0]
        if invoice_id and decision in ("approved", "rejected"):
            DECISIONS[invoice_id] = decision
        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()


def main():
    server = ThreadingHTTPServer(("", PORT), Handler)
    print(f"Serving on http://localhost:{PORT}/")
    server.serve_forever()


if __name__ == "__main__":
    main()
