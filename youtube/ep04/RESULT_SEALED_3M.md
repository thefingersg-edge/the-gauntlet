# The sealed segment — first out-of-sample read, all six arms

```
WINDOW:   2026-08-29 to 2026-11-06 (ten weeks)
WHY THAT  Every one of the 21 daily files previously ended on or before
DATE:     2026-08-28. This window is therefore unseen by the gate runs in
          RESULTS_ALL.md for EVERY market, not just some.
DATA:     refreshed from OANDA's own API via the project's fetch_oanda.py,
          then rebuilt by make_daily.py. Same feed as the originals, so no
          cross-feed problem. All 21 files now end 2026-11-06.
SAMPLE:   12 to 66 trades per arm. Small. See the caveat, which is the
          most important paragraph here.
```

## The readings

| Arm | backtest net/trade | sealed net/trade | n |
|---|---|---|---|
| **F** dip-buy (part A) | **+0.513%** | **+0.020%** | 13 |
| E twin sleeve | −0.088% | **+0.606%** | 23 |
| C ORB intraday | −0.016% | −0.086% | 66 |
| A Donchian 55/20 | −0.091% | −0.953% | 12 |
| D v3 trend + index MR | +0.031% | −0.861% | 34 |
| B path continuity | −0.057% | −2.065% | 32 |

**Five of six were negative in the sealed window.** ARM F stayed positive
at about 4% of its backtested edge. ARM E flipped from negative to
positive, on 23 trades.

No ratio column: four of the six baselines are negative, and a ratio
against a negative base is arithmetically meaningless — the same trap the
robustness gate hit earlier in this project.

## The caveat, which is the result

**Ten weeks is not a test.** Twelve to sixty-six trades per arm cannot
separate any of these numbers from noise. ARM E's sign flip and ARM F's
collapse are equally likely to be the same thing: a short window with a
particular character. Nothing in this table belongs on screen as a finding
about any strategy.

What it *is* good for: the pipeline now works end to end, on the real feed,
with a registered window and registered predictions. The twelve-month test
in `FORWARD_REGISTRATION.md` is what settles it, and this is the first
monthly tracker entry rather than an answer.

## The verdicts did not move

Every arm was re-scored on the refreshed data. **All seven verdicts are
identical** to the run on data ending 2026-08:

```
  ARM A       1 of 7      ARM D       2 of 7
  ARM B       2 of 7      ARM E       1 of 7
  ARM C       6 of 8      ARM F  A    5 of 7
                          ARM F  A+B  4 of 7
```

Ten extra weeks and a corrected final bar on every file moved the
full-sample per-trade figures slightly — ARM A −0.078% to −0.091%, ARM E
−0.051% to −0.088%, ARM D +0.050% to +0.031% — all downward, and none far
enough to change a gate. That the conclusions survive a data refresh is
worth more than any single figure in the table above.

## Two defects found and fixed in the project's own pipeline

**1. `--resume` was dead in batch mode.** `fetch_oanda.py` skipped every
existing file before the resume branch could run, so `--all --resume`
refreshed nothing and printed "exists, skipping" for all of it. That is why
the files had three different end dates: they were built in separate passes
and the script had been quietly declining to touch them ever since.
Fixed; backup at `fetch_oanda.py.bak-preresume`.

**2. Resumed files ended up with two timestamp formats.** Rows kept from
the existing file retained `+00:00`; rows fetched from the API were written
naive. `make_daily.py` then refused to parse the result outright — which is
the lucky outcome. The dangerous one is a reader that accepts both and
silently mis-stamps half the file by four or five hours, which is exactly
what would have happened to any session-boundary logic. This is the same
defect found earlier in `spx500usd_oanda_h1.csv`; the cause is now known.
`fetch_oanda.py` now canonicalises every timestamp on write, and
`make_daily.py` parses mixed files rather than failing. Backups kept.

Neither defect changed a result. Both would have, eventually.
