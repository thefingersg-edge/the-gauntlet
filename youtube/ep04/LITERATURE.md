# Episode 4/5 — verified literature

Every figure below was read from the primary document, not from a summary.
Where a figure is still second-hand, it says so. Nothing marked UNVERIFIED
goes on screen.

---

## 1. Wiecki, Campbell, Lent, Stauth — "All that glitters is not gold"

### Citation status

| Field | Status |
|---|---|
| Authors | VERIFIED: Thomas Wiecki, Andrew Campbell, Justin Lent, Jessica Stauth |
| Affiliation | VERIFIED: Quantopian Inc |
| Date | VERIFIED: 9 March 2016 |
| Journal | VERIFIED: The Journal of Investing |
| Volume / issue / pages | VERIFIED: 25(3), 69-80 |
| Issue | VERIFIED: Fall 2016, published 31 August 2016 |
| DOI (published) | VERIFIED: 10.3905/joi.2016.25.3.069 |
| DOI (SSRN preprint) | VERIFIED: 10.2139/ssrn.2745220 |
| SSRN abstract id | VERIFIED: 2745220 |

Two independent confirmations. The published DOI is self-describing:
`10.3905/joi.2016.25.3.069` decodes as the Journal of Investing (joi),
2016, volume 25, issue 3, first page 069. The publisher's article record at
pm-research.com/content/iijinvest/25/3/69 then states the full range
directly: "The Journal of Investing Fall 2016, 25 (3) 69 - 80".

Two dates are both correct and neither is wrong to use: the SSRN preprint
is dated 9 March 2016, the journal issue 31 August 2016. Cite the year as
2016 either way. Earlier caution in this file is resolved; it is kept in
the history below rather than deleted, because the reasoning was sound even
though the doubt turned out to be unnecessary.

**The published body is paywalled.** The article record shows metadata and
abstract only; the full text requires a subscription. So every body figure
in this file -- the per-metric R2 table, the Spearman result, the quoted
sentences, and all four internal inconsistencies in section 1d -- was read
from the **preprint** body, not the typeset one. That is almost certainly
fine, but it is a stated limitation: if a body quote becomes a narration
line, it should be checked against the published PDF if Dave can get one
through an institutional login. The abstract is the exception; we have the
published wording for that (section 1a) and should quote from it.

**On-screen citation card (approved for use):**

> Wiecki, Campbell, Lent & Stauth (2016)
> "All That Glitters Is Not Gold: Comparing Backtest and Out-of-Sample
> Performance on a Large Cohort of Trading Algorithms"
> The Journal of Investing, Fall 2016, 25(3), 69-80
> doi:10.3905/joi.2016.25.3.069

**Full reference, for the video description:**

> Wiecki, T., Campbell, A., Lent, J., & Stauth, J. (2016). All that glitters
> is not gold: Comparing backtest and out-of-sample performance on a large
> cohort of trading algorithms. The Journal of Investing, 25(3), 69-80.
> https://doi.org/10.3905/joi.2016.25.3.069
> Preprint: https://ssrn.com/abstract=2745220

Quote the **published** abstract (section 1a), not the preprint's.

### Source read

Re-hosted preprint PDF at smallake.kr, header reads
"Electronic copy available at: http://ssrn.com/abstract=2745220".
This is a preprint-style copy, not a typeset journal version. SSRN itself
is behind a Cloudflare bot check we did not attempt to circumvent.

### 1a. Published abstract vs preprint abstract

Dave supplied the publisher's typeset abstract. It is the same study with
the same figures, but it is NOT the same text. **Anything we put in quotation
marks on screen must come from the published version**, since that is the
version of record a critic will look up.

Substantive differences, preprint -> published:

- "we study" / "we find" -> "this article studies" / "the authors find"
  (third person throughout).
- "at least 6 months of out-of-sample performance" -> "at least six months".
- "higher order moments, like volatility and maximum drawdown" ->
  "higher-order moments, such as volatility and maximum drawdown".
- "portfolio construction features, like hedging" ->
  "portfolio construction features (e.g., hedging)".
- "training non-linear machine learning classifiers" ->
  "training nonlinear, machine-learning classifiers".
- The ML claim gains a comparator. Preprint: "out-of-sample performance can
  be predicted at a much higher accuracy (R2 = 0.17) on hold-out data".
  Published: "out-of-sample performance can be predicted with much greater
  accuracy (R2 = 0.17) on hold-out data **than when using linear, univariate
  features**."

That last one matters. The published wording is explicitly a comparison
against the univariate linear results -- 0.17 versus the sub-0.025 figures
in the table -- not a claim of absolute predictive skill. If we quote it,
we quote the comparator with it.

