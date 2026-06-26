# 💰 MoneyMan

**A 100% local, private personal financial *planner*.** Feed it your real bank,
credit-card, and loan statements (PDF, CSV, or QFX) and it shows where your money
goes, finds waste and forgotten subscriptions, computes the interest on
everything you owe, builds a **judgment-free plan to get to $0 debt**, tells you
what to **save for the surprises** ahead, and points the way toward financial
independence.

> 🔒 **Nothing ever leaves your computer.** No account, no login, no internet, no
> address look-ups. Your data stays in one folder you control.

New here? Read the **[Easy Start Guide](docs/USER-GUIDE.md)** and the
**[gather-everything checklist](docs/CHECKLIST.md)** — both written for
non-technical users.

---

## Why it exists

Apps like **Monarch**, **Simplifi**, **Copilot**, and **Rocket Money** have great
insight engines — but they live in the cloud and want your bank login. Privacy-first
tools like **GnuCash** keep your data local — but they're manual ledgers that don't
*plan* for you. **MoneyMan combines the smart engine with full privacy, and adds a
real planner: debt payoff, sinking funds, and a financial-independence roadmap.**
See [Research & Design](docs/RESEARCH-AND-DESIGN.md).

---

## Quick start (Windows)

1. **`Setup.bat`** — one-time, installs the offline PDF reader.
2. **`Try-Demo.bat`** — see a full plan built from realistic fake data.
3. **`Run-MoneyMan.bat`** — creates `Documents\MoneyMan\`. Then:
   - drop your statements into `Statements\` (a sub-folder per account),
   - fill in `config\Accounts-and-Debts.csv` and `config\My-Profile.csv`,
   - run it again. Your plan opens in your browser.

### From a terminal
```sh
python -m moneyman --demo     # generate sample data and open a full plan
python -m moneyman            # analyze Documents\MoneyMan and open the report
python -m moneyman init       # just create the folder structure
python -m moneyman interview  # plain-language Q&A that fills in your profile + debt rates
python -m moneyman serve      # edit your info in a local browser app (saves persist)
python -m moneyman --reset    # forget stored transactions, then re-import
python -m moneyman --no-open  # build the report without opening a browser
```

The `interview` and `serve` commands are also available as the double-click
`Interview.bat` and `Edit-MoneyMan.bat` launchers.

**Requirements:** Python 3.9+. PDF reading needs `pdfplumber`/`pypdf`
(`pip install -r requirements.txt`); CSV/QFX work with zero dependencies.

---

## What you get

- **Ingestion** of **PDF, CSV, OFX, QFX** statements from any number of accounts.
- **Exact de-duplication** across overlapping / re-downloaded statements.
- **Auto-categorization** of hundreds of merchants (extend via `config/categories.json`).
- **Recurring & subscription detection** with annualized cost.
- **A prioritized waste finder** (fees, redundant services, price creep, trial
  conversions, small-but-frequent spend, anomalies) — each with a $/year impact.
- **Debts & interest**: reads balance/APR/minimum from statements (infers APR from
  interest when needed), sorted by rate, with your monthly interest cost.
- **Payoff plans**: Easy / Average / Aggressive paths, avalanche & snowball, with
  debt-free dates and interest saved — driven by *your* spare money + recoverable waste.
- **Cash-flow forecast & "safe to spend"**: projects your checking balance forward
  from your own recent cash flow, flags a shortfall before it happens, and tells you
  what's genuinely free to spend this month after bills and savings.
- **Goal planner**: name a target and a date (`config/Goals.csv`) → the monthly amount
  it takes, and whether your surplus covers it.
- **Mortgage extra-principal analysis**: what paying $100/$250/$500 more a month does —
  years and interest saved on each home loan.
- **Tax orientation**: your estimated federal bracket and effective rate, with
  Traditional-vs-Roth guidance (an estimate, not tax advice).
- **"Possibilities" what-if**: a ranked, dollar-quantified comparison of the
  highest-impact use of a $5k / $20k windfall (pay debt vs. emergency vs. invest).
- **"Save for these" sinking funds**: probability-weighted reserves for car repairs
  & replacement, home maintenance, medical, pets.
- **Emergency-fund** target vs. your current cash.
- **Financial-independence roadmap**: the order of operations (employer match →
  high-interest debt → emergency fund → HSA → IRA → invest) plus *hidden wealth to
  track down* (old 401ks, pensions/TRS, Social Security, HSA, I bonds, unclaimed property).
- **A single self-contained, offline HTML report** with charts and a searchable
  transaction table.

---

## How it's organized

```
MoneyMan/
├─ Setup.bat               ← one-time: install offline PDF reader
├─ Run-MoneyMan.bat        ← analyze your statements
├─ Try-Demo.bat            ← see a demo with fake data
├─ README.md
├─ docs/
│  ├─ USER-GUIDE.md            ← non-technical step-by-step
│  ├─ CHECKLIST.md             ← everything worth gathering
│  ├─ RESEARCH-AND-DESIGN.md   ← market research + feature roadmap
│  └─ PRIVACY-AND-SECURITY.md  ← exactly how your data stays private
└─ moneyman/               ← the program (Python; stdlib + offline PDF libs)
   ├─ __main__.py    orchestration / CLI
   ├─ config.py      paths, categorization rules, intake checklist
   ├─ ingest.py      file scan + CSV / OFX / QFX parsers
   ├─ pdf.py         PDF statement reader (balance/APR/min + transactions)
   ├─ model.py       transaction model, merchant cleaning, categorizer
   ├─ store.py       local SQLite store + de-duplication
   ├─ analyze.py     recurring detection + the waste-finder insight engine
   ├─ debts.py       debt model, interest, payoff simulation (avalanche/snowball)
   ├─ planning.py    profile, emergency fund, reserves, retirement/FI, mortgage, tax
   ├─ forecast.py    cash-flow forecast, safe-to-spend, goal planner
   ├─ intake.py      checklist / completeness scoring + gating
   ├─ charts.py      dependency-free inline-SVG charts
   ├─ report.py      builds the self-contained HTML dashboard
   └─ sample.py      realistic demo-data generator (incl. a demo PDF)
```

Your **data** lives separately under `Documents\MoneyMan\` (or `--data DIR`):

```
Documents\MoneyMan\
├─ Statements\   ← drop bank/card/loan exports here (sub-folder per account)
├─ config\       ← Accounts-and-Debts.csv, My-Profile.csv, categories.json
├─ Reports\      ← generated plans (MoneyMan_Latest.html is the newest)
├─ database\     ← local SQLite store
└─ START-HERE.txt
```

---

## Privacy in one line

Runs locally, makes no network calls at runtime, no accounts, no telemetry, no
address look-ups — verify it yourself (see
[PRIVACY-AND-SECURITY.md](docs/PRIVACY-AND-SECURITY.md)).

## Disclaimer

MoneyMan provides information and education to help you decide. It is **not**
professional financial, tax, or investment advice.
