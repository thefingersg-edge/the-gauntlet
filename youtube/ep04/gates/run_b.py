import engine, arm_b, score
# its own sizing: notional = 0.0015 x E / sigma_daily ; approximate sigma by
# ATR/price so the shared simulator can size it the same way as the others
sizing = lambda t, atr, E, V: (0.0015 * E) / ((atr / t.entry_px) * t.entry_px * V)
r = score.score("ARM B (path continuity)", arm_b, sizing, claimed_dd=None)
