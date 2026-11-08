"""
common.py -- shared machinery for the FLOWS harnesses. No statistic about
any hypothesis is computed here; this file only loads, aligns and tests.

Everything a pre-registration fixes lives in the harness that implements it.
What lives here is plumbing that must be identical across the three:
hash pinning, bid/ask loading with grid checks, 17:00-New-York daily bars,
Newey-West OLS, Benjamini-Hochberg, eras, and the financing model.
"""
from __future__ import annotations
import hashlib, json, math, os, sys
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
V24 = os.path.join(ROOT, "fastbot", "data", "v24")
FDATA = os.path.join(HERE, "data")
NY = ZoneInfo("America/New_York")

#: sha256 of each frozen document, from its first commit (362d65e, def0b2c,
#: 216b8eb, f5d4b99). A harness refuses to run if its document has changed.
PINS = {
    "MONTHEND":  "e8cb9ac5365b444ffb2d76bb442105af23eac16b4ccd7c8567bc192e6ed7a6ed",
    "REFUNDING": "1325073b110229cc655495de57f5f4b2ffc7934ea172dd7c4868deef32ac1f07",
    "OVERNIGHT": "2227514a37ad46ad2fce7883dba46407861bc248c24a7b8a5e04f3af45f727ac",
    "EVENTS":    "57be5deac2e99aff280a975e816422065c696409614f4c86eeb43341ef8fa7e5",
    # FLOWS-4/5/6, pre-registered at d884bc5 (the NATGAS pin is the committed
    # text; section 2 was reworded before that first commit)
    "ANNOUNCE":  "9705a7250ea1af834dbbd7a9e5620bd0cfb19e6909252244a412562d7230a2a6",
    "ECBDRIFT":  "32e7cd4778bbf0eae05622ab3b67d23aaba0db54f4a698b1526c6f2721f99dda",
    "NATGAS":    "7467468391216cd2c57bc7c83f64b4ce3ece49abaed122cf176c2e6f99997bc9",
    "LOWVIX":    "03fbeac589cd3381f45892070695ea6248133fc34fe2c7e59f51889aa6cf54eb",   # FLOWS-7, b6b25b0
    # FLOWS-8..15, pre-registered at 8db5e79
    "FIXES":      "9d075e40a14d1eac346663bd4f392ffcc5f157bd8168e6f1046ac6c0a91975ce",
    "EARNINGS":   "4df6d4ae2ab641120871f3811ff11a817c8d95930b3920324e0a8369aeb6f6ab",
    "PREHOLIDAY": "b6aa1c2f3ad9989b055b493e0db094d73b1325376c58abb318ea10b537de80f7",
    "AUCTIONS":   "1c200ebf25d15d4526bfe9c95f84c89ed470972d3dfe858455e8a9ca712e0dca",
    "HALLOWEEN":  "e7101aa18c30aff09308e6bb6989b13e48925da2cf3611d6f70cc09610b19078",
    "FXVALUE":    "d36d1a8bb54fb9b7e3cf33c1107676dfe34140d4a1e4d8e353220be9e335bb87",
    "MACRO":      "554dcc8507d8d51a12410a7e44b8c31128123c9984a7212b9f89305afa5f167e",
    "VEHICLE":    "23d6dde494c51c051fca7ec79d338ffbfc63e76ca8b9c6c0c0323eca6124e7d9",
    "EARNINGS_A1": "70c6018a20f0a902842f2a0056840a30f9421bbb29dafca878dbce8a10847324",
    "FXVALUE_A1": "07f9698213c703bebda8afde0934f2893fdcfcebb1bd1615e4c85f14f7f9d52d",
    "AUCTION_EVENTS": "d1bfd6015b169f93dcaec6de7647a201d3023a48edcedf2e492b13954ff88d97",     # Mac, 2026-09-28
    "TSYFUT":     "8846965a8e3378264ab58bbd52e4fa68c6be4260bf2b5ff98efd1ef4f2786ce0",   # FLOWS-17, 2026-10-30 (relabelled from 16 before any data: MACDFF holds 16)
    "ANNOUNCE_A1": "056f6f5d7ef7509f22b8205ccbd2de45356029128b00fae80a5cbbfc15bab2bb",   # GDP dates = GDPC1 vintages
    # Step 0 tables. A table not listed here has not been frozen yet, and a
    # harness that needs it refuses to run.
    "EIA_EVENTS": "9f208aac9db3108bc9decfe2b52cc21667bcb81e1e4abdf9b9e485946874c1f1",
    "ANNOUNCE_EVENTS": "cfcbad38d974772d4fad076fabafe2150f54a30f666a89342e31209c1caeb05f",  # Mac, 2026-09-27
    "PREHOLIDAY_EVENTS": "0a9d89b3135536f088b0ddfa49afb3a5d4fb5d516aa228a7b5949413f223a23f",   # offline rule, 2026-09-28
    "HOLDOUT_EVENTS": "09dfd6805ce67fc6b21d9b00b47b31b6fc1e5eeb645e88768d2c7eff568c845b",   # Mac, 2026-09-28
    "ECB_EVENTS": "1b5b4968b28bc6721162e212fc147fb1f290d261a728f19f295bcb284a5cc7ce",       # Mac, 2026-09-27
}
#: data tables pinned by name (everything else in PINS is a PREREGISTRATION)
PIN_FILES = {"EVENTS": "refunding_events.csv", "EIA_EVENTS": "eia_events.csv",
             "ANNOUNCE_EVENTS": "announce_events.csv", "ECB_EVENTS": "ecb_events.csv",
             "HOLDOUT_EVENTS": "holdout_events.csv", "PREHOLIDAY_EVENTS": "preholiday_events.csv",
             "AUCTION_EVENTS": "auction_events.csv", "EARNINGS_UNIVERSE": "earnings_universe.csv",
             "EARNINGS_EVENTS": "earnings_events.csv"}
