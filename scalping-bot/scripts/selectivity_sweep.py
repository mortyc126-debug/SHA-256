"""Selectivity sweep — does cranking sigma_enter, confirm_bars, and
voter-unanimity get us to 90% win rate?

Hypothesis: extreme selectivity should raise win rate but collapse
trade count. Look for the knee where win rate is high enough to be
meaningful AND there are enough trades to be statistically valid.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

from scalping_bot.backtest.engine import BacktestEngine, FeeModel, Side
from scalping_bot.backtest.metrics import summarize_trades
from scalping_bot.features import load_trades_range
from scalping_bot.features.flow import aggregate_trades_to_bars
from scalping_bot.intuition import IntuitionConfig, IntuitionEngine
from scalping_bot.intuition.voters import (
    VoterResult,
    flow_imbalance_voter,
    momentum_voter,
    trade_rate_surge_voter,
    vwap_voter,
)
from scalping_bot.live.bar_builder import OneSecondBar


SYMBOL = "BTCUSDT"
TEST_DATE = date(2025, 12, 30)


def bars_from_polars(df) -> list[OneSecondBar]:
    return [
        OneSecondBar(
            ts_bar=row["ts_bar"], open=row["open"], high=row["high"], low=row["low"],
            close=row["close"], vwap=row["vwap"], volume=row["volume"],
            buy_volume=row["buy_volume"], sell_volume=row["sell_volume"],
            trade_count=row["trade_count"],
        )
        for row in df.iter_rows(named=True)
    ]


def unanimous_voter_filter(bars: Sequence[OneSecondBar]) -> int:
    """Return +1/-1 only if ALL 4 directional voters agree, else 0."""
    voters = [flow_imbalance_voter, momentum_voter, vwap_voter, trade_rate_surge_voter]
    results = [v(bars) for v in voters]
    directions = [r.direction for r in results if r.direction != 0]
    if not directions:
        return 0
    if all(d == 1 for d in directions):
        return 1
    if all(d == -1 for d in directions):
        return -1
    return 0


def run_one(
    bars: list[OneSecondBar],
    *,
    sigma_enter: float,
    confirm_bars: int,
    take_profit_bps: float,
    stop_loss_bps: float,
    max_hold_bars: int,
    require_unanimity: bool,
    leverage: float = 3.0,
) -> dict:
    engine = BacktestEngine(
        starting_capital_usd=100.0,
        leverage=leverage,
        fee_model=FeeModel(),
        use_taker=False,
    )
    intuition = IntuitionEngine(
        IntuitionConfig(
            confirm_bars=confirm_bars,
            sigma_enter=sigma_enter,
            sigma_exit=sigma_enter * 0.5,
            cooldown_bars=60,
        )
    )

    bars_in_pos = 0
    for i in range(1, len(bars) + 1):
        window = bars[:i]
        bar = bars[i - 1]
        engine.mark_to_market(bar.close)
        state = intuition.evaluate(window)

        if engine.position is not None:
            bars_in_pos += 1
            pos = engine.position
            if pos.side == Side.LONG:
                pnl_pct = (bar.close - pos.entry_price) / pos.entry_price
            else:
                pnl_pct = (pos.entry_price - bar.close) / pos.entry_price

            close_reason = None
            if pnl_pct >= take_profit_bps / 10_000:
                close_reason = "take_profit"
            elif pnl_pct <= -stop_loss_bps / 10_000:
                close_reason = "stop_loss"
            elif bars_in_pos >= max_hold_bars:
                close_reason = "time_exit"

            if close_reason:
                engine.close_position(bar.ts_bar, bar.close, close_reason)
                intuition.cooldown_after_trade()
                bars_in_pos = 0

        elif state.is_convicted:
            if require_unanimity:
                unanimous = unanimous_voter_filter(window)
                if unanimous == 0 or unanimous != state.direction:
                    continue
            side = Side.LONG if state.direction > 0 else Side.SHORT
            engine.open_position(side, bar.ts_bar, bar.close, 0.10)
            bars_in_pos = 0

    if engine.position is not None:
        engine.close_position(bars[-1].ts_bar, bars[-1].close, "session_end")

    summary = summarize_trades(engine.trades, starting_capital_usd=100.0)
    return {
        "sigma": sigma_enter,
        "confirm": confirm_bars,
        "tp": take_profit_bps,
        "sl": stop_loss_bps,
        "unan": "Y" if require_unanimity else "N",
        "trades": summary.n_trades,
        "win_rate": summary.win_rate,
        "return_pct": summary.total_return_pct,
        "final": summary.final_equity_usd,
    }


def main() -> None:
    print(f"\n=== SELECTIVITY SWEEP on {TEST_DATE} ===\n")
    trades = load_trades_range(Path("data/raw"), SYMBOL, TEST_DATE, TEST_DATE)
    bars_df = aggregate_trades_to_bars(trades, bar_seconds=1.0)
    bars = bars_from_polars(bars_df)
    print(f"Loaded {len(bars):,} bars\n")

    # Configuration grid
    configs = []

    # Section 1: vary selectivity, symmetric TP/SL
    for sigma in [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]:
        for confirm in [3, 5, 10, 20]:
            configs.append({
                "sigma_enter": sigma,
                "confirm_bars": confirm,
                "take_profit_bps": 20.0,
                "stop_loss_bps": 30.0,
                "max_hold_bars": 300,
                "require_unanimity": False,
            })

    # Section 2: extreme — asymmetric TP/SL (high win rate, big losers)
    for tp_sl in [(5, 50), (3, 100), (2, 200)]:
        configs.append({
            "sigma_enter": 0.40,
            "confirm_bars": 5,
            "take_profit_bps": tp_sl[0],
            "stop_loss_bps": tp_sl[1],
            "max_hold_bars": 300,
            "require_unanimity": False,
        })

    # Section 3: unanimous voters required
    for sigma in [0.40, 0.60]:
        for confirm in [5, 10]:
            configs.append({
                "sigma_enter": sigma,
                "confirm_bars": confirm,
                "take_profit_bps": 20.0,
                "stop_loss_bps": 30.0,
                "max_hold_bars": 300,
                "require_unanimity": True,
            })

    print(f"{'σ':>5}  {'conf':>4}  {'TP':>3}  {'SL':>3}  {'unan':>4}  "
          f"{'trades':>6}  {'win%':>6}  {'return':>8}  {'final $':>9}")
    print("-" * 80)

    best_winrate = None
    best_return = None
    for cfg in configs:
        r = run_one(bars, **cfg)
        if r["trades"] >= 10:  # only meaningful samples
            if best_winrate is None or r["win_rate"] > best_winrate["win_rate"]:
                best_winrate = r
            if best_return is None or r["return_pct"] > best_return["return_pct"]:
                best_return = r

        marker = ""
        if r["win_rate"] >= 0.75 and r["trades"] >= 10:
            marker = " ★ high WR"
        elif r["return_pct"] > 0.005 and r["trades"] >= 10:
            marker = " ✓ profitable"

        print(
            f"{r['sigma']:>5.2f}  {r['confirm']:>4}  {r['tp']:>3.0f}  {r['sl']:>3.0f}  "
            f"{r['unan']:>4}  {r['trades']:>6}  {r['win_rate']*100:>5.1f}%  "
            f"{r['return_pct']*100:>+7.3f}%  {r['final']:>9.3f}{marker}"
        )

    print("\n=== HIGHLIGHTS (10+ trades only) ===")
    if best_winrate:
        print(f"\nHighest WIN RATE: {best_winrate['win_rate']*100:.1f}%  "
              f"(σ={best_winrate['sigma']}, conf={best_winrate['confirm']}, "
              f"TP={best_winrate['tp']}, SL={best_winrate['sl']}, unan={best_winrate['unan']})")
        print(f"  → {best_winrate['trades']} trades, return {best_winrate['return_pct']*100:+.3f}%, "
              f"final ${best_winrate['final']:.3f}")
    if best_return:
        print(f"\nHighest RETURN:   {best_return['return_pct']*100:+.3f}%  "
              f"(σ={best_return['sigma']}, conf={best_return['confirm']}, "
              f"TP={best_return['tp']}, SL={best_return['sl']}, unan={best_return['unan']})")
        print(f"  → {best_return['trades']} trades, win rate {best_return['win_rate']*100:.1f}%, "
              f"final ${best_return['final']:.3f}")


if __name__ == "__main__":
    main()