One nitpick a quant will make, and we should not repeat it uncritically:
the paper calls volatility and maximum drawdown "higher-order moments."
Volatility is the second moment; maximum drawdown is not a moment at all,
it is a path-dependent extremum. If we narrate this beat we should say
"risk measures" rather than echoing "higher-order moments", or we hand a
pedant an easy win on a point that is not ours.

Verbatim published abstract, as supplied, held for quoting:

> When automated trading strategies are developed and evaluated using
> backtests on historical pricing data, there exists a tendency to overfit
> to the past. Using a unique dataset of 888 algorithmic trading strategies
> developed and backtested on the Quantopian platform, with at least six
> months of out-of-sample performance, this article studies the prevalence
> and impact of backtest overfitting. Specifically, the authors find that
> commonly reported backtest evaluation metrics, such as the Sharpe ratio,
> offer little value in predicting out-of-sample performance (R2 < 0.025).
> In contrast, higher-order moments, such as volatility and maximum
> drawdown, as well as portfolio construction features (e.g., hedging),
> show significant predictive value of relevance to quantitative finance
> practitioners. Moreover, in line with prior theoretical considerations,
> the authors find empirical evidence of overfitting -- the more backtesting
> a quant has done for a strategy, the larger the discrepancy between
> backtest and out-of-sample performance. Finally, they show that by
> training nonlinear, machine-learning classifiers on a variety of features
> that describe backtest behavior, out-of-sample performance can be
> predicted with much greater accuracy (R2 = 0.17) on hold-out data than
> when using linear, univariate features. A portfolio constructed by using
> predictions on hold-out data performed significantly better out-of-sample
> than one constructed from algorithms with the highest backtest Sharpe
> ratios.

Note what the published abstract does NOT resolve: the four internal
inconsistencies listed below are all between the abstract and the body, or
within the body, so they stand unless the typeset body differs from the
preprint body too. If we end up quoting a body figure, it should be checked
against the published body, not the preprint.

### Sample — VERIFIED

- Initial sample: 7,152 algorithms developed and backtested on Quantopian.
- Filters applied: removed strategies trading a single stock; Sharpe < -1.0;
  backtested over fewer than 500 days; not invested on at least 80% of
  trading days; correlated > 0.95 with a strategy already in the sample.
- Final sample: **888 algorithms.** The paper: "these preprocessing steps
  removed a large part of our initial data set and left us with 888
  algorithms."
- Universe: US equities. Minute bars. Zipline simulator, modelling
  transaction costs, order delays, liquidity constraints, market impact
  and slippage.
- In-sample: 2010 to end of 2015. Algorithms written Jan-Jun 2015.
- Out-of-sample: June 2015 to February 2016.
- Abstract says "at least 6 months" OOS; the introduction says
  "at least 6 to 12 months."

### Headline finding — VERIFIED, quoted

Abstract: "commonly reported backtest evaluation metrics like the Sharpe
ratio offer little value" "in predicting out of sample performance
(R2 < 0.025)."

Discussion: "predictability of OOS performance was low (R2 < 0.25)
suggesting that it is simply not possible to forecast profitability of a
trading strategy based on its backtest data."

Discussion: "predictive information can indeed be extracted from a
backtest, just not in a linear and univariate way."

### Per-metric table — VERIFIED

IS vs OOS Pearson R-squared, as the paper states them:

| Metric | R2 | Direction | Note |
|---|---|---|---|
| Annual returns | 0.015 | **negative** | "weakly negative but highly significant", p < 0.001 |
| Sharpe ratio | 0.02 | positive | p < 0.0001 |
| Sortino ratio | 0.02 | positive | p < 0.0001 |
| Information ratio | < 0.005 | — | not significant |
| Calmar ratio | < 0.005 | — | not significant |
| Financial alpha | < 0.005 | — | not significant |
| **Annual volatility** | **0.67** | positive | p < 0.0001 |
| **Maximum drawdown** | **0.34** | positive | p < 0.0001 |

Also: Sharpe computed from only the **last** backtest year rose to
R2 = 0.05 (p < 0.0001, "not shown" in the paper).

The shape of this is the single most useful thing in the paper for us:
**what a backtest tells you about is risk, not return.** Volatility and
drawdown carry over. Returns do not — and if anything invert.

### Overfitting from backtest intensity — VERIFIED, quoted

Results: "we confirmed a weak (Spearman R2=0.017) but highly significant
(p < 0.0001) positive correlation between the logarithm of the backtest
days and Sharpe ratio shortfall."

Figure 4 caption: "the more backtests a quant ran, the higher the IS Sharpe
ratio, the lower the OOS Sharpe ratio, and the larger the shortfall."

