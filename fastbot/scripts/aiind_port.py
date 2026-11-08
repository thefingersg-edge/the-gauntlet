#!/usr/bin/env python3
"""aiind_port.py -- exact Python ports of the two TradingView scripts in PREREGISTRATION_AIIND.md (author defaults).
    knn_signals(o,h,l,c,v, apply=True)  -> target position per bar (+1/-1/0), decided at the bar close (lastguru VWMA + kNN MFI/ADX)
    aima_signals(o,h,l,c, control=None) -> stDir per bar (+1/-1) and diagnostics (Zeiierman AI Source Switching MA, AI Supertrend)
    python3 aiind_port.py --self-test
Pine semantics kept: ta.ema / ta.rma / ta.atr seeded with an SMA; ta.stdev is the population sd; lastguru's own _rma starts from 0 (nz);
built-in v4 `tr` is na on the first bar; x/0 is na; comparisons with na are false.
I am not a financial adviser. This is a measurement, not a recommendation."""
import math, sys
import numpy as np
from numba import njit

NAN = np.nan


# ------------------------------------------------------------------ Pine building blocks
@njit(cache=True)
def ema_seeded(x, n, alpha):
    out = np.full(x.size, np.nan); s = -1
    for i in range(x.size):
        if not np.isnan(x[i]): s = i; break
    if s < 0 or s + n > x.size: return out
    acc = 0.0
    for i in range(s, s + n): acc += x[i]
    out[s + n - 1] = acc / n
    for i in range(s + n, x.size):
        out[i] = alpha * x[i] + (1 - alpha) * out[i - 1] if not np.isnan(x[i]) else np.nan
    return out


def ema(x, n): return ema_seeded(np.asarray(x, float), n, 2.0 / (n + 1))
def rma(x, n): return ema_seeded(np.asarray(x, float), n, 1.0 / n)


def sma(x, n):
    x = np.asarray(x, float); out = np.full(x.size, NAN)
    if x.size >= n:
        c = np.cumsum(np.r_[0.0, x]); out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def rsum(x, n):
    x = np.asarray(x, float); out = np.full(x.size, NAN)
    if x.size >= n:
        c = np.cumsum(np.r_[0.0, x]); out[n - 1:] = c[n:] - c[:-n]
    return out


@njit(cache=True)
def stdev_pop(x, n):
    out = np.full(x.size, np.nan)
    for i in range(n - 1, x.size):
        m = 0.0
        for j in range(i - n + 1, i + 1): m += x[j]
        m /= n; v = 0.0
        for j in range(i - n + 1, i + 1): v += (x[j] - m) ** 2
        out[i] = math.sqrt(v / n)
    return out


@njit(cache=True)
def roll_minmax(x, n):
    lo = np.full(x.size, np.nan); hi = np.full(x.size, np.nan)
    for i in range(n - 1, x.size):
        a = np.inf; b = -np.inf; bad = False
        for j in range(i - n + 1, i + 1):
            if np.isnan(x[j]): bad = True; break
            a = min(a, x[j]); b = max(b, x[j])
        if not bad: lo[i] = a; hi[i] = b
    return lo, hi


def shift(x, k):
    out = np.full(x.size, NAN)
    if k < x.size: out[k:] = x[:-k] if k > 0 else x
    return out


def atr(h, l, c, n):
    pc = shift(c, 1); tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    return rma(tr, n)


def crossover(a, b):
    a1, b1 = shift(a, 1), shift(b, 1)
    with np.errstate(invalid="ignore"): return (a > b) & (a1 <= b1)


# ------------------------------------------------------------------ lastguru: VWMA + kNN (MFI / ADX)
@njit(cache=True)
def _lg_rma(src, n):
    out = np.full(src.size, np.nan); prev = np.nan
    for i in range(src.size):
        p = 0.0 if np.isnan(prev) else prev
        out[i] = ((n - 1) * p + src[i]) / n          # na src -> na
        prev = out[i]
    return out


@njit(cache=True)
def _fixnan(x):
    out = x.copy(); last = np.nan
    for i in range(x.size):
        if np.isnan(x[i]): out[i] = last
        else: last = x[i]
    return out


