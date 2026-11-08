#!/usr/bin/env python3
"""PREREGISTRATION_v30 -- fetch the free positioning, sentiment and
prediction-market data. RUN LOCALLY (the sandboxes cannot reach these
sites). Public data, read only, no keys, no accounts.

Everything raw is kept under ../data/sentiment/ so the measurement can be
re-derived; a manifest records what each source returned. Re-running
skips what is already on disk.

    python3 sentiment_fetch.py --self-test
    python3 sentiment_fetch.py              # ~10-15 minutes
"""
from __future__ import annotations

import argparse, csv, datetime as dt, io, json, os, re, sys, time, zipfile
import urllib.error, urllib.parse, urllib.request

VERSION = "1.1"
OUT = "../data/sentiment"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) fastbot-research/1.0"}
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)

CFTC = "https://www.cftc.gov/files/dea/history/"
TFF_FILES = ["fin_fut_txt_2006_2016.zip"] + [f"fut_fin_txt_{y}.zip"
                                             for y in range(2017, 2027)]
DIS_FILES = ["fut_disagg_txt_hist_2006_2016.zip"] + [
    f"fut_disagg_txt_{y}.zip" for y in range(2017, 2027)]
#: CFTC contract market codes, section 2 of v30
CODES = {"13874A": "SPX500_USD", "209742": "NAS100_USD",
         "124603": "US30_USD", "099741": "EUR_USD", "088691": "XAU_USD"}
WANT = {"oi": "open_interest_all",
        "lev_l": "lev_money_positions_long_all",
        "lev_s": "lev_money_positions_short_all",
        "am_l": "asset_mgr_positions_long_all",
        "am_s": "asset_mgr_positions_short_all",
        "mm_l": "m_money_positions_long_all",
        "mm_s": "m_money_positions_short_all"}

AAII = "https://www.aaii.com/files/surveys/sentiment.xls"
CBOE = {"skew.csv": "https://cdn.cboe.com/api/global/us_indices/daily_prices/SKEW_History.csv",
        "equitypc.csv": "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv",
        "totalpc.csv": "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/totalpc.csv"}
KALSHI_BASES = ["https://api.elections.kalshi.com/trade-api/v2",
                "https://external-api.kalshi.com/trade-api/v2"]
KALSHI_SERIES = ("KXCPI", "KXCPICORE", "KXPAYROLLS", "KXU3")


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def norm(h):
    return re.sub(r"[^a-z0-9_]", "", h.strip().strip('"').lower().replace(" ", "_"))


