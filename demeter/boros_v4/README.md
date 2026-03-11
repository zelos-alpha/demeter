# Boros v4

`demeter.boros_v4` is an experimental Boros backtesting module for fixed-float
swap strategies.

The current implementation is designed for two use cases:

1. Two-leg Boros implied-rate spread backtests
2. Four-leg funding convergence backtests using two Boros legs plus synthetic
   perp funding cashflows

This module is usable for research and regression testing, but it is not a
protocol-perfect replay engine yet.

## Current scope

Supported today:

- Boros raw event loading from `orderbook/*.csv` and `liquidity/*.csv`
- `latestFTime`, `floating_index`, and `fee_index` recovery from Boros events
- `taker-only` event replay with `TX_REPLAY_BEST_EXEC`
- Two-market spread strategies
- Optional synthetic perp funding cashflows mounted on top of Boros positions
- Result exports for:
  - trade ledger
  - position ledger
  - settlement ledger
  - spread time series
  - perp funding ledger
  - summary JSON
  - markdown report

Not supported yet:

- a standalone perp market implementation
- maker orders, queue position, or full orderbook maintenance
- production-grade AMM replay
- liquidation or margin simulation for external perp venues
- protocol-perfect settlement fee oracle replay

## Protocol alignment notes

The current implementation intentionally follows several protocol-level Boros
practices:

- `latestFTime` is used as the time-to-maturity basis for trade recovery and
  settlement
- `floating_index` and `fee_index` are decoded from `FIndexUpdated` events
- fixed-float direction is aligned to Boros `Side`
  - `PAY_FIXED -> LONG`
  - `RECEIVE_FIXED -> SHORT`
- the public API now exposes Boros-side protocol primitives:
  - `Side`
  - `TimeInForce`
  - `Trade`
  - `Fill`

Known gaps against full protocol behavior:

- `mark_rate` in current backtests is still a traded implied-rate proxy built
  from decoded fills, not the exact protocol `markRateView` / oracle-derived
  mark rate
- the engine is still `taker-only`; maker zero-fee behavior is therefore not
  modeled yet
- settlement fee configuration is recovered from decoded index movement, not
  directly from full oracle config state
- external perp legs are cashflow-only in the four-leg experimental sample

## Sample strategies

Two sample scripts are the recommended entry points.

### 1. Two-leg Boros spread strategy

File:

- `samples/strategy-example/72_boros_funding_convergence.py`

What it does:

- Loads two Boros markets
- Trades the implied-rate spread between them
- Opens `PAY_FIXED` on the richer market and `RECEIVE_FIXED` on the cheaper
  market
- Closes when the spread mean-reverts

This sample is useful for:

- parser validation
- replay validation
- settlement validation
- relative signal research inside Boros

### 2. Four-leg funding convergence sample

File:

- `samples/strategy-example/77_boros_convergence_with_perp_funding.py`

What it does:

- Runs the same two Boros legs as above
- Loads external Binance and Hyperliquid funding histories
- Mounts those funding cashflows into the existing Boros backtest engine
- Exports a `perp_funding_ledger.csv` in addition to the Boros ledgers

This sample does not add a separate perp market. Instead, it treats perp
funding as synthetic external cashflows attached to the Boros hedge.

That makes it a practical bridge between:

- the current Boros backtesting engine
- the full four-leg funding arbitrage described by Boros

## Input data

The dual-market samples expect an event folder like:

```text
bn_hl_260121-260226/
  BINANCE-ETHUSDT-27FEB2026/
    orderbook/*.csv
    liquidity/*.csv
  HYPERLIQUID-ETH-27FEB2026/
    orderbook/*.csv
    liquidity/*.csv
```

For the funding-mounted sample, external funding histories are pulled from:

- Binance USD-M funding API
- Hyperliquid funding history API

No standalone perp market dataset is required for that sample.

## Execution modes

The Boros strategy layer currently supports these execution modes:

- `BAR_APPROX`
- `NEXT_TRADE`
- `TX_REPLAY_BEST_EXEC`
- `EVENT_REPLAY_FULL_PROTO`

For Boros convergence research:

- `TX_REPLAY_BEST_EXEC` is the stable experimental baseline
- `EVENT_REPLAY_FULL_PROTO` is the current highest-fidelity mode

Detailed mode guidance and comparison are documented in:

- `samples/boros-backtest-modes/README.md`
- `samples/boros-backtest-modes/CURRENT_COMPARISON.md`
- `samples/boros-backtest-modes/RELEASE_GUIDANCE.md`

## Key outputs

The convergence exports include:

- `trade_ledger.csv`
- `position_ledger.csv`
- `settlement_ledger.csv`
- `spread_timeseries.csv`
- `summary.json`
- `report.md`

If synthetic perp funding is enabled, the exports also include:

- `perp_funding_ledger.csv`

Important summary fields include:

- `final_net_value`
- `total_pnl`
- `combined_realized_pnl`
- `total_perp_funding_pnl`
- `total_opening_fees`
- `total_closing_execution_fees`
- `total_settlement_fees`
- `total_explicit_costs`

## Practical interpretation

The two sample categories answer different questions:

- `72_boros_funding_convergence.py`
  - "Do the two Boros implied-rate markets mean-revert in a tradable way?"
- `77_boros_convergence_with_perp_funding.py`
  - "What happens if we attach real external funding cashflows without building
    a standalone perp market?"

The second sample is closer to Boros's cross-exchange funding arbitrage idea,
but it is still experimental because the external perp legs are cashflow-only,
not fully simulated perp markets.
