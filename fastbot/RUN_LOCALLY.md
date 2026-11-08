# Running the M1 pull on your machine

Everything here runs locally. **The API token never leaves your machine** —
it isn't read, copied or transmitted by anything I have access to.

Assumes the layout the files were written into:

```
RStudio/Claude/
├── silver15/scripts/fetch_oanda.py      <- reused, untouched
└── fastbot/
    ├── scripts/  pull_m1.py  interval_budget.py  session_profile.py
    ├── data/
    └── results/
```

If `fetch_oanda.py` is somewhere else, add `--fetch-oanda-dir /path/to/it`
to every command below.

---

## Step 0 — environment (30 seconds)

```bash
cd ~/RStudio/Claude/fastbot/scripts
source ../../silver15/scripts/.venv/bin/activate      # the venv already there
python pull_m1.py --self-test
```

Expected: `ALL PASS`, 25 checks, no network used and no token needed. If this
fails, nothing below is worth running.

The token is found automatically from `$OANDA_API_TOKEN`, then
`~/.oanda_token`, then a `.oanda_token` beside `fetch_oanda.py` — whichever
you already use for the M15 pulls.

```bash
python pull_m1.py --check        # one request, confirms auth works
```

---

## Step 1 — the probe. **This is the decision point.**

```bash
python pull_m1.py --probe
```

Three instruments × two granularities, one request each, a few seconds total.
It prints how far back OANDA actually serves M1 and M5, and converts that
directly into the hurdle that matters:

```
2 years   -> 2-sigma bar 1.41 Sharpe
5 years   -> 0.89
10 years  -> 0.63
20 years  -> 0.45
```

Read it against the measured cost drag from `COST_BUDGET.md`: **0.82 Sharpe**
for NAS100 at 12 round trips/day inside 12:00–20:00 UTC, **0.27** at 4/day.

- **Bar comfortably below ~0.8** → cost is the binding constraint, the budget's
  conclusion holds, and a signal search is worth starting.
- **Bar around 1.4 or above** → detectability dominates and no amount of
  strategy work fixes it on this sample. The response is a longer hold or a
  coarser bar (which buys history), not a better indicator. The script says
  which of these it thinks you're in.

**Send me the probe output before starting Step 2.** If M1 depth is short,
Step 2 is a waste of an hour and the project takes a different shape.

---

## Step 2 — the pull. **M5 first, not M1.**

Probe result 2026-08-17: **21.6 years on all three indices**, 2σ bar 0.43
against a measured cost drag of 0.82. Cost is the binding constraint and the
pull is justified. But pull **M5** before M1:

- M5 gives the *same* 21.6 years — depth is identical, so the detectability
  bar is identical at 0.43.
- ~1.5M bars/side instead of ~7.8M: about 70MB per side against ~350MB, and
  ~5 minutes against ~25.
- The budget put the comfortable hold well above 5 minutes and capped the
  round-trip rate at 4–12/day. M5 bars are ample entry resolution for that;
  M1 only becomes necessary for execution modelling, and that comes after a
  signal exists.
- At ~70MB the files are small enough to send me directly, so I can run the
  analysis instead of handing you more commands.

```bash
python pull_m1.py --pull --instruments NAS100_USD --granularity M5
python pull_m1.py --derive-mid --instruments NAS100_USD --granularity M5
python pull_m1.py --verify --granularity M5 --instruments NAS100_USD
```

Defaults to bid and ask only. OANDA's mid is exactly `(bid+ask)/2` — I checked
it on your M15 set, 4,560 aligned bars, max difference 9e-13 — so pulling mid
would waste a third of the requests. Reconstruct it locally instead:

```bash
python pull_m1.py --derive-mid --instruments NAS100_USD --granularity M1
```

**Rough timing**, ~0.45s per request at 5,000 candles each:

| M1 depth | requests/side | both sides |
|---|---|---|
| 2 years | ~150 | ~2 min |
| 5 years | ~375 | ~6 min |
| 10 years | ~750 | ~11 min |
| 20 years | ~1,500 | ~23 min |

