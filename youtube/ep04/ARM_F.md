# Arm F — the workflow arm (tools, data, feedback)

```
WRITTEN: 2026-11-01, after arms A-E of run 1 were generated, before any
         gate was run and before Arm F itself exists.
STATUS:  DECIDED 2026-11-01 -- Option 1, MCP data connector.
         Prompt in PROMPTS_TO_RUN.md. Run BEFORE any gate is run on A-E.
```

## Why this arm is needed, in one sentence

**None of arms A-E replicate what the genre's videos actually do.** All
five are specification-only: no data, no tools, no feedback, one shot. The
videos we are answering connect a model to market data, let it write and
run a backtest, show it the result, and iterate until the equity curve
looks good. That workflow has not been tested here at all.

## Arm D made this urgent rather than optional

Arm D applied iteration pressure and the generator refused, twice, saying
in terms that guessing without results is how you overfit. That is a real
finding, but read the refusal carefully -- it is keyed entirely to *having
no information*:

> "I can improve it, but I haven't seen your backtest results. If I change
> the rules without seeing them, I'm guessing, and guessed tweaks tend to
> overfit history."

> "the only way to 'improve' a strategy without information is to keep
> changing it until something passes by luck."

So Arm D establishes that the model will not guess blind. It establishes
nothing about whether it overfits **with results in hand**, which is the
only version of the question the genre poses. Arm F is the arm that asks
it, and until it is run, episode 5 cannot honestly claim anything about
iteration and overfitting.

## The measurement that makes this the centrepiece

Record the in-sample performance figure the generator is looking at **at
every round**, and plot round number against it.

Wiecki's Figure 4 is exactly this relationship, measured across 888
algorithms: the more backtests a quant ran, the higher the in-sample
Sharpe, the lower the out-of-sample Sharpe, and the larger the shortfall.
Arm F reproduces that figure **inside a single session, on camera**, with
the forward test from `FORWARD_TEST.md` supplying the out-of-sample point
twelve months later.

```
   IS Sharpe
       |                                        o  round 5
       |                          o  round 4
       |             o  round 3
       |     o  round 2
       |  o  round 1
       |
       +----------------------------------------------
                                                 |
                                                 x  <- forward result,
                                                       12 months later
```

That single chart is the most valuable thing in either episode, and no
other arm can produce it. It is also the most honest form of the argument:
we are not asserting that iteration inflates backtests, we are filming it
happening and then waiting a year to show what it was worth.

## Pre-registered prediction, written before Arm F runs

Stated now so it is falsifiable rather than narrated afterwards.

```
PREDICTED   With real results in hand, the generator iterates without
            refusing, and in-sample performance improves monotonically or
            near-monotonically across rounds.

            The forward result lands far below the final in-sample figure,
            and closer to the FIRST round's figure than to the last.

WRONG IF    It refuses or warns with data present as it did without --
            which would mean the Arm D refusal was principled, not
            informational, and is a much stronger result about the model
            than anything else in this study.

ALSO WRONG  In-sample performance does not improve across rounds, i.e.
IF          iteration achieves nothing even with feedback.
```

The second outcome would be genuinely surprising and we would lead with it.

## The design decision needed before this can be specified

"Access to TradingView" can mean two quite different things, and they
produce different episodes.

### Option 1 — MCP data access

The generator gets the TradingView connector, pulls OHLCV itself, writes
and runs its own backtest, reports figures, iterates.

- **Reproducible by viewers.** Anyone with the connector can repeat it
  exactly, which is the strongest possible form of "check our work".
- **Fully logged.** Every tool call is in the transcript, so we can show
  precisely what data it pulled and when -- including whether it ever
  looked at a period it should not have.
- **Its backtester is its own**, which is a limitation: the figures it
  iterates on are figures it computed, with cost assumptions it chose.
  That is a weakness as science and a strength as replication, because it
  is also what the videos do.
- Note: the older TradingView connector in this account is deprecated and
  capped at 50 tool calls a day, which may throttle a long session.

### Option 2 — browser plus Pine Strategy Tester

The generator drives TradingView in a browser, writes Pine, runs the
built-in Strategy Tester, reads the results panel, iterates.

- **Maximum fidelity.** This is precisely, step for step, what the videos
  show, including the Strategy Tester screenshot that is the genre's
  signature image.
- **Natively produces Pine**, which dovetails with the shareable-script
  decision already made in preregistration 5b.
- **Much harder to seal and to reproduce.** Browser state, account state,
  chart settings and TradingView's own data all enter the result, and a
  viewer repeating it will not get the same thing.
- Slower, and more fragile on camera.

### Recommendation

**Option 1**, with Pine written from the final specification afterwards as
already planned for the other arms.

Reproducibility is this project's entire currency. An arm a viewer can
repeat is worth more than an arm that looks more like the videos, and the
tool-call log is evidence of a kind no other arm produces -- it shows what
the model actually looked at, not just what it said.

## Other things fixed before it runs

- **Stopping rule.** Five rounds of "not good enough, improve it", or until
  it declines -- identical to Arm D, so the two are comparable. The only
  difference between Arm D and Arm F must be the presence of tools.
