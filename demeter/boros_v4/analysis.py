import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

from .. import Actuator, MarketInfo, MarketTypeEnum, USD
from .market import BorosMarket
from .strategy import BorosExecutionMode, FundingConvergenceStrategy


def actions_to_dataframe(actions) -> pd.DataFrame:
    rows = []
    for action in actions:
        payload = action.__dict__.copy()
        payload["action_type"] = action.action_type.name
        payload["market"] = action.market.name
        rows.append(payload)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def build_position_ledger(markets: list[BorosMarket]) -> pd.DataFrame:
    rows = []
    for market in markets:
        for position in market.positions.values():
            rows.append(
                {
                    "market": market.market_info.name,
                    "position_id": position.position_id,
                    "direction": position.direction.name,
                    "notional": position.notional,
                    "remaining_notional": position.remaining_notional,
                    "closed_notional": position.closed_notional,
                    "entry_fixed_rate": position.entry_fixed_rate,
                    "entry_time": position.entry_time,
                    "exit_time": position.exit_time,
                    "entry_upfront_fixed_cost": position.entry_upfront_fixed_cost,
                    "entry_opening_fee_cost": position.entry_opening_fee_cost,
                    "realized_pnl": position.realized_pnl,
                    "is_closed": position.is_closed,
                }
            )
    return pd.DataFrame(rows)


def build_settlement_ledger(markets: list[BorosMarket], actions_df: pd.DataFrame) -> pd.DataFrame:
    if actions_df.empty:
        return pd.DataFrame()
    close_rows = actions_df.loc[actions_df["action_type"] == "boros_close_fixed_float"].copy()
    if close_rows.empty:
        return close_rows
    return close_rows[
        [
            "market",
            "position_id",
            "timestamp",
            "close_reason",
            "pnl",
            "settlement_payment",
            "settlement_fees",
            "mark_to_maturity_value",
            "execution_fee_paid",
            "execution_timestamp",
            "execution_tx_hash",
            "execution_source",
        ]
    ].reset_index(drop=True)


def summarize_backtest(actuator: Actuator, markets: list[BorosMarket], spread_df: pd.DataFrame) -> dict:
    final_status = actuator.account_status_df.iloc[-1]
    actions_df = actions_to_dataframe(actuator.actions)
    market_balances = {}
    for market in markets:
        balance = market.get_market_balance()
        market_actions = actions_df.loc[actions_df["market"] == market.market_info.name] if not actions_df.empty else pd.DataFrame()
        total_execution_fees = (
            market_actions["execution_fee_paid"].fillna(Decimal(0)).sum()
            if not market_actions.empty and "execution_fee_paid" in market_actions.columns
            else Decimal(0)
        )
        market_balances[market.market_info.name] = {
            "realized_pnl": str(balance.realized_pnl),
            "unrealized_pnl": str(balance.unrealized_pnl),
            "net_value": str(balance.net_value),
            "position_count": int(balance.position_count),
            "total_execution_fees": str(total_execution_fees),
        }
    signal_ready_df = spread_df.loc[spread_df["signal_ready"] == True] if not spread_df.empty and "signal_ready" in spread_df.columns else spread_df
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "final_net_value": str(final_status["net_value"][""]),
        "action_count": int(len(actuator.actions)),
        "market_balances": market_balances,
        "spread_last": str(spread_df["spread"].iloc[-1]) if not spread_df.empty else "0",
        "spread_mean": str(spread_df["spread"].mean()) if not spread_df.empty else "0",
        "signal_ready_count": int(len(signal_ready_df.index)) if signal_ready_df is not None else 0,
        "signal_ready_spread_mean": str(signal_ready_df["spread"].mean()) if signal_ready_df is not None and not signal_ready_df.empty else "0",
        "signal_ready_spread_max_abs": str(signal_ready_df["spread"].abs().max()) if signal_ready_df is not None and not signal_ready_df.empty else "0",
        "total_execution_fees": str(
            actions_df["execution_fee_paid"].fillna(Decimal(0)).sum()
            if not actions_df.empty and "execution_fee_paid" in actions_df.columns
            else Decimal(0)
        ),
    }
    return summary