Safe to interrupt. It writes incrementally and **resumes from the last row on
disk**, so re-running the same command continues rather than restarting. If it
stops at the page limit it says so — just run it again.

Each file gets a `.meta.json` alongside it recording instrument, granularity,
side, host, row count, timestamps and a SHA-256 of the bytes. The token is not
in it.

To add the other two indices:

```bash
python pull_m1.py --pull --instruments SPX500_USD,US30_USD --granularity M1
```

---

## Step 3 — verify before trusting any of it

```bash
python pull_m1.py --verify --granularity M1 --instruments NAS100_USD
```

Independent of the code that wrote the files. Checks sort order, duplicate
timestamps, intervals off the M1 grid, impossible OHLC rows, and crossed
quotes (ask below bid). Prints `ALL FILES OK` or names what's wrong.

> This check has already earned itself once. The corrupted-file control in the
> self-test caught a bug in my own crossed-quote comparison: a duplicate
> timestamp made the index non-unique and the check crashed instead of
> reporting. Fixed, and the control that found it is still in there.

---

## Step 3b — audit the deep history. **Do not skip this.**

```bash
python audit_history.py --self-test
python audit_history.py --instruments NAS100_USD --granularity M5
```

`--verify` checks the file is well-formed. This checks the **data is what it
claims to be**, which is a different question and the one that matters when a
feed hands you 21.6 years of intraday history for a CFD that did not exist in
that form in 2005.

Two things it settles, both of which would silently flatter a backtest:

1. **Is the early history interpolated?** Per year it reports the share of
   zero-range bars, zero-volume bars, median bar range and the effective price
   grid. Data resampled or forward-filled from a coarser source is unmistakable
   once those are on the page — the control in the self-test forward-fills
   hourly data to 1m and gets flagged `FLAT NOVOL COARSE-GRID`, while genuine
   data raises nothing.
2. **What was the spread actually?** `COST_BUDGET.md` measured 0.44bp
   in-session — **in 2026**. In 2008 it was certainly wider, and the whole case
   for NAS100 rests on that number. Because the pull fetches both sides, the
   historical spread is measured per year rather than assumed. If the worst
   year exceeds 2× the budget figure, the tool says so and the backtest must
   charge the spread that applied at the time, per bar.

Any year flagged should be cut from the sample rather than averaged in.

---

## Step 4 — re-run the budget on real data

```bash
python interval_budget.py --data ../data
python session_profile.py --data ../data --instruments nas100usd
```

Both currently read M15 and scale volatility to 1 minute by `sqrt` of time.
That assumption is the weakest link in `COST_BUDGET.md`. With real M1 on disk
it can be replaced by measurement — send me the verified files' row counts and
date ranges and I'll switch the scripts over to reading M1 natively rather than
scaling.

---

## What to send back

The console output of Step 3b, and — if the audit comes back clean — the three
M5 files themselves (`nas100usd_bid_5m.csv`, `_ask_`, `_mid_`, ~70MB each).
Small enough to attach, and with them here I can do the rest rather than
sending you more commands.

## One thing to decide before any strategy code

21.6 years is enough history to hold out a decade and still have a decade to
work in. `pineport` optimised on the full span and spent the only thing that
could have tested it — the `COMPARISON_V7OPT.md` verdict table has
"out-of-sample evidence exists: ❌ none left — fitted on everything".

So the split should be fixed **now**, in writing, before anyone looks at a
chart: fit on 2005–2015, and do not touch 2016–2026 until a pre-registration
names the criteria. That decision costs nothing today and cannot be recovered
later.

## If something breaks

- `cannot find fetch_oanda.py` → pass `--fetch-oanda-dir`
- `401` / auth failure → token not found, or `--env practice` needed if the
  token is for a demo account
- `'NAS100USD' is not OANDA naming` → use the underscore form, `NAS100_USD`
- rate limiting → raise `--pause 0.3`
