"""A tiny LOCAL web app so you can edit your info in the browser and have it
PERSIST. It listens only on 127.0.0.1 (this computer) — it is not on the
internet, and nothing is sent anywhere. Closing the browser doesn't lose your
edits: every Save writes to your local files (config\\*.csv) and re-runs.

    python -m moneyman serve        (or double-click Edit-MoneyMan.bat)
"""

from __future__ import annotations

import csv
import io
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Paths, data_home
from .people import SHARED, Person, write_assignments, write_people
from .report import build_html

# Only this computer may talk to the server. We bind to 127.0.0.1, but that alone
# does NOT stop a malicious website you happen to visit from using DNS rebinding
# to reach the server through your own browser and read your whole financial
# dashboard (or POST to /save-* to corrupt your files). Validating the Host header
# closes that hole: a rebinding attack still sends the attacker's hostname here, so
# anything that isn't a genuine localhost name is rejected. Privacy is the product.
_ALLOWED_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}


def host_is_local(host_header: str) -> bool:
    """True if a request's Host header names this machine (loopback only)."""
    host = (host_header or "").strip()
    if not host:
        return False                       # a real browser always sends Host
    if host.startswith("["):               # IPv6 literal, e.g. [::1]:8765
        hostname = host[1:host.find("]")] if "]" in host else host[1:]
    else:
        hostname = host.split(":", 1)[0]
    return hostname.lower() in _ALLOWED_HOSTNAMES


def is_cross_site_post(sec_fetch_site: str | None, origin: str | None) -> bool:
    """True if a state-changing POST looks cross-site (a CSRF attempt) → reject.

    The Host check (above) stops DNS-rebinding but NOT a plain cross-site form
    POST: a malicious page can submit a form to http://127.0.0.1:8765/save-* and
    the Host header is still '127.0.0.1', so it passes. Without this guard such a
    request could silently overwrite the user's config files. Browsers reveal the
    real initiator two ways and we trust either:

      * ``Sec-Fetch-Site``: a value of 'cross-site' is a forged submission;
        'same-origin' / 'same-site' / 'none' come from our own page.
      * ``Origin``: must name localhost; any other site is rejected.

    If neither header is present (a very old browser doing a genuine same-origin
    POST) we allow it — a cross-site attacker's browser always sends ``Origin``
    on a cross-origin POST, so the hole is closed.
    """
    if sec_fetch_site:
        return sec_fetch_site.strip().lower() == "cross-site"
    if origin:
        hostname = urllib.parse.urlsplit(origin.strip()).hostname or ""
        return hostname.lower() not in _ALLOWED_HOSTNAMES
    return False

# Editable profile inputs are named with their exact CSV field label, so saving
# is a direct write. (Listed here only to know which posted keys are profile.)
_PROFILE_FIELDS = {
    "Monthly take-home income", "Filing status (single/mfj/hoh/mfs)",
    "Your age", "Target retirement age", "Cash savings", "Retirement balance",
    "Monthly retirement contribution",
    "Estimated Social Security (monthly, household)", "Inflation assumption (%)",
    "Own your home? (y/n)",
    "Home value (your estimate)", "Own a rental property? (y/n)",
    "Rental property value", "Rental monthly rent income",
    "Rental mortgage balance", "Rental mortgage APR (%)",
}


def _read_profile(path) -> "dict[str, str]":
    out: dict[str, str] = {}
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as f:
            for r in csv.reader(x for x in f if not x.lstrip().startswith("#")):
                if len(r) >= 2 and r[0].strip() and r[0].strip().lower() != "field":
                    out[r[0].strip()] = r[1].strip()
    return out


def _save_profile(paths: Paths, form: dict) -> str:
    path = paths.config / "My-Profile.csv"
    existing = _read_profile(path)
    changed = 0
    for k, vals in form.items():
        if k in _PROFILE_FIELDS:
            existing[k] = (vals[0] if vals else "").strip()
            changed += 1
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Field", "Value"])
    for k, v in existing.items():
        w.writerow([k, v])
    path.write_text("# MoneyMan profile — edited in the web app; safe to edit here too.\n"
                    + buf.getvalue(), encoding="utf-8")
    return f"Saved your info ({changed} fields). Recalculated below."


def _save_debts(paths: Paths, form: dict) -> str:
    path = paths.config / "Accounts-and-Debts.csv"

    def g(k):
        return form.get(k, [""])[0].strip()

    n = int(g("d_count") or "0")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Name", "Type", "Balance Owed", "APR (%)",
                "Minimum Monthly Payment", "Credit Limit"])
    for i in range(n):
        name = g(f"d{i}_name")
        if not name:
            continue
        w.writerow([name, g(f"d{i}_kind") or "other", g(f"d{i}_bal"),
                    g(f"d{i}_apr"), g(f"d{i}_min"), g(f"d{i}_limit")])
    path.write_text("# Your debts — edited in the web app.\n"
                    "# Type: credit card, auto loan, student loan, personal loan, mortgage, medical, other\n"
                    + buf.getvalue(), encoding="utf-8")
    return "Saved your debt rates. Your payoff plan is updated below."