@njit(cache=True)
def _knn_loop(adx, mfi, src, longc, shortc, K, DIST, apply):
    n = adx.size
    cap = int(longc.sum() + shortc.sum()) + 2
    k1 = np.zeros(cap); k2 = np.zeros(cap); kr = np.zeros(cap); m_ = 1          # arrays start with one row (0, 0, result 0)
    prevp1 = 0.0; prevp2 = 0.0; prevsrc = 0.0
    filt = np.zeros(n); target = np.zeros(n); pos = 0.0
    for t in range(n):
        if longc[t] or shortc[t]:
            k1[m_] = prevp1; k2[m_] = prevp2; kr[m_] = 1.0 if src[t] >= prevsrc else -1.0; m_ += 1
            prevp1 = adx[t]; prevp2 = mfi[t]; prevsrc = src[t]
        # _knn: distances to every stored row, k smallest (nan last), threshold = max of those, all rows <= threshold vote
        tot = 0.0
        if longc[t] or shortc[t]:                      # the vote is only used on crossover bars, so only computed there
            d = np.empty(m_); fd = np.empty(m_); f = 0
            for i in range(m_):
                d[i] = math.sqrt((adx[t] - k1[i]) ** 2 + (mfi[t] - k2[i]) ** 2)
                if not np.isnan(d[i]): fd[f] = d[i]; f += 1
            # Pine: sort (na last), take the first min(k, size), threshold = max of those (na ignored)
            kk = min(K, m_)
            if f > 0:
                q = min(kk, f)
                thr = np.partition(fd[:f], q - 1)[q - 1]
                for i in range(m_):
                    if not np.isnan(d[i]) and d[i] <= thr: tot += kr[i]
        filt[t] = tot
        if longc[t] and ((not apply) or tot >= DIST): pos = 1.0
        if shortc[t] and ((not apply) or tot <= -DIST): pos = -1.0
        target[t] = pos
    return target, filt


def knn_signals(o, h, l, c, v, apply=True, SRC="open", FAST=13, SLOW=19, FILTER=13, SMOOTH=6, KNN=45, DIST=2):
    o, h, l, c, v = (np.asarray(a, float) for a in (o, h, l, c, v))
    src = o if SRC == "open" else c
    with np.errstate(invalid="ignore", divide="ignore"):
        fast = rsum(src * v, FAST) / rsum(v, FAST); slow = rsum(src * v, SLOW) / rsum(v, SLOW)
        fast[~np.isfinite(fast)] = NAN; slow[~np.isfinite(slow)] = NAN
        up = h - shift(h, 1); down = -(l - shift(l, 1))
        plusDM = np.where(np.isnan(up), NAN, np.where((up > down) & (up > 0), up, 0.0))
        minusDM = np.where(np.isnan(down), NAN, np.where((down > up) & (down > 0), down, 0.0))
        pc = shift(c, 1); tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))   # v4 `tr`: na on bar 0
        trur = _lg_rma(tr, FILTER)
        plus = _fixnan(100 * _lg_rma(plusDM, FILTER) / trur); minus = _fixnan(100 * _lg_rma(minusDM, FILTER) / trur)
        ssum = plus + minus
        adx = 100 * _lg_rma(np.abs(plus - minus) / np.where(ssum == 0, 1.0, ssum), SMOOTH)
        o4 = (o + h + l + c) / 4; ch = o4 - shift(o4, 1)
        upv = v * np.where(ch <= 0, 0.0, o4); dnv = v * np.where(ch >= 0, 0.0, o4)           # na change -> comparison false -> o4
        mu, md = rsum(upv, FILTER), rsum(dnv, FILTER)
        mfi = np.where(md == 0, NAN, 100.0 - 100.0 / (1.0 + mu / np.where(md == 0, 1.0, md)))
    longc = crossover(fast, slow); shortc = crossover(slow, fast)
    target, filt = _knn_loop(adx, mfi, src, longc, shortc, KNN, DIST, apply)
    return target, dict(adx=adx, mfi=mfi, filt=filt, longc=longc, shortc=shortc, fast=fast, slow=slow)


