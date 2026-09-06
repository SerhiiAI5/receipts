"""Кто находит монеты сам, кто идёт следом, и кто кому обеспечивает выход.

Обе метрики — факты о порядке и времени сделок, а не суждения о людях.
Совпадение по времени не означает сделку друг с другом: на AMM все торгуют
против пула. Но если вы систематически покупаете в момент, когда другие ту же
монету сливают, вы поглощаете их выход.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .positions import QUOTE_TOKENS


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _load(db: Path):
    """Раскладывает лог на покупки и продажи по токенам."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    buys: dict[str, list] = defaultdict(list)
    sells: dict[str, list] = defaultdict(list)
    for r in conn.execute("SELECT * FROM swaps ORDER BY ts, swap_id"):
        in_quote = r["in_token"] in QUOTE_TOKENS
        out_quote = r["out_token"] in QUOTE_TOKENS
        if in_quote == out_quote:
            continue
        token = r["out_token"] if in_quote else r["in_token"]
        usd = float((r["usd_in"] if in_quote else r["usd_out"]) or r["usd_in"] or r["usd_out"] or 0)
        (buys if in_quote else sells)[token].append((_dt(r["ts"]), r["trader"], usd))
    conn.close()
    return buys, sells


@dataclass
class Order:
    trader: str
    clusters: int
    avg_place: float          # 0.0 — всегда первый, 1.0 — всегда последний


def entry_order(db: Path, min_traders: int = 3, min_clusters: int = 10) -> list[Order]:
    """Среднее место входа среди тех, кто зашёл в тот же токен."""
    buys, _ = _load(db)
    first: dict[str, list] = defaultdict(list)
    for token, rows in buys.items():
        seen: dict[str, datetime] = {}
        for ts, trader, _ in rows:
            seen.setdefault(trader, ts)
        if len(seen) < min_traders:
            continue
        ordered = sorted(seen.items(), key=lambda kv: kv[1])
        last = len(ordered) - 1
        for i, (trader, _) in enumerate(ordered):
            first[trader].append(i / last)
    out = [Order(t, len(v), sum(v) / len(v)) for t, v in first.items() if len(v) >= min_clusters]
    return sorted(out, key=lambda o: o.avg_place)


@dataclass
class Flow:
    trader: str
    sold_usd: float
    bought_usd: float
    sells_into_buys: float    # доля продаж, совпавших с чужой покупкой
    buys_into_sells: float    # доля покупок, совпавших с чужой продажей

    @property
    def side(self) -> float:
        """Больше нуля — чаще выходит в чужие деньги. Меньше — чаще принимает чужой выход."""
        return self.sells_into_buys - self.buys_into_sells


def exit_flow(db: Path, window_hours: int = 2, min_usd: float = 50_000) -> list[Flow]:
    buys, sells = _load(db)
    window = timedelta(hours=window_hours)
    sold = defaultdict(float); sold_hit = defaultdict(float)
    bought = defaultdict(float); bought_hit = defaultdict(float)

    for token, rows in sells.items():
        counter = buys.get(token, [])
        for ts, trader, usd in rows:
            sold[trader] += usd
            if any(abs(bt - ts) <= window and bx != trader for bt, bx, _ in counter):
                sold_hit[trader] += usd
    for token, rows in buys.items():
        counter = sells.get(token, [])
        for ts, trader, usd in rows:
            bought[trader] += usd
            if any(abs(st - ts) <= window and sx != trader for st, sx, _ in counter):
                bought_hit[trader] += usd

    out = []
    for trader in set(sold) | set(bought):
        s, b = sold.get(trader, 0.0), bought.get(trader, 0.0)
        if s + b < min_usd:
            continue
        out.append(Flow(trader, s, b,
                        sold_hit.get(trader, 0.0) / s if s else 0.0,
                        bought_hit.get(trader, 0.0) / b if b else 0.0))
    return sorted(out, key=lambda f: -f.side)
