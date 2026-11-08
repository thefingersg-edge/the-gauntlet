# The Gauntlet

The research behind the YouTube channel
**[The Gauntlet — Finding the Edge](https://www.youtube.com/@TheGauntlet-FindingtheEdge)**:
every pre-registered test, every result, and the code that produced them.

Most of it is failure. That is not an apology — it is the finding.

```
184   pre-registrations
162   results
 25   registered, not yet run
  4   results with no matching registration
```

*Counts from [`REGISTRY.md`](REGISTRY.md), generated 2026-10-31. `registry.py` rebuilds it.*

## The rule

Every test here was written down before the data was touched. The
pre-registration states the hypothesis, the gates it has to clear, and the
condition that kills it. Then it runs, once. The result file records what
happened — including the times what happened was that my own code was wrong.

A backtest you can keep adjusting will eventually tell you what you want to
hear. The registration is the only thing that stops that.

### What this proves, and what it does not

You can read any registration, read the result that cites it, and re-run the
code against it. That part is solid.

What a git repository cannot prove by itself is *when* a file was written.
Commit dates are set by the author and can be rewritten, so the history here is
not evidence of sequence to anyone inclined to doubt it. The internal check is
that **82 of the 155 result files pin the sha256 of the registration they ran
against**, which means a registration quietly edited afterwards no longer
matches its own result. The other 73 carry nothing but my word for it.

I would rather state that plainly than imply a guarantee the repository does
not give.

## The episodes

| # | episode | the files behind it |
|---|---|---|
| 01 | *I Tested Chart Patterns on 21 Years of Data* | [`pineport/adaptive/PREREGISTRATION_ZOO.md`](pineport/adaptive/PREREGISTRATION_ZOO.md) → [`FINDINGS_ZOO.md`](pineport/adaptive/FINDINGS_ZOO.md). Detectors in `b1_shapes.py`, `b2_reversals.py`. |
| 02 | *Nine Candlestick Patterns Passed My Test. Then I Found The Bug.* | [`pineport/adaptive/PREREGISTRATION_CANDLESPACE.md`](pineport/adaptive/PREREGISTRATION_CANDLESPACE.md) → [`FINDINGS_CANDLESPACE.md`](pineport/adaptive/FINDINGS_CANDLESPACE.md). The matched control that broke, and its replacement, are in `b3_pattern_zoo.py`. |
| 03 | *Twenty Tests. Nothing Ever Passed. Then One Did.* | [`fastbot/RESULT_VIXCURVE.md`](fastbot/RESULT_VIXCURVE.md), [`RESULT_VIXDAILY.md`](fastbot/RESULT_VIXDAILY.md), [`RESULT_VIXCARRY.md`](fastbot/RESULT_VIXCARRY.md). Code in `fastbot/scripts/vix_*.py`. |
| 04 | *(in production)* | [`youtube/ep04/`](youtube/ep04/) — seven AI-generated strategies put through the same seven gates, six of them sealed from the project's own history. |

`RESULT_VIXCURVE.md` is worth reading for one reason beyond its subject: it was
published with stale figures, caught two months later, and restated in place
with every superseded number recorded in its §8. The verdict did not change.
Several of the headline claims did.

## Start here

- **[`PROGRAMME.md`](PROGRAMME.md)** — what the projects found when read together. One page.
- **[`REGISTRY.md`](REGISTRY.md)** — the generated index of all 184 registrations and what became of each.
- **[`REGISTRY.csv`](REGISTRY.csv)** — the same thing, machine-readable.

## Verifying a result

1. Open the result file. Its lead line is the verdict; the `SPEC:` line names the
   registration it ran against and, usually, that file's sha256.
2. Check the sha: `shasum -a 256 <registration>` against the value in the result.
3. Read the registration *first*. Decide whether the gates are honest before
   you see whether they were cleared.
4. Re-run the script named in the result. You will need the price data, which
   is not in this repository — see [`DATA.md`](DATA.md).

## What is not here

**The price data.** Roughly 18 GB of OANDA and TradingView bars sit behind
these tests. It is left out for size, and because redistributing a vendor's
market data is very likely against the terms I obtained it under.
[`DATA.md`](DATA.md) lists every series used and how to fetch it.

**My own trading records.** A personal journal of live trades exists in the
working tree and is deliberately excluded. It is not needed to check anything
here.

**Any API credentials.** Every script reads its key from an environment
variable. There is no key in this history, and `.gitignore` is written to keep
it that way.

## Found a bug?

Open an issue. I have a standing offer on the channel: **if you find a real
error in one of these results, I will make a video about it.** That is not a
figure of speech — four of the episodes so far are substantially about my own
mistakes, and the registry contains a correction notice for a result that stood
wrong for two months.

The errors most worth hunting, based on the ones already caught: controls that
quietly throw away most of the sample, timezone handling on session-stamped
bars, sign conventions in financing costs, and anything ranked by a statistic
that discards its own sign.

## Layout

```
PROGRAMME.md      the cross-project read
REGISTRY.md       generated index of every registration and result
registry.py       regenerates the above

fastbot/          event studies, forward tests, the VIX work
pineport/         the pattern families — twelve of them, none cleared
flows/            announcement, earnings and FX-value flows
silver15/         residual mean reversion against a gold-implied fair value
youtube/ep04/     the AI-strategy arms and the seven-gate engine
```

## Licence

Code is MIT. Prose, registrations and results are CC BY 4.0. See
[`LICENSE`](LICENSE).

## Not advice

Nothing here is investment advice. Almost everything in this repository is a
record of something that did not work, and the one thing that survived its
gates was rejected anyway on cost and risk. Trade your own money on your own
judgement.
