"""Daily closes for v52/v53 from the struct15 15m caches. Close = the 15m bar ending at the cash close:
SPX500/NAS100 bar starting 15:45 New York; UK100 bar starting 16:15 London; XAUUSD bar starting 16:45 New York (as v48).
Also returns the quoted spread at that bar's open (bp)."""
import numpy as np, datetime as dt
from zoneinfo import ZoneInfo
from struct15 import load15
SPEC = {"spx500usd": ("America/New_York", "15:45"), "nas100usd": ("America/New_York", "15:45"),
        "uk100gbp": ("Europe/London", "16:15"), "xauusd": ("America/New_York", "16:45")}

def daily(stem):
    d = load15(stem); tz, hm = SPEC[stem]; Z = ZoneInfo(tz); out = {}
    ts = d["t"].astype("datetime64[s]").astype(object)
    for i, t in enumerate(ts):
        L = t.replace(tzinfo=dt.timezone.utc).astimezone(Z)
        if L.strftime("%H:%M") == hm and L.weekday() < 5:
            out[L.date()] = (float(d["c"][i]), float(d["spr"][i]))
    return out
