import engine, arm_d, arm_e, score
sz_d = lambda t, atr, E, V: (0.006 * E) / (5.0 * atr * V)
sz_e = lambda t, atr, E, V: (0.0010 * E) / ((atr / t.entry_px) * t.entry_px * V)
score.score("ARM D (v3 trend + index MR)", arm_d, sz_d, claimed_dd=-0.30)
score.score("ARM E (twin sleeve)", arm_e, sz_e, claimed_dd=-0.20)
