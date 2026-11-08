# PROVENANCE — the inputs as they stood when v26, v27 and v28 ran

```
WRITTEN 2026-09-25, after the three runs, so that a reader can tell
        whether a later re-run used the same bars. data/v24 is APPENDED
        to by forward_tick.sh, so "the data" is not a fixed object and
        saying which version produced a number is not optional.
```

## The bar files as run

```
file                          rows      last bar (UTC)
de30eur_bid/ask_15m.csv    354,698      2026-09-18 19:45
eurusd_bid/ask_15m.csv     546,665      2026-09-18 20:45
nas100usd_bid/ask_15m.csv  505,999      2026-09-18 20:45
spx500usd_bid/ask_15m.csv  506,343      2026-09-18 20:45
us30usd_bid/ask_15m.csv    501,436      2026-09-18 20:45
xauusd_bid/ask_15m.csv     490,845      2026-09-18 20:45
events_v2.csv              CPI 413, payrolls 401, claims 903 at 08:30 ET
```

Every run excluded events from 2026-09-18 on, so the forward test's
sample is untouched by all three.

## Standing caveats that apply to all three result documents

1. **Cost before 2012 is understated.** bid == ask for 2005-2011 on
   SPX500, NAS100, US30 and DE30 (verify_pull.py, named in v24.1 s5).
   Gross figures are unaffected; every NET figure covering those years
   is kinder than reality.
2. **Financing is today's rate.** v27 charges -6.15%/yr on longs and
   credits +1.15%/yr on shorts, measured on SPX500_USD on 2026-09-04 and
   applied to twenty years and six instruments. In the 2009-2015 rate
   era the charge was much smaller. v27's conclusion does not rest on
   it: the gross increments beyond 09:45 were already flat.
3. **Excursion figures are 15-minute figures.** RESULT_PATHS Part A
   ("+13.27 bp left on the table", "73% of losers were once up +3 bp",
   "51% of winners were once 10 bp down") is measured on 15-minute bar
   extremes. On finer data every one of those numbers gets BIGGER, in
   both directions. They are lower bounds, not estimates.
4. **The control is not volatility-matched.** v27's +0.19 bp on ordinary
   mornings against +3.61 bp on release mornings compares all mornings,
   not mornings with similar-sized 08:30 bars. The control also contains
   other 08:30 releases (PPI, retail sales), which makes the contrast
   conservative rather than flattering.
5. **"Not a risk premium" is a claim about ONE kind.** v27 rules out a
   premium that accrues with holding time. It does not rule out a
   payment earned only inside the session.
6. **The same six instruments have now been queried across seven
   registrations.** Each run has its own gates, but nothing controls the
   error rate across the whole program, and which sample is "spent" for
   which question is recorded in prose rather than in a registry.

## v33 (2026-09-25)
Inputs as run: data/v24 15m bid/ask (six instruments), events_v2.csv, VIXCLS.csv (to 2026-08-31). PREREGISTRATION_v33 sha a730ea5e…; premarket_levels.py 1.0; output data/levels_v33_trades.csv, log data/levels_v33_run.log.

## v34 (2026-09-25)
Inputs as run: data/{spx500,nas100,us30}usd_{bid,ask}_5m.csv, VIXCLS.csv. PREREGISTRATION_v34 sha 546725b2…; general_levels.py 1.0; log data/general_v34_run.log.

## v35 (2026-09-25)
Inputs as run: data/{spx500,nas100,us30}usd_{bid,ask}_5m.csv. PREREGISTRATION_v35 sha bca23cad…; reactive.py 1.0; log data/reactive_v35_run.log.

## v36 (2026-09-25)
Inputs as run: data/{spx500,nas100,us30}usd_{bid,ask}_5m.csv, VIXCLS.csv. PREREGISTRATION_v36 sha aeffbae5…; momentum_v36.py 1.0; log data/momentum_v36_run.log.

## v37 (2026-09-26)
tl_build.py 1.1 (VX session-date fix), matrix.npz sha 6fc354b2...; timeline_v37_2.py; LOCK fb2f89ae...; logs data/timeline_v37/fit_v37_2.log, test_v37_2.log. Voided: v37 LOCK 1c93ecf5 (magnitude label), v37.1 LOCK 85be5ec7 (VX look-ahead).

## v37.3 (2026-09-26)
timeline_v37_3.py 1.0; matrix.npz 6fc354b2...; OLD model = LOCK_v37_2 fb2f89ae...; log data/timeline_v37/run_v37_3.log.

## v39 (2026-09-26)
v39_models.py 1.0; build_v39.py (shapes.npz, meta.npz); matrix.npz 6fc354b2...; logs data/v39/. Part D v39_deep.py pending (Mac).

## v38 (2026-09-26)
data/v38 (OANDA M5 bid/ask, 5 indices, pulled by Dave 2026-09-26); noise_v38.py 1.0; log data/v38/run_v38.log. v39 Part D: data/v39/deep_years.csv (Mac run).

## v40 (2026-09-26)
tl_build2.py 2.0 (Gate 0: identical to tl_build 1.1 on 42,121 SPX rows); v40_build.py -> data/v40/<stem>.npz; v40_confirm.py 1.0 -> data/v40/pred_<stem>.npy, test_v40.log. Registry housekeeping: PREREGISTRATION_FORWARD_v36.md pointer; SPEC/METHOD header lines added to v33-v40 results and TRACKA_D2/D3/LIQUIDITY; CLAUDE.md, PROGRAMME.md s.10, FINDINGS.md s.10 updated; registry.py re-run (79 prereg / 79 results; fastbot has 0 unlinked, 1 open = FORWARD_v36).

## v41 (2026-09-26)
Frozen model data/v41/forest_v41.pkl (sha e77aea7c...), freeze_v41.json (sha 7c338b95...), NAS100 history timeline data/v41/nas100_hist.npz; recorder forward_forest.py 1.0 (sha d2c42e69...); forward_tick.sh step 5 now pulls SPX500 M5 too. PREREGISTRATION_v41 sha ed9da57e...

## v42 (2026-09-27)
data/gex/DIX.csv (SqueezeMetrics, downloaded by Dave, sha b64bccce...); gex_v42.py 1.0; log data/gex/run_v42.log.

## v44-v49 frozen 2026-09-27 (harnesses to be written; each must pin its sha)
PREREGISTRATION_v44.md  7917ad0e7892da64df1c7d57f7e9051f1fa41f236b5cec9e250bb9fdc4189ab0
PREREGISTRATION_v45.md  69543678bcc92d7fc3ab4af4adeb6e94d84b72bdd03bcf1c4250f8a5426500ac
  -> run 2026-09-27: RESULT_REBAL_v45.md (rebal_v45.py 1.0) FAIL
PREREGISTRATION_v46.md  86d564dc80bcd5dcf2eb0b338285c9b64c78f37b39abe7bd4995ac2e3f49aba9
  -> run 2026-09-27: RESULT_TOM_v46.md (tom_v46.py 1.0) FAIL
PREREGISTRATION_v47.md  47a5d6eb384a5839bb425d28d036cf7c74517adc3f9294c0fcacd3c9ca724951
PREREGISTRATION_v48.md  2ad9b46b4083e2161a79e534aef48a241e781039b4ad4917eb8fe10eb917f287
  -> run 2026-09-27: RESULT_GOLDSEASON_v48.md (gold_season_v48.py 1.0) DESCRIPTIVE
PREREGISTRATION_v49.md  6a612316c5d96570518f426110d06950f378d7b358976fefc1243d263d082bc7
  -> run 2026-09-28: RESULT_UKOPEN_v49.md (ukopen_v49.py 1.0) FAIL
budget: scripts/budget_v44_49.py (counts and squared returns only)

## v48 event table frozen 2026-09-27, before any gold price joined
data/v48/events_v48.csv  b7640992bfbff8d1b64717d09ceca6a730ae995641794c656ecf858e8ef1ccd9
  (CNY: travelchinaguide; Diwali: when-is.com 2006-09, calendarific 2010-25 -- 2024 = Oct 31 per calendarific, some calendars say Nov 1)

## v50 frozen 2026-09-28 (fear/attention table; raw files to be downloaded by Dave into data/v50/raw/ and hashed here BEFORE reading)
PREREGISTRATION_v50.md  8560ed09ba26aad15dc3e637340203c8fc70d7fd57d57bfc10bdabfebcfda269
budget: scripts/budget_v50.py (squared 5m returns and VIX only), log data/budget_v50.log
v50 raw snapshot (hashed 2026-09-28 before any value was read; downloaded by Dave in the browser)
data/v50/raw/All_Daily_Policy_Data.csv  e444f4758a25c96c0527a38aaddcf3dfc742f8540b7c36c930ab74b31cd9142c  (US daily EPU, policyuncertainty.com)
data/v50/raw/data_gpr_daily_recent.xls  e5376ad7a25c7cbc19fa2d8aa8e8371b3d374dc7940d1a5b2716fda6bc58f6bd  (daily GPR, matteoiacoviello.com)
v50 raw snapshot, part 2 (hashed 2026-09-28 before any value was read)
data/v50/raw/tpu_web_latest.xlsx  5dc5d9406b1ce79540bc935f199c20e563e7060bed0c0fcf136c34b5c395da9f
data/v50/raw/tpu_web_latest_daily.xlsx  5dc5d9406b1ce79540bc935f199c20e563e7060bed0c0fcf136c34b5c395da9f
data/v50/raw/Stock_market_crash_google_trend.csv  56e6be715947373a456e16ea0416ca9ca60ce1f9d22424df1cebce02f3c6a738
data/v50/raw/Recession_google_trend.csv  0a3ab409abadda07f50769371b0abc7d1e04065ab2f7bdcf5dc50105d4135c55
  (the two TPU files are byte-identical; tpu_web_latest_daily.xlsx is the one used)
