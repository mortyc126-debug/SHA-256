# Bridging the SHA-256 research into the Observer trading bot

Honest assessment of which math from METHODOLOGY / the volumes / the research
can be applied to Observer (the MOEX observation + sandbox-trading bot), plus
one working prototype.

## Applicability, ranked (no forcing)

| Research piece | Market analog | Fit | Status |
|---|---|---|---|
| **Directional chain-test / Walsh spectrum** (Vol III, Vol I §4.4) | structured order flow (icebergs/worked orders) invisible to the linear delta | **strong** | **prototype here** (`orderflow_walsh.py`) |
| **HDV memory + Hamming retrieval** (Vol I §4.2, the 1765x) | encode a microstructure snapshot as a hypervector, retrieve nearest historical analogues -> "what followed last time the tape looked like this" | strong | proposed |
| **chi^2 / min-entropy fingerprint + per-target null** (Vol III IT-1.3, Phase 8C) | replace ad-hoc thresholds (`vol > 4*avg`) with deviation from an honest null model | strong | folded into the prototype's shuffle null |
| **OTOC scrambling** (Vol III §III.8) | regime gauge: how efficient/random vs structured the tape is now -> feeds the AI-budget dispatcher and "temperature" | speculative | proposed |
| **Phase-encoding of periodicity** (Vol I §76, the trading section) | intraday seasonality as phase, Z/m hierarchy for periodic patterns | speculative | proposed |
| **Tropical/min-plus Bellman-Ford** (Vol I §36) | Viterbi/HMM regime decoding is min-plus; cross-instrument path costs | marginal | note only |
| carry / MITM / Wang / ramification / prismatic | -- | **none** | these are SHA structural attacks; no market analog, not forced |

## The prototype: `orderflow_walsh.py`

Drop-in beside `watchdog.py` (deterministic, no AI). It takes the recent
buy/sell trade-direction stream (which Observer already has in
`watchdog.on_trade`) and scores its **temporal structure** with a
Walsh-power-spectrum statistic, against a **shuffle null** (same trades, order
destroyed -> same delta, structure gone). The score is orthogonal to the delta
by construction (order-0 dropped), so it adds a NEW axis the bot lacks.

Demonstrated property (`python3 orderflow_walsh.py`):

```
stream                    delta  imbalance%  structure_z   verdict
random flow                  24      59.4         0.89      noise
worked order (delta~0)        0      50.0       287.97      STRUCTURED
trending (imbalanced)        42      66.4         0.46      noise
```

The **worked order** (balanced buys/sells worked in bursts, like an iceberg or
quiet accumulation) has delta ~ 0 -> Observer's delta and imbalance see
**nothing**, while the structure score flags it strongly. A pure trend has no
extra structure beyond its imbalance -> correctly stays quiet. This is exactly
the Vol III thesis (a distributed signal invisible to linear/threshold
statistics) applied to live order flow.

### Wiring into Observer (suggested, ~15 lines)

In `watchdog.py`, keep a rolling list of directed trades and expose the score:

```python
# in Watchdog.__init__
self._dirs = deque(maxlen=256)          # +1 buy / -1 sell

# in Watchdog.on_trade, after computing direction:
self._dirs.append(1 if direction == "buy" else -1 if direction == "sell" else 0)

# new method
def flow_structure(self):
    from orderflow_walsh import flow_structure_z
    return flow_structure_z(list(self._dirs))
```

Then:
- **Alert**: in `_check_*`, if `flow_structure()["structured"]` -> add a
  `WORKED_ORDER` alert (with the 60s cooldown already in `_add_alert`). This is
  a genuinely new anomaly class (informed/iceberg flow at delta ~ 0).
- **Strength**: in `strategy.evaluate`, when a structured-flow score aligns with
  the trend, nudge `sig.strength` up (same role as `quiet_accumulation`, but at
  tick-microstructure resolution and with a principled null).
- **Dispatcher**: feed `|structure_z|` into the "temperature" so worked-order
  episodes raise the AI-budget priority.

## Honest caveats

- Validated on **synthetic** flows (the repo has no `market.db`). The mechanism
  is correct and null-controlled, but its **predictive** value (does structured
  flow precede a move?) must be backtested on Observer's real
  `data/<TICKER>/market.db` trade tape. The hook to do that is one query +
  `flow_structure_z` over rolling windows, labelled by the next-N-minute return.
- It detects STRUCTURE, not direction. Direction still comes from
  `strategy.py`'s trend. Use this as a confidence/þalert layer, not an entry.
- Phase 8C lesson is baked in: every score is relative to its own shuffle null,
  so it cannot become the kind of basis-artifact that sank IT-6.
