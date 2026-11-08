# Who makes money from trading? The backtest market, the course sellers, and what happens if the 99% stop

```
WRITTEN:  2026-10-09      TYPE: literature review + reasoning (no new test). Companion to HAYSTACK_95PCT.md
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## 1. The backtesting market: why a great backtest predicts almost nothing
- **The largest study of real users' algorithms** is Quantopian's (Wiecki, Campbell, Lent & Stauth, 2016). It covered 888 strategies, each with at least 6 months of live trading after the backtest.
  - Backtest performance explained only about **1–2%** of later performance (R² ≈ 0.01–0.02). The Sharpe ratio was the "best" predictor, and it was still almost useless.
  - **The more someone backtested, the bigger the gap** between backtest and live performance. More tweaking produced more overfitting.
- **Published, peer-reviewed signals fade too.** McLean & Pontiff (2016, *Journal of Finance*) followed 97 return predictors from academic papers. Returns were about **26% lower** out of sample and about **58% lower** after publication, as people traded them away.
- **Our own record says the same.** About 1,000 hypotheses would throw up roughly 50 false "winners" by chance at the usual 5% bar. Several of our early "passes" died on re-checking:
  - a bug-driven false PASS in silver15 v3;
  - nine false passes from a broken control in the candle-pattern study (ep02).
- **What this means for anything sold with a backtest** (indicators, EAs, "signals", course strategies):
  - A backtest is the cheapest thing in the world to manufacture. Run enough variations and one will look brilliant.
  - Without the number of variations tried, an untouched out-of-sample period and costs included, a backtest is marketing.
  - Our standard (pre-register, freeze, run once, Bonferroni, beat random entries, every era) is what a backtest has to survive before it means anything.

## 2. How many people selling trading courses actually trade (profitably)?
**No census exists.** There is no dataset of "course sellers' verified trading accounts", so no honest single percentage can be given. The evidence that does exist all points the same way:

- **FTC v. Online Trading Academy (settled Sept 2020).** This was one of the largest US trading-education firms.
  - The FTC said OTA's *own* surveys and third-party data showed **"most purchasers made little to no money."**
  - Claims that its instructors and salespeople were successful traders were false or unsupported. Several high-profile pitchmen **admitted they did not make significant money trading**.
  - The judgment was $362M, partly suspended.
- **Finfluencers.** Kakhbod, Kazempour, Livdan & Schürhoff (2023, Swiss Finance Institute) measured the stock calls of social-media finance influencers:
  - 28% were skilled (+2.6% a month);
  - 16% were unskilled;
  - **56% were "antiskilled"**: their calls did *worse* than random (−2.3% a month), so doing the opposite would have paid.
  - **The antiskilled ones had more followers and more influence.**
- **The business-model logic** (reasoning, not data):
  - Course revenue is certain and scales with followers. Trading profit is uncertain and scales with capital.
  - Someone with a real, repeatable edge earns more by trading it with more money than by selling it. Selling it also destroys it, because edges decay once shared (McLean & Pontiff).
  - So the incentive points the other way: the course *is* the business.
- **Possible Gauntlet test (not run, needs your go-ahead), COURSE1:**
  - Take a fixed, pre-registered sample, e.g. the 50 most-subscribed English-language trading-education YouTube channels.
  - Record one fact per channel: does it publish an **independently verified** live track record (broker statement, audited account, or third-party verified such as Myfxbook "track record verified")?
  - Report the percentage. Name no individuals in the video unless the record is public and verified.

## 3. What would happen if the 99% stopped trading?
Short-term trading is close to **zero-sum before costs and negative-sum after**. The profits of the winners are largely the losses of the losers, minus what the middlemen take.

**What the evidence says:**
- **Where the losses go.** Barber, Lee, Liu & Odean (2009, *Review of Financial Studies*) used the complete Taiwan market record:
  - individual investors' trading losses came to **about 2.2% of GDP**, or 2.8% of personal income;
  - **institutions gained about 1.5 percentage points a year** from trading against them, and foreign institutions took nearly half of that.
- **How big the 99% is.** Retail is about **21% of US stock-market volume** (Bloomberg Intelligence, Q3 2025). Retail is a much larger share of CFD, retail forex, prop-firm and short-dated options volume.
- **Why the pros want this flow.** Brokers are *paid* to route retail orders to market makers (payment for order flow). Small, uninformed orders are profitable to trade against. Many CFD brokers keep clients' losses as revenue when they take the other side.

**What would happen** (reasoned from the above, not measured):
1. **The 1% would lose their main source of income.** Their edge is largely *made of* the 99%'s mistakes. Take the losing players out of a poker game and the professionals start losing to each other and to the house. **The needle exists because of the haystack.**
2. **Market makers and HFT firms would earn far less**, and spreads would probably **widen** for everyone who is left. Uninformed flow subsidises liquidity (the Glosten–Milgrom adverse-selection logic): with only informed traders left, quoting gets riskier.
3. **A whole industry would shrink or vanish:**
   - CFD brokers whose revenue comes from client losses;
   - prop firms that earn on failed challenge fees (only 1–2% of buyers ever get paid);
   - course sellers, signal and indicator vendors;
   - much of trading YouTube.
4. **Prices would barely care in the long run.** Long-term value is set by earnings, rates and long-horizon investors (pensions, index funds). Short-term "noise trading" adds volatility and occasional mispricing, as in GameStop 2021. Less of it would mean calmer short-term prices, and fewer of the dislocations that skilled traders feed on.
5. **Volume would fall sharply, and exchange and broker revenue with it.** Ordinary savers in index funds would be almost unaffected.

**The episode line:** *"The market doesn't need the 99%, but the trading industry does."*

## Sources
- Wiecki, Campbell, Lent, Stauth (2016), "All that Glitters Is Not Gold" (Quantopian), summary: https://www.cxoadvisory.com/big-ideas/in-sample-vs-out-of-sample-performance-of-888-trading-strategies
- McLean & Pontiff (2016), "Does Academic Research Destroy Stock Return Predictability?", *J. Finance*; CFA digest: https://rpc.cfainstitute.org/research/cfa-digest/2016/06/does-academic-research-destroy-stock-return-predictability-digest-summary
- FTC, Online Trading Academy settlement, 15 Sept 2020: https://www.ftc.gov/news-events/news/press-releases/2020/09/ftc-settlement-requires-online-trading-academy-forgive-consumer-debt-principals-turn-over-millions
- Kakhbod, Kazempour, Livdan, Schürhoff (2023), "Finfluencers", SFI WP 23-30: https://www.sfi.ch/en/publications/n-23-30-finfluencers
- Barber, Lee, Liu, Odean (2009), "Just How Much Do Individual Investors Lose by Trading?", *RFS* 22(2): https://ideas.repec.org/a/oup/rfinst/v22y2009i2p609-632.html
- Bloomberg Intelligence via Bloomberg Opinion (Rubinstein, 26 Nov 2025), retail 20.9% of US equity volume: https://www.bloomberg.com/opinion/articles/2025-11-26/after-gamestop-meme-stock-traders-are-growing-up
- Prop-firm payout rates: see HAYSTACK_95PCT.md (Finance Magnates, Mar 2025)
