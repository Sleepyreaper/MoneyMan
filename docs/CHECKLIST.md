# 📋 What to gather — the MoneyMan checklist

MoneyMan gets smarter the more of your real picture it can see. You don't need
everything to start (3 months of bank + cards is enough for a first look), but
the full list below unlocks the complete payoff and independence plan.

**No lectures, no judgment.** This is your tool. Gather what you can.

---

## ✅ Start here (minimum for useful insights)
- [ ] **Checking account** — last **3 months** (6–12 is much better). PDF, CSV, or .QFX.
- [ ] **Every credit card** — last 3–12 months. This is where hidden subscriptions
      and high-interest debt hide.
- [ ] **Your income** — usually visible in the checking statements (paychecks/deposits).

## 🏦 All your accounts
- [ ] **Savings account(s)** — so transfers to savings aren't counted as spending.
- [ ] **Any other bank accounts** — joint accounts, cash apps that issue statements.
- [ ] **Investment / brokerage** — optional, for net-worth (statements or balances).

## 💳 Everything you owe (for the payoff plan)
For each debt, MoneyMan wants: **balance owed, interest rate (APR), minimum payment.**
It reads these from statements automatically when it can; otherwise type them into
`config\Accounts-and-Debts.csv`.
- [ ] **Credit cards** (balance, APR, minimum, credit limit)
- [ ] **Auto loan(s)** (balance, APR, payment)
- [ ] **Student loan(s)** (balance, APR, payment)
- [ ] **Personal / medical / other loans**
- [ ] **Mortgage** (balance, rate, payment)

## 🏠 Monthly household bills
- [ ] **Rent or mortgage**
- [ ] **Power / electricity**
- [ ] **Gas**
- [ ] **Water / sewer / trash**
- [ ] **Internet / phone**

## 🛡️ Insurance & protection
- [ ] **Auto insurance**
- [ ] **Home / renters insurance**
- [ ] **Health insurance** (premiums, and your plan's deductible / out-of-pocket max)
- [ ] **Life / disability** (if any)

## 👤 Your profile (one-time, in `config\My-Profile.csv`)
These power the personalized planning that statements can't tell us:
- [ ] **Your age**
- [ ] **Cash savings / emergency fund balance**
- [ ] **Retirement balance** (401k/403k/IRA) and whether you get the **full employer match**
- [ ] **Home**: do you own it, your best estimate of its **value**, and square footage
      *(enter this yourself from Zillow/Redfin — MoneyMan never looks up your address online)*
- [ ] **Cars**: for each — **year, current mileage, purchase date, purchase price**
      *(this drives repair & replacement-savings estimates)*
- [ ] **HSA eligible?** (high-deductible health plan)
- [ ] **Pension or TRS?** (teachers / public employees)

---

## 📥 How to download statements from your bank
1. Log in to the bank/card website in your browser.
2. Find **Download / Export / Statements**.
3. Choose **CSV** or **Quicken (.QFX)** if offered (most accurate). **PDF** also works.
4. Pick the **widest date range** available.
5. Save into `Documents\MoneyMan\Statements\<one folder per account>\`.

## 🔒 A note on the home-value question
You asked MoneyMan to estimate your home's value from its address. Doing that
automatically would require sending your address to an online service — which
breaks the promise that **nothing leaves your computer**. So MoneyMan asks you to
enter the value yourself (Zillow/Redfin show it in seconds) and keeps it local.
If you'd ever like an optional online lookup, you can turn it on knowingly — just ask.
