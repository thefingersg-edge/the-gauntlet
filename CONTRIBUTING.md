# Found something wrong?

Open an issue. The standing offer on the channel is that a real error in one of
these results gets its own video, with credit.

## What makes a good issue

Name the file, the figure and what you got instead. "The control in
`FINDINGS_CANDLESPACE.md` looks wrong" is hard to act on; "`b3_pattern_zoo.py`
line 212 excludes ±21 bars around every detection, which on `xauusd` leaves 167
control days out of 5188, and the §4 baseline is computed on those" is a
finding.

If you re-ran something and got a different number, say which data you used and
over what dates. Several of these series were refreshed to a common end date of
2026-08-31; an older pull will not match.

## What I am least confident about

In rough order, based on the errors already caught:

- **Controls that silently shrink.** The matched-control construction excludes a
  window around every detection. Where a pattern fires often, almost nothing is
  left. There is now a coverage floor, but check it.
- **Session-stamped bars.** Daily futures bars are stamped at the session open,
  in exchange local time, across daylight saving changes. One pass of this was
  found and fixed. I would not bet there is only one.
- **Financing signs.** Long pays, short receives, and the markup differs by
  asset class. Brent's implied benchmark is around −46% a year because the roll
  lives in the financing line. Easy to get backwards.
- **Robustness ratios on a negative base.** Meaningless, and they were being
  computed anyway until gate 5 was changed to refuse them.
- **Anything ranked by |t|.** Sorting by significance discards the sign, and in
  at least one case the sign was the only thing distinguishing signal from
  artefact.

## What is out of scope

- Requests for a strategy, signal or entry. There isn't one; that is the result.
- Suggestions to loosen a gate so something passes. The gates were written
  before the data and are not negotiable after it. A reasoned argument that a
  gate was *wrongly specified in the first place* is very much in scope — say so
  explicitly and I will treat it as a registration amendment, dated.
- Trading advice, in either direction.
