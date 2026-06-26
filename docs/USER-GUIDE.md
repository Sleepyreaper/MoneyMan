# MoneyMan — Easy Start Guide

*A friendly, no-jargon guide. If you can download a file and double-click an icon,
you can use MoneyMan.*

MoneyMan looks at your real bank, credit-card, and loan statements and becomes
your **private financial planner**: it shows where your money goes, finds waste
and forgotten subscriptions, calculates the interest on everything you owe, lays
out a **judgment-free plan to get to $0 debt**, tells you what to **save for the
surprises** coming your way, and points the way toward real financial
independence.

> 🔒 **Everything stays on your computer.** No website, no login, no telemetry —
> and your financial information never leaves this machine. MoneyMan runs fully
> offline by default; the only thing that can touch the internet is an optional
> home-value lookup you'd have to turn on yourself (and even then it sends only
> your street address, never your money details).

---

## 🚀 First-time setup (about 2 minutes)

1. **Install the PDF reader (one time).** Double-click **`Setup.bat`**. It installs
   a small *offline* library so MoneyMan can read PDF statements. (If you'll only
   use CSV/QFX files, you can skip this.)
2. **See the demo.** Double-click **`Try-Demo.bat`** — MoneyMan invents realistic
   pretend statements, debts, and a profile, then opens a finished plan in your
   browser. Nothing real is touched. Best way to see what you'll get.
