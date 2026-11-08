# ARM G — how to run it

## Setup

A **new chat**. Memory off. No project.

Attach these three files, which are in this folder:

```
PROGRAMME.md     the programme's cross-project summary
REGISTRY.md      every pre-registration and result, 184 and 162
EP04_BRIEF.md    the six blind arms, the gates, the measured costs
```

Unlike arms A-F this run is NOT sealed — that is the point. Everything it
gets is published or about to be, so a viewer can assemble the same pack
and repeat it.

Take the **first output**. No regenerating. If it refuses or pushes back,
that is the result.

## The message

```
Attached is the complete record of a systematic trading research
programme: a cross-project summary, a registry of 184 pre-registrations
and 162 results, and the full results of six AI-generated strategies put
through its gates.

Daily bars, 21 markets, 2005 to 2026:
  FX           eurusd gbpusd usdjpy usdcad audusd eurgbp eurjpy
  metals       xauusd xagusd xptusd xcuusd
  indices      spx500usd nas100usd de30eur
  energy       bcousd natgasusd
  rates        usb10yusd de10ybeur
  softs        cornusd wheatusd sugarusd
Open, high, low, close for every bar. No volume on the FX and metals
series. Hourly bars are available for all 21, and 15-minute bars for 11.

It will be judged against the seven gates in EP04_BRIEF.md, with the
measured cost table in that file, on this data.

Read what has already been tried and closed. Then build me the strategy
you think has the best chance of clearing all seven gates — and tell me
what the attached record rules out, so I can see you have used it.

Tell me what economic reason it has for working. Tell me what result would
make you abandon it. And tell me honestly whether you think the programme's
accumulated negative results make this search better or just better
informed.

Give me the strategy as a complete, mechanical specification that someone
else could implement without asking you a single follow-up question. It
must state, explicitly:
  - which instruments it trades, from the list above
  - the bar timeframe it operates on
  - the exact entry condition, as a formula or an unambiguous rule
  - the exact exit condition, including any stop or target
  - position sizing, in units that work on a $10,000 account
  - every parameter value, with no ranges and no "tune this"
If a rule depends on a value you have not fixed, fix it now and say what it
is. Do not give me code. Give me the specification.
```

## What is being scored, fixed before the run

See `../ARM_G.md` for the three registered predictions. In short:

1. **Avoidance** — does it propose anything on the closed list? Five of the
   six blind arms proposed trend following. If ARM G does too, the briefing
   was not used.
2. **Holding period** — does it hold days rather than weeks, and say that
   financing is why? That is the one thing our gates found that every blind
   arm missed.
3. **Gates** — we expect it NOT to clear all seven. If it does, that is the
   headline, and the publication rule in `../PUBLICATION_POLICY.md` point 3
   is triggered before anything is shown.

## Where to put the output

```
youtube/ep04/generated/run1_armG.md
```

Raw. Do not tidy, trim the preamble, or drop the caveats.
