# Privacy & Security

MoneyMan was built so that **your financial information never leaves your
computer.** This page explains exactly how, in terms you can verify.

## The promises

1. **No internet, ever.** MoneyMan makes no network connections. It has no
   server, no API, no “sync,” and no update-checker. You can run it with your
   Wi-Fi turned off and it works identically.
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
5. **We never look up your address or accounts online.** Things we can't compute
   locally — like your home's market value — are **typed in by you** and kept on
   your machine. MoneyMan will not send your address, balances, or any detail to
   a property site, bank, or any other service.
6. **Your data stays in plain files you control.** Statements you provide, your
   `config` files, a local SQLite database, and the HTML reports all live under
   one folder: `Documents\MoneyMan\`. Delete that folder and MoneyMan knows nothing.

## How you can verify it yourself

- **Watch the network.** Run MoneyMan with the internet disconnected — it
  behaves exactly the same.
- **Read the code.** It's a small amount of plain Python in the `moneyman\`
  folder. Search it for `http`, `socket`, `urllib`, `requests`, `upload` — you
  won't find network calls. The only “open” is `webbrowser.open(...)`, which
  opens your **local** report file in your browser.
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