# ------------------------------------------------------------------ Zeiierman: AI Source Switching MA (AI Supertrend)
def _features(src, h, l, atrv):
    with np.errstate(invalid="ignore", divide="ignore"):
        T = np.where(atrv == 0, 0.0, np.clip((ema(src, 10) - ema(src, 34)) / atrv, -3, 3) / 3)
        basis = sma(src, 30); dev = stdev_pop(src, 30)
        M = np.where(dev == 0, 0.0, np.clip(-((src - basis) / dev), -3, 3) / 3)
        Mo = np.clip((src / shift(src, 14) - 1.0) / 0.05, -3, 3) / 3
        sd = stdev_pop(src, 20); lo, hi = roll_minmax(sd, 100)
        V = np.where(hi == lo, 0.5, np.clip((sd - lo) / (hi - lo), 0.0, 1.0)) * 2.0 - 1.0
        V[np.isnan(lo)] = NAN
        rng = h - l
        R = np.where(rng == 0, 0.0, np.clip(((src - l) / np.where(rng == 0, 1, rng)) * 2.0 - 1.0, -1, 1))
        S = np.where(atrv == 0, 0.0, np.clip((src - shift(src, 3)) / atrv, -3, 3) / 3)
    for a in (T, M, Mo, S): a[np.isnan(atrv) | np.isnan(a)] = NAN
    return np.vstack([T, M, Mo, V, R, S]).T          # (n, 6)


@njit(cache=True)
def _clamp(x, lo, hi): return max(lo, min(x, hi))


@njit(cache=True)
def _valid(f): return not (np.isnan(f[0]) or np.isnan(f[1]) or np.isnan(f[2]) or np.isnan(f[3]) or np.isnan(f[4]) or np.isnan(f[5]))


@njit(cache=True)
def _add(bank, cnt, row, limit):
    # newest row at index 0; drop the oldest beyond limit
    m = min(cnt + 1, limit)
    for i in range(m - 1, 0, -1): bank[i, :] = bank[i - 1, :]
    bank[0, :] = row
    return m


@njit(cache=True)
def _knn_score(f, bank, n, w, memoryDepth, spacing, K):
    gaps = np.empty(K); cls_ = np.empty(K); k = 0
    if n > 1 and _valid(f):
        scanEnd = min(n - 1, memoryDepth - 1)
        for i in range(scanEnd + 1):
            if i % spacing == 0:
                g = 0.0
                for j in range(6): g += w[j] * math.log(1.0 + abs(f[j] - bank[i, j]))
                cl = bank[i, 6]
                if not np.isnan(g) and cl != 0:
                    if k < K:
                        gaps[k] = g; cls_[k] = cl; k += 1
                    else:
                        worst = 0; wg = gaps[0]
                        for j in range(1, k):
                            if gaps[j] > wg: wg = gaps[j]; worst = j
                        if g < wg: gaps[worst] = g; cls_[worst] = cl
    total = 0.0; bull = 0.0; bear = 0.0; score = 0.0; gs = 0.0
    for j in range(k):
        wg = 1.0 / (1.0 + gaps[j]); total += wg; score += cls_[j] * wg
        if cls_[j] > 0: bull += wg
        if cls_[j] < 0: bear += wg
        gs += gaps[j]
    analog = score / total if total > 0 else 0.0
    d = 1 if analog > 0.15 else (-1 if analog < -0.15 else 0)
    agree = ((bull if d == 1 else (bear if d == -1 else 0.0)) / total) if total > 0 else 0.0
    avgGap = gs / k if k > 0 else 0.0
    gapScale = (w[0] + w[1] + w[2] + w[3] + w[4] + w[5]) * 0.45 + 0.000001
    tight = _clamp(1.0 - avgGap / gapScale, 0.0, 1.0)
    return analog, agree, tight, k