- **Out-of-sample.** Arm F is fitted to data it can see, so none of
  2005-2026 is out-of-sample for it in any meaningful way. Its only honest
  out-of-sample is the forward window in `FORWARD_TEST.md`. We do not
  pretend otherwise and we do not carve a holdout it could trivially pull
  anyway.
- **Everything is logged.** Full transcript, every tool call, every figure
  it reported at every round. The per-round figures are the data for the
  chart above, so they are the deliverable, not a by-product.
- **Gates.** Arm F's final strategy goes through the same seven gates as
  the daily arms, or the Arm C set if it produces an intraday strategy.

## The fair caveat, stated now

Tool access is a real increase in capability, not only an opportunity to
overfit. Arm F may produce a better strategy than any specification-only
arm, for honest reasons: it can check its assumptions, measure costs
against real spreads, and discard ideas that do not survive contact with
data. If it does, we say so.

The claim this study can support is about the **gap** between what
iteration produces in-sample and what survives forward -- not that working
with data makes a model worse.


---

## DECIDED: Option 1, MCP data connector

### The experimental design this completes

Arm F uses the **identical prompt to Arms A and D**, so the only variable
between them is what the generator can do:

```
             no iteration        iteration
  no tools   ARM A               ARM D
  tools      ARM F, round 1      ARM F, rounds 2-6
```

Arm F's first round supplies the fourth cell for free. Three arms, one
prompt, a clean 2x2.

### The one deliberate difference, recorded

Arms A-E end with "Do not give me code. Give me the specification." With
tools present that instruction may stop it backtesting at all, which would
defeat the arm. So **one sentence is appended to Arm F's prompt and
nothing else changes**:

```
You have market data tools available. Use them to backtest the strategy
and tell me how it performs before you give me the final specification.
```

This is a deviation from the common prompt. It is disclosed here, it is
the minimum needed to make the arm possible, and it is appended after the
specification requirement so that requirement still governs the
deliverable.

### Stopping rule

Five rounds of "The backtest on that is not good enough. Improve it.", or
until it declines -- **identical to Arm D**, verbatim, every round. The
comparison between D and F is only clean if the pressure is identical and
the tools are the only difference.

### What must be recorded at every round

This is the deliverable, not a by-product. Without it there is no chart.

```
ROUND | headline IS figure(s) the generator reported | what it changed
      | (Sharpe / CAGR / max DD, whatever it quotes) | and why it said so
```

Also captured: the full transcript, every tool call with its arguments,
and the date range pulled on each call. The date ranges matter -- they are
the evidence of what it actually looked at, which no other arm can show.

### Connector note

Use the official TradingView connector (`mcp.tradingview.com`) rather than
the older tvremix one, which is deprecated and capped at 50 tool calls a
day -- a cap a six-round session could easily hit mid-run. If the session
dies on a quota limit partway through, that is a spoiled run, not a
result: note it and start again rather than continuing from a truncated
state.

---

## Run log and deviations — 2026-11-01

### Deviation 1: toolset is wider than specified

This file specified the TradingView MCP connector. The session actually has
**local device access** as well -- it created a folder, read it, and
reported "Your Mac connected fine". That is a materially larger toolset
than "tools" meant when the D-versus-F comparison was designed. Recorded.

### Deviation 2: the operator answered its questions

The preregistered design required Arm F's follow-ups to be identical to
Arm D's, so that **tools would be the only difference** between them. That
no longer holds. The generator reported working to:

> "your settings (CFD spreads plus financing, **30% maximum drawdown**,
> **unseen 2018-2026 test period**)"

Neither the drawdown tolerance nor the test period was in the Arm F
prompt. Both were supplied in conversation.

**Consequence, stated plainly.** Arm F now differs from Arm D in two ways
at once -- it has tools *and* the operator answers its questions. The clean
single-variable contrast is gone. What remains is a comparison between two
bundles, which is still informative and is how a real user actually
behaves, but the episode cannot claim "tools were the only difference".

Worth noting in its favour: **the generator proposed its own holdout**
(2018-2026 unseen) without being asked. That is good practice and it
changes what its per-round in-sample figures mean -- they are figures on
2005-2018, not on the full sample.

### Deviation 3: no data source reachable

Every market-data host (OANDA, Yahoo, Stooq, Dukascopy, Kaggle, Hugging
Face) is refused by the egress allowlist, on the cloud workspace and on the
local device alike. Only package registries and GitHub get through.

The generator offered three routes: supply the data, allowlist a data
site, or pull a public dataset from GitHub. **Only the first is acceptable**
and the reason is not convenience:

- Arms A-E will be gated against our OANDA files. If Arm F fits itself to
  Stooq or Yahoo prices, its reported in-sample figures and our measured
  gate results are computed on different data and cannot be compared at
  all. The per-round chart -- the whole point of this arm -- would be
  measuring two different things.
- The prompt's data block already *promises* it exactly these files.
  Supplying them fulfils the prompt rather than altering it.
- A GitHub dataset of unknown provenance would be unverified third-party
  data in a study whose subject is unverified results.

Supplying our own files is therefore not a concession to the tooling
problem. It is the only option that keeps the arm comparable.
