# Privacy & Security

MoneyMan was built so that **your financial information never leaves your
computer.** This page explains exactly how, in terms you can verify.

## The promises

1. **100% local by default — no internet.** Out of the box MoneyMan makes **no
   network connections**: no server, no API, no “sync,” no update-checker, no
   telemetry. Run it with your Wi-Fi off and it works identically. There is
   exactly **one** off-by-default exception, described in #5: an *address-only*
   home-value lookup you must turn on yourself. With that left off (the default),
   nothing ever leaves your computer.
2. **No account, no login.** There's nothing to sign up for. MoneyMan never asks
   for — and cannot use — your bank username or password. *You* download your
   statements from your bank; MoneyMan only reads the files you place in a folder.
3. **No telemetry, no analytics.** It does not phone home, count users, or report
   crashes anywhere.
4. **Almost no third-party code.** MoneyMan's own logic uses **only the Python
   standard library**. The single exception is reading **PDF** statements, which
   needs an offline PDF-parsing library (`pdfplumber` / `pypdf`). These are
   well-known, open-source, *offline* parsers: they read the PDF file on your
   disk and make no network connections. Installing them (via `Setup.bat`) is the
   only moment anything touches the internet — and it transmits **none** of your
   financial data; it just downloads the library from Python's package index. If
   you never use PDFs, you can skip the install entirely and run on CSV/QFX with
   zero dependencies.
5. **The one optional online feature: an address-only home-value lookup (OFF by
   default).** MoneyMan can't compute your home's market value locally. By
   default you simply **type it in**. If you'd rather have it fetched, you can opt
   in by setting `Look up home value online?` to `y` in `My-Profile.csv` **and**
   supplying your own property-data API key (the `MONEYMAN_RENTCAST_KEY`
   environment variable). Only then — and only your **street address** — is sent,
   to that one service; **never** your balances, transactions, debts, or any other
   financial detail. With no key set, nothing is transmitted at all (MoneyMan just
   builds a Zillow/Redfin link you can click). Your bank accounts are *never*
   looked up online under any setting. The code path is a single, clearly-labeled
   file: `moneyman/homevalue.py`.
6. **Your data stays in plain files you control.** Statements you provide, your
   `config` files, a local SQLite database, and the HTML reports all live under
   one folder: `Documents\MoneyMan\`. Delete that folder and MoneyMan knows nothing.

## How you can verify it yourself

- **Watch the network.** With the home-value lookup off (the default), run
  MoneyMan with the internet disconnected — it behaves exactly the same.
- **Read the code.** It's a small amount of plain Python in the `moneyman\`
  folder. If you search it for `urllib`, `socket`, or `http`, you'll find exactly
  **two** documented things, and nothing else:
  1. `moneyman/homevalue.py` — the **opt-in, off-by-default** address-only
     home-value lookup described in promise #5. Leave the profile flag at `n`
     (the default) and it never runs.
  2. `moneyman/serve.py` — the optional “edit in your browser” app, which binds a
     socket to **`127.0.0.1` (this computer only)** and rejects any request not
     addressed to localhost. It is not reachable from the internet.
  There is no `requests`, no `upload`, and no hidden phone-home anywhere. The only
  `webbrowser.open(...)` call just opens your **local** report file in your browser.
- **Check what's installed.** The only optional packages are the offline PDF
  parsers `pdfplumber` and `pypdf` (see `requirements.txt`). They are read-only
  document parsers with no networking. Everything else is the Python standard
  library.

## What the report contains

The generated HTML report contains your transactions and the insights derived
from them. Treat it like a statement:
- It's saved under `Documents\MoneyMan\Reports\`.
- It's a single self-contained file (no external links or trackers).
- If you share it (e.g., with a partner or advisor), remember it includes your
  transaction details — share deliberately.

## Sensible hardening (optional)

- Keep the `Documents\MoneyMan\` folder on an encrypted disk (Windows BitLocker /
  macOS FileVault) if your whole machine isn't already encrypted.
- Use your operating-system user account password — that's your first line of
  defense for the local database and reports.
- A future optional feature is passphrase encryption of the local database; until
  then, rely on full-disk encryption for at-rest protection.

## What MoneyMan deliberately does **not** do

- It does not connect to banks or use “bank aggregators” (the services that ask
  for your login). That convenience is exactly the privacy trade MoneyMan exists
  to avoid.
- It does not auto-cancel subscriptions or negotiate bills (that requires acting
  on your behalf online). It **finds** them and tells you what to cancel; the
  cancellation is yours to do.
