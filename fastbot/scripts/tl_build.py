#!/usr/bin/env python3
"""v37 TIMELINE -- build the event timeline, the hindsight trade labels and
the decision-point feature matrix for SPX500 (5m, 09:30-15:55 ET).

Nothing here fits a model or reads a label into a feature. Every event is
stamped with the moment it was KNOWN (bar close, release time, publication
lag); a decision at time t sees only events stamped <= t.

    python3 tl_build.py --self-test
    python3 tl_build.py                 # writes ../data/timeline_v37/
"""
from __future__ import annotations

import argparse, bisect, csv, datetime as dt, math, os, re, statistics as st, sys
import numpy as np

from reactive import load
from premarket_levels import read_vix

VERSION = "1.1"
OUT = "../data/timeline_v37"
DEC_BARS = tuple((dt.datetime(2000, 1, 1, 9, 40) + dt.timedelta(minutes=15 * i)).strftime("%H:%M")
                 for i in range(17))                     # bars closing 09:45 .. 13:45
HORIZON = 24                                             # 2 hours of 5m bars
BARRIER_K = 1.0                                          # target = stop = 1 sigma(2h)
SIG_SESS = 20
CAP_MIN = 86400.0                                        # 60 days
FORWARD_START = dt.date(2026, 9, 18)
_FORBIDDEN = re.compile(r"order|execute|submit|position", re.I)

INTRADAY = ["sma20x50_up", "sma20x50_dn", "px_x_sma20_up", "px_x_sma20_dn",
            "rsi_x70_up", "rsi_x30_dn", "rsi_x50_up", "rsi_x50_dn",
            "macd_x_up", "macd_x_dn", "bb_above", "bb_below",
            "shock3_up", "shock3_dn", "sess_high", "sess_low",
            "orb_up", "orb_dn", "sweep_high", "sweep_low",
            "noise_up", "noise_dn", "r16_up", "r16_dn",
            "engulf_bull", "engulf_bear", "inside_bar", "nr7_bar"]
DAILY = ["d_sma50x200_up", "d_sma50x200_dn", "d_x_sma50_up", "d_x_sma50_dn",
         "d_nr7", "d_inside", "d_engulf_bull", "d_engulf_bear",
         "d_high20", "d_low20", "d_up3", "d_dn3", "d_big_up", "d_big_dn",
         "gap_up", "gap_dn"]
CALENDAR = ["CPI", "NFP", "CLAIMS", "FOMC", "FOMC_PC"]
MACRO = ["vix_jump", "vix_drop", "vix_x20_up", "vix_x20_dn", "vix_x30_up",
         "vixcurve_inv", "vixcurve_norm", "skew_x140_up", "skew_x140_dn",
         "aaii_bull_ext", "aaii_bear_ext", "pc_x1_up", "pc_x1_dn",
         "cot_lev_long_ext", "cot_lev_short_ext",
         "y2_up20", "y2_dn20", "usd_up1", "usd_dn1", "gas_up3", "gas_dn3"]
EVENTS = INTRADAY + DAILY + CALENDAR + MACRO
STATES = ["min_since_open", "dow", "ret_open_s", "dist_sma20_s", "dist_sma50_s",
          "rsi", "macd_hist_s", "bb_pctb", "gap_sd", "prev_day_sd", "ret5d_sd",
          "rv_ratio", "vix", "vix_chg5", "vx_ratio", "skew", "aaii", "cot_z",
          "y2_chg5", "usd_chg5", "to_cpi", "to_nfp", "to_fomc", "to_claims",
          "noise_pos", "r16_pos", "sigma2h_bp"]


def _guard():
    bad = [n for n in globals() if _FORBIDDEN.search(n)]
    if bad:
        raise SystemExit(f"namespace guard: {bad}")


# ------------------------------------------------------------ side data
def _dt(d, hm):
    return dt.datetime.combine(d, dt.time(int(hm[:2]), int(hm[3:])))


