import engine, arm_a, score
sizing = lambda t, atr, E, V: (0.01 * E) / (3.0 * atr * V)
r = score.score("ARM A (Donchian 55/20 + EMA filter)", arm_a, sizing, claimed_dd=-0.40)   # its own stated range was 20-40%