ERAS = (("E1", "2005-01-01", "2012-03-31"),
        ("E2", "2012-04-01", "2019-06-30"),
        ("E3", "2019-07-01", "2026-08-31"))
END = pd.Timestamp("2026-08-31")          # last trading date used by all three

#: where each instrument's 15-minute bid/ask files live
SOURCES = {
    "SPX500_USD": V24, "NAS100_USD": V24, "US30_USD": V24, "DE30_EUR": V24,
    "USB10Y_USD": FDATA, "USB30Y_USD": FDATA, "DE10YB_EUR": FDATA,
    "NATGAS_USD": FDATA, "EUR_USD": V24,
    **{p: FDATA for p in ("USD_JPY", "GBP_USD", "AUD_USD", "USD_CAD", "USD_CHF", "NZD_USD", "USD_NOK", "USD_SEK")},
}


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def check_pin(name: str) -> str:
    path = (os.path.join(FDATA, PIN_FILES[name]) if name in PIN_FILES
            else os.path.join(HERE, f"PREREGISTRATION_{name}.md"))
    if name not in PINS:
        raise SystemExit(f"\n  REFUSING TO RUN: {os.path.relpath(path, ROOT)} is not frozen yet.\n"
                         f"  Build it (Step 0), then pin its sha256 in common.PINS['{name}'] and commit.")
    got = sha256(path)
    if got != PINS[name]:
        raise SystemExit(f"\n  REFUSING TO RUN: {os.path.relpath(path, ROOT)} has changed.\n"
                         f"  pinned {PINS[name][:16]}...  found {got[:16]}...\n"
                         f"  A frozen document may not change after registration.")
    return got


def _file(inst: str, side: str) -> str:
    stem = inst.replace("_", "").lower()
    return os.path.join(SOURCES[inst], f"{stem}_{side}_15m.csv")


def load_side(inst: str, side: str) -> pd.DataFrame:
    d = pd.read_csv(_file(inst, side), usecols=["time", "open", "high", "low", "close"])
    d["time"] = pd.to_datetime(d["time"], utc=True)
    return d.set_index("time")


