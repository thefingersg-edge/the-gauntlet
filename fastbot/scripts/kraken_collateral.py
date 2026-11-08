#!/usr/bin/env python3
"""PHASE 0 for PREREGISTRATION_v7 -- is the collateral buffer real?

WHAT IS BEING ASKED
-------------------
RESULT_KRAKENBASIS measured +4.15 points of excess over the T-bill and then
rejected it on ONE input: a USD collateral buffer of 73.5%, which multiplied
committed capital by 1.73x and turned +3.75 points into +0.53.

That buffer assumed BTC collateral is worth nothing against a short BTC
future. Whether that is true is a CONTRACT TERM. This file reads it.

No return data is touched here. The v4 measurement stands as made.

THE CONTAMINATION (v7 section 2)
--------------------------------
I already know that without the buffer both v4 gates pass. So this Phase 0
decides the whole thing, and it is being run by someone who knows which
answer revives the candidate. The guard is that section 4 of the
pre-registration fixed, before anything was read, exactly what settles it:

    PROCEED       BTC accepted, haircut <= 30%, one pool or a transfer
                  route, and a dated BTC contract currently listed
    CONFIRM       any of those false
    UNDETERMINED  the terms do not clearly say -- and v4's rejection STANDS

Ambiguity is not a pass. This file returns UNDETERMINED rather than a
default, and exits non-zero when it does.

TWO DEFECTS FOUND IN v1.2, BOTH FIXED HERE (v1.3)
-------------------------------------------------
1. `known=bool(source)` accepted ANY non-empty string as a source. A run
   was made with `--source "Kraken Futures collateral schedule, <url>"` --
   the literal placeholder text from an example command -- and Gate 0
   returned PROCEED on it. **A gate that can be passed by pasting the
   example is not a gate.** `source_is_real()` now rejects placeholder
   markers and requires a checkable locator, and the self-test plants that
   exact string and asserts it FAILS.

2. `tradeable` was still being read as availability. RESULT_TRACKA named
   this error and this file kept making it: it printed "3 inverse dated
   contract(s) are listed and tradeable" minutes before basis_monitor.py
   printed "inverse: 0 of 3 quoted", from the same venue, in the same
   directory. Liveness is now read from the tickers endpoint and the
   inverse branch requires a QUOTED contract, not a listed one. The
   predicate is defined here once and imported by basis_monitor, so the
   two files cannot drift apart again.

THE BUFFER MODEL
----------------
If BTC collateral is accepted at haircut h, then when the price rises by r
the short loses r while the collateral's usable value gains (1-h)*r. The
shortfall is r*h. Adding maintenance margin m on the notional:

    buffer = rally * haircut + maintenance

At h = 1.0 and m = 0 this returns v4's 0.735 exactly, which is the
regression check in section 9.2.

    python kraken_collateral.py --self-test
    python kraken_collateral.py --btc-haircut 0.20 --maintenance 0.05
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken_probe as KP                                    # noqa: E402

VERSION = "1.3"

#: Substrings that mark a source as unfilled boilerplate rather than a
#: reference. `<url>` is here because it was actually submitted and
#: actually passed.
PLACEHOLDERS = ("<", ">", "todo", "tbd", "fixme", "xxx", "placeholder",
                "example", "somewhere", "insert ", "your ", "...")

#: PREREGISTRATION_v7 section 4. Frozen.
MAX_HAIRCUT = 0.30
#: Read from RESULT_KRAKENBASIS. Not recomputed here -- section 5 forbids
#: re-measuring, and these are the published outputs of that run.
V4_RALLY = 0.735
V4_NET_NOTIONAL = 0.0758      # annualised, net of roll and commission
V4_RF = 0.0384                # contemporaneous T-bill, time-weighted
V4_EXCESS_AT_BUFFER = 0.0053  # what v4 reported
GATE_A_EXCESS = 0.020


def source_is_real(s):
    """Is this a reference a third party could go and check?

    v1.2 asked only whether the string was non-empty, and a placeholder
    copied out of an example command satisfied that. The frozen rule in
    PREREGISTRATION_v7 section 4 says an unsourced figure is UNDETERMINED;
    this is only a tightening of what 'sourced' operationalises to, not a
    change to the rule, and it is being written after seeing a false pass
    rather than after seeing a result.

    Requires: no placeholder marker, at least 15 characters, and a
    locator -- a URL, or a date the document can be pinned to.

    Returns (ok, reason).
    """
    t = (s or "").strip()
    if not t:
        return False, "no source given"
    low = t.lower()
    for p in PLACEHOLDERS:
        if p in low:
            return False, f"contains the placeholder {p!r}"
    if len(t) < 15:
        return False, f"too short to identify a document ({len(t)} chars)"
    has_url = bool(re.search(r"https?://\S{4,}", t))
    has_date = bool(re.search(r"(19|20)\d{2}", t))
    if not (has_url or has_date):
        return False, "no URL and no date -- nothing to check it against"
    return True, "url" if has_url else "dated reference"


def is_dead(tick):
    """Listed but not traded: no quote, no interest, mark == index.

    'tradeable' in the instruments endpoint means the venue permits
    orders. It does not mean anyone is sending them. PREREGISTRATION_v7
    read the flag and treated it as availability, which is a different
    thing -- and the difference is the whole distance between a contract
    existing and a contract you can get into.

    This is the CANONICAL definition. basis_monitor.py imports it from
    here rather than keeping its own, because the defect this fixes was
    two files in one directory disagreeing about the same contract.

    Returns (dead, reasons).
    """
    #: An empty payload is not one weak signal, it is no evidence of life
    #: at all. Falling through to the two-reason rule would have let a
    #: contract with NO ticker read as merely thin.
    if not tick:
        return True, ["no ticker data at all"]
    why = []
    if tick.get("bid") in (None, "", 0) or tick.get("ask") in (None, "", 0):
        why.append("no two-sided quote")
    for k in ("openInterest", "vol24h"):
        v = tick.get(k)
        if v is not None and float(v) == 0.0:
            why.append(f"{k} is zero")
    mk, ix = tick.get("markPrice"), tick.get("indexPrice")
    if mk is not None and ix is not None and float(mk) == float(ix):
        why.append("mark equals index -- nothing is pricing it")
    return (len(why) >= 2), why


def inverse_short_loss_btc(n_usd, f_entry, f_exit):
    """BTC lost by a short inverse future as the price moves.

    An inverse contract is denominated in USD and settles in BTC, so
    P&L_BTC = N * (1/F_exit - 1/F_entry) for a short. As F_exit rises
    without limit the loss converges to N/F_entry -- the initial BTC
    notional -- and cannot exceed it.
    """
    return n_usd * (1.0 / f_entry - 1.0 / f_exit)


def linear_short_loss_usd(n_btc, f_entry, f_exit):
    """USD lost by a short linear future. Unbounded above."""
    return n_btc * (f_exit - f_entry)


def linear_short_loss_btc(n_btc, f_entry, f_exit):
    """The same loss valued in BTC at the exit price.

    Worth computing because it is the subtlety that makes the inverse
    contract look more special than it is. Measured in BTC the linear
    short ALSO converges to the initial notional, since
    (F_exit - F_entry)/F_exit -> 1. The two structures do not differ in
    how much BTC can be lost; they differ in the UNIT THE MARGIN IS
    COMPUTED IN, and therefore in whether the collateral offsets the loss
    automatically or through a valuation with a haircut.
    """
    return linear_short_loss_usd(n_btc, f_entry, f_exit) / f_exit


def buffer_required(rally=V4_RALLY, haircut=1.0, maintenance=0.0):
    """Fraction of notional that must sit in USD to survive `rally`."""
    return rally * haircut + maintenance


def excess_at(buffer_frac, net_notional=V4_NET_NOTIONAL, rf=V4_RF):
    """v4's measured return, re-divided by the corrected capital."""
    return net_notional / (1.0 + buffer_frac) - rf


