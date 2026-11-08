#!/usr/bin/env python3
"""Pull YOUR OWN OANDA fill and financing history, READ-ONLY, for the cost audit (fills_audit.py).
RUN LOCALLY on the Mac. The token is found by fetch_oanda.load_token() ($OANDA_API_TOKEN, ~/.oanda_token,
or .oanda_token beside fetch_oanda.py). It is never printed or written. Only HTTP GET is used; this file
contains no order, close, modify or cancel call of any kind.

Writes data/fills/fills.csv and data/fills/financing.csv with ONLY the fields the audit needs:
time, instrument, units, price, bid/ask at the fill, halfSpreadCost, pl, financing, commission,
reason, trade ids. No account id, balance, margin or personal detail is written.

    python3 oanda_fills_pull.py --self-test
    python3 oanda_fills_pull.py                 # live account, first account on the token
    python3 oanda_fills_pull.py --env practice  # if your trades are on the demo account
"""
import argparse, csv, hashlib, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
FO_DIR = next(d for d in (os.path.join(HERE, "..", "..", "silver15", "scripts"), os.path.join(HERE, "..", "..", "pineport"))
              if os.path.exists(os.path.join(d, "fetch_oanda.py")))
OUT = os.path.join(HERE, "..", "data", "fills")
CHUNK = 1000

def build_summary_url(host, account): return f"{host}/v3/accounts/{account}/summary"
def build_accounts_url(host): return f"{host}/v3/accounts"
def build_range_url(host, account, lo, hi, types):
    return f"{host}/v3/accounts/{account}/transactions/idrange?from={lo}&to={hi}&type={','.join(types)}"

FILL_COLS = ["time", "fill_id", "role", "trade_id", "instrument", "units", "price", "bid", "ask",
             "halfSpreadCost", "pl", "financing", "reason"]

def fill_rows(t):
    """One row per (fill, trade it opened, closed or reduced). Keeps only what the audit needs."""
    fp = t.get("fullPrice", {}) or {}
    bid = (fp.get("bids") or [{}])[0].get("price", ""); ask = (fp.get("asks") or [{}])[0].get("price", "")
    base = [t.get("time", ""), t.get("id", "")]
    out = []
    o = t.get("tradeOpened")
    if o:
        out.append(base + ["open", o.get("tradeID", ""), t.get("instrument", ""), o.get("units", ""),
                           o.get("price", t.get("price", "")), bid, ask, o.get("halfSpreadCost", ""), "", "", t.get("reason", "")])
    for c in (t.get("tradesClosed") or []) + ([t["tradeReduced"]] if t.get("tradeReduced") else []):
        out.append(base + ["close", c.get("tradeID", ""), t.get("instrument", ""), c.get("units", ""),
                           c.get("price", t.get("price", "")), bid, ask, c.get("halfSpreadCost", ""),
                           c.get("realizedPL", ""), c.get("financing", ""), t.get("reason", "")])
    return out

def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    src = open(__file__).read()
    bad = ["meth" + "od=", "url" + "open(", "requ" + "ests.", "/ord" + "ers", "/clo" + "se"]
    check("no HTTP method override, no direct urlopen/requests, no order or close endpoint in this file",
          not any(b in src for b in bad))
    check("URL builders take no token argument", all("token" not in f.__code__.co_varnames
          for f in (build_summary_url, build_accounts_url, build_range_url)))
    rs = fill_rows({"time": "T", "id": "9", "instrument": "NAS100_USD", "units": "-1", "price": "100",
                    "fullPrice": {"bids": [{"price": "99.9"}], "asks": [{"price": "100.1"}]},
                    "tradeOpened": {"tradeID": "10", "units": "-1", "price": "99.9", "halfSpreadCost": "0.1"},
                    "tradesClosed": [{"tradeID": "7", "units": "1", "price": "99.9", "realizedPL": "2.5", "halfSpreadCost": "0.1"}],
                    "accountBalance": "SECRET", "accountID": "SECRET"})
    check("one row per trade touched, bid/ask kept, balance and account id dropped",
          len(rs) == 2 and rs[0][7] == "99.9" and rs[1][2] == "close" and rs[1][10] == "2.5" and not any("SECRET" in x for r in rs for x in r))
    print("ALL PASS" if ok else "FAILURES ABOVE"); return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--env", default="live", choices=("live", "practice"))
    ap.add_argument("--self-test", action="store_true"); a = ap.parse_args()
    if a.self_test: sys.exit(self_test())
    sys.path.insert(0, FO_DIR); import fetch_oanda as fo
    host = fo.HOSTS[a.env]; token = fo.load_token()
    try:
        accts = fo.api_get(build_accounts_url(host), token).get("accounts", [])
        if not accts: sys.exit("no accounts visible on this token")
        acct = accts[0]["id"]; print(f"  {a.env}: {len(accts)} account(s) visible, using the first (...{acct[-4:]})")
        last = int(fo.api_get(build_summary_url(host, acct), token)["lastTransactionID"])
        fills, fin = [], []
        for lo in range(1, last + 1, CHUNK):
            hi = min(lo + CHUNK - 1, last)
            for t in fo.api_get(build_range_url(host, acct, lo, hi, ["ORDER_FILL", "DAILY_FINANCING"]), token).get("transactions", []):
                if t.get("type") == "ORDER_FILL": fills.extend(fill_rows(t))
                elif t.get("type") == "DAILY_FINANCING": fin.append([t.get("time", ""), t.get("financing", "")])
    except Exception as e:
        sys.exit(f"  request failed: {fo.redact(str(e), token)[:200]}")
    os.makedirs(OUT, exist_ok=True)
    for name, cols, rows in (("fills.csv", FILL_COLS, fills), ("financing.csv", ["time", "financing"], fin)):
        p = os.path.join(OUT, name)
        with open(p, "w", newline="") as fh: w = csv.writer(fh); w.writerow(cols); w.writerows(rows)
        print(f"  {name}: {len(rows)} rows   sha256 {hashlib.sha256(open(p, 'rb').read()).hexdigest()}")

if __name__ == "__main__":
    main()
