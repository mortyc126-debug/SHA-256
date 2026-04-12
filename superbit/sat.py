"""
SuperBit SAT solvers — WalkSAT variants with σ-guidance.

Three solvers:
  walksat()         — plain WalkSAT baseline
  sigma_walksat()   — native-σ guided (flip frequency)
  hybrid_walksat()  — native-σ + Ising-σ fallback on stall
  restart_walksat() — multi-restart with σ-memory
"""

import numpy as np
from typing import List, Tuple, Optional

from .core import Clause, SATState, sat_to_ising, sbit_scores


def walksat(n: int, clauses: List[Clause],
            max_flips: int = 100000, noise: float = 0.4,
            rng: Optional[np.random.Generator] = None
            ) -> Tuple[bool, int]:
    """Plain WalkSAT. Returns (solved, flips_used)."""
    if rng is None:
        rng = np.random.default_rng(42)

    m = rng.choice([-1, 1], size=n).astype(float)
    state = SATState(n, clauses, m)

    for flip in range(max_flips):
        if state.n_unsat == 0:
            return True, flip

        unsat_list = list(state.unsat_set)
        ci = unsat_list[rng.integers(len(unsat_list))]
        clause = clauses[ci]

        if rng.random() < noise:
            v, _ = clause[rng.integers(len(clause))]
        else:
            best_v = clause[0][0]
            best_g = state.net_gain(best_v)
            for v, s in clause[1:]:
                g = state.net_gain(v)
                if g > best_g:
                    best_g = g
                    best_v = v
            v = best_v

        state.flip(v)

    return False, max_flips


def sigma_walksat(n: int, clauses: List[Clause],
                  max_flips: int = 100000, noise: float = 0.4,
                  sigma_strength: float = 0.5,
                  rng: Optional[np.random.Generator] = None
                  ) -> Tuple[bool, int, np.ndarray]:
    """WalkSAT with native-σ (flip frequency tracking).
    Returns (solved, flips_used, sigma).
    """
    if rng is None:
        rng = np.random.default_rng(42)

    m = rng.choice([-1, 1], size=n).astype(float)
    state = SATState(n, clauses, m)
    flip_count = np.zeros(n)
    warmup = max_flips // 10

    for flip in range(max_flips):
        if state.n_unsat == 0:
            sigma = 1.0 - flip_count / max(flip_count.max(), 1)
            return True, flip, sigma

        unsat_list = list(state.unsat_set)
        ci = unsat_list[rng.integers(len(unsat_list))]
        clause = clauses[ci]

        # Compute sigma from flip frequency
        if flip > warmup and flip_count.max() > 0:
            sigma = 1.0 - flip_count / flip_count.max()
        else:
            sigma = np.full(n, 0.5)

        if rng.random() < noise:
            if flip > warmup:
                weights = np.array([1.0 - sigma_strength * sigma[v]
                                    for v, _ in clause])
                weights = np.maximum(weights, 0.01)
                weights /= weights.sum()
                idx = rng.choice(len(clause), p=weights)
            else:
                idx = rng.integers(len(clause))
            v = clause[idx][0]
        else:
            best_v = clause[0][0]
            best_g = state.net_gain(best_v)
            for v, s in clause[1:]:
                g = state.net_gain(v)
                if g > best_g:
                    best_g = g
                    best_v = v
            v = best_v

        state.flip(v)
        flip_count[v] += 1

    sigma = 1.0 - flip_count / max(flip_count.max(), 1)
    return False, max_flips, sigma


