"""
SuperBit temporal monitoring — track σ over time for regime detection.
"""

import numpy as np
from typing import Dict, List, Optional

from .core import gibbs_sweep, self_tune_T, measure_sigma_from_history


def temporal_monitor(n: int,
                     J_sequence: List[np.ndarray],
                     h: np.ndarray,
                     window: int = 30,
                     sweeps_per_step: int = 100,
                     rng: Optional[np.random.Generator] = None
                     ) -> Dict[str, np.ndarray]:
    """Monitor σ over a sequence of coupling matrices J(t).

    Returns dict with time series:
      mean_sigma, sigma_var, frozen_frac, energy, temperature
    """
    if rng is None:
        rng = np.random.default_rng(42)

    n_steps = len(J_sequence)
    m = rng.choice([-1, 1], size=n).astype(float)
    T = 2.0

    results = {
        'mean_sigma': np.zeros(n_steps),
        'sigma_var': np.zeros(n_steps),
        'frozen_frac': np.zeros(n_steps),
        'energy': np.zeros(n_steps),
        'temperature': np.zeros(n_steps),
    }

    for t in range(n_steps):
        J = J_sequence[t]
        prev = m.copy()
        history = []

        for s in range(sweeps_per_step):
            m = gibbs_sweep(m, J, h, T, rng)
            ga = float(np.mean(m * prev))
            T = self_tune_T(T, ga)
            if s > sweeps_per_step // 3:
                history.append(m.copy())
            prev = m.copy()

        if len(history) >= 5:
            hist_arr = np.array(history)
            sigma = measure_sigma_from_history(hist_arr, m)
        else:
            sigma = np.full(n, 0.5)

        E = -0.5 * m @ J @ m - h @ m

        results['mean_sigma'][t] = sigma.mean()
        results['sigma_var'][t] = sigma.var()
        results['frozen_frac'][t] = np.mean(sigma > 0.8)
        results['energy'][t] = E
        results['temperature'][t] = T

    return results
