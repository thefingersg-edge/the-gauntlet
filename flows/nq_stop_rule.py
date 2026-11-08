#!/usr/bin/env python3
"""
nq_stop_rule.py -- v36 rule N with an optional stop (stdlib + momentum_v36 only, so the
Mac's plain python3 can run it). Moved verbatim from stops_nq.py 2026-10-11 so that
the descriptive study and FORWARD_NQ_STOP use one copy of the logic.
kind: None | 'trail-pts' | 'fixed-pts' | 'trail-pct' | 'fixed-pct'; D in points or %.
"""
from __future__ import annotations
import os, statistics as st, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fastbot", "scripts"))
import momentum_v36 as M                                   # noqa: E402
from reactive import hm                                    # noqa: E402

TICK, MULT, COMM = 0.25, 20.0, 2.50


def day_with_stop(bars, prev_close, sig, kind=None, D=None, out=None, date=None):
    if "09:30" not in bars or "15:55" not in bars:
        return None
    keys = sorted(bars)
    op = bars["09:30"][0]
    up_ref, dn_ref = max(op, prev_close), min(op, prev_close)
    chk = set(M.CHECKS)
    side, entry, trades = 0, None, []
    stop = best = None
    pending = None                     # ("enter", side) or ("exit",) to execute at this bar's open

    def gap(px):
        return D if kind.endswith("pts") else px * D / 100.0

    def close_trade(px_mid, how):
        nonlocal side, entry, stop, best
        mid_in = entry[0]
        g = side * (px_mid / mid_in - 1) * 1e4
        if side > 0:
            n = ((px_mid - TICK) / entry[5] - 1) * 1e4
        else:
            n = -((px_mid + TICK) / entry[4] - 1) * 1e4
        trades.append((g, n, how)); side = 0; entry = stop = best = None

    for k in keys:
        b = bars[k]
        if pending:                                        # fills at this bar's open
            if pending[0] == "exit" and side != 0:
                close_trade(b[0], "rule")
            elif pending[0] == "enter" and side == 0:
                side, entry = pending[1], b
                best = b[0]
                stop = (best - side * gap(best)) if kind else None
            pending = None
        if side != 0 and kind:                             # intrabar stop
            if side > 0 and b[2] <= stop:
                close_trade(min(b[0], stop), "stop")
            elif side < 0 and b[1] >= stop:
                close_trade(max(b[0], stop), "stop")
            elif kind.startswith("trail"):
                best = max(best, b[1]) if side > 0 else min(best, b[2])
                stop = max(stop, best - gap(best)) if side > 0 else min(stop, best + gap(best))
        if k in chk and sig.get(k) is not None and hm(k, 1) in bars:
            c = b[3]
            U, L = up_ref * (1 + sig[k]), dn_ref * (1 - sig[k])
            vw = M.session_vwap(bars, k)
            exit_now = (side == 1 and c < max(U, vw)) or (side == -1 and c > min(L, vw))
            if exit_now:
                # rule exit at the next bar's open, and a re-entry decision at the same checkpoint
                nxt = bars[hm(k, 1)]
                close_trade(nxt[0], "rule")
            if side == 0:
                if c > U:
                    pending = ("enter", 1)
                elif c < L:
                    pending = ("enter", -1)
        if k == "15:55" and side != 0:
            close_trade(b[3], "close")
    # the base rule exits AT the next bar's open (mid) and pays the quoted spread like v36:
    if out is not None:
        px = bars["09:30"][0]
        comm = COMM / (px * MULT) * 1e4
        for g, n, how in trades:
            out.append(dict(date=date, g=g, n=n - comm, how=how))
    return [(g, n) for g, n, _ in trades]


def run_variant(days, kind, D):
    trades = []
    ds = sorted(days)
    rows = []
    hist = []
    for i in range(1, len(ds)):
        d, bars, prev = ds[i], days[ds[i]], days[ds[i - 1]]
        mv = ({k: abs(bars[k][3] / bars["09:30"][0] - 1) for k in M.CHECKS if k in bars} if "09:30" in bars else {})
        if len(hist) >= M.LOOKBACK and "15:55" in prev:
            sig = {}
            for k in M.CHECKS:
                xs = [h[k] for h in hist[-M.LOOKBACK:] if k in h]
                sig[k] = st.mean(xs) if len(xs) >= 10 else None
            tr = day_with_stop(bars, prev["15:55"][3], sig, kind, D, trades, d)
            if tr:
                rows.append(dict(date=d, n=len(tr), Ng=sum(g for g, _ in tr), Nn=sum(n for _, n in tr)))
        if mv:
            hist.append(mv)
    return trades, rows
