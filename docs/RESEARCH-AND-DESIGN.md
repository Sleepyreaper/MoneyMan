# MoneyMan — Research & Design

This document captures the market research and the feature thinking behind
MoneyMan: what the leading personal-finance tools do, what real people need, and
where MoneyMan sits.

---

## 1. The market, and the gap MoneyMan fills

I looked at the tools people actually use in 2026. They cluster into three camps:

### Camp A — Smart cloud apps (great insights, your data lives on their servers)
| Tool | Strengths | The catch |
|---|---|---|
| **Monarch Money** | Auto-categorization, recurring/subscription detection with a renewal calendar, net-worth tracking, flexible budgeting, an AI assistant, weekly recaps. | ~$100/yr. Connects to your bank via a third party; your data sits in their cloud. |
| **Quicken Simplifi** | “Spending plan,” a real-time *safe-to-spend* number, 12-month cash-flow projections, savings goals, custom reports. | ~$48/yr. Cloud-based bank sync. |
| **Copilot Money** | Best-in-class auto-categorization, beautiful design, investment + net-worth tracking. | ~$13/mo, iOS-first, cloud. |
| **Rocket Money** | The famous **subscription finder** — it identifies forgotten subscriptions and will even *cancel* them and negotiate bills for you. | Needs your bank login; takes a cut of negotiated savings; cloud. |
| **YNAB** | A philosophy: “give every dollar a job” (zero-based budgeting); strong habit-building. | ~$109/yr. Forward-looking budgeting, not a “find my waste” analyzer; cloud. |

**Common thread:** to give you insights, they all require linking your bank
account and uploading your financial life to a server. That's the trade most
people quietly accept.

### Camp B — Privacy-first local apps (your data, but mostly manual)
**GnuCash, Actual Budget, HomeBank, Money Manager Ex** all run on your own
computer with no cloud. They're excellent, but they're fundamentally
**accounting / budgeting ledgers** — you do the categorizing and the thinking.
They don't proactively say *“you're wasting $510/year on overlapping streaming
services.”*

### Camp C — Spreadsheets (Tiller, manual Excel)
Maximum control, maximum effort, and Tiller still keeps data in your cloud
Google/Microsoft account.

### 🎯 The gap → MoneyMan
> **The insight engine of Monarch/Rocket Money, with the privacy of GnuCash.**

