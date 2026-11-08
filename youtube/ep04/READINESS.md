# Episodes 4/5 — what is done, what is not

```
AS OF: 2026-11-06
SHORT ANSWER: the science is done. The video is not.
```

## Done

- **Preregistration** written before any generation, with the three eras
  defined (a hole found and closed before any gate was run).
- **Run 0 binned and documented** — the seal failed, caught by reading the
  outputs, published as `generated/_CONTAMINATION.md`.
- **Six arms generated clean** in fresh chats with no project and memory
  off. All raw outputs preserved verbatim in `generated/`.
- **Literature verified** from the primary source: Wiecki et al. (2016),
  *The Journal of Investing* 25(3), 69-80, doi:10.3905/joi.2016.25.3.069,
  with four internal inconsistencies in the paper documented.
- **Gate engine built and independently validated** against ARM F's own
  published figures to within 1-2% on every reported quantity.
- **All six arms scored.** `gates/RESULTS_ALL.md`.
- **ARM B's own pre-registered kill tests honoured** (below).
- **A data defect found and handled** — mixed timestamp conventions inside
  one hourly file.

## ARM B's kill tests — run, because it committed to them

It pre-registered seven abandonment conditions. The two that test the
mechanism rather than the profit both pass:

| Test | Result |
|---|---|
| **Mirror** — reverse the filter, trade jump-built trends instead | smooth −0.00139 vs jump-built **−0.00363**. The jumpy trends do materially worse, as the theory predicts. **Filter survives.** |
| **Monotone gradient** — edge must rise from jumpiest to smoothest tercile | jumpiest −0.00619, mid −0.00020, smoothest **−0.00014**. Monotone, in the predicted direction. **Gradient confirmed.** |

**So the mechanism is real and the strategy is still abandoned** — on its
own condition 3 (edge versus matched control is negative), not condition 1.
Frog-in-the-pan carries into these markets in the direction the literature
says. It is just far too small to pay a spread with.

That is a better result than a flat null, and ARM B called it in advance:
"Criterion 3, effect size... Low-volatility FX pairs need roughly 0.35-0.40%
gross per trade to clear 0.20% net, which is demanding."

## Not done — blocking, needs Dave

1. **The spread table.** It decides ARM F's overnight sleeve and ARM C
   outright. Both sit within a basis point of their own costs.
2. **Gate 7's threshold** (a claim may understate the measured drawdown by
   at most 25%). Mine, not preregistered.
3. **Wiecki figure captions.** Three of four readings are still inference
   from plot geometry, and Fig. D has an unresolved date discrepancy. Not
   to go on screen until resolved.

## Not done — production

4. **Pine scripts.** Preregistration 5b commits to publishing one per
   strategy with the "this cannot reproduce our numbers" disclosure.
5. **Episode scripts** for 4 (build) and 5 (break). Nothing written.
6. **The degradation frame** — five curves, one axis: the honest strategy,
   then intrabar look-ahead, ex-post market selection, costs removed,
   closed-trade-only equity. Replaces the B-vs-E frame ARM E refused to
   provide.
7. **Wiecki Fig. B rebuilt in channel style** — IS vs OOS for volatility,
   drawdown and Sharpe side by side.
8. **The round-versus-Sharpe chart** from ARM F: 0.82 -> 1.08 -> 1.23
   in-sample against 0.61 -> 0.60 -> 0.67 out, with the configuration count.
9. **Thumbnails, titles, descriptions, tags, chapters.**

## Not done — later

10. **The rejected-list file** (14 price conditions, 25 indicators, 32 chart
    constructions with reasons), needed to score the informed-run episode.
