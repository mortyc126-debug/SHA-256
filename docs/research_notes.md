# Research Notes — Crypto Scalping Bot (April 2026)

Компиляция внешних данных (2025-2026) для информированного
дизайна бота. 8 параллельных поисков + анализ свежих arxiv
статей + официальных док Bybit.

---

## 1. Executive findings

### Market reality
- **AI/боты = 58% объёма crypto-торгов (январь 2026)**. Retail
  конкурирует с институциональной инфраструктурой. Edge
  требует institutional-grade data precision.
- **Scalping остаётся жизнеспособным** только для тех, кто видит
  микроструктуру быстрее и чище других (CoinAPI 2025).
- **Oct 2025 crash** показал: при стрессе ликвидности биржи
  ломаются одновременно → плечо + low liquidity = death spiral.
- **44% опубликованных стратегий не воспроизводятся** на
  новых данных (академический обзор).

### Signal structure
- **OBI (Order Book Imbalance) — реальный предиктор**, работает
  на горизонтах 50ms-5min.
- **OBI time-of-day dependent**: +10% OBI в 15:00 UTC = шум,
  тот же +10% в 03:00 UTC = сильный сигнал (Binance BTC/FDUSD
  2025). Значит **фичи регима обязательны**.
- **Feature ranking стабилен кросс-ассетно** (arxiv 2506.05764).
- **OFI (Order Flow Imbalance)** = incremental OBI, более
  чистый сигнал.

### Model architecture
- **Transformer > LSTM** для BTC prediction (Wiley 2025,
  Journal of Applied Mathematics).
- **TFT (Temporal Fusion Transformer)** — лучший в
  сравнительном исследовании Kose 2025.
