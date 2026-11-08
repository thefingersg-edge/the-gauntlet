# adaptive/ — eight pre-registered studies, 2026-08

Every study here has a `PREREGISTRATION_*.md` written **before** the run and a
matching `FINDINGS_*.md`. All were held to `../GAUNTLET.md`. Twenty-one markets,
daily bars, 2005–2026.

**One candidate passed. Seven did not. The eighth measured what the others were
worth.**

| # | candidate | verdict | the number |
|---|---|---|---|
| A1 | the optimal lookback persists | **FAIL** | ρ is *negative*; chasing last block's winner loses to a fixed pair |
| A2 | a state variable predicts next quarter's best speed | **FAIL** | best 4 of 11, against 2.75 expected by chance |
| A3 | an adaptive MA beats a fixed one | **FAIL** | 14 of 15 variants below the fixed curve at matched average lookback |
| A4 | refitting on recent data beats never refitting | **FAIL** | trailing windows cost 0.10–0.18 Sharpe, t = −3.9 |
| B | wedges and triangles carry information | **FAIL** | 41% detection survival on the pivot parameter; direction +0.02% vs +0.52% unconditional |
| C | grid agreement is worth something as a *size* | **FAIL 7/7** | sizing by \|A\| loses to using its sign |
| D | real yields predict gold at 3–12 months | **FAIL 4/5** | ρ −0.037, era-unstable; the *level* gives +0.635 with the sign backwards |
| E | the variance risk premium predicts returns | **FAIL 5/5** | loses to the implied-vol level 0 of 4 |
| **F** | **implied vol is the better sizing input** | **PASS 6/6** | dispersion 0.399 → 0.280; the flattest plateau here |
| G | …and it replicates | **PASS 2/2** | and caught a forward-fill bug worth 29% of a sample |
| H | allocation turns a small edge into a business | **FAIL 4/7** | on ten unseen markets the rule returns **+0.005** |

## The three things worth carrying forward

1. **Manage size, not direction.** Every directional test failed. Volatility
   targeting held, the stop-loss plateau held, implied-vol sizing held.
2. **The checks are the asset, not the strategies.** `../GAUNTLET.md` — four
   rules were added by these studies alone: the sampling grid (2.1), shared
   terms (1.1), effective sample size (3.2), stale inputs (1.6), and edge before
   diversification (0.5).
3. **Doing nothing beats all of it.** Buy-and-hold the 21-market basket returns
   Sharpe +0.624 at 4.95% a year. The best rule measured here returns +0.164 at
   0.80%. What the rules buy is drawdown, which is a risk case and has to be
   argued as one.

## Files

| | |
|---|---|
| `core.py` | data loading, state variables, the 26-pair crossover grid, metrics |
| `make_daily.py`, `g1_diversify.py` | build daily bars; measure effective sample size |
| `a1`–`a4`, `b1`, `c1`–`c2`, `d1`–`d2`, `e1`–`e2`, `f1`–`f3`, `g2` | the studies |
| `verify.py` | lookahead audit, detector sanity, noise checks |
| `macro/` | FRED series — real yields, breakevens, dollar, volatility indices |

Reproduce any study by running its script; each prints its own gates and
verdict. Nothing here is a recommendation to trade any particular way.


---

## Companion documents

- `CODE_REVIEW.md` — the 13 material defects found in this codebase and the
  order to fix them in.
- `UNEXPLORED.md` — literature scan of signal families we have never tested.