def liquidation_price(m_btc, n_usd, f_entry, mmr):
    """Price at which a BTC-margined short inverse future is liquidated.

    Equity in BTC is `M - N/F_entry + N/F`, the maintenance requirement is
    `mmr * N/F`, and liquidation is equity < requirement. Solving for
    `u = 1/F`:

        u < (N/F_entry - M) / (N * (1 - mmr))

    If the collateral equals the initial BTC notional the numerator is
    zero, so no positive price satisfies it: a FULLY COLLATERALISED short
    inverse future cannot be liquidated by an upward move, at any price.

    Returns None when that is the case.
    """
    num = n_usd / f_entry - m_btc
    if num <= 0:
        return None
    u = num / (n_usd * (1.0 - mmr))
    return (1.0 / u) if u > 0 else None


def gate_0_inverse(dated_inverse_quoted, mmr, collateral_ratio=1.0):
    """Gate 0 for an INVERSE contract, where no haircut applies.

    PREREGISTRATION_v7 section 4 was written for the linear structure --
    BTC posted as collateral, valued in USD, reduced by a haircut. It did
    not anticipate that Kraken still lists INVERSE dated contracts, which
    are margined in BTC directly. There is no conversion and therefore no
    haircut to read: the loss and the collateral are the same asset.

    THIS IS A STRUCTURAL FACT, NOT A FAVOURABLE READING. It is decided by
    the contract type the venue publishes and by arithmetic, both checked
    below, rather than by interpreting a margin schedule. What would
    falsify it: the contract not being inverse, NOT BEING QUOTED, or a
    fully collateralised short having a finite liquidation price.

    The argument is named QUOTED and not `listed` since v1.3. v1.2 passed
    it `bool(inv)` off the `tradeable` flag, and every inverse contract on
    the venue is flagged tradeable with a zero book. An instrument you
    cannot enter has no capital requirement to be efficient about.
    """
    if not dated_inverse_quoted or mmr is None:
        return "UNDETERMINED", None
    f_entry, n_usd = 50000.0, 50000.0
    m_btc = collateral_ratio * n_usd / f_entry
    liq = liquidation_price(m_btc, n_usd, f_entry, mmr)
    if liq is not None:
        return "CONFIRM", liq / f_entry
    return "PROCEED", None