def macro_events(here):
    """[(stamp, type)] plus daily state series {name: [(avail_datetime, value)]}."""
    ev, ser = [], {}
    D = os.path.join(here, "../data")
    vix = read_vix(os.path.join(D, "VIXCLS.csv"))
    ser["vix"] = [(_dt(d, "16:15"), v) for d, v in vix]
    for (d0, v0), (d1, v1) in zip(vix, vix[1:]):
        s = _dt(d1, "16:15")
        if v1 > v0 * 1.10: ev.append((s, "vix_jump"))
        if v1 < v0 * 0.90: ev.append((s, "vix_drop"))
        if v0 < 20 <= v1: ev.append((s, "vix_x20_up"))
        if v0 >= 20 > v1: ev.append((s, "vix_x20_dn"))
        if v0 < 30 <= v1: ev.append((s, "vix_x30_up"))

    def tv(fn):
        out = {}
        # 1.1: TradingView stamps a CBOE futures daily bar at the session OPEN,
        # 17:00 Chicago on the PREVIOUS calendar day (vix_curve_budget.py knew
        # this; 1.0 did not, and dated every VX close one day EARLY -- a full
        # day of look-ahead that made "VIX curve inversion" the top predictor).
        from zoneinfo import ZoneInfo
        for r in list(csv.reader(open(os.path.join(D, fn))))[1:]:
            ch = dt.datetime.fromtimestamp(int(r[0]), ZoneInfo("America/Chicago"))
            day = ch.date() + (dt.timedelta(days=1) if ch.hour >= 16 else dt.timedelta(0))
            out[day] = float(r[4])
        return out
    v1, v2 = tv("CBOE_DLY_VX1!, 1D_1f2b8.csv"), tv("CBOE_DLY_VX2!, 1D_7782c.csv")
    ds = sorted(set(v1) & set(v2))
    ser["vx_ratio"] = [(_dt(d, "16:15"), v1[d] / v2[d]) for d in ds if v2[d] > 0]
    for a, b in zip(ds, ds[1:]):
        if v1[a] <= v2[a] and v1[b] > v2[b]: ev.append((_dt(b, "16:15"), "vixcurve_inv"))
        if v1[a] > v2[a] and v1[b] <= v2[b]: ev.append((_dt(b, "16:15"), "vixcurve_norm"))
    sk = sorted((dt.datetime.strptime(r["DATE"], "%m/%d/%Y").date(), float(r["SKEW"]))
                for r in csv.DictReader(open(os.path.join(D, "sentiment/cboe_skew.csv"))))
    ser["skew"] = [(_dt(d, "16:15"), v) for d, v in sk]
    for (a, x), (b, y) in zip(sk, sk[1:]):
        if x < 140 <= y: ev.append((_dt(b, "16:15"), "skew_x140_up"))
        if x >= 140 > y: ev.append((_dt(b, "16:15"), "skew_x140_dn"))
    import xlrd
    wb = xlrd.open_workbook(os.path.join(D, "sentiment/aaii_sentiment.csv"))
    sh = wb.sheet_by_index(0)
    aa = []
    for i in range(sh.nrows):
        v = sh.row_values(i)
        if isinstance(v[0], float) and v[0] > 30000 and v[1] != "" and v[3] != "":
            aa.append((xlrd.xldate_as_datetime(v[0], wb.datemode).date(), (float(v[1]) - float(v[3])) * (100 if float(v[1]) <= 1 else 1)))
    aa.sort()
    ser["aaii"] = [(_dt(d + dt.timedelta(days=1), "00:00"), v) for d, v in aa]
    for d, v in aa:
        if v > 20: ev.append((_dt(d + dt.timedelta(days=1), "00:00"), "aaii_bull_ext"))
        if v < -20: ev.append((_dt(d + dt.timedelta(days=1), "00:00"), "aaii_bear_ext"))
    pc = []
    for line in list(open(os.path.join(D, "sentiment/cboe_totalpc.csv")))[3:]:
        p = [x.strip() for x in line.split(",")]
        try:
            pc.append((dt.datetime.strptime(p[0], "%m/%d/%Y").date(), float(p[4])))
        except (ValueError, IndexError):
            pass
    pc.sort()
    for (a, x), (b, y) in zip(pc, pc[1:]):
        if x < 1.0 <= y: ev.append((_dt(b, "18:00"), "pc_x1_up"))
        if x >= 1.0 > y: ev.append((_dt(b, "18:00"), "pc_x1_dn"))
    cot = sorted((dt.date.fromisoformat(r["report_date"]), float(r["lev_l"]), float(r["lev_s"]), float(r["oi"]))
                 for r in csv.DictReader(open(os.path.join(D, "sentiment/cftc_positions.csv")))
                 if r["instrument"] == "SPX500_USD" and r["lev_l"] and r["lev_s"] and r["oi"])
    net = [(d, (l - s) / oi) for d, l, s, oi in cot]
    zs = []
    for i in range(52, len(net)):
        base = [x for _, x in net[i - 52:i]]
        sd = st.stdev(base)
        if sd > 0:
            z = (net[i][1] - st.mean(base)) / sd
            stamp = _dt(net[i][0] + dt.timedelta(days=3), "15:30")
            zs.append((stamp, z))
            if z > 1.5: ev.append((stamp, "cot_lev_long_ext"))
            if z < -1.5: ev.append((stamp, "cot_lev_short_ext"))
    ser["cot_z"] = zs

    def fred(fn):
        out = []
        for r in csv.DictReader(open(os.path.join(D, fn))):
            try:
                out.append((dt.date.fromisoformat(r["date"]), float(r["value"])))
            except (ValueError, TypeError):
                pass
        return sorted(out)
    y2, usd, gas = fred("v31/DGS2.csv"), fred("v31/DTWEXBGS.csv"), fred("v31/GASREGW.csv")
    ser["y2_chg5"] = [(_dt(y2[i][0], "18:00"), y2[i][1] - y2[i - 5][1]) for i in range(5, len(y2))]
    ser["usd_chg5"] = [(_dt(usd[i][0], "18:00"), math.log(usd[i][1] / usd[i - 5][1])) for i in range(5, len(usd))]
    for s, v in ser["y2_chg5"]:
        if v > 0.20: ev.append((s, "y2_up20"))
        if v < -0.20: ev.append((s, "y2_dn20"))
    for s, v in ser["usd_chg5"]:
        if v > 0.01: ev.append((s, "usd_up1"))
        if v < -0.01: ev.append((s, "usd_dn1"))
    for (a, x), (b, y) in zip(gas, gas[1:]):
        s = _dt(b + dt.timedelta(days=1), "00:00")
        if y > x * 1.03: ev.append((s, "gas_up3"))
        if y < x * 0.97: ev.append((s, "gas_dn3"))
    return ev, ser, vix


