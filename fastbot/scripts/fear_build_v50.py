#!/usr/bin/env python3
"""v50 / v50.1 -- build the fear table from the hashed raw files ONLY. No prices touched.
Output data/v50/fear_table.csv: for each calendar date d (the last index date included):
  z_EPU, z_GPR, z_TPU, C = mean(z_EPU, z_GPR), C3 = mean(all three).
A_i(d) = log(mean of the 7 calendar days d-6..d) - log(mean of the last 250 observations ending d)
         (TPU: log(mean+1), per v50.1)
z_i(d) = A_i(d) / sd(A_i over the 250 observations before d).
The harness uses C(target - 2 days).  Also data/v50/trends_monthly.csv (reported only)."""
import csv, datetime as dt, hashlib, math, sys
import numpy as np, xlrd, openpyxl

RAW = "../data/v50/raw/"
PIN = {"All_Daily_Policy_Data.csv": "e444f4758a25c96c0527a38aaddcf3dfc742f8540b7c36c930ab74b31cd9142c",
       "data_gpr_daily_recent.xls": "e5376ad7a25c7cbc19fa2d8aa8e8371b3d374dc7940d1a5b2716fda6bc58f6bd",
       "tpu_web_latest_daily.xlsx": "5dc5d9406b1ce79540bc935f199c20e563e7060bed0c0fcf136c34b5c395da9f",
       "Stock_market_crash_google_trend.csv": "56e6be715947373a456e16ea0416ca9ca60ce1f9d22424df1cebce02f3c6a738",
       "Recession_google_trend.csv": "0a3ab409abadda07f50769371b0abc7d1e04065ab2f7bdcf5dc50105d4135c55"}
for f, h in PIN.items():
    if hashlib.sha256(open(RAW + f, "rb").read()).hexdigest() != h:
        sys.exit(f"{f} changed since it was hashed -- refused")

def epu():
    out = {}
    for r in csv.DictReader(open(RAW + "All_Daily_Policy_Data.csv")):
        try: out[dt.date(int(r["year"]), int(r["month"]), int(r["day"]))] = float(r["daily_policy_index"])
        except ValueError: pass
    return out

def gpr():
    s = xlrd.open_workbook(RAW + "data_gpr_daily_recent.xls").sheet_by_index(0)
    h = s.row_values(0); iD, iG = h.index("DAY"), h.index("GPRD"); out = {}
    for k in range(1, s.nrows):
        r = s.row_values(k)
        try: out[dt.datetime.strptime(str(int(r[iD])), "%Y%m%d").date()] = float(r[iG])
        except (ValueError, TypeError): pass
    return out

def tpu():
    ws = openpyxl.load_workbook(RAW + "tpu_web_latest_daily.xlsx", read_only=True)["TPU_DAILY"]
    rows = list(ws.iter_rows(values_only=True)); h = list(rows[0]); iD, iV = h.index("DATE"), h.index("TPUD_index"); out = {}
    for r in rows[1:]:
        if r[iD] is not None and r[iV] is not None: out[r[iD].date()] = float(r[iV])
    return out

def zseries(x, plus1=False):
    ds = sorted(x); v = np.array([x[d] for d in ds]); f = (lambda m: math.log(m + 1)) if plus1 else math.log
    pos = {d: i for i, d in enumerate(ds)}; A = {}
    for i, d in enumerate(ds):
        if i < 249: continue
        w7 = [x[d - dt.timedelta(days=k)] for k in range(7) if d - dt.timedelta(days=k) in pos]
        m7, m250 = np.mean(w7), v[i - 249:i + 1].mean()
        if (not plus1) and (m7 <= 0 or m250 <= 0): continue
        A[d] = f(m7) - f(m250)
    ad = sorted(A); av = np.array([A[d] for d in ad]); Z = {}
    for j, d in enumerate(ad):
        if j < 250: continue
        sd = av[j - 250:j].std(ddof=1)
        if sd > 0: Z[d] = av[j] / sd
    return Z

E, G, T = epu(), gpr(), tpu()
zE, zG, zT = zseries(E), zseries(G), zseries(T, plus1=True)
days = sorted(set(zE) | set(zG))
with open("../data/v50/fear_table.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["date", "z_EPU", "z_GPR", "z_TPU", "C", "C3"])
    n = n3 = 0
    for d in days:
        e, g, t = zE.get(d), zG.get(d), zT.get(d)
        C = (e + g) / 2 if e is not None and g is not None else None
        C3 = (e + g + t) / 3 if None not in (e, g, t) else None
        n += C is not None; n3 += C3 is not None
        f = lambda x: "" if x is None else f"{x:.6f}"
        w.writerow([d.isoformat(), f(e), f(g), f(t), f(C), f(C3)])
first = next(d for d in days if zE.get(d) is not None and zG.get(d) is not None)
first3 = next((d for d in days if None not in (zE.get(d), zG.get(d), zT.get(d))), None)
print(f"raw: EPU {min(E)}..{max(E)} ({len(E)})  GPR {min(G)}..{max(G)} ({len(G)})  TPU {min(T)}..{max(T)} ({len(T)})")
print(f"table: {len(days)} dates;  C from {first} ({n} values);  C3 from {first3} ({n3} values)")
with open("../data/v50/trends_monthly.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["month", "crash", "recession"]); T2 = {}
    for f, k in (("Stock_market_crash_google_trend.csv", 0), ("Recession_google_trend.csv", 1)):
        for line in open(RAW + f).read().splitlines():
            p = line.split(",")
            if len(p) == 2 and len(p[0]) == 7 and p[0][4] == "-":
                T2.setdefault(p[0], [None, None])[k] = p[1].replace("<1", "0.5")
    for m in sorted(T2): w.writerow([m] + T2[m])
print(f"trends: {len(T2)} months")
