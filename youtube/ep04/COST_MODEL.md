# The cost model — a flaw, and the fix

```
FOUND:  2026-11-06, before any of this went on screen.
STATUS: results in RESULTS_ALL.md stand, with this disclosure attached,
        until a measured table replaces the current one.
```

## What is wrong

`gates/engine.py` describes its spread table as "one model for all six
arms", fixed before any arm was run. That is true but incomplete. **The
table is an exact copy of ARM B's**, all twenty-one values:

```
  eurusd 2bp   gbpusd 3bp   usdjpy 2bp   usdcad 3bp   audusd 3bp
  eurgbp 3bp   eurjpy 4bp   xauusd 5bp   xagusd 10bp  xptusd 25bp
  xcuusd 15bp  spx500usd 3bp  nas100usd 4bp  de30eur 4bp
  bcousd 8bp   natgasusd 30bp  usb10yusd 6bp  de10ybeur 6bp
  cornusd 25bp  wheatusd 25bp  sugarusd 30bp
```

Every figure matches ARM B's generated cost table exactly.

**So one contestant's assumption was used to judge the other five.** ARM F's
overnight sleeve and ARM C both failed on costs, and the costs that failed
them came from a competing arm. A critic would be right to call that out,
and they would find it in ten minutes because both tables are published.

It did not favour ARM B — it failed anyway, on 2 of 7. But that is luck,
not method.

## Why it is not fatal

The two verdicts the cost model actually decides are already reported as
cost-decided, with each arm's own assumption printed beside ours:

- **ARM F part B**: gross +0.0508%, our cost 0.0497%, net +0.0011%. On its
  own cheaper assumption it is worth 2.5-4% a year.
- **ARM C**: gross +1.92bp, our cost 3.50bp. On its own assumption,
  marginally positive.

No verdict rests on a hidden number. But "we disclosed it" is weaker than
"we measured it", and this is measurable.

## The fix: measure the spread from the broker

OANDA serves bid and ask as separate candle streams, so the spread is an
observable, not an estimate. The project already has the precedent —
`score_holdouts.py` uses `MEASURED_SPREAD = 0.25`, "half the measured 0.50
median, per registration".

Run, on the Mac:

```bash
cd ~/RStudio/Claude/pineport
python3 fetch_oanda.py --all --price B --start 2024-01-01
python3 fetch_oanda.py --all --price A --start 2024-01-01
python3 fetch_oanda.py --diversifiers --price B --start 2024-01-01
python3 fetch_oanda.py --diversifiers --price A --start 2024-01-01
```

That writes `*_oanda_h1_bid.csv` and `*_oanda_h1_ask.csv` without touching
the mid files. **A third defect was fixed to make this safe**: in batch mode
the output filename ignored `--price`, so `--all --price B` would have
overwritten twenty years of mid data with bid data, silently. Patched.

Two years is enough for a median and keeps the fetch short. The spread is
then `median((ask - bid) / mid)` per market, doubled for a round trip, and
that becomes the table — measured, from the broker the strategies would
actually trade at, owing nothing to any arm.

## What changes afterwards

Only two results can move: ARM F's part B and ARM C, both of which sit
within a basis point of their own costs. Everything else fails or passes by
margins no plausible spread table touches.

If the measured table is *cheaper* than ARM B's guess, ARM F's full spec
may clear gate 3 and ARM C may turn marginally positive. **That would be a
better outcome for the episode, not a worse one**, because it would mean the
honest number was found rather than assumed — and because a result that
changes when the cost assumption is measured is itself the point: at this
edge size, the broker is the strategy.