def grid_problems(d: pd.DataFrame) -> list:
    """The checks pull_m1 --verify would have run: order, duplicates, grid."""
    out = []
    t = d.index
    if not t.is_monotonic_increasing:
        out.append("not sorted")
    dup = int(t.duplicated().sum())
    if dup:
        out.append(f"{dup} duplicate timestamps")
    # as_unit("ns"): pandas 3 parses text to 's'/'us' resolution, so raw
    # asi8 is not nanoseconds everywhere (found on the Mac venv, 2026-09-26)
    off = int(((t.as_unit("ns").asi8 // 10**9) % 900 != 0).sum())
    if off:
        out.append(f"{off} bars off the 15-minute grid")
    return out


def load_bidask(inst: str, end: pd.Timestamp = END) -> pd.DataFrame:
    """Bid, ask and mid on the bars both sides share, bar START times in UTC,
    truncated at the 17:00 NY rollover that ends trading date `end`."""
    b, a = load_side(inst, "bid"), load_side(inst, "ask")
    for side, d in (("bid", b), ("ask", a)):
        p = grid_problems(d)
        if p:
            raise SystemExit(f"{inst} {side}: {', '.join(p)}")
    j = b.join(a, lsuffix="_b", rsuffix="_a", how="inner")
    for c in ("open", "high", "low", "close"):
        j[f"{c}_m"] = (j[f"{c}_b"] + j[f"{c}_a"]) / 2.0
    cut = pd.Timestamp(end.date(), tz=NY) + pd.Timedelta(hours=17)
    return j[j.index < cut.tz_convert("UTC")]


def trading_date(t_utc: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """17:00 New York rollover, DST-aware (pineport make_daily.py, R4).
    A bar belongs to the trading date whose 17:00 NY close it precedes;
    Saturday folds to Friday and Sunday to Monday."""
    ny = t_utc.tz_convert(NY).tz_localize(None) - pd.Timedelta(hours=17)
    td = ny.normalize() + pd.Timedelta(days=1)
    dow = td.dayofweek
    td = td.where(dow != 5, td - pd.Timedelta(days=1))
    td = td.where(dow != 6, td + pd.Timedelta(days=1))
    return pd.DatetimeIndex(td)


def daily(ba: pd.DataFrame, min_bars: int = 4) -> pd.DataFrame:
    """Daily bars on the 17:00-NY grid. Close = the close of the last 15-min
    bar of the trading date (bid, ask and mid); open = the first bar's open."""
    td = trading_date(ba.index)
    g = ba.groupby(td)
    out = pd.DataFrame({
        "open_m": g["open_m"].first(), "open_a": g["open_a"].first(), "open_b": g["open_b"].first(),
        "close_m": g["close_m"].last(), "close_b": g["close_b"].last(), "close_a": g["close_a"].last(),
        "first_bar": g.apply(lambda x: x.index[0]), "last_bar": g.apply(lambda x: x.index[-1]),
        "nbars": g.size()})
    out.index.name = "date"
    return out[out["nbars"] >= min_bars]


def ols_nw(y, X, lags: int):
    """OLS with Newey-West (Bartlett) standard errors. X must include the
    intercept column. Returns (coef, se, t, n)."""
    y = np.asarray(y, float); X = np.asarray(X, float)
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    u = y - X @ b
    Xu = X * u[:, None]
    S = Xu.T @ Xu
    for l in range(1, lags + 1):
        w = 1.0 - l / (lags + 1.0)
        G = Xu[l:].T @ Xu[:-l]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(V))
    return b, se, b / se, n


def p_two_sided(t: float) -> float:
    return math.erfc(abs(t) / math.sqrt(2.0))


def mean_t(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 2:
        return float("nan"), float("nan"), len(x)
    m = x.mean(); se = x.std(ddof=1) / math.sqrt(len(x))
    return m, (m / se if se > 0 else float("nan")), len(x)


def bh(pvals: dict) -> dict:
    ks = [k for k, v in pvals.items() if np.isfinite(v)]
    ps = np.array([pvals[k] for k in ks]); m = len(ps)
    order = np.argsort(ps); q = np.empty(m)
    run = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        run = min(run, ps[i] * m / rank)
        q[i] = run
    return {k: float(q[i]) for i, k in enumerate(ks)}


def era_of(d) -> str:
    d = pd.Timestamp(d)
    for name, a, b in ERAS:
        if pd.Timestamp(a) <= d <= pd.Timestamp(b):
            return name
    return ""


# ---------------------------------------------------------------- financing
def load_fred(series: str) -> pd.Series:
    d = pd.read_csv(os.path.join(FDATA, f"fred_{series.lower()}.csv"), parse_dates=["date"])
    return d.set_index("date")[series.lower()].astype(float) / 100.0


class Financing:
    """Annual financing rate for a long or short CFD position on a date.

    Index CFDs follow the oanda_financing.py method: rate = -(benchmark +
    markup) for longs and benchmark - markup for shorts, with each markup
    calibrated from today's live rate and today's benchmark.

    Bond CFDs carry: a long earns the bond yield and pays the benchmark, so
    long = (yield - benchmark) - markup_long and short = (benchmark - yield)
    - markup_short, markups calibrated the same way. This is the one place
    the implementation goes beyond the pre-registration's wording
    ('benchmark plus OANDA's markup'); it affects FLOWS-1 G7 costs only.

    Charged per 17:00 NY rollover held, times the instrument's days-charged
    table for that weekday, divided by 365.
    """
    WEEK = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")

    def __init__(self, inst: str, snapshot: dict, bench: pd.Series, yld: pd.Series | None = None):
        s = snapshot["instruments"][inst]
        self.inst, self.days = inst, s["daysCharged"]
        self.bench, self.yld = bench.sort_index(), (yld.sort_index() if yld is not None else None)
        today = pd.Timestamp(snapshot["fetched_utc"][:10])
        b0 = self._asof(self.bench, today)
        if self.yld is None:
            self.m_long = -s["longRate"] - b0
            self.m_short = b0 - s["shortRate"]
        else:
            y0 = self._asof(self.yld, today)
            self.m_long = (y0 - b0) - s["longRate"]
            self.m_short = (b0 - y0) - s["shortRate"]

    @staticmethod
    def _asof(s: pd.Series, d) -> float:
        v = s[s.index <= pd.Timestamp(d)]
        return float(v.iloc[-1]) if len(v) else float("nan")

    def rate(self, d, side: str) -> float:
        b = self._asof(self.bench, d)
        if self.yld is None:
            return -(b + self.m_long) if side == "long" else (b - self.m_short)
        y = self._asof(self.yld, d)
        return ((y - b) - self.m_long) if side == "long" else ((b - y) - self.m_short)

    def charge(self, rollover_dates, side: str) -> float:
        """Return contribution (a fraction; negative = paid) of holding one
        unit of notional across the 17:00 NY rollovers on these dates."""
        tot = 0.0
        for d in rollover_dates:
            n = int(self.days.get(self.WEEK[pd.Timestamp(d).dayofweek], 1))
            tot += self.rate(d, side) * n / 365.0
        return tot


def load_snapshot() -> dict:
    return json.load(open(os.path.join(FDATA, "financing_snapshot.json")))


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    ok = True
    def check(n, c):
        nonlocal ok; print(f"  {'PASS' if c else 'FAIL'}  {n}"); ok = ok and bool(c)
    # trading-date assignment across DST, Friday and Sunday
    t = pd.DatetimeIndex(pd.to_datetime([
        "2025-07-10 20:45", "2025-07-10 21:00",     # EDT: 16:45 NY -> Thu, 17:00 NY -> Fri
        "2025-01-09 21:45", "2025-01-09 22:00",     # EST: 16:45 NY -> Thu, 17:00 NY -> Fri
        "2025-07-11 21:00",                         # Fri 17:00 NY -> Friday (make_daily folds Sat->Fri;
                                                    #   markets are shut, such bars are strays)
        "2025-07-13 22:00"], utc=True))             # Sun 18:00 NY -> Monday
    td = [str(x.date()) for x in trading_date(t)]
    check("17:00 NY rollover, EDT", td[0:2] == ["2025-07-10", "2025-07-11"])
    check("17:00 NY rollover, EST", td[2:4] == ["2025-01-09", "2025-01-10"])
    check("stray Friday-evening bar -> Friday; Sunday evening -> Monday (make_daily)",
          td[4:6] == ["2025-07-11", "2025-07-14"])
    # OLS / NW
    rng = np.random.default_rng(1)
    x = rng.normal(size=2000); y = 0.3 - 0.5 * x + rng.normal(size=2000)
    X = np.column_stack([np.ones_like(x), x])
    b, se, tt, n = ols_nw(y, X, 0)
    check("OLS recovers a planted slope", abs(b[1] + 0.5) < 0.06 and tt[1] < -10)
    e = y - X @ b; hc0 = np.sqrt(np.diag(np.linalg.inv(X.T@X) @ (X.T*(e**2))@X @ np.linalg.inv(X.T@X)))
    check("NW with 0 lags equals White HC0", np.allclose(se, hc0))
    ar = np.zeros(4000); eps = rng.normal(size=4000)
    for i in range(1, 4000): ar[i] = 0.8 * ar[i-1] + eps[i]
    _, se0, _, _ = ols_nw(ar, np.ones((4000, 1)), 0); _, se10, _, _ = ols_nw(ar, np.ones((4000, 1)), 10)
    check("NW widens the error on autocorrelated data", se10[0] > 2 * se0[0])
    q = bh({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.2})
    check("Benjamini-Hochberg q-values", abs(q["a"] - 0.04) < 1e-12 and abs(q["b"] - 0.0533333) < 1e-6
          and abs(q["d"] - 0.2) < 1e-12)
    check("eras", era_of("2012-03-31") == "E1" and era_of("2019-07-01") == "E3" and era_of("2004-12-31") == "")
    check("p-value", abs(p_two_sided(1.96) - 0.05) < 1e-3)
    # financing
    snap = {"fetched_utc": "2026-09-26T00:00:00", "instruments": {
        "IDX": {"longRate": -0.0637, "shortRate": 0.0137, "daysCharged": {"FRIDAY": 3}},
        "BND": {"longRate": -0.016, "shortRate": -0.034, "daysCharged": {}}}}
    bench = pd.Series([0.0, 0.0387], index=pd.to_datetime(["2015-01-01", "2026-09-01"]))
    yld = pd.Series([0.02, 0.043], index=pd.to_datetime(["2015-01-01", "2026-09-01"]))
    fi = Financing("IDX", snap, bench)
    check("index financing reproduces today's live rates",
          abs(fi.rate("2026-09-20", "long") + 0.0637) < 1e-12 and abs(fi.rate("2026-09-20", "short") - 0.0137) < 1e-12)
    check("index long cheaper when the benchmark was zero", fi.rate("2016-01-01", "long") > fi.rate("2026-09-20", "long"))
    check("Friday rollover charged three days",
          abs(fi.charge(["2026-09-18"], "long") - 3 * fi.rate("2026-09-18", "long") / 365) < 1e-15)
    fb = Financing("BND", snap, bench, yld)
    check("bond financing reproduces today's live rates",
          abs(fb.rate("2026-09-20", "long") + 0.016) < 1e-12 and abs(fb.rate("2026-09-20", "short") + 0.034) < 1e-12)
    for unit in ("s", "ms", "us", "ns"):
        gi = pd.DatetimeIndex(pd.date_range("2025-01-01", periods=8, freq="15min", tz="UTC")).as_unit(unit)
        bad = pd.DatetimeIndex(list(gi[:-1]) + [gi[-1] + pd.Timedelta(minutes=1)]).as_unit(unit)
        check(f"grid check is resolution-independent ({unit})",
              grid_problems(pd.DataFrame(index=gi)) == [] and grid_problems(pd.DataFrame(index=bad)) != [])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(self_test())
