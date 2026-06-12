"""
null_model.py — Честная нулевая модель вместо «магических порогов».

Урок из исследований (Phase 8C, Том III): любой «сигнал» обязан сравниваться
со своей СОБСТВЕННОЙ нулевой моделью под тем же протоколом. В методичке целая
ветка результатов (Ω_k, +0.98) оказалась артефактом именно потому, что null
был неправильный (биномиальный вместо per-target). Стоила эта ошибка месяцев.

В Observer сейчас аномалии ловятся жёсткими порогами:
    volume > avg * 4          (VOLUME_SPIKE)
    volume > avg * 10         (BIG_TRADE)
    bid_pct > 80              (OB_IMBAL)
Порог 4× на тихой бумаге — спам, на ликвидной — слепота. Этот модуль заменяет
порог на z-оценку/перцентиль относительно эмпирического null, построенного из
самих данных. «Аномально» = «не похоже на перемешанную/ресэмплированную
версию того же потока», а не «больше произвольного числа».

Ничего внешнего, чистый stdlib. Детерминированно при фиксированном seed.
"""

from __future__ import annotations
import math
import random
from typing import Callable, Sequence

try:
    from logger import get_logger
    log = get_logger("null_model")
except Exception:                       # standalone-режим вне Observer
    import logging
    log = logging.getLogger("null_model")


def zscore_vs_null(observed: float, null_samples: Sequence[float]) -> float:
    """z-оценка наблюдения против выборки из нулевой модели."""
    if len(null_samples) < 2:
        return 0.0
    mu = sum(null_samples) / len(null_samples)
    var = sum((x - mu) ** 2 for x in null_samples) / (len(null_samples) - 1)
    sd = math.sqrt(var) if var > 0 else 1e-12
    return (observed - mu) / sd


def percentile_vs_null(observed: float, null_samples: Sequence[float]) -> float:
    """Доля null-выборок, которые НЕ превышают наблюдение (0..1)."""
    if not null_samples:
        return 0.5
    below = sum(1 for x in null_samples if x <= observed)
    return below / len(null_samples)


def shuffle_null(stream: Sequence[float], stat: Callable[[Sequence[float]], float],
                 n: int = 200, seed: int = 0) -> list[float]:
    """
    Перемешать поток и пересчитать статистику n раз. Перемешивание убивает
    ВРЕМЕННУЮ структуру, сохраняя распределение значений — изолирует структуру.
    """
    rng = random.Random(seed)
    s = list(stream)
    out = []
    for _ in range(n):
        rng.shuffle(s)
        out.append(stat(s))
    return out


def block_bootstrap_null(stream: Sequence[float], stat: Callable[[Sequence[float]], float],
                         block: int = 8, n: int = 200, seed: int = 0) -> list[float]:
    """
    Блочный бутстрэп: ресэмплинг блоками длины `block` — сохраняет локальную
    автокорреляцию, ломает глобальную. Честнее простого shuffle для рядов,
    где есть естественная локальная зависимость (цена соседних тиков).
    """
    rng = random.Random(seed)
    s = list(stream)
    L = len(s)
    if L < block:
        return [stat(s)] * n
    out = []
    nblocks = L // block
    for _ in range(n):
        resampled = []
        for _ in range(nblocks):
            start = rng.randrange(0, L - block)
            resampled.extend(s[start:start + block])
        out.append(stat(resampled))
    return out


def anomaly_score(observed: float, null_samples: Sequence[float],
                  z_threshold: float = 3.0) -> dict:
    """
    Единая точка: насколько наблюдение аномально относительно null.
    Возвращает z, перцентиль и булев флаг — готово для алерта watchdog.
    """
    z = zscore_vs_null(observed, null_samples)
    p = percentile_vs_null(observed, null_samples)
    return {
        "z": round(z, 2),
        "percentile": round(p, 4),
        "anomalous": abs(z) >= z_threshold,
        "null_mean": round(sum(null_samples) / len(null_samples), 4) if null_samples else None,
    }


def adaptive_volume_threshold(recent_volumes: Sequence[float],
                              z_threshold: float = 3.0) -> dict:
    """
    Замена `volume > avg * 4`. Считает порог как mean + z·std по реальному
    распределению объёмов бумаги — сам подстраивается под ликвидность.
    Возвращает рекомендованный абсолютный порог + статистику.
    """
    v = [x for x in recent_volumes if x > 0]
    if len(v) < 10:
        return {"threshold": float("inf"), "note": "мало данных"}
    mu = sum(v) / len(v)
    var = sum((x - mu) ** 2 for x in v) / (len(v) - 1)
    sd = math.sqrt(var) if var > 0 else 0.0
    # объёмы лог-нормальны: считаем порог в лог-пространстве, честнее чем mean·4
    logs = [math.log(x) for x in v]
    lmu = sum(logs) / len(logs)
    lvar = sum((x - lmu) ** 2 for x in logs) / (len(logs) - 1)
    lsd = math.sqrt(lvar) if lvar > 0 else 0.0
    thr = math.exp(lmu + z_threshold * lsd)
    return {
        "threshold": round(thr, 1),
        "mean": round(mu, 1),
        "std": round(sd, 1),
        "logmean": round(lmu, 3),
        "logstd": round(lsd, 3),
        "note": f"порог = exp(μ_log + {z_threshold}·σ_log) — адаптивен к ликвидности",
    }


# ── демонстрация ────────────────────────────────────────────────────────────

def _demo():
    rng = random.Random(1)
    # лог-нормальные объёмы (как на реальном рынке)
    vols = [math.exp(rng.gauss(6, 0.8)) for _ in range(500)]
    print("1) Адаптивный порог объёма vs жёсткое avg×4:")
    avg = sum(vols) / len(vols)
    print(f"   avg×4 (текущая логика Observer) = {avg*4:.0f}")
    rec = adaptive_volume_threshold(vols)
    print(f"   адаптивный (μ_log+3σ_log)       = {rec['threshold']:.0f}")
    print(f"   -> на лог-нормальных объёмах avg×4 ловит шум; адаптивный — хвост\n")

    print("2) anomaly_score: один большой принт против null того же потока:")
    spike = max(vols) * 3
    score = anomaly_score(spike, vols)
    print(f"   спайк {spike:.0f}: z={score['z']}, перцентиль={score['percentile']}, "
          f"аномалия={score['anomalous']}")


if __name__ == "__main__":
    _demo()