def gate_0(accepted, haircut, one_pool, dated_quoted, known=True):
    """PREREGISTRATION_v7 section 4. Pure, so it can be tested.

    `dated_quoted`, not `dated_listed`: same correction as above.

    Returns one of 'PROCEED', 'CONFIRM', 'UNDETERMINED'.
    """
    if not known or accepted is None or haircut is None \
            or one_pool is None or dated_quoted is None:
        return "UNDETERMINED"
    if not dated_quoted:
        return "CONFIRM"
    if not accepted or not one_pool:
        return "CONFIRM"
    if haircut > MAX_HAIRCUT:
        return "CONFIRM"
    return "PROCEED"


def classify(payload, pair="XBTUSD"):
    """Dated BTC contracts currently listed, and whether inverse."""
    rows = []
    for it in payload.get("instruments", []):
        sym = (it.get("symbol") or "").upper()
        m = KP.DATED.match(sym)
        if not m or m.group(2) != pair.upper():
            continue
        typ = (it.get("type") or "").lower()
        rows.append(dict(symbol=sym, kind=m.group(1), type=typ,
                         tradeable=bool(it.get("tradeable", False)),
                         inverse=("inverse" in typ or m.group(1) == "FI"),
                         imr=it.get("marginLevels", [{}])[0].get(
                             "initialMargin"),
                         mmr=it.get("marginLevels", [{}])[0].get(
                             "maintenanceMargin")))
    return sorted(rows, key=lambda r: r["symbol"])


