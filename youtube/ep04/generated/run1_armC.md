# RUN 1 — ARM C (intraday persona) — raw first output

```
RECEIVED: 2026-11-01
PROMPT:   PROMPTS_TO_RUN.md, ARM C, pasted verbatim
RUN:      fresh chat, no project, memory off
STATUS:   first output, unedited.
```

The closing question was NOT answered. Per preregistration section 2 the
first output is the one that gets tested. The question is a real
implementation dependency and is tracked separately -- see the note at the
foot of this file.

---

Below is a complete specification. One thing first, because it matters more than any parameter: I haven't tested this on your data, and nobody can promise in advance that an intraday strategy will make money. The rules are based on a documented effect: on US index days, the direction of the first part of the session tends to carry into the last hour. That effect is real but small, and it has weakened in recent years. After costs it may be marginal. If you attach the hourly files for spx500usd and nas100usd, I can run this exact spec over 2005-2026 and tell you whether it actually holds up.

## Strategy: US index first-hour -> last-hour momentum

**Instruments:** spx500usd and nas100usd. They are traded independently, with at most one trade per instrument per day.

**Timeframe:** 1-hour bars. Daily bars are used only for ATR.

**Time convention:** All session times are America/New_York local time, with US daylight saving applied. Hourly bars are assumed to be stamped in UTC by their open time. So the 09:00 ET bar is the 13:00 UTC bar while daylight time is in effect (EDT) and the 14:00 UTC bar while standard time is in effect (EST).

**Definitions**

- C_prev = close of the 15:00-16:00 ET hourly bar on the previous NYSE trading day.
- C_open = close of the 09:00-10:00 ET hourly bar today.
- ATR = 14-period Wilder ATR of the daily bars, using daily bars up to and including the last completed daily bar before today.
- Move = C_open - C_prev, measured in index points.
- Threshold = 0.20 x ATR.

**Days traded**

- Trade every NYSE full trading day.
- Skip any day on which the NYSE closes early (13:00 ET).
- Skip the day after an NYSE holiday, because C_prev must come from the immediately preceding trading day.
- Skip any day where the 09:00, 15:00 or prior-day 15:00 ET bar is missing.

**Entry.** At the open of today's 15:00-16:00 ET hourly bar:

- Long if Move >= +Threshold.
- Short if Move <= -Threshold.
- Otherwise, no trade.

**Exit**

- Stop: 0.30 x ATR from the entry price. For a long, the stop is entry - 0.30 x ATR; for a short, it is entry + 0.30 x ATR. The stop is placed at entry and never moved.
- Stop fill rule: if the bar's low (for a long) or high (for a short) touches the stop, exit at the stop price.
- Time exit: if the stop is not hit, exit at the close of the 15:00-16:00 ET bar.
- No profit target.
- No position is ever held past 16:00 ET.

**Position sizing ($10,000 account)**

- Risk per trade = 1.0% of current account equity. That is $100 at $10,000.
- Units = floor(risk / (0.30 x ATR)). One unit is $1 per index point on these CFDs.
- Notional cap: reduce units so that units x entry price <= 3 x equity.
- Minimum size: if units = 0, skip the trade.
- Worst case: with both instruments stopped out on the same day, the loss is 2% of equity.

**Cost assumptions for any backtest**

- Round-trip spread of 1.0 point on spx500usd and 2.0 points on nas100usd.
- Additional 0.5 point of slippage on stop fills.
- No financing, since nothing is held overnight.

**Rough scale at today's levels.** These are illustrative figures only:

- spx500usd: a daily ATR of about 70 gives a stop of about 21 points and a position of about 4 units.
- nas100usd: a daily ATR of about 330 gives a stop of about 99 points and a position of 1 unit.

One question so I can make this airtight: are your hourly bar timestamps in UTC, stamped by bar open? If they're in another timezone, or stamped by close, the 09:00 and 15:00 bar mapping above shifts, and I'll restate it for your data.

I can also turn this into a doc you can hand to whoever implements it.

---

## Implementation dependencies and gate notes (added by us, not part of the output)

**1. Bar timestamp convention MUST be verified before running.** The spec
assumes hourly bars stamped in UTC by bar open, and derives the ET session
mapping from that assumption (09:00 ET = 13:00 UTC under EDT, 14:00 UTC
under EST). If our OANDA hourly bars are stamped by close, or in another
zone, every bar reference in the strategy is wrong and the result would be
noise. This is gate C8 (session integrity) and it is checked first, before
any P&L is computed.

**2. Breadth: Dave's call vindicated.** This strategy trades 2 instruments
by design. The original daily gate asked 14 of 21. The proportional
reformulation that was considered and rejected would have asked 8 of 12.
Both are unsatisfiable for a 2-instrument strategy, so removing the gate
and reporting the raw number was the only honest option available. Report:
how many of the markets it trades agreed in sign, out of how many it
traded.

**3. UNRESOLVED -- robustness versus the hypothesis.** Gate C3 as
preregistered perturbs every parameter by half a step "with time-of-day
parameters included", on the reasoning that session and clock parameters
are the ones most likely to have been fitted.

For this strategy that reasoning does not hold. The 15:00-16:00 hour is
not a tuned value, it **is** the hypothesis -- the claim is specifically
about the last hour of the US session. Moving it half a step does not test
robustness, it tests a different hypothesis, and it would fail by
construction.

This cannot be decided after seeing the result. Decision needed before the
gate run.
