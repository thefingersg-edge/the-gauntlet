# RESULT — v46: turn of the month. There is a small turn-of-month tilt, but it is a fraction of the historical effect and does not beat ordinary holding after costs.

```
SPEC:     PREREGISTRATION_v46.md  sha 86d564dc…
METHOD:   tom_v46.py 1.0; SPX500, NAS100 (OANDA 5m, data/) and UK100 (OANDA 5m, data/v38); cash-close bars; log data/run_v46.log; windows data/tom_v46_trades.csv
RUN:      2026-09-27
VERDICT:  G1 FAIL   G2 FAIL   G3 FAIL   -> FAIL
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Interpretations fixed in the harness before the run
- TOM is the close of day −2 to the close of day +3, on each instrument's own session list.
- The reference is the remaining sessions, cut into non-overlapping 4-session blocks.
- Cost is the spread at entry plus (DGS3MO + 2.5%)/365 for each calendar night. Before 2013, the 2013 median spread is used. DGS3MO is applied to UK100 as written.
- G1 uses the literal reading: TOM **net** minus reference **gross**. Net against net is reported only.
- The self-test passed: a planted +150 bp passes G1 and a planted zero edge fails it.

## Numbers (bp per 4-session window; SEs clustered by month)
```
windows: SPX 259, NAS 259, UK 260 TOM;  2,972 reference blocks
pooled TOM gross +23.7, cost 10.6, net +13.1;   reference gross +10.0 (net -0.1)
G1  TOM net - reference gross    +3.2 bp   t +0.23                    FAIL
G2  TOM net by era  2005-12 +20.4   2013-19 -5.6   2020-26 +24.1      FAIL
G3  TOM-only Sharpe 0.23 over 260 months (bar 0.46)                   FAIL
reported: net vs net  +13.3 bp  t +0.96;   gross vs gross +13.8 bp
reported: per index   TOM gross / net / ref gross     eras net
  SPX500   +17.6 / +5.7  / +11.7     +0.4  -4.9  +23.5
  NAS100   +31.0 / +19.8 / +18.8    +12.6 +12.3  +36.4
  UK100    +22.6 / +13.9 / -0.5     +48.3 -24.2  +12.6
reported: Etula pre-turn (-6..-3) pooled gross +18.8 vs reference +10.0 (eras +26.5 +6.5 +22.4)
```

## Read it plainly
- **TOM windows did beat ordinary 4-day windows, by about 14 bp gross.** That is far from significant (t about 1). It is also well below both the 50–100 bp in the older papers and the 47 bp this test could detect.
- **Costs eat most of it.** A round trip plus about six nights' financing costs about 11 bp. Net of that, the TOM window is no better than just holding the index (G1 t 0.23).
- **It is not stable.** 2013–19 was negative pooled, and UK100 swung from +48 to −24 to +13 bp by era.
- **The Etula "weakness before the turn" is not there.** Days −6 to −3 were *stronger* than average (+18.8 bp against +10.0), not weaker.
- This is the same pattern as the rest of the programme: a well-known calendar effect is now small and unstable, and does not pay a CFD's costs.

## Caveats
- Using the 2013 median spread before 2013 may overstate costs in 2005–12. Gross-vs-gross is +13.8 bp either way, and G1 would still fail.
- The financing proxy is not OANDA's historical rate, and UK100 is charged a US rate.
- Daily cash-close bars are used; futures settlement prices would differ slightly.