def report(rows, haircut, maintenance, source, tickers=None):
    by_sym = {(t.get("symbol") or "").upper(): t
              for t in (tickers or [])}
    have_ticks = bool(by_sym)
    for r in rows:
        t = by_sym.get(r["symbol"], {})
        d, why = is_dead(t)
        r["quoted"] = (not d) if have_ticks else None
        r["why"] = "; ".join(why)

    listed = [r for r in rows if r["tradeable"]]
    #: v1.2 read `inv` off this line, from the tradeable flag alone.
    quoted = [r for r in listed if r["quoted"]]
    inv = [r for r in quoted if r["inverse"]]
    inv_listed = [r for r in listed if r["inverse"]]

    print(f"\n  DATED BTC CONTRACTS")
    print(f"    {len(rows)} visible, {len(listed)} flagged tradeable, "
          f"{len(quoted) if have_ticks else '?'} actually quoted, "
          f"{len(inv)} of those inverse")
    for r in rows[:12]:
        state = ("?" if r["quoted"] is None
                 else ("quoted" if r["quoted"] else "DEAD"))
        print(f"    {r['symbol']:<20}{r['type']:<20}"
              f"{'tradeable' if r['tradeable'] else 'not tradeable':<16}"
              f"{'inverse' if r['inverse'] else 'linear':<9}{state}")

    if not have_ticks:
        print("\n    NO TICKER DATA. Liveness is unknown, so this run "
              "cannot tell a")
        print("    traded contract from a paper listing -- which is the "
              "exact error")
        print("    v1.2 made. Every branch below returns UNDETERMINED.")
    elif inv_listed and not inv:
        print(f"\n    {len(inv_listed)} inverse contract(s) are flagged "
              f"tradeable and NONE is quoted:")
        for r in inv_listed:
            print(f"      {r['symbol']:<20}{r['why']}")
        print("    `tradeable` means the venue permits orders, not that "
              "anyone sends")
        print("    them. The inverse branch is UNAVAILABLE, and with it "
              "the argument")
        print("    that removed v4's buffer.")
    if quoted and not inv:
        print("\n    NOTE: the quoted contracts are LINEAR. The inverse "
              "structure --")
        print("    whose BTC loss is bounded by construction -- applies to "
              "the earlier")
        print("    part of the v4 sample and is not what would be traded "
              "today.")

    mm = [r["mmr"] for r in (quoted or listed) if r["mmr"] is not None]
    print(f"\n  MARGIN, from the instruments endpoint")
    if mm:
        print(f"    maintenance margin on listed contracts: "
              f"{min(mm)*100:.1f}% - {max(mm)*100:.1f}%")
    else:
        print("    the endpoint returned no margin levels")

    print(f"\n  BTC COLLATERAL HAIRCUT")
    if haircut is None:
        print("    NOT SUPPLIED. Kraken publishes collateral haircuts in "
              "its support")
        print("    documentation rather than the public API, so this file "
              "cannot read")
        print("    it. Pass --btc-haircut with the figure and --source "
              "with where it")
        print("    came from. Guessing it would decide the entire test.")
    else:
        print(f"    {haircut*100:.1f}%   source: {source or 'NOT STATED'}")
    src_ok, src_why = source_is_real(source)
    if haircut is not None and not src_ok:
        print(f"    SOURCE REJECTED -- {src_why}.")
        print("    v1.2 accepted any non-empty string here, and a run was "
              "made with the")
        print("    placeholder text out of an example command. A figure "
              "with no source")
        print("    is UNDETERMINED under section 4 whatever its value, so "
              "the number")
        print("    above decides nothing.")

    #: The inverse branch is decided first, because when it applies the
    #: haircut question does not arise at all.
    mmr = min([r["mmr"] for r in (quoted or listed)
               if r["mmr"] is not None], default=None)
    v_inv, liq = gate_0_inverse(bool(inv), mmr)
    if inv:
        print(f"\n  THE INVERSE BRANCH -- section 4 did not anticipate it")
        print(f"    {len(inv)} inverse dated contract(s) are listed and "
              f"tradeable, and an")
        print(f"    inverse future is margined in BTC. Loss and collateral "
              f"are the same")
        print(f"    asset, so no conversion and no haircut apply. The "
              f"question becomes")
        print(f"    whether a fully collateralised short can be liquidated "
              f"at all.")
        for cov in (1.00, 0.90, 0.75):
            L = liquidation_price(cov * 1.0, 50000.0, 50000.0, mmr or 0.01)
            print(f"      collateral {cov*100:>4.0f}% of notional  ->  "
                  + ("NEVER liquidated by an upward move"
                     if L is None else f"liquidated at {L/50000:.2f}x"))

    accepted = None if haircut is None else True
    one_pool = None if haircut is None else True
    lin_quoted = bool([r for r in quoted if not r["inverse"]])
    v_lin = gate_0(accepted, haircut, one_pool,
                   lin_quoted if have_ticks else None,
                   known=(haircut is not None and src_ok))
    #: The overall verdict may only be carried by a branch that is
    #: actually available. v1.2's `v_inv if inv else v_lin` was right in
    #: form and wrong in input, because `inv` came off the tradeable flag.
    v = v_inv if inv else v_lin

    print(f"\n  GATE 0 -- PREREGISTRATION_v7 section 4")
    print(f"    inverse branch: {v_inv}"
          + (f"  (liquidated at {liq:.2f}x)" if liq else
             ("  (no liquidation price exists)" if v_inv == "PROCEED"
              else "  -- no inverse contract is quoted")))
    print(f"    linear branch:  {v_lin}"
          + ("  -- needs a SOURCED haircut" if v_lin == "UNDETERMINED"
             else ""))
    print(f"    {v}")
    if v == "PROCEED" and inv:
        #: No USD buffer: the BTC that is the long leg IS the margin.
        b = 0.0
        e = excess_at(b)
        print(f"\n    buffer  0.0% -- the BTC long leg is itself the "
              f"margin")
        print(f"    capital committed  1.00x  (v4 assumed "
              f"{1+V4_RALLY:.2f}x)")
        print(f"    excess over the T-bill  {e*100:+.2f} pts  "
              f"(v4 reported {V4_EXCESS_AT_BUFFER*100:+.2f})")
        print(f"    Gate A needs {GATE_A_EXCESS*100:.1f} pts: "
              f"{'PASS' if e >= GATE_A_EXCESS else 'FAIL'}")
        print("\n    WHAT THIS STILL DOES NOT SETTLE")
        print("      Only 6 of v4's 18 cycles used inverse contracts; the "
              "other 12 were")
        print("      linear. The premium is the same either way, but the "
              "capital claim")
        print("      rests on the instrument you would trade TODAY.")
        print("      [RETRACTED] v1.1 warned that the hedge drifts and "
              "needs rebalancing.")
        print("      It does not, and the arithmetic is exact: with "
              "M = N/F_entry,")
        print("      equity is N/F and notional is N/F at EVERY price, so "
              "the ratio is")
        print("      1.0000 up and down without a single trade. The USD "
              "value of the")
        print("      equity is constant at N -- the position IS BTC "
              "converted to")
        print("      synthetic USD. This correction FAVOURS the candidate, "
              "which is why")
        print("      it is shown rather than quietly dropped.")
        print("      What remains is basis risk: mid-life the equity is "
              "marked at the")
        print("      FUTURES price, not spot, so its spot value moves with "
              "F/S until")
        print("      expiry. v4 section 1 already named that.")
        print("      Auto-deleveraging can close a profitable short when "
              "counterparties")
        print("      are liquidated. Not readable from the API, and it "
              "bites exactly when")
        print("      it matters.")
        print("      Counterparty risk is unchanged and still priced only "
              "as v4's judgement.")
        print("\n    Re-run kraken_basis.py --buffer 0.0 to apply Gates B "
              "and C to the")
        print("    SAME per-cycle returns.")
    elif v == "PROCEED":
        b = buffer_required(V4_RALLY, haircut, maintenance)
        e = excess_at(b)
        print(f"\n    buffer  {V4_RALLY*100:.1f}% rally x "
              f"{haircut*100:.0f}% haircut + {maintenance*100:.0f}% "
              f"maintenance = {b*100:.1f}% of notional")
        print(f"    capital committed  {1+b:.2f}x  (v4 assumed "
              f"{1+V4_RALLY:.2f}x)")
        print(f"    excess over the T-bill  {e*100:+.2f} pts  "
              f"(v4 reported {V4_EXCESS_AT_BUFFER*100:+.2f})")
        print(f"    Gate A needs {GATE_A_EXCESS*100:.1f} pts: "
              f"{'PASS' if e >= GATE_A_EXCESS else 'FAIL'}")
        print("\n    Gates B and C are NOT decided here. Re-run "
              "kraken_basis.py with")
        print(f"    --buffer {b:.4f} to apply them to the SAME per-cycle "
              "returns.")
    elif v == "CONFIRM":
        print("    v4's rejection is CONFIRMED rather than assumed.")
    else:
        print("    The terms do not clearly say. Section 4: ambiguity is "
              "not a pass,")
        print("    and v4's rejection STANDS.")
    return v