@njit(cache=True)
def _aima_loop(F, outcome, memoryDepth, K, h_, spacing, useNeural, neuralInf, lr, huberD,
               useFisher, fSpeed, fFloor, minRows, fixed_best):
    n = F.shape[1]
    banks = np.zeros((4, memoryDepth, 7)); cnt = np.zeros(4, np.int64)
    bankAll = np.zeros((memoryDepth * 4, 7)); cntAll = 0
    wA = np.ones(6); nw = np.array([0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.0]); mo = np.zeros(7); ve = np.zeros(7); step = 0
    best = np.full(n, 3, np.int64); drive = np.zeros(n)
    b1, b2, eps = 0.9, 0.999, 1e-8
    for t in range(n):
        # ---- bank update (rows: features h_ bars ago + outcome now)
        if t > h_ + 120 and t - h_ >= 0:
            for s in range(4):
                fr = F[s, t - h_]
                if _valid(fr):
                    row = np.empty(7); row[:6] = fr; row[6] = outcome[t]
                    cnt[s] = _add(banks[s], cnt[s], row, memoryDepth)
                    cntAll = _add(bankAll, cntAll, row, memoryDepth * 4)
        # ---- Fisher weights
        if useFisher:
            imp = np.ones(6)
            if cntAll >= minRows:
                sB = np.zeros(6); sS = np.zeros(6); qB = np.zeros(6); qS = np.zeros(6); nB = 0; nS = 0
                for i in range(cntAll):
                    cl = bankAll[i, 6]
                    if cl != 0:
                        for j in range(6):
                            val = bankAll[i, j]
                            if cl > 0: sB[j] += val; qB[j] += val * val
                            else: sS[j] += val; qS[j] += val * val
                        if cl > 0: nB += 1
                        else: nS += 1
                if nB > 3 and nS > 3:
                    fish = np.zeros(6); mx = 0.0
                    for j in range(6):
                        mB = sB[j] / nB; mS = sS[j] / nS
                        vB = max(0.0, qB[j] / nB - mB * mB); vS = max(0.0, qS[j] / nS - mS * mS)
                        fish[j] = (mB - mS) ** 2 / (vB + vS + 0.000001); mx = max(mx, fish[j])
                    for j in range(6):
                        nm = fish[j] / mx if mx > 0 else 1.0
                        imp[j] = max(fFloor, nm * 8.0)
            for j in range(6): wA[j] = wA[j] + fSpeed * (imp[j] - wA[j])
        w = wA.copy() if useFisher else np.ones(6)
        # ---- kNN analog scores per source
        an = np.zeros(4); ag = np.zeros(4); ti = np.zeros(4); kk = np.zeros(4)
        for s in range(4):
            a_, g_, t_, k_ = _knn_score(F[s, t], banks[s], cnt[s], w, memoryDepth, spacing, K)
            an[s] = a_; ag[s] = g_; ti[s] = t_; kk[s] = k_
        # ---- neural online training (close features h_ bars ago)
        tgt = 1.0 if outcome[t] > 0 else (-1.0 if outcome[t] < 0 else 0.0)
        if t - h_ >= 0:
            fc = F[3, t - h_]
            pred = nw[6]
            for j in range(6): pred += nw[j] * fc[j]
            err = pred - tgt
            grad = err if abs(err) <= huberD else huberD * (1.0 if err > 0 else (-1.0 if err < 0 else 0.0))
            if useNeural and t > h_ + 120 and _valid(fc) and tgt != 0:
                step += 1
                for j in range(7):
                    gj = grad * (fc[j] if j < 6 else 1.0)
                    mo[j] = b1 * mo[j] + (1 - b1) * gj; ve[j] = b2 * ve[j] + (1 - b2) * gj * gj
                    mh = mo[j] / (1 - b1 ** step); vh = ve[j] / (1 - b2 ** step)
                    nw[j] = nw[j] - lr * mh / (math.sqrt(vh) + eps)
        # ---- ranking
        r = np.zeros(4)
        for s in range(4):
            neu = 0.0
            if useNeural:
                neu = nw[6]
                for j in range(6): neu += nw[j] * F[s, t, j]
            ns_ = 1.0 / (1.0 + math.exp(-_clamp(neu, -8.0, 8.0)))
            raw = abs(an[s]) / 3.0 * 0.35 + ag[s] * 0.25 + ti[s] * 0.20 + ns_ * neuralInf + (0.10 if kk[s] >= K else 0.0)
            r[s] = _clamp(raw, 0.0, 1.0)
        ready = cnt[0] > 20 and cnt[1] > 20 and cnt[2] > 20 and cnt[3] > 20
        if not ready: r[:] = 0.25
        if r[0] >= r[1] and r[0] >= r[2] and r[0] >= r[3]: b = 0
        elif r[1] >= r[2] and r[1] >= r[3]: b = 1
        elif r[2] >= r[3]: b = 2
        else: b = 3
        best[t] = b if fixed_best < 0 else fixed_best
        drive[t] = _clamp(abs(an.mean()) * 0.20 + ag.mean() * 0.40 + ti.mean() * 0.40, 0.0, 1.0)
    return best, drive


