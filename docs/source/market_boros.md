# Boros Market

`demeter.boros_v4` provides experimental Boros support for fixed-float swap
backtests.

The current focus is cross-market rate research rather than full protocol or
centralized-exchange replay.

## What is supported

- Two Boros markets loaded from raw `orderbook` and `liquidity` event files
- Recovery of Boros settlement state from `FIndexUpdated`-style events
- Taker-only replay with `TX_REPLAY_BEST_EXEC`
- Two-leg Boros implied-rate spread strategies
- Four-leg style experiments where Boros legs are combined with synthetic perp
  funding cashflows

## What is not supported yet

- A standalone perp market inside Demeter
- Full maker queue simulation
- Protocol-perfect settlement fee oracle replay
- Full liquidation and margin simulation for centralized exchange perps

## Two recommended samples

### Two-leg Boros spread sample

Run:

```bash
PYTHONPATH=/path/to/demeter .venv/bin/python samples/strategy-example/72_boros_funding_convergence.py
```

This sample:

- loads Binance and Hyperliquid Boros markets
- trades the Boros implied-rate spread
- uses Boros settlement and replay only

Use it when you want to validate:

- event parsing
- settlement behavior
- Boros-only spread trading logic

### Four-leg experimental sample

Run:

```bash
PYTHONPATH=/path/to/demeter .venv/bin/python samples/strategy-example/77_boros_convergence_with_perp_funding.py
```

This sample:

- runs the same two Boros legs
- fetches Binance and Hyperliquid funding histories
- mounts funding cashflows into the existing Boros engine

This is still experimental. The external perp side is modeled as cashflow only,
not as a separate market with order fills, margin, or liquidation.

## Strategy structure

### Two-leg sample

The two-leg sample trades:

- one Boros `PAY_FIXED` leg
- one Boros `RECEIVE_FIXED` leg

It is a spread mean-reversion strategy over two Boros implied-rate markets.

### Four-leg experimental sample

The funding-mounted sample is conceptually closer to the Boros article's
cross-exchange funding arbitrage:

- Boros leg on venue A
- Boros leg on venue B
- synthetic perp funding cashflow on venue A
- synthetic perp funding cashflow on venue B

The current implementation only simulates the Boros legs as full markets. The
perp side is attached as external funding cashflow series.

## Output files

The Boros convergence exporter writes:

- `trade_ledger.csv`
- `position_ledger.csv`
- `settlement_ledger.csv`
- `spread_timeseries.csv`
- `summary.json`
- `report.md`

When synthetic funding is enabled it also writes:

- `perp_funding_ledger.csv`

## Current recommendation

If your goal is parser and settlement validation, start with the two-leg sample.

If your goal is research on Boros plus external funding carry, use the
four-leg experimental sample and treat it as a costed research prototype, not a
production-grade perp replay.