MoneyMan proactively *finds the waste* (Camp A's superpower) while running
**100% locally with zero accounts and zero network access** (Camp B's
superpower). You download your own statements — no bank credentials are ever
entered anywhere — and everything is analyzed on your machine.

---

## 2. What people actually need (and the feature priority)

I sorted features into **Must-have**, **Should-have**, and **Could-have**, based
on what the tools above compete on and what causes real financial leakage.

### ✅ Must-have — *shipped in v1.0*
- **Ingest real statements** from any account: CSV, OFX, QFX. One folder you
  drop files into.
- **Bullet-proof de-duplication** so overlapping/re-downloaded statements never
  double-count (uses bank transaction IDs when available, a content fingerprint
  otherwise).
- **Automatic categorization** of hundreds of common merchants, user-extendable.
- **Recurring & subscription detection** with the *annualized* cost — the number
  people most underestimate.
- **The “waste finder” insight engine**, prioritized by dollar impact:
  - Total recurring commitments per month/year.
  - **Avoidable fees & interest** (overdraft, ATM, late, foreign-transaction).
  - **Redundant services** (e.g., 4 streaming apps; 2 gyms).
  - **Price creep** on subscriptions (old price → new price, +%/yr).
  - **Newly-started recurring charges** (likely free-trial conversions).
  - **“Death by a thousand cuts”** (coffee, food delivery) with yearly totals.
  - **Spending anomalies** (a category spiking far above its normal month).
  - **Cash-flow / savings-rate** health check.
- **Trends & visuals**: monthly cash flow, spending by category, top merchants.
- **Searchable, sortable transaction table.**
- **A single self-contained HTML report** that opens offline.
- **True privacy**: standard-library Python only, no telemetry, and no
  third-party packages that could phone home. Makes no network calls at runtime —
  except one off-by-default, address-only home-value lookup you must explicitly
  enable.

### 🟦 Should-have — *natural next steps*
- **Net-worth tracking**: read account balances (assets/debts) over time.
- **Budgets & “safe-to-spend”**: set category limits; show remaining like Simplifi.
- **Cash-flow forecast**: project the next 1–12 months from known recurring items.
- **Bill/renewal calendar**: “these subscriptions renew in the next 30 days.”
- **Cross-account transfer netting**: automatically pair a credit-card payment
  from checking with the card, so transfers never look like spending.
- **Goal tracking** (emergency fund, vacation) with progress vs. target.
- **Year-over-year comparisons** and tax-relevant category summaries.
- **One-click CSV/PDF export** of the findings.

### 🟨 Could-have — *power-user / future*
- **Optional encryption at rest** (passphrase-locked local database).
- **Local-only “explain my spending” assistant** using a small on-device model,
  so even the AI Q&A stays offline.
- **Smarter categorization** that learns from your manual corrections.
- **Investment & retirement tracking** (holdings, allocation, fees).
- **Receipt OCR** to enrich transactions (local).
- **Multi-currency** support.
- **“What-if” simulator**: “If I cancel these 3 subscriptions, I save $X/yr.”

---

## 3. How MoneyMan's insight engine works (in plain terms)

Everything is **explainable rules**, not a black box — important for trust when
money is involved.

- **Recurring detection.** Group transactions by cleaned merchant name. If a
  merchant has ≥3 charges that arrive on a regular rhythm (weekly, monthly,
  yearly, etc.) *and* at a steady amount, it's recurring. The cadence sets the
  annualized cost (a $15/mo charge = $180/yr; a $99/yr charge = $99/yr).
- **Price creep.** Within a recurring stream, compare the earliest charge to the
  latest. A meaningful increase is flagged with the extra yearly cost.
- **Redundancy.** Two or more active subscriptions in the same category
  (Streaming, Software, Fitness) get flagged as possible overlap.
- **New / trial conversions.** A recurring charge whose first occurrence appears
  well after your history begins is likely a recent sign-up or trial-to-paid.
- **Fees.** Anything matching fee/interest keywords is summed — these are the
  most avoidable dollars in the whole report.
- **Anomalies.** For each category with enough history, a month more than ~2.2×
  its typical month is surfaced.

Duplicate handling deserves special mention because it's where naïve tools fail:
- If the file provides a bank transaction ID (OFX/QFX `FITID`), that's the key —
  perfectly exact.
- Otherwise the key is `account + date + amount + merchant + Nth-occurrence-in-file`.
  The “Nth occurrence” trick means two genuine $5 coffees on the same day are
  *kept*, while the same statement imported twice is *collapsed*.

---

## 4. Design principles

1. **Privacy is the product.** If a feature needs the cloud, it doesn't ship
   (or it ships as an explicit, off-by-default local option). No account, no
   network, no telemetry.
2. **Non-technical first.** A double-clickable launcher, a single folder for
   input, an auto-opening report, and plain-English findings with dollar amounts.
3. **No dependencies.** Pure Python standard library → trivial to install, audit,
   and trust. There are no third-party packages that could change behavior or
   exfiltrate data.
4. **Explainable.** Every insight is a transparent rule a person can reason
   about, not an opaque model.
5. **Your data is yours.** Plain files you can read, back up, move, or delete.

---

## 5. Sources

- Monarch Money review — FinanceBuzz: <https://financebuzz.com/monarch-money-review>
- Monarch Money review — CNBC Select: <https://www.cnbc.com/select/monarch-money-budgeting-app-review/>
- Quicken Simplifi review — CNBC Select: <https://www.cnbc.com/select/quicken-simplifi-review/>
- Quicken Simplifi winter 2026 updates — Quicken: <https://www.quicken.com/blog/quicken-simplifi-winter-2026-updates/>
- Rocket Money vs Copilot — Rocket Money: <https://www.rocketmoney.com/compare/copilot>
- Best budgeting apps 2026 — The College Investor: <https://thecollegeinvestor.com/32672/best-budgeting-apps/>
- Best budgeting apps 2026 — Engadget: <https://www.engadget.com/apps/best-budgeting-apps-120036303.html>
- Privacy-focused / open-source finance software — SourceForge: <https://sourceforge.net/directory/personal-finance/>
- Tiller Money alternatives — AlternativeTo: <https://alternativeto.net/software/tiller-money/>
