# Silver 15m mean-reversion

Separate from the XAUUSD work. Nothing here writes to that project.

    silver15/
    ├── data/      xagusd_15m.csv, xauusd_15m.csv, eurusd_15m.csv
    ├── scripts/   dukascopy.py, dukascopy_intraday.py, silver_mr.py
    ├── pine/      silver_mr.pine
    └── results/   one subfolder per run: config + frontier + coefficients

## Environment

`dukascopy.py` and `dukascopy_intraday.py` MUST live in the same folder --
the second does `import dukascopy`. Everything else is path-driven, so a flat
folder is fine; just drop the `../` prefixes below (`--out xagusd_15m.csv`,
`--data .`).

"pandas not recognised" is nearly always the wrong interpreter, not a missing
package. Either make a venv here:

    python3 -m venv .venv
    .venv/bin/pip install pandas numpy scikit-learn
    .venv/bin/python setup_check.py

or reuse the venv from the other project by absolute path:

    /path/to/other/project/.venv/bin/python setup_check.py

Then use that same interpreter for every command below. Note scikit-learn is
needed only by silver_mr.py -- the data pull runs on pandas + numpy alone, so
a missing sklearn will not block step 2.

## Order of operations

    cd scripts
    .venv/bin/python setup_check.py        # 0. environment + layout

    # 1. offline checks (no network)
    python dukascopy_intraday.py --self-test

    # 2. VERIFY THE DAY INDEX BEFORE ANY LONG PULL
    python dukascopy_intraday.py --instrument XAGUSD --verify --year 2024 --month 6

    # 3. pull all three instruments (~30-40 min each on first run, cached after)
    python dukascopy_intraday.py --instrument XAGUSD --tf 15m --start 2016 --out ../data/xagusd_15m.csv
    python dukascopy_intraday.py --instrument XAUUSD --tf 15m --start 2016 --out ../data/xauusd_15m.csv
    python dukascopy_intraday.py --instrument EURUSD --tf 15m --start 2016 --out ../data/eurusd_15m.csv

    # 4. backtest
    python silver_mr.py --data ../data --tf 15m | tee ../results/run_$(date +%Y%m%d_%H%M).txt

## Why three instruments

The primary signal is silver's residual from gold-implied fair value. Silver
alone cannot produce it. EURUSD is inverted into a DXY proxy because Dukascopy
publishes no dollar index.

## Two traps already handled, worth not re-introducing

* Month is zero-indexed on this feed; the day convention is verified rather
  than assumed (step 1). Getting either wrong yields plausible, wrong bars.
* Record field order is open, CLOSE, LOW, HIGH -- not OHLC.
