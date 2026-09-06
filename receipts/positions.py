"""Rebuild positions from a raw swap log.

The whole point of this file is the difference between three states that
leaderboards collapse into one number:

    CLOSED      the position is gone. profit or loss is real.
    OPEN        still held. any "profit" here is a quote, not money.
    INCOMPLETE  we saw a sell without the matching buy, or the history is
                left-censored. it cannot be scored either way.

Anything that treats OPEN as profit is measuring a bag, not a trader.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# Stablecoins and wrapped native assets are the quote side of a trade, never
# the position itself. A swap between two quote assets is not a trade we score.
QUOTE_TOKENS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC (solana)
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT (solana)
    "So11111111111111111111111111111111111111112",   # wrapped SOL
}


@dataclass
class Position:
    trader: str
    token: str
    buy_count: int = 0
    sell_count: int = 0
    bought_qty: float = 0.0
    sold_qty: float = 0.0
    remaining_qty: float = 0.0
    buy_usd: float = 0.0
    sell_usd: float = 0.0
    realized_cost_usd: float = 0.0
    realized_pnl_usd: float = 0.0
    first_buy_at: str | None = None
    last_event_at: str | None = None
    incomplete: bool = False
    _open_cost: float = field(default=0.0, repr=False)

    @property
    def status(self) -> str:
        if self.incomplete:
            return "INCOMPLETE"
        return "OPEN" if self.remaining_qty > 0 else "CLOSED"

    @property
    def roi(self) -> float | None:
        if self.realized_cost_usd <= 0:
            return None
        return self.realized_pnl_usd / self.realized_cost_usd

    @property
    def multiple(self) -> float | None:
        if self.realized_cost_usd <= 0:
            return None
        return self.sell_usd / self.realized_cost_usd


def _apply_buy(p: Position, qty: float, usd: float, ts: str) -> None:
    if qty <= 0 or usd <= 0:
        p.incomplete = True
        return
    p.buy_count += 1
    p.bought_qty += qty
    p.remaining_qty += qty
    p._open_cost += usd
    p.buy_usd += usd
    p.first_buy_at = p.first_buy_at or ts


def _apply_sell(p: Position, qty: float, usd: float) -> None:
    # Average cost. Selling more than we ever saw bought means the history is
    # incomplete, not that the trader printed money out of nothing.
    if qty <= 0 or usd <= 0 or p.remaining_qty <= 0 or qty > p.remaining_qty * 1.001:
        p.incomplete = True
        return
    avg_cost = p._open_cost / p.remaining_qty
    cost = avg_cost * qty
    p.sell_count += 1
    p.sold_qty += qty
    p.sell_usd += usd
    p.realized_cost_usd += cost
    p.realized_pnl_usd += usd - cost
    p.remaining_qty -= qty
    p._open_cost -= cost
    if p.remaining_qty <= max(1e-12, p.bought_qty * 1e-9):
        p.remaining_qty = 0.0
        p._open_cost = 0.0


def rebuild(db: Path, trader: str | None = None) -> list[Position]:
    """Replay every swap in time order and return one Position per (trader, token)."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    where, args = ("WHERE trader = ?", (trader,)) if trader else ("", ())
    rows = conn.execute(
        f"SELECT * FROM swaps {where} ORDER BY trader, ts, swap_id", args).fetchall()
    censored = {r["trader"] for r in conn.execute(
        "SELECT trader FROM traders WHERE history_complete = 0")}
    conn.close()

    book: dict[tuple[str, str], Position] = {}
    for r in rows:
        in_quote = r["in_token"] in QUOTE_TOKENS
        out_quote = r["out_token"] in QUOTE_TOKENS
        if in_quote == out_quote:
            continue                      # quote-to-quote or token-to-token: unassignable
        token = r["out_token"] if in_quote else r["in_token"]
        key = (r["trader"], token)
        p = book.setdefault(key, Position(trader=r["trader"], token=token))
        p.last_event_at = r["ts"]
        # The USD paid and the USD received are not always the same number.
        # Using one for both sides quietly corrupts the cost basis.
        if in_quote:
            usd = float(r["usd_in"] or r["usd_out"] or 0)
            _apply_buy(p, float(r["out_amount"] or 0), usd, r["ts"])
        else:
            usd = float(r["usd_out"] or r["usd_in"] or 0)
            _apply_sell(p, float(r["in_amount"] or 0), usd)

    for p in book.values():
        if p.trader in censored:
            p.incomplete = True
    return list(book.values())
