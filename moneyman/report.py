"""Builds the dashboard: a single self-contained .html file.

Everything (styles, charts, scripts) is inlined, so the report opens with no
internet connection and references nothing external.
"""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from . import __version__, charts
from .config import CHECKLIST
from .people import SHARED


def _esc(s) -> str:
    return html.escape(str(s))


def _money(x: float, signed: bool = False) -> str:
    if signed:
        return ("-" if x < 0 else "+") + f"${abs(x):,.2f}"
    return f"${x:,.2f}"


def _m0(x: float) -> str:
    return f"${x:,.0f}"


def _mc(x: float) -> str:
    """Compact money that fits in small boxes: $2.04M, $190k, $1,234."""
    a = abs(x)
    sign = "-" if x < 0 else ""
    if a >= 1_000_000:
        return f"{sign}${a/1e6:.2f}M"
    if a >= 100_000:
        return f"{sign}${a/1e3:.0f}k"
    if a >= 10_000:
        return f"{sign}${a/1e3:.1f}k"
    return f"{sign}${a:,.0f}"


CSS = """
:root{--bg:#f4f6fb;--card:#fff;--ink:#1f2733;--muted:#6b7785;--line:#e6eaf0;
--accent:#4f8cff;--green:#1f9d6b;--red:#e0524a;--amber:#c98a12;--purple:#7c5cfc;}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
background:var(--bg);color:var(--ink);line-height:1.45}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px 64px}
header.top{background:linear-gradient(120deg,#2b5dd6,#4f8cff 55%,#34c38f);
color:#fff;padding:30px 0 26px;margin-bottom:-26px}
header.top .wrap{padding-bottom:0}
.brand{font-size:26px;font-weight:700}
.brand small{font-weight:400;opacity:.9}
.badges{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}
.badge{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.35);
padding:4px 10px;border-radius:999px;font-size:12.5px}
.subtle{color:var(--muted);font-size:13px}
h2{font-size:19px;margin:38px 0 6px;display:flex;align-items:center;gap:8px}
.lede{color:var(--muted);font-size:13.5px;margin:0 0 12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;
margin-top:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:16px 18px;box-shadow:0 1px 2px rgba(20,30,50,.04);min-width:0;overflow-wrap:anywhere}
.kpi .label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.3px}
.kpi .value{font-size:clamp(18px,2.6vw,23px);font-weight:700;margin-top:4px;
line-height:1.15;overflow-wrap:anywhere}
.green{color:var(--green)} .red{color:var(--red)} .amber{color:var(--amber)} .purple{color:var(--purple)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:18px 20px;box-shadow:0 1px 2px rgba(20,30,50,.04)}
.grid2{display:grid;grid-template-columns:1.3fr 1fr;gap:16px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:820px){.grid2,.grid3{grid-template-columns:1fr}}
.intro{background:#f0f7ff;border:1px solid #d8e8ff;border-radius:12px;padding:14px 16px;
font-size:14px;color:#2b3a4a}
.insight{display:flex;gap:14px;padding:14px 16px;border-radius:12px;border:1px solid var(--line);
background:var(--card);margin-bottom:10px;border-left-width:5px}
.insight.high{border-left-color:var(--red)}.insight.medium{border-left-color:var(--amber)}
.insight.low{border-left-color:var(--accent)}
.insight .ico{font-size:22px}.insight .t{font-weight:650}
.insight .d{color:var(--muted);font-size:13.5px;margin-top:3px}
.insight ul{margin:8px 0 0;padding-left:18px;font-size:13px;color:#445}
.impact{margin-left:auto;background:#eef4ff;color:#2b5dd6;border-radius:999px;
padding:4px 11px;font-weight:650;font-size:13px;height:fit-content;white-space:nowrap}
table{width:100%;border-collapse:collapse;font-size:13.5px;table-layout:fixed}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);
overflow-wrap:anywhere;vertical-align:top}
th{font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:var(--muted);cursor:pointer;
position:sticky;top:0;background:var(--card)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{font-size:11.5px;padding:2px 8px;border-radius:999px;background:#eef2f7;color:#4a5568}
.pill.on{background:#e6f6ee;color:#1f9d6b}.pill.off{background:#fdeceb;color:#e0524a}
.pill.apr{background:#fde7e6;color:#c0392b;font-weight:700}
.pill.est{background:#fff6e5;color:#b7791f}
.legend{display:flex;flex-direction:column;gap:6px;font-size:13px;margin-top:6px}
.legend .row{display:flex;align-items:center;gap:8px}
.dot{width:11px;height:11px;border-radius:3px;flex:none;display:inline-block}
.search{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;
font-size:14px;margin:6px 0 12px}
.tablewrap{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:12px}
svg.line,svg.bars,svg.hbars,svg.donut{width:100%;height:auto}
.grid{stroke:#eef1f5;stroke-width:1}.axis{font-size:10px;fill:#9aa6b2}
.donut-total{font-size:20px;font-weight:700;fill:#1f2733}.donut-sub{font-size:11px;fill:#9aa6b2}
.hbar-label{font-size:12.5px;fill:#3a4654}.hbar-val{font-size:12px;fill:#6b7785}
.plan{border:1px solid var(--line);border-radius:14px;padding:16px;background:var(--card)}
.plan.best{border-color:#34c38f;box-shadow:0 0 0 2px rgba(52,195,143,.18)}
.plan .tier{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--muted)}
.plan .big{font-size:22px;font-weight:750;margin:4px 0}
.plan .save{color:var(--green);font-weight:650;font-size:13px}
.step{display:flex;gap:12px;padding:12px 14px;border:1px solid var(--line);border-radius:12px;
margin-bottom:9px;background:var(--card)}
.step .mark{font-size:18px;flex:none;width:24px;text-align:center}
.step.done{border-left:5px solid var(--green)}
.step.partial{border-left:5px solid var(--amber)}
.step.todo{border-left:5px solid var(--accent)}
.step.na{opacity:.55}
.step .t{font-weight:650}.step .a{font-size:13.5px;margin:2px 0}
.step .w{font-size:12.5px;color:var(--muted)}.step .h{font-size:12.5px;color:#2b5dd6;margin-top:2px}
.check{display:flex;align-items:flex-start;gap:10px;padding:7px 0;border-bottom:1px solid var(--line);font-size:13.5px}
.gauge{height:12px;border-radius:999px;background:#e9eef5;overflow:hidden;margin:6px 0}
.gauge>div{height:100%;background:linear-gradient(90deg,#4f8cff,#34c38f)}
.prompt{background:#fffdf5;border:1px dashed #e7d9a8;border-radius:12px;padding:14px 16px;font-size:13.5px}
details{margin-top:14px;border-top:1px solid var(--line);padding-top:6px}
details>summary{cursor:pointer;font-size:17px;font-weight:650;padding:8px 0;list-style:none}
details>summary::-webkit-details-marker{display:none}
details>summary:before{content:"▸ ";color:var(--accent)}
details[open]>summary:before{content:"▾ "}
.summary-box{background:linear-gradient(120deg,#f0f7ff,#eafaf2);border:1px solid #d8e8ff;
border-radius:16px;padding:20px 22px;font-size:16px;line-height:1.6}
.summary-box b{color:#1f2733}
.prio{border:1px solid var(--line);border-radius:12px;margin-bottom:9px;
background:var(--card);border-left-width:5px;overflow:hidden}
.prio.p1{border-left-color:var(--red)}.prio.p2{border-left-color:var(--amber)}
.prio.p3{border-left-color:var(--accent)}
.prio>summary{display:flex;gap:13px;align-items:flex-start;padding:13px 16px;
cursor:pointer;list-style:none}
.prio>summary::-webkit-details-marker{display:none}
.prio>summary:hover{background:#f7f9fc}
.prio .rank{font-weight:750;font-size:16px;color:var(--accent);width:18px;flex:none}
.prio .t{font-weight:650}.prio .a{font-size:13.5px;color:var(--muted);margin-top:2px}
.prio .chev{color:var(--muted);font-size:12px;margin-top:4px}
.prio[open] .chev{transform:rotate(90deg)}
.drill{padding:2px 16px 14px 47px}
.drill .subtle{margin-top:6px}
.editbox{background:#fbfdff;border:1px solid #d8e8ff}
.editbox>summary{font-size:17px;font-weight:700;color:#2b5dd6}
.editgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin:6px 0}
.ef{display:flex;flex-direction:column;font-size:12.5px;color:var(--muted)}
.ef input,.ef select{margin-top:3px;padding:7px 9px;border:1px solid var(--line);
border-radius:8px;font-size:14px;color:var(--ink)}
input.mini{width:90px;padding:5px 7px;border:1px solid var(--line);border-radius:7px}
.savebtn{margin-top:12px;background:#2b5dd6;color:#fff;border:0;border-radius:9px;
padding:10px 18px;font-size:14px;font-weight:600;cursor:pointer}
.savebtn:hover{background:#1f49b0}
.saved{background:#e6f6ee;border:1px solid #bfead4;color:#1f7a4d;border-radius:10px;
padding:10px 14px;margin-bottom:12px;font-size:14px}
.note{font-size:13px;color:var(--muted);background:#fff;border:1px dashed var(--line);border-radius:12px;padding:14px 16px}
.foot{margin-top:40px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:12.5px}
.tag{font-size:11px;background:#eef2f7;color:#5a6675;border-radius:6px;padding:1px 6px;margin-left:6px}
/* tabbed-app navigation (offline, vanilla JS) */
.nav{position:sticky;top:0;z-index:30;background:rgba(255,255,255,.92);
backdrop-filter:blur(8px);border-bottom:1px solid var(--line);box-shadow:0 1px 6px rgba(20,30,50,.04)}
.nav-inner{display:flex;gap:4px;overflow-x:auto;padding:8px 20px;max-width:1080px;margin:0 auto}
.navtab{border:0;background:transparent;color:var(--muted);font-size:14px;font-weight:600;
padding:9px 13px;border-radius:10px;cursor:pointer;white-space:nowrap;transition:background .12s}
.navtab:hover{background:#f0f4fa;color:var(--ink)}
.navtab.active{background:#eaf1ff;color:#2b5dd6}
.tab{display:block}
body.tabbed .tab{display:none;animation:fade .18s ease}
body.tabbed .tab.active{display:block}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.cards.hero .card{cursor:default}
.cards.hero .card.jump{cursor:pointer;transition:box-shadow .12s,transform .12s}
.cards.hero .card.jump:hover{box-shadow:0 4px 14px rgba(20,30,50,.10);transform:translateY(-1px)}
.tabintro{color:var(--muted);font-size:13.5px;margin:2px 0 4px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
input.pin{width:100%;padding:6px 8px;border:1px solid var(--line);border-radius:7px;
font-size:13.5px;color:var(--ink)}
.person-sub{font-size:13px;color:var(--muted);margin-top:2px}
/* drag-and-drop "who is this for" board */
.board{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:12px}
.pcol{background:#f7f9fc;border:1px solid var(--line);border-radius:12px;padding:8px;
display:flex;flex-direction:column}
.pcol-h{font-weight:700;font-size:13px;display:flex;justify-content:space-between;
align-items:center;gap:6px;padding:4px 6px 8px;border-bottom:1px solid var(--line);margin-bottom:7px}
.pcol-total{color:var(--muted);font-weight:600;font-variant-numeric:tabular-nums}
.cards-col{display:flex;flex-direction:column;gap:6px;min-height:46px;flex:1}
.mcard{background:#fff;border:1px solid var(--line);border-radius:9px;padding:7px 9px;
cursor:grab;box-shadow:0 1px 2px rgba(20,30,50,.05)}
.mcard:active{cursor:grabbing}
.mc-name{font-size:12.5px;font-weight:600;overflow-wrap:anywhere}
.mc-amt{font-size:12px;color:var(--muted)}
.movesel{margin-top:5px;width:100%;font-size:11.5px;padding:3px 4px;border:1px solid var(--line);
border-radius:6px;color:var(--ink);background:#fff}
.pcol.dragover{outline:2px dashed var(--accent);outline-offset:-2px;background:#eef4ff}
"""

