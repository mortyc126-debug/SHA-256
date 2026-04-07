"""
Experiment v2: Fixing the sparsity problem.

Key insight from v1: rank of communication matrix is dominated by
sparsity (number of satisfying assignments), not computational complexity.

New approaches:
1. Normalize by sparsity — use rank / sqrt(#solutions) or similar
2. Use a DIFFERENT measure: instead of the SAT function, look at the
   SEARCH structure — correlation between variable groups
3. Compare functions of EQUAL sparsity but different complexity

Approach 3 is most principled: construct pairs of functions with
the same number of 1s, where one is "easy" and one is "hard",
and compare their entanglement profiles.
"""

import numpy as np
from itertools import product
import random
from collections import Counter

def random_3sat(n_vars, n_clauses):
    clauses = []
    for _ in range(n_clauses):
        vars_chosen = random.sample(range(n_vars), 3)
        signs = [random.choice([1, -1]) for _ in range(3)]
        clause = [(v, s) for v, s in zip(vars_chosen, signs)]
        clauses.append(clause)
    return clauses

def evaluate_3sat(clauses, assignment):
    for clause in clauses:
        satisfied = False
        for var, sign in clause:
            val = assignment[var]
            if sign == 1 and val == 1:
                satisfied = True
                break
            if sign == -1 and val == 0:
                satisfied = True
                break
        if not satisfied:
            return 0
    return 1

def truth_table(func, n):
    """Compute full truth table as a vector of length 2^n."""
    table = []
    for i in range(2**n):
        bits = tuple((i >> j) & 1 for j in range(n))
        table.append(func(bits))
    return np.array(table, dtype=np.float64)

def communication_matrix(table, n, cut_indices):
    """Build communication matrix from precomputed truth table."""
    all_indices = list(range(n))
    b_indices = [i for i in all_indices if i not in cut_indices]
    a_size = len(cut_indices)
    b_size = len(b_indices)

    M = np.zeros((2**a_size, 2**b_size), dtype=np.float64)

    for full_int in range(2**n):
        bits = [(full_int >> j) & 1 for j in range(n)]

        a_int = 0
        for idx, ci in enumerate(cut_indices):
            a_int |= (bits[ci] << idx)

        b_int = 0
        for idx, bi in enumerate(b_indices):
            b_int |= (bits[bi] << idx)

        M[a_int, b_int] = table[full_int]

    return M

def gf2_rank(M):
    M = M.astype(int) % 2
    M = M.copy()
    rows, cols = M.shape
    rank = 0
    for col in range(cols):
        pivot = None
        for row in range(rank, rows):
            if M[row, col] == 1:
                pivot = row
                break
        if pivot is None:
            continue
        M[[rank, pivot]] = M[[pivot, rank]]
        for row in range(rows):
            if row != rank and M[row, col] == 1:
                M[row] = (M[row] + M[rank]) % 2
        rank += 1
    return rank