def calendar(here):
    ev, sched = [], {k: [] for k in ("CPI", "NFP", "FOMC", "CLAIMS")}
    for r in csv.DictReader(open(os.path.join(here, "../data/events_v2.csv"))):
        if r["event"] not in sched:
            continue
        s = _dt(dt.date.fromisoformat(r["date"]), r["time_et"] or ("14:00" if r["event"] == "FOMC" else "08:30"))
        sched[r["event"]].append(s)
        ev.append((s, r["event"]))
        if r["event"] == "FOMC" and r.get("press_conference") == "yes":
            ev.append((s + dt.timedelta(minutes=30), "FOMC_PC"))
    return ev, {k: sorted(v) for k, v in sched.items()}


# --------------------------------------------------------- indicators
class Ind:
    """Running 5m indicators over consecutive RTH closes."""
    def __init__(self):
        self.c = []
        self.ema12 = self.ema26 = self.sig = None
        self.avg_g = self.avg_l = None

    def push(self, x):
        prev = self.c[-1] if self.c else None
        self.c.append(x)
        if len(self.c) > 60:
            self.c.pop(0)
        a12, a26, a9 = 2 / 13, 2 / 27, 2 / 10
        self.ema12 = x if self.ema12 is None else self.ema12 + a12 * (x - self.ema12)
        self.ema26 = x if self.ema26 is None else self.ema26 + a26 * (x - self.ema26)
        m = self.ema12 - self.ema26
        self.sig = m if self.sig is None else self.sig + a9 * (m - self.sig)
        if prev is not None:
            g, l = max(x - prev, 0.0), max(prev - x, 0.0)
            if self.avg_g is None:
                self.avg_g, self.avg_l = g, l
            else:
                self.avg_g += (g - self.avg_g) / 14
                self.avg_l += (l - self.avg_l) / 14

    def sma(self, n):
        return st.fmean(self.c[-n:]) if len(self.c) >= n else None

    def rsi(self):
        if self.avg_g is None or len(self.c) < 15:
            return None
        return 100.0 if self.avg_l == 0 else 100 - 100 / (1 + self.avg_g / self.avg_l)

    def macd(self):
        return None if self.sig is None or len(self.c) < 35 else (self.ema12 - self.ema26) - self.sig

    def bb(self):
        if len(self.c) < 20:
            return None
        w = self.c[-20:]
        mu, sd = st.fmean(w), st.pstdev(w)
        return None if sd == 0 else (mu - 2 * sd, mu + 2 * sd)


