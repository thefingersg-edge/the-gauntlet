#!/usr/bin/env python3
"""Fetch historical candles from the OANDA v20 REST API.

Why this matters more than "another data source": your TradingView charts are
OANDA, so this is the *same* feed. The cross-feed reproducibility problem that
dominated the RSI Boll Squeeze analysis -- only 43% of long trades and ~0% of
short trades survived moving from OANDA to Dukascopy -- disappears when the
backtest runs on the feed the chart uses. It is also the feed you would execute
against if you trade with OANDA, which makes it the honest choice for a
backtest.

CREDENTIALS -- never put the token in a file you might share
------------------------------------------------------------
The token is read, in order, from:

  1. the OANDA_API_TOKEN environment variable
  2. ~/.oanda_token          (a file containing just the token)
  3. .oanda_token            (same, in this folder -- gitignored)

    export OANDA_API_TOKEN='your-token-here'
  or
    echo 'your-token-here' > ~/.oanda_token && chmod 600 ~/.oanda_token

The token is never printed, never written to output files, and never included
in an error message.

USAGE
-----
    python fetch_oanda.py --check                       # auth + account test
    python fetch_oanda.py --instrument XAU_USD --probe  # a few recent candles
    python fetch_oanda.py --instrument XAU_USD --start 2005-01-01 --out xauusd_oanda_1h.csv
    python fetch_oanda.py --all                         # the whole test set
    python fetch_oanda.py --self-test                   # offline

NOTES THAT WILL SAVE YOU TIME
-----------------------------
* **Instrument names use an underscore**: XAU_USD, not XAUUSD.
* **5,000 candles per request maximum.** This paginates automatically; 20 years
  of hourly data is roughly 25 requests per instrument.
* **`price` selects bid, ask or mid.** Dukascopy data in this project is BID, so
  `--price B` is the like-for-like comparison. Mid (`M`) is the more usual
  choice for backtesting and is the default. Which one TradingView draws
  depends on the chart's settings -- if you want an exact match, fetch both and
  compare.
* **Incomplete candles are dropped.** The most recent bar is usually still
  forming; including it produces a phantom final trade.
* **History depth varies by instrument and account type.** OANDA does not
  guarantee 20 years. Whatever is returned is reported rather than assumed.
* **Practice and live use different hosts.** A practice token will not
  authenticate against the live host, which presents as a 401.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

HOSTS = {
    "live": "https://api-fxtrade.oanda.com",
    "practice": "https://api-fxpractice.oanda.com",
}

MAX_COUNT = 5000              # OANDA's hard per-request limit

#: The multi-market test set, in OANDA's naming.
INSTRUMENTS = [
    ("XAU_USD", "gold"),
    ("XAG_USD", "silver"),
    ("EUR_USD", "euro"),
    ("GBP_USD", "sterling"),
    ("USD_JPY", "yen"),
    ("AUD_USD", "aussie"),
    ("SPX500_USD", "S&P 500"),
    ("DE30_EUR", "DAX"),
    ("BCO_USD", "Brent crude"),
    ("XCU_USD", "copper"),
]

GRANULARITY_SECONDS = {
    "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
    "H1": 3600, "H4": 14400, "D": 86400,
}


# --------------------------------------------------------------------------
# credentials
# --------------------------------------------------------------------------

def load_token() -> str:
    """Find the API token without ever echoing it."""
    tok = os.environ.get("OANDA_API_TOKEN", "").strip()
    if tok:
        return tok
    for path in (os.path.expanduser("~/.oanda_token"),
                 os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              ".oanda_token")):
        if os.path.exists(path):
            with open(path) as fh:
                tok = fh.read().strip()
            if tok:
                return tok
    raise SystemExit(
        "No OANDA token found.\n"
        "  export OANDA_API_TOKEN='...'\n"
        "or\n"
        "  echo '...' > ~/.oanda_token && chmod 600 ~/.oanda_token\n"
        "Do not paste the token into a chat or commit it to git."
    )


def redact(text: str, token: str) -> str:
    """Strip the token from anything about to be displayed."""
    return text.replace(token, "<redacted>") if token else text


# --------------------------------------------------------------------------
# pure helpers -- unit tested offline
# --------------------------------------------------------------------------

def rfc3339(dt: datetime) -> str:
    """OANDA wants RFC3339 with a Z suffix and no microseconds."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_url(host: str, instrument: str, granularity: str, price: str,
              start: datetime, count: int = MAX_COUNT) -> str:
    q = urllib.parse.urlencode({
        "granularity": granularity,
        "price": price,
        "count": min(count, MAX_COUNT),
        "from": rfc3339(start),
        "includeFirst": "true",
    })
    return f"{host}/v3/instruments/{instrument}/candles?{q}"


