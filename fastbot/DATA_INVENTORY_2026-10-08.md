# Data inventory and gaps — gold, S&P 500, Nasdaq 100, oil (2026-10-08)

**I am not a financial adviser. This is a measurement, not a recommendation.**

## 1. What is on disk
| Category | Data | Span |
|---|---|---|
| Index / gold prices (OANDA bid/ask) | SPX500, NAS100, US30, XAUUSD, EURUSD, DE30 at 15m (`data/v24`); SPX/NAS/US30 5m; UK100, JP225, AU200, EU50, DE30 5m (`v38`); NAS/SPX 1m (`m1_tf1`) | 2005→2026 (1m: 2022→) |
| **Oil prices** | **none** (Dave trades Brent CFD BCO_USD; the fills audit lists it "never tested") | — |
| Volatility | VIX daily (FRED, 1990→), VX1/VX2 futures (2004→), VIX3M, SKEW, **GVZ (gold volatility)** | long |
| Breadth / internals | S5FI, S5TH, ADD, ADV, DECL (TradingView); point-in-time S&P breadth rebuilt from Sharadar | 1998→ |
| Options / dealer positioning | DIX and GEX (SqueezeMetrics); CBOE total and equity put/call | 2011→ |
| Positioning | CFTC financial (TFF) for SPX, NAS, US30, EUR, **gold**; **CFTC disaggregated zips 2017–2024 (includes crude oil, not yet parsed)** | 2006→ |
| Sentiment | AAII weekly | 1987→ |
| Macro calendar | CPI, NFP, FOMC, jobless claims with release times; release surprises (`release_content.csv`) | 1994→ |
| Rates / credit / dollar | 2y, 10y, 3m T-bill, Baa−10y, high-yield OAS, broad dollar (weekly-published), policy rates, US gasoline | long |
| Single stocks | Sharadar full history: prices, fundamentals, insiders, 8-K events, S&P 500 membership | 1998→ |
| Microstructure | Databento: auction costs (400 trades), closing imbalances (2018→), SPY second-level path at the close | 2018→ |

## 2. What each market has already been tested against (all FAIL unless stated)
- **S&P 500 / Nasdaq:** bar patterns and structure (1m–4h), levels/VWAP, intraday momentum (noise band — forward-recorded), timeline ML model, macro releases, sentiment, breadth (narrow v56 pass, then BREADTH2 fail), credit/correlation overlays, dealer gamma (near-miss), turn-of-month, opex, rebalance, closing imbalance, earnings-season aggregates, pairs.
- **Gold:** London fix (worked pre-2015 only), festival seasonality (descriptive), sentiment, futures positioning, patterns (v51 structure included XAU).
- **Oil:** nothing.

## 3. What drives each market, and what we lack
| Market | Main documented drivers | Have | Missing (cost) |
|---|---|---|---|
| **Gold** | real interest rates (TIPS yield), US dollar, ETF flows, central-bank buying, fear/volatility, futures positioning | dollar (weekly), GVZ, CFTC, VIX | **10-year TIPS real yield (FRED DFII10, free)**; **GLD ETF holdings (SPDR site, free)**; central-bank purchases (World Gold Council, quarterly, free) |
| **S&P 500** | earnings, rates, credit, volatility regime, dealer/option hedging, systematic (CTA / vol-control) flows, buybacks | most of these | buyback blackout calendar (derivable from Sharadar earnings dates — free); fund flows (ICI weekly, free); options open interest by strike (OPRA — expensive) |
| **Nasdaq 100** | as S&P plus mega-cap earnings and rates sensitivity | as S&P | mega-cap earnings calendar (Sharadar — free) |
| **Oil** | inventories (EIA weekly, Wednesday 10:30 ET), OPEC+ decisions, futures curve (contango/backwardation), rig counts, dollar, positioning | gasoline price, CFTC disaggregated (unparsed) | **OANDA WTICO_USD / BCO_USD bid/ask (free, existing puller)**; **futures curve CL1/CL2 or Brent equivalents (TradingView, free; or Databento CME)**; **EIA weekly inventory history + consensus (EIA API free with a key; consensus from the TradingView calendar)**; Baker Hughes rig counts (free); OPEC+ meeting dates (manual) |

## 4. Never tested anywhere in the project
- **Time-series momentum / trend following** across gold, oil and the indices (daily–monthly). One of the best-documented premia over a century (Moskowitz, Ooi & Pedersen 2012; Hurst, Ooi & Pedersen). Uses data we mostly have.
- **Commodity carry** (futures curve shape) for oil — a risk premium, the same family as the VIX carry that survived (Koijen, Moskowitz, Pedersen & Vrugt, "Carry").
- **Oil inventory surprises** (EIA) — an event study, the one design that escapes the "more bars is not more evidence" rule.
- **Gold vs real yields** — mostly explains moves rather than predicting them; lower expected value.