def asof(series, t):
    """Latest value whose availability stamp is <= t (within 14 days)."""
    ks = series["_k"]
    i = bisect.bisect_right(ks, t) - 1
    if i < 0 or (t - ks[i]).days > 14:
        return None
    return series["_v"][i]


def prep(series):
    s = sorted(series)
    return {"_k": [a for a, _ in s], "_v": [b for _, b in s]}


# ----------------------------------------------------------- labels
def barrier(bars_after, entry, b, side):
    """(+1 win, -1 loss, 0 timeout, gross_bp) on mid, first touch; a bar that
    touches both sides counts as a loss."""
    up, dn = entry * (1 + b), entry * (1 - b)
    for bar in bars_after:
        hi, lo = bar[1], bar[2]
        if side > 0:
            if lo <= dn: return -1, -b * 1e4
            if hi >= up: return 1, b * 1e4
        else:
            if hi >= up: return -1, -b * 1e4
            if lo <= dn: return 1, b * 1e4
    last = bars_after[-1][3]
    return 0, side * (last / entry - 1) * 1e4


# ------------------------------------------------------------- build
def build(data_dir, here, limit_days=None, verbose=True):
    days = load(data_dir, "spx500usd")
    ds = sorted(d for d in days if d < FORWARD_START)
    if limit_days:
        ds = ds[:limit_days]
    mev, ser, vix = macro_events(here)
    cev, sched = calendar(here)
    ser = {k: prep(v) for k, v in ser.items()}
    vixd = dict(vix)
    ext = sorted(mev + cev)
    ei = 0
    last = {e: None for e in EVENTS}
    recent = []                      # (stamp, type) intraday, for 60-min counts
    ind = Ind()
    rows, feats, evlog = [], [], []
    slot_hist, day_ret_hist, noise_hist = {}, [], []
    daily = []                       # (d, O, H, L, C)
    r5_hist = []                     # per session list of 5m returns

    def fire(t, e):
        last[e] = t
        evlog.append((t, e))
        if e in INTRADAY:
            recent.append((t, e))

    for di, d in enumerate(ds):
        bars = days[d]
        hms = sorted(bars)
        if "09:30" not in bars or "15:55" not in bars:
            continue
        # ---- day-start context
        sig5 = (math.sqrt(st.fmean([x * x for s in r5_hist[-SIG_SESS:] for x in s]))
                if len(r5_hist) >= SIG_SESS else None)
        sd_day = st.pstdev(day_ret_hist[-20:]) if len(day_ret_hist) >= 20 else None
        O = bars["09:30"][0]
        prevC = daily[-1][4] if daily else None
        # gap event at the open
        if prevC and sd_day:
            g = (O / prevC - 1) / sd_day
            if g > 0.5: fire(_dt(d, "09:30"), "gap_up")
            if g < -0.5: fire(_dt(d, "09:30"), "gap_dn")
        pv = [v for k, v in vixd.items()] if False else None
        vprev = None
        k = bisect.bisect_left(vix, (d,)) - 1
        if k >= 0 and (d - vix[k][0]).days <= 7:
            vprev = vix[k][1]
        R16 = (prevC * (1 + vprev * 6.25e-4), prevC * (1 - vprev * 6.25e-4)) if prevC and vprev else None
        r16_done = False
        # noise band sigma per checkpoint (v36 definition)
        nsig = {}
        if len(noise_hist) >= 14:
            for kk in {h for h in hms}:
                xs = [h[kk] for h in noise_hist[-14:] if kk in h]
                nsig[kk] = st.fmean(xs) if len(xs) >= 10 else None
        today_noise = {}
        sh = sl = None
        or_hi = or_lo = None
        orb_u = orb_d = False
        rets = []
        prev_bar = None
        ranges = []
        for hm in hms:
            t = _dt(d, hm) + dt.timedelta(minutes=5)        # bar CLOSE time
            while ei < len(ext) and ext[ei][0] <= t:
                fire(ext[ei][0], ext[ei][1]); ei += 1
            o, h, l, c = bars[hm][:4]
            s20o, s50o, rsio, macdo = ind.sma(20), ind.sma(50), ind.rsi(), ind.macd()
            prev_c = ind.c[-1] if ind.c else None
            ind.push(c)
            s20, s50, rsi, macd, bb = ind.sma(20), ind.sma(50), ind.rsi(), ind.macd(), ind.bb()
            if s20o and s50o and s20 and s50:
                if s20o <= s50o and s20 > s50: fire(t, "sma20x50_up")
                if s20o >= s50o and s20 < s50: fire(t, "sma20x50_dn")
            if s20o and prev_c and s20:
                if prev_c <= s20o and c > s20: fire(t, "px_x_sma20_up")
                if prev_c >= s20o and c < s20: fire(t, "px_x_sma20_dn")
            if rsio is not None and rsi is not None:
                if rsio < 70 <= rsi: fire(t, "rsi_x70_up")
                if rsio > 30 >= rsi: fire(t, "rsi_x30_dn")
                if rsio < 50 <= rsi: fire(t, "rsi_x50_up")
                if rsio > 50 >= rsi: fire(t, "rsi_x50_dn")
            if macdo is not None and macd is not None:
                if macdo <= 0 < macd: fire(t, "macd_x_up")
                if macdo >= 0 > macd: fire(t, "macd_x_dn")
            if bb:
                if c > bb[1]: fire(t, "bb_above")
                if c < bb[0]: fire(t, "bb_below")
            r = (c / o - 1)
            hs = slot_hist.get(hm, [])
            if len(hs) >= 20:
                s = math.sqrt(st.fmean([x * x for x in hs[-20:]]))
                if s > 0 and r / s >= 3: fire(t, "shock3_up")
                if s > 0 and r / s <= -3: fire(t, "shock3_dn")
            slot_hist.setdefault(hm, []).append(r)
            if sh is not None:
                if h > sh:
                    fire(t, "sess_high")
                    if c < sh: fire(t, "sweep_high")
                if l < sl:
                    fire(t, "sess_low")
                    if c > sl: fire(t, "sweep_low")
            sh = h if sh is None else max(sh, h)
            sl = l if sl is None else min(sl, l)
            if hm <= "09:55":
                or_hi = h if or_hi is None else max(or_hi, h)
                or_lo = l if or_lo is None else min(or_lo, l)
            else:
                if not orb_u and c > or_hi: fire(t, "orb_up"); orb_u = True
                if not orb_d and c < or_lo: fire(t, "orb_dn"); orb_d = True
            if R16 and not r16_done and hm <= "14:50":
                if c > R16[0]: fire(t, "r16_up"); r16_done = True
                elif c < R16[1]: fire(t, "r16_dn"); r16_done = True
            if prev_bar:
                po, ph, pl, pc_ = prev_bar
                if pc_ < po and c > o and c >= po and o <= pc_: fire(t, "engulf_bull")
                if pc_ > po and c < o and c <= po and o >= pc_: fire(t, "engulf_bear")
                if h < ph and l > pl: fire(t, "inside_bar")
            ranges.append(h - l)
            if len(ranges) >= 7 and ranges[-1] == min(ranges[-7:]) and ranges[-1] > 0:
                fire(t, "nr7_bar")
            # noise band at the v36 checkpoints (bars closing on :00 / :30, 10:00-15:30)
            if hm >= "09:55" and hm <= "15:25" and hm[3:] in ("25", "55"):
                today_noise[hm] = abs(c / O - 1)
                sg = nsig.get(hm)
                if sg and prevC:
                    U, L = max(O, prevC) * (1 + sg), min(O, prevC) * (1 - sg)
                    if c > U: fire(t, "noise_up")
                    if c < L: fire(t, "noise_dn")
            if prev_c is not None and hm != "09:30":
                rets.append(c / prev_c - 1)
            prev_bar = (o, h, l, c)

            # ---------------- decision point ----------------
            if hm in DEC_BARS and sig5:
                i0 = hms.index(hm)
                after = [bars[x] for x in hms[i0 + 1: i0 + 1 + HORIZON]]
                if len(after) < HORIZON:
                    continue
                sig2h = sig5 * math.sqrt(HORIZON)
                b = BARRIER_K * sig2h
                entry = after[0][0]
                spread = (after[0][5] / after[0][4] - 1) * 1e4
                yl, gl = barrier(after, entry, b, 1)
                ys, gs = barrier(after, entry, b, -1)
                f = {}
                for e in EVENTS:
                    f["ms_" + e] = math.log1p(min(CAP_MIN, (t - last[e]).total_seconds() / 60)) if last[e] else math.log1p(CAP_MIN)
                cut = t - dt.timedelta(minutes=60)
                while recent and recent[0][0] < t - dt.timedelta(days=1):
                    recent.pop(0)
                for e in INTRADAY:
                    f["n60_" + e] = sum(1 for s, x in recent if x == e and s > cut)
                mso = (t - _dt(d, "09:30")).total_seconds() / 60
                rv = math.sqrt(st.fmean([x * x for x in rets])) if rets else None
                f.update(min_since_open=mso, dow=d.weekday(),
                         ret_open_s=(c / O - 1) / sig2h,
                         dist_sma20_s=None if not s20 else (c / s20 - 1) / sig5,
                         dist_sma50_s=None if not s50 else (c / s50 - 1) / sig5,
                         rsi=rsi, macd_hist_s=None if macd is None else macd / c / sig5,
                         bb_pctb=None if not bb else (c - bb[0]) / (bb[1] - bb[0]),
                         gap_sd=None if not (prevC and sd_day) else (O / prevC - 1) / sd_day,
                         prev_day_sd=None if not (len(daily) >= 2 and sd_day) else (daily[-1][4] / daily[-2][4] - 1) / sd_day,
                         ret5d_sd=None if not (len(daily) >= 6 and sd_day) else (daily[-1][4] / daily[-6][4] - 1) / sd_day,
                         rv_ratio=None if not rv else rv / sig5,
                         vix=asof(ser["vix"], t), vx_ratio=asof(ser["vx_ratio"], t),
                         skew=asof(ser["skew"], t), aaii=asof(ser["aaii"], t),
                         cot_z=asof(ser["cot_z"], t), y2_chg5=asof(ser["y2_chg5"], t),
                         usd_chg5=asof(ser["usd_chg5"], t), sigma2h_bp=sig2h * 1e4)
                v5 = asof(ser["vix"], t - dt.timedelta(days=7))
                f["vix_chg5"] = None if (f["vix"] is None or v5 is None) else f["vix"] - v5
                for key, ev_ in (("to_cpi", "CPI"), ("to_nfp", "NFP"), ("to_fomc", "FOMC"), ("to_claims", "CLAIMS")):
                    L_ = sched[ev_]
                    j = bisect.bisect_right(L_, t)
                    f[key] = math.log1p((L_[j] - t).total_seconds() / 60) if j < len(L_) else None
                sg = nsig.get(hm) if hm in nsig else None
                f["noise_pos"] = None
                if prevC:
                    # distance beyond the nearest v36 band, in sigma(2h) units (last checkpoint's sigma)
                    sgs = [nsig.get(x) for x in sorted(nsig) if x <= hm and nsig.get(x)]
                    if sgs:
                        U, L = max(O, prevC) * (1 + sgs[-1]), min(O, prevC) * (1 - sgs[-1])
                        f["noise_pos"] = ((c - U) if c > U else (c - L) if c < L else 0.0) / c / sig2h
                f["r16_pos"] = None if not R16 else (c / prevC - 1) / (vprev * 6.25e-4)
                rows.append(dict(date=d, hm=hm, entry=entry, b_bp=b * 1e4, spread=spread,
                                 yl=yl, ys=ys, gl=gl, gs=gs))
                feats.append(f)
        # ---- day end
        H = max(bars[x][1] for x in hms); Lw = min(bars[x][2] for x in hms); C = bars["15:55"][3]
        tclose = _dt(d, "16:00")
        if daily:
            pO, pH, pL, pC = daily[-1][1:]
            closes = [x[4] for x in daily] + [C]
            if len(closes) >= 201:
                a50o, a200o = st.fmean(closes[-51:-1]), st.fmean(closes[-201:-1])
                a50, a200 = st.fmean(closes[-50:]), st.fmean(closes[-200:])
                if a50o <= a200o and a50 > a200: fire(tclose, "d_sma50x200_up")
                if a50o >= a200o and a50 < a200: fire(tclose, "d_sma50x200_dn")
            if len(closes) >= 51:
                a50o, a50 = st.fmean(closes[-51:-1]), st.fmean(closes[-50:])
                if pC <= a50o and C > a50: fire(tclose, "d_x_sma50_up")
                if pC >= a50o and C < a50: fire(tclose, "d_x_sma50_dn")
            rng = [x[2] - x[3] for x in daily[-6:]] + [H - Lw]
            if len(rng) == 7 and rng[-1] == min(rng): fire(tclose, "d_nr7")
            if H < pH and Lw > pL: fire(tclose, "d_inside")
            if pC < pO and C > O and C >= pO and O <= pC: fire(tclose, "d_engulf_bull")
            if pC > pO and C < O and C <= pO and O >= pC: fire(tclose, "d_engulf_bear")
            if len(closes) >= 21:
                if C > max(closes[-21:-1]): fire(tclose, "d_high20")
                if C < min(closes[-21:-1]): fire(tclose, "d_low20")
            if len(closes) >= 4:
                ch = [closes[-i] - closes[-i - 1] for i in (1, 2, 3)]
                if all(x > 0 for x in ch) and not (len(closes) >= 5 and closes[-4] > closes[-5]): fire(tclose, "d_up3")
                if all(x < 0 for x in ch) and not (len(closes) >= 5 and closes[-4] < closes[-5]): fire(tclose, "d_dn3")
            dr = C / pC - 1
            if sd_day and dr > 2 * sd_day: fire(tclose, "d_big_up")
            if sd_day and dr < -2 * sd_day: fire(tclose, "d_big_dn")
            day_ret_hist.append(dr)
        daily.append((d, O, H, Lw, C))
        r5_hist.append(rets)
        noise_hist.append(today_noise)
        if verbose and di % 500 == 0:
            print(f"  {d}  decision points so far {len(rows):,}", flush=True)
    return rows, feats, evlog