PREREGISTRATION_v50.1.md  6beae2ec94ca32c5f452761eef64a2b69499d1c13d0551f7d96922f5311b6364  (amendment: TPU daily starts 2015 -> primary C = EPU+GPR; frozen before the table was built)
data/v50/fear_table.csv  e58d9de5ea1f6e8ac9cb99fa6f7babca339b23d246d8804717c2922e40db594e  (fear_build_v50.py, from the hashed raw files only; frozen before any price join)
data/v50/trends_monthly.csv  350c5f84fc7030a2d78c67b5266292d38177cafa63d16118584fc6460b520a95
  -> run 2026-09-28: RESULT_FEAR_v50.md (fear_v50.py 1.0) G1 FAIL G2 FAIL G3 FAIL -> NOT USEFUL
  -> CLOSED 2026-09-28 by Dave: duplicates VIX; forward record not started

## v51-v53 frozen 2026-10-01 (batch: BOS/CHoCH; 200-day MA overlay; credit + stock-bond correlation overlays)
PREREGISTRATION_v51.md  c57bd85d9dc52da50fd600c95482050852a9480a305e463611825948f7b0cca5
PREREGISTRATION_v52.md  0101fb2f68ff08ced19821d0262ce556653825c363b2b9ce21bb8b19bc30a122
PREREGISTRATION_v53.md  c8ed1d96884525cf07874e80f6cd6b925b30c30cd81094d7fcd4c9b52d11ffd8
scripts/struct15.py  a162ce2a0eb39525ce7e2fb96ecf8f33aa5509a218eb6d424d18b268fbc7f6ef
scripts/daily_close.py  617eadd2fc60ae99a736e0fa8b7455e12f0c3918069f3587f4176e5b0044c88c
budget: scripts/budget_v51_53.py (event counts, squared returns, daily vol only), log data/budget_v51_53.log
v53 data to be fetched by Dave: scripts/fred_fetch_v53.py -> data/v53/raw/ (hash before reading)
v53 raw snapshot (fetched by Dave 2026-10-01 via fred_fetch_v53.py; hashes match his printout; recorded before any value was read)
data/v53/raw/BAA10Y.csv  1c77186b4991482fffb1c521eb7e010609d15bfb3e5b1e9e45c987d7c59558d6
data/v53/raw/DGS10.csv  98af25bb5f90d3dbcd181dbee47b9eb48d57813d09b7b0aed299f258c9427c8d
data/v53/raw/BAMLH0A0HYM2.csv  03c27ed65a16bc286796a6b7454ab9384f518a81554c8c7bf37d14f0dff453f6
  BAMLH0A0HYM2 (HY OAS) history starts 2023-10-02 only -> the reported HY OAS variant is not computable as specified (needs 2005); recorded, not substituted
  -> v51 run 2026-10-01: RESULT_STRUCTURE_v51.md (structure_v51.py 1.0) CHoCH FAIL, BOS FAIL
  -> v52 run 2026-10-01: RESULT_MA_v52.md (ma_overlay_v52.py 1.0) G1 PASS G2 FAIL G3 FAIL -> NOT USEFUL; G4 PASS. Post-hoc null-DD addendum labelled.
  -> v53 run 2026-10-01: RESULT_CREDIT_v53.md (credit_v53.py 1.0) CREDIT NOT USEFUL, CORR NOT USEFUL

## Sharadar bundle (full history), downloaded by Dave 2026-10-02 via scripts/sharadar_pull.py; re-hashed 16:22 UTC, all match MANIFEST; recorded before any value was read
data/sharadar/raw/tickers.csv.zip  8ef5082177d35fd98cae18c6dc9e03350dfecb354497ceb8fcb132ff5f66eccb  (4894058 bytes)
data/sharadar/raw/stocks.csv.zip  2e42069d08125211eb8852d339c4832b46775a42c078bab59708743d79692efd  (989329325 bytes)
data/sharadar/raw/actions.csv.zip  d3c2af69385bd1484daf6b612c93db44ec2986cd7819e3eab47344ceeac8fcbc  (10599119 bytes)
data/sharadar/raw/events.csv.zip  9c605a975f9686436ac214286f1440d37497cb5556b018b39a89a2d3b40a5e81  (11524172 bytes)
data/sharadar/raw/daily.csv.zip  787a2f90b86a1b6bb05768f10ee13652a1e3cf35c2dfdadab7483527ba6d7e5f  (765333284 bytes)
data/sharadar/raw/fundamentals.csv.zip  c9496673f2b18eb5579dc6f9f8aee63df23f5269f2b1b30109a767f8af2ce4c1  (661707729 bytes)
data/sharadar/raw/sp500.csv.zip  d504d1f2012c6e204034cdf378893ad2bc1da05640e93ca37bf1703bc685245e  (287080 bytes)
data/sharadar/raw/insiders.csv.zip  a5ccc4f1f69186d05b6ea3b18f5ca618e3316a538bd5470a8a547aac518f5165  (247076369 bytes)
data/sharadar/raw/metrics.csv.zip  e9d192085aec76dc3b38b193cef71bc9114ff79da24ab32280fd81c3d0ec7d4c  (1479081 bytes)
data/sharadar/raw/descriptions.csv.zip  caf7cdf6d50734e64d8ddb2ec40841f2414708526e4f62f6a66a3c71444deb04  (18958 bytes)

## PEAD1 frozen 2026-10-02 (single-stock earnings drift)
PREREGISTRATION_PEAD1.md  527d3ce58f70aeb47397b37268279bf53cc5732e10c0ea1b675b57874424ae97
singlestock/pead_engine.py  a9a48da76af824c69879aa0c1f8e89bd3de1740ac6e558ac8ad6ba560523d300
singlestock/ss_lib.py  b6a9594e43e16af1f9701cb4f9d9e6ac28666e518db6d40eeeda64de2679cdde
budget: singlestock/budget_pead1.py (counts + squared returns, all announcements), log data/budget_pead1.log
  -> PEAD1 run 2026-10-02: RESULT_PEAD1.md FAIL (G4 PASS: gross drift real; costs eat it). Post-hoc addendum labelled.

## Batch 2 frozen 2026-10-03 (PEAD2 auction execution, PEAD3 EAR+SUE, INSIDER1 insider clusters, STRAT1 combined strategy)
PREREGISTRATION_PEAD2.md  c55ca77ca89556754f3bda358f95d92d92155be59fd6bcf39a021b428a3386e0
PREREGISTRATION_PEAD3.md  23419e48198a09522c7fbc8d59697e3056764f3ba35ffc7c9c418974de6154f5
PREREGISTRATION_INSIDER1.md  9a3c50c55dcd512e7fcee32446c91f0f720e41632a1733d7b386a905720faac9
PREREGISTRATION_STRAT1.md  e1f3bdddd308ac0fd5a4b8814265f774fe89e4e02753979ae528fff75012205d
singlestock/ss_events2.py  cf4bfa27d54c2a557f0759b6875eb52f88aef96b2eeba67c1c2e95e5d244fc13
singlestock/strat1_engine.py  9b8dccf1e1a751219dae2360ccb306a2bc107932bdfb919951cfa94110d7a2f3
budget: singlestock/budget_batch2.py, log data/budget_batch2.log
  -> batch 2 run 2026-10-03: RESULT_PEAD2 FAIL; RESULT_PEAD3 FAIL (G2 era 2005-12 only; strongest lead); RESULT_INSIDER1 FAIL; RESULT_STRAT1 FAIL

## GRAN1 frozen 2026-10-03 (granular single-stock data -> SPX500/NAS100; sealed hold-out from 2023-07)
PREREGISTRATION_GRAN1.md  67e1d50da7008d4b2397118eb1b7b0f587ba8479cfb47140c424cc5c136893fb
data/sharadar/cache/gran_daily.csv  6377d9b212bc828463648d0b68c9ffcb3a354d11295ea7fb45629fc53e33b0fa
singlestock/gran1_run.py  ed1a29d51cb7ae2c350f4a966ff5df82861c77fee5114c37ac952b03720751a1
  -> GRAN1 run 2026-10-03: RESULT_GRAN1.md H1 FAIL H2 FAIL H3 FAIL; sealed window untouched

## BATCHB frozen 2026-10-03 (B1 S&P deletions, B2 pre-earnings, B3 weekly reversal, B4 momentum; sealed hold-out)
PREREGISTRATION_BATCHB.md  b2c39827fd9d53dd6d0d0fae0963691fe04c2205387053ccc277ec37eb35627c
singlestock/batchB_engine.py  a02360b27a7e6f33a76983de7002e9478a93445f9e96d04ef5cad7641a191fc9
singlestock/batchB_select.py  b75648889a990d0cbba1079e51ffb278026f72779ad69b8557b228584599c476
  -> BATCHB run 2026-10-03: RESULT_BATCHB.md all FAIL; sealed window still untouched

## PEAD4 frozen 2026-10-03
PREREGISTRATION_PEAD4.md  d79d7c1a1ddf13535b4bdbc195a093f0beca71053b3570a01a018bde2f97ac96
  -> PEAD4 run 2026-10-03: RESULT_PEAD4.md H4a FAIL H4b FAIL (lead: drift lasts > 60 days)

## PEAD5 frozen 2026-10-03
PREREGISTRATION_PEAD5.md  6f84fda84659229262ec7c54e65c14c3bfeac0d29404dc2f830e92964589f44d

