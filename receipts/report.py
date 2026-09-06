"""Render a scorecard the way it gets published."""
from __future__ import annotations

from datetime import datetime, timezone

from .metrics import Scorecard


def usd(value: float) -> str:
    return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def _as_of() -> str:
    """Histories keep filling in, so a scorecard without a date will eventually
    contradict an older one. Always stamp it."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def card(sc: Scorecard, claimed_pnl: float | None = None) -> str:
    pf = "n/a" if sc.profit_factor is None else (
        "inf" if sc.profit_factor == float("inf") else f"{min(sc.profit_factor, 99):.2f}")
    lines = [f"scorecard: {sc.trader}", ""]
    if claimed_pnl is not None:
        lines.append(f"the leaderboard says {usd(claimed_pnl)}.")
        lines.append("here is what the trades actually did.")
        lines.append("")
    lines += [
        f"closed positions   {sc.closed}",
        f"realized pnl       {usd(sc.realized_pnl_usd)}",
        f"win rate           {_pct(sc.win_rate)}",
        f"profit factor      {pf}",
        f"biggest win        {_pct(sc.top_winner_share)} of gross profit",
        f"green weeks        {_pct(sc.green_week_rate)}",
        f"still open         {sc.open_positions}   (not counted as profit)",
        f"unscoreable        {sc.incomplete}   (incomplete history)",
        "",
    ]
    if sc.realized_pnl_usd <= 0:
        lines.append(f"down {usd(abs(sc.realized_pnl_usd))} on closed positions. "
                     f"{_pct(sc.win_rate)} of trades were green; the losses were bigger.")
    elif sc.one_hit:
        lines.append("most of the profit sits in one position. "
                     "one coin carrying a record is luck until it repeats.")
    else:
        lines.append("profit spread across positions and weeks, not carried by one coin.")
    lines += ["", f"as of {_as_of()} — rebuilt from the trade log, not a leaderboard."]
    return "\n".join(lines)


def table(cards: list[Scorecard], limit: int = 15) -> str:
    out = [f"{'trader':<16}{'realized':>12}{'closed':>8}{'WR':>6}{'PF':>7}{'top-1':>7}"]
    for sc in cards[:limit]:
        pf = "n/a" if sc.profit_factor is None else (
            "inf" if sc.profit_factor == float("inf") else f"{min(sc.profit_factor, 99):.2f}")
        out.append(f"{sc.trader[:16]:<16}{usd(sc.realized_pnl_usd):>12}{sc.closed:>8}"
                   f"{_pct(sc.win_rate):>6}{pf:>7}{_pct(sc.top_winner_share):>7}")
    green = sum(c.realized_pnl_usd > 0 for c in cards)
    out += ["", f"{green} of {len(cards)} traders are green on realized pnl.",
            f"as of {_as_of()}."]
    return "\n".join(out)


def order_table(rows, limit: int = 10) -> str:
    """Кто находит монеты сам, а кто приходит следом."""
    out = [f"{'trader':<18}{'clusters':>10}{'avg place':>12}", ""]
    for o in rows[:limit]:
        out.append(f"{o.trader[:18]:<18}{o.clusters:>10}{o.avg_place:>12.2f}")
    if len(rows) > limit:
        out += ["...", ""]
        for o in rows[-3:]:
            out.append(f"{o.trader[:18]:<18}{o.clusters:>10}{o.avg_place:>12.2f}")
    out += ["", "0.00 = always first into a coin, 1.00 = always last.",
            "random would be 0.50. nobody here is systematically early.",
            f"as of {_as_of()}."]
    return "\n".join(out)


def flow_table(rows, limit: int = 6) -> str:
    """Кто продаёт в чужие покупки, а кто принимает чужой выход."""
    head = f"{'trader':<18}{'sold':>12}{'sells into buys':>18}{'buys into sells':>18}"
    out = [head, ""]
    for f in rows[:limit]:
        out.append(f"{f.trader[:18]:<18}{usd(f.sold_usd):>12}"
                   f"{f.sells_into_buys:>17.0%}{f.buys_into_sells:>18.0%}")
    if len(rows) > limit:
        out += ["...", ""]
        for f in rows[-limit:]:
            out.append(f"{f.trader[:18]:<18}{usd(f.sold_usd):>12}"
                       f"{f.sells_into_buys:>17.0%}{f.buys_into_sells:>18.0%}")
    out += ["",
            "top rows exit while others are buying the same coin.",
            "bottom rows buy while others are selling it.",
            "timing overlap, not a direct counterparty — everyone trades the pool.",
            f"as of {_as_of()}."]
    return "\n".join(out)
