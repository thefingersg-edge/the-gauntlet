#!/usr/bin/env python3
"""
fetch_financing.py -- FLOWS-1/2/3 Step 0: OANDA financing terms per instrument.

RUN LOCALLY. The token is read by fetch_oanda.load_token() ($OANDA_API_TOKEN,
~/.oanda_token, or .oanda_token beside fetch_oanda.py), never printed, never
written. Reuses the account and instrument URL builders in
fastbot/scripts/oanda_financing.py rather than a second copy of them.

Records, for each instrument: longRate, shortRate and the days-charged table
(OANDA books the weekend on FRIDAY for SPX500_USD -- each instrument is read,
not assumed). FLOWS-1 charges financing from this; FLOWS-2 and FLOWS-3 use it
only to evidence that their trades cross no 17:00 NY rollover.

    python3 fetch_financing.py --self-test
    python3 fetch_financing.py
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FB = os.path.join(os.path.dirname(HERE), "fastbot", "scripts")
INSTRUMENTS = ["SPX500_USD", "NAS100_USD", "US30_USD", "DE30_EUR",
               "USB10Y_USD", "DE10YB_EUR", "USB30Y_USD"]
OUT = os.path.join(HERE, "data", "financing_snapshot.json")


def parse(payload: dict) -> dict:
    out = {}
    for ins in payload.get("instruments", []):
        fin = ins.get("financing", {}) or {}
        out[ins.get("name")] = dict(
            displayName=ins.get("displayName"), type=ins.get("type"),
            longRate=float(fin.get("longRate", "nan")),
            shortRate=float(fin.get("shortRate", "nan")),
            daysCharged={d["dayOfWeek"]: int(d["daysCharged"])
                         for d in fin.get("financingDaysOfWeek", [])})
    return out


def main(env: str) -> int:
    sys.path.insert(0, FB)
    import oanda_financing as of
    fo = of.load_fo(of.DEFAULT_FO_DIR)
    host, token = fo.HOSTS[env], fo.load_token()
    accts = fo.api_get(of.build_accounts_url(host), token).get("accounts", [])
    if not accts:
        raise SystemExit("no accounts on this token")
    url = of.build_instruments_url(host, accts[0]["id"], instrument=",".join(INSTRUMENTS))
    if token in url:
        raise SystemExit("token leaked into a URL -- refusing to send")
    got = parse(fo.api_get(url, token))
    missing = [i for i in INSTRUMENTS if i not in got]
    snap = dict(fetched_utc=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                env=env, instruments=got, missing=missing)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(snap, fh, indent=2, sort_keys=True)
    print(f"{'instrument':<12}{'long %/yr':>11}{'short %/yr':>12}   days charged Mon..Sun")
    for n, v in got.items():
        days = " ".join(str(v["daysCharged"].get(d, "?")) for d in
                        ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"))
        print(f"{n:<12}{v['longRate']*100:>+11.3f}{v['shortRate']*100:>+12.3f}   {days}")
    if missing:
        print(f"\n  NOT RETURNED (not tradeable on this account?): {missing}")
    print(f"\n  -> {os.path.relpath(OUT, os.path.dirname(HERE))}  sha256 "
          f"{hashlib.sha256(open(OUT,'rb').read()).hexdigest()[:16]}")
    return 0 if not {"SPX500_USD", "USB10Y_USD"} & set(missing) else 1


def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    p = {"instruments": [{"name": "USB10Y_USD", "type": "CFD", "displayName": "US 10Y T-Note",
         "financing": {"longRate": "-0.0654", "shortRate": "0.0154",
                       "financingDaysOfWeek": [{"dayOfWeek": "FRIDAY", "daysCharged": 3},
                                               {"dayOfWeek": "MONDAY", "daysCharged": 1}]}}]}
    r = parse(p)
    check("rates parsed as floats", abs(r["USB10Y_USD"]["longRate"] + 0.0654) < 1e-12)
    check("days-charged table kept per weekday", r["USB10Y_USD"]["daysCharged"]["FRIDAY"] == 3)
    check("instrument URL builder importable", os.path.exists(os.path.join(FB, "oanda_financing.py")))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--env", default="live", choices=("live", "practice"))
    a = ap.parse_args()
    sys.exit(self_test() if a.self_test else main(a.env))
