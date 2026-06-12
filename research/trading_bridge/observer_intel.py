"""
observer_intel.py — Интеллект-слой: связывает прототипы в один интерфейс.

Это «клей» между исследовательскими модулями и существующим Observer.
Watchdog/strategy/dispatcher вызывают ОДИН объект IntelLayer и получают
сводку, не зная деталей математики. Слой детерминированный, без ИИ —
живёт рядом с watchdog.py.

Что он отдаёт на каждом снапшоте:
  - flow_structure_z   : структура потока ордеров (Walsh, Том III) — айсберги
  - regime             : режим рынка (OTOC-скрэмблинг) — стоит ли торговать
  - precedent          : прогноз по памяти прецедентов (HDV, §4.2)
  - cycle_bias         : внутридневной сезонный приор (фазы, §76)
  - alerts             : новые аномалии (WORKED_ORDER и т.п.)
  - confidence_mult    : единый множитель уверенности для strategy/risk
  - ai_factor          : подсказка диспетчеру по частоте консилиума

Архитектура (как это встаёт в существующий конвейер):

    Stream → Watchdog.on_trade/on_orderbook
                 │  (копит знаки сделок, объёмы, цены)
                 ▼
            IntelLayer.update(snapshot, dirs, returns, ts)
                 │
       ┌─────────┼──────────────┬───────────────┐
       ▼         ▼              ▼               ▼
  orderflow   regime_otoc   hdv_memory      phase_cycle
   _walsh                   (recall)
       └─────────┴──────────────┴───────────────┘
                 ▼
        IntelLayer.intel()  →  strategy.evaluate (strength)
                              →  risk.position_size (size_mult)
                              →  dispatcher (ai_factor)
                              →  watchdog.alerts (WORKED_ORDER)

После закрытия сделки: IntelLayer.learn(snapshot_hv, outcome) — память
прецедентов и фазовый накопитель дописываются. Так слой САМ улучшается,
без переобучения моделей.
"""

from __future__ import annotations
from dataclasses import dataclass, field

try:
    from logger import get_logger
    log = get_logger("intel")
except Exception:
    import logging
    log = logging.getLogger("intel")

from orderflow_walsh import flow_structure_z
from regime_otoc import scrambling_rate, regime_multipliers
from hdv_memory import FeatureCodebook, PrecedentMemory
from phase_cycle import PhaseAccumulator, session_phase_bin


@dataclass
class Intel:
    flow_structure_z: float = 0.0
    structured_flow: bool = False
    regime_score: float = 0.0
    regime_note: str = ""
    precedent: dict = field(default_factory=dict)
    cycle_bias_pct: float = 0.0
    confidence_mult: float = 1.0
    size_mult: float = 1.0
    ai_factor: float = 1.0
    alerts: list = field(default_factory=list)


