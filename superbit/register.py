"""
SuperBitRegister — main computation object.
"""

import numpy as np
from typing import Optional, Tuple, List, Dict, Set

from .core import (
    ising_energy, sat_to_ising, qubo_to_ising, check_sat,
    gibbs_sweep, parallel_sweep, self_tune_T,
    measure_sigma_from_history, Clause
)


class SuperBitRegister:
    """Register of n superbits with Ising couplings.

    Each superbit i has:
      m[i]  ∈ {-1, +1} : spin value
      σ[i]  ∈ [0, 1]   : certainty (from history)

    Global: T (self-tuning temperature), J (coupling), h (field).
    """

    def __init__(self, n: int, seed: int = 42):
        self.n = n
        self.rng = np.random.default_rng(seed)
        self.m = self.rng.choice([-1.0, 1.0], size=n)
        self.sigma = np.full(n, 0.5)
        self.J = np.zeros((n, n))
        self.h = np.zeros(n)
        self.T = 2.0
        self.prev_m = self.m.copy()
        self._history: List[np.ndarray] = []
        self._hist_max = 100
        self.total_flips = 0
        self.best_energy = float('inf')
        self.best_state = self.m.copy()

    # ---- Problem setup ----

    def set_coupling(self, J: np.ndarray, h: Optional[np.ndarray] = None):
        self.J = J.copy()
        self.h = h.copy() if h is not None else np.zeros(self.n)

    def set_from_sat(self, n_vars: int, clauses: List[Clause]):
        self.__init__(n_vars, seed=int(self.rng.integers(1 << 31)))
        J, h = sat_to_ising(n_vars, clauses)
        self.set_coupling(J, h)

    def set_from_qubo(self, Q: np.ndarray):
        n = Q.shape[0]
        self.__init__(n, seed=int(self.rng.integers(1 << 31)))
        J, h, _ = qubo_to_ising(Q)
        self.set_coupling(J, h)

    # ---- Core operations ----

    def energy(self) -> float:
        return ising_energy(self.m, self.J, self.h)

    def sweep(self):
        """One full Gibbs sweep with self-tuning and σ update."""
        self.m = gibbs_sweep(self.m, self.J, self.h, self.T, self.rng)
        self.total_flips += self.n

        E = self.energy()
        if E < self.best_energy:
            self.best_energy = E
            self.best_state = self.m.copy()

        ga = np.mean(self.m * self.prev_m)
        self.T = self_tune_T(self.T, ga)

        self._history.append(self.m.copy())
        if len(self._history) > self._hist_max:
            self._history.pop(0)
        if len(self._history) >= 10:
            hist = np.array(self._history[-50:])
            self.sigma = measure_sigma_from_history(hist, self.m)

        self.prev_m = self.m.copy()

    # ---- High-level algorithms ----

    def optimize(self, sweeps: int = 1000) -> Tuple[float, np.ndarray]:
        """Find minimum energy state."""
        for _ in range(sweeps):
            self.sweep()
        return self.best_energy, self.best_state

    def detect_frozen(self, sweeps: int = 1000,
                      threshold: float = 0.8) -> Tuple[Set[int], np.ndarray]:
        """Detect frozen variables via σ measurement."""
        for _ in range(sweeps):
            self.sweep()
        frozen = set(i for i in range(self.n) if self.sigma[i] > threshold)
        return frozen, self.sigma

    def sample(self, sweeps: int = 500,
               n_samples: int = 100) -> List[np.ndarray]:
        """Collect Boltzmann samples."""
        for _ in range(sweeps // 2):
            self.sweep()
        samples = []
        interval = max(1, sweeps // (2 * n_samples))
        for s in range(sweeps // 2):
            self.sweep()
            if s % interval == 0 and len(samples) < n_samples:
                samples.append(self.m.copy())
        return samples

    def optimize_3phase(self, sweeps: int = 1000,
                        detect_frac: float = 0.3,
                        lock_frac: float = 0.3) -> Tuple[float, np.ndarray, dict]:
        """Three-phase: DETECT → DECIMATE → ANNEAL."""
        detect_sweeps = int(sweeps * detect_frac)
        anneal_sweeps = sweeps - detect_sweeps

        # Phase 1: DETECT
        from .core import sbit_scores
        scores = sbit_scores(self.n, self.J, self.h,
                             sweeps=detect_sweeps, n_runs=1, rng=self.rng)

        # Phase 2: DECIMATE
        n_lock = int(self.n * lock_frac)
        order = np.argsort(-scores)
        locked = {}
        for k in range(n_lock):
            i = int(order[k])
            locked[i] = self.m[i]

        free_vars = [i for i in range(self.n) if i not in locked]
        n_free = len(free_vars)

        # Phase 3: ANNEAL
        for i, val in locked.items():
            self.m[i] = val

        if n_free > 0:
            T = 2.0
            cool = (0.01 / 2.0) ** (1.0 / max(anneal_sweeps * n_free, 1))
            for _ in range(anneal_sweeps):
                for _ in range(n_free):
                    idx = free_vars[self.rng.integers(n_free)]
                    dE = 2 * self.m[idx] * (self.h[idx] + self.J[idx] @ self.m)
                    if dE < 0 or self.rng.random() < np.exp(-dE / max(T, 1e-10)):
                        self.m[idx] *= -1
                    T *= cool
                E = self.energy()
                if E < self.best_energy:
                    self.best_energy = E
                    self.best_state = self.m.copy()

        return self.best_energy, self.best_state, {
            'locked': locked, 'n_free': n_free, 'scores': scores
        }

    def analyze(self, sweeps: int = 1000) -> Dict:
        """Full analysis: optimization + detection in one run."""
        for _ in range(sweeps):
            self.sweep()
        return {
            'energy': self.best_energy,
            'best_state': self.best_state.copy(),
            'sigma': self.sigma.copy(),
            'frozen': set(i for i in range(self.n) if self.sigma[i] > 0.8),
            'free': set(i for i in range(self.n) if self.sigma[i] < 0.3),
            'temperature': self.T,
            'total_flips': self.total_flips,
            'n': self.n,
            'memory_bytes': self.n * self.n * 8 + self.n * 3 * 8,
        }

    # ---- Phase operations ----

    def phase_product(self, indices: list) -> float:
        result = 1.0
        for i in indices:
            result *= self.m[i]
        return result

    def phase_correlator(self, i: int, j: int) -> float:
        if len(self._history) < 5:
            return self.m[i] * self.m[j]
        hist = np.array(self._history[-30:])
        return float(np.mean(hist[:, i] * hist[:, j]))

    # ---- Utility ----

    def reset(self, seed: Optional[int] = None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.m = self.rng.choice([-1.0, 1.0], size=self.n)
        self.sigma = np.full(self.n, 0.5)
        self.T = 2.0
        self.prev_m = self.m.copy()
        self._history = []
        self.total_flips = 0
        self.best_energy = float('inf')
        self.best_state = self.m.copy()

    def __repr__(self):
        return (f"SuperBitRegister(n={self.n}, T={self.T:.3f}, "
                f"E={self.energy():.4f}, flips={self.total_flips})")