def self_test():
    ok = True
    def check(n, c):
        nonlocal ok; ok &= bool(c); print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"tl_build.py v{VERSION} self-test\n")
    bar = lambda o, h, l, c: (o, h, l, c, o, o, c, c)
    check("long hits target first -> +1", barrier([bar(100, 101.2, 99.5, 101)], 100, 0.01, 1)[0] == 1)
    check("PLANTED: a bar touching both sides is a LOSS, never a win",
          barrier([bar(100, 101.5, 98.5, 100)], 100, 0.01, 1)[0] == -1
          and barrier([bar(100, 101.5, 98.5, 100)], 100, 0.01, -1)[0] == -1)
    check("timeout pays the drift", barrier([bar(100, 100.2, 99.9, 100.1)], 100, 0.01, 1) == (0, (100.1 / 100 - 1) * 1e4))
    s = prep([(dt.datetime(2020, 1, 1, 16, 15), 20.0), (dt.datetime(2020, 1, 2, 16, 15), 99.0)])
    check("as-of never sees a value before its stamp",
          asof(s, dt.datetime(2020, 1, 2, 10, 0)) == 20.0 and asof(s, dt.datetime(2020, 1, 2, 16, 15)) == 99.0)
    check("decision bars close 09:45 .. 13:45 so a 2h trade ends by 15:45",
          DEC_BARS[0] == "09:40" and DEC_BARS[-1] == "13:40" and len(DEC_BARS) == 17)
    # small real build: no feature may equal a label
    rows, feats, evlog = build("../data", os.path.dirname(os.path.abspath(__file__)), limit_days=60, verbose=False)
    check("a 60-session build produces decision points", len(rows) > 300)
    check("every event in the log is stamped at or before the decision that saw it",
          all(e[0] <= _dt(rows[-1]["date"], "16:00") + dt.timedelta(days=4) for e in evlog))
    names = sorted(feats[0])
    check("feature names contain no label", not any(n in ("yl", "ys", "gl", "gs") for n in names))
    here = os.path.dirname(os.path.abspath(__file__))
    ev, ser, vix = macro_events(here)
    pr = prep(ser["vx_ratio"]); vr = {k.date(): v for k, v in zip(pr["_k"], pr["_v"])}
    vx = dict(vix)
    def corr(lag):
        a, b = [], []
        ds = sorted(set(vr) & set(vx))
        for i in range(1, len(ds)):
            x0, x1 = ds[i - 1] + dt.timedelta(days=lag), ds[i] + dt.timedelta(days=lag)
            if x0 in vr and x1 in vr:
                a.append(vr[x1] - vr[x0]); b.append(vx[ds[i]] - vx[ds[i - 1]])
        return float(np.corrcoef(a, b)[0, 1])
    c0, cm = corr(0), corr(-1)
    check(f"VX curve moves WITH the same-day VIX (corr {c0:+.2f}) and not with the day before's (lag +1 day: {cm:+.2f})",
          c0 > 0.5 and cm < 0.3)
    check("namespace guard", not [n for n in globals() if _FORBIDDEN.search(n)])
    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())
    here = os.path.dirname(os.path.abspath(__file__))
    rows, feats, evlog = build("../data", here)
    names = [f"ms_{e}" for e in EVENTS] + [f"n60_{e}" for e in INTRADAY] + STATES
    X = np.array([[np.nan if f.get(n) is None else f[n] for n in names] for f in feats], dtype=np.float32)
    out = os.path.join(here, OUT)
    np.savez_compressed(os.path.join(out, "matrix.npz"), X=X, names=np.array(names),
                        date=np.array([r["date"].isoformat() for r in rows]),
                        hm=np.array([r["hm"] for r in rows]),
                        yl=np.array([r["yl"] for r in rows], dtype=np.int8),
                        ys=np.array([r["ys"] for r in rows], dtype=np.int8),
                        gl=np.array([r["gl"] for r in rows], dtype=np.float32),
                        gs=np.array([r["gs"] for r in rows], dtype=np.float32),
                        b_bp=np.array([r["b_bp"] for r in rows], dtype=np.float32),
                        spread=np.array([r["spread"] for r in rows], dtype=np.float32))
    with open(os.path.join(out, "trade_points.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "decision_bar_close_et", "entry_mid", "target_stop_bp", "wanted", "long_result", "short_result"])
        for r in rows:
            t = (dt.datetime.strptime(r["hm"], "%H:%M") + dt.timedelta(minutes=5)).strftime("%H:%M")
            want = "LONG" if r["yl"] == 1 else ("SHORT" if r["ys"] == 1 else "")
            w.writerow([r["date"], t, f"{r['entry']:.2f}", f"{r['b_bp']:.1f}", want, r["yl"], r["ys"]])
    with open(os.path.join(out, "event_timeline.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["known_at_et", "event"])
        for t, e in evlog:
            w.writerow([t.strftime("%Y-%m-%d %H:%M"), e])
    print(f"\n  {len(rows):,} decision points, {len(names)} features, {len(evlog):,} events -> {out}")


_guard()

if __name__ == "__main__":
    main()