3. **Set up your own.** Double-click **`Run-MoneyMan.bat`** once. It creates your
   folder at `Documents\MoneyMan\`.

---

## 📥 Step 1 — Add your statements

See the full **[checklist](CHECKLIST.md)** for everything worth gathering. The
short version:

1. Log in to each bank / credit-card / loan website.
2. **Download / Export** your transactions — choose **PDF, CSV, or Quicken (.QFX)**.
   (CSV/QFX are the most accurate; PDF works too.)
3. Pick the **widest date range** you can (3 months minimum, 12 is best).
4. Save the files into `Documents\MoneyMan\Statements\`, ideally one folder per
   account:
   ```
   Documents\MoneyMan\Statements\Chase Checking\
   Documents\MoneyMan\Statements\Amex Card\
   Documents\MoneyMan\Statements\Car Loan\
   ```

## ✍️ Step 2 — Answer the interview (double-click `Interview.bat`)

Instead of editing spreadsheets, just double-click **`Interview.bat`** and answer
a few plain questions (press Enter to skip any):

- Your age, savings, retirement balance, and employer match.
- Your **home** (own/rent + value) and any **rental property** (value, rent it
  earns, its mortgage balance & rate).
- Your **cars** (year, mileage, what you paid) — for repair/replacement planning.
- The **interest rate (APR) and minimum payment** on each debt. MoneyMan already
  found your balances **and estimates the APR for you** from the interest each card
  was charged (shown with an *“est”* tag) — so the payoff plan works right away.
  Typing in the exact rate just makes it precise.
- **People to track** (optional) — a partner, or each child. You can claim a whole
  account that's theirs and/or a few merchant words (like “roblox”), and MoneyMan
  totals up what each person spends.

Your answers are saved locally to `config\My-Profile.csv`,
`config\Accounts-and-Debts.csv`, and `config\Who-Is-Spending.csv` — you can re-run
the interview or edit those files any time.

## ▶️ Step 3 — See your plan (two ways)

- **`Run-MoneyMan.bat`** → builds a report file and opens it. Fast, read-only.
- **`Edit-MoneyMan.bat`** → opens MoneyMan as a small **web app on your computer**
  where you can **type in your info and click Save**. Your home value, rental
  details, and the **interest rate on each debt** save to your local files and are
  **remembered after you close the browser**. Editing the debt rates here is what
  unlocks your payoff plan. (It runs only on this computer — leave the little black
  window open while you use it, and close it when done.)

Re-run any time you add new statements — duplicates are handled automatically.

> **Finding your way around.** The report opens as a tidy dashboard with tabs
> across the top — **Overview · Debts & payoff · People · Spending · Net worth ·
> Plan ahead · Data** (plus **My info** in the editable web app). Click a tab, or
> click one of the summary cards at the top, to jump straight to what you want.

> **Tip — the "Bills you pay every month" table** lists every charge that repeats
> monthly (vendor, the day it hits, the amount, how long you've paid it, and the
> total you've paid so far). Great for spotting things you forgot you're paying.
> **Click any "What matters most" item** to drill into the exact transactions behind it.

> **Tip — track spending by person.** On the **My info** tab (in
> `Edit-MoneyMan.bat`), add each person you want to follow — a partner, each kid —
> and tell MoneyMan how to spot their charges (a whole account, or merchant words
> like “roblox”). The **People** tab then shows what each person costs per month,
> with a click-through to every charge. Anything not assigned stays in a shared
> *Everyone / Household* total.

> **Tip — the drag-and-drop board (the easy way).** In `Edit-MoneyMan.bat`, the
> **People** tab has a board where every expense is a card and every person is a
> column. **Drag a card onto whoever it's for** — the column totals update live so
> you can *see* where the money goes — then click **Save**. What you set by hand
> always wins over the keyword rules, and it's remembered (saved to
> `config\Spending-Assignments.csv`). No typing required.

---

## 📊 What's in your report

| Section | What it gives you |
|---|---|
| **🧩 Gather the full picture** | A checklist + a completeness % so you know what to add next. |
| **💡 Action items** | The biggest, most fixable money leaks first, each with a yearly cost. |
| **💳 Debts & interest** | Every debt sorted by interest rate, the APR on each (auto-estimated from your interest charges when you haven't typed it), and what you pay in interest **every month**. |
| **👨‍👩‍👧‍👦 People** | What each person in your household spends — per month, as a share of the total, and a click-through to every charge. Optional; set it up on the *My info* tab. |
| **🧗 Your path to $0 owed** | Three judgment-free plans — **Easy / Average / Aggressive** — each showing your debt-free date and the interest you'd save. Plus the order to pay (avalanche) and a snowball option. |
| **🎲 Possibilities** | "If I had **$5,000** / **$20,000**, what's the biggest impact?" — pay debt vs. emergency fund vs. invest. |
| **🌧️ Save for these** | Probability-weighted **sinking funds** for the surprises coming your way — car repairs & replacement, home maintenance, medical, pets — with a monthly amount to set aside. |
| **🛟 Safety net** | Your emergency fund vs. a 3–6 month target. |
| **🧭 The way forward** | A step-by-step order for every dollar (employer match → high-interest debt → emergency fund → HSA → IRA → invest), plus **hidden wealth to track down** (old 401ks, pensions/TRS, Social Security, HSA, I bonds, unclaimed property). |
| **Charts & tables** | Cash flow, spending by category, top merchants, recurring subscriptions, and every transaction (searchable). |

---

## 🔁 Every month
1. Download your latest statements.
2. Drop them in the matching `Statements` sub-folders.
3. Double-click **`Run-MoneyMan.bat`**.

---

## ❓ Troubleshooting

**“Python was not found.”** Install Python 3 from <https://www.python.org/downloads/>
and tick **“Add python.exe to PATH.”** Then run again.

**“PDF reading needs a small offline library.”** Double-click **`Setup.bat`** once.

**A PDF didn't read / numbers look off.** Some statements are scanned images (no
text to read) or use an unusual layout. Use the **CSV/QFX** export if available,
and type the key debt numbers into `Accounts-and-Debts.csv`. Bank PDF layouts
vary — share an example and the parser can be tuned to it.

**My payoff plan amount looks too high/low.** It's based on the money you have
left over plus the waste MoneyMan found. To set your own number, fill in
*“Monthly amount for goals”* in `My-Profile.csv`.

---

*MoneyMan is free, offline, and yours. It gives you information and education to
decide with — it is not professional financial advice.*