@njit(cache=True)
def supertrend(src, c, stAtr, mult):
    n = c.size; L = np.full(n, np.nan); S = np.full(n, np.nan); D = np.ones(n, np.int64)
    for t in range(n):
        up = src[t] - mult[t] * stAtr[t]; dn = src[t] + mult[t] * stAtr[t]
        if t == 0 or np.isnan(L[t - 1]): L[t] = up
        else: L[t] = max(up, L[t - 1]) if c[t - 1] > L[t - 1] else up
        if t == 0 or np.isnan(S[t - 1]): S[t] = dn
        else: S[t] = min(dn, S[t - 1]) if c[t - 1] < S[t - 1] else dn
        if np.isnan(up): L[t] = np.nan
        if np.isnan(dn): S[t] = np.nan
        if t == 0: D[t] = 1
        elif D[t - 1] == -1 and (not np.isnan(S[t - 1])) and c[t] > S[t - 1]: D[t] = 1
        elif D[t - 1] == 1 and (not np.isnan(L[t - 1])) and c[t] < L[t - 1]: D[t] = -1
        else: D[t] = D[t - 1]
    return D, L, S


def aima_signals(o, h, l, c, control=None, memoryDepth=40, K=9, horizon=4, spacing=4, learnAtr=0.45, useNeural=True,
                 neuralInf=0.35, lr=0.01, huberD=0.02, useFisher=True, fSpeed=0.20, fFloor=0.40, minRows=80,
                 srcSmooth=3, stLen=10, stMult=1.7, stAdapt=0.80):
    """control=None -> the AI as published. control=d (a number) -> source fixed to close and multiplier fixed at stMult*(1+stAdapt*(1-d))."""
    o, h, l, c = (np.asarray(a, float) for a in (o, h, l, c))
    a14 = atr(h, l, c, 14)
    F = np.stack([_features(x, h, l, a14) for x in (o, h, l, c)])          # (4, n, 6)
    mv = c - shift(c, horizon); band = learnAtr * shift(a14, horizon)
    with np.errstate(invalid="ignore"):
        outc = np.where(mv > 2 * band, 3, np.where(mv > band, 2, np.where(mv > 0, 1, np.where(mv < -2 * band, -3, np.where(mv < -band, -2, np.where(mv < 0, -1, 0))))))
    outc = outc.astype(float)
    best, drive = _aima_loop(F, outc, memoryDepth, K, horizon, spacing, useNeural, neuralInf, lr, huberD,
                             useFisher, fSpeed, fFloor, minRows, -1 if control is None else 3)
    hard = np.choose(best, [o, h, l, c]).astype(float)
    aiSrc = ema(hard, srcSmooth)
    mult = stMult * (1.0 + stAdapt * (1.0 - (drive if control is None else np.full(c.size, float(control)))))
    D, L, S = supertrend(aiSrc, c, atr(h, l, c, stLen), mult)
    return D, dict(best=best, drive=drive, aiSource=aiSrc, stLong=L, stShort=S, mult=mult)


# ------------------------------------------------------------------ self-tests
def _synth(n=6000, seed=1):
    rng = np.random.default_rng(seed); r = rng.normal(0, 0.002, n)
    c = 100 * np.exp(np.cumsum(r)); o = np.r_[100, c[:-1]] * (1 + rng.normal(0, 0.0003, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.001, n))); l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.001, n)))
    v = rng.integers(50, 500, n).astype(float)
    return o, h, l, c, v


