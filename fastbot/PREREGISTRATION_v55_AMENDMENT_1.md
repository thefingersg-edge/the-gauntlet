# PREREGISTRATION v55, Amendment 1: connector change (2026-10-16)

Written 2026-10-16, after two forward release days (2026-10-02 payrolls, 2026-10-14 CPI), both recorded `missed`. No consensus figure has been recorded with status `ok`, and none has been joined to any return.

## What changed
- **Connector.** The tvremix MCP ("TradingView_AI", `get_economic_calendar`) is being retired. Pulls now come from TradingView's official MCP (https://mcp.tradingview.com/mcp), tool `mcp-tv-get-economic-calendar`, called with `countries="US"`, `min_importance=1`, and `date_from`/`date_to` covering the release day (UTC).
- **Recorder.** scripts/record_consensus.py v1.0 → v1.1.
  - v1.0 sha256: `13a999282b683ba8c0ddaf545e0b9e3594e7a15e689a58748ef6fe36845de8b2`
  - v1.1 sha256: `749db6dfbe853c70c0673f16897372bc449c647831dc1d97e47a0758a69f30eb`
  - v1.1 reads the official MCP's `{"result": [...]}` envelope as well as tvremix's `{"data": {"events": [...]}}`. The event fields used (title, country, date, forecast, actual, previous, unit) and the row logic are unchanged.
  - v1.1 exits with an error on a raw file of unknown shape, or with no US event on its day. v1.0 would have appended nothing and said so only in passing.
  - v1.1 takes `--pulled-utc <ISO>`: the real pull time, for a raw file that reaches the Mac after it was pulled (see "A pull the folder could not receive" below). Every pull time, given or taken from the file's mtime, must fall on the raw file's own date at or after 08:30 ET, or the file is refused.

## Why this is the same source, not another vendor
- Both connectors serve TradingView's own economic calendar. Section 4's "not patched from another vendor" rule is therefore not triggered. The primary titles ("Inflation Rate MoM", "Non Farm Payrolls") are identical in both.
- The `forecast`, `actual` and `previous` fields keep the same units (payrolls in thousands; the official MCP also carries `*Raw` fields in full units, which are not used).

## A pull the folder could not receive
- Since 2026-10-14, scheduled runs have sometimes started without the research folder, although the task lists it. Such a run first asks for the folder again. If it still cannot reach it, it **still pulls the calendar on the release day**, keeps the response unedited, notes the UTC time of the pull, and sends Dave the raw file and the pull time.
- That file is recorded later, unchanged, as data/v55/raw/<date>.json with `--pulled-utc <the noted time>`. The record is the release-day pull; only its arrival on the Mac is late. This is not a back-fill: the recorder refuses any pull time that is not on the release day at or after 08:30 ET.
- If no release-day pull exists at all, the day is `missed`, as before.

## What did not change
- **No back-fill.** The official MCP can return past dates (data since 2003). That does not change the rule: a pull is recorded only on its release day, after 08:30 ET. The `missed` rows for 2026-10-02 and 2026-10-14 stand.
- Everything else in PREREGISTRATION_v55.md (the test, horizon, failure modes, the pre-release pull) is unchanged.
