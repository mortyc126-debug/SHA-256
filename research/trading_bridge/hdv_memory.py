"""
hdv_memory.py — Память прецедентов на гипервекторах (HDC / Kanerva).

Прямой потомок главного численного результата Тома I (§4.2): инверсия SHA-256
R=1 ускорилась в 1765× за счёт HDV-памяти пар (состояние → прообраз) с поиском
ближайшего по Хэммингу. Здесь та же механика, но «состояние» = снапшот
микроструктуры рынка, а «прообраз» = то, что случилось ДАЛЬШЕ.

Идея для Observer:
  Каждый снапшот рынка (тренд, дельта, дисбаланс стакана, активность,
  волатильность, структура потока, фаза дня) кодируется в один бинарный
  гипервектор D≈8192. К нему привязывается ИСХОД — движение цены через N минут.
  Сохраняем тысячи таких пар. Когда рынок сейчас выглядит как X, достаём
  k ближайших исторических ситуаций и смотрим распределение их исходов:
  «когда стакан/поток так выглядел — в 70% случаев через 15 мин был рост».

Это не предсказание из формулы, а АССОЦИАТИВНАЯ ПАМЯТЬ прецедентов —
то, что трейдер называет «насмотренностью», переведённое в математику HDC.
Свойства HDV (Том I, фаза A): псевдо-ортогональность, устойчивость к шуму,
один и тот же субстрат = и память, и распознавание.

Чистый Python (целые как битовые векторы). Реальная версия — numpy uint8.
"""

from __future__ import annotations
import json
import os
import random
from dataclasses import dataclass, field

try:
    from logger import get_logger
    log = get_logger("hdv_memory")
except Exception:
    import logging
    log = logging.getLogger("hdv_memory")

D = 8192                     # размерность гипервектора (бит)
_RNG = random.Random(20260612)


def _random_hv() -> int:
    """Случайный бинарный гипервектор как D-битное целое."""
    return _RNG.getrandbits(D)


def _hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def similarity(a: int, b: int) -> float:
    """sim = 1 − Hamming/D ∈ [0,1] (Том I, фаза A)."""
    return 1.0 - _hamming(a, b) / D


def _bundle(vectors: list[int]) -> int:
    """Бандл = побитовое голосование большинством (агрегация, Том I)."""
    if not vectors:
        return 0
    out = 0
    half = len(vectors) / 2
    for bit in range(D):
        ones = sum((v >> bit) & 1 for v in vectors)
        if ones > half:
            out |= (1 << bit)
    return out


