#!/usr/bin/env python3
"""
Synthetic CLO data generator.
Produces realistic, internally-consistent data for a CLO servicing shop:
 - 4 CLO deals (featuring Golub Capital; broadly-syndicated + middle market)
 - tranche capital structures
 - a pool of syndicated-loan collateral
 - quarterly collections, payment waterfall, indenture compliance tests
 - trustee-vs-internal reconciliation with injected breaks

Outputs: CSVs in data/ and a loaded SQLite database (clo.sqlite).
Deterministic (fixed seed) so results are reproducible.
"""
import csv, os, sqlite3, random, datetime as dt

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

# ---------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------
# Moody's rating -> (rating factor, rank, is_ccc)
RATING_SCALE = [
    ("Aaa", 1, 1, 0), ("Aa1", 10, 2, 0), ("Aa2", 20, 3, 0), ("Aa3", 40, 4, 0),
    ("A1", 70, 5, 0), ("A2", 120, 6, 0), ("A3", 180, 7, 0),
    ("Baa1", 260, 8, 0), ("Baa2", 360, 9, 0), ("Baa3", 610, 10, 0),
    ("Ba1", 940, 11, 0), ("Ba2", 1350, 12, 0), ("Ba3", 1766, 13, 0),
    ("B1", 2220, 14, 0), ("B2", 2720, 15, 0), ("B3", 3490, 16, 0),
    ("Caa1", 4770, 17, 1), ("Caa2", 6500, 18, 1), ("Caa3", 8070, 19, 1),
    ("Ca", 10000, 20, 1),
]
RF = {r[0]: r[1] for r in RATING_SCALE}
CCC = {r[0]: r[3] for r in RATING_SCALE}

# Distribution of loan ratings typical of a US CLO pool (weighted to B-range,
# with a small Caa/CCC tail that stays under the 7.5% limit)
LOAN_RATINGS = (
    ["Ba1"]*3 + ["Ba2"]*7 + ["Ba3"]*12 + ["B1"]*24 + ["B2"]*28 +
    ["B3"]*14 + ["Caa1"]*3 + ["Caa2"]*1 + ["Baa3"]*5
)

INDUSTRIES = [
    "Healthcare & Pharmaceuticals", "High Tech Industries", "Services: Business",
    "Banking, Finance, Insurance", "Telecommunications", "Hotel, Gaming & Leisure",
    "Chemicals, Plastics & Rubber", "Aerospace & Defense", "Construction & Building",
    "Consumer Goods: Durable", "Media: Broadcasting", "Retail",
    "Automotive", "Energy: Oil & Gas", "Capital Equipment", "Beverage, Food & Tobacco",
]

OBLIGOR_WORDS_A = ["Summit","Vertex","Cobalt","Meridian","Atlas","Pioneer","Cascade",
    "Ironwood","Beacon","Sterling","Granite","Harbor","Sequoia","Titan","Crestline",
    "Northwind","Redwood","Vantage","Clarion","Everest","Monarch","Sable","Keystone",
    "Bluepeak","Halyard","Concord","Ridgeline","Aegis","Pinnacle","Cardinal"]
OBLIGOR_WORDS_B = ["Holdings","Industries","Group","Partners","Technologies","Solutions",
    "Health","Networks","Materials","Brands","Systems","Logistics","Capital","Foods",
    "Energy","Media","Devices","Pharma"]