def export_convergence_result(
    actuator: Actuator,
    strategy: FundingConvergenceStrategy,
    output_dir: str,
    markets: list[BorosMarket],
):
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    actions_df = actions_to_dataframe(actuator.actions)
    positions_df = build_position_ledger(markets)
    settlement_df = build_settlement_ledger(markets, actions_df)
    spread_df = pd.DataFrame(strategy.spread_history)
    summary = summarize_backtest(actuator, markets, spread_df)

    actions_df.to_csv(root / "trade_ledger.csv", index=False)
    positions_df.to_csv(root / "position_ledger.csv", index=False)
    settlement_df.to_csv(root / "settlement_ledger.csv", index=False)
    spread_df.to_csv(root / "spread_timeseries.csv", index=False)
    with open(root / "summary.json", "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    report_lines = [
        "# Boros Funding Convergence Report",
        "",
        f"- final_net_value: {summary['final_net_value']}",
        f"- action_count: {summary['action_count']}",
        f"- spread_last: {summary['spread_last']}",
        f"- spread_mean: {summary['spread_mean']}",
        f"- signal_ready_count: {summary['signal_ready_count']}",
        f"- signal_ready_spread_mean: {summary['signal_ready_spread_mean']}",
        f"- signal_ready_spread_max_abs: {summary['signal_ready_spread_max_abs']}",
        f"- total_execution_fees: {summary['total_execution_fees']}",
        "",
        "## Markets",
    ]
    for market_name, payload in summary["market_balances"].items():
        report_lines.append(
            f"- {market_name}: net_value={payload['net_value']}, realized_pnl={payload['realized_pnl']}, "
            f"unrealized_pnl={payload['unrealized_pnl']}, position_count={payload['position_count']}, "
            f"total_execution_fees={payload['total_execution_fees']}"
        )
    with open(root / "report.md", "w", encoding="utf-8") as file:
        file.write("\n".join(report_lines) + "\n")


def run_funding_convergence_backtest(
    event_dir: str,
    output_dir: str,
    market_a_name: str,
    market_b_name: str,
    market_a_key: str,
    market_b_key: str,
    venue_a: str,
    venue_b: str,
    maturity: datetime,
    notional: Decimal = Decimal("100"),
    lookback: int = 60,
    entry_threshold: Decimal = Decimal("0.003"),
    exit_threshold: Decimal = Decimal("0.0008"),
    stop_loss: Decimal = Decimal("2"),
    execution_mode: BorosExecutionMode = BorosExecutionMode.TX_REPLAY_BEST_EXEC,
    min_time_to_maturity_seconds: int = 24 * 3600,
    max_signal_rate: Decimal = Decimal("2"),
    expected_holding_seconds: int | None = None,
    min_expected_edge_after_cost: Decimal = Decimal("0"),
) -> tuple[Actuator, FundingConvergenceStrategy, list[BorosMarket]]:
    market_a_info = MarketInfo(market_a_name, MarketTypeEnum.boros)
    market_b_info = MarketInfo(market_b_name, MarketTypeEnum.boros)
    market_a = BorosMarket(market_a_info)
    market_b = BorosMarket(market_b_info)
    market_a.load_event_data(event_dir=event_dir, market_key=market_a_key, venue=venue_a, maturity=maturity)
    market_b.load_event_data(event_dir=event_dir, market_key=market_b_key, venue=venue_b, maturity=maturity)

    actuator = Actuator()
    actuator.broker.add_market(market_a)
    actuator.broker.add_market(market_b)
    actuator.broker.set_balance(USD, Decimal("1000"))
    strategy = FundingConvergenceStrategy(
        market_a_info=market_a_info,
        market_b_info=market_b_info,
        notional=notional,
        lookback=lookback,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
        stop_loss=stop_loss,
        execution_mode=execution_mode,
        min_time_to_maturity_seconds=min_time_to_maturity_seconds,
        max_signal_rate=max_signal_rate,
        expected_holding_seconds=expected_holding_seconds,
        min_expected_edge_after_cost=min_expected_edge_after_cost,
    )
    actuator.strategy = strategy
    price_index = market_a.get_price_from_data().index.union(market_b.get_price_from_data().index)
    actuator.set_price(pd.DataFrame(index=price_index))
    actuator.run(print_result=False)
    export_convergence_result(actuator=actuator, strategy=strategy, output_dir=output_dir, markets=[market_a, market_b])
    return actuator, strategy, [market_a, market_b]
