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


def render_page(plan, invoices):
    by_id = {row.get("id"): row for row in invoices if isinstance(row, dict)}
    cards = []
    for action in plan["actions"]:
        invoice = by_id.get(action["invoice_id"], {})
        approval = "<p class='badge'>No approval needed</p>"
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
        cards.append(
            "<article class='card'><div class='card-head'><div>"
            f"<p class='eyebrow'>{escape(action['step'])} reminder</p>"
            f"<h3>{escape(str(invoice.get('customer', 'Customer')))}</h3></div>"
            f"<span class='badge'>{action['days_overdue']} days overdue</span></div>"
            f"<p><strong>Invoice:</strong> {escape(action['invoice_id'])} &nbsp; "
            f"<strong>Amount:</strong> {escape(amount)}</p>"
            f"<p class='message'>{escape(action['message'])}</p>{approval}</article>"
        )
    action_html = "".join(cards) or (
        "<div class='empty'><h3>You are all caught up</h3>"
        "<p>No reminders need action today.</p></div>"
    )
    reasons = {
        "duplicate_id": "This invoice ID appears more than once.",
        "invalid_amount": "The amount is missing or is not a positive number.",
        "missing_due_date": "The due date is missing.",
        "invalid_due_date": "The due date is not a valid calendar date.",
        "invalid_paid_date": "The paid date is invalid or is after today.",
    }
    skipped_html = (
        "<ul class='skipped'>" + "".join(
            f"<li><strong>{escape(item['invoice_id'])}:</strong> "
            f"{escape(reasons.get(item['reason'], 'This invoice has invalid data.'))}</li>"
            for item in plan["skipped"]
        ) + "</ul>"
        if plan["skipped"] else "<p class='muted'>No invoices were skipped.</p>"
    )
    approvals = sum(action["needs_approval"] for action in plan["actions"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Payment reminders</title>
<style>
:root{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#172a31;background:#f4f7f6}}*{{box-sizing:border-box}}body{{margin:0}}header{{background:#143b3b;color:#fff;padding:32px max(20px,calc((100vw - 960px)/2)}}header p{{margin:0;color:#cce0dc}}main{{max-width:960px;padding:28px 20px 60px;margin:auto}}h1{{margin:0 0 8px;font-size:clamp(1.7rem,5vw,2.4rem)}}h2{{margin:30px 0 14px;font-size:1.25rem}}.summary{{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 28px}}.stat,.card,.empty,.error{{background:#fff;border:1px solid #dce6e2;border-radius:14px;padding:18px;margin:12px 0}}.stat{{min-width:130px;border-radius:12px}}.stat strong{{display:block;font-size:1.35rem}}.stat span,.muted{{color:#5b6d6b;font-size:.92rem}}.card-head{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}}.card h3{{margin:4px 0}}.eyebrow{{text-transform:uppercase;letter-spacing:.09em;font-weight:700;font-size:.72rem;color:#287164;margin:0}}.badge{{display:inline-block;border-radius:999px;background:#e8f3ef;color:#175b4c;padding:6px 10px;font-size:.83rem;font-weight:650}}.card p{{line-height:1.55}}.message{{border-left:3px solid #8db7aa;padding:8px 12px;background:#f7faf9}}.decision{{color:#175b4c;font-weight:700}}form{{display:flex;gap:10px;flex-wrap:wrap}}button{{font:inherit;font-weight:650;border:0;border-radius:8px;padding:10px 16px;background:#176b58;color:white;cursor:pointer}}button.secondary{{background:white;color:#344c4a;border:1px solid #9aadaa}}button:focus-visible{{outline:3px solid #e4a72c;outline-offset:3px}}.skipped{{padding-left:22px}}.skipped li{{padding:7px 0}}footer{{margin-top:32px;color:#5b6d6b;font-size:.88rem}}@media(max-width:480px){{header{{padding:25px 20px}}main{{padding:22px 14px 40px}}.card{{padding:16px}}.card-head{{display:block}}.card-head .badge{{margin-top:8px}}}}
</style></head><body><header><h1>Payment reminders</h1>
<p>Daily accounts overview · {escape(plan['today'])}</p></header><main>
<div class="summary"><div class="stat"><strong>{len(plan['actions'])}</strong><span>reminders to review</span></div>
<div class="stat"><strong>{approvals}</strong><span>need approval</span></div>
<div class="stat"><strong>{len(plan['skipped'])}</strong><span>invoices skipped</span></div></div>
<h2>Today's plan</h2>{action_html}<h2>Invoices to check</h2>{skipped_html}
<footer>Approvals are recorded for this app session. No messages are sent.</footer>
</main></body></html>"""


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