def parse_candles(payload: dict, price: str) -> list[dict]:
    """Turn an OANDA response into rows, dropping incomplete candles.

    The `complete` flag is the important part: the most recent candle is
    normally still forming, and including it creates a bar that will change,
    which in a backtest becomes a phantom final trade.
    """
    key = {"M": "mid", "B": "bid", "A": "ask"}.get(price, "mid")
    rows = []
    for c in payload.get("candles", []):
        if not c.get("complete", False):
            continue
        ohlc = c.get(key)
        if not ohlc:
            continue
        rows.append({
            "time": c["time"][:19].replace("T", " "),
            "open": float(ohlc["o"]), "high": float(ohlc["h"]),
            "low": float(ohlc["l"]), "close": float(ohlc["c"]),
            "volume": float(c.get("volume", 0)),
        })
    return rows


def next_start(rows: list[dict], granularity: str) -> datetime | None:
    """Where the following page should begin: one bar after the last one held."""
    if not rows:
        return None
    last = datetime.strptime(rows[-1]["time"], "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=timezone.utc)
    return last + timedelta(seconds=GRANULARITY_SECONDS.get(granularity, 3600))


# --------------------------------------------------------------------------
# network
# --------------------------------------------------------------------------

def api_get(url: str, token: str, timeout: float = 30.0,
            retries: int = 5) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept-Datetime-Format": "RFC3339",
        "Content-Type": "application/json",
    })
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")[:300]
            if exc.code == 401:
                raise SystemExit(
                    "401 Unauthorised. The token was rejected.\n"
                    "  - a PRACTICE token will not work against the live host\n"
                    "    (and vice versa) -- try --env practice\n"
                    "  - check the token has not expired or been revoked")
            if exc.code == 400:
                raise SystemExit(f"400 Bad request: {redact(body, token)}\n"
                                 "Usually a bad instrument name -- OANDA uses "
                                 "XAU_USD, not XAUUSD.")
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(delay); delay *= 2
                continue
            raise SystemExit(f"HTTP {exc.code}: {redact(body, token)}")
        except Exception as exc:                        # noqa: BLE001
            if attempt == retries:
                raise SystemExit(f"request failed: {redact(str(exc), token)}")
            time.sleep(delay); delay *= 2
    raise SystemExit("exhausted retries")


def fetch_instrument(instrument: str, start: datetime, granularity: str,
                     price: str, host: str, token: str,
                     pause: float = 0.15, max_pages: int = 400) -> list[dict]:
    """Page through history until OANDA stops returning new candles."""
    rows, seen, cursor = [], set(), start
    for page in range(max_pages):
        payload = api_get(build_url(host, instrument, granularity, price, cursor),
                          token)
        batch = parse_candles(payload, price)
        fresh = [r for r in batch if r["time"] not in seen]
        if not fresh:
            break
        for r in fresh:
            seen.add(r["time"])
        rows.extend(fresh)
        nxt = next_start(fresh, granularity)
        if nxt is None or nxt >= datetime.now(timezone.utc):
            break
        cursor = nxt
        if page % 5 == 0:
            print(f"    {len(rows):>7,} candles ... {fresh[-1]['time']}")
        time.sleep(pause)
    rows.sort(key=lambda r: r["time"])
    return rows


def write_csv(rows: list[dict], path: str) -> None:
    import csv
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["time", "open", "high", "low",
                                           "close", "volume"])
        w.writeheader()
        w.writerows(rows)


def summarise(rows: list[dict], label: str) -> None:
    if not rows:
        print(f"  {label}: no candles returned")
        return
    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]
    span = (datetime.strptime(rows[-1]["time"], "%Y-%m-%d %H:%M:%S")
            - datetime.strptime(rows[0]["time"], "%Y-%m-%d %H:%M:%S")).days / 365.25
    print(f"  {label}: {len(rows):,} candles  {rows[0]['time'][:10]} -> "
          f"{rows[-1]['time'][:10]}  ({span:.1f}y)")
    print(f"    price {min(closes):,.4f} to {max(closes):,.4f}   "
          f"zero-volume bars {sum(1 for v in vols if v <= 0)}")


# --------------------------------------------------------------------------