- **Linear features часто бьют deep NN на LOB** (arxiv
  2506.05764: "Better inputs matter more than stacking another
  hidden layer"). Это подтверждает наш выбор Distinguisher
  v4.1 архитектуры из SHA-методички.
- **Bi-LSTM + RoBERTa sentiment** = MAPE 2.01% (Springer 2025).

### Reinforcement Learning realities
- **PPO vs DQN**: PPO быстро реагирует в trend, deep drawdown
  в choppy. DQN меньше торгует, лучше контроль drawdown, может
  пропустить momentum.
- **Binary reward ломает RL** (наш §136 findings + литература
  2025-2026 подтверждает). Нужен reward shaping:
  risk-adjusted returns с penalty за drawdown и transaction
  costs.
- **4 способа смерти RL-политики**: noise, overfitting,
  slippage, regime shifts.
- **Проблема тренировки**: realistic simulator = 3-6 месяцев
  работы. Не стартуем с RL.

### Backtesting discipline
- **Walk-forward validation** — must (rolling windows).
- **Sharpe >4 с малым числом сделок = overfit** (warning sign).
- **Equity curve без drawdown = overfit**.
- **Lookahead bias, data leakage** — три главные ловушки.

---

## 2. Bybit-specific (BTCUSDT Perpetual)

### Rate limits
- **Default**: 600 req/5s per IP.
- **WebSocket**: до 500 connections per 5 min на endpoint.
- **Critical**: market data через WebSocket НЕ считается в
  REST rate limit → гонять всё через WS.
- **ccxt Bybit**: rate limit до 400 req/s при использовании
  qualified API.

### Best practices
- Используй `X-RateLimit-Reset` и `Retry-After` headers.
- Exponential backoff обязателен на failures.
- Testnet mandatory перед mainnet.
- WebSocket для market data, REST только для orders/positions.

### Funding rates
- **Средняя ставка 2025**: 0.015% per 8h (выросло 50% с 2024).
- **Positive 92% времени** (Q3 2025) — если лонг, платишь.
- **Cost для retail $100 @ 3x leverage**: ~$0.13/день на long
  bias (funding) → 0.4% месяц только funding.

### Liquidation math
- **100x leverage**: 1% move против = liquidation.
- **20x leverage**: 5% move = liquidation.
- **5x leverage**: 20% move = liquidation (реалистичный safety).
- **3x leverage** (наш выбор): 33% move = liquidation, но
  realistic для BTC 5-минутной волатильности.

---

## 3. Стратегические решения на основе findings

### Archviz (architecture)

**Слой 1 — Feature engineering** (входит WebSocket data):
- Order Book Imbalance (top 5 levels): `(bid_vol - ask_vol) / (bid_vol + ask_vol)`
- Order Flow Imbalance (incremental per tick)
- Trade flow aggressor ratio (buy_vol / total_vol)
- Spread in bps
- Depth skew (log(bid_depth / ask_depth))
- Realized volatility (1min, 5min, 15min EWMA)
- Funding rate + delta to predicted next
- Time-of-day encoding (sin/cos of UTC hour, обязательно)
- Cross-timeframe momentum (5s, 30s, 1min, 5min returns)
- Kline body/wick ratios

Всего **20-30 фичей**. Нормализация: z-score rolling 1h.

**Слой 2 — Distinguisher classifier** (§128-129 SHA-методики):
- 10-15 linear weighted features: `score_lin = Σ phi_i × feature_i`
- 10-15 pairwise AND conditions: `if (feat_a > p90_a AND feat_b < p10_b): bonus += w_ij`
- Combined score → threshold → {long_signal, no_trade, short_signal}
- Confidence = |score - threshold| / σ(score)

Обучение: logistic regression с L1 на future return ∈ {up, down, flat}
в окне 30 секунд. Feature selection по Fisher matrix
(§139 SHA-методики).

**Слой 3 — SuperBit execution** (наши §78-79):
- σ-Kelly sizing: `position_size = confidence × σ × kelly_fraction × margin`
- σ risk brake: mean σ > threshold → freeze all new entries
- Regime filter: если realized vol > 2× historical → pause
- Hard limits: max position 30%, max daily loss 3%, max 20 trades/hour

**Слой 4 — Order router**:
- Post-only maker orders где возможно (maker rebate на Bybit)
- Taker только при high confidence + time-critical
- IOC/FOK логика
- Kill switch hook (close-all endpoint)

### Risk parameters (HARDCODED, не в конфиге для защиты от "just one more time")

```python
MAX_LEVERAGE = 3.0              # НЕ 100
MAX_POSITION_PCT = 0.30         # 30% от капитала
MAX_DAILY_LOSS_PCT = 0.03       # 3% → auto-stop
MAX_TRADES_PER_HOUR = 20
MIN_LIQUIDATION_DISTANCE = 0.10 # 10% от mark price
MAX_CONSECUTIVE_LOSSES = 3      # auto-pause
KILL_SWITCH_DRAWDOWN_PCT = 0.10 # 10% from peak = emergency stop
```

### Timeline reality

| Фаза | Длительность | Gate |
|---|---|---|
| 0. Setup + kill-switch framework | 1 неделя | — |
| 1. WebSocket data collector | 1-2 недели | 1 месяц чистых данных накоплено |
| 2. Feature engineering + EDA | 2 недели | — |
| 3. Distinguisher training | 2 недели | AUC > 0.55 на walk-forward |
| 4. SuperBit integration | 1 неделя | unit tests pass |
| 5. Realistic backtest | 2-3 недели | Sharpe > 1.5 after costs |
| 6. Paper trading (testnet) | 4-8 недель | paper matches backtest ±30% |
| 7. Micro-live ($20-30) | 4 недели | positive после 100+ trades |
| 8. Scale to $100 + | по результатам | — |

**Реалистичный timeline до реальных денег: 4-6 месяцев.**

### Expected outcomes (honest)
- **Вероятность положительного edge**: ~30% (конкурируем с AI
  botами 58% объёма; 44% стратегий не воспроизводятся).
- **Если edge есть**: 10-30% годовой return реалистично, 50%+
  нереалистично без huge risk.
- **Max drawdown будет**: 15-25% в плохой месяц гарантированно.
- **$100 wipe scenario**: возможен в первые 2 недели live.

---

## 4. Что НЕ делаем (anti-patterns)

1. **100x leverage** — быстрая смерть ($100 → 0 за 1% move)
2. **Deep learning-first** — overfit на малых данных гарантирован
3. **RL без realistic simulator** — 3-6 месяцев работы впустую
4. **Binary reward для RL** — подтверждено failure (§136 + 2026 RL research)
5. **Скипнуть paper trading** — 44% стратегий умирают в live
6. **Жёсткий long bias** — funding rate 92% positive = ежедневная плата
7. **Один таймфрейм** — OBI time-of-day dependent, нужен multi-scale
8. **Без kill switch** — баг может слить депозит за секунды
9. **Backtest на ≤1 месяце данных** — не захватит regime switches
10. **Sharpe-chasing в backtest** — Sharpe>4 = overfit flag, не победа

---

## 5. Sources (2025-2026)

### Academic (arxiv)
- [Exploring Microstructural Dynamics in Cryptocurrency Limit Order Books (2506.05764)](https://arxiv.org/html/2506.05764v2)
- [Order Book Filtration and Directional Signal Extraction at High Frequency (2507.22712)](https://arxiv.org/html/2507.22712v1)
- [Explainable Patterns in Cryptocurrency Microstructure (2602.00776)](https://arxiv.org/html/2602.00776v1)
- [Interpretable Hypothesis-Driven Trading: Walk-Forward Validation Framework (2512.12924)](https://arxiv.org/html/2512.12924v1)
- [Crypto Price Prediction using LSTM+XGBoost (2506.22055)](https://arxiv.org/html/2506.22055v1)
- [Technical Analysis Meets Machine Learning: Bitcoin Evidence (2511.00665)](https://arxiv.org/html/2511.00665v1)

### Peer-reviewed journals (2025)
- [Deep Learning Insights into Bitcoin Economic Drivers (Wiley, Köse 2025)](https://onlinelibrary.wiley.com/doi/full/10.1002/for.3258)
- [Analysis and Forecasting of Bitcoin Price Volatility: DNN, LSTM, Transformers (Wiley, Quang 2025)](https://onlinelibrary.wiley.com/doi/10.1155/jama/9089827)
- [Machine Learning Cryptocurrency Trading Optimization (Springer 2025)](https://link.springer.com/article/10.1007/s44163-025-00519-y)
- [Sentiment-Driven Cryptocurrency Forecasting (Springer 2025)](https://link.springer.com/article/10.1007/s13278-025-01463-6)
- [Reinforcement Learning Bitcoin Trading Deep Q-Network (Taylor 2025)](https://www.tandfonline.com/doi/full/10.1080/23322039.2025.2594873)
- [Funding Rate Arbitrage Risk/Return Profiles (ScienceDirect 2025)](https://www.sciencedirect.com/science/article/pii/S2096720925000818)

### Practical / exchange docs
- [Bybit API Rate Limit Rules](https://bybit-exchange.github.io/docs/v5/rate-limit)
- [Market Making with Alpha — Order Book Imbalance (hftbacktest)](https://hftbacktest.readthedocs.io/en/latest/tutorials/Market%20Making%20with%20Alpha%20-%20Order%20Book%20Imbalance.html)
- [Crypto Crash Oct 2025: Leverage Meets Liquidity (FTI)](https://www.fticonsulting.com/insights/articles/crypto-crash-october-2025-leverage-met-liquidity)

### Guides / industry
- [Is Crypto Scalping Still Profitable in 2025? (CoinAPI)](https://www.coinapi.io/blog/is-crypto-scalping-still-profitable-2025-coinapi-data-driven-insights)
- [Reinforcement Learning in Dynamic Crypto Markets (NeuralArb 2025)](https://www.neuralarb.com/2025/11/20/reinforcement-learning-in-dynamic-crypto-markets/)
- [AI Agents Dominating Crypto Trading (2026)](https://www.cryptostart.app/beyond-human-limits-how-ai-agents-are-dominating-crypto-trading-and-what-it-means-for-simulators/)
- [Funding Rate Arbitrage Strategy 2025 (Gate)](https://www.gate.com/learn/articles/perpetual-contract-funding-rate-arbitrage/2166)
- [Comprehensive 2025 Backtesting Guide (3Commas)](https://3commas.io/blog/comprehensive-2025-guide-to-backtesting-ai-trading)
- [Walk-Forward Optimization (QuantInsti)](https://blog.quantinsti.com/walk-forward-optimization-introduction/)
- [Order Flow Imbalance HFT Signal (Dean Markwick)](https://dm13450.github.io/2022/02/02/Order-Flow-Imbalance.html)
