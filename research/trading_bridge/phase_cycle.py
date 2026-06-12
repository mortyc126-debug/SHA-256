"""
phase_cycle.py — Фазовое кодирование внутридневной периодики.

Источник: Том I §76 (phase-encoding price-time series, Z/m для периодических
паттернов) + phase bits (§5): комплексная фаза несёт информацию, недоступную
вероятностным маргиналам (GHZ±-различение). Тут — мягкая, практичная версия.

Идея: у торгового дня есть устойчивая структура — открытие волатильно,
середина вялая, перед закрытием всплеск; плюс эффекты времени суток, дня недели.
Кодируем момент времени как ФАЗУ на окружности Z/m (m корзин по сессии) и
накапливаем знаковые движения как фазовые векторы e^{i·2πk/m}. Магнитуда
суммы по фазе показывает, есть ли устойчивый периодический сдвиг, а её
аргумент — в какую фазу дня смещение.

Это даёт Observer сезонный приор: «на этой бумаге последний час сессии
исторически склонен к росту» — слабый, но реальный and ортогональный тренду
сигнал, который можно подмешать в strength или в выбор времени входа.

Чистый Python, комплексные числа из stdlib.
"""

from __future__ import annotations
import cmath
import math
import random
from dataclasses import dataclass, field

try:
    from logger import get_logger
    log = get_logger("phase_cycle")
except Exception:
    import logging
    log = logging.getLogger("phase_cycle")


def session_phase_bin(hour: int, minute: int,
                      start_hour: int = 10, end_hour: int = 18,
                      m: int = 8) -> int:
    """Момент времени → корзина фазы 0..m-1 по торговой сессии."""
    total_min = (end_hour - start_hour) * 60
    if total_min <= 0:
        return 0
    elapsed = (hour - start_hour) * 60 + minute
    frac = max(0.0, min(0.999, elapsed / total_min))
    return int(frac * m)


@dataclass
class PhaseAccumulator:
    """
    Накопитель фазовых векторов по m корзинам сессии.
    Для каждой корзины храним сумму знаковых движений как комплексное
    e^{iθ}·move, где θ = 2π·bin/m. Магнитуда результанта по корзине = сила
    устойчивого сдвига, знак реальной части по фазе = направление.
    """
    m: int = 8
    bins: list = field(default_factory=list)
    counts: list = field(default_factory=list)

    def __post_init__(self):
        if not self.bins:
            self.bins = [0.0] * self.m          # суммарный знаковый move по корзине
            self.counts = [0] * self.m

    def observe(self, phase_bin: int, move_pct: float):
        b = phase_bin % self.m
        self.bins[b] += move_pct
        self.counts[b] += 1

    def bias(self, phase_bin: int) -> dict:
        """Текущий сезонный приор для данной фазы дня."""
        b = phase_bin % self.m
        if self.counts[b] < 5:
            return {"bias_pct": 0.0, "n": self.counts[b], "note": "мало истории"}
        avg = self.bins[b] / self.counts[b]
        return {"bias_pct": round(avg, 3), "n": self.counts[b],
                "note": f"корзина {b}/{self.m}: ист. сдвиг {avg:+.2f}%"}

    def periodicity_strength(self) -> dict:
        """
        Есть ли вообще периодическая структура (Walsh/phase-аналог).
        Считаем результант Σ avg_b · e^{i·2π b/m}; |результант| велик ⇒
        движения систематически сдвинуты по фазе дня, а не случайны.
        """
        active = [(b, self.bins[b] / self.counts[b]) for b in range(self.m)
                  if self.counts[b] >= 5]
        if len(active) < 3:
            return {"strength": 0.0, "note": "мало данных по фазам"}
        resultant = sum(avg * cmath.exp(1j * 2 * math.pi * b / self.m)
                        for b, avg in active)
        mag = abs(resultant)
        # нормировка на сумму |avg| (если бы все были в одной фазе)
        denom = sum(abs(avg) for _, avg in active) or 1e-9
        strength = mag / denom
        peak_phase = cmath.phase(resultant)
        peak_bin = int((peak_phase % (2 * math.pi)) / (2 * math.pi) * self.m)
        return {
            "strength": round(strength, 3),
            "peak_bin": peak_bin,
            "note": f"периодичность {strength:.2f}, пик в фазе {peak_bin}/{self.m}",
        }


# ── демонстрация ────────────────────────────────────────────────────────────

def _demo():
    rng = random.Random(3)
    m = 8
    acc = PhaseAccumulator(m=m)

    # Сценарий: последний час сессии (корзины 6,7) систематически растёт,
    # открытие (корзина 0) волатильно но без смещения, середина — шум.
    for _ in range(60):  # 60 дней
        for b in range(m):
            if b >= 6:
                move = rng.gauss(+0.25, 0.3)      # рост к закрытию
            elif b == 0:
                move = rng.gauss(0.0, 0.6)        # волатильное открытие
            else:
                move = rng.gauss(0.0, 0.2)        # вялая середина
            acc.observe(b, move)

    print("Фазовое кодирование сессии (m=8 корзин):\n")
    for b in range(m):
        bi = acc.bias(b)
        print(f"  фаза {b}/{m}: ист. сдвиг {bi['bias_pct']:+.2f}% (n={bi['n']})")
    ps = acc.periodicity_strength()
    print(f"\n  {ps['note']}")
    print("  -> система сама нашла приор 'последний час склонен к росту'.")
    print("     Слабый, ортогональный тренду сигнал для strength/тайминга.")


if __name__ == "__main__":
    _demo()