def self_test() -> int:
    fails = []

    def check(n, c, d=""):
        print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"  {d}" if not c else ""))
        if not c:
            fails.append(n)

    print("URL and time formatting")
    d = datetime(2024, 6, 1, 12, 30, tzinfo=timezone.utc)
    check("RFC3339 has a Z and no microseconds", rfc3339(d) == "2024-06-01T12:30:00Z",
          rfc3339(d))
    check("naive datetimes treated as UTC",
          rfc3339(datetime(2024, 6, 1, 12, 30)) == "2024-06-01T12:30:00Z")
    u = build_url(HOSTS["live"], "XAU_USD", "H1", "M", d)
    check("instrument in path", "/instruments/XAU_USD/candles" in u)
    check("count capped at 5000", "count=5000" in build_url(
        HOSTS["live"], "XAU_USD", "H1", "M", d, count=99999))
    check("granularity present", "granularity=H1" in u)

    print("\nresponse parsing")
    payload = {"candles": [
        {"complete": True, "volume": 100, "time": "2024-06-01T00:00:00.000000000Z",
         "mid": {"o": "2000.1", "h": "2005.2", "l": "1999.0", "c": "2003.3"},
         "bid": {"o": "2000.0", "h": "2005.1", "l": "1998.9", "c": "2003.2"}},
        {"complete": True, "volume": 50, "time": "2024-06-01T01:00:00.000000000Z",
         "mid": {"o": "2003.3", "h": "2006.0", "l": "2002.0", "c": "2004.0"},
         "bid": {"o": "2003.2", "h": "2005.9", "l": "2001.9", "c": "2003.9"}},
        {"complete": False, "volume": 7, "time": "2024-06-01T02:00:00.000000000Z",
         "mid": {"o": "2004.0", "h": "2004.5", "l": "2003.5", "c": "2004.2"},
         "bid": {"o": "2003.9", "h": "2004.4", "l": "2003.4", "c": "2004.1"}},
    ]}
    rows = parse_candles(payload, "M")
    check("incomplete candle dropped", len(rows) == 2, f"got {len(rows)}")
    check("mid prices used", abs(rows[0]["close"] - 2003.3) < 1e-9)
    check("bid selectable", abs(parse_candles(payload, "B")[0]["close"] - 2003.2) < 1e-9)
    check("time normalised", rows[0]["time"] == "2024-06-01 00:00:00", rows[0]["time"])
    check("volume carried", rows[0]["volume"] == 100)
    check("empty response is empty list", parse_candles({}, "M") == [])

    print("\npagination")
    n = next_start(rows, "H1")
    check("next page starts one bar after the last",
          n == datetime(2024, 6, 1, 2, 0, tzinfo=timezone.utc), str(n))
    check("H4 steps four hours",
          next_start(rows, "H4") == datetime(2024, 6, 1, 5, 0, tzinfo=timezone.utc))
    check("no rows -> no cursor", next_start([], "H1") is None)

    print("\ncredential safety")
    check("token redacted from messages",
          redact("failed with abc123 in it", "abc123") == "failed with <redacted> in it")
    check("no token in a built URL", "abc123" not in build_url(
        HOSTS["live"], "XAU_USD", "H1", "M", d))

    print("\n" + "=" * 58)
    if fails:
        print(f"{len(fails)} FAILED: {', '.join(fails)}")
        return 1
    print("all checks passed (network path untested -- run --check first)")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--instrument", default="XAU_USD")
    ap.add_argument("--granularity", default="H1", choices=sorted(GRANULARITY_SECONDS))
    ap.add_argument("--price", default="M", choices=["M", "B", "A"],
                    help="M=mid (default), B=bid (matches the Dukascopy data here)")
    ap.add_argument("--start", default="2005-01-01")
    ap.add_argument("--out", default=None)
    ap.add_argument("--env", default="live", choices=sorted(HOSTS))
    ap.add_argument("--pause", type=float, default=0.15)
    ap.add_argument("--all", action="store_true", help="fetch the whole test set")
    ap.add_argument("--probe", action="store_true", help="a few recent candles only")
    ap.add_argument("--check", action="store_true", help="verify auth only")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())

    token = load_token()
    host = HOSTS[args.env]
    print(f"host: {host}   (token loaded, not displayed)")

    if args.check:
        p = api_get(build_url(host, "XAU_USD", "H1", "M",
                              datetime.now(timezone.utc) - timedelta(days=3), 5),
                    token)
        rows = parse_candles(p, "M")
        print(f"auth OK -- {len(rows)} recent XAU_USD candles returned")
        for r in rows[-3:]:
            print(f"    {r['time']}  close {r['close']}")
        return

    if args.probe:
        start = datetime.now(timezone.utc) - timedelta(days=5)
        rows = parse_candles(api_get(build_url(host, args.instrument,
                                               args.granularity, args.price,
                                               start, 20), token), args.price)
        summarise(rows, args.instrument)
        for r in rows[-5:]:
            print(f"    {r['time']}  O {r['open']} H {r['high']} "
                  f"L {r['low']} C {r['close']}  vol {r['volume']:.0f}")
        return

    start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    targets = INSTRUMENTS if args.all else [(args.instrument, "")]

    for inst, note in targets:
        out = (args.out if args.out and not args.all
               else f"{inst.replace('_', '').lower()}_oanda_"
                    f"{args.granularity.lower()}.csv")
        if args.all and os.path.exists(out):
            print(f"--- {inst}: {out} exists, skipping")
            continue
        print(f"\n--- {inst} {('(' + note + ')') if note else ''} -> {out}")
        try:
            rows = fetch_instrument(inst, start, args.granularity, args.price,
                                    host, token, args.pause)
        except SystemExit as exc:
            print(f"    FAILED: {exc}")
            continue
        if not rows:
            print("    no candles returned -- check the instrument name")
            continue
        write_csv(rows, out)
        summarise(rows, inst)
        print(f"    wrote {out}")

    print("\nNext: compare against the Dukascopy files with")
    print("  python feed_compare.py --a xauusd_1h.csv --b xauusd_oanda_h1.csv")


if __name__ == "__main__":
    main()
