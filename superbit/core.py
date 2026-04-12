"""
SuperBit core utilities — deduplicated shared code.

All shared functions live here. No duplication elsewhere.
"""

import numpy as np
from typing import List, Tuple, Optional, Set


# ====================================================================
# Types
# ====================================================================
Clause = List[Tuple[int, int]]  # [(var_index, sign), ...], 0-indexed, sign ∈ {-1,+1}


# ====================================================================
# Ising energy
# ====================================================================
def ising_energy(m: np.ndarray, J: np.ndarray, h: np.ndarray) -> float:
    """Ising energy: H(m) = -½ mᵀJm - hᵀm."""
    return -0.5 * m @ J @ m - h @ m


# ====================================================================
# SAT ↔ Ising conversion
# ====================================================================
def sat_to_ising(n: int, clauses: List[Clause]) -> Tuple[np.ndarray, np.ndarray]:
    """Convert 3-SAT to 2-body Ising (J, h).

    Each clause (v1,s1),(v2,s2),(v3,s3):
      h[vi] -= si/8
      J[vi,vj] += si*sj/8 (symmetric)
    """
    J = np.zeros((n, n))
    h = np.zeros(n)
    for clause in clauses:
        for k, (v, s) in enumerate(clause):
            h[v] -= s / 8
        for k in range(len(clause)):
            for l in range(k + 1, len(clause)):
                vk, sk = clause[k]
                vl, sl = clause[l]
                J[vk, vl] += sk * sl / 8
                J[vl, vk] += sk * sl / 8
    return J, h


