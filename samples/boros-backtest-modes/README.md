# Boros Backtest Modes

This folder documents the Boros experimental backtest modes that can be used as
parameterized engine choices when launching a Boros strategy in Demeter.

It is intended as the release-facing companion to `demeter.boros_v4`.

## Strategy Samples

Primary sample entry points:

- `samples/strategy-example/72_boros_funding_convergence.py`
  - Two-leg Boros implied-rate spread strategy
- `samples/strategy-example/77_boros_convergence_with_perp_funding.py`
  - Four-leg style experimental strategy using two Boros legs plus synthetic
    perp funding cashflows
- `samples/strategy-example/78_boros_full_execution_compare.py`
  - Benchmarks the recommended replay engines
- `samples/strategy-example/79_boros_full_execution_diagnostics.py`
  - Exports source-selection diagnostics for full execution

## Engine Modes

The Boros strategy layer currently supports four execution modes.

### 1. `BAR_APPROX`

What it does:

- Uses the current bar `mark_rate`
- Does not wait for a real trade or tx replay candidate
- Fastest mode

Use it for:

- smoke tests
- signal debugging
- very rough parameter iteration

Do not use it for:

- release-quality pnl studies
- execution-sensitive research

### 2. `NEXT_TRADE`

What it does:

- Delays signal execution to the next trade minute
- Reduces the worst artifacts from trading on empty bars

Use it for:

- a lightweight replay baseline
- quick checks that are stricter than pure bar approximation

### 3. `TX_REPLAY_BEST_EXEC`

What it does:

- Replays real tx-aligned trade candidates
- Enforces execution delay and pair skew guards
- Uses decoded Boros event trades as the main research-grade taker replay

Use it for:

- the default experimental research baseline
- two-leg and four-leg Boros studies when speed and stability matter

### 4. `EVENT_REPLAY_FULL_PROTO`

What it does:

- Uses event-window `mark_rate_full_proto`
- Builds source-aware quotes from orderbook and AMM events
- Compares all-in quotes including opening fee and execution fee
- Applies dust-quote filtering and conservative split gating

Use it for:

- the highest-fidelity Boros execution mode currently available in Demeter
- release candidate evaluation
- deciding whether deeper protocol execution work is worth it

## Current Recommendation

Recommended default for external users:

- `TX_REPLAY_BEST_EXEC` if they want the most stable, low-friction experimental
  replay mode
- `EVENT_REPLAY_FULL_PROTO` if they want the best currently available Boros
  execution fidelity

Recommended internal comparison workflow:

1. Run `TX_REPLAY_BEST_EXEC`
2. Run `EVENT_REPLAY_FULL_PROTO`
3. Compare pnl, runtime, and source diagnostics

## What To Read Next

- `CURRENT_COMPARISON.md`
- `RELEASE_GUIDANCE.md`