JS = """
function mmFilter(id,q){var t=document.getElementById(id);q=q.toLowerCase();
for(var i=0;i<t.rows.length;i++){var r=t.rows[i];
r.style.display=r.innerText.toLowerCase().indexOf(q)>-1?'':'none';}}
function mmSort(tid,col,numeric){var t=document.getElementById(tid);
var rows=Array.prototype.slice.call(t.rows);
var dir=t.getAttribute('data-d'+col)==='asc'?-1:1;t.setAttribute('data-d'+col,dir===1?'asc':'desc');
rows.sort(function(a,b){var x=a.cells[col].getAttribute('data-v')||a.cells[col].innerText;
var y=b.cells[col].getAttribute('data-v')||b.cells[col].innerText;
if(numeric){return ((parseFloat(x)||0)-(parseFloat(y)||0))*dir;}return x.localeCompare(y)*dir;});
rows.forEach(function(r){t.appendChild(r);});}
function mmTab(id){var s=document.getElementsByClassName('tab');
for(var i=0;i<s.length;i++){s[i].classList.remove('active');}
var n=document.getElementsByClassName('navtab');
for(var j=0;j<n.length;j++){n[j].classList.remove('active');}
var t=document.getElementById('tab-'+id),b=document.getElementById('nav-'+id);
if(t){t.classList.add('active');}if(b){b.classList.add('active');}
window.scrollTo(0,0);}
function mmAllow(e){e.preventDefault();e.currentTarget.classList.add('dragover');}
function mmLeave(e){e.currentTarget.classList.remove('dragover');}
function mmDrag(e,i){e.dataTransfer.setData('text',i);e.dataTransfer.effectAllowed='move';}
function mmDrop(e){e.preventDefault();var col=e.currentTarget;col.classList.remove('dragover');
mmPlace(e.dataTransfer.getData('text'),col.getAttribute('data-person'),col);}
function mmMove(i,person){var c=document.querySelectorAll('.pcol');for(var k=0;k<c.length;k++){
if(c[k].getAttribute('data-person')===person){mmPlace(i,person,c[k]);return;}}}
function mmPlace(i,person,col){var card=document.getElementById('card'+i);if(!card)return;
col.querySelector('.cards-col').appendChild(card);
var h=document.getElementById('p'+i);if(h)h.value=person;
var s=card.querySelector('.movesel');if(s)s.value=person;mmTotals();}
function mmTotals(){var cols=document.getElementsByClassName('pcol');
for(var c=0;c<cols.length;c++){var sum=0,cards=cols[c].getElementsByClassName('mcard');
for(var k=0;k<cards.length;k++){sum+=parseFloat(cards[k].getAttribute('data-amt'))||0;}
var t=cols[c].querySelector('.pcol-total');if(t)t.textContent='$'+Math.round(sum).toLocaleString();}}
document.addEventListener('DOMContentLoaded',function(){document.body.classList.add('tabbed');
if(document.getElementById('assignform')){mmTotals();}});
"""


# --------------------------------------------------------------------------- #
# Section builders
# --------------------------------------------------------------------------- #
def _kpi(label, value, cls="", tab=""):
    extra = (f' jump" onclick="mmTab(\'{tab}\')' if tab else "")
    return (f'<div class="card kpi{extra}"><div class="label">{_esc(label)}</div>'
            f'<div class="value {cls}">{value}</div></div>')


def _checklist_section(intake: dict) -> str:
    mark = {"done": "✅", "partial": "◐", "missing": "⬜"}
    rows = ""
    for it in intake["items"]:
        req = "" if it["required"] else '<span class="tag">optional</span>'
        rows += (f'<div class="check"><div>{mark.get(it["status"],"⬜")}</div>'
                 f'<div><b>{_esc(it["label"])}</b>{req}<br>'
                 f'<span class="subtle">{_esc(it["why"])}</span></div></div>')
    pct = intake["completeness"]
    nxt = ""
    if intake["next_steps"]:
        items = "".join(f"<li>{_esc(s['label'])}</li>" for s in intake["next_steps"])
        nxt = (f'<div class="prompt" style="margin-top:12px"><b>To sharpen your plan, '
               f'add next:</b><ul style="margin:6px 0 0">{items}</ul></div>')
    return (f'<div class="grid2"><div class="panel">'
            f'<b>Your data completeness: {pct}%</b>'
            f'<div class="gauge"><div style="width:{pct}%"></div></div>'
            f'<span class="subtle">The more complete your picture, the better the '
            f'insights and the payoff/independence plan below.</span>{nxt}</div>'
            f'<div class="panel">{rows}</div></div>')


def _debts_section(plan: dict) -> str:
    debts = sorted(plan["debts"], key=lambda d: d.apr, reverse=True)
    if not debts:
        return ('<div class="prompt">💳 <b>No debts loaded yet.</b> To unlock your '
                'payoff plan and the “what-if” calculator, open '
                '<code>config\\Accounts-and-Debts.csv</code> and type each balance, '
                'interest rate (APR), and minimum payment. MoneyMan also reads these '
                'from PDF statements automatically when it can.</div>')
    rows = ""
    tot_bal = tot_min = tot_int = 0.0
    for d in debts:
        if d.apr > 0:
            est = '<span class="pill est">est</span>' if d.apr_estimated else ""
            apr_cell = f'<span class="pill apr">{d.apr:.2f}%</span> {est}'
            int_cell = _money(d.monthly_interest)
        else:
            apr_cell = '<span class="pill est">add rate</span>'
            int_cell = "—"
        util = (f'{d.utilization:.0f}%' if d.utilization is not None else "—")
        minc = _money(d.min_payment) if d.min_payment > 0 else "—"
        rows += (f'<tr><td>{_esc(d.name)}</td><td>{_esc(d.kind)}</td>'
                 f'<td class="num" data-v="{d.balance}">{_money(d.balance)}</td>'
                 f'<td class="num">{apr_cell}</td>'
                 f'<td class="num">{minc}</td>'
                 f'<td class="num">{int_cell}</td>'
                 f'<td class="num">{util}</td></tr>')
        tot_bal += d.balance; tot_min += d.min_payment; tot_int += d.monthly_interest
    return (
        f'<div class="panel"><div class="subtle">Sorted by interest rate — your '
        f'highest-rate debt costs you the most and should usually go first. Right now '
        f'you pay about <b>{_money(tot_int)}/month in interest alone</b>.</div>'
        f'<table id="debts" style="margin-top:8px"><thead><tr>'
        f'<th onclick="mmSort(\'debts\',0,false)">Debt</th><th>Type</th>'
        f'<th class="num" onclick="mmSort(\'debts\',2,true)">Balance</th>'
        f'<th class="num" onclick="mmSort(\'debts\',3,true)">APR</th>'
        f'<th class="num">Min/mo</th><th class="num">Interest/mo</th>'
        f'<th class="num">Used</th></tr></thead><tbody>{rows}</tbody>'
        f'<tfoot><tr><td colspan="2"><b>Total owed</b></td>'
        f'<td class="num"><b>{_money(tot_bal)}</b></td><td></td>'
        f'<td class="num"><b>{_money(tot_min)}</b></td>'
        f'<td class="num"><b>{_money(tot_int)}</b></td><td></td></tr></tfoot></table></div>')


