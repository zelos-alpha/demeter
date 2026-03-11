# Current Boros Engine Comparison

This file records the latest stable comparison between the two recommended
research engines on the real dual-market Boros dataset.

Dataset:

- `BINANCE-ETHUSDT-27FEB2026`
- `HYPERLIQUID-ETH-27FEB2026`
- Event range: `2026-01-21` to `2026-02-26`

Benchmark source:

- `outputs/boros_full_execution_compare/comparison.json`
- `outputs/boros_full_execution_diagnostics/diagnostics_report.md`

## Headline Result

`EVENT_REPLAY_FULL_PROTO` is now the best current Boros execution mode.

It improves pnl relative to `TX_REPLAY_BEST_EXEC` without a runtime penalty
large enough to block adoption.

## Comparison Table

| Engine | Runtime (s) | Final Net Value | Total PnL | Action Count | Mark Rate Model |
| --- | ---: | ---: | ---: | ---: | --- |
| `TX_REPLAY_BEST_EXEC` | 209.50 | 996.1757 | -3.8243 | 380 | `trade_vwap_proxy` |
| `EVENT_REPLAY_FULL_PROTO` | 200.70 | 1000.8072 | +0.8072 | 372 | `event_window_twap_proto` |

Delta of `EVENT_REPLAY_FULL_PROTO` vs `TX_REPLAY_BEST_EXEC`:

- runtime ratio: `0.9580x`
- pnl delta: `+4.6314`
- action delta: `-8`

## Full Execution Diagnostics Snapshot

Latest diagnostics after dust filtering and conservative split gating:

- final net value: `1000.8802`
- total pnl: `+0.8802`
- diagnostics rows: `180`
- source counts:
  - `orderbook_fill: 155`
  - `amm_fill: 25`
  - `split_fill: 0`
- selection reason counts:
  - `only_available_quote: 150`
  - `selected_best_all_in_rate: 30`

Interpretation:

- Most executions still have only one credible source candidate.
- Multi-option execution exists, but it is not dominant.
- Conservative split gating removed the residual `split_fill` selections with
  almost no pnl loss.

## Practical Recommendation

If you are exposing Boros execution mode as a user-facing parameter:

- safe default: `TX_REPLAY_BEST_EXEC`
- recommended high-fidelity mode: `EVENT_REPLAY_FULL_PROTO`
- dev-only modes: `BAR_APPROX`, `NEXT_TRADE`

## Release Baseline

The checked-in release baseline now lives at:

- `samples/boros-backtest-modes/release_baseline.json`

Use the single-entry validator to confirm that:

- `72_boros_funding_convergence.py`
- `77_boros_convergence_with_perp_funding.py`
- `78_boros_full_execution_compare.py`
- `79_boros_full_execution_diagnostics.py`

still match the expected research baseline before release.