def self_test():
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        if not isinstance(cond, (bool, int)):
            raise TypeError(f"check({name!r}) got {type(cond).__name__}")
        ok &= bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
              + (f"   {detail}" if detail else ""))

    print(f"kraken_collateral.py v{VERSION} self-test\n")

    print("the inverse short's BTC loss is BOUNDED (sec 9.1)")
    fe = 50000.0
    n = fe                      # $50,000 notional = 1 BTC at entry
    losses = [inverse_short_loss_btc(n, fe, fe * k)
              for k in (1.5, 5, 100, 1e6, 1e12)]
    check("it rises with the price but converges",
          all(losses[i] < losses[i + 1] for i in range(len(losses) - 1)),
          " ".join(f"{x:.4f}" for x in losses))
    check("and the limit is exactly the initial BTC notional",
          abs(losses[-1] - 1.0) < 1e-6, f"{losses[-1]:.6f} BTC")
    check("it can never exceed it",
          all(x < 1.0 for x in losses))

    print("\nthe linear short is unbounded IN USD (sec 9.1)")
    usd = [linear_short_loss_usd(1.0, fe, fe * k) for k in (1.5, 5, 100)]
    check("USD loss grows without limit",
          usd[-1] > usd[0] * 50, f"${usd[0]:,.0f} -> ${usd[-1]:,.0f}")
    #: The subtlety worth recording: valued in BTC the linear short ALSO
    #: converges to one notional. The structures do not differ in how much
    #: BTC is at risk. They differ in the UNIT the margin is computed in.
    btc = [linear_short_loss_btc(1.0, fe, fe * k)
           for k in (1.5, 5, 100, 1e6)]
    check("but valued in BTC it converges to one notional too",
          abs(btc[-1] - 1.0) < 1e-5, f"{btc[-1]:.6f} BTC")
    check("so the difference is the margin UNIT, not the BTC at risk",
          abs(btc[-1] - losses[-1]) < 1e-4,
          "both converge to 1.0 BTC")

    print("\nthe buffer model reproduces v4 (sec 9.2)")
    b100 = buffer_required(V4_RALLY, haircut=1.0, maintenance=0.0)
    check("a 100% haircut gives back v4's 73.5% buffer",
          abs(b100 - V4_RALLY) < 1e-12, f"{b100*100:.1f}%")
    check("and v4's reported excess",
          abs(excess_at(b100) - V4_EXCESS_AT_BUFFER) < 5e-4,
          f"{excess_at(b100)*100:+.2f} vs "
          f"{V4_EXCESS_AT_BUFFER*100:+.2f} pts")
    check("a zero buffer gives back v4's unbuffered +3.75",
          abs(excess_at(0.0) - 0.0375) < 5e-4,
          f"{excess_at(0.0)*100:+.2f} pts")
    b20 = buffer_required(V4_RALLY, 0.20, 0.05)
    check("a 20% haircut plus 5% maintenance is far smaller",
          abs(b20 - (0.735 * 0.20 + 0.05)) < 1e-12, f"{b20*100:.1f}%")
    check("and it clears Gate A", excess_at(b20) >= GATE_A_EXCESS,
          f"{excess_at(b20)*100:+.2f} pts")

    print("\nthe inverse branch is decided by arithmetic, not by reading")
    fe = 50000.0
    check("a FULLY collateralised short has no liquidation price",
          liquidation_price(1.0, fe, fe, 0.01) is None)
    #: planted: under-collateralise it and a finite price must appear,
    #: because a branch that can only ever return "safe" is not a test
    for cov, want in ((0.90, 9.90), (0.75, 3.96), (0.50, 1.98)):
        L = liquidation_price(cov, fe, fe, 0.01)
        check(f"at {cov*100:.0f}% collateral it liquidates at "
              f"{want:.2f}x",
              L is not None and abs(L / fe - want) < 0.02,
              f"{L/fe:.2f}x" if L else "None")
    check("a higher maintenance margin liquidates sooner",
          liquidation_price(0.90, fe, fe, 0.20)
          < liquidation_price(0.90, fe, fe, 0.01),
          f"{liquidation_price(0.90, fe, fe, 0.20)/fe:.2f}x vs "
          f"{liquidation_price(0.90, fe, fe, 0.01)/fe:.2f}x")
    #: v1.1 printed a warning that the hedge drifts and needs
    #: rebalancing. It was wrong, and this is the check that shows it.
    #: With M = N/F_entry the equity and the notional are BOTH N/F, so
    #: the collateralisation ratio is exactly 1 at every price.
    for k in (0.25, 1.0, 5.0, 20.0):
        F = fe * k
        eq = 1.0 - fe * (1.0 / fe - 1.0 / F)
        notl = fe / F
        check(f"at {k:g}x the ratio is still exactly 1",
              abs(eq / notl - 1.0) < 1e-12, f"{eq:.4f} / {notl:.4f}")
    check("and the equity's USD value is constant",
          all(abs((1.0 - fe * (1.0 / fe - 1.0 / (fe * k))) * (fe * k) - fe)
              < 1e-6 for k in (0.25, 1.0, 5.0, 20.0)),
          "N at every price -- BTC converted to synthetic USD")

    v, _ = gate_0_inverse(True, 0.01)
    check("QUOTED inverse contracts PROCEED", v == "PROCEED")
    v2, r2 = gate_0_inverse(True, 0.01, collateral_ratio=0.9)
    check("under-collateralised CONFIRMS the rejection",
          v2 == "CONFIRM" and r2 is not None, f"{r2:.2f}x")
    v3, _ = gate_0_inverse(False, 0.01)
    check("no inverse contract QUOTED is UNDETERMINED, not PROCEED",
          v3 == "UNDETERMINED")
    v4_, _ = gate_0_inverse(True, None)
    check("a missing maintenance margin is UNDETERMINED",
          v4_ == "UNDETERMINED")

    print("\nthe source must be checkable (v1.3, defect 1)")
    #: PLANTED: the exact string submitted on 2026-08-25, which v1.2
    #: accepted and which turned Gate 0's linear branch into a PROCEED.
    #: If this ever passes again the gate is worthless.
    BAD = "Kraken Futures collateral schedule, <url>"
    okc, whyc = source_is_real(BAD)
    check("the placeholder that actually passed v1.2 is REJECTED",
          not okc, f"{BAD!r} -> {whyc}")
    check("and gate_0 returns UNDETERMINED when handed it",
          gate_0(True, 0.20, True, True,
                 known=source_is_real(BAD)[0]) == "UNDETERMINED")
    for bad, tag in ((""              , "empty"),
                     ("   "           , "whitespace"),
                     ("TODO"          , "TODO"),
                     ("see docs"      , "too short"),
                     ("example page"  , "the word example"),
                     ("their website" , "no URL and no date")):
        check(f"rejected: {tag}", not source_is_real(bad)[0],
              source_is_real(bad)[1])
    for good, tag in (
            ("https://support.kraken.com/articles/multi-collateral", "URL"),
            ("Kraken Futures collateral schedule, retrieved 2026-08-25",
             "dated reference")):
        check(f"accepted: {tag}", source_is_real(good)[0])
    #: and it must not be passable by padding to length alone
    check("15 characters of nothing is still rejected",
          not source_is_real("aaaaaaaaaaaaaaaaaaaa")[0])

    print("\nlisted is not quoted (v1.3, defect 2)")
    DEAD = dict(symbol="FI_XBTUSD_260828", bid=None, ask=None,
                openInterest=0, vol24h=0,
                markPrice=79889.33, indexPrice=79889.33)
    LIVE = dict(symbol="FF_XBTUSD_260925", bid=78923, ask=80183,
                openInterest=18.76, vol24h=18.83,
                markPrice=79600.0, indexPrice=79889.33)
    d, why = is_dead(DEAD)
    check("the real dead inverse ticker reads DEAD", d, "; ".join(why))
    check("the real quoted linear ticker does not", not is_dead(LIVE)[0])
    check("an absent ticker is DEAD, not merely thin", is_dead({})[0])
    #: PLANTED: the gate must refuse the branch when nothing is quoted,
    #: even though the venue flags all three tradeable.
    check("gate_0_inverse refuses a listed-but-unquoted contract",
          gate_0_inverse(False, 0.01)[0] == "UNDETERMINED")
    check("and accepts it once it IS quoted",
          gate_0_inverse(True, 0.01)[0] == "PROCEED")
    #: the two files must not disagree about the same contract again
    CASES = [DEAD, LIVE, {},
             dict(bid=1, ask=2, openInterest=0, vol24h=5.0),
             dict(bid=1, ask=2, openInterest=3, vol24h=5.0,
                  markPrice=100.0, indexPrice=100.0)]
    try:
        import basis_monitor as BM
        #: NOT an identity check. Run as a script this module is
        #: `__main__`, so `BM.is_dead is is_dead` is False for a reason
        #: that has nothing to do with the defect. What matters is that
        #: basis_monitor does not DEFINE one.
        check("basis_monitor does not own a copy of is_dead",
              BM.is_dead.__module__ == "kraken_collateral",
              f"defined in {BM.is_dead.__module__}")

        def agree(f, g):
            return all(f(c)[0] == g(c)[0] for c in CASES)
        check("and the two files agree on every case",
              agree(BM.is_dead, is_dead), f"{len(CASES)} tickers")
        #: PLANTED: swap in a predicate that disagrees on exactly one
        #: case and confirm the comparison notices. An agreement check
        #: that has never been seen to fail has not been tested.
        check("the agreement check demonstrably FIRES",
              not agree(lambda t: (False, []), is_dead))
    except Exception as exc:                                  # noqa: BLE001
        check("basis_monitor imports cleanly", False, str(exc)[:60])

    print("\nGate 0, either side of the 30% threshold (sec 9.3)")
    check("exactly 30% PROCEEDS",
          gate_0(True, 0.30, True, True) == "PROCEED")
    check("30.1% CONFIRMS the rejection",
          gate_0(True, 0.301, True, True) == "CONFIRM")
    check("no BTC collateral CONFIRMS",
          gate_0(False, 0.10, True, True) == "CONFIRM")
    check("separate pools with no transfer CONFIRMS",
          gate_0(True, 0.10, False, True) == "CONFIRM")
    check("no dated contract QUOTED CONFIRMS",
          gate_0(True, 0.10, True, False) == "CONFIRM")

    print("\nambiguity returns UNDETERMINED, never a default (sec 9.4)")
    check("an unknown haircut is UNDETERMINED",
          gate_0(True, None, True, True) == "UNDETERMINED")
    check("an unsourced figure is UNDETERMINED",
          gate_0(True, 0.10, True, True, known=False) == "UNDETERMINED")
    check("UNDETERMINED is not PROCEED",
          gate_0(True, None, True, True) != "PROCEED")

    print("\nno returns are recomputed here (sec 9.5)")
    import kraken_collateral as _self
    banned = ("measure", "cycle", "candle", "backtest", "simulate")
    def scan():
        return [x for x in dir(_self) if not x.startswith("_")
                and any(w in x.lower() for w in banned)]
    check("no measurement function exists", scan() == [], f"{scan()}")
    setattr(_self, "measure_cycles", lambda: None)
    fired = scan() == ["measure_cycles"]
    delattr(_self, "measure_cycles")
    check("and the detector demonstrably FIRES", fired and scan() == [])
    check("v4's numbers are constants read from the result, not derived",
          isinstance(V4_NET_NOTIONAL, float)
          and isinstance(V4_RF, float) and isinstance(V4_RALLY, float))

    print("\n" + ("ALL PASS" if ok else "FAILURES ABOVE"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--btc-haircut", type=float, default=None,
                    help="BTC collateral haircut as a decimal, e.g. 0.20")
    ap.add_argument("--maintenance", type=float, default=0.0)
    ap.add_argument("--source", default="",
                    help="where the haircut figure came from")
    ap.add_argument("--pair", default="XBTUSD")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(self_test())

    print(f"kraken_collateral.py v{VERSION}   PHASE 0 -- CONTRACT TERMS "
          f"ONLY\n")
    payload = None
    for url in KP.INSTRUMENT_URLS:
        try:
            payload = json.loads(KP._get(url))
            print(f"  {url.rsplit('/', 1)[-1]}  OK")
            break
        except Exception as exc:                              # noqa: BLE001
            print(f"  {url.rsplit('/', 1)[-1]}  FAIL {str(exc)[:60]}")
    if payload is None:
        raise SystemExit("\n  UNDETERMINED: no instrument list retrieved. "
                         "v4's rejection stands.")

    #: v1.3. Listing is read from instruments; LIVENESS is read from
    #: tickers. v1.2 had only the first and inferred the second from a
    #: flag that does not mean it.
    ticks = []
    try:
        tj = json.loads(KP._get(f"{KP.FUT}/derivatives/api/v3/tickers"))
        ticks = tj.get("tickers", [])
        print(f"  tickers  OK  ({len(ticks)} instruments)")
    except Exception as exc:                                  # noqa: BLE001
        print(f"  tickers  FAIL {str(exc)[:60]}")
        print("  Without them a paper listing is indistinguishable from a "
              "market.")

    v = report(classify(payload, a.pair), a.btc_haircut, a.maintenance,
               a.source, ticks)
    sys.exit(0 if v == "PROCEED" else 2)


if __name__ == "__main__":
    main()