DEALS = [
    # Featured client — Golub Capital (largest / flagship deal in this project)
    dict(deal_id="CLO-GOLB-241", deal_name="Golub Capital Partners CLO 2024-1",
         manager="Golub Capital", deal_type="Middle Market", trustee="BNY",
         currency="USD", closing_date="2024-05-16", reinvestment_end="2028-07-20",
         stated_maturity="2036-07-20", target_par=650_000_000, n_assets=215,
         par_low=1_200_000, par_high=3_800_000),
    dict(deal_id="CLO-CARL-231", deal_name="Carlyle US CLO 2023-1",
         manager="Carlyle", deal_type="Broadly Syndicated", trustee="BNY",
         currency="USD", closing_date="2023-04-18", reinvestment_end="2028-04-15",
         stated_maturity="2036-04-15", target_par=500_000_000, n_assets=170,
         par_low=1_800_000, par_high=4_500_000),
    dict(deal_id="CLO-ARES-222", deal_name="Ares Middle Market CLO 2022-2",
         manager="ARES", deal_type="Middle Market", trustee="BNY",
         currency="USD", closing_date="2022-09-27", reinvestment_end="2026-10-20",
         stated_maturity="2034-10-20", target_par=400_000_000, n_assets=150,
         par_low=1_500_000, par_high=3_500_000),
    dict(deal_id="CLO-BAIN-241", deal_name="Bain Capital US CLO 2024-1",
         manager="Bain Capital", deal_type="Broadly Syndicated", trustee="BNY",
         currency="USD", closing_date="2024-02-08", reinvestment_end="2029-01-20",
         stated_maturity="2037-01-20", target_par=450_000_000, n_assets=165,
         par_low=1_700_000, par_high=4_200_000),
]

# Tranche template as % of target par + rating + spread
TRANCHE_TMPL = [
    dict(cls="A",   rating="Aaa",  rank=1, pct=0.620, spread=148, defer=0, oc=None,   ic=None),
    dict(cls="B",   rating="Aa2",  rank=2, pct=0.105, spread=185, defer=0, oc=None,   ic=None),
    dict(cls="C",   rating="A2",   rank=3, pct=0.060, spread=210, defer=1, oc=119.5,  ic=115.0),
    dict(cls="D",   rating="Baa3", rank=4, pct=0.055, spread=310, defer=1, oc=112.8,  ic=110.0),
    dict(cls="E",   rating="Ba3",  rank=5, pct=0.045, spread=615, defer=1, oc=107.2,  ic=105.0),
    dict(cls="F",   rating="B3",   rank=6, pct=0.020, spread=845, defer=1, oc=104.5,  ic=102.5),
    dict(cls="Sub", rating=None,   rank=7, pct=0.095, spread=None, defer=1, oc=None,  ic=None),
]

PERIODS = [
    ("2024-Q4", "2024-10-15"),
    ("2025-Q1", "2025-01-15"),
    ("2025-Q2", "2025-04-15"),
    ("2025-Q3", "2025-07-15"),
]

def rnd_name():
    return f"{random.choice(OBLIGOR_WORDS_A)} {random.choice(OBLIGOR_WORDS_B)}"

def add_days(datestr, days):
    d = dt.date.fromisoformat(datestr)
    return (d + dt.timedelta(days=days)).isoformat()

# ---------------------------------------------------------------------
# Build obligors (shared universe)
# ---------------------------------------------------------------------
obligors = []
used = set()
for i in range(300):
    name = rnd_name()
    while name in used:
        name = rnd_name()
    used.add(name)
    obligors.append(dict(
        obligor_id=f"OB{i+1:04d}",
        obligor_name=name,
        industry=random.choice(INDUSTRIES),
        country=random.choices(["United States","Canada","United Kingdom"],
                               weights=[92,5,3])[0],
        moodys_rating=random.choice(LOAN_RATINGS),
    ))

# ---------------------------------------------------------------------
# Build tranches
# ---------------------------------------------------------------------
tranches = []
deal_tranches = {}
for d in DEALS:
    deal_tranches[d["deal_id"]] = []
    for t in TRANCHE_TMPL:
        bal = round(d["target_par"] * t["pct"], 2)
        tr = dict(
            tranche_id=f"{d['deal_id']}-{t['cls']}",
            deal_id=d["deal_id"], class_name=t["cls"], moodys_rating=t["rating"],
            seniority_rank=t["rank"], original_balance=bal, current_balance=bal,
            coupon_spread_bps=t["spread"], is_deferrable=t["defer"],
            oc_trigger_pct=t["oc"], ic_trigger_pct=t["ic"],
        )
        tranches.append(tr)
        deal_tranches[d["deal_id"]].append(tr)

