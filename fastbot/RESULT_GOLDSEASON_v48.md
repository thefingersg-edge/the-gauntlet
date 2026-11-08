# RESULT — v48: gold before Chinese New Year and Diwali. DESCRIPTIVE ONLY. Gold rose into both on average, but the numbers are too noisy to separate from normal drift.

```
SPEC:     PREREGISTRATION_v48.md  sha 2ad9b46b…  (descriptive by pre-registration; MDE ~194 bp)
METHOD:   gold_season_v48.py 1.0; XAU/USD OANDA 15m (data/v24), 16:45 NY bar close; event table data/v48/events_v48.csv sha b7640992… (frozen before the price join); log data/run_v48.log
RUN:      2026-09-27
VERDICT:  DESCRIPTIVE (no gate)
```

**I am not a financial adviser. This is a measurement, not a recommendation.**

## Event table
- **Chinese New Year:** travelchinaguide.com.
- **Diwali:** when-is.com for 2006–09 and calendarific.com for 2010–25. 2024 is recorded as Oct 31; some calendars give Nov 1.
- CNY 2006 falls before the gold data starts, and Diwali 2026 is after it ends. Both were dropped, leaving 40 events.

## Numbers (bp per 15-trading-day window)
```
reference 15-day blocks: 279   gross +61.1 (sd 425)   net +27.9
CNY     n 20   gross +166.1   net +131.3   up 60%   minus reference +105.0  t +1.24
DIWALI  n 20   gross  +89.5   net  +54.5   up 60%   minus reference  +28.5  t +0.22
both    n 40   gross +127.8   net  +92.9   up 60%   minus reference  +66.7  t +0.78
eras (both):  2006-12 +186 vs ref +109   2013-19 +42 vs ref -10   2020-26 +162 vs ref +86
```

## Read it plainly
- **Gold did rise into both festivals on average.** The run-up into Chinese New Year was +105 bp above an ordinary 15-day window, and it was above reference in all three eras.
- **None of it can be told apart from noise.** A 15-day gold window has a standard deviation of about 425 bp. With 20 events the best t is 1.24, far from the 194 bp detectable effect the pre-registration said was needed.
- **Single years dominate:**
  - Diwali 2008 was −1,583 bp (the crisis).
  - Diwali 2025 was +1,361 bp.
  - CNY 2016 was +923 bp.
- Nothing is claimed. This test was registered so the record is complete. It was never able to confirm a realistic seasonal effect.
