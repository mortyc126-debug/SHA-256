"""
SuperBit — computational primitive beyond binary bits.

Usage:
    from superbit import SuperBitRegister, from_ising, from_qubo

    # Create register
    reg = SuperBitRegister(100)
    reg = from_ising(J, h)

    # Optimize
    energy, state = reg.optimize(sweeps=500)

    # Analyze (optimize + detect frozen core)
    info = reg.analyze(sweeps=500)
    print(info['frozen'])   # set of frozen variable indices
    print(info['sigma'])    # per-variable certainty

    # SAT solving
    from superbit.sat import walksat, sigma_walksat, hybrid_walksat, restart_walksat
    solved, flips = walksat(n, clauses)
    solved, flips, sigma = sigma_walksat(n, clauses)  # + σ-map

    # Parallel optimization (GPU-style)
    from superbit.optimize import parallel_optimize
    E, state, sigma, T = parallel_optimize(n, J, h)

    # Temporal monitoring
    from superbit.monitor import temporal_monitor
    results = temporal_monitor(n, J_sequence, h)
"""

from .register import SuperBitRegister
from .core import (
    ising_energy,
    sat_to_ising,
    qubo_to_ising,
    generate_3sat,
    check_sat,
    sbit_scores,
    Clause,
)


def from_ising(J, h=None, seed=42):
    """Create SuperBitRegister from Ising problem."""
    n = J.shape[0]
    reg = SuperBitRegister(n, seed)
    reg.set_coupling(J, h)
    return reg


def from_qubo(Q, seed=42):
    """Create SuperBitRegister from QUBO problem."""
    reg = SuperBitRegister(Q.shape[0], seed)
    reg.set_from_qubo(Q)
    return reg


def from_sat(n_vars, clauses, seed=42):
    """Create SuperBitRegister from SAT problem."""
    reg = SuperBitRegister(n_vars, seed)
    reg.set_from_sat(n_vars, clauses)
    return reg


__version__ = "2.0.0"
__all__ = [
    'SuperBitRegister',
    'from_ising', 'from_qubo', 'from_sat',
    'ising_energy', 'sat_to_ising', 'qubo_to_ising',
    'generate_3sat', 'check_sat', 'sbit_scores',
]