def _save_people(paths: Paths, form: dict) -> str:
    path = paths.config / "Who-Is-Spending.csv"

    def g(k):
        return form.get(k, [""])[0].strip()

    n = int(g("p_count") or "0")
    people: list[Person] = []
    for i in range(n):
        name = g(f"p{i}_name")
        if not name:
            continue
        accounts = [x.strip() for x in g(f"p{i}_acct").replace(",", ";").split(";")
                    if x.strip()]
        keywords = [x.strip() for x in g(f"p{i}_kw").replace(",", ";").split(";")
                    if x.strip()]
        people.append(Person(name=name, accounts=accounts, keywords=keywords))
    write_people(path, people)
    return (f"Saved {len(people)} person(s). Spending-by-person is updated on the "
            "People tab.")


def _save_assignments(paths: Paths, form: dict) -> str:
    path = paths.config / "Spending-Assignments.csv"

    def g(k):
        return form.get(k, [""])[0].strip()

    n = int(g("a_count") or "0")
    mapping: dict[str, str] = {}
    for i in range(n):
        merchant = g(f"m{i}")
        if merchant:
            mapping[merchant] = g(f"p{i}") or SHARED
    write_assignments(path, mapping)
    moved = sum(1 for v in mapping.values() if v != SHARED)
    return (f"Saved — {moved} expense(s) assigned to a person, the rest shared. "
            "People totals are updated.")


class _Handler(BaseHTTPRequestHandler):
    paths: Paths = None        # set before serving
    saved_msg: str = ""

    def log_message(self, *a):
        pass                    # keep the console quiet

    def _reject_foreign_host(self) -> bool:
        """Block anything not addressed to localhost (DNS-rebinding defense)."""
        if host_is_local(self.headers.get("Host", "")):
            return False
        self.send_response(403)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"MoneyMan only accepts requests from this computer.")
        return True

    def _reject_cross_site(self) -> bool:
        """Block cross-site POSTs to the save endpoints (CSRF defense)."""
        if is_cross_site_post(self.headers.get("Sec-Fetch-Site"),
                              self.headers.get("Origin")):
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"MoneyMan blocked a cross-site request.")
            return True
        return False

    def _html(self, status=200):
        from .__main__ import compute
        analysis, plan, warnings, stats, _, dup = compute(_Handler.paths)
        html = build_html(analysis, _Handler.paths.root, warnings, stats, dup, plan,
                          editable=True, saved_msg=_Handler.saved_msg)
        _Handler.saved_msg = ""
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self._reject_foreign_host():
            return
        if self.path in ("/", "/index.html"):
            self._html()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self._reject_foreign_host():
            return
        if self._reject_cross_site():
            return
        length = int(self.headers.get("Content-Length", 0))
        form = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"))
        try:
            if self.path == "/save-profile":
                _Handler.saved_msg = _save_profile(_Handler.paths, form)
            elif self.path == "/save-debts":
                _Handler.saved_msg = _save_debts(_Handler.paths, form)
            elif self.path == "/save-people":
                _Handler.saved_msg = _save_people(_Handler.paths, form)
            elif self.path == "/save-assignments":
                _Handler.saved_msg = _save_assignments(_Handler.paths, form)
        except Exception as e:
            _Handler.saved_msg = f"Couldn't save ({e}). Nothing was lost."
        self.send_response(303)        # redirect back to a fresh, recalculated page
        self.send_header("Location", "/")
        self.end_headers()


def _port_in_use(port: int) -> bool:
    """True if something is already listening on 127.0.0.1:port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def run_server(paths: Paths, port: int = 8765) -> int:
    paths.ensure()
    # On Windows HTTPServer sets SO_REUSEADDR, so a second launch would silently
    # bind the same port and serve confusing, stale pages. Detect that and stop.
    if _port_in_use(port):
        url = f"http://127.0.0.1:{port}/"
        print(f"MoneyMan already appears to be running — open {url} in your browser.")
        print("(If not, something else is using the port; close it and try again.)")
        try:
            webbrowser.open(url)
        except Exception:
            pass
        return 0
    _Handler.paths = paths
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{port}/"
    print("=" * 60)
    print("  MoneyMan is running as a LOCAL web app (this computer only).")
    print(f"  Open:  {url}")
    print("  Edit your info / debt rates in the page and click Save —")
    print("  it writes to your local files and persists.")
    print("  Press Ctrl+C here to stop.")
    print("=" * 60)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Your data is saved in", paths.root)
    finally:
        httpd.server_close()
    return 0