def qubo_to_ising(Q: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert QUBO (minimize x^T Q x, x∈{0,1}) to Ising (m∈{-1,+1}).
    Returns (J, h, offset).
    """
    n = Q.shape[0]
    J = np.zeros((n, n))
    h = np.zeros(n)
    offset = 0.0
    for i in range(n):
        h[i] = -Q[i, i] / 2 - sum(Q[i, j] + Q[j, i] for j in range(n) if j != i) / 4
        for j in range(i + 1, n):
            J[i, j] = -(Q[i, j] + Q[j, i]) / 4
            J[j, i] = J[i, j]
    return J, h, offset


# ====================================================================
# SAT utilities
# ====================================================================
def generate_3sat(n: int, m: int, rng: np.random.Generator) -> List[Clause]:
    """Generate random 3-SAT instance with n variables, m clauses."""
    clauses = []
    for _ in range(m):
        vs = rng.choice(n, size=3, replace=False)
        signs = rng.choice([-1, 1], size=3)
        clauses.append(list(zip(vs.tolist(), signs.tolist())))
    return clauses


def check_sat(m: np.ndarray, clauses: List[Clause]) -> Tuple[bool, int]:
    """Check if assignment m satisfies all clauses.
    Returns (all_satisfied, n_unsatisfied).
    """
    n_unsat = 0
    for clause in clauses:
        if not any((s > 0 and m[v] > 0) or (s < 0 and m[v] < 0)
                   for v, s in clause):
            n_unsat += 1
    return n_unsat == 0, n_unsat


# ====================================================================
# Gibbs sampling primitives
# ====================================================================
def gibbs_sweep(m: np.ndarray, J: np.ndarray, h: np.ndarray,
                T: float, rng: np.random.Generator) -> np.ndarray:
    """One sequential Gibbs sweep: update all n variables."""
    n = len(m)
    beta = 1.0 / max(T, 0.01)
    for i in rng.permutation(n):
        I_i = h[i] + J[i] @ m
        p = (1.0 + np.tanh(beta * I_i)) / 2.0
        m[i] = 1.0 if rng.random() < p else -1.0
    return m


def parallel_sweep(m: np.ndarray, J: np.ndarray, h: np.ndarray,
                   beta_vec: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """One parallel sweep: update all variables simultaneously (vectorized)."""
    I_all = h + J @ m
    p = (1.0 + np.tanh(beta_vec * I_all)) / 2.0
    m = np.where(rng.random(len(m)) < p, 1.0, -1.0)
    return m


# ====================================================================
# Self-tuning temperature
# ====================================================================
def self_tune_T(T: float, autocorr: float,
                heat_rate: float = 1.02,
                cool_rate: float = 0.97,
                T_min: float = 0.05,
                T_max: float = 50.0) -> float:
    """Adjust T based on autocorrelation feedback."""
    if autocorr > 0.8:
        T *= heat_rate
    elif autocorr < 0.3:
        T *= cool_rate
    return np.clip(T, T_min, T_max)


# ====================================================================
# σ measurement
# ====================================================================
def measure_sigma_from_history(history: np.ndarray,
                               m_current: np.ndarray) -> np.ndarray:
    """Compute σ from sliding window history.
    σ_i = fraction of history where m_i matches current value.
    """
    if len(history) < 2:
        return np.full(len(m_current), 0.5)
    return np.mean(history * m_current[np.newaxis, :] > 0, axis=0)


def sbit_scores(n: int, J: np.ndarray, h: np.ndarray,
                sweeps: int = 1500, n_runs: int = 3,
                rng: Optional[np.random.Generator] = None) -> np.ndarray:
    """S-bit detection scores: |magnetization| + autocorrelation.
    Returns combined score per variable ∈ [0, 1].
    """
    if rng is None:
        rng = np.random.default_rng(42)

    all_mag = []
    all_ac = []
    for _ in range(n_runs):
        m = rng.choice([-1, 1], size=n).astype(float)
        T = 1.0
        prev = m.copy()
        mag_sum = np.zeros(n)
        ac_sum = np.zeros(n)
        cnt = 0
        for s in range(sweeps):
            m = gibbs_sweep(m, J, h, T, rng)
            ga = np.mean(m * prev)
            T = self_tune_T(T, ga)
            if s > sweeps // 3:
                mag_sum += m
                ac_sum += m * prev
                cnt += 1
            prev = m.copy()
        if cnt > 0:
            all_mag.append(np.abs(mag_sum / cnt))
            all_ac.append(ac_sum / cnt)

    if not all_mag:
        return np.full(n, 0.5)
    return (np.mean(all_mag, axis=0) + np.mean(all_ac, axis=0)) / 2


# ====================================================================
# Incremental SAT state tracker
# ====================================================================
class SATState:
    """Incremental clause satisfaction tracker for O(degree) flips."""

    def __init__(self, n: int, clauses: List[Clause], m: np.ndarray):
        self.n = n
        self.clauses = clauses
        self.m = m.copy()

        # Build var→clause index
        self.var_clauses = [[] for _ in range(n)]
        for ci, clause in enumerate(clauses):
            for v, s in clause:
                self.var_clauses[v].append(ci)

        # Count satisfied literals per clause
        self.true_count = np.zeros(len(clauses), dtype=int)
        self.unsat_set = set()

        for ci, clause in enumerate(clauses):
            for v, s in clause:
                if (s > 0 and m[v] > 0) or (s < 0 and m[v] < 0):
                    self.true_count[ci] += 1
            if self.true_count[ci] == 0:
                self.unsat_set.add(ci)

    @property
    def n_unsat(self) -> int:
        return len(self.unsat_set)

    def flip(self, v: int):
        """Flip variable v and update clause counts incrementally."""
        self.m[v] *= -1
        for ci in self.var_clauses[v]:
            clause = self.clauses[ci]
            for cv, cs in clause:
                if cv == v:
                    if (cs > 0 and self.m[v] > 0) or (cs < 0 and self.m[v] < 0):
                        self.true_count[ci] += 1
                    else:
                        self.true_count[ci] -= 1
                    break
            if self.true_count[ci] == 0:
                self.unsat_set.add(ci)
            else:
                self.unsat_set.discard(ci)

    def net_gain(self, v: int) -> int:
        """Net change in satisfied clauses if v is flipped."""
        make = 0
        brk = 0
        for ci in self.var_clauses[v]:
            if self.true_count[ci] == 0:
                make += 1
            elif self.true_count[ci] == 1:
                clause = self.clauses[ci]
                for cv, cs in clause:
                    if cv == v:
                        if (cs > 0 and self.m[v] > 0) or (cs < 0 and self.m[v] < 0):
                            brk += 1
                        break
        return make - brk
