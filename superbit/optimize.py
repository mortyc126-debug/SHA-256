"""
SuperBit optimization — parallel sweep and SA comparison.
"""

import numpy as np
from typing import Tuple, Optional

from .core import ising_energy, parallel_sweep, self_tune_T, measure_sigma_from_history


def parallel_optimize(n: int, J: np.ndarray, h: np.ndarray,
                      sweeps: int = 1000, kappa: float = 3.0,
                      rng: Optional[np.random.Generator] = None
                      ) -> Tuple[float, np.ndarray, np.ndarray, float]:
    """Parallel SuperBit: vectorized sweep with per-variable temperature.

    T_i = T_global / (1 + κ · σ_i)

    Returns (best_energy, best_state, sigma, final_T).
    """
    if rng is None:
        rng = np.random.default_rng(42)

    m = rng.choice([-1, 1], size=n).astype(float)
    T = 2.0
    prev = m.copy()
    best_E = ising_energy(m, J, h)
    best_m = m.copy()

    window = min(50, sweeps // 3)
    history = np.zeros((window, n))
    hist_idx = 0
    hist_count = 0
    sigma = np.full(n, 0.5)

    # Cooling schedule
    T_start = 2.0
    T_end = 0.01
    cool = (T_end / T_start) ** (1.0 / max(sweeps, 1))

    for sweep_num in range(sweeps):
        # Per-variable β
        T_vec = T / (1.0 + kappa * sigma)
        T_vec = np.maximum(T_vec, 0.01)
        beta_vec = 1.0 / T_vec

        # Parallel update
        m = parallel_sweep(m, J, h, beta_vec, rng)

        E = ising_energy(m, J, h)
        if E < best_E:
            best_E = E
            best_m = m.copy()

        # Update history and sigma
        history[hist_idx] = m.copy()
        hist_idx = (hist_idx + 1) % window
        hist_count += 1
        if hist_count >= 5:
            length = min(hist_count, window)
            sigma = measure_sigma_from_history(history[:length], m)

        # Self-tune + cool
        ga = float(np.mean(m * prev))
        T = self_tune_T(T, ga)
        T *= cool
        T = max(T, 0.01)
        prev = m.copy()

    return best_E, best_m, sigma, T


def sa_optimize(n: int, J: np.ndarray, h: np.ndarray,
                sweeps: int = 1000,
                T_start: float = 2.0, T_end: float = 0.01,
                rng: Optional[np.random.Generator] = None
                ) -> Tuple[float, np.ndarray]:
    """Standard Simulated Annealing (sequential, geometric cooling).
    Returns (best_energy, best_state).
    """
    if rng is None:
        rng = np.random.default_rng(42)

    m = rng.choice([-1, 1], size=n).astype(float)
    best_E = ising_energy(m, J, h)
    best_m = m.copy()
    T = T_start
    cool = (T_end / T_start) ** (1.0 / max(sweeps * n, 1))

    for _ in range(sweeps):
        for i in rng.permutation(n):
            dE = 2 * m[i] * (h[i] + J[i] @ m)
            if dE < 0 or rng.random() < np.exp(-dE / max(T, 1e-10)):
                m[i] *= -1
            T *= cool
        E = ising_energy(m, J, h)
        if E < best_E:
            best_E = E
            best_m = m.copy()

    return best_E, best_m
