# Boros Release Guidance

This file summarizes what still needs to be done before Boros experimental
support can be released with confidence.

## Ready To Expose

These pieces are ready to expose as experimental functionality:

- Two-leg Boros spread backtests
- Four-leg style experiments with synthetic perp funding cashflows
- Parameterized execution mode selection
- Full execution diagnostics and source-selection reporting

## Suggested Public API Posture

Publicly document Boros as:

- `experimental`
- `taker-only`
- suitable for research and regression testing
- not yet a protocol-perfect full matching engine

## Remaining Gaps Before A Strong Experimental Release

### Must Have

- Freeze a regression baseline for:
  - `72_boros_funding_convergence.py`
  - `77_boros_convergence_with_perp_funding.py`
  - `78_boros_full_execution_compare.py`
- Add one release test that verifies the recommended mode matrix does not drift
  materially.
- Document which execution mode should be considered default and why.

### Should Have

- Add a single command or script that regenerates the Boros mode comparison
  outputs for release validation.
- Add a short troubleshooting section for missing event files or mismatched
  market keys.
- Clarify in public docs that synthetic perp funding is cashflow-only, not a
  standalone perp market simulation.

### Later

- Full `TradeModule` / matching-engine replay
- Full maker queue simulation
- Standalone perp market implementation
- External liquidation and margin model

## Current Recommendation

If Boros were released today, the best release framing would be:

- Boros experimental support
- recommended high-fidelity engine:
  - `EVENT_REPLAY_FULL_PROTO`
- recommended stable baseline engine:
  - `TX_REPLAY_BEST_EXEC`
- advanced protocol replay:
  - not yet claimed

## Current Validation Entry Point

The release baseline is now checked in at:

- `samples/boros-backtest-modes/release_baseline.json`

The single-entry validation command is:

```bash
PYTHONPATH=/Users/hou/Desktop/demeter /Users/hou/Desktop/demeter/.venv/bin/python \
  /Users/hou/Desktop/demeter/samples/strategy-example/80_boros_release_validation.py
```

To regenerate the heavy baseline scenarios instead of reusing existing outputs:

```bash
PYTHONPATH=/Users/hou/Desktop/demeter /Users/hou/Desktop/demeter/.venv/bin/python \
  /Users/hou/Desktop/demeter/samples/strategy-example/80_boros_release_validation.py --rerun
```

Validation output is written to:

- `outputs/boros_release_validation/report.md`
- `outputs/boros_release_validation/validation.json`
