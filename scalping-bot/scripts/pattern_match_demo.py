"""Pattern-matching demo: bot uses k-NN over recent windows to predict
the next horizon. Adds 'pattern_voter' to the intuition consensus.

Tests the user's hypothesis: chart at moment t has many possible
futures; library of recent similar windows narrows that distribution.
Predict + risk-manage with trailing stop.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

from scalping_bot.backtest.engine import BacktestEngine, FeeModel, Side
from scalping_bot.backtest.metrics import summarize_trades
from scalping_bot.features import load_trades_range
from scalping_bot.features.flow import aggregate_trades_to_bars
from scalping_bot.intuition import (
    IntuitionConfig,
    IntuitionEngine,
    PatternMatcher,
    TrailingStopConfig,
    TrailingStopState,
)
from scalping_bot.intuition.voters import VoterResult
from scalping_bot.live.bar_builder import OneSecondBar


SYMBOL = "BTCUSDT"
TEST_DATE = date(2025, 12, 30)
STARTING_CAPITAL = 100.0
MAX_LEVERAGE = 10.0
MAX_HOLD_BARS = 600


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


def make_pattern_voter(matcher: PatternMatcher):
    """Wrap the pattern matcher into the VoterResult-producing voter API."""
    def voter(bars: Sequence[OneSecondBar]) -> VoterResult:
        pred = matcher.predict(bars)
        if pred is None:
            return VoterResult("pattern_match", 0, 0.0, "warmup")
        return VoterResult(
            "pattern_match",
            pred.direction,
            pred.confidence,
            f"mean={pred.mean_return_bps:+.2f}bps n={pred.n_matches} conf={pred.confidence:.2f}",
        )
    return voter


def run(
    bars: list[OneSecondBar],
    *,
    use_pattern_matcher: bool,
    sigma_enter: float,
    confirm_bars: int,
    trail_cfg: TrailingStopConfig,
) -> dict:
    engine = BacktestEngine(
        starting_capital_usd=STARTING_CAPITAL,
        leverage=MAX_LEVERAGE,
        fee_model=FeeModel(),
        use_taker=False,
    )
    intuition_cfg = IntuitionConfig(
        confirm_bars=confirm_bars,
        sigma_enter=sigma_enter,
        sigma_exit=sigma_enter * 0.5,
        cooldown_bars=60,
        voter_weights={
            "flow_imbalance": 1.0,
            "momentum": 1.0,
            "vwap": 0.7,
            "trade_rate_surge": 0.5,
            "pattern_match": 1.5,  # high weight when active
        },
    )

    if use_pattern_matcher:
        matcher = PatternMatcher(
            window_bars=60,
            horizon_bars=60,
            library_capacity=14_400,
            library_age_bars=14_400,
            k=20,
        )
        # Override default voter list with our own + pattern voter
        from scalping_bot.intuition.voters import (
            flow_imbalance_voter,
            momentum_voter,
            trade_rate_surge_voter,
            vwap_voter,
        )
        voters = [
            flow_imbalance_voter,
            momentum_voter,
            vwap_voter,
            trade_rate_surge_voter,
            make_pattern_voter(matcher),
        ]
        intuition = IntuitionEngine(intuition_cfg, directional_voters=voters)
    else:
        matcher = None
        intuition = IntuitionEngine(intuition_cfg)

    stop_state: TrailingStopState | None = None
    bars_in_pos = 0

    for i in range(1, len(bars) + 1):
        window = bars[:i]
        bar = bars[i - 1]
        engine.mark_to_market(bar.close)

        if matcher is not None:
            matcher.observe(window)

        state = intuition.evaluate(window)

        if engine.position is not None and stop_state is not None:
            bars_in_pos += 1
            if stop_state.update(bar.close, trail_cfg):
                realized = stop_state.realized_profit_bps_if_stopped()
                reason = (
                    "trail_lock_profit"
                    if stop_state.breakeven_triggered and realized > 0
                    else ("trail_breakeven" if stop_state.breakeven_triggered else "initial_sl")
                )
                engine.close_position(bar.ts_bar, bar.close, reason)
                intuition.cooldown_after_trade()
                stop_state = None
                bars_in_pos = 0
            elif bars_in_pos >= MAX_HOLD_BARS:
                engine.close_position(bar.ts_bar, bar.close, "time_exit")
                intuition.cooldown_after_trade()
                stop_state = None
                bars_in_pos = 0
        elif engine.position is None and state.is_convicted:
            sigma_abs = abs(state.sigma)
            lev = 1.0 + (MAX_LEVERAGE - 1.0) * sigma_abs
            size_fraction = (lev / MAX_LEVERAGE) * 0.20
            side = Side.LONG if state.direction > 0 else Side.SHORT
            if engine.open_position(side, bar.ts_bar, bar.close, size_fraction):
                stop_state = TrailingStopState.open(side, bar.close, trail_cfg)
                bars_in_pos = 0

    if engine.position is not None:
        engine.close_position(bars[-1].ts_bar, bars[-1].close, "session_end")

    summary = summarize_trades(engine.trades, starting_capital_usd=STARTING_CAPITAL)
    reasons: dict[str, int] = {}
    for t in engine.trades:
        reasons[t.reason_close] = reasons.get(t.reason_close, 0) + 1

    return {
        "trades": summary.n_trades,
        "win_rate": summary.win_rate,
        "return_pct": summary.total_return_pct,
        "max_dd": summary.max_drawdown_pct,
        "fees": summary.total_fees_usd,
        "final": summary.final_equity_usd,
        "library_size": matcher.library_size if matcher else 0,
        "reasons": reasons,
    }


def main() -> None:
    print(f"\n=== PATTERN-MATCHING DEMO on {TEST_DATE} ===\n")
    trades = load_trades_range(Path("data/raw"), SYMBOL, TEST_DATE, TEST_DATE)
    bars_df = aggregate_trades_to_bars(trades, bar_seconds=1.0)
    bars = bars_from_polars(bars_df)
    print(f"Loaded {len(bars):,} bars\n")

    trail_cfg = TrailingStopConfig(
        initial_sl_bps=30.0,
        breakeven_trigger_bps=5.0,
        trail_distance_bps=5.0,
        initial_lock_bps=1.0,
    )

    print(f"{'Config':50s}  {'Trades':>6}  {'Win%':>6}  {'Return':>8}  "
          f"{'MaxDD':>7}  {'Final':>8}  {'Lib':>5}")
    print("-" * 110)

    # 1. Reference: trailing only, no pattern matcher
    r1 = run(bars, use_pattern_matcher=False, sigma_enter=0.50, confirm_bars=10, trail_cfg=trail_cfg)
    print(f"{'trailing only (4 voters)':50s}  {r1['trades']:>6}  "
          f"{r1['win_rate']*100:>5.1f}%  {r1['return_pct']*100:>+7.3f}%  "
          f"{r1['max_dd']*100:>6.2f}%  {r1['final']:>8.3f}  {r1['library_size']:>5}")

    # 2. Add pattern matcher
    r2 = run(bars, use_pattern_matcher=True, sigma_enter=0.50, confirm_bars=10, trail_cfg=trail_cfg)
    print(f"{'+ pattern matcher (5 voters)':50s}  {r2['trades']:>6}  "
          f"{r2['win_rate']*100:>5.1f}%  {r2['return_pct']*100:>+7.3f}%  "
          f"{r2['max_dd']*100:>6.2f}%  {r2['final']:>8.3f}  {r2['library_size']:>5}")

    # 3. Pattern matcher with looser sigma (more trades)
    r3 = run(bars, use_pattern_matcher=True, sigma_enter=0.40, confirm_bars=5, trail_cfg=trail_cfg)
    print(f"{'+ pattern matcher (loose σ=0.40 conf=5)':50s}  {r3['trades']:>6}  "
          f"{r3['win_rate']*100:>5.1f}%  {r3['return_pct']*100:>+7.3f}%  "
          f"{r3['max_dd']*100:>6.2f}%  {r3['final']:>8.3f}  {r3['library_size']:>5}")

    # 4. Pattern matcher with very tight sigma
    r4 = run(bars, use_pattern_matcher=True, sigma_enter=0.60, confirm_bars=15, trail_cfg=trail_cfg)
    print(f"{'+ pattern matcher (tight σ=0.60 conf=15)':50s}  {r4['trades']:>6}  "
          f"{r4['win_rate']*100:>5.1f}%  {r4['return_pct']*100:>+7.3f}%  "
          f"{r4['max_dd']*100:>6.2f}%  {r4['final']:>8.3f}  {r4['library_size']:>5}")

    print("\n=== INTERPRETATION ===\n")
    print(f"Trailing only:             {r1['return_pct']*100:+.3f}% return, "
          f"{r1['win_rate']*100:.1f}% WR")
    print(f"+ pattern matcher:         {r2['return_pct']*100:+.3f}% return, "
          f"{r2['win_rate']*100:.1f}% WR  (Δ {(r2['return_pct']-r1['return_pct'])*100:+.3f}pp)")

    best = max([r1, r2, r3, r4], key=lambda r: r["return_pct"])
    print(f"\nBest config:")
    print(f"  Return: {best['return_pct']*100:+.3f}%")
    print(f"  Win rate: {best['win_rate']*100:.1f}%")
    print(f"  Trades: {best['trades']}")
    print(f"  Max DD: {best['max_dd']*100:.2f}%")
    print(f"  Library size at end: {best['library_size']}")
    print(f"  Reasons:")
    for r, c in sorted(best["reasons"].items(), key=lambda x: -x[1]):
        print(f"    {r:24}  {c:>4}")


if __name__ == "__main__":
    main()
