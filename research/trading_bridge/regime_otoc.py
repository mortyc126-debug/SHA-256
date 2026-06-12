"""
regime_otoc.py — Датчик режима рынка через скорость «скрэмблинга».

Источник: Том III §III.8 (OTOC, out-of-time-order correlator). В исследовании
OTOC мерил, как быстро SHA-256 «перемешивает» информацию (scrambling at r=24/64)
— физически обоснованная метрика с теоретическим RO-базисом, пережившая аудит
Phase 8C (0 откатов), в отличие от Ω_k.

Рыночный аналог: насколько быстро рынок «забывает» возмущение.
  - БЫСТРЫЙ скрэмблинг (автокорреляция доходностей гаснет за 1-2 лага) =
    рынок близок к случайному блужданию = эффективный = НЕэксплуатируемый.
    Тренд-следящей стратегии тут делать нечего, размер ужать.
  - МЕДЛЕННЫЙ скрэмблинг (автокорреляция/структура держится много лагов) =
    в рынке есть память = трендовость или возврат к среднему = эксплуатируемо.
    Сигналам strategy.py можно доверять больше.

Это даёт Observer то, чего у него нет: ОБЪЕКТИВНУЮ оценку «стоит ли вообще
сейчас торговать по тренду», и регулятор для ИИ-бюджета диспетчера
(структурный режим = чаще запускать консилиум).

Метрика: скорость затухания |автокорреляции| ряда знаковых доходностей +
доля «удержанной» структуры. Нормировано в [0,1]: 0 = чистый RO/случайность,
1 = сильная память. RO-базис — перемешанный ряд (даёт ≈0).
"""

from __future__ import annotations
import math
import random
from typing import Sequence

try:
    from logger import get_logger
    log = get_logger("regime_otoc")
except Exception:
    import logging
    log = logging.getLogger("regime_otoc")


def _autocorr(series: Sequence[float], lag: int) -> float:
    n = len(series)
    if n <= lag + 1:
        return 0.0
    m = sum(series) / n
    num = sum((series[i] - m) * (series[i - lag] - m) for i in range(lag, n))
    den = sum((x - m) ** 2 for x in series)
    return num / den if den > 0 else 0.0


def scrambling_rate(returns: Sequence[float], max_lag: int = 12) -> dict:
    """
    Оценка скорости скрэмблинга по ряду доходностей (или знаков движения).
    Возвращает:
      - decay_tau: за сколько лагов |автокорр| падает в e раз (большое = память),
      - retained: сумма |автокорр| по лагам 1..max_lag (структурная «масса»),
      - regime_score: [0,1], где 1 = много памяти (эксплуатируемо).
    """
    series = list(returns)
    if len(series) < max_lag + 5:
        return {"regime_score": 0.0, "decay_tau": 0.0, "retained": 0.0,
                "note": "мало данных"}

    acs = [abs(_autocorr(series, k)) for k in range(1, max_lag + 1)]
    retained = sum(acs)

    # время затухания: первый лаг, где |ac| < ac[0]/e
    a0 = acs[0] if acs[0] > 1e-6 else 1e-6
    tau = float(max_lag)
    for k, a in enumerate(acs, start=1):
        if a < a0 / math.e:
            tau = float(k)
            break

    # RO-базис: перемешанный ряд должен дать retained ≈ статистический шум.
    # нормируем retained на ожидание шума ~ max_lag/sqrt(N)
    noise = max_lag / math.sqrt(len(series))
    regime_score = max(0.0, min(1.0, (retained - noise) / (max_lag * 0.3)))

    return {
        "regime_score": round(regime_score, 3),
        "decay_tau": round(tau, 2),
        "retained": round(retained, 3),
        "ac1": round(acs[0], 3),
        "note": _label(regime_score),
    }


def _label(score: float) -> str:
    if score < 0.15:
        return "эффективный (≈случайное блуждание) — тренду не доверять, размер ↓"
    if score < 0.45:
        return "слабая память — обычный режим"
    return "структурный режим (память держится) — сигналам доверять ↑, ИИ чаще"


def regime_multipliers(score: float) -> dict:
    """
    Перевод режима в конкретные ручки Observer:
      - size_mult: множитель размера позиции (эффективный рынок → меньше),
      - ai_factor: множитель интервала диспетчера (структурный → чаще, factor<1).
    """
    size_mult = round(0.6 + 0.7 * score, 2)            # 0.6..1.3
    ai_factor = round(1.6 - 1.1 * score, 2)            # 1.6 (тихо) .. 0.5 (горячо)
    return {"size_mult": size_mult, "ai_factor": ai_factor}


# ── демонстрация ────────────────────────────────────────────────────────────

def _demo():
    rng = random.Random(7)

    def random_walk(n):
        return [rng.gauss(0, 1) for _ in range(n)]

    def trending(n, phi=0.55):
        # AR(1) с положительной памятью (тренд)
        out = [0.0]
        for _ in range(n - 1):
            out.append(phi * out[-1] + rng.gauss(0, 1))
        return [out[i] - out[i - 1] for i in range(1, len(out))]

    def mean_revert(n, phi=-0.5):
        out = [0.0]
        for _ in range(n - 1):
            out.append(phi * out[-1] + rng.gauss(0, 1))
        return out

    print("Датчик режима (scrambling): regime_score 0=случайность, 1=память\n")
    print(f"{'ряд':<22} {'regime':>7} {'tau':>5} {'retained':>9} {'ручки Observer'}")
    for name, series in [("случайное блуждание", random_walk(400)),
                         ("трендовый AR(1)+", trending(400)),
                         ("возврат к среднему", mean_revert(400))]:
        r = scrambling_rate(series)
        m = regime_multipliers(r["regime_score"])
        print(f"{name:<22} {r['regime_score']:>7} {r['decay_tau']:>5} "
              f"{r['retained']:>9} size×{m['size_mult']} ai×{m['ai_factor']}")
    print("\n  -> случайный рынок: размер ужимается, ИИ реже. Структурный:")
    print("     размер растёт, консилиум чаще. Объективно, не на глаз.")


if __name__ == "__main__":
    _demo()