def parse_date(s):
    #: v1.1 -- the 2006-2016 TFF file writes "12/27/2016 12:00:00 AM";
    #: v1.0 rejected the time part and dropped every row of that file.
    s = s.strip().strip('"').split(" ")[0]
    for f in ("%Y-%m-%d", "%m/%d/%Y", "%y%m%d", "%Y%m%d", "%m_%d_%Y"):
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def cftc_rows(blob):
    """Yield normalised rows for our five markets from one CFTC zip."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    for name in z.namelist():
        text = z.read(name).decode("latin-1")
        rd = csv.reader(io.StringIO(text))
        head = [norm(h) for h in next(rd)]
        idx = {h: i for i, h in enumerate(head)}
        dcol = next((h for h in head if h.startswith("report_date_as_yyyy")), None) \
            or next((h for h in head if h.startswith("report_date")), None) \
            or next((h for h in head if h.startswith("as_of_date")), None)
        ccol = "cftc_contract_market_code"
        if dcol is None or ccol not in idx:
            continue
        for row in rd:
            if len(row) <= idx[ccol]:
                continue
            code = row[idx[ccol]].strip().strip('"')
            if code not in CODES:
                continue
            out = {"instrument": CODES[code], "code": code,
                   "name": row[idx.get("market_and_exchange_names", 0)].strip(),
                   "report_date": parse_date(row[idx[dcol]])}
            for k, col in WANT.items():
                v = row[idx[col]].strip() if col in idx and idx[col] < len(row) else ""
                out[k] = v
            if out["report_date"] is None and "as_of_date_in_form_yymmdd" in idx:
                out["report_date"] = parse_date(row[idx["as_of_date_in_form_yymmdd"]])
            if out["report_date"]:
                yield out


def self_test():
    ok = True
    def check(n, c, d=""):
        nonlocal ok; ok &= bool(c)
        print(f"  [{'PASS' if c else 'FAIL'}] {n}" + (f"   {d}" if d else ""))
    print(f"sentiment_fetch.py v{VERSION} self-test\n")
    check("CFTC headers normalise", norm(' "Lev_Money_Positions_Long_All" ')
          == "lev_money_positions_long_all")
    check("dates in every CFTC format parse",
          parse_date("2020-06-09") == parse_date("06/09/2020")
          == parse_date("200609") == dt.date(2020, 6, 9))
    body = ('"Market_and_Exchange_Names","Report_Date_as_YYYY-MM-DD",'
            '"CFTC_Contract_Market_Code","Open_Interest_All",'
            '"Lev_Money_Positions_Long_All","Lev_Money_Positions_Short_All"\n'
            '"E-MINI S&P 500 - CME","2020-06-09","13874A","100","30","50"\n'
            '"SOMETHING ELSE","2020-06-09","999999","1","1","1"\n')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("f.txt", body)
    rows = list(cftc_rows(buf.getvalue()))
    check("only our five markets are kept, mapped to our instruments",
          len(rows) == 1 and rows[0]["instrument"] == "SPX500_USD"
          and rows[0]["lev_l"] == "30" and rows[0]["am_l"] == "")
    check("the 2006-2016 file's date-with-time parses (v1.1)",
          parse_date("12/27/2016 12:00:00 AM") == dt.date(2016, 12, 27))
    check("five markets, DE30 has none", len(CODES) == 5
          and "DE30_EUR" not in CODES.values())
    check("no order, execute, submit or position name in this file",
          not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    os.makedirs(f"{OUT}/cftc", exist_ok=True)
    os.makedirs(f"{OUT}/kalshi", exist_ok=True)
    man = {"fetched_utc": dt.datetime.utcnow().isoformat() + "Z", "version": VERSION}
    print(f"sentiment_fetch.py v{VERSION}   PREREGISTRATION_v30 -- public data only\n")

    # 1. CFTC
    rows = []
    for kind, files in (("tff", TFF_FILES), ("disagg", DIS_FILES)):
        for f in files:
            p = f"{OUT}/cftc/{f}"
            if not os.path.exists(p):
                try:
                    blob, _ = get(CFTC + f)
                    open(p, "wb").write(blob)
                    time.sleep(0.5)
                except Exception as e:                           # noqa: BLE001
                    print(f"  CFTC {f}: FAILED ({type(e).__name__} {getattr(e, 'code', '')})")
                    continue
            got = list(cftc_rows(open(p, "rb").read()))
            for r in got:
                r["report"] = kind
            rows += got
            print(f"  CFTC {f:<34} {len(got):>5} rows for our markets")
    keys = ["report", "instrument", "code", "name", "report_date"] + list(WANT)
    with open(f"{OUT}/cftc_positions.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["instrument"], r["report_date"])):
            w.writerow(r)
    names = sorted({(r["code"], r["name"]) for r in rows})
    man["cftc"] = {"rows": len(rows), "markets": names}
    print(f"  -> cftc_positions.csv, {len(rows):,} rows. Markets found:")
    for c, n in names:
        print(f"       {c}  {n}")

    # 2. AAII
    p = f"{OUT}/aaii_sentiment.xls"
    try:
        blob, ctype = get(AAII)
        if blob[:1] == b"<" or "html" in ctype.lower():
            raise ValueError("got a web page, not the spreadsheet (bot check)")
        open(p, "wb").write(blob)
        man["aaii"] = "ok"
        try:
            import xlrd                                          # noqa: F401
            wb = xlrd.open_workbook(p)
            sh = wb.sheet_by_index(0)
            with open(f"{OUT}/aaii_sentiment.csv", "w", newline="") as fh:
                w = csv.writer(fh)
                for i in range(sh.nrows):
                    w.writerow(sh.row_values(i))
            print("  AAII ok -> aaii_sentiment.csv")
        except ImportError:
            print("  AAII downloaded. To convert: pip3 install xlrd, then re-run")
            man["aaii"] = "downloaded, needs xlrd"
    except Exception as e:                                       # noqa: BLE001
        man["aaii"] = f"failed: {e}"
        print(f"  AAII FAILED ({e}).\n     Manual: open aaii.com/sentimentsurvey,"
              f" download the historical spreadsheet, open it in Excel and\n"
              f"     Save As CSV to data/sentiment/aaii_sentiment.csv")

    # 3. CBOE
    man["cboe"] = {}
    for fn, url in CBOE.items():
        try:
            blob, _ = get(url)
            open(f"{OUT}/cboe_{fn}", "wb").write(blob)
            man["cboe"][fn] = len(blob)
            print(f"  CBOE {fn:<14} ok, {len(blob):,} bytes")
        except Exception as e:                                   # noqa: BLE001
            man["cboe"][fn] = f"failed: {type(e).__name__}"
            print(f"  CBOE {fn:<14} FAILED ({type(e).__name__})")

    # 4. Kalshi -- markets, then hourly candles around each release
    base = None
    for b in KALSHI_BASES:
        try:
            get(f"{b}/series/KXCPI", timeout=20)
            base = b
            break
        except Exception:                                        # noqa: BLE001
            continue
    man["kalshi"] = {"base": base, "series": {}}
    if base is None:
        print("  Kalshi: no API base reachable")
    else:
        print(f"  Kalshi via {base}")
        for s in KALSHI_SERIES:
            #: v1.1 -- v1.0 read only /markets, which holds the latest
            #: settled events; older ones live under /historical/markets.
            mk, seen = [], set()
            for path, extra in (("/markets", {"status": "settled"}),
                                ("/historical/markets", {})):
                cursor = ""
                while True:
                    q = dict(series_ticker=s, limit=1000, **extra)
                    if cursor:
                        q["cursor"] = cursor
                    try:
                        blob, _ = get(f"{base}{path}?" + urllib.parse.urlencode(q))
                    except Exception as e:                       # noqa: BLE001
                        print(f"    {s}: {path} FAILED ({type(e).__name__})")
                        break
                    js = json.loads(blob)
                    for m in js.get("markets", []):
                        if m.get("ticker") not in seen:
                            seen.add(m.get("ticker"))
                            m["_source"] = path
                            mk.append(m)
                    cursor = js.get("cursor") or ""
                    if not cursor:
                        break
                    time.sleep(0.3)
            json.dump(mk, open(f"{OUT}/kalshi/{s}_markets.json", "w"))
            ok_c = fail_c = 0
            for m in mk:
                t = m.get("ticker")
                p = f"{OUT}/kalshi/{t}_candles.json"
                if not t or os.path.exists(p):
                    continue
                close = m.get("close_time") or m.get("expiration_time")
                try:
                    ct = dt.datetime.fromisoformat(close.replace("Z", "+00:00"))
                except Exception:                                # noqa: BLE001
                    fail_c += 1
                    continue
                q = {"start_ts": int((ct - dt.timedelta(days=3)).timestamp()),
                     "end_ts": int(ct.timestamp()), "period_interval": 60}
                got = None
                paths = (f"/series/{s}/markets/{t}/candlesticks",
                         f"/historical/markets/{t}/candlesticks")
                if m.get("_source") == "/historical/markets":
                    paths = paths[::-1]
                for path in paths:
                    try:
                        blob, _ = get(base + path + "?" + urllib.parse.urlencode(q))
                        got = blob
                        break
                    except Exception:                            # noqa: BLE001
                        continue
                if got is None:
                    fail_c += 1
                else:
                    open(p, "wb").write(got)
                    ok_c += 1
                time.sleep(0.25)
            man["kalshi"]["series"][s] = {"markets": len(mk), "candles_ok": ok_c,
                                          "candles_failed": fail_c}
            print(f"    {s:<11} {len(mk):>5} settled markets   candles ok {ok_c}"
                  f"   failed {fail_c}")

    json.dump(man, open(f"{OUT}/manifest.json", "w"), indent=1, default=str)
    print(f"\n  manifest -> {OUT}/manifest.json. Paste me this whole output.")


if __name__ == "__main__":
    main()