Discussion: "we find significant evidence that the more backtests a user
ran, the bigger the difference between IS and OOS performance."

Note the paper's own word for the relationship: **weak.** If we use this
beat — and it is the beat that most directly indicts iterating on a
strategy until it looks good — we quote the direction and say the effect
size is small. R2 = 0.017 is not a thunderbolt.

### Machine-learning result — VERIFIED

A non-linear model on backtest features reached R2 = 0.17 on 20% hold-out
data (DataRobot's best was an Extra Trees Regressor). A 10-strategy
portfolio picked by a Random Forest's predicted Sharpe achieved an OOS
Sharpe the Results section gives as 1.8, against 0.7 for the top 10 by
in-sample Sharpe.

### Internal inconsistencies in the paper — DISCLOSE IF WE CITE

We found four. Any of them could be used against us if we quote one side
and a critic quotes the other.

1. **Figure 1 caption contradicts the body.** Caption: "None of the
   performance metrics show a significant correlation between their IS and
   OOS periods." Body: reports significant correlations for annual returns,
   Sharpe and Sortino.
2. **Abstract vs Discussion on Sharpe.** Abstract: Sharpe "offer[s] little
   value." Discussion: "Sharpe and Sortino ratio have the highest OOS
   predictability." Both are true — highest among a set of near-zeros — but
   quoting either alone misleads.
3. **Sharpe R2 figure.** Abstract says "< 0.025"; body gives 0.02 for
   full-IS Sharpe and 0.05 for last-year-only Sharpe.
4. **ML portfolio Sharpe.** Results say 1.8; Discussion says 1.2.

Safest on-screen quote is the abstract plus the per-metric table, since
those agree with each other.

### Limitations — PUT THESE ON SCREEN

Being first to state the weaknesses of our own best citation is the whole
brand. All verified from the paper:

- Population: "all algorithms were developed by Quantopian users," which
  the paper describes as including "engineers and academics with limited
  formal quant finance backgrounds." The paper says it "can not currently
  address" whether the results extend to professionals.
- Regime: the IS period was "a bull market with relatively little
  volatility," the OOS period "a flat-to-bear market with medium-to-high
  volatility." The paper tested a market-neutral subset and reports the
  results "are reproduced in this subset."
- ML caveat: "we cannot yet claim that this specific selection mechanism
  will work well on future data."
- Conflict of interest: the authors were employed by Quantopian, the
  platform that supplied the data, and the acknowledgements thank
  "John Fawcett, CEO of Quantopian, for generously supporting this
  research."

The population limitation cuts both ways for us, and we should say so out
loud: this is a cohort of retail and semi-professional algorithm writers.
That is *exactly* the population our episode is about — someone asking a
language model for a strategy — so it is arguably the most relevant
cohort in the literature rather than the least. But we do not get to use
it to say anything about professional quant funds.

---

## 2. Still to verify

Nothing else in the ep04/05 plan rests on an outside paper yet. If a beat
starts to, it gets a section here with the same treatment before it goes
anywhere near a script.

---

## 1b. The paper's own figures — read from the plots

Dave supplied four figures. These are read off the images; **the captions and
figure numbers are not in front of us**, so anything here that becomes a
narration line has to be checked against the published caption first. What
the plots show is nonetheless clearer than the prose.

### Fig. A — mean return vs annual volatility, 888 algorithms

x = annual volatility (0 to 0.40), y = mean returns (-0.1 to 0.7). A straight
blue line from the origin with slope 1 is labelled "Sharpe ratio IS = 1".
Curved contours are shaded by a colourbar reading "Sharpe ratio OOS", running
from about -0.9 (blue) to +1.2 (red).

- The dense mass of algorithms sits at volatility 0.05-0.20 and mean returns
  0.05-0.25, i.e. straddling and mostly under the IS Sharpe = 1 line.
- The contours are curved, not rays through the origin, so this is a fitted
  surface over the IS plane, not simple iso-Sharpe lines. Red (good OOS)
  is top-left: high return, **low** volatility. Blue (bad OOS) is the
  right-hand side: high volatility, regardless of return.
- The gradient runs far more steeply along the volatility axis than along
  the return axis. That is the paper's thesis drawn rather than stated.

CHECK BEFORE USE: confirm from the caption that the contours are a fitted
OOS surface and not something else. The reading above is inference from
the geometry.

### Fig. B — IS vs OOS, volatility and maximum drawdown  **(the money shot)**

Two panels side by side.

- Left, blue: annual volatility IS (x, -0.1 to 0.5) against annual
  volatility OOS (y). A tight, obviously linear cloud hugging a regression
  line with a narrow confidence band. This is the R2 = 0.67.
- Right, green: maximum drawdown IS (x, -0.3 to 0.1) against maximum
  drawdown OOS (y, -0.3 to 0.1). A much looser cloud, but with a clear
  positive tilt and a visible band. This is the R2 = 0.34.

**This is the single most valuable frame in the paper for us.** Put these
two panels beside an equivalent panel for Sharpe -- which at R2 = 0.02 is a
formless blob -- and the entire argument of both episodes is on screen with
no narration at all. Three scatter plots: two have a shape, one does not.

We should rebuild this in channel style rather than screenshot it, with our
own axes and the R2 printed on each panel. Credit on frame.

### Fig. C — random forest feature importances  **(new, and strong)**

Fifteen bars, importance 0 to 0.08, descending:

| Rank | Feature | Importance |
|---|---|---|
| 1 | tail_ratio | 0.072 |
| 2 | sharpe_ratio_last_year | 0.064 |
| 3 | **user_backtest_days** | **0.045** |
| 4 | kurtosis | 0.034 |
| 5-15 | skewness, sharpe_std, alpha_spy, median_max_short_pos_concentration, min_loss_per_losing_trade, total_pos_count, sortino_ratio, pct_trades_profitable, mean_hedge_ratio, mean_monthly_turnover, min_hedge_ratio | 0.026 down to 0.021 |

Two things here we did not have.

**(i) `user_backtest_days` is the third most important feature.** How much
backtesting the author did predicts out-of-sample performance better than
skewness, Sortino, alpha to SPY, hedging, turnover, or percentage of
profitable trades. This is a far harder version of the overfitting claim
than the Spearman R2 = 0.017 we were going to quote, and it comes from the
paper's own model rather than a univariate correlation. It is also directly
on-theme: the episode is about someone iterating with a language model until
the equity curve looks right, and the paper is saying the iteration count
itself is one of the most informative things about the result.

**(ii) No feature exceeds 0.072, and ranks 5-15 are effectively tied.** The
spread from 0.026 to 0.021 across eleven features is noise; we must not rank
within that tail on screen. The honest framing is "four features separate
from the pack, and even the best carries only about 7% of the importance" --
which is itself the point. There is no one number in a backtest that tells
you what you want to know.

### Fig. D — portfolio outcomes  **(the honesty beat)**

Two panels.

Left: cumulative return, x-axis May 2014 to Feb 2016, y 0.7 to 1.3. Three
series -- "Highest predicted Sharpe (n = 10)" in green ending about 1.16,
"Highest IS Sharpe (n = 10)" in orange ending about 1.06, and a dense fan of
"Random selections" in pale blue spanning roughly 0.80 to 1.28 at the end.
Green and orange track each other until around Aug 2015, then separate.

Right: distribution of the random selections' Sharpe ratios, centred near 0
with most mass between -1.5 and +1.5. An orange vertical line at about 0.7
(highest IS Sharpe) and a green one at about 1.8 (highest predicted Sharpe).

Read this carefully, because it cuts our way harder than the prose does:

- **The orange line sits inside the bulk of the random distribution.**
  Selecting the ten best algorithms by in-sample Sharpe produced a portfolio
  that a dartboard beats roughly a quarter of the time. "Picking on backtest
  Sharpe was not reliably better than picking at random" is a stronger,
  plainer and more quotable claim than "R2 = 0.02", and the paper's own
  figure is the evidence for it.
- The green line at 1.8 is genuinely out in the right tail, but the random
  distribution does reach there, and on the left panel a number of random
  paths finish above the green line. The machine-learning result is real and
  should not be oversold -- which is exactly what the published abstract's
  "than when using linear, univariate features" comparator is doing.

**DISCREPANCY TO RESOLVE BEFORE USE.** The paper states the out-of-sample
period as June 2015 to February 2016. This figure's x-axis starts **May
2014**, more than a year earlier, and the green and orange series track each
other closely until around August 2015. Either the figure includes a
pre-OOS stretch, or the portfolio formation date differs from the stated OOS
start, or the axis covers something else. We cannot narrate this chart until
that is settled from the caption and the body text. Flagging it here so it
does not get quietly used.

### What to do with these

1. Rebuild Fig. B in channel style. It is the episode's thesis in one frame.
2. Fig. C's top four, with the "even the best is 7%" caveat spoken aloud,
   replaces the weak Spearman correlation as our overfitting evidence.
3. Fig. D's right panel, with the orange line called out against the random
   distribution, is the strongest single image in the paper for episode 5.
4. Get the captions. Three of the four readings above are inference from
   geometry, and one carries an unresolved date discrepancy.