def self_test():
    ok = True; o, h, l, c, v = _synth()
    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    # Pine helpers
    x = np.arange(1, 11, dtype=float)
    chk("ta.ema seeded with an SMA (len 3: first value = mean of 1..3 = 2, next = 0.5*4+0.5*2 = 3)", np.isclose(ema(x, 3)[2], 2) and np.isclose(ema(x, 3)[3], 3))
    chk("ta.rma seeded with an SMA (len 2: 1.5, then 0.5*3+0.5*1.5 = 2.25)", np.isclose(rma(x, 2)[1], 1.5) and np.isclose(rma(x, 2)[2], 2.25))
    chk("population stdev", np.isclose(stdev_pop(x, 10)[-1], np.std(x)))
    # lastguru
    t1, d1 = knn_signals(o, h, l, c, v); t0, d0 = knn_signals(o, h, l, c, v, apply=False)
    nx = int(d1["longc"].sum() + d1["shortc"].sum())
    xb = np.flatnonzero(d0["longc"] | d0["shortc"])
    chk(f"unfiltered: {len(xb)} crossovers, position = +1 after every long cross and -1 after every short cross",
        len(xb) > 50 and np.all(t0[np.flatnonzero(d0["longc"])] == 1) and np.all(t0[np.flatnonzero(d0["shortc"])] == -1))
    chk("filter only ever skips crossovers (filtered changes are a subset of unfiltered crossover bars)",
        set(np.flatnonzero(np.diff(t1) != 0) + 1) <= set(np.flatnonzero(d1["longc"] | d1["shortc"])))
    # hand-checked kNN vote: 3 stored rows + the dummy row
    adx = np.array([10., 10., 50., 50., 12.]); mfi = np.array([10., 10., 50., 50., 11.]); src = np.array([1., 1., 2., 0.5, 1.])
    lc = np.array([True, False, True, False, True]); sc = np.array([False, False, False, True, False])   # bar 4 is a crossover too (the vote is computed on crossover bars)
    tg, fl = _knn_loop(adx, mfi, src, lc, sc, 2, 1, True)
    # rows: dummy(0,0,r0), stored at t0: (0,0, 1>=0 -> +1); at t2: (10,10, 2>=1 -> +1); at t3: (50,50, 0.5>=2 -> -1)
    # bar 4 first stores (50,50, 1>=0.5 -> +1), then queries (12,11): two nearest = (10,10) d=2.24 [+1] and (50,50) d=54.4 vs (0,0) d=16.3 x2 -> k=2 smallest {2.24, 16.3}, threshold 16.3 -> rows (10,10)+1, (0,0) 0, (0,0) +1 = 2
    chk(f"kNN vote matches a hand calculation (got {fl[4]:+.0f}, expected +2)", fl[4] == 2)
    # no look-ahead: changing bars after t leaves every decision up to t unchanged
    cut = 4000; o2, h2, l2, c2, v2 = (a.copy() for a in (o, h, l, c, v))
    for a in (o2, h2, l2, c2): a[cut + 1:] *= 1.07
    v2[cut + 1:] *= 3
    t2, _ = knn_signals(o2, h2, l2, c2, v2)
    chk("lastguru: no look-ahead (future bars changed, all decisions up to the cut identical)", np.array_equal(t1[:cut + 1], t2[:cut + 1]))
    # Zeiierman
    D, dd = aima_signals(o, h, l, c)
    D2, _ = aima_signals(o2, h2, l2, c2)
    chk("Zeiierman: no look-ahead (future bars changed, every trend state up to the cut identical)", np.array_equal(D[:cut + 1], D2[:cut + 1]))
    chk(f"Zeiierman: source switches happen ({len(set(dd['best'][200:].tolist()))} of 4 sources used) and flips occur ({int((np.diff(D) != 0).sum())})",
        len(set(dd["best"][200:].tolist())) >= 2 and (np.diff(D) != 0).sum() > 20)
    chk("Zeiierman: band multiplier stays inside [1.7, 3.06]", np.nanmin(dd["mult"]) >= 1.7 - 1e-9 and np.nanmax(dd["mult"]) <= 1.7 * 1.8 + 1e-9)
    Dc, dc = aima_signals(o, h, l, c, control=0.5)
    # control equals a plain supertrend on ema(close,3) with a fixed multiplier
    Dp, _, _ = supertrend(ema(c, 3), c, atr(h, l, c, 10), np.full(c.size, 1.7 * (1 + 0.8 * 0.5)))
    chk("control = a plain Supertrend on EMA3(close) with a fixed multiplier", np.array_equal(Dc, Dp))
    print("ALL PASS" if ok else "FAILURES"); return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]: sys.exit(0 if self_test() else 1)
    print(__doc__)