class FeatureCodebook:
    """
    Кодовая книга: каждой (роль, значение) — свой случайный гипервектор.
    Роль ⊗ значение через XOR-привязку (bind), затем бандл по ролям.
    Непрерывные признаки квантуются в корзины (level-кодирование с
    сохранением близости соседних уровней — thermometer).
    """

    def __init__(self):
        self.roles: dict[str, int] = {}
        self.levels: dict[str, list[int]] = {}

    def _role(self, name: str) -> int:
        if name not in self.roles:
            self.roles[name] = _random_hv()
        return self.roles[name]

    def _level_vec(self, role: str, level: int, n_levels: int) -> int:
        """Уровневые гипервекторы: соседние уровни похожи (thermometer-код)."""
        if role not in self.levels:
            base = _random_hv()
            vecs = [base]
            # каждый следующий уровень отличается на ~D/(2·n) бит — плавная шкала
            flip_per = max(1, D // (2 * n_levels))
            cur = base
            for _ in range(n_levels - 1):
                cur = cur ^ _RNG.getrandbits(D) & ((1 << flip_per) - 1) << _RNG.randrange(0, D - flip_per)
                vecs.append(cur)
            self.levels[role] = vecs
        vecs = self.levels[role]
        return vecs[max(0, min(len(vecs) - 1, level))]

    def encode(self, features: dict) -> int:
        """
        features: словарь, например
          {"trend":"up", "delta_sign":"+", "imbalance":7, "activity":3,
           "vol":2, "flow_struct":1, "phase":4}
        Категориальные → bind(role, value_hv). Числовые (с суффиксом #N_levels)
        → bind(role, level_hv). Всё бандлится в один снапшот-HDV.
        """
        parts = []
        for k, v in features.items():
            if isinstance(v, str):
                parts.append(self._role(k) ^ self._role(f"{k}={v}"))
            else:
                n_levels = 10
                parts.append(self._role(k) ^ self._level_vec(k, int(v), n_levels))
        return _bundle(parts)


@dataclass
class Precedent:
    hv: int
    outcome: float          # напр. доходность через N минут, %
    meta: dict = field(default_factory=dict)


class PrecedentMemory:
    """
    Память прецедентов: хранит (снапшот-HDV → исход) и отвечает на запрос
    «что бывало, когда рынок выглядел так».
    """

    def __init__(self, capacity: int = 20000):
        self.items: list[Precedent] = []
        self.capacity = capacity

    def remember(self, hv: int, outcome: float, meta: dict | None = None):
        self.items.append(Precedent(hv, outcome, meta or {}))
        if len(self.items) > self.capacity:
            self.items.pop(0)

    def recall(self, hv: int, k: int = 16, min_sim: float = 0.55) -> dict:
        """
        k ближайших по Хэммингу прецедентов → агрегированный прогноз исхода.
        min_sim отсекает непохожие (иначе усредняем шум).
        """
        if not self.items:
            return {"n": 0, "note": "память пуста"}
        scored = [(similarity(hv, p.hv), p) for p in self.items]
        scored.sort(key=lambda t: t[0], reverse=True)
        near = [(s, p) for s, p in scored[:k] if s >= min_sim]
        if not near:
            return {"n": 0, "best_sim": round(scored[0][0], 3),
                    "note": "нет достаточно похожих прецедентов"}
        outcomes = [p.outcome for _, p in near]
        sims = [s for s, _ in near]
        wsum = sum(sims)
        # взвешенное по схожести среднее + доля положительных
        exp_outcome = sum(s * o for s, o in zip(sims, outcomes)) / wsum
        win_rate = sum(1 for o in outcomes if o > 0) / len(outcomes)
        return {
            "n": len(near),
            "expected_outcome": round(exp_outcome, 3),
            "win_rate": round(win_rate, 3),
            "best_sim": round(near[0][0], 3),
            "confidence": round(min(1.0, len(near) / k) * near[0][0], 3),
            "note": f"{len(near)} похожих прецедентов, ср. исход {exp_outcome:+.2f}%",
        }

    def save(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            for p in self.items:
                f.write(json.dumps({"hv": hex(p.hv), "o": p.outcome, "m": p.meta}) + "\n")

    def load(self, path: str):
        if not os.path.exists(path):
            return
        self.items.clear()
        with open(path) as f:
            for line in f:
                try:
                    d = json.loads(line)
                    self.items.append(Precedent(int(d["hv"], 16), d["o"], d.get("m", {})))
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass


# ── демонстрация: память учится «паттерн A → рост», потом узнаёт его ─────────

def _demo():
    cb = FeatureCodebook()
    mem = PrecedentMemory()

    # Сценарий: когда (тренд up + тихое накопление + слабый дисбаланс) →
    # через 15 мин обычно рост; когда (тренд down + спайк продаж) → падение.
    def pattern_A():
        return {"trend": "up", "flow_struct": 1, "imbalance": _RNG.randint(4, 6),
                "activity": _RNG.randint(2, 4)}
    def pattern_B():
        return {"trend": "down", "flow_struct": 0, "imbalance": _RNG.randint(7, 9),
                "activity": _RNG.randint(6, 8)}

    for _ in range(400):
        mem.remember(cb.encode(pattern_A()), outcome=_RNG.gauss(+0.8, 0.4))
        mem.remember(cb.encode(pattern_B()), outcome=_RNG.gauss(-0.7, 0.4))
    # немного шума
    for _ in range(200):
        mem.remember(cb.encode({"trend": _RNG.choice(["up", "down", "flat"]),
                                "flow_struct": _RNG.randint(0, 1),
                                "imbalance": _RNG.randint(0, 9),
                                "activity": _RNG.randint(0, 9)}),
                     outcome=_RNG.gauss(0, 0.5))

    print("Память прецедентов: 1000 ситуаций, спрашиваем про новые\n")
    qA = cb.encode(pattern_A())
    qB = cb.encode(pattern_B())
    rA = mem.recall(qA)
    rB = mem.recall(qB)
    print(f"  запрос ПАТТЕРН A (up+накопление): {rA['note']}, "
          f"win_rate={rA['win_rate']}, confidence={rA['confidence']}")
    print(f"  запрос ПАТТЕРН B (down+спайк):    {rB['note']}, "
          f"win_rate={rB['win_rate']}, confidence={rB['confidence']}")
    print("\n  -> память сама вспомнила: A склонен к росту, B к падению.")
    print("     Это §4.2 (1765×) в роли 'насмотренности' трейдера.")


if __name__ == "__main__":
    _demo()