# ---------------------------------------------------------------------
# Build assets (collateral pool) per deal
# ---------------------------------------------------------------------
assets = []
deal_assets = {}
aid = 0
for d in DEALS:
    deal_assets[d["deal_id"]] = []
    pool = random.sample(obligors, d["n_assets"])  # unique obligors per deal
    running = 0.0
    for ob in pool:
        aid += 1
        par = round(random.uniform(d["par_low"], d["par_high"]), 2)
        running += par
        rating = ob["moodys_rating"]
        # 2nd lien loans are a small slice and priced/spread wider
        lien = random.choices(["First Lien","Second Lien"], weights=[95,5])[0]
        defaulted = 1 if random.random() < 0.012 else 0
        if defaulted:
            price = round(random.uniform(35, 68), 3)
        elif CCC[rating]:
            price = round(random.uniform(78, 94), 3)
        else:
            price = round(random.uniform(96.5, 100.5), 3)
        spread = (375 if lien=="First Lien" else 700) + (RF[rating]/1000.0)*40
        spread = round(spread + random.uniform(-35, 55), 1)
        a = dict(
            asset_id=f"A{aid:05d}", deal_id=d["deal_id"], obligor_id=ob["obligor_id"],
            facility_name=f"{ob['obligor_name']} {random.choice(['Term Loan B','Term Loan A','TL B-2','Delayed Draw TL','Term Loan C'])}",
            lien_type=lien, par_amount=par, market_price=price,
            coupon_spread_bps=spread, base_rate_pct=5.33,
            purchase_date=add_days(d["closing_date"], random.randint(0, 400)),
            maturity_date=add_days(d["closing_date"], random.randint(1600, 2600)),
            moodys_rating=rating, is_defaulted=defaulted,
            is_cov_lite=1 if random.random() < 0.85 else 0,
        )
        assets.append(a)
        deal_assets[d["deal_id"]].append(a)

# ---------------------------------------------------------------------
# Ramp each deal to ~100.5% of target par (a fully-ramped CLO holds
# collateral at/above target, which keeps the OC tests comfortably passing).
# ---------------------------------------------------------------------
for d in DEALS:
    das = deal_assets[d["deal_id"]]
    cur = sum(a["par_amount"] for a in das)
    scale = d["target_par"] * 1.005 / cur
    for a in das:
        a["par_amount"] = round(a["par_amount"] * scale, 2)

# ---------------------------------------------------------------------
# Portfolio metric helpers
# ---------------------------------------------------------------------
def perform_par(dassets):
    # defaulted assets carry at market value for OC (haircut), performing at par
    tot = 0.0
    for a in dassets:
        if a["is_defaulted"]:
            tot += a["par_amount"] * a["market_price"]/100.0
        else:
            tot += a["par_amount"]
    return tot

def collateral_par(dassets):
    return sum(a["par_amount"] for a in dassets)

def warf(dassets):
    num = sum(RF[a["moodys_rating"]] * a["par_amount"] for a in dassets if not a["is_defaulted"])
    den = sum(a["par_amount"] for a in dassets if not a["is_defaulted"])
    return num/den

def was_bps(dassets):
    num = sum(a["coupon_spread_bps"] * a["par_amount"] for a in dassets if not a["is_defaulted"])
    den = sum(a["par_amount"] for a in dassets if not a["is_defaulted"])
    return num/den

def ccc_pct(dassets):
    tot = collateral_par(dassets)
    ccc = sum(a["par_amount"] for a in dassets if CCC[a["moodys_rating"]] and not a["is_defaulted"])
    return 100.0*ccc/tot

def defaulted_pct(dassets):
    tot = collateral_par(dassets)
    return 100.0*sum(a["par_amount"] for a in dassets if a["is_defaulted"])/tot

def largest_obligor_pct(dassets):
    tot = collateral_par(dassets)
    by_ob = {}
    for a in dassets:
        by_ob[a["obligor_id"]] = by_ob.get(a["obligor_id"],0)+a["par_amount"]
    return 100.0*max(by_ob.values())/tot

