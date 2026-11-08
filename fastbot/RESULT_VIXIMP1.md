# RESULT — VIXIMP1: a contango filter halves the VIX-carry crash, but a $10,000 account still can't hold one mini contract, and the return still trails the index

```
SPEC:     PREREGISTRATION_VIXIMP1.md  sha 649658db…  (frozen before any number)
METHOD:   scripts/viximp1_run.py (sha in PROVENANCE); roll construction from vix_daily_risk.py 1.2 (roll offset −6 identified, t 6.8, 268 rolls)
DATA:     VX1!/VX2! daily 2004-03-26 → 2026-08-18; FRED VIXCLS
RUN:      2026-10-10
VERDICT:  R1 contango filter FAIL (G1, G2 pass; G3, G4 fail)   R2 spot-VIX stop FAIL (all gates)
```
**I am not a financial adviser. This is a measurement, not a recommendation.**

## Costs used (researched 2026-10-10)
| item | value | source |
|---|---|---|
| Mini VIX (VXM) | $100 per vol point; tick 0.05 = $5 | Cboe (via Macroption) |
| IBKR exchange-fee recovery | $0.20 per VXM; $1.50 per fill all-in assumed | IBKR UK fee page |
| Margin, VXM front month | $572 maintenance, $629 heightened (Jul 2024) | Cboe CFE margin schedule |
| SVIX (−1x short-VIX ETF) | expense ratio 1.47%; US-domiciled, no PRIIPs KID, so **not sold to UK retail** | etfdb; justETF |

## Results (one VXM, net of roll and switch costs)
```
                          net/yr per VXM   t      eras (vol pts)          worst drawdown   worst day   in market
R0 always short           $778             2.16   +51.7 / +61.4 / +61.2   -68.2 = $6,820   -17.6       100%
R1 contango filter        $549             2.30   +54.5 / +30.8 / +37.7   -38.0 = $3,804   -10.3        83%
R2 VIX > 25 -> flat       $287             1.13   +19.9 / +45.6 /  -1.2   -50.8 = $5,075   -17.6        84%
episodes (vol pts)        2008 Sep-Dec    Feb-2018    Mar-2020
R0                        -31.4           -9.1        -32.4
R1                         +0.4           -2.8         -4.8
R2                         -3.5          -19.7         -4.8
```
**Account view (30% drawdown budget):**

| | $10k | $25k | $50k |
|---|---|---|---|
| R0 | 0 fit (1 VXM = 68% of account) | 1 VXM, +3.1%/yr | 2 VXM, +3.1%/yr |
| R1 | 0 fit (38%) | 1 VXM, +2.2%/yr | 3 VXM, +3.3%/yr |
| R2 | 0 fit (51%) | 1 VXM, +1.1%/yr | 2 VXM, +1.1%/yr |

The benchmark to beat is **5.1%/yr** (the index sized to the same budget, RESULT_VIXDAILY). No margin breaches occurred at these sizes.

**ETP route (context only):** a −1x daily short of the front month, with 1.47% fees, lost **113% in one day** on 5 Feb 2018, i.e. total loss. That is the XIV event: XIV lost 96% that day and was shut down by its issuer, from $1.9bn in assets.

## Read it plainly
- **The contango filter works as risk control.** It turned the 2008 crash from −31 vol points into +0.4, cut March 2020 from −32 to −5, and nearly halved the worst drawdown (−68 → −38). The premium survived (t 2.3, every era positive).
- **It is not enough for a small account.** One mini contract still risks 38% of $10,000 in the worst stretch. Even at $50,000, the return (+3.3%/yr) is below simply holding the index sized to the same risk (5.1%).
- **The spot-VIX stop is worse.** It exits after the damage has started, missed Feb 2018 entirely (−19.7), and gave up most of the premium.
- **Short-VIX ETPs are the cautionary tale.** They are also off-limits to UK retail.

## Decisions only Dave can make
1. **Risk appetite.** Even filtered, this is a strategy that can lose about 38 vol points ($3,800 per mini) on closing prices, and more intraday. Is any capital going to be exposed to that?
2. **Account.** It needs a futures account (e.g. IBKR) with roughly $25,000+ to hold even one contract within a 30% drawdown budget.
3. **Purpose.** On these numbers the VIX carry doesn't beat the index for a small account. Its value would be as a *diversifier* alongside equities (it pays when markets are calm). That is a portfolio question, not a standalone one, and it would need its own pre-registration.

**What the evidence supports:** nothing here justifies committing money. A paper forward record of R1 costs nothing, if wanted.
