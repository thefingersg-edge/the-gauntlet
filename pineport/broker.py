"""A broker emulator that follows TradingView's default strategy execution model.

The defaults being reproduced (all of them are Pine's out-of-the-box settings,
and each one changes results if you get it wrong):

``calc_on_every_tick = false``
    The script body runs once, at the close of each bar. Signals therefore use
    only closed-bar information.

``process_orders_on_close = false``
    Orders submitted at the close of bar *i* are live from bar *i+1*. A market
    entry fills at the open of bar *i+1*, never at the close of bar *i*. This
    single bar of latency is the most common source of an over-optimistic
    Python port.

``pyramiding = 0``
    At most one entry in a given direction. A same-direction entry order while
    already in that position is rejected outright. An opposite-direction entry
    reverses: it closes the open position and opens a new one, in one fill.

Stop orders
    A stop attached via ``strategy.exit`` at the close of bar *i* is live during
    bar *i+1*. Within a bar it fills at the stop price, unless the bar gapped
    through it, in which case it fills at the open. Because the position is only
    known to the script at the close of the entry bar, the entry bar itself has
    no protective stop -- a real characteristic of the original, not an
    approximation.

Intrabar path
    OHLC bars do not say whether the high or the low came first. This engine
    only ever has one stop live at a time, so the ambiguity never has to be
    resolved and no optimistic assumption is smuggled in.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd

LONG = 1
SHORT = -1


@dataclass
class Trade:
    """One completed round trip."""
    direction: int
    qty: float
    entry_bar: int
    entry_time: pd.Timestamp
    entry_price: float
    exit_bar: int = -1
    exit_time: pd.Timestamp | None = None
    exit_price: float = np.nan
    exit_reason: str = ""
    pnl: float = np.nan
    return_pct: float = np.nan
    bars_held: int = 0
    mae: float = 0.0          # worst unrealised loss, in currency
    mfe: float = 0.0          # best unrealised gain, in currency
    equity_at_entry: float = np.nan

    @property
    def side(self) -> str:
        return "long" if self.direction == LONG else "short"


@dataclass
class _PendingEntry:
    direction: int
    qty: float
    comment: str = ""


@dataclass
class BrokerConfig:
    initial_capital: float = 4000.0
    point_value: float = 1.0
    #: commission charged per contract per side, in account currency
    commission_per_contract: float = 0.0
    #: commission charged as a fraction of notional per side (0.0002 == 2bp)
    commission_pct: float = 0.0
    #: adverse price adjustment applied to every fill, in price points
    slippage_points: float = 0.0


class PineBroker:
    """Stateful order book + position ledger driven one bar at a time."""

    def __init__(self, config: BrokerConfig | None = None):
        self.cfg = config or BrokerConfig()
        self.position_size: float = 0.0      # signed; qty in contracts
        self.entry_price: float = np.nan
        self.open_trade: Trade | None = None
        self.trades: list[Trade] = []

        self._pending_entry: _PendingEntry | None = None
        self._active_stop: float | None = None
        self._active_limit: float | None = None

        self.realised_pnl: float = 0.0
        self.equity_curve: list[float] = []
        self.position_history: list[float] = []
        self._fills_this_bar: list[str] = []

    # -- introspection used by the strategy body ---------------------------

    @property
    def equity(self) -> float:
        """Pine ``strategy.equity`` = initial capital + net profit + open profit.

        Callers must have marked the bar to market first (``mark_to_market``).
        """
        return self.cfg.initial_capital + self.realised_pnl + self._open_pnl

    @property
    def open_trades(self) -> int:
        return 1 if self.position_size != 0 else 0

    def opentrades_entry_price(self) -> float:
        """Pine ``strategy.opentrades.entry_price(n)``.

        With ``pyramiding = 0`` there is never more than one open trade, so
        index 0 and index ``strategy.opentrades - 1`` refer to the same fill.
        The original script uses both forms interchangeably; here they collapse
        to one value, which is faithful for this configuration.
        """
        return self.entry_price if self.position_size != 0 else np.nan

    # -- order submission (called at bar close) ----------------------------

    def submit_entry(self, direction: int, qty: float, comment: str = "") -> None:
        """Pine ``strategy.entry`` -- a market order for the next bar's open.

        Rejected when it would add to an existing position in the same
        direction, because ``pyramiding = 0``.
        """
        if qty is None or not np.isfinite(qty) or qty <= 0:
            return
        if self.position_size != 0 and np.sign(self.position_size) == direction:
            return  # pyramiding = 0 -> same-direction entry rejected
        self._pending_entry = _PendingEntry(direction, float(qty), comment)

    def cancel_entry(self) -> None:
        """Pine ``strategy.cancel`` -- drop an unfilled entry order."""
        self._pending_entry = None

    def set_exit(self, stop: float | None = None, limit: float | None = None) -> None:
        """Pine ``strategy.exit`` -- arm protective orders for the next bar."""
        self._active_stop = None if stop is None or not np.isfinite(stop) else float(stop)
        self._active_limit = None if limit is None or not np.isfinite(limit) else float(limit)

    def clear_exit(self) -> None:
        self._active_stop = None
        self._active_limit = None

    # -- bar processing ----------------------------------------------------

    def process_bar(self, i: int, ts: pd.Timestamp, o: float, h: float,
                    l: float, c: float) -> list[str]:
        """Execute everything the broker does *during* bar ``i``.

        Called before the strategy body evaluates bar ``i``'s close, so the
        strategy always sees a position state that already reflects this bar's
        fills -- the same ordering Pine uses.
        """
        self._fills_this_bar = []

        # 1. Market entries queued at the previous close fill at this open.
        if self._pending_entry is not None:
            self._fill_entry(self._pending_entry, i, ts, o)
            self._pending_entry = None

        # 2. Protective orders armed at the previous close are live this bar.
        elif self.position_size != 0:
            self._check_protective_orders(i, ts, o, h, l)

        # 3. Mark the (possibly new) position to this bar's close.
        self._update_excursions(h, l)
        return self._fills_this_bar

    def mark_to_market(self, c: float) -> None:
        """Update open P&L and append to the equity curve at the bar close."""
        self._mark_price = c
        self.equity_curve.append(self.equity)
        self.position_history.append(self.position_size)

    # -- internals ---------------------------------------------------------

    _mark_price: float = np.nan

    @property
    def _open_pnl(self) -> float:
        if self.position_size == 0 or not np.isfinite(self._mark_price):
            return 0.0
        return ((self._mark_price - self.entry_price)
                * self.position_size * self.cfg.point_value)

    def _slip(self, price: float, direction: int) -> float:
        """Move a fill against us by the configured slippage."""
        return price + direction * self.cfg.slippage_points

    def _commission(self, price: float, qty: float) -> float:
        return (self.cfg.commission_per_contract * abs(qty)
                + self.cfg.commission_pct * abs(price * qty * self.cfg.point_value))

    def _fill_entry(self, order: _PendingEntry, i: int, ts: pd.Timestamp, open_px: float) -> None:
        fill = self._slip(open_px, order.direction)

        # An opposite-direction entry reverses: close first, at the same price.
        if self.position_size != 0 and np.sign(self.position_size) != order.direction:
            self._close_position(i, ts, open_px, "reverse")

        self.clear_exit()
        self.position_size = order.direction * order.qty
        self.entry_price = fill
        self.realised_pnl -= self._commission(fill, order.qty)
        self.open_trade = Trade(
            direction=order.direction, qty=order.qty, entry_bar=i,
            entry_time=ts, entry_price=fill,
            equity_at_entry=self.cfg.initial_capital + self.realised_pnl,
        )
        self._fills_this_bar.append(f"entry {order.direction:+d} @ {fill:.2f}")

    def _check_protective_orders(self, i: int, ts: pd.Timestamp, o: float,
                                 h: float, l: float) -> None:
        long = self.position_size > 0
        stop, limit = self._active_stop, self._active_limit

        if long:
            # A gap through the stop fills at the open, not at the stop price.
            if stop is not None and l <= stop:
                px = min(o, stop) if o <= stop else stop
                self._close_position(i, ts, px, "stop")
                return
            if limit is not None and h >= limit:
                px = max(o, limit) if o >= limit else limit
                self._close_position(i, ts, px, "limit")
                return
        else:
            if stop is not None and h >= stop:
                px = max(o, stop) if o >= stop else stop
                self._close_position(i, ts, px, "stop")
                return
            if limit is not None and l <= limit:
                px = min(o, limit) if o <= limit else limit
                self._close_position(i, ts, px, "limit")
                return

    def _close_position(self, i: int, ts: pd.Timestamp, price: float, reason: str) -> None:
        if self.position_size == 0 or self.open_trade is None:
            return
        direction = int(np.sign(self.position_size))
        fill = self._slip(price, -direction)
        qty = abs(self.position_size)

        pnl = (fill - self.entry_price) * self.position_size * self.cfg.point_value
        pnl -= self._commission(fill, qty)

        t = self.open_trade
        t.exit_bar = i
        t.exit_time = ts
        t.exit_price = fill
        t.exit_reason = reason
        t.pnl = pnl
        t.bars_held = i - t.entry_bar
        notional = abs(t.entry_price * qty * self.cfg.point_value)
        t.return_pct = 100.0 * pnl / notional if notional else np.nan

        self.trades.append(t)
        self.realised_pnl += pnl
        self.position_size = 0.0
        self.entry_price = np.nan
        self.open_trade = None
        self.clear_exit()
        self._fills_this_bar.append(f"exit ({reason}) @ {fill:.2f}")

    def _update_excursions(self, h: float, l: float) -> None:
        t = self.open_trade
        if t is None:
            return
        pv = self.cfg.point_value
        if t.direction == LONG:
            t.mfe = max(t.mfe, (h - t.entry_price) * t.qty * pv)
            t.mae = min(t.mae, (l - t.entry_price) * t.qty * pv)
        else:
            t.mfe = max(t.mfe, (t.entry_price - l) * t.qty * pv)
            t.mae = min(t.mae, (t.entry_price - h) * t.qty * pv)

    # -- results -----------------------------------------------------------

    def force_close(self, i: int, ts: pd.Timestamp, price: float) -> None:
        """Close any open position at the end of the run, so metrics are complete."""
        if self.position_size != 0:
            self._close_position(i, ts, price, "end_of_data")

    def trades_frame(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame(columns=[f.name for f in Trade.__dataclass_fields__.values()])
        df = pd.DataFrame([asdict(t) for t in self.trades])
        df["side"] = np.where(df["direction"] == LONG, "long", "short")
        return df