def largest_industry_pct(dassets, obmap):
    tot = collateral_par(dassets)
    by_ind = {}
    for a in dassets:
        ind = obmap[a["obligor_id"]]["industry"]
        by_ind[ind] = by_ind.get(ind,0)+a["par_amount"]
    return 100.0*max(by_ind.values())/tot

obmap = {o["obligor_id"]: o for o in obligors}

# ---------------------------------------------------------------------
# Collections, waterfall distributions, compliance tests per period
# ---------------------------------------------------------------------
collections, distributions, compliance = [], [], []
cid = did = tid = 0

for d in DEALS:
    dassets = deal_assets[d["deal_id"]]
    trs = sorted(deal_tranches[d["deal_id"]], key=lambda x: x["seniority_rank"])
    col_par = collateral_par(dassets)
    perf_par = perform_par(dassets)

    for pi, (period, paydate) in enumerate(PERIODS):
        # --- interest collections: ~ (base + WAS) on performing par, quarterly ---
        was = was_bps(dassets)
        gross_yield = (5.33 + was/100.0)/100.0
        interest_coll = perf_par * gross_yield * 0.25
        # small principal amortisation / prepayments each quarter
        principal_coll = col_par * random.uniform(0.004, 0.011)
        cid += 1
        collections.append(dict(collection_id=cid, deal_id=d["deal_id"], period=period,
            payment_date=paydate, interest_collections=round(interest_coll,2),
            principal_collections=round(principal_coll,2)))

        # --- interest waterfall (senior -> subordinated) ---
        avail = interest_coll
        # senior fees first (0.35% p.a. on collateral, quarterly)
        senior_fee = col_par * 0.0035 * 0.25
        avail -= senior_fee
        step = 0
        for tr in trs:
            step += 1
            if tr["class_name"] == "Sub":
                # equity gets the residual
                did += 1
                distributions.append(dict(distribution_id=did, deal_id=d["deal_id"],
                    tranche_id=tr["tranche_id"], period=period, payment_date=paydate,
                    waterfall_step=step, interest_due=0.0,
                    interest_paid=round(max(avail,0),2), principal_paid=0.0,
                    deferred_interest=0.0))
                avail = 0
                continue
            coupon = (5.33 + tr["coupon_spread_bps"]/100.0)/100.0
            due = tr["current_balance"] * coupon * 0.25
            paid = min(avail, due)
            deferred = 0.0
            if paid < due:
                if tr["is_deferrable"]:
                    deferred = due - paid          # PIK
                else:
                    paid = due                     # senior must be paid (assume ok)
            avail -= paid
            did += 1
            distributions.append(dict(distribution_id=did, deal_id=d["deal_id"],
                tranche_id=tr["tranche_id"], period=period, payment_date=paydate,
                waterfall_step=step, interest_due=round(due,2),
                interest_paid=round(paid,2), principal_paid=0.0,
                deferred_interest=round(deferred,2)))

        # --- compliance tests (recomputed each period) ---
        def add_test(cat, name, thr, act, ttype):
            global tid
            tid += 1
            res = "PASS" if ((act >= thr) if ttype=="min" else (act <= thr)) else "FAIL"
            compliance.append(dict(test_id=tid, deal_id=d["deal_id"], period=period,
                test_category=cat, test_name=name, threshold_value=round(thr,4),
                actual_value=round(act,4), threshold_type=ttype, result=res))

        # OC tests: adjusted collateral / (sum of that tranche + all senior)
        # small period drift so some tests tighten over time
        drift = 1.0 - pi*0.004
        adj_par = perf_par * drift
        senior_cum = 0.0
        for tr in trs:
            if tr["class_name"] == "Sub":
                continue
            senior_cum += tr["current_balance"]
            if tr["oc_trigger_pct"] is not None:
                oc = 100.0 * adj_par / senior_cum
                add_test("Coverage", f"Class {tr['class_name']} OC Test",
                         tr["oc_trigger_pct"], oc, "min")
            if tr["ic_trigger_pct"] is not None:
                # IC = interest collections / interest due on this + senior tranches
                int_due_cum = 0.0
                for t2 in trs:
                    if t2["seniority_rank"] <= tr["seniority_rank"] and t2["class_name"]!="Sub":
                        int_due_cum += t2["current_balance"]*((5.33+t2["coupon_spread_bps"]/100.0)/100.0)*0.25
                ic = 100.0 * interest_coll / int_due_cum
                add_test("Coverage", f"Class {tr['class_name']} IC Test",
                         tr["ic_trigger_pct"], ic, "min")

        # Collateral quality tests
        add_test("Collateral Quality", "Weighted Avg Rating Factor (WARF)",
                 2900.0, warf(dassets)*drift, "max")
        add_test("Collateral Quality", "Weighted Avg Spread (WAS)",
                 340.0, was_bps(dassets), "min")
        # Concentration tests
        add_test("Concentration", "Largest Obligor",
                 2.0, largest_obligor_pct(dassets), "max")
        add_test("Concentration", "Largest Moody's Industry",
                 12.0, largest_industry_pct(dassets, obmap), "max")
        add_test("Concentration", "Caa/CCC Bucket",
                 7.5, ccc_pct(dassets)*(1+pi*0.03), "max")
        add_test("Concentration", "Defaulted Obligations",
                 100.0*d["target_par"]*0.0 + 2.0, defaulted_pct(dassets)*(1+pi*0.05), "max")
        add_test("Concentration", "Second Lien Loans",
                 5.0, 100.0*sum(a["par_amount"] for a in dassets if a["lien_type"]=="Second Lien")/col_par, "max")