def random_balanced_cut(n):
    indices = list(range(n))
    random.shuffle(indices)
    return sorted(indices[:n // 2])

# ============================================================
# APPROACH: Fourier analysis over GF(2)
# ============================================================
# Instead of raw rank, use the Fourier spectrum of the Boolean function.
# The Fourier coefficients reveal the "algebraic complexity" of f.
#
# For f: {0,1}^n -> {-1,+1} (converting 0->1, 1->-1),
# f(x) = Σ_S f̂(S) · χ_S(x)
# where χ_S(x) = (-1)^{Σ_{i∈S} x_i}
#
# The SPECTRAL NORM (L1 norm of Fourier coefficients) is related to
# communication complexity. Specifically:
#   log(rank(M_f)) >= spectral_norm_related_quantity

def fourier_transform(table_pm):
    """
    Compute all Fourier coefficients of f: {0,1}^n -> {-1,+1}.
    Uses the Walsh-Hadamard transform.
    table_pm: truth table in {-1, +1} encoding, length 2^n.
    """
    n = int(np.log2(len(table_pm)))
    N = len(table_pm)
    f_hat = table_pm.copy()

    # Fast Walsh-Hadamard transform
    h = 1
    while h < N:
        for i in range(0, N, h * 2):
            for j in range(i, i + h):
                x = f_hat[j]
                y = f_hat[j + h]
                f_hat[j] = x + y
                f_hat[j + h] = x - y
        h *= 2

    f_hat /= N
    return f_hat

def spectral_analysis(table_01, n):
    """
    Analyze the Fourier spectrum of a Boolean function.
    Returns: spectral L1 norm, number of nonzero coefficients,
             max coefficient magnitude, spectral entropy.
    """
    # Convert {0,1} -> {-1,+1}: f(x)=0 -> +1, f(x)=1 -> -1
    table_pm = 1.0 - 2.0 * table_01

    f_hat = fourier_transform(table_pm)

    # Spectral L1 norm
    l1 = np.sum(np.abs(f_hat))

    # Number of "significant" coefficients (> threshold)
    threshold = 1e-10
    n_nonzero = np.sum(np.abs(f_hat) > threshold)

    # Maximum coefficient
    max_coeff = np.max(np.abs(f_hat))

    # Spectral entropy
    probs = f_hat**2  # Parseval: sum = 1 for balanced functions
    total = np.sum(probs)
    if total > 0:
        probs = probs / total
        probs = probs[probs > 1e-15]
        entropy = -np.sum(probs * np.log2(probs))
    else:
        entropy = 0

    return {
        'l1_norm': l1,
        'n_nonzero': int(n_nonzero),
        'max_coeff': max_coeff,
        'spectral_entropy': entropy,
        'sparsity': int(np.sum(table_01)),  # number of 1s
    }

# ============================================================
# APPROACH: Approximation rank
# ============================================================
# Instead of exact rank, look at APPROXIMATE rank:
# What is the rank of the best approximation to M with error ε?
# This is measured by the singular values of M.

def singular_value_profile(table_01, n, cut_indices):
    """Compute singular values of the communication matrix."""
    M = communication_matrix(table_01, n, cut_indices)

    if np.all(M == 0):
        return np.array([0.0])

    # Normalize M so that ||M||_F = 1
    frob = np.linalg.norm(M, 'fro')
    if frob > 0:
        M_norm = M / frob
    else:
        return np.array([0.0])

    sv = np.linalg.svd(M_norm, compute_uv=False)
    return sv

def approximate_rank(sv, epsilon=0.1):
    """
    Minimum k such that sum of sv[k:]^2 < epsilon^2.
    (Fraction of Frobenius norm captured by top-k singular values)
    """
    total = np.sum(sv**2)
    if total == 0:
        return 0
    cumulative = np.cumsum(sv**2) / total
    k = np.searchsorted(cumulative, 1 - epsilon**2) + 1
    return min(k, len(sv))


def run_experiments():
    random.seed(42)
    np.random.seed(42)

    print("=" * 80)
    print("EXPERIMENT A: Fourier spectral analysis")
    print("Comparing spectral complexity of SAT vs easy functions")
    print("=" * 80)

    for n in range(8, 19, 2):
        n_trials = 30 if n <= 14 else 10

        stats_thresh = {'l1': [], 'nonzero': [], 'entropy': [], 'sparsity': []}
        stats_easy = {'l1': [], 'nonzero': [], 'entropy': [], 'sparsity': []}

        for _ in range(n_trials):
            # SAT at threshold
            sat_t = random_3sat(n, int(4.27 * n))
            tt_t = truth_table(lambda x, c=sat_t: evaluate_3sat(c, x), n)
            s_t = spectral_analysis(tt_t, n)

            stats_thresh['l1'].append(s_t['l1_norm'])
            stats_thresh['nonzero'].append(s_t['n_nonzero'])
            stats_thresh['entropy'].append(s_t['spectral_entropy'])
            stats_thresh['sparsity'].append(s_t['sparsity'])

            # SAT easy (underconstrained)
            sat_e = random_3sat(n, int(2.0 * n))
            tt_e = truth_table(lambda x, c=sat_e: evaluate_3sat(c, x), n)
            s_e = spectral_analysis(tt_e, n)

            stats_easy['l1'].append(s_e['l1_norm'])
            stats_easy['nonzero'].append(s_e['n_nonzero'])
            stats_easy['entropy'].append(s_e['spectral_entropy'])
            stats_easy['sparsity'].append(s_e['sparsity'])

        avg = lambda lst: sum(lst)/len(lst) if lst else 0

        print(f"\nn = {n}  (2^n = {2**n})")
        print(f"  SAT@threshold: L1={avg(stats_thresh['l1']):.3f}  "
              f"nonzero={avg(stats_thresh['nonzero']):.0f}/{2**n}  "
              f"entropy={avg(stats_thresh['entropy']):.2f}  "
              f"#solutions={avg(stats_thresh['sparsity']):.0f}")
        print(f"  SAT@easy:      L1={avg(stats_easy['l1']):.3f}  "
              f"nonzero={avg(stats_easy['nonzero']):.0f}/{2**n}  "
              f"entropy={avg(stats_easy['entropy']):.2f}  "
              f"#solutions={avg(stats_easy['sparsity']):.0f}")

    print("\n")
    print("=" * 80)
    print("EXPERIMENT B: Singular value decay (approximate rank)")
    print("How quickly do singular values decay? Slow decay = high entanglement")
    print("=" * 80)

    for n in [10, 12, 14, 16]:
        print(f"\nn = {n}")
        n_trials = 20 if n <= 14 else 5

        for label, ratio in [("SAT@thresh", 4.27), ("SAT@easy", 2.0)]:
            approx_ranks = {0.01: [], 0.05: [], 0.1: [], 0.2: []}

            for _ in range(n_trials):
                sat = random_3sat(n, int(ratio * n))
                tt = truth_table(lambda x, c=sat: evaluate_3sat(c, x), n)

                # Skip trivially unsatisfiable
                if np.sum(tt) == 0:
                    continue

                cut = random_balanced_cut(n)
                sv = singular_value_profile(tt, n, cut)

                for eps in approx_ranks:
                    approx_ranks[eps].append(approximate_rank(sv, eps))

            if all(len(v) > 0 for v in approx_ranks.values()):
                avg = lambda lst: sum(lst)/len(lst)
                max_rank = 2**(n//2)
                parts = []
                for eps in sorted(approx_ranks.keys()):
                    r = avg(approx_ranks[eps])
                    parts.append(f"ε={eps}:{r:.1f}/{max_rank}")
                print(f"  {label:>12}: {' | '.join(parts)}")

    # EXPERIMENT C: Compare equal-sparsity functions
    print("\n")
    print("=" * 80)
    print("EXPERIMENT C: Fixed sparsity comparison")
    print("Functions with SAME number of 1s but different structure")
    print("=" * 80)

    for n in [10, 12, 14]:
        print(f"\nn = {n}")
        N = 2**n
        half = n // 2

        # Generate SAT functions that are satisfiable
        sat_ranks = []
        random_ranks = []
        structured_ranks = []

        for trial in range(30):
            # Find a satisfiable SAT instance at threshold
            for attempt in range(50):
                sat = random_3sat(n, int(4.27 * n))
                tt_sat = truth_table(lambda x, c=sat: evaluate_3sat(c, x), n)
                k = int(np.sum(tt_sat))
                if k > 0:
                    break
            else:
                continue

            # Create a RANDOM function with same sparsity k
            tt_rand = np.zeros(N)
            ones_pos = random.sample(range(N), k)
            for pos in ones_pos:
                tt_rand[pos] = 1.0

            # Create a STRUCTURED (easy) function with same sparsity k
            # Use a threshold function: f(x) = 1 iff popcount(x) in some range
            # This is computable in P easily
            popcounts = [bin(i).count('1') for i in range(N)]
            sorted_by_pop = sorted(range(N), key=lambda i: (popcounts[i], i))
            tt_struct = np.zeros(N)
            for pos in sorted_by_pop[:k]:
                tt_struct[pos] = 1.0

            # Compute ranks for all three
            cut = random_balanced_cut(n)
            M_sat = communication_matrix(tt_sat, n, cut)
            M_rand = communication_matrix(tt_rand, n, cut)
            M_struct = communication_matrix(tt_struct, n, cut)

            sat_ranks.append(np.linalg.matrix_rank(M_sat))
            random_ranks.append(np.linalg.matrix_rank(M_rand))
            structured_ranks.append(np.linalg.matrix_rank(M_struct))

        if sat_ranks:
            avg = lambda lst: sum(lst)/len(lst)
            max_r = 2**half
            print(f"  SAT@threshold: avg rank = {avg(sat_ranks):.1f} / {max_r}")
            print(f"  Random (same sparsity): avg rank = {avg(random_ranks):.1f} / {max_r}")
            print(f"  Structured (popcount): avg rank = {avg(structured_ranks):.1f} / {max_r}")


if __name__ == "__main__":
    run_experiments()