class IntelLayer:
    """
    Состояние слоя переживает рестарт (память прецедентов и фазы — на диске).
    Один экземпляр на тикер (как Watchdog).
    """

    def __init__(self, ticker: str, mem_path: str | None = None):
        self.ticker = ticker
        self.codebook = FeatureCodebook()
        self.memory = PrecedentMemory()
        self.cycles = PhaseAccumulator(m=8)
        self.mem_path = mem_path or f"data/{ticker}/precedents.jsonl"
        self.memory.load(self.mem_path)
        self._last_hv: int | None = None

    # ── снапшот → признаки для HDV ────────────────────────────────────────
    @staticmethod
    def _features(snapshot: dict, flow_z: float, regime: float, phase_bin: int) -> dict:
        """Снапшот watchdog + наши метрики → дискретные признаки для кодбука."""
        delta = snapshot.get("delta", 0)
        bid = snapshot.get("bid_pct", 50.0)
        act = snapshot.get("activity", 0.0)
        return {
            "trend": snapshot.get("trend", "flat"),
            "delta_sign": "+" if delta > 0 else "-" if delta < 0 else "0",
            "imbalance": int(bid / 10),                 # 0..9
            "activity": int(min(9, act * 10)),          # 0..9
            "flow_struct": 1 if flow_z > 3.0 else 0,
            "regime": int(min(9, regime * 10)),
            "phase": phase_bin,
        }

    # ── основной вызов ────────────────────────────────────────────────────
    def update(self, snapshot: dict, trade_dirs: list[int],
               returns: list[float], hour: int, minute: int) -> Intel:
        intel = Intel()

        # 1) структура потока ордеров (Walsh / Том III)
        fs = flow_structure_z(trade_dirs)
        intel.flow_structure_z = fs.get("flow_structure_z", 0.0)
        intel.structured_flow = fs.get("structured", False)
        if intel.structured_flow:
            intel.alerts.append({"type": "WORKED_ORDER",
                                 "z": intel.flow_structure_z,
                                 "detail": "структурированный поток при дельте≈0"})

        # 2) режим рынка (OTOC / Том III §III.8)
        rg = scrambling_rate(returns)
        intel.regime_score = rg.get("regime_score", 0.0)
        intel.regime_note = rg.get("note", "")
        mult = regime_multipliers(intel.regime_score)
        intel.size_mult = mult["size_mult"]
        intel.ai_factor = mult["ai_factor"]

        # 3) фазовый сезонный приор (Том I §76)
        pb = session_phase_bin(hour, minute, m=self.cycles.m)
        intel.cycle_bias_pct = self.cycles.bias(pb).get("bias_pct", 0.0)

        # 4) память прецедентов (HDV / §4.2)
        feats = self._features(snapshot, intel.flow_structure_z,
                               intel.regime_score, pb)
        hv = self.codebook.encode(feats)
        self._last_hv = hv
        intel.precedent = self.memory.recall(hv)

        # 5) единый множитель уверенности для strategy/risk.
        #    база 1.0; структурный поток в сторону тренда ↑; эффективный
        #    рынок ↓; согласие прецедента и фазы ↑.
        conf = 1.0
        if intel.structured_flow:
            conf += 0.15
        conf *= (0.7 + 0.6 * intel.regime_score)        # режим — главный фильтр
        pc = intel.precedent
        if pc.get("n", 0) >= 8:
            conf *= (0.85 + 0.3 * pc.get("win_rate", 0.5))
        intel.confidence_mult = round(max(0.4, min(1.8, conf)), 2)

        return intel

    # ── обучение после закрытия сделки ────────────────────────────────────
    def learn(self, outcome_pct: float, hour: int, minute: int):
        """
        Дописать прецедент и фазовый накопитель ИСХОДОМ закрытой сделки.
        Вызывать из risk.close_position / reflector.
        """
        if self._last_hv is not None:
            self.memory.remember(self._last_hv, outcome_pct,
                                 {"ticker": self.ticker})
            self.memory.save(self.mem_path)
        pb = session_phase_bin(hour, minute, m=self.cycles.m)
        self.cycles.observe(pb, outcome_pct)
        log.debug(f"{self.ticker}: learned outcome {outcome_pct:+.2f}% @ phase {pb}")


# ── демонстрация полного слоя ───────────────────────────────────────────────

def _demo():
    import random
    rng = random.Random(11)
    intel_layer = IntelLayer("DEMO", mem_path="/tmp/demo_precedents.jsonl")

    # «обучаем» немного истории
    for _ in range(300):
        out = rng.gauss(0.3, 0.6)
        intel_layer._last_hv = intel_layer.codebook.encode(
            {"trend": "up", "flow_struct": 1, "imbalance": 5,
             "activity": 3, "regime": 6, "phase": 6, "delta_sign": "+"})
        intel_layer.memory.remember(intel_layer._last_hv, out)
        intel_layer.cycles.observe(6, out)

    # текущий снапшот: тренд вверх, структурный поток, структурный режим
    snapshot = {"trend": "up", "delta": 50, "bid_pct": 55.0, "activity": 0.3}
    dirs = ([1] * 8 + [-1] * 8) * 8          # worked order, дельта≈0
    returns = [0.55 * 0 + rng.gauss(0, 1) for _ in range(200)]
    # сделаем returns трендовыми (память)
    ar = [0.0]
    for _ in range(199):
        ar.append(0.5 * ar[-1] + rng.gauss(0, 1))
    returns = [ar[i] - ar[i - 1] for i in range(1, len(ar))]

    it = intel_layer.update(snapshot, dirs, returns, hour=17, minute=15)
    print("IntelLayer — сводка для одного снапшота:\n")
    print(f"  поток:      structure_z={it.flow_structure_z}  "
          f"structured={it.structured_flow}")
    print(f"  режим:      score={it.regime_score}  ({it.regime_note})")
    print(f"  прецедент:  {it.precedent.get('note','—')}")
    print(f"  фаза дня:   ист. сдвиг {it.cycle_bias_pct:+.2f}%")
    print(f"  алерты:     {[a['type'] for a in it.alerts]}")
    print(f"  → confidence_mult={it.confidence_mult}  size_mult={it.size_mult}  "
          f"ai_factor={it.ai_factor}")
    print("\n  Один вызов даёт strategy (strength×conf), risk (size×size_mult),")
    print("  dispatcher (interval×ai_factor) и watchdog (WORKED_ORDER) сразу.")


if __name__ == "__main__":
    _demo()
