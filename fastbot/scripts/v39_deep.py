#!/usr/bin/env python3
"""PREREGISTRATION_v39 Part D -- deep learning on raw 5-minute price shape plus
the v37 timeline. RUN THIS ON YOUR MAC (it uses the Apple GPU if present):

    python3 -m pip install torch numpy          # once
    python3 ~/RStudio/Claude/fastbot/scripts/v39_deep.py

Same yearly walk-forward as v39_models.py (train on every year before, test
the year), same direction labels, same trading rule. Writes
data/v39/deep_years.csv. About 15-40 minutes on an M-series Mac.
I am not a financial adviser. This is a measurement, not a recommendation.
"""
import csv, hashlib, math, os, sys, datetime as dt
import numpy as np
import torch, torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = ("PREREGISTRATION_v39.md", "f42c19b2b1f015dbd198108ccc07d8647744005f29f49550d9e359e7e2d77d93")
YEARS = list(range(2012, 2027))
EPOCHS, PATIENCE, BATCH, LR = 40, 5, 512, 1e-3
torch.manual_seed(39); np.random.seed(39)
dev = torch.device("mps" if torch.backends.mps.is_available() else "cpu")


def auc(y, p):
    y = np.asarray(y, bool); r = np.argsort(np.argsort(p)) + 1.0
    n1, n0 = y.sum(), (~y).sum()
    return (r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)


def day_shift(y, dates, rng):
    ud = np.unique(dates); k = int(rng.integers(20, len(ud) - 20))
    pos = {d: np.where(dates == d)[0] for d in ud}; out = np.empty_like(y)
    for i, d in enumerate(ud):
        a, b = pos[d], pos[ud[(i + k) % len(ud)]]
        out[a] = y[b[np.arange(len(a)) % len(b)]]
    return out


class Net(nn.Module):
    def __init__(self, nx):
        super().__init__()
        self.cnn = nn.Sequential(nn.Conv1d(1, 32, 5, padding=2), nn.ReLU(), nn.Conv1d(32, 32, 5, padding=2), nn.ReLU(),
                                 nn.AdaptiveAvgPool1d(1), nn.Flatten())
        self.mlp = nn.Sequential(nn.Linear(nx, 64), nn.ReLU(), nn.Dropout(0.3))
        self.head = nn.Sequential(nn.Linear(96, 32), nn.ReLU(), nn.Dropout(0.3), nn.Linear(32, 1))

    def forward(self, s, x):
        return self.head(torch.cat([self.cnn(s.unsqueeze(1)), self.mlp(x)], 1)).squeeze(1)


def fit(S, X, y, d, S_te, X_te):
    cut = np.sort(np.unique(d))[-126]
    core, inner = d < cut, d >= cut
    med = np.nanmedian(X[core], 0); X = np.where(np.isnan(X), med, X); X_te = np.where(np.isnan(X_te), med, X_te)
    mu, sd = X[core].mean(0), X[core].std(0) + 1e-6
    X, X_te = (X - mu) / sd, (X_te - mu) / sd
    S, S_te = np.nan_to_num(S), np.nan_to_num(S_te)
    T = lambda a: torch.tensor(a, dtype=torch.float32, device=dev)
    net = Net(X.shape[1]).to(dev); opt = torch.optim.Adam(net.parameters(), LR, weight_decay=1e-4)
    lossf = nn.BCEWithLogitsLoss()
    Sc, Xc, yc = T(S[core]), T(X[core]), T(y[core]); Si, Xi, yi = T(S[inner]), T(X[inner]), T(y[inner])
    best, bad, state = 1e9, 0, None
    for ep in range(EPOCHS):
        net.train(); perm = torch.randperm(len(yc), device=dev)
        for i in range(0, len(yc), BATCH):
            b = perm[i:i + BATCH]; opt.zero_grad(); lossf(net(Sc[b], Xc[b]), yc[b]).backward(); opt.step()
        net.eval()
        with torch.no_grad():
            l = lossf(net(Si, Xi), yi).item()
        if l < best - 1e-4:
            best, bad, state = l, 0, {k: v.clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= PATIENCE:
                break
    net.load_state_dict(state); net.eval()
    with torch.no_grad():
        return torch.sigmoid(net(T(S_te), T(X_te))).cpu().numpy()


def simulate(sig, dates, net_):
    tn, block, last = [], 0, None
    for i in range(len(sig)):
        if dates[i] != last: block, last = 0, dates[i]
        if block > 0: block -= 1; continue
        if sig[i] != 0: tn.append(net_[i][0] if sig[i] > 0 else net_[i][1]); block = 8
    return np.array(tn)


def main():
    got = hashlib.sha256(open(os.path.join(HERE, "..", DOC[0]), "rb").read()).hexdigest()
    if got != DOC[1]:
        print("PREREGISTRATION_v39.md changed since frozen. Refused."); sys.exit(2)
    print(f"v39_deep.py  device {dev}\nI am not a financial adviser. This is a measurement, not a recommendation.\n")
    z = np.load(os.path.join(HERE, "../data/timeline_v37/matrix.npz")); sh = np.load(os.path.join(HERE, "../data/v39/shapes.npz"))
    d, X, S = z["date"], z["X"].astype(np.float32), sh["s78"]
    hit = (z["yl"] == 1) | (z["ys"] == 1); up = (z["yl"] == 1).astype(np.float32)
    netm = np.column_stack([z["gl"] - z["spread"], z["gs"] - z["spread"]])
    rng = np.random.default_rng(39); prev = {}
    out = []
    for Y in YEARS:
        tr = hit & (d < f"{Y}-01-01"); te_all = (d >= f"{Y}-01-01") & (d <= f"{Y}-12-31") & (d <= "2026-09-17")
        if (te_all & hit).sum() < 200: continue
        for name in ("DEEP", "DEEP-NULL"):
            y = up[tr] if name == "DEEP" else day_shift(up[tr], d[tr], rng)
            p = fit(S[tr], X[tr], y, d[tr], S[te_all], X[te_all])
            h = hit[te_all]; a = auc(up[te_all][h] == 1, p[h])
            nb, nt = float("nan"), 0
            if name in prev:
                lo, hi = np.quantile(prev[name], [0.1, 0.9])
                tn = simulate(np.where(p >= hi, 1, np.where(p <= lo, -1, 0)), d[te_all], netm[te_all])
                if len(tn): nb, nt = float(tn.mean()), len(tn)
            prev[name] = p
            out.append(dict(model=name, year=Y, auc=a, net_bp=nb, trades=nt))
            print(f"  {Y} {name:<9} AUC {a:.4f}  trades {nt:>4} net {nb:+.2f}", flush=True)
    with open(os.path.join(HERE, "../data/v39/deep_years.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print("\nwritten data/v39/deep_years.csv -- tell Claude it is there.")


if __name__ == "__main__":
    main()