## Forward / design pre-registrations frozen 2026-10-03
PREREGISTRATION_FORWARD_PEAD3.md  adbae427ffbf8786d05149cce892935dc2698df9db862495f16a5403e6727258
PREREGISTRATION_PORT1.md  db783cb45dc6556e429d57d133ccf041ef3e22e13ea1a8b264224c2490dcfaec
PREREGISTRATION_COSTS1.md  52b098db0e4f6af6672c4669c0804db236807001e1683d029a75f7bbc451ae81
PREREGISTRATION_FORWARD_C1.md  230a8ff67d11d753f1f8a5769f259395ee4ffd1cc83bdafdcc49b5c7c0e8f4e1
singlestock/pead_forward.py  cd206172e6db90e7bb1fd55bc38716874ccfcb92e2c2a62a63223a67f643f334
scripts/c1_forward.py  2f2ad1108229669327b57f2b306ed66830d16b4a81693e2a213d4952811b8d56
PREREGISTRATION_COSTS1.1.md  1d3b8fb6ed080b3adc5959c7a92f776a069f4ceb74c909a3fda5949fa9f0f847
singlestock/costs1_sample.py  652dba870518024bbcdaa8b7b342f209d866974c5dbf2d57fd9e3fd43740c20e
data/costs1/sample.csv  b740ef3725e1dedab319f7b8f75209bd412b064a70719dde602f37d8de55d500
scripts/databento_costs1.py  67b9d02a3c95ef27d877eff887f81c724a92f51bccdac1da31f749e3c45ff0f7
RESULT_PEAD5.md  26b00306926c9d047696c60b32fa5d805c345af2733ad75b50f40a5c1ce600df
scripts/databento_costs1.py  701800b5d7153a4a70d5d056dad5c4d65a3ccb8a91baf8a209da05cf00623c6c  (fix: tolerate unavailable dataset + pull.log; before any quote read)
scripts/databento_costs1.py  3fd6f06d62a48cc6aa43611e9d7c662743ae5488dd642cc90e2150fc4e2bcc75  (fix: abort on empty key / auth errors instead of marking rows missing; no quote had been read)
singlestock/costs1_verdict.py  5507dc22e5b44704c3dea8ac3adb61a9e00adc0986f187f230b191737b0d17bb
data/costs1/measures.csv  f11ad9380edf9c67fda809c3b35e38a3279a13da77423f6450eefcbec139c1ce
RESULT_COSTS1.md  2fdcfe906d5dcc195ae572272015d10093cf08c9695f759bd832e332fb7b6f18

## PEAD6 frozen 2026-10-04
PREREGISTRATION_PEAD6.md  48272fdd4f01c87b18f17ae8c73c3ab1d66cbff1b9fa19526c9d0bb6ce455ce3
singlestock/pead6_run.py  d2135551d8d8db1a555fc56222344e967d36da9dad321e16f320bd95aa93b6d0
RESULT_PEAD6.md  01f6f7641e86d4d81a5ff92e8fdd5aa35a702303ca808d791d347b33b9045f0c
PREREGISTRATION_COSTS2.md  979f7f5a4e6a5ae78f304fa43555ad72ad264e0bf9c3dbe4313f4761c9f72de2
scripts/databento_costs2.py  80db2fc21e5fceb3dfe22872448a03c5de30fe7841a05ac18732e3b1157e38f6
singlestock/costs2_verdict.py  ce9650d3288c2b1f5e6baa02af0410aad2ffeb26514d9a4babec7df0e6c868f5
data/costs1/measures2.csv  5e5084c6a24f7a010961dafbfa228f2a8cb6e554aae791cc2eda10331ec3253f
singlestock/costs2_verdict.py  bed65b206fe8a41c87eb826a8bf69306b15cfaeabd29b57640251916bb20d230  (fix: drop 2 rows with undefined official open; first output was NaN)
RESULT_COSTS2.md  40f758792223145cbe7ba9cedac62599c929a007ddacb063af5ee988a03602b9

## PEAD7 frozen 2026-10-04
PREREGISTRATION_PEAD7.md  101b6b1152a07bd163b4db9368f0a2695e14eca599b1e0ef14b9cdb8702f84ab
singlestock/pead7_run.py  715de784fcdba9d22c1e0715967e8050ef90d71d2a31b66f40c106bbb2f4d3e4
RESULT_PEAD7.md  e2a1cd4af0ae45adaa782706598296aa79798f02e9fd8cc1698b047bc7872664
scripts/weekly_job.sh  9a6349df466b2e2f28ad23e5dc7d819a97d69f5ef838943552c2fb162672f318
scripts/fred_vix_refresh.py  19378b2b5f40b382afda8959ba0ff0b18545c513310acfb5188775c2e08e5405
scripts/com.fastbot.weeklyjob.plist  f24c497c30a8a9292de77d8b39c83dd08d93d15392ea56e88a1f71b8ca8eb4ac
scripts/install_weekly_job.sh  d7bb54a773d0841e2aa6926b84ac3df9197fa43a19b143498241f8478dcf9c2e
singlestock/pead7_posthoc_years.py  5b670374f5456092635cb4ac95b64d984b4e6f6676163ef01eea51b094a41fad  (descriptive)
RESULT_PEAD7.md  61f116fe17876808291871e27b44c42c26a897b4c2cb7c3bccc759a0552cff9a  (appendix added)
scripts/c1_forward.py  3023f1b0f37bd33cabea6e419afbd5f4ebdd2f02ae601f6f1db33d5073601e2b  (fix 2026-10-04: header written only when the ledger is empty; previously repeated on every run before the first data row; no data rows existed)

