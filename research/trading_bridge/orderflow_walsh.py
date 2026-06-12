"""
orderflow_walsh.py  --  a directional chain-test / Walsh detector for order flow,
ported from the SHA-256 Volume III info-theory toolkit into Observer's style
(deterministic, no AI, drop-in beside watchdog.py).

WHY (the research idea, applied):
  Observer's watchdog summarises order flow with the *linear* delta
  (buy_vol - sell_vol). Volume III showed that a coherent signal can be
  DISTRIBUTED across many scales so that every linear/threshold statistic sees
  noise, while a Walsh/chain-test sees it (IT-4.Q7D: directional chain beats
  max|z|). Informed accumulation/distribution is exactly such a signal: someone
  works an order in clustered bursts, often with delta ~ 0 (they buy and let it
  settle), so the net delta is blind but the TEMPORAL STRUCTURE is not.

WHAT this computes, on the last L (power-of-two) trade directions s in {+1,-1}:
  - WHT(s): the Walsh-Hadamard spectrum of the sign stream.
  - structure energy in mid/high Walsh orders (degree >= 2) -- multi-scale
    clustering that the delta (order-1 / mean) cannot see.
  - a SHUFFLE NULL (Phase 8C lesson: always compare to a per-input null):
    permuting the stream destroys temporal structure but keeps the delta, so
    the z-score isolates STRUCTURE beyond imbalance.

Output: a z-score 'flow_structure_z'. High (e.g. > 3) = structured/worked order
flow that the linear delta misses -- a candidate "informed trading" alert and a
strength multiplier for strategy.py, complementary to quiet_accumulation().
"""

from __future__ import annotations
import math
import random


def _wht(vec: list[float]) -> list[float]:
    """In-place fast Walsh-Hadamard transform (natural order). len must be 2^k."""
    a = list(vec)
    n = len(a)
    h = 1
    while h < n:
        for i in range(0, n, h * 2):
            for j in range(i, i + h):
                x, y = a[j], a[j + h]
                a[j], a[j + h] = x + y, x - y
        h *= 2
    return a


def _spectral_structure(signs: list[int]) -> float:
    """
    Deviation of the Walsh POWER spectrum from white (flat).  For a random +/-1
    stream the Walsh coefficients are ~iid so the power is spread evenly across
    modes; ANY temporal structure (clustering, trend, periodicity) concentrates
    power into specific Walsh modes.  We measure that concentration as the
    variance of the normalised power spectrum, excluding order 0 (= the linear
    delta), so the score is BLIND to net imbalance and sees only structure.
    This is the chi-square / hyperuniformity fingerprint (Vol III IT-1.3) on the
    Walsh basis (Vol I sec 4.4).  Higher = more structured.
    """
    n = len(signs)
    spec = _wht([float(s) for s in signs])
    power = [spec[i] * spec[i] for i in range(1, n)]   # drop order 0 (delta)
    tot = sum(power)
    if tot <= 0:
        return 0.0
    p = [x / tot for x in power]                       # normalised distribution
    mean = 1.0 / len(p)
    return sum((pi - mean) ** 2 for pi in p) / mean     # chi^2-like concentration


def flow_structure_z(directions: list[int], window: int = 128,
                     n_null: int = 200, seed: int = 0) -> dict:
    """
    directions: list of +1 (buy) / -1 (sell) (unknown -> drop or 0, filtered out).
    Returns dict with the structure z-score and the linear delta for contrast.

    The z-score compares the real stream's high-order Walsh energy against a
    shuffle null (same multiset of signs => same delta, structure destroyed).
    """
    s = [d for d in directions if d in (1, -1)]
    # use the last power-of-two block
    L = 1 << (len(s).bit_length() - 1) if s else 0
    L = min(L, window)
    if L < 16:
        return {"flow_structure_z": 0.0, "delta": sum(s), "n": len(s),
                "note": "too few directed trades"}
    block = s[-L:]
    obs = _spectral_structure(block)

    rng = random.Random(seed)
    null = []
    for _ in range(n_null):
        perm = block[:]
        rng.shuffle(perm)            # same multiset => same delta, structure gone
        null.append(_spectral_structure(perm))
    mu = sum(null) / len(null)
    var = sum((x - mu) ** 2 for x in null) / max(1, len(null) - 1)
    sd = math.sqrt(var) if var > 0 else 1e-12
    z = (obs - mu) / sd

    delta = sum(block)
    return {
        "flow_structure_z": round(z, 2),
        "delta": delta,                       # the linear view (what watchdog uses)
        "imbalance_pct": round(50 + 50 * delta / L, 1),
        "n": L,
        "structured": z > 3.0,                # structure beyond imbalance + noise
    }


# ---- self-test / demonstration ---------------------------------------------

def _demo():
    rng = random.Random(42)

    def random_flow(n):
        return [rng.choice((1, -1)) for _ in range(n)]

    def worked_order_balanced(n, burst=8):
        """Balanced overall (delta ~ 0) but CLUSTERED: alternating bursts of
        buys then sells -- an iceberg/worked order. Linear delta ~ 0."""
        out = []
        side = 1
        while len(out) < n:
            out += [side] * burst
            side *= -1
        return out[:n]

    def trending(n, p=0.62):
        return [1 if rng.random() < p else -1 for _ in range(n)]

    print("Detector: Walsh power-spectrum structure vs shuffle null (z-score)\n")
    print(f"{'stream':<28} {'delta':>7} {'imbalance%':>11} {'structure_z':>12} "
          f"{'verdict':>12}")
    cases = {
        "random flow": random_flow(256),
        "worked order (delta~0)": worked_order_balanced(256),
        "trending (imbalanced)": trending(256),
    }
    for name, flow in cases.items():
        r = flow_structure_z(flow)
        verdict = "STRUCTURED" if r["structured"] else "noise"
        print(f"{name:<28} {r['delta']:>7} {r['imbalance_pct']:>11} "
              f"{r['flow_structure_z']:>12} {verdict:>12}")
    print("\nKey point: the 'worked order' has delta ~ 0 -> watchdog's linear")
    print("delta/imbalance sees NOTHING, but the Walsh structure score flags it.")
    print("That is the Volume III thesis (distributed signal invisible to linear")
    print("statistics) applied to live order flow.")


if __name__ == "__main__":
    _demo()
