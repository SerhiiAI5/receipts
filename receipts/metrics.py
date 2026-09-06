"""Score a trader from rebuilt positions.

Every number here is computed from CLOSED positions only. Open positions are
counted and reported separately, never folded into profit.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from .positions import Position


@dataclass
class Scorecard:
    trader: str
    closed: int
    open_positions: int
    incomplete: int
    realized_pnl_usd: float
    win_rate: float | None
    median_roi: float | None
    profit_factor: float | None
    top_winner_share: float | None
    green_week_rate: float | None
    active_days: int

    @property
    def one_hit(self) -> bool:
        """One position carrying the record is luck until it repeats."""
        return self.top_winner_share is not None and self.top_winner_share > 0.5


def _parse(ts: str | None):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def score(positions: list[Position], trader: str) -> Scorecard:
    mine = [p for p in positions if p.trader == trader]
    closed = [p for p in mine if p.status == "CLOSED" and p.realized_cost_usd > 0]
    pnls = [p.realized_pnl_usd for p in closed]
    wins = [x for x in pnls if x > 0]
    losses = [-x for x in pnls if x < 0]

    weeks: dict[str, float] = defaultdict(float)
    days = set()
    for p in closed:
        d = _parse(p.last_event_at)
        if d:
            weeks[f"{d.isocalendar()[0]}-{d.isocalendar()[1]}"] += p.realized_pnl_usd
            days.add(d.date())

    rois = [p.roi for p in closed if p.roi is not None]
    return Scorecard(
        trader=trader,
        closed=len(closed),
        open_positions=sum(p.status == "OPEN" for p in mine),
        incomplete=sum(p.status == "INCOMPLETE" for p in mine),
        realized_pnl_usd=sum(pnls),
        win_rate=(sum(x > 0 for x in pnls) / len(pnls)) if pnls else None,
        median_roi=statistics.median(rois) if rois else None,
        profit_factor=(sum(wins) / sum(losses)) if losses else (None if not wins else float("inf")),
        top_winner_share=(max(wins) / sum(wins)) if wins else None,
        green_week_rate=(sum(v > 0 for v in weeks.values()) / len(weeks)) if weeks else None,
        active_days=len(days),
    )


def rank(positions: list[Position], min_closed: int = 20) -> list[Scorecard]:
    traders = {p.trader for p in positions}
    cards = [score(positions, t) for t in traders]
    return sorted([c for c in cards if c.closed >= min_closed],
                  key=lambda c: -c.realized_pnl_usd)