## PEAD8 frozen 2026-10-04
PREREGISTRATION_PEAD8.md  b458213e47ec3ca8474d26d1a84d89973f590b6243c98bf4dd3a79eaf185f2b9
singlestock/pead8_run.py  12d0395bd40700f952b7e12563dc93b8753db59cc5f3c38fd96b3862f554cd0c
RESULT_PEAD8.md  9fc70587a257cafa6ab6b4f2ec0c0cfd47e5d159beb7652babade0cb11685f37
PREREGISTRATION_FORWARD_PEAD3.1.md  4dab46559140deb37d36421d5cb948ce3bf0980d66d53de758a46bfef18cb136
singlestock/pead_forward.py  ee589fb581894fb3be19524eb7b85c7046fd16eeb9bc2e553e7bbcfa94b42220  (FORWARD_PEAD3.1 columns)
RESULT_AUDIT_LOOKAHEAD.md  4e9fb4107bd3e7581d0e540cc822834fce04038d369e0ac20c35e8421fa2fe9c  (audit 2026-10-04)
singlestock/audit_lookahead.py  ece8755f84e0def8011b87092e66bb4b252d9cb0ec0e8e89538db14bdbd31ed6  (audit 2026-10-04)
singlestock/pead7c_run.py  16fcccc285f6cb8abf27970c5fbd911a8ad354f343ae707add96b1c1a1971fec  (audit 2026-10-04)
singlestock/pead_forward.py  b3a2525ad054f67c183371c2abe6aaf3b5eaac51352bc1435a2c3d6984adbc20  (audit 2026-10-04)
RESULT_PEAD3.md  94ef8337327cc974f900ace712803b713cb824b8fbb39546e060ce4c4d9f3c1c  (audit 2026-10-04)
RESULT_PEAD4.md  568f9b326b26b4374cf03efe812f946265bda235daac35037b4a0e95ac5e887c  (audit 2026-10-04)
RESULT_PEAD6.md  9143f3f60843262a4b9b8593b43ebfc1f7a23cbca93ea73b8ae941a21bca439f  (audit 2026-10-04)
RESULT_PEAD7.md  9b91441f64d37ec1b09704fbd3bfb95f8f7218241adf4301722d25c20f09049a  (audit 2026-10-04)
RESULT_PEAD8.md  2825531908553b3b5414703e5b1116e024887897b66049105631cc4b1121a801  (audit 2026-10-04)
PREREGISTRATION_FORWARD_SMALLCAP1.md  2770cd3a2dd82f1b5dbdd496c5fbea06a6d14c920a1cd2294ecf1ef44576c053
REVIEW_2026-10-04.md  ce12d15143ebc2b56c479e07f62fd532cac9d4fba6925a94b5bd7753243e187d
PREREGISTRATION_BREADTH2.md  6d3f68969ef1f685e570144c42b6c83a19da2959b1d5d87d1f0bfa1c987597da
PREREGISTRATION_ADD1.md  ca59a6f6e368594804f376b342560c7831a92be89df14b71560654862f131614
singlestock/add1_run.py  97ae5b88911d7e189837fdf5f26a44d33ebc7e43cf9a33a79c8437c3ac1532d5
singlestock/breadth2_run.py  1279b41930ff1ff2f79366869d81c25238a6b1eb15a7b96c062cab264894f410
RESULT_BREADTH2.md  2c35d4bc0e9b101d333048a1130707cdc4812a9bb1d0383f6c46df328dd207e3
RESULT_ADD1.md  6e4f2b4528d02ebf13077eb47fb6ba5dd53e8a2b4c757d3e57f539d802133a34
RESULT_AUDIT_INDEX.md  87696a01f6e1e332e15a9797b20b4a1c86e2a4f84ea5c48b1d7238bc5d85f7ac
PREREGISTRATION_v41.2.md  51cb12190074400eef4ad2dfcc0c297f6afdda8ecab34f2d94d6ceb3e25f72c4
scripts/forward_forest.py  e18e8a6bd5c602e8d512994c36434aae377848e1b1048d7d7da0af9a644d1d3d  (v41.2)
singlestock/forward_breadth.py  6ef6b7514e6c8cd46f563dfe24491e3ed63bc48804baa69a6d5453d2ed198354
PREREGISTRATION_FORWARD_BREADTH1.md  6a765d0e0eb7960010321bc7110d1890a1fe01a2a373d303fcbaaecb537034cb
POLICY_RECENT_REGIME.md  ce75b93ec917be77d6b2200e9e420ee75d48393a50a062994fd4163ed3943a92
PREREGISTRATION_SPIN1.md  81bb0b715127a40d3c0cc68d589922bbda24d0ca76e027d777a245b70aad59e0
singlestock/spin1_run.py  8c32d289cf9f93fa9c36cb7ac0682e29271d6693d38859466668f407564f83a3
RESULT_SPIN1.md  7ffff8123b366b2dfa4aac0cbf18338bd97bbe916df31f778c99c1bf7cebaa06
PREREGISTRATION_IMB1.md  30687efc1f077d5effc0baeaed10dc1d72b7f39873f446da4edfdfa48c187c42
data/imb1/members.csv  eb791cb0eae1fd65b6abe66c9f09bd6c585667561c408c4293d9c78d717a8dd3
singlestock/imb1_members.py  a608e12bdbbafa0e01d2fcac946839f146be15eee34fc7eb667ecb4b4c2c1327
scripts/databento_imb1.py  7f51af8340000139d34040e1845866ddf21830e46adba093ff652cf1ac96f721
singlestock/imb1_run.py  bcbb09b4739a58c0460298f1e81c8f6b7230de9c50456b660f44f318b8e51bcc
data/imb1/days.csv  65ff65228f9918bafab58b9a0a21f1268fe827e5b143ac43b986c36d27f75554
data/imb1/symbols.csv  bef06ed9c49645e5952dd12722dedc4f37b3582d8cbe25281898da099809f466
RESULT_IMB1.md  66d652d35895fc8f14b555d804b95541dddd6a7921a116f27f1ab4330ea03c30
PREREGISTRATION_BOUNCE1.md  fbd86804ffff4e579693142219c3a01371876d7b71c3db3f77144a04575c7447
scripts/databento_imb2.py  4c90425a6ea91cde0a9ccdb35c117f3e553ccb10d2867d95450d25f031edff38
PREREGISTRATION_BOUNCE1.1.md  bfb854ab391f864b4b5dd26ac3f495ee19d5dd30582a5412aec6c5b875527635
AUDIT_ASSUMPTIONS_2026-10-07.md  5d206d46d2d82c41e3ae1cb46854d84ce8c4e63b7c32c1a25dc9c28a62de1c34
singlestock/audit_delist.py  80916eaba9eb78d635c59168ad6d9496cbb3071894c08db5ac7d04a66023674a
PREREGISTRATION_TF1.md  9662675182cd1bdee91ee95620c5a4f7dcd5b01a147830beb7fe69109cb29ca0
PREREGISTRATION_TF1.1.md  0ab7d54fcd77f7a5788d03134fca3392bbf8b906711793da9b0c56a06db23caf
scripts/tf1_run.py  b824eb582f35ea88a7dbf2e66b1f44b68ec5265f91416b1fc344041e92fb28e6  (mechanical: chunked runs per instrument/part/half; computation unchanged; 4h already run whole)
RESULT_TF1_partial.md  8f6fa753b4c410a537162b0b3456a283c8c26ce0f7b1fd127a41b04b413c63ec
PREREGISTRATION_PAIRS1.md  579e8e63a6c61558e7cd67bfa69409a83a08b7b75d276e642144cc0168f86003
scripts/pairs1_run.py  6bc5699fb6f28c80ac17159504d30376b89b5b818c4d77b2f6c26538768b0f78
RESULT_PAIRS1.md  1e3b69134b8e62f23e7a916dc43df6f9a60548c0017d0ff48ea621dea8b0079e
singlestock/bounce1_run.py  77582a07588ecf89ac0ab2afddab726be4b1b566546740a992f4b23b1e5d9220
data/imb1/spy_path.csv  d4b9410fc38ae0ab20eebd7f0457f4baadf4d800be94648e2affb7df77a72f90
scripts/tf1_run.py  4af55010227325f34ea74615f628357913efef544a09fbea204c0f4efae3964b  (mechanical: pattern list split into N groups, e.g. 0of4; halves identical to before; computation unchanged)
RESULT_BOUNCE1.md  fd4425e796ad91a6d2594f3e65c5ae513cfe8458fe29d35dba0ae8708d040e75
RESULT_TF1.md  6532f7d8f4ee71e3e94e1bb24cc873909e72f4bf58161d68e4d418dedd19d6c9
PREREGISTRATION_PRE1.md  f6aff317268835d557e9ad45554c906ee7ee28de10ab0b3978404a728e8590a8
singlestock/pre1_run.py  c2d413bf96aa5bf5092dbd5de437be9c5f7c19e786dcdcaa8fe0a29100746f99
PREREGISTRATION_IMB2.md  e6344bc1124aca1e81547c4176644071ca9fc8b5098e1743a2efd04fdb5aad80
scripts/databento_imb2b.py  f99d0b2850b907966e7b7ff4f7b471d5d28651a32fb5a9db1fca28f6eddb2148
RESULT_PRE1.md  3a2f70a3ab83b41d0269ee3d74c4be5365cf8dfe6cdf173ff7681ce57b432b97
DATA_INVENTORY_2026-10-08.md  91f748a2fecac8dc9a21f2fd6ca192b64c7f1f836f05bccbfc89b73f6a717f20
PREREGISTRATION_TSMOM1.md  97df17b7a1882092b4fe98928a4336f09da1e4f63d7ac075664e7fda0aefc2bc
scripts/tsmom1_run.py  14c5b2237397f682d08a741e8ab7c0b4cae87b124087276bfaaaaed7a1f37021
PREREGISTRATION_BUYBACK1.md  624801b66616d1fa58c2343786de2d1edde5313db3c256d5b68d79725c5d4699
singlestock/buyback1_run.py  903fc244beb378482f29343d1653809f6e9000e6f6d8f8bff364a958eb98fa18
PREREGISTRATION_OILGOLD_BATCH.md  182b6e9f88835a9cb10485dcbfdb2946dfc15f1e65664535b5669f0636198f94
scripts/eia_fred_gld_pull.py  19823ca0724a250306d8ce873e59862528158b724742fb863fa2fd1270fd0200
scripts/pull_oilgold.sh  8179f2b2dd631f19e4e3ff3a0c906e6b35b9c22966db86eb5d5e318d271d54d6
RESULT_TSMOM1_BUYBACK1.md  616d40187c1687bbde5c5c4aef69e4c86fca04c398204f135337e833e84fa477
scripts/databento_imb2b.py  a31bd776fd873e3fb11b9e311129623298a3f57aad1b851afc87d47ff276be45  (fix: ts_recv is the DataFrame index; empty output files treated as new; no data had been written)
OBJECTIONS_2026-10-09.md  ae7924087caa652465108927f58dc52f9dd2bfe6eeb5ca3aecc003bfdd0ba518
PREREGISTRATION_SESSION1.md  11bb4e0a1ea101d9c840f4b8bd3e9a802ca6761592664fa41a44efb8619d416a  (frozen before any SESSION1/REGIME1 number)
PREREGISTRATION_REGIME1.md  b3a1b70b20e44ccc761132257c788c24ef6eb76e7fdf4ad281ec8dccb9d52c69  (frozen before any SESSION1/REGIME1 number)
scripts/session1_run.py  f8c783c49b4888a447a6a4fd81b8f747a1f2b0eb9f50e3dfe1a59af4349c6c1e  (SESSION1 harness, frozen before run)
scripts/regime1_run.py  90ff0a830fff717e40591068cf555cef56785d82f8da4a8572fdc5cc7c66e101  (REGIME1 harness, frozen before run)
fastbot/RESULT_SESSION1_REGIME1.md  8c6d68bc46f860b9b6b3aec87cb21eb7e96e556c9ede91fcd694569bd795ace0
fastbot/OBJECTIONS_2026-10-09.md  b68339a4ee3b4dd0833e981253003b0002edb52cdea5de0d62a5b5084b3b46b6  (updated: SESSION1/REGIME1 answered)
PREREGISTRATION_REGIME2.md  885697581f4e4ecb7091519e28b90de548e2d194ac7553816ab80213a8047842  (frozen before any REGIME2 number)
scripts/regime2_run.py  798a2edf0249702e358dc3b4885f130359a962c307ae7d72b0e39cd48e961e17  (REGIME2 harness, frozen before run)
fastbot/RESULT_REGIME2.md  5a11df3a449df57653c9cf9c26560658399341f7ac85c6f9772c74debf59942e
fastbot/OBJECTIONS_2026-10-09.md  17820af2aaca50907612168b1423654672512d659fbde73279987f80a5ccd26b  (updated: REGIME2)
DEFINITION_CYCLES1.md  fa06a3ff268a75f2bf19fafed1cc115da665a942821a9aff7b5672529b162436  (CYCLES1, frozen before dating; shiller = datasets/s-and-p-500 GitHub mirror, fetched 2026-10-09)
data/cycles/shiller_monthly.csv  3a45dffabc414afc298c12159abc84c2875f88175ff3d4473ef7417e725ecac6  (CYCLES1, frozen before dating; shiller = datasets/s-and-p-500 GitHub mirror, fetched 2026-10-09)
cycles/cycles1_run.py  f19c0ffb906c2e105e69a5bc222559602b32d224419039d7b332e25152c19d4a  (CYCLES1 harness, frozen before run)
cycles/cycles1_run.py  1528c4571d412b86bae05ab6f21cea214a48a7e32ba5074ddae88f755e2b35fe  (mechanical: self-test expected bear confirm index corrected 5->4 (95 <= 0.8*120); no phase dated before this)
fastbot/RESULT_CYCLES1.md  b3d51a303a3c592a254c02f80c8a7b15eff49789b7edaf9517e4b3b734e6181c
fastbot/cycles/fred_cycles_pull.py  00c728bbbbe2b4eb1f522e77215022ace91cfb3cca505b69b9910453bf34cf62
DEFINITION_CYCLES1.1.md  652048d85133d9322dbea618c7e5f4b91bb3224008498f68d623de90a50f7734  (frozen before computation)
PREREGISTRATION_CYCLES2.md  3770e1332bf18875e197dd435568b58ecfa5183c7fa160eb5f5129f1f2a61141  (frozen before computation)
cycles/cycles2_run.py  95f0cb84c9e6bd5d3bef714468d424db4968cc5b64ef035cf714bc096458b6a9  (CYCLES1.1 + CYCLES2 harness, frozen before run)
fastbot/HAYSTACK_95PCT.md  595715fed0dcd811bfa87dc840a05db6df477decbb046a0f4346263cdbc5f0d5
fastbot/RESULT_CYCLES2_S.md  42cb07f1dd73f1c9015434eca2d3d678281760a815c054fefc2444ed0e62c97f
fastbot/RESEARCH_ECOLOGY_2026-10-09.md  bfc5e2f18d218e519e2172336555275673c7c919fe16211347a0fcdc8e218fcb
youtube/SERIES_STANDING_CARDS.md  d36db3c2deca71c354dc2e574f8456a2dfa76e330718fa5cc1b6a375a9ad7b5a
youtube/course1/PREREGISTRATION_COURSE1.md  4561792c30f69e6cc62dce3026332231a34c3d71ad8c91c2a81855d6e1e5e412  (COURSE1, frozen before any classification)
youtube/course1/COURSE1_FRAME.csv  00a99bd39b3d7b43a7bb343c95a0637d219ddb583d6e54c645b1610cc75de895  (COURSE1, frozen before any classification)
youtube/course1/RESULT_COURSE1.md  98d03bedc79975de759e1777f8fe63004cebffeaac26ef05cd8b32c2b8b0ef8c
youtube/course1/COURSE1_classified.csv  b9d164d3df609daa205c47ae733287520f04d53e4de55797531be2641dd8fc51
youtube/course1/COURSE1_classified_partial.csv  b154712f1ae88979183e4372e2a2a8fdc0fbdde5ed4d2db3b07904ed62aaf2cc
youtube/course1/LIVE_EVIDENCE.md  b2922c220e13458347adcdc4ed0d4c6078efafdbde58acfc63ae0c0a7c8d9b4e
PREREGISTRATION_PROBE1.md  1320a760421c6029101d44fc85dd3cc5683e3aeb6366f87125aeea282c106eb6  (frozen before any PROBE1 number)
scripts/probe1_run.py  3397d812a576e6382fe8614e80c605fdd2e32e5133f919ce9d203cf57184d87a  (PROBE1 harness, frozen before run)
fastbot/RESULT_PROBE1.md  e4eef3d956c4b7e1fd1297639241f50e5eeb8a2c29367bed558b6bcbb0e0b7f0
fastbot/PREREGISTRATION_UNGER_BATCH.md  ce14205ed8219efd19f5190ab53dcfdb62dbb4f8fcda5bf59a2c1eb0c91f3716  (frozen before any number: PROBE1-OIL, GOLDTREND1, CONTEXT1, MULTI1, ROTATE1, TURBO1)
PREREGISTRATION_VIXIMP1.md  649658dbe0d0f41b1274998de025ccc65008968fcc8ea4f2fb71a36d5de94a49  (frozen before any number)
scripts/viximp1_run.py  fb7a2a170f1914e1ffb893c8b94c79ff37c922cc4f45212cba76d0a5a769b460  (VIXIMP1 harness, frozen before run)
fastbot/RESULT_VIXIMP1.md  199a8a5c53ab3030d23bfc806b255049527e12c9bb23a3f37c1b586f47798540
fastbot/data/cycles/fred/AAA.csv  a363bb0cac42972adbfcc521ce574f20824ab4bf43ee8d90c0fe8867f7ece3eb
fastbot/data/cycles/fred/BAA.csv  a19a4e7230f5dbf42ad2b056b7b13a8cee53307f1ae893fb073d829a6e0f8f1c
fastbot/data/cycles/fred/CPIAUCSL.csv  4c2036481c712dff551cecbbdbacc745d75b8d06fc348fdd2e3c0fedfeeac716
fastbot/data/cycles/fred/FEDFUNDS.csv  1febfbfd22ef4d1e354d412ab224009f9df4214fd880e60e3b1d3d6f22798573
fastbot/data/cycles/fred/GS10.csv  14101ef859fbbacf0f0be00bc7a7ad70eea56b640a7a33b41a19982519639c60
fastbot/data/cycles/fred/ICSA.csv  14767781b3dd5edf0041f34dd1ae874e9688ebea5701e28820f90410e56f992c
fastbot/data/cycles/fred/INDPRO.csv  ba831a4ed739f44bc9ce48ef3153db985ca335401f2eb602c5f629b5d10ca3ad
fastbot/data/cycles/fred/M2SL.csv  fd05e0260190ab728067e48ea23492438bd88df341c89c254c53059b4160cf3c
fastbot/data/cycles/fred/NFCI.csv  fb7d33dfd43351e89096410ad92e095b9b44eae9c14daccc12942dede6d44b46
fastbot/data/cycles/fred/PAYEMS.csv  83c7c12c488b80d76d650f590d602a4553426a782ca43a9b2fc3040d95c23974
fastbot/data/cycles/fred/PERMIT.csv  b483df51650c25f468003db2601048b13a7c97ebfcbc03270890238ba1eed688
fastbot/data/cycles/fred/TB3MS.csv  e521dc1d6f381a29e7899d3309b28de097b470be950f00db2545cf4637b62fb1
fastbot/data/cycles/fred/UMCSENT.csv  ed53e3df4e388af2e8621ffea7e4115a52e21569a6f303c94b719e6309c0373f
fastbot/data/cycles/fred/UNRATE.csv  0de63da6480014b798bfb4a1c830e0505bea205ec5718da76c934b45ee1704bf
fastbot/data/cycles/fred/USREC.csv  21ac8e5cd4882d9af6fb0ea60c508ef64bb36cd392ab24e2c2cbf33863020d65
fastbot/data/cycles/fred/WTISPLC.csv  0f917359164123db1598402e455c1694e8c639fe58b9cc8e66ba03bcc3d5f4ef
fastbot/RESULT_CYCLES2_F.md  61ab20348012c73dbe6a66615faa6e8413d67303d7b4efbf3f36f516834318fc
PREREGISTRATION_v59.md  d1339ab1ec7daee4d16fed9b211609b4a07a53d457429a4c9a13eb137e815dd1  (v59, frozen before any v59 data pulled)
scripts/fred_v59_pull.py  26c34ece86a6db31f3da5158637c4691d2c6ece87ea0bdf9ec8792a9ea9847a7  (v59, frozen before any v59 data pulled)
scripts/probe1_oil.py  f27f3736dcbe6127297957444f56452488bf6ecb69b836924dd1c2c13fd49378  (mechanical wrapper: PROBE1 on WTI/Brent + batch clean-day rule; frozen before run)
fastbot/RESULT_PROBE1_OIL.md  4c3061e383f2e742cce8cb8edaf0e02da29cda9879c3dee2e86f797e88721fc9
scripts/imb2_run.py  8b41afcd21a55ab28c59cb0f02cc90ca3e9c310db6d53adcb540fb06d87bb85b  (IMB2 analysis harness, frozen before run)
fastbot/RESULT_IMB2.md  a65440fadf2655099a3d51f01647ee756e11305229cdb3bbda8d3ffeb1882e8a
fastbot/scripts/imb2_posthoc.py  77f1f449074d67dd6e3db7cbcad49b0a1ab5b05520fe861457503485f536ec94
fastbot/data/imb1/imb2_msgs.csv  a4cf85e423e9ee404bbe800dd260b54bffd65ba00c05927ca1ea24c01d6ac18a
fastbot/data/imb1/imb2_px.csv  cb1de58c74cfd20de150e764f4600b0af5e74d3e6392f00191f7fd83a697288d
scripts/oilgold_run.py  84a58e225b84506bd653ac32c1d19a76bedbad6ed754e5989dc60477240a9967  (OILGOLD harness: OILCARRY1, EIA1, GOLDRY1; frozen before run)
fastbot/data/run_tsmom2a.log  c0257f141297d1f9475d6190708e2a31546f105df555065d8dc14ddeff34d01d
fastbot/data/run_tsmom2b.log  d938df7e5ec6df7bde672bfbefe4692532cbd5906e9cdf9f7a16be6f4704d736
fastbot/data/oil/crude_stocks_exspr.csv  bba2fa5424695c70170ed8106d472753377a434edc4af3dae2b5c01a3e081efd
fastbot/data/oil/wti_f1.csv  a2b8d8a70fc2180f8ef3c0acf7897e3a538ce2aa94d2708a4e11b78e36c3446e
fastbot/data/oil/wti_f2.csv  26a9e9db2a3bb640814829a5e8ebcf4c549cd4ebcb133d997bffae322311521d
fastbot/data/oil/wti_f3.csv  cc19e5b4c07cf93bc20d063230917ffd22af40dcda4ac84f7e1cbabe756a6e3e
fastbot/data/oil/wti_f4.csv  e45c4836b9f1e2545b2a526f93c75c95498affffe5d1d5caeb44e41e57dbf69b
fastbot/data/gold/DFII10.csv  3b21d0a20952a81b09da478a5215bd627e4e4a6fd2c16f27f02a35ede13283d6
scripts/oilcarry1_rollfix.py  11cbc3393c0077f6851244f831339c8ac702807975d9b6cd68999f8d9a0bf0b5  (mechanical roll-day fix written after the registered OILCARRY1 run; descriptive companion)
fastbot/RESULT_OILGOLD_BATCH.md  4b9e9b5bd880a9c3a2acb37629712c6c7c12ddf0c051a494a75ebeb460f91da3
fastbot/data/run_oilcarry1.log  efee3600c72dc13edbf405a33c6d5a4b3d959093773d7bf23f88365fd44d6947
fastbot/data/run_oilcarry1_rollfix.log  89d70642d174736c68cb5e645c233c49784d2b6af3fa7dba6ecb12142528f14e
fastbot/data/run_eia1.log  bde7fcbd1198ba9efa7fd8e73c79296930549f63f442f789cd5ff06fd1f1fdca
fastbot/data/run_goldry1.log  28122958cc99d31b4173422d1f74c4f623620f64fa3dbe3be304923e6342c33d
scripts/tl_build4.py  12d01e7012296b6ab0b6a4b006af20d6a6bc1c017f04c4e8591ba90d21f78d14  (v59 harness, frozen before any v59 build; spec table defines 12 events + 8 states = 20 features, the summary line's '9 states, 21' is a typo)
scripts/v59_build.py  353f6732e52a74185e3535a6cc9b51b8970a3c0d895c7dd6a3e03641737a3747  (v59 harness, frozen before any v59 build; spec table defines 12 events + 8 states = 20 features, the summary line's '9 states, 21' is a typo)
scripts/macro_v59.py  a9ea7ff8c3dea9b3ca173fc319b2a13c471e96f926e78ff926e7c72a541b5017  (v59 harness, frozen before any v59 build; spec table defines 12 events + 8 states = 20 features, the summary line's '9 states, 21' is a typo)
fastbot/data/v59/fred/DAAA.csv  482260e88898065666411953bd03413d9e365c1d800f79a016b04c88b2501937
fastbot/data/v59/fred/DBAA.csv  36b7ce4d80c6f7277113c76cf0d5993bf8114f20ba83c6a1c516be76d9793a08
fastbot/data/v59/fred/DCOILWTICO.csv  09cc788012610db025e00d9eeb39e849e32bb77792ce82d76d9a3840870613b2
fastbot/data/v59/fred/DFF.csv  1d9e4fea4c432e581356161528118f799a04cbb2dca215b2f280947faa96e368
fastbot/data/v59/fred/ICSA.csv  14767781b3dd5edf0041f34dd1ae874e9688ebea5701e28820f90410e56f992c
fastbot/data/v59/fred/NFCI.csv  fb7d33dfd43351e89096410ad92e095b9b44eae9c14daccc12942dede6d44b46
fastbot/data/v59/fred/T10Y3M.csv  86190403eb0f26cca60136513bf6c7d07798d62c50b8bbe1ec3cf5eb69d5a527
fastbot/data/us2000usd_bid_5m.csv  72de376225a62648542ee33ea46ddc25028958ea07205c00268297d8573a9cc9
fastbot/data/us2000usd_ask_5m.csv  0a8853901c85b756fd34f3758a919496b20c454e7721c208b21543f600aae10c

## v59 — run 2026-10-11 (once). Verdict FAIL (G1, G2). Result: RESULT_v59.md
fastbot/RESULT_v59.md  3e2600e5e219e35587e64cb7de0ff53e28568103118047a6654206c94e4a833d
fastbot/data/v59/spx500usd.npz  34a2f372413ae8be9cf3adc1484e26ac233f9b1b35393c0bd5d327c8df957253
fastbot/data/v59/us2000usd.npz  e5ed68fb1a5e1058123201b3a0a156505e5a51c8b1dc489f0f3e0a76d82fb4d9
fastbot/data/v59/pred_aug_spx500usd.npy  a27f3acae5ce47d9caca77be49cab221601769bc0e8dec8d90b4b35f336f0689
fastbot/data/v59/pred_aug_us2000usd.npy  b8990e2812c80464ccc6a9fd6e5e2838ab5d76aeaf01ca7e3bd10057d6dbf0dd
fastbot/data/v59/pred_base_spx500usd.npy  3f40a91f3dadc9692f0d46ca287c80f70bd98757c001a5e0271d63229c9edb39
fastbot/data/v59/pred_base_us2000usd.npy  a93cc690df29d71f5a0e189dad205fbf3b47ce81ad91eb35dde4a60ab20bae01
fastbot/data/v59/run_v59_test.log  031be8b7e3b0a0724719b6dbeeb8f4f4b0aa55bc2d24218ab2ce48108c650706

## UNGER batch sections 2-6 harness — frozen 2026-10-11 before any run
fastbot/scripts/unger_run.py  ab415b4ce08bd096bafc023c221b1a254563e9e58a1cbca1cfcd8c1450aa0660
  Mechanical readings, logged before running:
  - CONTEXT1: a filter that can't be computed yet (start of history) counts as OFF (flat). F6 closes a position that is against the trend at the day's first bar.
  - MULTI1: missing market days count as 0 return, and the portfolio averages the systems that have started. Vol-target rebalancing is not charged.
  - ROTATE1: switch cost = 1/4 × weight × |position| × half the open spread, for each system entering or leaving. Rotation starts once all 12 have a full lookback.
  - WTI/Brent spreads before 2012 are also zero in the source, so they get the same 2012–14 median imputation as the indices (oil appears in MULTI1's reported-only portfolio).
  - TURBO1: the same seed-0 paths are used for every setting; contests continue the same random stream.

## UNGER BATCH sections 2-6 (GOLDTREND1, CONTEXT1, MULTI1, ROTATE1, TURBO1): harness frozen 2026-10-11 BEFORE any run
fastbot/scripts/unger_batch.py  e31a29d23112e77cddf52782924afa23c2fbc5482a77ab981e337111cc393cf9
  Self-test passes. It checks: probe_lv reproduces probe1_run.probe(); planted paths for the daily engine, mean reversion, channel, breakout, vol targeting and weekly levels.
  Mechanical readings of the spec are listed in the script docstring (S2 re-entry at the exit open, F6 closes positions against the allowed direction, warm-up = OFF, oil spread imputation 2013-15 reported-only, ROTATE switch cost).
  Run in the session workspace on staged copies of the device data. The inputs are identical to these on-device shas:
  data/v51/xauusd_15m.npz 0e164fa1…  spx500usd 8ffb69de…  nas100usd 27336b46…  uk100gbp 8d5bda8e…  wticousd a322458b…  bcousd 7788f5e6…  data/policy_rates.csv 89302fb9…

## GLDFLOW1 harness frozen 2026-10-11, before any GLD holdings history is on disk
fastbot/scripts/gldflow1_run.py  cf50e9e071273ba67ea1e056953600fd020d5bdf4f0e457e1d64a6ff367712be
  data/gold/GLD_US_archive_EN.csv (pulled 2026-10-10) is NOT the history: it is a 120-page PDF bar list of the trust's vault as of 09-Oct-2026 (5,944 bars, 2,411,823 oz fine). Unusable; kept as is.
  Input expected: data/gold/GLD_history.(csv|xlsx), the SPDR historical archive exported from spdrgoldshares.com by Dave.
  Mechanical additions fixed now (reported, not gated): a Thursday-holdings variant (strictly known before Friday 16:00) and a quintile gap. The self-test plants a flow effect and checks the null.

## OILIMP1 -- frozen 2026-10-11 before any OILIMP1 number
fastbot/PREREGISTRATION_OILIMP1.md  923437deab315a8f7f0eea6b12a8a8955ea7d09d1bdabcefa61af1353d29533f
fastbot/scripts/oilimp1_run.py  54fa0e18ab43e7d3ccb59d0ec1227f092b3cbdeb338e3ceefa3c011070687518  (self-test reproduces the logged roll-fixed OILCARRY1 Sharpe +0.54)
fastbot/scripts/forward_oilcarry.py  9d18c9ce4cc110763382511afa28920ec05a715ac88a7236573d77ea0434dc03  (stdlib; self-test incl. EWMA = pandas; planted append-only ledger check)
  inputs: data/oil/wti_f1.csv a2b8d8a7…  wti_f2.csv 26a9e9db…  wti_f3.csv cc19e5b4…  data/v51/wticousd_15m.npz a322458b…
  main run in the session workspace on staged copies of these files; 'oos' waits for forward_oilcarry.py --seed on the Mac.

## FORWARD_IMB2 -- frozen 2026-10-11 before the first forward day (2026-10-12)
fastbot/PREREGISTRATION_FORWARD_IMB2.md  bba7f3d414552577b63e4216245857314632734cfc7810ef496655feccfdeda5
fastbot/scripts/forward_imb2.py  0058581aabd3fb5a0713bfdc25eed5a548a3b674e08f1769f62dbef86a008cdf
  Self-test on the device passes. It reproduces IMB2's primary from imb2_msgs.csv / imb2_px.csv (n 487, +1.313 bp, t 3.153), and planted CSV parses pass.
  Membership is frozen at members.csv 2026-09-30. Cost guard: $1/day.

## forward_tick.sh steps 8-9 added 2026-10-11 (NON-FATAL, same pattern as step 7): FORWARD_IMB2 and the OILIMP1 forward record

## Results logged 2026-10-11 (UNGER batch 2-6, OILIMP1 main)
fastbot/RESULT_OILIMP1.md  b8ba670ea2f9fa13911f703925192e552cfd5f2449ebdcb6fc9ef4b50e577e14
fastbot/RESULT_UNGER_BATCH.md  260f1aa12e8b8813b438c2eb4d298d138b9bd7ed0d051d508ed1a0da531e630a
fastbot/data/run_oilimp1.log  166c4eb90d862a9edcbfeb240125ce8257c824186bb2b1991b835cac78a6f4df
fastbot/data/unger/run_context.log  848ba724749f58e50d1d49766b26721a0fba7e413f69080fa1738a03cf0202fa
fastbot/data/unger/run_goldtrend.log  26076c3b9c10357807b079f454bc3f2cb277aad2e6da034a14dbc64ed014cdc8
fastbot/data/unger/run_multi.log  866dccb1ff922344c1b5c8f64a4b7ea5e38d5fe84313ec27575291341db7f469
fastbot/data/unger/run_rotate.log  274440be1153d7a8c4419051bc0cf91ee9c95e5fc9fc5558fc8f5fed1b80a28a
fastbot/data/unger/run_turbo.log  e2e537d55d752175df004272339b13f78d0007709a285fd8bd771ff5b75f0c49

## UNGER2 -- pre-registered and frozen 2026-10-11, before any UNGER2 number (harness to be frozen separately before the first run)
fastbot/PREREGISTRATION_UNGER2.md  ead637125fb9c3eb19bb2bb8ef51d479e466193e326b934cffb92f377ce972e4
fastbot/scripts/fetch_unger2_futures.py  e0e975b69bb140222d109d5ea41bd9e6b963774e237ed5bea917dd2079d30f5c  (mechanical copy of flows/fetch_futures.py: CL.v.0 + GC.v.0 1m, 2010-06-07 -> 2026-10-01; prints the cost and downloads only with --confirm)

## UNGER2 harness frozen 2026-10-12 BEFORE any run
fastbot/scripts/unger2_run.py  afaa7aef009e096ece03416c95f46a0f4ab78490b228cad330c42ece79f1a2af  (self-test: 8 planted checks pass; mechanical readings in its docstring)
fastbot/scripts/unger2_build.py  5854c6a364bc3d0d31352c4e6111238730eff1452dd5effbf546945ad3e0431d  (1m -> 15m futures; DAX 5m mid + spread. Mechanical fix before any use: .copy() on a read-only numpy array)
  Databento pull 2026-10-11 by Dave: cost $41.25 (futures.meta.json); all 34 yearly files match their meta shas in the session workspace.
  Built in the session workspace (the VM's 180 s call limit kills long jobs):
    data/unger2/CL_15m.npz 91f6bb05… (385,138 bars, 196 roll buckets)  GC_15m.npz 515b7b6f… (384,954 bars, 81 roll buckets)  de30_5m.npz bc97a50b… (1,063,488 bars)

## UNGER2 results logged 2026-10-12 (A, B, C, D, F each run once; 0 of 4 pass on either route)
fastbot/RESULT_UNGER2.md  22d4b7ecec0fdb6e68a41dd084f0232e772ba46a92895567ca887ddd9f3c73af
fastbot/data/unger2/run_unger2_A.log  dd7c70688eaa397343233030a525661660362457f24a75fe8b0260d814ec481b
fastbot/data/unger2/run_unger2_B.log  fa5388a7a19da7c8d98417b3eadc4d9089a51ce37e3c900644155abe12ea7a35
fastbot/data/unger2/run_unger2_C.log  0d28400b4cb054bbff9d570cf5ed3578737e1aba69acebb80bd552c5ee0634a6
fastbot/data/unger2/run_unger2_D.log  42b0bab05222fd30b719c87c84cf5475f5ff22dbf0845673d03344c734f3349d
fastbot/data/unger2/run_unger2_F.log  c00ba1407ed39b75dfa0c819619823fa35c42a69aa1d129509151e8ea226cf65
fastbot/data/unger2/CL_15m.npz  91f6bb056970064adc902c53c50406d4086d97c4d5bbc2d26ec905d629865a99
fastbot/data/unger2/GC_15m.npz  515b7b6f25a755be32d48e22284eb596df05b24ff2906b7c930fcb3a1df16e8c
  data/unger2/de30_5m.npz bc97a50b… kept in the session workspace (51 MB, over the commit limit); rebuild with unger2_build.py dax

## UNGER2 A replication (TradingView, 2026-10-12)
fastbot/RESULT_UNGER2.md  df00c0405ca2b1b4109123ea2dcb6597572743da8e6d23b36075d5b9c94e42f3
fastbot/data/unger2/tv_trades_ungerdax1.csv  243fe092421862cc849850227e073c414a48093b995cd4e48bf873e324bbfbda
fastbot/pine/ungerdax1.pine  8288e5f0abab2a2e03b38ebd77e4d38d9a878988dadf61e6fc9b867e54be01b8

## ORBCORE1, LIFECYCLE1, FUTPORT1 pre-registered + INCUBATOR spec, frozen 2026-10-12 before any number or pull
fastbot/PREREGISTRATION_ORBCORE1.md  66c0aca9d467bf001150558fc5b63b724c32155cd06b42131ec4661b130f1050
fastbot/PREREGISTRATION_LIFECYCLE1.md  74ca3c9f74decdfeb17ca29a48f869820498202db0fb2212809d367f65d01394
fastbot/PREREGISTRATION_FUTPORT1.md  764490027abe2ef51bef493808dfd701309b0c87904a88f054e082110f2363c6
fastbot/SPEC_INCUBATOR.md  0dff4212cc50d75ec249115aa743a7c1582f76fd3e9c8e9436e4b8353f1705b8
fastbot/scripts/fetch_futport1.py  0c0cb00157342317247bb5364123973a7d4457ec7121d95c1d52b04cf5fdac31
  fetch_futport1.py self-test passes; it prints the cost first and downloads only with --confirm (cap $25).

## ORBCORE1 + LIFECYCLE1 harnesses and the DAX forward recorder, frozen 2026-10-12 BEFORE any run
fastbot/scripts/orbcore1_run.py  7ff171d25eff122c92c2609fbcba7243ca636530c082662436e41893cc06e1aa  (4 planted self-tests pass)
fastbot/scripts/forward_orbcore_dax.py  f7ede2b8e346780092b276ad7a78cae0029981863b2a1d4fcf3fa28085124a80  (stdlib; 2 planted self-tests pass on the device; ledger data/forward_orbcore_dax.csv from 2026-10-13)
fastbot/scripts/lifecycle1_run.py  149e787ad853e6ace4a26961551a63a62f65a09c05e947b3558c409cd2e184e5  (4 self-tests pass; library builds exactly 48 systems; names and date spans checked before any statistic)
  forward_tick.sh step 10 added (NON-FATAL): forward_orbcore_dax.py
  MECHANICAL FIX (before any statistic was seen; only per-market trade counts were printed while diagnosing a crash):
  the first run attempt crashed on an empty trade frame. AU200 has no bars at 09:00-10:00 Sydney on this CFD, because OANDA's AU200 quotes from 09:50,
  so its range cannot form (0 of 5,495 days). Per the spec's literal G3 it counts as NOT positive, and it is absent from the pool.
  fastbot/scripts/orbcore1_run.py  75dfd73230ad36f8e1fb43e2116cc17bcd4810505f21c664e4343a9c6dd0013d  (replaces 7ff171d2…; the rule logic is unchanged)

## ORBCORE1 FAIL + LIFECYCLE1 FAIL, results logged 2026-10-12 (each run once)
fastbot/RESULT_ORBCORE1_LIFECYCLE1.md  6770ac712340b6bf3c87398d70efdf18297dccee97290b85422ae37a2dec91da
fastbot/data/orbcore1/run_orbcore1.log  83778d0e81a8119d50017d294b4d0ae3551cc83945b2de3ca7028f3c8e41aaf0
fastbot/data/orbcore1/orbcore1_trades.csv  a23bfc01cd9f9eed5907a61f24b67b1b323d6c30449a2843f6c6846c96c1fd9b
fastbot/data/lifecycle1/run_lifecycle1.log  5484210bec7171581fccc95601d5fa7bfcb3f47494c0325665282d095edc74d1
fastbot/data/lifecycle1/lifecycle1_systems.csv  fc153af98ad8f4bbeb8047abb3cc9c17393e0f136b9cc4094dddb9e250a34c15

## FUTPORT1 data pull, mechanical (2026-10-12)
  First --confirm run: 45 of 58 files downloaded. ZC.c.0 timed out at curl's 900 s limit with 383,418 bytes (ending 2023-08-11).
  That partial file was moved to data/futport1/_to_delete/ (not used). 13 files were still missing (ZC c0+c1, ZS, ZW, ZL, ZM, LE, HE).
  fastbot/scripts/fetch_futport1.py v1.1  0542c5b928ace99fdf3bc9c27645133fc51b43b58694d1ca0c6a6ca7cbfa4107  (per-year requests, 3 retries each, finished parts kept; no change to symbols, dates or schema)

## FUTPORT1 data complete + harness frozen 2026-10-12 BEFORE the run
  The second --confirm (v1.1) completed: 58 files, futport1.meta.json total cost $2.60, every file's sha matches its meta entry (checked on the device and in the session workspace).
  The partial ZC_c_0 remains in data/futport1/_to_delete (unused).
fastbot/scripts/futport1_run.py  6b28c76179f7e33bae4eed3638d55d31d3c7d24fc12a8e54272b9f3066409ed2  (5 self-tests pass; mechanical readings in its docstring: weekend stubs dropped, c.0/c.1 inner join, timing)

## FUTPORT1 FAIL, result logged 2026-10-12 (run once)
fastbot/RESULT_FUTPORT1.md  c68b0b2f5ed0534c28653484a873057926415d718e69fcb1766f507a67c6e6bc
fastbot/data/futport1/run_futport1.log  f2a4a05ef8c03873f98c0e27d5d3634a85850c4562dde78403b57bc619effb4d
fastbot/data/futport1/futport1_daily.csv  a481ef073e919f51ed537742dff521bad2dc19a708e85fe355cf77ad020a709a

## CARRY2, FUTMICRO1, FORWARD_BATCH2 pre-registered and frozen 2026-10-12, before any number
fastbot/PREREGISTRATION_CARRY2.md  dddef3284f5fd80e535e165811662ac2c82d7c06f592e501459d192e36b846c1
fastbot/PREREGISTRATION_FUTMICRO1.md  ae167b336fc79f42eb88ac117310038b6c6a379a38f6e8326554d26ac5958ab5
fastbot/PREREGISTRATION_FORWARD_BATCH2.md  65d539aa8303972316d182e91b757977f0f2d990755d91e25d3e571f7acb89fa
  CARRY2 and FUTMICRO1 use only data on disk (data/futport1). FORWARD_BATCH2's recorder (forward_trend1.py) is to be frozen before its first tick.

## CARRY2 + FUTMICRO1 harnesses frozen 2026-10-12 BEFORE any run
fastbot/scripts/carry2_run.py  3213af62a87371b026ea36a0219227d4453c3cfdd17d28f65bffbf794b3350a3  (3 self-tests pass. One planted-test expectation was corrected before freezing: the shallower-contango leg hits the 4x cap.)
fastbot/scripts/futmicro1_run.py  c09a39497b18f8e4e21fc3bad9f66860b1d579209c3aa0e6fd5ef509065509ba  (3 self-tests pass)
  Both import futport1_run.py (frozen 6b28c761…) unchanged.

## CARRY2 FAIL (A, B, C) + FUTMICRO1 FAIL, results logged 2026-10-12 (each run once)
fastbot/RESULT_CARRY2_FUTMICRO1.md  db1c4778738a3dd22fbc5b6e499051480337acb1e4eaf00988d978d09434910d
fastbot/data/futport1/run_carry2.log  46731333f148a37e34eabdfca71a4e2f69f73c563d31e7917efa21585ceb649b
fastbot/data/futport1/run_futmicro1.log  e461b22efae85b25cac986be90ca97fd5a699d520ad7ea62f4c75c4b09e595c2

## FORWARD_BATCH2 recorders frozen 2026-10-12, before any forward day
fastbot/scripts/forward_trend1.py  baa5ecf22bf8ce707606f604f6a895a29fe72a9a9433ab27af8048469225fa99
  stdlib. The self-test reproduces FUTPORT1's trend sleeve on 3,736/3,736 days (max diff 5.6e-17) and futmicro1's $50k P&L (max diff $9e-13). Ledger start 2026-10-13.
  Data is copied once to data/trend1fwd/ and appended there (the frozen data/futport1 files are never touched). Pulls over $1 are refused. Only dates at least 2 days old are recorded.
fastbot/scripts/forward_goldry1.py  0153026e4da2c59c5dca681cae546b07527764d882090a250ee124959447023d
  stdlib. Residuals equal the frozen oilgold_run.goldry construction on 921 Fridays (max diff 1e-16). Paper sigma = sd of the last 52 weekly log returns x sqrt 52 (fixed in its docstring).
  Mechanical: it refreshes data/gold/DFII10.csv itself from FRED (append-only), because the existing FRED step does not include DFII10. First Friday 2026-10-16.
  forward_tick.sh steps 11-12 added (NON-FATAL).

2026-10-13  MECHANICAL FIX (no rule change): forward_trend1.py 1.0 -> 1.0.1
  Ticks at 2026-10-13 00:47 and 06:51 UTC failed with Databento dataset_unavailable_range (licence ends ~8 h before the request),
  so the ledger step was skipped. Pull end is now (UTC now - 9 h) floored to a date, as forward_oilcarry 1.0.1; a failed pull logs
  one line and the ledger step still runs. No ledger row had been written yet, so nothing recorded is affected.
fastbot/scripts/forward_trend1.py  235d129719ead544e92f37243ce74c2fcd6118399a54cdc8205639fdf78ccc40

2026-10-16  GLDFLOW2 frozen before any number (Dave approved "Pre-register monthly")
  data: WGC Goldhub ETF-flows workbook downloaded by Dave (as of 2026-09-30), saved as data/gold/WGC_ETF_Flows_2026-09.xlsx
  harness self-test fixed before freezing: planted-slope check moved to a no-noise case (exact), noisy case kept at t > 3.
fastbot/PREREGISTRATION_GLDFLOW2.md  da425cabf9f75f954d2daa926f792ffdce1f29676541d730e168a3b9b29f7584
fastbot/data/gold/WGC_ETF_Flows_2026-09.xlsx  54c8ae7aff679b681ea6d90ff01aa8da1b976d30887aeb1e2f670c50d5275ec4
fastbot/scripts/gldflow2_run.py  c79d8859f1a1a7837fc4bcb3585b13c565b950730d383f5b9474bf4bd7331a7e

2026-10-19  AIIND batch (AIKNN1, AIMA1) pre-registered and frozen before any data pull or port run (Dave's request)
fastbot/PREREGISTRATION_AIIND.md  bbc0ff63f41a456b683c6b471bcb2d901ca0b4a2a87113858fe173fa779dc52a
fastbot/pine/aiind/lastguru_vwma_knn_mfi_adx.pine  13f856e2f8ca55018a80cc71b6054747ee66f79df10521ec94967fb149149714
fastbot/pine/aiind/zeiierman_ai_source_switching_ma.pine  f123c21ab60b4a7414e661fd558fd6739411385f64d21efd3e6c75c6bc2db00c
fastbot/scripts/fetch_aiind.py  0b06a768a3267f486e57f912c1b9a2ef3a80209e39a5848fbe1bd95250488dcd
2026-10-19  AIIND ports and harness frozen before any real data was loaded (self-test ALL PASS: Pine helpers, hand-checked kNN vote,
  no-look-ahead checks on both scripts, control = plain Supertrend; synthetic back-adjust and trade-fill checks)
fastbot/scripts/aiind_port.py  ab2d0fcdc2f0b609d6bd346bc8ce07f5aaec2cbb63017d3ab082310072858db6
fastbot/scripts/aiind_run.py  c5868bc5f472020f3bc5ef321a66ad660562d823fadf34051c2ed7cfb9e4c8b9
2026-10-19  AIIND data in: Binance BTCUSDT 5m 962,473 bars 2017-08-17 -> 2026-10-16 (126 files); ES/NQ top-ups to 2026-10-16 (fut/*_2026b.npz built in the cloud copy).
  First TradingView export received was KRAKEN:BTCUSD on a 15-minute chart (not the registered BINANCE:BTCUSDT 5m), so it cannot serve as the port check.
  Disclosure: reading its format showed TradingView's own figures for that chart (Oct 2025 -> Oct 2026, zero commission: cumulative -47%).
  No rule, window or cost was changed; the main runs have not been started.
2026-10-20  AIIND port check (before either main run): TradingView exports arrived as BINANCE:BTCUSD 5m (thin USD pair), not BTCUSDT.
  Mechanical deviation: ports run on the OHLCV inside TradingView's own exports. Zeiierman VERIFIED (99.6% state match);
  lastguru PARTLY VERIFIED (VWMAs to 5e-12, 53/53 entries on port crossovers; kNN vote not checkable: memory predates the export).
  Disclosure: the BTCUSD trade list shows TradingView's own figures for that pair (Oct 2025 -> Oct 2026, zero commission: -42%).
  Main runs started 2026-10-20 in the cloud copy with the frozen shas (bbc0ff63 / ab2d0fcd / c5868bc5).
2026-10-20  AIIND runs done (once each): AIKNN1 FAIL, AIMA1 FAIL. Post-hoc (not registered) random-filter placebo for KNN-ADD.
fastbot/RESULT_AIIND.md  cde036f56693611ddff86686a55663e50a4c2ce0964cbd445473526631641295
fastbot/scripts/aiind_posthoc_placebo.py  649496ea3dc63ff98eb95cd192a77139c6e9216df75137351ef41fe1471e1186

2026-10-24  PREREGISTRATION_v25.3 (Dave approved): calendar keeps every BLS date ever fetched; CPI 2026-10-14 counted as MISSED.
fastbot/PREREGISTRATION_v25.3.md  f7be8d12e0265b507673617429f23ca2bd2b023e2c1083d00eae3412ebbad645
fastbot/scripts/calendar_forward.py  3bc7327e1236351b8cf62d17b8a35883cd3b989147d36b91b73cc7cae1e96e24  (v1.6; v1.5 dac781ee... kept in scripts/archive/)
2026-10-24  data/tv refreshed through 2026-10-23 (11 series, vintage checks passed; tvremix get_ohlcv count=15; raw in data/tv/raw/20261024,
  bars transcribed from the session's tool output). USI:PCC NOT updated: TradingView revised 2026-10-15 (0.790806 stored -> 0.790382); awaiting Dave.
  AAII refreshed by Dave 2026-10-24 (survey 2026-10-22).
2026-10-24  PCC 2026-10-15 pinned to the stored value 0.790806 (Dave); PCC refreshed to 2026-10-23. VINTAGE_PINS.json 87e36fa76b7aef6d...
2026-10-24  PCC 2026-10-15 pinned (Dave: keep stored 0.790806 over TradingView's revision 0.790382); PCC refreshed to 2026-10-23.
2026-10-30 weekly v41 refresh: data/tv raw/20261030 converted (12 ok, none); forest SPX +3 NAS +3 sessions; AAII last 2026-10-22
2026-10-30  AAII refreshed from Dave's download (survey 2026-10-29) into data/v41/refresh/aaii_sentiment.xls
2026-10-31  weekly forest catch-up: AAII unchanged, last survey 2026-10-29; data/tv refreshed (11 series ok, 1 refused: PCC vintage change 2026-10-29 0.84477->0.84476, awaiting Dave); scikit-learn 1.7.2 installed in Cowork VM; forest rows 41
2026-11-01  PCC 2026-10-29 pinned (Dave: keep stored 0.84477 over TradingView's revision 0.84476; standing choice: do not change recorded data for small revisions); PCC refreshed to 2026-10-30.
2026-11-01  scripts/tv_autopin.py v1.0 (sha 73468cf4fd92e8b5e7bdfc501fc46f119031d249266b5761b464973683826df5): Dave's standing rule -- TradingView revisions <=1% are pinned to the original value automatically and logged in data/tv/VINTAGE_REVISIONS.csv; larger ones are logged and flagged, not pinned. Log seeded with the three past PCC decisions.
2026-11-05  monthly upkeep re-run at Dave's request (the 2026-11-03 run stopped mid-pull, nothing converted): data/tv raw/20261105 converted, 12 ok, no new revisions; pulled count=15 instead of 300 (usage limit hit on 11-03/11-05); forest rows 48 data, SPX +4 NAS +4 sessions; deferred 2026-10-30..11-04 awaiting AAII/COT/FRED
2026-11-06  AAII refreshed from Dave's download (sentiment (4).xls, survey 2026-11-05) into data/v41/refresh/aaii_sentiment.xls; forest recorder re-run
2026-11-07  weekly forest catch-up: AAII unchanged (already current), last survey 2026-11-05; data/tv refreshed (12 series ok; revisions auto-kept: none new (existing PCC 2026-10-29 pin applied); large revisions flagged: none); forest rows 51