# ---------------------------------------------------------------------
# Trustee reconciliation (as-of most recent period) with injected breaks
# ---------------------------------------------------------------------
trustee, rid = [], 0
asof = "2025-07-15"
for a in assets:
    rid += 1
    internal = a["par_amount"]
    roll = random.random()
    if roll < 0.88:                       # matched
        trustee_par = internal
        btype, status, age = "Matched", "Matched", 0
    elif roll < 0.945:                    # position break (qty diff)
        trustee_par = round(internal * random.choice([0.5,0.75,1.25,0.9,1.1]),2)
        btype = "Position Break"
        age = random.randint(1, 40)
        status = "Escalated" if age > 15 else "Open"
    elif roll < 0.975:                    # trade settled internally, not at trustee
        trustee_par = 0.0
        btype, age = "Missing at Trustee", random.randint(1, 25)
        status = "Escalated" if age > 15 else "Open"
    else:                                 # trustee shows a position we don't
        trustee_par = round(internal,2)
        internal = 0.0
        btype, age = "Missing Internally", random.randint(1, 30)
        status = "Escalated" if age > 15 else "Open"
    trustee.append(dict(recon_id=rid, deal_id=a["deal_id"], asset_id=a["asset_id"],
        as_of_date=asof, trustee_par=trustee_par, internal_par=round(internal,2),
        break_amount=round(trustee_par-internal,2), break_type=btype,
        age_days=age, status=status))

# ---------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------
def write_csv(name, rows, cols):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

write_csv("rating_scale.csv",
    [dict(moodys_rating=r[0], rating_factor=r[1], rank_order=r[2], is_ccc=r[3]) for r in RATING_SCALE],
    ["moodys_rating","rating_factor","rank_order","is_ccc"])
write_csv("deals.csv", DEALS,
    ["deal_id","deal_name","manager","deal_type","trustee","currency",
     "closing_date","reinvestment_end","stated_maturity","target_par"])
write_csv("tranches.csv", tranches,
    ["tranche_id","deal_id","class_name","moodys_rating","seniority_rank",
     "original_balance","current_balance","coupon_spread_bps","is_deferrable",
     "oc_trigger_pct","ic_trigger_pct"])
write_csv("obligors.csv", obligors,
    ["obligor_id","obligor_name","industry","country","moodys_rating"])
