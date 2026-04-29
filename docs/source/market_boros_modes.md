# Boros Backtest Modes

`demeter.boros_v4` supports multiple execution modes that should be treated as
engine parameters rather than different strategy families.

## Mode Matrix

| Mode | Intended Use | Fidelity | Speed | Recommendation |
| --- | --- | --- | --- | --- |
| `BAR_APPROX` | smoke tests, signal debugging | low | highest | dev only |
| `NEXT_TRADE` | lightweight replay baseline | low to medium | high | dev and sanity checks |
| `TX_REPLAY_BEST_EXEC` | stable experimental replay | medium | high | default experimental baseline |
| `EVENT_REPLAY_FULL_PROTO` | highest current Boros fidelity | highest | high enough | recommended high-fidelity mode |

## Current Comparison

Latest stable comparison on the real dual-market Boros dataset:

| Engine | Runtime (s) | Final Net Value | Total PnL |
| --- | ---: | ---: | ---: |
| `TX_REPLAY_BEST_EXEC` | 209.50 | 996.1757 | -3.8243 |
| `EVENT_REPLAY_FULL_PROTO` | 200.70 | 1000.8072 | +0.8072 |

Interpretation:

- `EVENT_REPLAY_FULL_PROTO` currently improves pnl materially.
- It does so without a runtime penalty large enough to reject it.
- That makes it the best candidate for the recommended high-fidelity Boros
  engine.

## Diagnostics

The full execution mode also supports source-selection diagnostics.

Current diagnostic snapshot after dust filtering and conservative split gating:

- `orderbook_fill`: 155
- `amm_fill`: 25
- `only_available_quote`: 150
- `selected_best_all_in_rate`: 30

This suggests:

- most executions still come from a single credible source
- deeper split or matching complexity should be justified by measured gains,
  not by assumption

## Recommendation

For public experimental release:

- expose `TX_REPLAY_BEST_EXEC` as the stable default
- expose `EVENT_REPLAY_FULL_PROTO` as the higher-fidelity experimental option
- keep `BAR_APPROX` and `NEXT_TRADE` documented as development utilities
