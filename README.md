# receipts

**What a trader actually realized — not what a leaderboard claims.**

A leaderboard PnL number is mostly a quote on bags somebody is still holding.
`receipts` replays a trader's raw swap log and separates the two things that
number collapses into one:

- **realized** — positions that are gone. The profit or loss is money.
- **unrealized** — positions still open. That is a price, not a result.

Zero dependencies. Python 3.10+. Nothing to install.

```bash
python cli.py rank
python cli.py card trader_43
```

```
scorecard: trader_43

closed positions   84
realized pnl       $68,507
win rate           51%
profit factor      2.07
biggest win        29% of gross profit
green weeks        65%
still open         8   (not counted as profit)
unscoreable        16   (incomplete history)

profit spread across positions and weeks, not carried by one coin.
```

## Why the numbers differ from a leaderboard

Running this over the top 100 accounts of one social trading platform:

| | |
|---|---|
| combined PnL the leaderboard shows | **+$103.8M** |
| combined realized result of the same accounts | **−$1.2M** |
| accounts green on realized PnL | **15 of 58** |
| share of their position value that is unrealized | **84%** |

Nothing here is an accusation. It is what the number measures. Rank is driven by
open positions across every chain those accounts touch. If you are picking
someone to follow, that is not the number you want.

## What it computes

Positions are rebuilt with **average cost**, replayed in time order:

- a swap from a quote asset into a token is a **buy**
- a swap from a token back into a quote asset is a **sell**
- token-to-token and quote-to-quote swaps are **skipped**, not guessed at

Every position lands in one of three states, and this is the part that matters:

| state | meaning |
|---|---|
| `CLOSED` | scored |
| `OPEN` | counted and reported, never added to profit |
| `INCOMPLETE` | a sell with no matching buy, or a left-censored history — unscoreable |

Then, from closed positions only: realized PnL, win rate, median ROI, profit
factor, the share of gross profit sitting in the single best position, and the
share of active weeks that closed green.

The last two carry most of the signal. A big number produced by one coin is luck
until it repeats. A number spread across positions and weeks is a process.

## Limitations

Read these before quoting any output.

- **A trade log is not a chain.** Deposits, airdrops and transfers are not
  trades, so a position that arrived without a buy shows up as `INCOMPLETE`
  rather than as free profit.
- **Left-censored history cannot be fixed.** If the log starts after the trader
  did, early positions are unscoreable. That is marked, not guessed.
- **Histories keep filling in.** Every scorecard is stamped with a date, because
  the same trader will produce a different number next week.
- **This measures results, not skill.** A green scorecard is not a
  recommendation and copying someone's entries is a different question entirely.

## Data

`data/sample.db` holds 45,484 real swaps across 104 traders. Handles are
replaced with `trader_NN` — the arithmetic is verifiable, the identities are not
redistributed. Bring your own export to run it on named accounts.

## License

MIT.