def _payoff_section(plan: dict) -> str:
    po = plan["payoff"]
    if not po.get("has_debts"):
        return ""
    paths, base = po["paths"], po["baseline"]
    tiers = [("easy", "Easy", "a gentle nudge above minimums"),
             ("average", "Average", "balanced — recommended"),
             ("aggressive", "Aggressive", "debt-free soonest")]
    never = po.get("minimums_never_payoff")
    cards = ""
    for key, name, tagline in tiers:
        p = paths[key]; a = p["avalanche"]
        best = " best" if key == "average" else ""
        feas = "" if a.covers_minimums else '<div class="red" style="font-size:12px">⚠ below your minimums</div>'
        if never or p["interest_saved"] is None:
            save = ('<div class="save">Actually clears it — minimums alone never '
                    'would</div>')
        else:
            save = (f'<div class="save">Saves {_money(p["interest_saved"])} & '
                    f'{p["months_saved"]} months vs minimums</div>')
        cards += (f'<div class="plan{best}"><div class="tier">{name} · {tagline}</div>'
                  f'<div class="big">{_money(a.monthly_budget)}<span class="subtle" '
                  f'style="font-size:13px">/mo</span></div>'
                  f'<div>Debt-free <b>{a.payoff_date}</b> ({a.months} months){feas}</div>'
                  f'<div class="subtle">Interest paid {_money(a.total_interest)}</div>'
                  f'{save}</div>')

    never_html = ""
    if never:
        never_html = (
            f'<div class="intro" style="margin-top:14px;background:#fff4f4;'
            f'border-color:#f3c2c2">⚠️ <b>Paying only the minimums never clears this '
            f'debt.</b> At these rates the minimum barely covers the interest, so the '
            f'balance would hang on for decades while you pay about '
            f'<b>{_money(po.get("minimums_annual_interest", 0))}/year</b> in interest. '
            f'Any of the plans above actually gets you to $0 — that\'s the whole point '
            f'of putting a little extra on top.</div>')

    order = po["paths"]["average"]["avalanche"].order
    debt_by = {d.name: d for d in plan["debts"]}
    order_html = " → ".join(
        f'{i+1}. {_esc(n)} ({debt_by[n].apr:.1f}%)' for i, n in enumerate(order)
        if n in debt_by)
    snow = po["paths"]["average"]["snowball"]
    extra_int = snow.total_interest - po["paths"]["average"]["avalanche"].total_interest

    bot = po["paths"]["average"]["avalanche"].balances_over_time
    line = charts.line(bot, x_label_every=max(1, len(bot) // 8))

    wr = plan.get("waste_redirect")
    waste_html = ""
    if wr and (wr["months_saved"] > 0 or wr["interest_saved"] > 0):
        waste_html = (
            f'<div class="intro" style="margin-top:14px;background:#eafaf2;'
            f'border-color:#bfead4">♻️ <b>Redirect the waste MoneyMan found</b> '
            f'(~{_money(wr["monthly"])}/mo) straight at your debt and you\'re done by '
            f'<b>{wr["payoff_with"]}</b> — about {wr["months_saved"]} months sooner, '
            f'saving {_money(wr["interest_saved"])} in interest. Same income, same '
            f'life — just plugging the leaks.</div>')

    return (
        f'<div class="intro" style="margin-bottom:14px">This is judgment-free. The '
        f'plan uses <b>your</b> numbers: about {_money(po["leftover"])}/mo you have '
        f'left over plus {_money(po["recoverable_waste"])}/mo of waste you could '
        f'redirect. Every path still pays all your minimums — the difference is how '
        f'much extra goes on top. You can change the amount any time.</div>'
        f'<div class="grid3">{cards}</div>'
        f'<div class="panel" style="margin-top:14px"><b>Pay in this order (avalanche '
        f'— cheapest):</b><div style="margin:6px 0 4px">{order_html}</div>'
        f'<div class="subtle">Prefer quick wins? The “snowball” method clears the '
        f'smallest balance first — it costs about {_money(max(0,extra_int))} more in '
        f'interest but can feel more motivating. Both are valid; pick what keeps you '
        f'going.</div>'
        f'<div style="margin-top:10px"><b>Your balance on the Average plan:</b>{line}</div></div>'
        f'{never_html}{waste_html}')


def _networth_section(plan: dict) -> str:
    nw = plan["net_worth"]
    rp = plan["retirement"]
    if nw["total_assets"] <= 0 and nw["total_debts"] <= 0:
        return ('<div class="prompt">Add a balances export (or fill in '
                '<code>config\\My-Profile.csv</code>: savings, retirement, home value, '
                'cars) to see your net worth and a retirement projection.</div>')
    bars = charts.hbars([(k, v, "") for k, v in list(nw["assets"].items())[:12]]) \
        if nw["assets"] else ""
    as_of = (f' · as of {_esc(nw["as_of"])}' if nw.get("as_of") else "")
    trend = plan.get("net_worth_trend") or []
    trend_block = ""
    if len(trend) >= 3:
        vals = [v for _, v in trend]
        trend_block = (f'<div class="panel" style="margin-top:14px">'
                       f'<b>📈 Net worth over time</b> '
                       f'<span class="subtle">({trend[0][0]} → {trend[-1][0]}, monthly)'
                       f'</span>{charts.line(vals, color="#1f9d6b", x_unit="mo")}</div>')
    nw_cls = "green" if nw["net_worth"] >= 0 else "red"
    fi = rp
    track = ('<span class="green">on track</span>' if fi["on_track"]
             else '<span class="amber">needs attention</span>')
    ytf = f'{fi["years_to_fi"]} yrs' if fi["years_to_fi"] is not None else "—"
    ss = fi.get("social_security_monthly", 0) or 0
    ss_line = (f'<div class="subtle">Includes ~{_money(ss)}/mo Social Security; the '
               f'4% draw on your portfolio covers the rest.</div>' if ss > 0 else
               '<div class="subtle">Tip: add your Social Security estimate (ssa.gov) '
               'in “My info” — it lowers the number you need.</div>')
    lean = fi.get("fi_number_lean")
    lean_line = (f'<div class="subtle">A leaner, essentials-only version is '
                 f'{_money(lean)}.</div>' if lean and lean < fi["fi_number"] else "")
    return (
        f'<div class="grid2"><div class="panel"><div class="kpi">'
        f'<div class="label">Net worth (assets − debts){as_of}</div>'
        f'<div class="value {nw_cls}">{_money(nw["net_worth"])}</div></div>'
        f'<div class="subtle">{_money(nw["total_assets"])} assets · '
        f'{_money(nw["total_debts"])} owed</div>{bars}</div>'
        f'<div class="panel"><b>🎯 Retirement / financial independence</b>'
        f'<div class="subtle">At {fi["return_pct"]:.0f}%/yr ('
        f'~{fi.get("real_return_pct", 0):.1f}% after {fi.get("inflation_pct", 0):.1f}% '
        f'inflation), age {fi["current_age"]}→{fi["target_age"]}. '
        f'<b>All figures in today’s dollars.</b></div>'
        f'<div style="margin-top:8px">Projected nest egg: '
        f'<b>{_money(fi["projected_balance"])}</b> '
        f'(~{_money(fi["projected_income_monthly"])}/mo to spend)</div>'
        f'<div>Your “work-optional” number (25× the spending your savings must '
        f'cover): <b>{_money(fi["fi_number"])}</b></div>{lean_line}'
        f'<div>Reach it in about <b>{ytf}</b> at your current pace — {track}.</div>'
        f'{ss_line}'
        f'<div class="subtle" style="margin-top:6px">Uses the 4% rule, in today’s '
        f'purchasing power. Raising your monthly contribution is the biggest lever '
        f'here.</div></div></div>'
        f'{trend_block}')


def _safe_to_spend_section(plan: dict) -> str:
    s = plan.get("safe_to_spend")
    if not s:
        return ""
    cls = "red" if s["negative"] else "green"
    tip = ("Spending is running ahead of your bills and savings — trim a little, or "
           "lower a set-aside." if s["negative"] else
           "This is yours to spend freely without touching bills or your savings plan.")
    return (
        f'<div class="panel"><div class="kpi"><div class="label">Safe to spend this '
        f'month</div><div class="value {cls}">{_money(s["safe_to_spend"])}</div></div>'
        f'<div class="subtle">≈ <b>{_money(s["weekly"])}/week</b>. {tip}</div>'
        f'<div class="subtle" style="margin-top:6px">Income {_money(s["income"])} − '
        f'essentials {_money(s["essentials"])} − subscriptions '
        f'{_money(s["subscriptions"])} − {_money(s["savings_setaside"])} set aside '
        f'(goals, emergency fund, extra debt payment).</div></div>')


def _cashflow_section(plan: dict) -> str:
    cf = plan.get("cashflow")
    if not cf:
        return ('<div class="subtle">Add a balances export and a few months of '
                'history and MoneyMan will forecast your cash here.</div>')
    vals = [cf["starting_cash"]] + [p["typical"] for p in cf["points"]]
    chart = charts.line(vals, color="#1f9d6b", x_unit="mo")
    if cf["shortfall_month"]:
        banner = (f'<div class="intro" style="background:#fff4f4;border-color:#f3c2c2">'
                  f'⚠️ <b>Heads up:</b> in a normal lean month your cash dips below '
                  f'{_money(cf["cash_floor"])} around <b>{cf["shortfall_month"]}</b>. '
                  f'Building the emergency fund is the fix.</div>')
    elif cf["runway_months"] is not None:
        banner = (f'<div class="intro" style="background:#fff4f4;border-color:#f3c2c2">'
                  f'⚠️ You\'re spending more than you bring in — at this pace the cash '
                  f'on hand lasts about <b>{cf["runway_months"]} months</b>.</div>')
    else:
        banner = (f'<div class="intro" style="background:#eafaf2;border-color:#bfead4">'
                  f'✅ On track: starting at <b>{_money(cf["starting_cash"])}</b>, your '
                  f'cash trends to about <b>{_money(cf["ending_typical"])}</b> in '
                  f'{cf["months"]} months.</div>')
    rows = "".join(
        f'<tr><td>{_esc(p["month"])}</td>'
        f'<td class="num">{_money(p["typical"])}</td>'
        f'<td class="num subtle">{_money(p["lean"])}</td></tr>' for p in cf["points"])
    return (
        f'<p class="lede">Where your checking balance is headed, projected from your '
        f'own recent cash flow (typical month '
        f'<b>{_money(cf["typical_net"])}/mo</b>, a lean month '
        f'{_money(cf["lean_net"])}/mo).</p>{banner}'
        f'<div class="panel"><b>Projected cash (typical month)</b>{chart}</div>'
        f'<div class="panel" style="margin-top:12px"><table><thead><tr><th>Month</th>'
        f'<th class="num">Typical</th><th class="num">Lean month</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></div>')


def _goals_section(plan: dict) -> str:
    g = plan.get("goals")
    if not g or not g["goals"]:
        return ('<div class="subtle">Name what you\'re saving for in '
                '<code>config\\Goals.csv</code> (target amount + date) and MoneyMan '
                'will tell you the monthly amount it takes.</div>')
    rows = ""
    for it in g["goals"]:
        when = _esc(it["target_date"]) if it["target_date"] else "no date"
        if it["required_monthly"] is not None:
            need = f'<b>{_money(it["required_monthly"])}/mo</b>'
            pace = ('<span class="green">on pace</span>' if it["on_pace"]
                    else '<span class="amber">tight</span>')
        else:
            eta = f'{it["eta_months"]} mo' if it["eta_months"] else "—"
            need = f'<span class="subtle">~{eta} at current surplus</span>'
            pace = ""
        rows += (f'<tr><td>{_esc(it["name"])}</td>'
                 f'<td class="num">{_money(it["target"])}</td>'
                 f'<td class="num subtle">{_money(it["saved"])}</td>'
                 f'<td>{when}</td><td class="num">{need}</td><td>{pace}</td></tr>')
    afford = ('<span class="green">your surplus covers them all</span>'
              if g["affordable"] else
              '<span class="amber">they add up to more than your monthly surplus — '
              'stagger the dates or trim a target</span>')
    return (
        f'<p class="lede">Saving with a deadline. Required-monthly is the goal amount '
        f'spread over the time left; together {afford}.</p>'
        f'<div class="panel"><table><thead><tr><th>Goal</th><th class="num">Target</th>'
        f'<th class="num">Saved</th><th>By</th><th class="num">Need/mo</th><th>Pace</th>'
        f'</tr></thead><tbody>{rows}</tbody>'
        f'<tfoot><tr><td colspan="4"><b>Total required / month</b></td>'
        f'<td class="num"><b>{_money(g["required_total"])}</b></td>'
        f'<td class="subtle">of {_money(g["monthly_capacity"])}</td></tr></tfoot>'
        f'</table></div>')


def _mortgage_section(plan: dict) -> str:
    ms = plan.get("mortgages")
    if not ms:
        return ""
    cards = ""
    for m in ms:
        est = (' <span class="subtle">(payment estimated — confirm yours for exact '
               'numbers)</span>' if m["payment_is_estimated"] else "")
        opt_rows = "".join(
            f'<tr><td>+{_money(o["extra"])}/mo</td>'
            f'<td class="num">{o["months_saved"]} mo sooner</td>'
            f'<td class="num green">save {_money(o["interest_saved"])}</td></tr>'
            for o in m["options"])
        cards += (
            f'<div class="panel" style="margin-bottom:12px">'
            f'<b>🏠 {_esc(m["name"])}</b> — {_money(m["balance"])} at {m["apr"]:.2f}%{est}'
            f'<div class="subtle">Payment ~{_money(m["payment"])}/mo · interest right '
            f'now ~{_money(m["monthly_interest"])}/mo · paid off in about '
            f'{m["base_months"]//12} yrs {m["base_months"]%12} mo.</div>'
            f'<table style="margin-top:8px"><thead><tr><th>Pay extra</th>'
            f'<th class="num">Finish</th><th class="num">Interest saved</th></tr>'
            f'</thead><tbody>{opt_rows}</tbody></table></div>')
    return (f'<p class="lede">Extra principal goes straight at the balance, so a little '
            f'each month can cut years and real money off a home loan.</p>{cards}')


def _tax_section(plan: dict) -> str:
    t = plan.get("tax")
    if not t:
        return ""
    fil = {"mfj": "married filing jointly", "single": "single",
           "hoh": "head of household",
           "mfs": "married filing separately"}.get(t["filing"], t["filing"])
    yr = t.get("tax_year")
    yr_txt = f"{yr} " if yr else ""
    return (
        f'<div class="panel"><b>🧾 Your tax picture</b> '
        f'<span class="subtle">({yr_txt}federal estimate, {fil} — not tax advice)</span>'
        f'<div style="margin-top:8px">Marginal bracket <b>{t["marginal_rate"]:.0f}%</b>'
        f' · effective rate ~<b>{t["effective_rate"]:.0f}%</b> · est. federal tax '
        f'~{_money(t["est_federal_tax"])} on {_money(t["gross_income"])}.</div>'
        f'<div style="margin-top:8px">{t["guidance"]}</div>'
        f'<div class="subtle" style="margin-top:6px">Every $1,000 of '
        f'<b>Traditional</b> (pre-tax) retirement contribution lowers this year\'s '
        f'tax by about <b>{_money(t["trad_saving_per_1k"])}</b>.</div></div>')


def _bills_section(plan: dict) -> str:
    bills = plan["bills"]
    if not bills:
        return ""
    total = sum(b["potential_annual"] for b in bills)
    rows = "".join(
        f'<div class="insight low"><div class="ico">💸</div><div style="flex:1">'
        f'<div class="t">{_esc(b["name"])} — about {_money(b["monthly"])}/mo '
        f'({_esc(b["kind"])})</div><div class="d">{_esc(b["tip"])}</div></div>'
        f'<div class="impact">~{_money(b["potential_annual"])}/yr</div></div>'
        for b in bills)
    return (f'<p class="lede">Fixed bills are the easiest savings — a few phone calls, '
            f'no lifestyle change. Estimated room to save: '
            f'<b>{_money(total)}/yr</b>.</p>{rows}')


def _possibilities_section(plan: dict) -> str:
    lumps = plan["lump_sums"]
    if not plan["payoff"].get("has_debts") and not lumps:
        return ""
    cards = ""
    for ls in lumps:
        amt = ls["amount"]
        parts = []
        if ls["debt"]:
            d = ls["debt"]
            parts.append(f'<div>💳 <b>Pay debt:</b> save {_money(d["interest_saved"])} '
                         f'interest & {d["months_saved"]} months '
                         f'(a guaranteed {d["guaranteed_return_pct"]:.0f}% return)</div>')
        if ls["emergency"]:
            e = ls["emergency"]
            parts.append(f'<div>🛟 <b>Emergency fund:</b> add {_money(e["applied"])}'
                         f'{" — fully funds your 3-month cushion" if e["closes_gap"] else ""}</div>')
        iv = ls["invest"]
        parts.append(f'<div>📈 <b>Invest:</b> ~{_money(iv["future_value"])} in '
                     f'{iv["years"]} yrs at {iv["assumed_return_pct"]:.0f}%</div>')
        # Ranked, apples-to-apples dollar comparison (biggest benefit first).
        comp = ls.get("comparison") or []
        comp_html = ""
        if comp:
            crows = "".join(
                f'<tr><td>{"🏆 " if c["label"]==ls.get("best") else ""}'
                f'{_esc(c["label"])}</td>'
                f'<td class="num"><b>{_money(c["dollars"])}</b></td>'
                f'<td class="subtle">{"guaranteed" if c["guaranteed"] else "expected"}'
                f'</td></tr>' for c in comp)
            comp_html = (f'<table style="margin-top:8px;font-size:13px"><thead><tr>'
                         f'<th>Option</th><th class="num">$ benefit</th><th></th></tr>'
                         f'</thead><tbody>{crows}</tbody></table>')
        cards += (f'<div class="plan"><div class="tier">If you had</div>'
                  f'<div class="big purple">{_m0(amt)}</div>'
                  f'{"".join(parts)}{comp_html}'
                  f'<div class="save" style="margin-top:8px">→ {_esc(ls["recommendation"])}</div></div>')
    return (f'<p class="lede">A quick look at the highest-impact use of a windfall — '
            f'a bonus, tax refund, or sale. The table ranks each by the actual dollars '
            f'it puts in your pocket.</p><div class="grid2">{cards}</div>')


def _surprises_section(plan: dict) -> str:
    sur = plan["surprises"]
    rows = ""
    for s in sur:
        chance = "certain" if s["annual_prob"] >= 1 else f'{s["annual_prob"]*100:.0f}% / yr'
        rows += (f'<tr><td>{_esc(s["name"])}</td><td>{_esc(chance)}</td>'
                 f'<td class="num">{_money(s["typical_cost"])}</td>'
                 f'<td class="num"><b>{_money(s["expected_monthly"])}</b></td>'
                 f'<td class="subtle">{_esc(s["basis"])}</td></tr>')
    cars = ""
    for c in plan["cars"]:
        cars += (f'<div class="card"><b>🚗 {_esc(c["name"])}</b><br>'
                 f'<span class="subtle">{c["age"] or "?"} yrs · {c["miles"]:,} mi · '
                 f'{c["repair_risk"]} repair risk</span><br>'
                 f'Repairs: <b>{_money(c["monthly_repair_reserve"])}/mo</b> · '
                 f'Replace in ~{c["years_to_replace"]} yrs: '
                 f'<b>{_money(c["monthly_replace_reserve"])}/mo</b></div>')
    if plan["home"]:
        h = plan["home"]
        cars += (f'<div class="card"><b>🏠 Home</b><br>'
                 f'<span class="subtle">value {_m0(h["home_value"])}</span><br>'
                 f'Maintenance (~1%/yr): <b>{_money(h["monthly_reserve"])}/mo</b></div>')
    car_block = f'<div class="cards" style="margin-top:12px">{cars}</div>' if cars else ""
    no_profile = ("" if (plan["cars"] or plan["home"]) else
                  '<div class="prompt" style="margin-top:10px">Add your cars and home '
                  'to <code>config\\My-Profile.csv</code> for personalized repair and '
                  'replacement reserves.</div>')
    return (
        f'<p class="lede">Irregular costs <i>will</i> happen — the trick is to save a '
        f'little each month so they\'re boring, not emergencies. These are estimates; '
        f'start at the top and fund what you can.</p>'
        f'<div class="panel"><table><thead><tr><th>What</th><th>Chance</th>'
        f'<th class="num">Typical</th><th class="num">Set aside</th><th>Why</th>'
        f'</tr></thead><tbody>{rows}</tbody>'
        f'<tfoot><tr><td colspan="3"><b>Ideal total “save for surprises”</b></td>'
        f'<td class="num"><b>{_money(plan["surprises_total"])}/mo</b></td><td></td>'
        f'</tr></tfoot></table>{car_block}{no_profile}</div>')


def _emergency_section(plan: dict) -> str:
    e = plan["emergency"]
    pct = min(100, round(e["current"] / e["target_min"] * 100)) if e["target_min"] else 0
    return (f'<div class="panel"><b>🛟 Emergency fund</b>'
            f'<div class="subtle">Covers about {e["months_covered"]} month(s) of '
            f'essentials right now.</div>'
            f'<div class="gauge"><div style="width:{pct}%"></div></div>'
            f'<div class="subtle">Have {_money(e["current"])} · 3-month target '
            f'{_money(e["target_min"])} · 6-month {_money(e["target_full"])}'
            f'{" · gap " + _money(e["gap_to_min"]) if e["gap_to_min"]>0 else " · funded!"}</div>'
            f'</div>')


def _foo_section(plan: dict) -> str:
    mark = {"done": "✅", "partial": "◐", "todo": "▢", "na": "—"}
    steps = ""
    for s in plan["foo"]:
        how = f'<div class="h">How: {_esc(s["how"])}</div>' if s["how"] else ""
        steps += (f'<div class="step {s["status"]}"><div class="mark">'
                  f'{mark.get(s["status"],"▢")}</div><div><div class="t">'
                  f'{_esc(s["title"])}</div><div class="a">{_esc(s["action"])}</div>'
                  f'<div class="w">Why: {_esc(s["why"])}</div>{how}</div></div>')
    hid = "".join(f'<li><b>{_esc(t)}</b> — {_esc(d)}</li>' for t, d in plan["hidden"])
    return (
        f'<p class="lede">Getting out of debt is step one. Here\'s a sensible order '
        f'for every dollar after that — to stop just surviving and start building real '
        f'independence. Educational, not personalized investment advice.</p>{steps}'
        f'<div class="panel" style="margin-top:14px"><b>💎 Hidden wealth & benefits to '
        f'track down</b><ul style="margin:8px 0 0;font-size:13.5px;line-height:1.6">'
        f'{hid}</ul></div>')


def _nonmortgage_debts(plan: dict) -> list:
    return [d for d in plan["debts"]
            if "mortgage" not in d.kind and d.balance > 0]


def summary_section(analysis: dict, plan: dict) -> str:
    """One plain-English paragraph: here's your money, the issue, the move."""
    if analysis.get("empty"):
        return ('<div class="summary-box">Add your statements (and a Balances export '
                'if you have one) to the <b>Statements</b> folder, and I\'ll summarize '
                'your whole picture here in plain English.</div>')
    s = analysis["summary"]
    months = max(1, s["months_span"])
    spend = plan.get("expense_monthly", s["expense"] / months)
    inc = plan.get("income_monthly", s["income"] / months)
    net = inc - spend
    nw = plan["net_worth"]
    parts: list[str] = []

    parts.append(f"You're worth about <b>{_mc(nw['net_worth'])}</b>"
                 + (f" (about {_mc(nw['total_assets'])} in assets minus "
                    f"{_mc(nw['total_debts'])} owed)." if nw.get("total_debts") else "."))
    rate = (net / inc * 100) if inc > 0 else 0
    yours = " (your figure)" if plan.get("income_is_override") else ""
    parts.append(f"You bring in roughly <b>{_mc(inc)}/mo</b>{yours} and spend about "
                 f"<b>{_mc(spend)}/mo</b>, keeping {_mc(net)} — a {rate:.0f}% "
                 f"savings rate.")

    nonmort = _nonmortgage_debts(plan)
    if nonmort:
        total = sum(d.balance for d in nonmort)
        known = [d for d in nonmort if d.apr > 0]
        if known:
            mi = sum(d.monthly_interest for d in known)
            hi = max(known, key=lambda d: d.apr)
            parts.append(f"You carry <b>{_mc(total)}</b> of non-mortgage debt costing "
                         f"about <b>{_mc(mi)}/mo in interest</b> — led by "
                         f"{_esc(hi.name)} at {hi.apr:.1f}%.")
        else:
            parts.append(f"You carry <b>{_mc(total)}</b> of non-mortgage debt, but I "
                         f"don't know the interest rates yet — add them (run the "
                         f"interview) and I'll show the true cost and the fastest way out.")

    recov = plan["recoverable_waste"] * 12
    if recov > 200:
        parts.append(f"I spotted about <b>{_mc(recov)}/yr</b> you could likely recover "
                     f"from waste and fixable bills.")

    # The single recommended move.
    move = None
    known_hi = [d for d in nonmort if d.apr >= 12]
    if known_hi:
        hi = max(known_hi, key=lambda d: d.apr)
        move = (f"<b>Smartest next move:</b> attack {_esc(hi.name)} ({hi.apr:.1f}%) "
                f"first — nothing else returns that much, guaranteed.")
    elif nonmort and not [d for d in nonmort if d.apr > 0]:
        move = ("<b>Next move:</b> add your debt interest rates so I can build your "
                "payoff plan.")
    elif recov > 200:
        move = ("<b>Smartest next move:</b> redirect that recovered waste into savings "
                "or your highest-rate debt.")
    if move:
        parts.append(move)

    return '<div class="summary-box">' + " ".join(parts) + "</div>"


def _evidence(records, cats=(), merchants=(), accounts=(), limit=40) -> str:
    """A small table of the actual transactions behind a finding (drill-down)."""
    cats, merchants, accounts = set(cats), set(merchants), set(accounts)
    hits = [r for r in records if r["category"] in cats
            or r["merchant"] in merchants or r["account"] in accounts]
    if not hits:
        return ""
    hits.sort(key=lambda r: r["date"], reverse=True)
    spent = sum(-r["amount"] for r in hits if r["amount"] < 0)
    shown = hits[:limit]
    rows = "".join(
        f'<tr><td>{_esc(r["date"])}</td><td>{_esc(r["merchant"])}</td>'
        f'<td>{_esc(r["account"])}</td>'
        f'<td class="num {"green" if r["amount"]>0 else "red"}">'
        f'{_money(r["amount"], signed=True)}</td></tr>' for r in shown)
    cap = (f'Showing {len(shown)} of {len(hits)} transactions · '
           f'total spent {_mc(spent)}.' if len(hits) > len(shown)
           else f'{len(hits)} transactions · total spent {_mc(spent)}.')
    return (f'<div class="tablewrap" style="max-height:280px;margin-top:8px">'
            f'<table><thead><tr><th>Date</th><th>Merchant</th><th>Account</th>'
            f'<th class="num">Amount</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'<div class="subtle">{cap}</div>')


def priorities_section(analysis: dict, plan: dict):
    """Return (top_html, more_html). Each item is clickable to drill into its data."""
    if analysis.get("empty"):
        return "", ""
    records = analysis.get("records", [])
    actions: list[dict] = []      # things you can DO to save money, ranked by $
    context: list[dict] = []      # useful observations, but not a savings action

    # High-interest debts (known rate) are usually the #1 dollar priority.
    for d in _nonmortgage_debts(plan):
        if d.apr >= 12:
            annual = d.balance * d.apr / 100
            actions.append({
                "impact": annual, "icon": "🔥",
                "title": f"Pay off {d.name} — {d.apr:.1f}% APR on {_mc(d.balance)}",
                "action": f"Costs ~{_mc(annual)}/yr in interest. Put every spare "
                          f"dollar here first.",
                "accounts": [d.name],
                "detail": (f'<div class="subtle">Balance {_money(d.balance)} · APR '
                           f'{d.apr:.2f}% · ~{_money(d.monthly_interest)}/mo interest · '
                           f'minimum {_money(d.min_payment)}.</div>')})

    for i in analysis["insights"]:
        items = ("<ul style='margin:8px 0 0;font-size:13px'>"
                 + "".join(f"<li>{_esc(x)}</li>" for x in i["items"]) + "</ul>"
                 ) if i.get("items") else ""
        entry = {"impact": i.get("annual_impact", 0), "icon": i.get("icon", "•"),
                 "title": i["title"], "action": i["detail"],
                 "cats": i.get("match_categories", []),
                 "merchants": i.get("match_merchants", []), "detail": items}
        # Only items that represent real, recoverable money are "actions".
        if i.get("recoverable") and i.get("annual_impact", 0) > 0:
            actions.append(entry)
        else:
            context.append(entry)

    for b in plan.get("bills", []):
        actions.append({"impact": b["potential_annual"], "icon": "💸",
                        "title": f"{b['name']} looks high (~{_mc(b['monthly'])}/mo)",
                        "action": b["tip"], "merchants": [b["name"]]})

    seen, uniq = set(), []
    for c in sorted(actions, key=lambda x: x["impact"], reverse=True):
        key = c["title"][:40]
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    top, rest = uniq[:6], uniq[6:]

    def card(rank, c, cls, show_impact=True):
        body = c.get("detail", "") + _evidence(
            records, c.get("cats", []), c.get("merchants", []), c.get("accounts", []))
        if not body:
            body = ('<div class="subtle">No itemized transactions to show for this '
                    'one.</div>')
        pill = (f'<div class="impact">~{_mc(c["impact"])}/yr</div>'
                if show_impact and c.get("impact") else "")
        return (f'<details class="prio {cls}"><summary>'
                f'<div class="rank">{rank}</div>'
                f'<div style="flex:1"><div class="t">{c["icon"]} {_esc(c["title"])}</div>'
                f'<div class="a">{_esc(c["action"])}</div></div>'
                f'{pill}<div class="chev">▶</div></summary>'
                f'<div class="drill">{body}</div></details>')

    top_html = "".join(
        card(i + 1, c, "p1" if i < 2 else "p2" if i < 4 else "p3")
        for i, c in enumerate(top)) or \
        '<div class="note">No clear savings actions right now — nicely managed. 🎉</div>'

    more_bits = "".join(card("·", c, "p3") for c in rest)
    ctx_bits = "".join(card("ℹ", c, "p3", show_impact=False) for c in context)
    more_html = ""
    if more_bits or ctx_bits:
        n = len(rest) + len(context)
        more_html = (f'<details><summary>{n} more observations &amp; context</summary>'
                     f'<div style="margin-top:10px">{more_bits}{ctx_bits}</div></details>')
    return top_html, more_html


def _dur(months: int) -> str:
    y, m = months // 12, months % 12
    if y and m:
        return f"{y} yr {m} mo"
    if y:
        return f"{y} yr"
    return f"{m} mo"


def monthly_bills_section(analysis: dict) -> str:
    """The 'did you know you pay each of these every month?' table."""
    if analysis.get("empty"):
        return ""
    bills = [r for r in analysis["recurring"]
             if r["cadence"] == "monthly" and r["active"]]
    if not bills:
        return ""
    bills.sort(key=lambda r: r["annual_cost"], reverse=True)
    total_mo = sum(r["typical_amount"] for r in bills)
    total_yr = sum(r["annual_cost"] for r in bills)
    rows = "".join(
        f'<tr><td>{_esc(r["merchant"])}</td>'
        f'<td>~the {r["typical_day"]}{_ordinal(r["typical_day"])}</td>'
        f'<td class="num">{_money(r["typical_amount"])}</td>'
        f'<td>{_esc(r["first_date"][:7])} · {_dur(r["months_paying"])}</td>'
        f'<td class="num">{_money(r["annual_cost"])}</td>'
        f'<td class="num">{_money(r["lifetime_total"])}</td></tr>'
        for r in bills)
    return (
        f'<p class="lede">Same vendor, similar amount, every month. Do you still want '
        f'each of these? Together they\'re <b>{_money(total_mo)}/mo</b> '
        f'(<b>{_money(total_yr)}/yr</b>).</p>'
        f'<div class="tablewrap"><table><thead><tr><th>Vendor</th><th>Charges on</th>'
        f'<th class="num">Each</th><th>Paying since</th><th class="num">Per year</th>'
        f'<th class="num">Paid so far</th></tr></thead><tbody>{rows}</tbody>'
        f'<tfoot><tr><td colspan="2"><b>Total monthly bills</b></td>'
        f'<td class="num"><b>{_money(total_mo)}</b></td><td></td>'
        f'<td class="num"><b>{_money(total_yr)}</b></td><td></td></tr></tfoot>'
        f'</table></div>')


def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _fmtv(v) -> str:
    if v in (None, 0, 0.0, ""):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _people_drill(txns: list, limit: int = 60) -> str:
    shown = txns[:limit]
    rows = "".join(
        f'<tr><td>{_esc(r["date"])}</td><td>{_esc(r["merchant"])}</td>'
        f'<td>{_esc(r["category"])}</td><td>{_esc(r["account"])}</td>'
        f'<td class="num red">{_money(r["amount"], signed=True)}</td></tr>'
        for r in shown)
    cap = (f'Showing {len(shown)} of {len(txns):,} transactions.'
           if len(txns) > len(shown) else f'{len(txns):,} transactions.')
    return (f'<div class="tablewrap" style="max-height:300px;margin-top:8px">'
            f'<table><thead><tr><th>Date</th><th>Merchant</th><th>Category</th>'
            f'<th>Account</th><th class="num">Amount</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div><div class="subtle">{cap}</div>')


def _people_section(plan: dict) -> str:
    """Spending broken out by person — click a person to see their transactions."""
    pe = plan.get("people")
    if not pe or not pe.get("tracked"):
        return ('<div class="prompt">👨‍👩‍👧‍👦 <b>See what each person costs.</b> Want to '
                'know what a partner — or each child — actually spends? Open the '
                '<b>✏️ My info</b> tab and add people: claim a whole account (like a '
                'kid\'s debit card) and/or a few merchant words (like “roblox” or '
                '“gamestop”). MoneyMan tags every matching charge and totals it here. '
                '(You can also edit <code>config\\Who-Is-Spending.csv</code> directly.)'
                '</div>')
    ppl = pe["people"]
    bar = charts.hbars([(p["name"], p["total"], f'{p["count"]}×')
                        for p in ppl if p["total"] > 0])
    bar_html = bar or '<div class="subtle">No tagged spending yet.</div>'
    cards = ""
    for p in ppl:
        chips = "".join(f'<span class="pill">{_esc(c)} · {_mc(v)}</span>'
                        for c, v in p["top_categories"]) or \
            '<span class="subtle">no spending tagged yet</span>'
        cls = "p3" if p["is_shared"] else "p2"
        icon = "🏠" if p["is_shared"] else "🙂"
        cards += (
            f'<details class="prio {cls}"><summary>'
            f'<div style="flex:1"><div class="t">{icon} {_esc(p["name"])}</div>'
            f'<div class="person-sub">{_mc(p["monthly"])}/mo · {p["count"]:,} charges'
            f' · {p["pct"]:.0f}% of tracked spending</div>'
            f'<div class="chips">{chips}</div></div>'
            f'<div class="impact">{_mc(p["total"])}</div>'
            f'<div class="chev">▶</div></summary>'
            f'<div class="drill">{_people_drill(p["txns"])}</div></details>')
    return (
        f'<p class="lede">Who is the money going to? These are spending totals '
        f'(income &amp; transfers excluded) across your whole history — about '
        f'<b>{_mc(pe["monthly_total"])}/mo</b> all together. Click a person to see '
        f'every charge attributed to them.</p>'
        f'<div class="panel">{bar_html}</div>'
        f'<div style="margin-top:12px">{cards}</div>'
        f'<div class="note" style="margin-top:12px">Tip: refine who-gets-what in the '
        f'<b>✏️ My info</b> tab — assign an account or add merchant keywords. '
        f'Untagged spending stays in <b>Everyone / Household</b>.</div>')


def _chips(items) -> str:
    return "".join(f'<span class="pill">{_esc(e)}</span>' for e in items)


def _discovery_section(plan: dict) -> str:
    """'Get to know you' — the data-built profile + the smart questions."""
    d = plan.get("discovery")
    if not d:
        return '<div class="subtle">Add your statements to build your profile.</div>'
    if not d.get("enough"):
        return (f'<div class="prompt">📆 MoneyMan gets to know you better with more '
                f'history. You have about <b>{d.get("months", 0)} month(s)</b>; once '
                f'you reach <b>{d.get("min_months", 6)}+</b> it reads your patterns and '
                f'builds a profile plus the questions worth answering.</div>')

    narr = (f'<div class="summary-box">{_esc(d["narrative"])}</div>'
            if d.get("narrative") else "")

    inc = ""
    if d.get("income"):
        chips = _chips(f'{s["name"]} · {_mc(s["monthly"])}/mo' for s in d["income"][:6])
        inc = (f'<div class="panel" style="margin-top:12px"><b>💵 Income I can see</b>'
               f'<div class="chips" style="margin-top:8px">{chips}</div></div>')

    sig = ""
    if d.get("signals"):
        rows = ""
        for s in d["signals"]:
            rows += (f'<div class="insight low"><div class="ico">🔎</div>'
                     f'<div style="flex:1"><div class="t">{_esc(s["label"])}</div>'
                     f'<div class="d">{_esc(s["why"])}</div>'
                     f'<div class="chips" style="margin-top:6px">'
                     f'{_chips(s["evidence"])}</div></div>'
                     f'<div class="impact">{_mc(s["total"])}</div></div>')
        sig = f'<h3 style="margin-top:18px">What your spending reveals</h3>{rows}'

    q = ""
    if d.get("questions"):
        cards = ""
        for i, qq in enumerate(d["questions"]):
            cards += (f'<details class="prio p3"><summary>'
                      f'<div class="rank">{i + 1}</div>'
                      f'<div style="flex:1"><div class="t">❓ {_esc(qq["q"])}</div>'
                      f'<div class="a">{_esc(qq["why"])}</div></div>'
                      f'<div class="chev">▶</div></summary>'
                      f'<div class="drill"><div class="chips">{_chips(qq["evidence"])}'
                      f'</div></div></details>')
        q = (f'<h3 style="margin-top:18px">Questions that would sharpen your plan</h3>'
             f'<p class="lede">Each one is here because of a real pattern in your data. '
             f'Answer them in the <b>✏️ My info</b> tab — or in '
             f'<code>Reports\\Getting-To-Know-You.txt</code>.</p>{cards}')

    return narr + inc + sig + q


def _assignment_board(plan: dict) -> str:
    """A drag-and-drop board (web app only): drop each merchant on whoever it's for."""
    board = plan.get("assign_board")
    cfg = plan.get("people_config") or []
    if not board or not cfg:
        return ""
    columns = [p.name for p in cfg] + [SHARED]

    def opts(sel):
        return "".join(
            f'<option value="{_esc(c)}"{" selected" if c == sel else ""}>'
            f'{_esc(c)}</option>' for c in columns)

    by_col = {c: [] for c in columns}
    hidden = ""
    for i, m in enumerate(board):
        who = m["person"] if m["person"] in by_col else SHARED
        by_col[who].append(
            f'<div class="mcard" id="card{i}" draggable="true" '
            f'ondragstart="mmDrag(event,{i})" data-amt="{m["total"]}">'
            f'<div class="mc-name">{_esc(m["merchant"])}</div>'
            f'<div class="mc-amt">{_money(m["total"])} · {m["count"]}×</div>'
            f'<select class="movesel" onchange="mmMove({i},this.value)">'
            f'{opts(who)}</select></div>')
        hidden += (f'<input type="hidden" name="m{i}" value="{_esc(m["merchant"])}">'
                   f'<input type="hidden" id="p{i}" name="p{i}" value="{_esc(who)}">')

    cols_html = ""
    for c in columns:
        icon = "🏠" if c == SHARED else "🙂"
        cols_html += (f'<div class="pcol" data-person="{_esc(c)}" '
                      f'ondragover="mmAllow(event)" ondragleave="mmLeave(event)" '
                      f'ondrop="mmDrop(event)"><div class="pcol-h">'
                      f'<span>{icon} {_esc(c)}</span>'
                      f'<span class="pcol-total">$0</span></div>'
                      f'<div class="cards-col">{"".join(by_col[c])}</div></div>')

    return (
        f'<h3 style="margin-top:20px">🗂️ Drag each expense to whoever it\'s for</h3>'
        f'<p class="lede">Grab a card and drop it in a person\'s column — or use the '
        f'little menu on each card. The column totals update as you move things, so you '
        f'can see exactly where the money goes. These are your top {len(board)} '
        f'merchants by spend; what you set here <b>overrides the keyword rules</b>. '
        f'Click Save to keep it. Anything you don\'t place stays in {_esc(SHARED)}.</p>'
        f'<form method="post" action="/save-assignments" id="assignform">'
        f'<input type="hidden" name="a_count" value="{len(board)}">'
        f'<div class="board">{cols_html}</div>{hidden}'
        f'<button class="savebtn" type="submit" style="margin-top:14px">'
        f'💾 Save who-spent-what</button></form>')


def _people_editor(plan: dict) -> str:
    """The 'track by person' editor (web app only): add people + their rules."""
    cfg = plan.get("people_config") or []
    accts = plan.get("accounts") or []
    hint = (" Your accounts: " + ", ".join(_esc(a) for a in accts[:14])) if accts else ""

    def prow(i, name="", accounts="", keywords=""):
        return (f'<tr>'
                f'<td><input class="pin" name="p{i}_name" value="{_esc(name)}" '
                f'placeholder="e.g. Emma"></td>'
                f'<td><input class="pin" name="p{i}_acct" value="{_esc(accounts)}" '
                f'placeholder="card or account name(s)"></td>'
                f'<td><input class="pin" name="p{i}_kw" value="{_esc(keywords)}" '
                f'placeholder="roblox; nintendo"></td></tr>')

    rows, n = "", 0
    for p in cfg:
        rows += prow(n, p.name, "; ".join(p.accounts), "; ".join(p.keywords))
        n += 1
    for _ in range(3):                      # spare blank rows to add new people
        rows += prow(n)
        n += 1
    return (
        f'<b style="display:block;margin-top:18px">👨‍👩‍👧‍👦 Track spending by person</b>'
        f'<p class="lede">Add anyone you want to track (each child, a partner). Claim '
        f'their spending by <b>account</b> (a whole card is theirs) and/or by '
        f'<b>merchant words</b>. Separate multiple with a semicolon.<br>'
        f'<span class="subtle">{hint}</span></p>'
        f'<form method="post" action="/save-people">'
        f'<input type="hidden" name="p_count" value="{n}">'
        f'<table><thead><tr><th>Person</th><th>Accounts (use ;)</th>'
        f'<th>Merchant words (use ;)</th></tr></thead><tbody>{rows}</tbody></table>'
        f'<button class="savebtn" type="submit">💾 Save people &amp; recalculate'
        f'</button></form>')


def edit_panel(plan: dict) -> str:
    """Editable form (only in the local web app) that saves to disk and persists."""
    p = plan.get("profile")
    if p is None:
        return ""

    def ti(label, val, placeholder=""):
        ph = f' placeholder="{_esc(placeholder)}"' if placeholder else ""
        return (f'<label class="ef"><span>{_esc(label)}</span>'
                f'<input name="{_esc(label)}" value="{_esc(_fmtv(val))}"{ph}></label>')

    # Suggest a monthly income from the steady paychecks we detected.
    income_hint = "what lands in your accounts each month"
    disc = plan.get("discovery")
    if disc and disc.get("enough"):
        pay = [x for x in disc.get("income", [])
               if x.get("regular") and x["monthly"] >= 400][:3]
        if pay:
            tot = sum(x["monthly"] for x in pay)
            names = " + ".join(x["name"] for x in pay)
            income_hint = f"~{tot:,.0f} from {names}"

    def yn(label, val):
        opts = "".join(
            f'<option value="{o}"{" selected" if ((val and o=="y") or (not val and o=="n")) else ""}>'
            f'{o or "—"}</option>' for o in ("", "y", "n"))
        return (f'<label class="ef"><span>{_esc(label)}</span>'
                f'<select name="{_esc(label)}">{opts}</select></label>')

    prof = "".join([
        ti("Monthly take-home income", p.monthly_income_override, income_hint),
        ti("Your age", p.age), ti("Target retirement age", p.target_retirement_age),
        ti("Cash savings", p.cash_savings), ti("Retirement balance", p.retirement_balance),
        ti("Monthly retirement contribution", p.monthly_retirement_contribution),
        ti("Estimated Social Security (monthly, household)",
           p.social_security_monthly, "ssa.gov estimate; lowers what you need"),
        ti("Inflation assumption (%)", p.inflation_pct, "2.5 typical"),
        yn("Own your home? (y/n)", p.owns_home),
        ti("Home value (your estimate)", p.home_value),
        yn("Own a rental property? (y/n)", p.owns_rental),
        ti("Rental property value", p.rental_value),
        ti("Rental monthly rent income", p.rental_rent_income),
        ti("Rental mortgage balance", p.rental_mortgage_balance),
        ti("Rental mortgage APR (%)", p.rental_mortgage_apr),
    ])
    prof_form = (f'<form method="post" action="/save-profile"><div class="editgrid">'
                 f'{prof}</div><button class="savebtn" type="submit">💾 Save my info'
                 f'</button></form>')

    debts_form = ""
    if plan["debts"]:
        rows = ""
        for i, d in enumerate(plan["debts"]):
            rows += (
                f'<tr><td>{_esc(d.name)}</td><td class="num">{_money(d.balance)}</td>'
                f'<td><input class="mini" name="d{i}_apr" value="{_fmtv(d.apr)}"></td>'
                f'<td><input class="mini" name="d{i}_min" value="{_fmtv(d.min_payment)}">'
                f'<input type="hidden" name="d{i}_name" value="{_esc(d.name)}">'
                f'<input type="hidden" name="d{i}_kind" value="{_esc(d.kind)}">'
                f'<input type="hidden" name="d{i}_bal" value="{d.balance}">'
                f'<input type="hidden" name="d{i}_limit" value="{d.credit_limit}"></td></tr>')
        debts_form = (
            f'<b style="display:block;margin-top:16px">Your debts — add each interest '
            f'rate &amp; minimum to unlock the payoff plan</b>'
            f'<form method="post" action="/save-debts">'
            f'<input type="hidden" name="d_count" value="{len(plan["debts"])}">'
            f'<table><thead><tr><th>Debt</th><th class="num">Balance</th>'
            f'<th>APR %</th><th>Min $/mo</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<button class="savebtn" type="submit">💾 Save rates &amp; recalculate'
            f'</button></form>')

    return (f'<div class="editbox panel" style="padding:18px 20px">'
            f'<p class="lede">Edit anything below and click Save. It writes to your '
            f'local files and is remembered after you close this — the rest of the '
            f'report recalculates on save. Everything stays on this computer.</p>'
            f'<b>You, your home &amp; rental</b>{prof_form}{debts_form}'
            f'{_people_editor(plan)}</div>')


# --------------------------------------------------------------------------- #
def build_html(analysis: dict, data_root: Path, warnings: list[str],
               ingest_stats: dict, dup_skipped: int, plan: dict,
               editable: bool = False, saved_msg: str = "") -> str:
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    empty = analysis.get("empty")
    s = {} if empty else analysis["summary"]

    # KPI cards
    if empty:
        kpis = (_kpi("Money in", "—") + _kpi("Money out", "—")
                + _kpi("Net", "—") + _kpi("Transactions", "0"))
        range_badge = "no statements yet"
        acct_badge = "—"
    else:
        months = max(1, s["months_span"])
        spend_mo = plan.get("expense_monthly", s["expense"] / months)
        inc_mo = plan.get("income_monthly", s["income"] / months)
        net_mo = inc_mo - spend_mo
        inc_label = "Income / mo (yours)" if plan.get("income_is_override") else "Income / mo"
        nonmort = sum(d.balance for d in plan["debts"]
                      if "mortgage" not in d.kind and d.balance > 0)
        nwv = plan["net_worth"]["net_worth"]
        kpis = "".join([
            _kpi("Net worth", _mc(nwv), "green" if nwv >= 0 else "red", tab="networth"),
            _kpi(inc_label, _mc(inc_mo), "green"),
            _kpi("Spending / mo", _mc(spend_mo), "red", tab="spending"),
            _kpi("Kept / mo", _mc(net_mo), "green" if net_mo >= 0 else "red"),
            _kpi("Debt (non-mortgage)", _mc(nonmort), "red", tab="debts"),
        ])
        range_badge = f'{s["data_min"]} → {s["data_max"]}'
        acct_badge = f'{s["n_accounts"]} accounts · {s["n_txns"]:,} transactions'

    # Plain-English summary + the few things that matter (replaces the old dump).
    summary_html = summary_section(analysis, plan)
    prio_top, prio_more = priorities_section(analysis, plan)
    edit_html = edit_panel(plan) if editable else ""
    bills_html = monthly_bills_section(analysis)
    saved_banner = f'<div class="saved">✔ {_esc(saved_msg)}</div>' if saved_msg else ""

    # Charts (only when there's data)
    charts_block = ""
    if not empty:
        cat_top = analysis["category_totals"][:9]
        other = sum(c["total"] for c in analysis["category_totals"][9:])
        donut_items = [(c["category"], c["total"]) for c in cat_top]
        if other > 0:
            donut_items.append(("Other", other))
        donut_svg = charts.donut(donut_items)
        legend = "".join(
            f'<div class="row"><span class="dot" style="background:'
            f'{charts.PALETTE[i%len(charts.PALETTE)]}"></span>{_esc(l)} — {_money(v)}</div>'
            for i, (l, v) in enumerate(donut_items))
        bars_svg = charts.grouped_bars(analysis["cash_flow"])
        merch_svg = charts.hbars([(m["merchant"], m["total"], f'{m["count"]}×')
                                  for m in analysis["top_merchants"][:10]])
        charts_block = (
            f'<h2>📊 Cash flow by month</h2><div class="panel">{bars_svg}'
            f'<div class="subtle"><span class="dot" style="background:#34c38f"></span> '
            f'in &nbsp;<span class="dot" style="background:#f46a6a"></span> out</div></div>'
            f'<div class="grid2" style="margin-top:16px">'
            f'<div class="panel"><b>Where your money goes</b>{donut_svg}'
            f'<div class="legend">{legend}</div></div>'
            f'<div class="panel"><b>Top merchants</b>{merch_svg}</div></div>')

    # Recurring + transactions tables
    rec_tables = ""
    if not empty:
        rec_rows = "".join(
            f'<tr><td>{_esc(r["merchant"])}</td><td>{_esc(r["category"])}</td>'
            f'<td>{_esc(r["cadence"])}</td>'
            f'<td class="num">{_money(r["typical_amount"])}</td>'
            f'<td class="num" data-v="{r["annual_cost"]}">{_money(r["annual_cost"])}</td>'
            f'<td>{_esc(r["last_date"])}</td>'
            f'<td><span class="pill {"on" if r["active"] else "off"}">'
            f'{"active" if r["active"] else "stopped"}</span></td></tr>'
            for r in analysis["recurring"])
        txn_rows = "".join(
            f'<tr><td data-v="{_esc(r["date"])}">{_esc(r["date"])}</td>'
            f'<td>{_esc(r["account"])}</td><td>{_esc(r["merchant"])}</td>'
            f'<td>{_esc(r["category"])}</td>'
            f'<td class="num {"green" if r["amount"]>0 else "red"}" '
            f'data-v="{r["amount"]}">{_money(r["amount"], signed=True)}</td></tr>'
            for r in analysis["records"])
        rec_html = (
            f'<div class="tablewrap">'
            f'<table id="rec"><thead><tr><th>Merchant</th><th>Category</th><th>Cadence</th>'
            f'<th class="num">Each</th><th class="num" onclick="mmSort(\'rec\',4,true)">'
            f'Per year</th><th>Last</th><th>Status</th></tr></thead>'
            f'<tbody>{rec_rows}</tbody></table></div>')
        txn_html = (
            f'<input class="search" placeholder="🔎 Search {len(analysis["records"]):,} '
            f'transactions…" oninput="mmFilter(\'txn\',this.value)">'
            f'<div class="tablewrap"><table id="txn"><thead><tr>'
            f'<th onclick="mmSort(\'txn\',0,false)">Date</th><th>Account</th>'
            f'<th onclick="mmSort(\'txn\',2,false)">Merchant</th><th>Category</th>'
            f'<th class="num" onclick="mmSort(\'txn\',4,true)">Amount</th></tr></thead>'
            f'<tbody>{txn_rows}</tbody></table></div>')
    else:
        rec_html = txn_html = ""

    all_notes = list(warnings) + list(plan.get("notes", []))
    notes = ""
    if all_notes:
        ws = "".join(f"<li>{_esc(w)}</li>" for w in all_notes[:14])
        notes = (f'<h2>📂 Notes</h2><div class="note"><ul style="margin:0;'
                 f'padding-left:18px">{ws}</ul></div>')

    # ---- assemble the tabbed app -------------------------------------------- #
    has_debts = plan["payoff"].get("has_debts")
    if plan["debts"]:
        debt_prompt = (
            '<div class="prompt">I found your balances and pre-filled '
            '<code>config\\Accounts-and-Debts.csv</code>. Add each <b>APR</b> and '
            '<b>minimum payment</b> (easiest: open the <b>✏️ My info</b> tab, or run '
            "the interview) and I'll build your full payoff plan.</div>")
    else:
        debt_prompt = '<div class="subtle">Add your debts to generate a payoff plan.</div>'
    payoff_or_prompt = _payoff_section(plan) or debt_prompt
    possibilities_html = (
        '<h3 style="margin-top:18px">🎲 What a lump sum could do</h3>'
        + _possibilities_section(plan)) if has_debts else ""
    bills_block = bills_html or ('<div class="subtle">No clear monthly bills detected '
                                 'yet.</div>')
    recurring_html = (
        '<h3 style="margin-top:18px">🔁 Recurring &amp; subscriptions</h3>'
        + rec_html) if rec_html else ""
    spending_block = (charts_block or '<div class="subtle">No spending data yet.'
                      '</div>') + recurring_html
    txn_block = ('<h3 style="margin-top:18px">🧾 All transactions</h3>'
                 + txn_html) if txn_html else ""
    people_html = _people_section(plan)

    overview_inner = (
        f'<h2>📌 Your money, in plain English</h2>{summary_html}'
        f'<h2>🎯 What matters most</h2>'
        f'<p class="lede">The few highest-impact things — biggest dollars first. '
        f'Click any one to see the exact transactions behind it.</p>'
        f'{prio_top}{prio_more}'
        f'<h2>📅 Bills you pay every month — did you know?</h2>{bills_block}')
    mortgage_html = _mortgage_section(plan)
    mortgage_block = (f'<h3 style="margin-top:18px">🏠 Pay your home loan down faster'
                      f'</h3>{mortgage_html}') if mortgage_html else ""
    debts_inner = (
        f'<h2>💳 Debts &amp; your path to $0</h2>{_debts_section(plan)}'
        f'<div style="margin-top:14px">{payoff_or_prompt}</div>'
        f'{mortgage_block}{possibilities_html}')
    cashflow_inner = (
        f'<h2>💵 Safe to spend</h2>{_safe_to_spend_section(plan)}'
        f'<h2 style="margin-top:18px">🔮 Cash-flow forecast</h2>'
        f'{_cashflow_section(plan)}')
    board_html = _assignment_board(plan) if editable else ""
    people_inner = f'<h2>👨‍👩‍👧‍👦 Spending by person</h2>{people_html}{board_html}'
    networth_inner = (
        f'<h2>🏛️ Net worth &amp; where you\'re headed</h2>{_networth_section(plan)}')
    plan_inner = (
        f'<h2>🎯 Goals with a deadline</h2>{_goals_section(plan)}'
        f'<h2 style="margin-top:18px">🌧️ Save for surprises &amp; your safety net</h2>'
        f'{_surprises_section(plan)}'
        f'<div style="margin-top:14px">{_emergency_section(plan)}</div>'
        f'<h2 style="margin-top:18px">🧾 Taxes &amp; account strategy</h2>'
        f'{_tax_section(plan)}'
        f'<h2 style="margin-top:18px">🧭 The way forward — building independence</h2>'
        f'{_foo_section(plan)}')
    data_inner = (f'<h2>🧩 Data completeness — what to add for sharper advice</h2>'
                  f'{_checklist_section(plan["intake"])}{txn_block}{notes}')
    about_inner = (f'<h2>👤 Getting to know you</h2>'
                   f'<p class="lede">Built from your real spending — who this household '
                   f'looks like, and the questions a good planner would ask next.</p>'
                   f'{_discovery_section(plan)}')

    tabs = [
        ("overview", "🏠", "Overview", overview_inner),
        ("about", "👤", "About you", about_inner),
        ("cashflow", "💵", "Cash flow", cashflow_inner),
        ("debts", "💳", "Debts &amp; payoff", debts_inner),
        ("people", "🧑‍🤝‍🧑", "People", people_inner),
        ("spending", "💸", "Spending", spending_block),
        ("networth", "🏛️", "Net worth", networth_inner),
        ("plan", "🧭", "Plan ahead", plan_inner),
        ("data", "🧩", "Data", data_inner),
    ]
    if editable:
        tabs.insert(1, ("info", "✏️", "My info",
                        f'<h2>✏️ Your info — type here, it saves to your computer</h2>'
                        f'{edit_html}'))

    active = "overview"
    nav = "".join(
        f'<button class="navtab{" active" if tid == active else ""}" id="nav-{tid}" '
        f'onclick="mmTab(\'{tid}\')">{ico} {lbl}</button>'
        for tid, ico, lbl, _inner in tabs)
    sections = "".join(
        f'<section class="tab{" active" if tid == active else ""}" id="tab-{tid}">'
        f'{inner}</section>'
        for tid, _ico, _lbl, inner in tabs)

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MoneyMan — your private finance plan</title><style>{CSS}</style></head><body>
<header class="top"><div class="wrap">
<div class="brand">💰 MoneyMan <small>· your private finance plan</small></div>
<div class="badges"><span class="badge">🔒 100% local — nothing left this computer</span>
<span class="badge">📅 {_esc(range_badge)}</span><span class="badge">🏦 {acct_badge}</span></div>
</div></header>
<div class="nav"><div class="nav-inner">{nav}</div></div>
<div class="wrap">
{saved_banner}
<div class="cards hero">{kpis}</div>
<div class="subtle" style="margin-top:8px">Generated {now} · MoneyMan v{__version__} ·
tap a card or a tab above to explore.</div>
{sections}
<div class="foot"><b>Your privacy:</b> MoneyMan ran entirely on this computer — no
internet, no account, no data sent anywhere, no address look-ups. Everything lives in
<code>{_esc(str(data_root))}</code>.<br>
This report is information and education to help you decide — it is not professional
financial, tax, or investment advice. MoneyMan v{__version__} · {now}.</div>
</div><script>{JS}</script></body></html>"""


def write_report(analysis, paths, warnings, ingest_stats, dup_skipped, plan) -> Path:
    paths.reports.mkdir(parents=True, exist_ok=True)
    html_text = build_html(analysis, paths.root, warnings, ingest_stats,
                           dup_skipped, plan)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out = paths.reports / f"MoneyMan_Report_{stamp}.html"
    out.write_text(html_text, encoding="utf-8")
    (paths.reports / "MoneyMan_Latest.html").write_text(html_text, encoding="utf-8")
    return out
