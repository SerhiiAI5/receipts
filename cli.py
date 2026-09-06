#!/usr/bin/env python3
"""receipts — what a trader actually realized, not what a leaderboard claims.

    python cli.py card trader_07
    python cli.py rank
    python cli.py rank --min-closed 30
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from receipts.metrics import rank, score          # noqa: E402
from receipts.positions import rebuild            # noqa: E402
from receipts.report import card, table           # noqa: E402

DEFAULT_DB = Path(__file__).resolve().parent / "data" / "sample.db"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["card", "rank"])
    parser.add_argument("trader", nargs="?")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--min-closed", type=int, default=20)
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    if not args.db.exists():
        print(f"no database at {args.db}", file=sys.stderr)
        return 1

    if args.command == "card":
        if not args.trader:
            parser.error("card requires a trader")
        positions = rebuild(args.db, trader=args.trader)
        if not positions:
            print(f"no trades found for {args.trader}", file=sys.stderr)
            return 1
        print(card(score(positions, args.trader)))
    else:
        print(table(rank(rebuild(args.db), min_closed=args.min_closed), limit=args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