write_csv("assets.csv", assets,
    ["asset_id","deal_id","obligor_id","facility_name","lien_type","par_amount",
     "market_price","coupon_spread_bps","base_rate_pct","purchase_date",
     "maturity_date","moodys_rating","is_defaulted","is_cov_lite"])
write_csv("collections.csv", collections,
    ["collection_id","deal_id","period","payment_date","interest_collections","principal_collections"])
write_csv("distributions.csv", distributions,
    ["distribution_id","deal_id","tranche_id","period","payment_date","waterfall_step",
     "interest_due","interest_paid","principal_paid","deferred_interest"])
write_csv("compliance_tests.csv", compliance,
    ["test_id","deal_id","period","test_category","test_name","threshold_value",
     "actual_value","threshold_type","result"])
write_csv("trustee_positions.csv", trustee,
    ["recon_id","deal_id","asset_id","as_of_date","trustee_par","internal_par",
     "break_amount","break_type","age_days","status"])

# ---------------------------------------------------------------------
# Load into SQLite
# ---------------------------------------------------------------------
DB = os.path.join(HERE, "clo.sqlite")
# Build on local disk first (SQLite dislikes some mounted filesystems), then copy.
import tempfile, shutil
TMP_DB = os.path.join(tempfile.gettempdir(), "clo_build.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
con = sqlite3.connect(TMP_DB)
with open(os.path.join(HERE, "sql", "00_schema.sql")) as f:
    con.executescript(f.read())

def load(table, rows, cols):
    ph = ",".join("?"*len(cols))
    con.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({ph})",
                    [tuple(r[c] for c in cols) for r in rows])

load("rating_scale",
     [dict(moodys_rating=r[0], rating_factor=r[1], rank_order=r[2], is_ccc=r[3]) for r in RATING_SCALE],
     ["moodys_rating","rating_factor","rank_order","is_ccc"])
load("deals", DEALS, ["deal_id","deal_name","manager","deal_type","trustee","currency",
     "closing_date","reinvestment_end","stated_maturity","target_par"])
load("tranches", tranches, ["tranche_id","deal_id","class_name","moodys_rating","seniority_rank",
     "original_balance","current_balance","coupon_spread_bps","is_deferrable","oc_trigger_pct","ic_trigger_pct"])
load("obligors", obligors, ["obligor_id","obligor_name","industry","country","moodys_rating"])
load("assets", assets, ["asset_id","deal_id","obligor_id","facility_name","lien_type","par_amount",
     "market_price","coupon_spread_bps","base_rate_pct","purchase_date","maturity_date",
     "moodys_rating","is_defaulted","is_cov_lite"])
load("collections", collections, ["collection_id","deal_id","period","payment_date",
     "interest_collections","principal_collections"])
load("distributions", distributions, ["distribution_id","deal_id","tranche_id","period","payment_date",
     "waterfall_step","interest_due","interest_paid","principal_paid","deferred_interest"])
load("compliance_tests", compliance, ["test_id","deal_id","period","test_category","test_name",
     "threshold_value","actual_value","threshold_type","result"])
load("trustee_positions", trustee, ["recon_id","deal_id","asset_id","as_of_date","trustee_par",
     "internal_par","break_amount","break_type","age_days","status"])
con.commit()

# create reporting views
with open(os.path.join(HERE, "sql", "05_views.sql")) as f:
    con.executescript(f.read())
con.commit()

# quick summary
print("Rows loaded:")
for t in ["deals","tranches","obligors","assets","collections","distributions",
          "compliance_tests","trustee_positions"]:
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t:20s} {n:>6d}")
fails = con.execute("SELECT COUNT(*) FROM compliance_tests WHERE result='FAIL'").fetchone()[0]
breaks = con.execute("SELECT COUNT(*) FROM trustee_positions WHERE break_type<>'Matched'").fetchone()[0]
print(f"Compliance FAILs: {fails}   Recon breaks: {breaks}")
con.close()
try:
    if os.path.exists(DB):
        os.remove(DB)
except PermissionError:
    pass
shutil.copy(TMP_DB, DB)
print("Done. DB at", DB)
