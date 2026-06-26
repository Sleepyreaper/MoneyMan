"""MoneyMan regression tests — standard-library `unittest`, zero dependencies.

Run from the repo root:

    python -m unittest discover -s tests -t .
    python tests/test_moneyman.py            # also works (self-pathing)

These cover the parts where a silent bug would quietly mislead someone about
their money: the sign convention, de-duplication, statement parsing,
categorization, APR inference, and the payoff simulation. They are intentionally
fast and offline.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Make the package importable whether run via `unittest discover` or directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moneyman.analyze import analyze, detect_recurring, _d
from moneyman.config import DEFAULT_CATEGORY_RULES
from moneyman.debts import (Debt, infer_apr, infer_aprs_from_records, plan_paths,
                            simulate_payoff)
from moneyman.ingest import (_looks_like_balances, _parse_amount, _parse_date,
                             parse_balances, parse_csv, parse_ofx)
from moneyman.model import Txn, categorize, clean_merchant
from moneyman.planning import (Profile, emergency_fund, net_worth_from_balances,
                               retirement_projection)
from moneyman.planning import (amortize, liquid_cash_from_balances,
                               lump_sum_options, mortgage_analysis,
                               standard_payment, tax_insights)
from moneyman.forecast import (cashflow_forecast, expected_monthly_net, goal_plan,
                               safe_to_spend)
from moneyman.serve import host_is_local, is_cross_site_post
from datetime import date

RULES = DEFAULT_CATEGORY_RULES


def _rec(date, amount, merchant, category, account="Acct", raw=""):
    """A minimal analysis record (what analyze/detect_recurring consume)."""
    return {"date": date, "amount": amount, "merchant": merchant,
            "category": category, "account": account,
            "raw_description": raw or merchant}


class TestAmountParsing(unittest.TestCase):
    def test_currency_and_separators(self):
        self.assertAlmostEqual(_parse_amount("$1,234.56"), 1234.56)

    def test_parentheses_are_negative(self):
        self.assertAlmostEqual(_parse_amount("(45.00)"), -45.00)

    def test_leading_minus(self):
        self.assertAlmostEqual(_parse_amount("-12.30"), -12.30)

    def test_cr_is_positive_dr_is_negative(self):
        self.assertAlmostEqual(_parse_amount("12.30 CR"), 12.30)
        self.assertAlmostEqual(_parse_amount("50.00 DR"), -50.00)

    def test_blank_and_garbage(self):
        self.assertIsNone(_parse_amount(""))
        self.assertIsNone(_parse_amount("  "))
        self.assertIsNone(_parse_amount("n/a"))


class TestDateParsing(unittest.TestCase):
    def test_common_formats(self):
        self.assertEqual(_parse_date("2024-01-15"), "2024-01-15")
        self.assertEqual(_parse_date("01/15/2024"), "2024-01-15")
        self.assertEqual(_parse_date("1/5/24"), "2024-01-05")

    def test_ofx_timestamp(self):
        self.assertEqual(_parse_date("20240115120000[-8:PST]"), "2024-01-15")

    def test_unparseable(self):
        self.assertIsNone(_parse_date("not a date"))
        self.assertIsNone(_parse_date(""))


class TestMerchantCleaning(unittest.TestCase):
    def test_known_brands_canonicalize(self):
        self.assertEqual(clean_merchant("AMZN MKTP US*2X9 AMZN.COM/BILL WA"), "Amazon")
        self.assertEqual(clean_merchant("NETFLIX.COM 866-579-7172 CA"), "Netflix")

    def test_noise_prefix_and_trailing_geo_stripped(self):
        out = clean_merchant("TST* THE CORNER CAFE  SAN FRANCISCO CA 94016")
        self.assertNotIn("TST", out)
        self.assertNotIn("94016", out)
        self.assertTrue(out)

    def test_never_returns_empty(self):
        self.assertTrue(clean_merchant(""))
        self.assertTrue(clean_merchant("   "))


class TestFingerprintDedup(unittest.TestCase):
    def test_fitid_drives_identity(self):
        a = Txn("Card", "2024-01-01", -10.0, "x", "f.ofx", fitid="ABC123")
        b = Txn("Card", "2024-06-09", -99.0, "y", "f.ofx", fitid="ABC123")
        self.assertEqual(a.fingerprint(), b.fingerprint())

    def test_composite_key_when_no_fitid(self):
        a = Txn("Card", "2024-01-01", -10.0, "x", "f.csv", merchant="Shop", occ=1)
        b = Txn("Card", "2024-01-01", -10.0, "x", "f.csv", merchant="Shop", occ=1)
        self.assertEqual(a.fingerprint(), b.fingerprint())

    def test_same_day_repeat_kept_distinct_by_occ(self):
        a = Txn("Card", "2024-01-01", -10.0, "x", "f.csv", merchant="Shop", occ=1)
        b = Txn("Card", "2024-01-01", -10.0, "x", "f.csv", merchant="Shop", occ=2)
        self.assertNotEqual(a.fingerprint(), b.fingerprint())


class TestCategorize(unittest.TestCase):
    def test_expense_keyword(self):
        self.assertEqual(categorize("Starbucks", "STARBUCKS 123", -5.0, RULES),
                         "Coffee")

    def test_income_keyword_positive(self):
        self.assertEqual(categorize("", "PAYROLL DIRECT DEPOSIT", 4200.0, RULES),
                         "Income")

    def test_transfer_keyword_not_counted_as_spend(self):
        self.assertEqual(categorize("", "Online Transfer to Savings", -500.0, RULES),
                         "Transfers")

    def test_source_category_transfer_wins(self):
        # Monarch/Copilot exports: a credit-card payment is moving money, not spending.
        self.assertEqual(
            categorize("Chase", "AUTOPAY", -300.0, RULES,
                       source_category="Credit Card Payment"),
            "Transfers")

    def test_balance_transfer_artifact_is_neutralized(self):
        self.assertEqual(
            categorize("Card", "Promotional APR Balance Transfer", -1000.0, RULES),
            "Transfers")

    def test_positive_at_expense_merchant_is_not_miscounted_as_that_category(self):
        # A refund (positive) at a coffee shop must not register as Coffee spend.
        self.assertEqual(categorize("Starbucks", "REFUND", 5.0, RULES), "Income")


class TestCsvParsing(unittest.TestCase):
    def _write(self, text):
        f = Path(tempfile.mkstemp(suffix=".csv")[1])
        f.write_text(text, encoding="utf-8")
        return f

    def test_signed_amount_column(self):
        f = self._write("Date,Description,Amount\n"
                        "2024-01-02,STARBUCKS STORE 123,-5.25\n"
                        "2024-01-03,PAYROLL,2000.00\n")
        txns, warnings = parse_csv(f, "Checking")
        self.assertEqual(len(txns), 2)
        self.assertAlmostEqual(txns[0].amount, -5.25)
        self.assertAlmostEqual(txns[1].amount, 2000.00)

    def test_debit_credit_columns(self):
        f = self._write("Date,Description,Debit,Credit\n"
                        "01/02/2024,COFFEE,5.25,\n"
                        "01/03/2024,REFUND,,9.99\n")
        txns, _ = parse_csv(f, "Card")
        self.assertAlmostEqual(txns[0].amount, -5.25)   # debit = money out
        self.assertAlmostEqual(txns[1].amount, 9.99)    # credit = money in

    def test_monarch_columns_thread_merchant_account_category(self):
        f = self._write("Date,Merchant,Category,Account,Amount\n"
                        "2024-01-02,Trader Joe's,Groceries,Amex,-42.10\n")
        txns, _ = parse_csv(f, "ignored-folder-name")
        self.assertEqual(txns[0].merchant, "Trader Joe's")   # pre-cleaned, trusted
        self.assertEqual(txns[0].account, "Amex")            # per-row account wins
        self.assertEqual(txns[0].source_category, "Groceries")

    def test_unrecognized_columns_skip_gracefully(self):
        f = self._write("Foo,Bar\n1,2\n")
        txns, warnings = parse_csv(f, "X")
        self.assertEqual(txns, [])
        self.assertTrue(warnings)


class TestOfxParsing(unittest.TestCase):
    def test_minimal_block_with_fitid(self):
        ofx = ("<OFX><BANKTRANLIST>"
               "<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20240115120000"
               "<TRNAMT>-23.45<FITID>X-9001<NAME>WHOLEFOODS"
               "</STMTTRN></BANKTRANLIST></OFX>")
        f = Path(tempfile.mkstemp(suffix=".ofx")[1])
        f.write_text(ofx, encoding="utf-8")
        txns, _ = parse_ofx(f, "Checking")
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].fitid, "X-9001")
        self.assertAlmostEqual(txns[0].amount, -23.45)
        self.assertEqual(txns[0].date, "2024-01-15")


class TestBalancesExport(unittest.TestCase):
    def test_header_detection(self):
        self.assertTrue(_looks_like_balances(["Date", "Balance", "Account"]))
        self.assertFalse(_looks_like_balances(["Date", "Amount", "Account"]))

    def test_parse_rows(self):
        f = Path(tempfile.mkstemp(suffix=".csv")[1])
        f.write_text("Date,Account,Balance\n2024-01-31,Checking,1500.00\n"
                     "2024-01-31,Card,-2000.00\n", encoding="utf-8")
        rows = parse_balances(f)
        self.assertIn(("2024-01-31", "Checking", 1500.00), rows)
        self.assertIn(("2024-01-31", "Card", -2000.00), rows)


class TestAnalyze(unittest.TestCase):
    def test_sign_convention_and_transfers_excluded(self):
        rows = [
            _rec("2024-01-05", 5000.0, "Employer", "Income"),
            _rec("2024-01-06", -100.0, "Trader Joe's", "Groceries"),
            _rec("2024-01-07", -800.0, "Landlord", "Housing"),
            # A transfer in and out must not count as income or expense.
            _rec("2024-01-08", 1000.0, "Self", "Transfers"),
            _rec("2024-01-09", -1000.0, "Self", "Transfers"),
        ]
        a = analyze(rows)
        self.assertFalse(a["empty"])
        self.assertAlmostEqual(a["summary"]["income"], 5000.0)
        self.assertAlmostEqual(a["summary"]["expense"], 900.0)
        self.assertAlmostEqual(a["summary"]["net"], 4100.0)

    def test_empty(self):
        self.assertTrue(analyze([])["empty"])


class TestRecurring(unittest.TestCase):
    def test_monthly_subscription_detected(self):
        rows = [_rec(f"2024-{m:02d}-15", -15.99, "Netflix", "Streaming")
                for m in range(1, 7)]
        found = detect_recurring(rows, _d("2024-06-20"))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].merchant, "Netflix")
        self.assertEqual(found[0].cadence, "monthly")
        self.assertTrue(found[0].active)

    def test_irregular_is_not_recurring(self):
        rows = [_rec("2024-01-03", -8.0, "Random Shop", "Shopping"),
                _rec("2024-02-19", -140.0, "Random Shop", "Shopping"),
                _rec("2024-05-02", -3.0, "Random Shop", "Shopping")]
        self.assertEqual(detect_recurring(rows, _d("2024-06-20")), [])


class TestDebts(unittest.TestCase):
    def test_infer_apr_from_one_period(self):
        self.assertAlmostEqual(infer_apr(20.0, 1000.0), 24.0, places=2)
        self.assertIsNone(infer_apr(0.0, 1000.0))
        self.assertIsNone(infer_apr(20.0, 0.0))

    def test_payoff_finishes_and_accrues_interest(self):
        d = Debt("Visa", "credit card", 1000.0, 24.0, 25.0)
        res = simulate_payoff([d], 200.0, "avalanche")
        self.assertTrue(res.finished)
        self.assertTrue(res.covers_minimums)
        self.assertGreater(res.total_interest, 0.0)
        self.assertEqual(res.order, ["Visa"])

    def test_avalanche_targets_highest_apr_first(self):
        high = Debt("HighAPR", "credit card", 1000.0, 25.0, 25.0)
        low = Debt("LowAPR", "credit card", 1000.0, 5.0, 25.0)
        res = simulate_payoff([high, low], 250.0, "avalanche")
        self.assertEqual(res.order[0], "HighAPR")

    def test_snowball_targets_smallest_balance_first(self):
        big = Debt("Big", "credit card", 4000.0, 10.0, 80.0)
        small = Debt("Small", "credit card", 500.0, 10.0, 25.0)
        res = simulate_payoff([big, small], 400.0, "snowball")
        self.assertEqual(res.order[0], "Small")

    def test_plan_paths_intensity_is_monotonic(self):
        d = Debt("Visa", "credit card", 6000.0, 22.0, 120.0)
        plan = plan_paths([d], monthly_leftover=300.0,
                          recoverable_waste_monthly=100.0)
        self.assertTrue(plan["has_debts"])
        self.assertFalse(plan["minimums_never_payoff"])     # min > interest here
        self.assertIsNotNone(plan["paths"]["easy"]["interest_saved"])
        easy = plan["paths"]["easy"]["extra"]
        avg = plan["paths"]["average"]["extra"]
        agg = plan["paths"]["aggressive"]["extra"]
        self.assertLessEqual(easy, avg)
        self.assertLessEqual(avg, agg)
        # More money down => no later than the gentler plan.
        self.assertLessEqual(plan["paths"]["aggressive"]["avalanche"].months,
                             plan["paths"]["easy"]["avalanche"].months)

    def test_minimum_only_never_payoff_is_flagged_not_inflated(self):
        # 24% APR with a 2% minimum: the minimum exactly covers the interest, so
        # minimums-only never clears it. We must flag that, not quote a huge "saved".
        d = Debt("Trap Card", "credit card", 5000.0, 24.0, 100.0)
        plan = plan_paths([d], monthly_leftover=0.0, recoverable_waste_monthly=0.0)
        self.assertTrue(plan["minimums_never_payoff"])
        self.assertIsNone(plan["paths"]["easy"]["interest_saved"])
        self.assertIsNone(plan["paths"]["easy"]["months_saved"])
        self.assertAlmostEqual(plan["minimums_annual_interest"], 1200.0, delta=1.0)

    def test_infer_aprs_from_records_unlocks_a_card(self):
        d = Debt("Card", "other", 1000.0, 0.0, 0.0)        # unknown APR + min
        records = [
            _rec("2024-01-20", -20.0, "Interest Charge", "Fees & Interest", "Card"),
            _rec("2024-02-20", -20.0, "Interest Charge", "Fees & Interest", "Card"),
        ]
        balances = [("2024-01-31", "Card", -1000.0),
                    ("2024-02-29", "Card", -1000.0)]
        n = infer_aprs_from_records([d], records, balances, months_span=2)
        self.assertEqual(n, 1)
        self.assertAlmostEqual(d.apr, 24.0, delta=1.0)
        self.assertTrue(d.apr_estimated)
        self.assertGreater(d.min_payment, 0.0)             # payoff now unlockable
        self.assertEqual(d.kind, "credit card")            # reclassified as revolving


class TestPlanning(unittest.TestCase):
    def test_emergency_fund_math(self):
        ef = emergency_fund(1000.0, 5000.0)
        self.assertAlmostEqual(ef["target_min"], 3000.0)
        self.assertAlmostEqual(ef["target_full"], 6000.0)
        self.assertEqual(ef["gap_to_min"], 0.0)            # already past 3 months
        self.assertAlmostEqual(ef["months_covered"], 5.0)

    def test_net_worth_from_balances_splits_assets_and_debts(self):
        nw = net_worth_from_balances({"Checking": 5000.0, "Card": -2000.0})
        self.assertAlmostEqual(nw["total_assets"], 5000.0)
        self.assertAlmostEqual(nw["total_debts"], 2000.0)
        self.assertAlmostEqual(nw["net_worth"], 3000.0)

    def test_retirement_projection_grows_and_sets_fi_number(self):
        p = Profile(age=40, target_retirement_age=65, retirement_balance=100_000.0,
                    monthly_retirement_contribution=1000.0, expected_return_pct=7.0,
                    inflation_pct=2.5)
        proj = retirement_projection(p, essentials_monthly=4000.0)
        self.assertGreater(proj["projected_balance"], 100_000.0)
        self.assertAlmostEqual(proj["fi_number"], 4000.0 * 12 * 25)

    def test_projection_is_reported_in_todays_dollars(self):
        # The real (today's-dollars) balance must be below the nominal face value,
        # otherwise we'd be comparing future dollars to a today's-dollars FI number.
        p = Profile(age=35, target_retirement_age=65, retirement_balance=50_000.0,
                    monthly_retirement_contribution=800.0, expected_return_pct=7.0,
                    inflation_pct=2.5)
        proj = retirement_projection(p, essentials_monthly=4000.0)
        self.assertTrue(proj["in_todays_dollars"])
        self.assertLess(proj["projected_balance"],
                        proj["projected_balance_nominal"])
        self.assertLess(proj["real_return_pct"], proj["return_pct"])

    def test_social_security_lowers_the_number_you_need(self):
        base = Profile(age=50, target_retirement_age=67, expected_return_pct=7.0)
        withss = Profile(age=50, target_retirement_age=67, expected_return_pct=7.0,
                         social_security_monthly=2000.0)
        fi_base = retirement_projection(base, 4000.0)["fi_number"]
        fi_ss = retirement_projection(withss, 4000.0)["fi_number"]
        self.assertAlmostEqual(fi_base, 4000.0 * 12 * 25)
        self.assertAlmostEqual(fi_ss, (4000.0 - 2000.0) * 12 * 25)
        self.assertLess(fi_ss, fi_base)

    def test_full_fi_uses_total_spend_lean_uses_essentials(self):
        p = Profile(age=45, target_retirement_age=65, expected_return_pct=7.0)
        proj = retirement_projection(p, essentials_monthly=3000.0,
                                     total_spend_monthly=5000.0)
        self.assertAlmostEqual(proj["fi_number"], 5000.0 * 12 * 25)
        self.assertAlmostEqual(proj["fi_number_lean"], 3000.0 * 12 * 25)


class TestCashflowForecast(unittest.TestCase):
    def _cf(self, nets):
        return [{"month": f"2026-{i+1:02d}", "income": 0, "expense": 0, "net": n}
                for i, n in enumerate(nets)]

    def test_expected_monthly_net_is_median_based(self):
        est = expected_monthly_net(self._cf([100, 200, 300, 400]))
        self.assertAlmostEqual(est["typical"], 250.0)
        self.assertLess(est["lean"], est["typical"])     # lean = lower quartile

    def test_surplus_grows_and_stays_healthy(self):
        cf = cashflow_forecast(5000.0, self._cf([1000] * 6), months=6, cash_floor=0.0)
        self.assertTrue(cf["healthy"])
        self.assertIsNone(cf["shortfall_month"])
        self.assertAlmostEqual(cf["ending_typical"], 11000.0)

    def test_deficit_flags_shortfall_and_runway(self):
        cf = cashflow_forecast(3000.0, self._cf([-1000] * 6), months=6, cash_floor=0.0)
        self.assertFalse(cf["healthy"])
        self.assertIsNotNone(cf["shortfall_month"])
        self.assertEqual(cf["runway_months"], 3)         # 3000 / 1000

    def test_safe_to_spend_math(self):
        s = safe_to_spend(10_000.0, 3000.0, 200.0, 2000.0)
        self.assertAlmostEqual(s["committed"], 5200.0)
        self.assertAlmostEqual(s["safe_to_spend"], 4800.0)
        self.assertFalse(s["negative"])


class TestGoalPlanner(unittest.TestCase):
    def test_required_monthly_and_pace(self):
        goals = [{"name": "Roof", "target": 18000.0, "saved": 2000.0,
                  "target_date": "2027-05-01"}]
        plan = goal_plan(goals, monthly_capacity=1000.0, today=date(2026, 1, 1))
        it = plan["goals"][0]
        self.assertEqual(it["months_left"], 16)
        self.assertAlmostEqual(it["required_monthly"], 1000.0)   # 16000 / 16
        self.assertTrue(it["on_pace"])
        self.assertTrue(plan["affordable"])

    def test_tight_capacity_is_not_on_pace(self):
        goals = [{"name": "Roof", "target": 18000.0, "saved": 2000.0,
                  "target_date": "2027-05-01"}]
        plan = goal_plan(goals, monthly_capacity=500.0, today=date(2026, 1, 1))
        self.assertFalse(plan["goals"][0]["on_pace"])
        self.assertFalse(plan["affordable"])

    def test_dateless_goal_uses_eta(self):
        goals = [{"name": "Cushion", "target": 6000.0, "saved": 0.0,
                  "target_date": ""}]
        plan = goal_plan(goals, monthly_capacity=1000.0, today=date(2026, 1, 1))
        it = plan["goals"][0]
        self.assertIsNone(it["required_monthly"])
        self.assertEqual(it["eta_months"], 7)            # int(6000/1000)+1


class TestMortgageMath(unittest.TestCase):
    def test_standard_payment_matches_known_value(self):
        # 30-yr, 6%, $100k -> ~$599.55/mo (textbook amortization).
        self.assertAlmostEqual(standard_payment(100_000.0, 6.0, 30), 599.55, delta=0.5)

    def test_amortize_finishes_and_extra_saves(self):
        pay = standard_payment(100_000.0, 6.0, 30)
        base = amortize(100_000.0, 6.0, pay)
        faster = amortize(100_000.0, 6.0, pay, extra=200.0)
        self.assertTrue(base["finished"])
        self.assertLess(faster["months"], base["months"])
        self.assertLess(faster["total_interest"], base["total_interest"])

    def test_payment_below_interest_never_finishes(self):
        res = amortize(100_000.0, 12.0, 100.0)           # interest is $1000/mo
        self.assertFalse(res["finished"])
        self.assertIsNone(res["months"])

    def test_mortgage_analysis_options_and_apr_guard(self):
        m = mortgage_analysis("Home", 200_000.0, 4.0)
        self.assertIsNotNone(m)
        self.assertTrue(m["payment_is_estimated"])
        self.assertTrue(all(o["interest_saved"] > 0 for o in m["options"]))
        self.assertGreater(m["options"][-1]["months_saved"], 0)
        self.assertIsNone(mortgage_analysis("NoRate", 200_000.0, 0.0))


class TestTaxInsights(unittest.TestCase):
    def test_single_bracket_and_effective_rate(self):
        t = tax_insights(100_000.0, "single")
        self.assertEqual(t["marginal_rate"], 22.0)       # taxable 85k -> 22% bracket
        self.assertTrue(8.0 < t["effective_rate"] < 22.0)
        self.assertLess(t["effective_rate"], t["marginal_rate"])

    def test_high_income_mfj_is_24_percent(self):
        t = tax_insights(400_000.0, "mfj")
        self.assertEqual(t["marginal_rate"], 24.0)
        self.assertAlmostEqual(t["trad_saving_per_1k"], 240.0)

    def test_zero_income_returns_none(self):
        self.assertIsNone(tax_insights(0.0, "mfj"))


class TestLiquidCash(unittest.TestCase):
    def test_only_cash_accounts_counted(self):
        lc = liquid_cash_from_balances({
            "Credit Union Checking": 3000.0,
            "Regular Savings (...1)": 500.0,
            "MICROSOFT 401(K) PLAN": 1_000_000.0,    # excluded
            "Individual Brokerage (...2)": 5000.0,    # excluded
            "Venture X (...3)": -2000.0,              # negative, excluded
        })
        self.assertAlmostEqual(lc["total"], 3500.0)
        self.assertIn("Credit Union Checking", lc["accounts"])
        self.assertNotIn("MICROSOFT 401(K) PLAN", lc["accounts"])


class TestWindfallComparison(unittest.TestCase):
    def test_comparison_is_ranked_and_picks_a_best(self):
        debts = [Debt("Card", "credit card", 8000.0, 24.0, 160.0)]
        ls = lump_sum_options(5000.0, debts, emergency_gap=4000.0)
        labels = [c["label"] for c in ls["comparison"]]
        dollars = [c["dollars"] for c in ls["comparison"]]
        self.assertEqual(dollars, sorted(dollars, reverse=True))   # ranked desc
        self.assertIn(ls["best"], labels)
        # Against a 24% card, paying debt should be the top guaranteed move.
        self.assertEqual(ls["best"], "Pay down debt")


class TestServeHostGuard(unittest.TestCase):
    def test_localhost_names_allowed(self):
        for h in ("127.0.0.1:8765", "localhost:8765", "[::1]:8765",
                  "127.0.0.1", "LOCALHOST"):
            self.assertTrue(host_is_local(h), h)

    def test_foreign_or_missing_host_rejected(self):
        for h in ("evil.com:8765", "192.168.1.5:8765", "attacker.example", ""):
            self.assertFalse(host_is_local(h), repr(h))


class TestServeCsrfGuard(unittest.TestCase):
    def test_cross_site_sec_fetch_blocked(self):
        self.assertTrue(is_cross_site_post("cross-site", None))
        self.assertTrue(is_cross_site_post("Cross-Site", "http://127.0.0.1:8765"))

    def test_same_origin_sec_fetch_allowed(self):
        for sfs in ("same-origin", "same-site", "none"):
            self.assertFalse(is_cross_site_post(sfs, None), sfs)

    def test_foreign_origin_blocked_when_no_sec_fetch(self):
        for o in ("https://evil.com", "http://attacker.example:9000",
                  "https://127.0.0.1.evil.com"):
            self.assertTrue(is_cross_site_post(None, o), o)

    def test_local_origin_allowed_when_no_sec_fetch(self):
        for o in ("http://127.0.0.1:8765", "http://localhost:8765",
                  "http://[::1]:8765"):
            self.assertFalse(is_cross_site_post(None, o), o)

    def test_no_signal_is_allowed(self):
        # A genuine same-origin POST from an old browser sends neither header.
        self.assertFalse(is_cross_site_post(None, None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