def hybrid_walksat(n: int, clauses: List[Clause],
                   max_flips: int = 100000, noise: float = 0.4,
                   stall_threshold: int = 1000,
                   rng: Optional[np.random.Generator] = None
                   ) -> Tuple[bool, int, np.ndarray, int]:
    """Hybrid WalkSAT: native-σ → stall → Ising-σ → continue.
    Returns (solved, flips, sigma, n_ising_calls).
    """
    if rng is None:
        rng = np.random.default_rng(42)

    m = rng.choice([-1, 1], size=n).astype(float)
    state = SATState(n, clauses, m)
    flip_count = np.zeros(n)
    sigma = np.full(n, 0.5)
    n_ising_calls = 0

    best_unsat = state.n_unsat
    stall_counter = 0

    for flip in range(max_flips):
        if state.n_unsat == 0:
            sigma = 1.0 - flip_count / max(flip_count.max(), 1)
            return True, flip, sigma, n_ising_calls

        # Stall detection
        if state.n_unsat < best_unsat:
            best_unsat = state.n_unsat
            stall_counter = 0
        else:
            stall_counter += 1

        # Switch to Ising-σ on stall
        if stall_counter >= stall_threshold:
            J, h = sat_to_ising(n, clauses)
            sigma = sbit_scores(n, J, h, sweeps=200, n_runs=1, rng=rng)
            n_ising_calls += 1
            stall_counter = 0

        # Update native sigma periodically
        if flip % 100 == 0 and flip_count.max() > 0:
            native_sigma = 1.0 - flip_count / flip_count.max()
            if n_ising_calls > 0:
                sigma = 0.5 * sigma + 0.5 * native_sigma
            else:
                sigma = native_sigma

        # Variable selection
        unsat_list = list(state.unsat_set)
        ci = unsat_list[rng.integers(len(unsat_list))]
        clause = clauses[ci]

        if rng.random() < noise:
            weights = np.array([1.0 - 0.5 * sigma[v] for v, _ in clause])
            weights = np.maximum(weights, 0.01)
            weights /= weights.sum()
            idx = rng.choice(len(clause), p=weights)
            v = clause[idx][0]
        else:
            best_v = clause[0][0]
            best_g = state.net_gain(best_v)
            for v, s in clause[1:]:
                g = state.net_gain(v)
                if g > best_g:
                    best_g = g
                    best_v = v
            v = best_v

        state.flip(v)
        flip_count[v] += 1

    sigma = 1.0 - flip_count / max(flip_count.max(), 1)
    return False, max_flips, sigma, n_ising_calls


def restart_walksat(n: int, clauses: List[Clause],
                    max_restarts: int = 10,
                    flips_per_restart: int = 10000,
                    noise: float = 0.4,
                    preserve_threshold: float = 0.7,
                    rng: Optional[np.random.Generator] = None
                    ) -> Tuple[bool, int, np.ndarray, int]:
    """Multi-restart WalkSAT with σ-memory.
    High-σ variables preserved across restarts.
    Returns (solved, total_flips, sigma, n_restarts).
    """
    if rng is None:
        rng = np.random.default_rng(42)

    m = rng.choice([-1, 1], size=n).astype(float)
    sigma_ema = np.full(n, 0.5)
    total_flips = 0

    for restart in range(max_restarts):
        state = SATState(n, clauses, m)
        flip_count = np.zeros(n)

        for flip in range(flips_per_restart):
            if state.n_unsat == 0:
                return True, total_flips + flip, sigma_ema, restart

            unsat_list = list(state.unsat_set)
            ci = unsat_list[rng.integers(len(unsat_list))]
            clause = clauses[ci]

            if rng.random() < noise:
                v, _ = clause[rng.integers(len(clause))]
            else:
                best_v = clause[0][0]
                best_g = state.net_gain(best_v)
                for v, s in clause[1:]:
                    g = state.net_gain(v)
                    if g > best_g:
                        best_g = g
                        best_v = v
                v = best_v

            state.flip(v)
            flip_count[v] += 1

        total_flips += flips_per_restart

        # Update σ from flip frequency
        if flip_count.max() > 0:
            run_sigma = 1.0 - flip_count / flip_count.max()
            sigma_ema = 0.7 * sigma_ema + 0.3 * run_sigma

        # Restart: preserve high-σ, randomize low-σ
        m = state.m.copy()
        for v in range(n):
            if sigma_ema[v] < preserve_threshold:
                m[v] = rng.choice([-1.0, 1.0])

    return False, total_flips, sigma_ema, max_restarts
