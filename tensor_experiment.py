"""
Numerical experiment: entanglement profile of SAT instances.

For small n, we construct the communication matrix M_f for a random 3-SAT
instance and measure its rank across balanced cuts. We compare:
1. Random 3-SAT near the satisfiability threshold (~4.27 clauses/variable)
2. Random 3-SAT far below threshold (easy, underconstrained)
3. A known P-complete function (e.g., iterated XOR / parity)

If NP-complete functions are "more entangled" than P functions,
we should see rank(M_f) grow faster for SAT near threshold.
"""

import numpy as np
from itertools import product
import random
from math import comb

def random_3sat(n_vars, n_clauses):
    """Generate a random 3-SAT instance as a list of clauses.
    Each clause is a list of 3 literals (positive = var, negative = NOT var).
    Variables are 0-indexed."""
    clauses = []
    for _ in range(n_clauses):
        vars_chosen = random.sample(range(n_vars), 3)
        signs = [random.choice([1, -1]) for _ in range(3)]
        clause = [(v, s) for v, s in zip(vars_chosen, signs)]
        clauses.append(clause)
    return clauses

def evaluate_3sat(clauses, assignment):
    """Evaluate a 3-SAT instance on a given assignment (tuple of 0/1)."""
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

def parity(assignment):
    """Simple parity function - XOR of all bits."""
    return sum(assignment) % 2

def communication_matrix(func, n, cut_indices):
    """
    Build the communication matrix for function func on n variables,
    with the given cut: cut_indices are the 'A' variables,
    the rest are 'B' variables.

    M[a, b] = func(combined_assignment)

    Returns the matrix as a numpy array.
    """
    all_indices = list(range(n))
    b_indices = [i for i in all_indices if i not in cut_indices]

    a_size = len(cut_indices)
    b_size = len(b_indices)

    n_rows = 2 ** a_size
    n_cols = 2 ** b_size

    M = np.zeros((n_rows, n_cols), dtype=np.float64)

    for a_int in range(n_rows):
        a_bits = [(a_int >> i) & 1 for i in range(a_size)]
        for b_int in range(n_cols):
            b_bits = [(b_int >> i) & 1 for i in range(b_size)]

            # Reconstruct full assignment
            assignment = [0] * n
            for idx, val in zip(cut_indices, a_bits):
                assignment[idx] = val
            for idx, val in zip(b_indices, b_bits):
                assignment[idx] = val

            M[a_int, b_int] = func(tuple(assignment))

    return M

def matrix_rank(M):
    """Compute rank of a binary matrix over the reals."""
    return np.linalg.matrix_rank(M)

def gf2_rank(M):
    """Compute rank over GF(2) via Gaussian elimination."""
    M = M.astype(int) % 2
    M = M.copy()
    rows, cols = M.shape
    rank = 0
    for col in range(cols):
        # Find pivot
        pivot = None
        for row in range(rank, rows):
            if M[row, col] == 1:
                pivot = row
                break
        if pivot is None:
            continue
        # Swap
        M[[rank, pivot]] = M[[pivot, rank]]
        # Eliminate
        for row in range(rows):
            if row != rank and M[row, col] == 1:
                M[row] = (M[row] + M[rank]) % 2
        rank += 1
    return rank

def balanced_cut(n):
    """Return a balanced cut: first n//2 variables vs rest."""
    return list(range(n // 2))

def random_balanced_cut(n):
    """Return a random balanced cut."""
    indices = list(range(n))
    random.shuffle(indices)
    return sorted(indices[:n // 2])

def experiment(n_range=range(6, 17, 2), n_trials=10, n_cuts=5):
    """
    Main experiment: compare entanglement profiles.
    """
    print(f"{'n':>4} | {'SAT(thresh) R-rank':>18} | {'SAT(thresh) GF2':>15} | "
          f"{'SAT(easy) R-rank':>16} | {'SAT(easy) GF2':>13} | "
          f"{'PARITY R-rank':>13} | {'PARITY GF2':>10} | "
          f"{'Max possible':>12}")
    print("-" * 120)

    for n in n_range:
        half = n // 2
        max_rank = min(2**half, 2**(n - half))

        # Threshold ratio for 3-SAT
        threshold_ratio = 4.27
        easy_ratio = 2.0

        sat_thresh_ranks_r = []
        sat_thresh_ranks_gf2 = []
        sat_easy_ranks_r = []
        sat_easy_ranks_gf2 = []
        parity_ranks_r = []
        parity_ranks_gf2 = []

        for trial in range(n_trials):
            # Generate SAT instances
            n_clauses_thresh = int(threshold_ratio * n)
            n_clauses_easy = int(easy_ratio * n)

            sat_thresh = random_3sat(n, n_clauses_thresh)
            sat_easy_inst = random_3sat(n, n_clauses_easy)

            # Create function wrappers
            def f_thresh(x, clauses=sat_thresh):
                return evaluate_3sat(clauses, x)

            def f_easy(x, clauses=sat_easy_inst):
                return evaluate_3sat(clauses, x)

            # Try multiple random cuts and take the average
            for _ in range(n_cuts):
                cut = random_balanced_cut(n)

                M_thresh = communication_matrix(f_thresh, n, cut)
                M_easy = communication_matrix(f_easy, n, cut)
                M_parity = communication_matrix(parity, n, cut)

                sat_thresh_ranks_r.append(matrix_rank(M_thresh))
                sat_thresh_ranks_gf2.append(gf2_rank(M_thresh))
                sat_easy_ranks_r.append(matrix_rank(M_easy))
                sat_easy_ranks_gf2.append(gf2_rank(M_easy))
                parity_ranks_r.append(matrix_rank(M_parity))
                parity_ranks_gf2.append(gf2_rank(M_parity))

        avg = lambda lst: sum(lst) / len(lst)

        print(f"{n:>4} | {avg(sat_thresh_ranks_r):>18.1f} | {avg(sat_thresh_ranks_gf2):>15.1f} | "
              f"{avg(sat_easy_ranks_r):>16.1f} | {avg(sat_easy_ranks_gf2):>13.1f} | "
              f"{avg(parity_ranks_r):>13.1f} | {avg(parity_ranks_gf2):>10.1f} | "
              f"{max_rank:>12}")

def detailed_scaling(n_range=range(6, 19, 2), n_trials=20):
    """
    Focus on how rank scales with n for SAT at threshold.
    Compute rank / max_rank ratio to see if it saturates.
    """
    print("\nScaling analysis: rank(M) / max_possible_rank")
    print(f"{'n':>4} | {'SAT@thresh ratio':>16} | {'SAT@easy ratio':>14} | {'PARITY ratio':>12}")
    print("-" * 60)

    for n in n_range:
        half = n // 2
        max_rank = 2 ** half  # for balanced cut

        ratios_thresh = []
        ratios_easy = []
        ratios_parity = []

        for _ in range(n_trials):
            sat_thresh = random_3sat(n, int(4.27 * n))
            sat_easy_inst = random_3sat(n, int(2.0 * n))

            cut = random_balanced_cut(n)

            def f_t(x, c=sat_thresh): return evaluate_3sat(c, x)
            def f_e(x, c=sat_easy_inst): return evaluate_3sat(c, x)

            r_t = matrix_rank(communication_matrix(f_t, n, cut))
            r_e = matrix_rank(communication_matrix(f_e, n, cut))
            r_p = matrix_rank(communication_matrix(parity, n, cut))

            ratios_thresh.append(r_t / max_rank)
            ratios_easy.append(r_e / max_rank)
            ratios_parity.append(r_p / max_rank)

        avg = lambda lst: sum(lst) / len(lst)
        print(f"{n:>4} | {avg(ratios_thresh):>16.4f} | {avg(ratios_easy):>14.4f} | {avg(ratios_parity):>12.4f}")

if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)

    print("=" * 120)
    print("EXPERIMENT 1: Communication matrix rank comparison")
    print("Comparing SAT@threshold vs SAT@easy vs PARITY across balanced cuts")
    print("=" * 120)
    experiment(n_range=range(6, 17, 2))

    print("\n")
    print("=" * 60)
    print("EXPERIMENT 2: Scaling of rank ratio")
    print("=" * 60)
    detailed_scaling(n_range=range(6, 19, 2))

    print("\n")
    print("INTERPRETATION:")
    print("- If SAT@threshold ratio stays close to 1.0 as n grows,")
    print("  the function is 'maximally entangled' — evidence for P≠NP")
    print("- If ratio decays, there's exploitable structure — weaker evidence")
    print("- PARITY should show ratio = 2/max_rank (rank is always 2 over R)")
    print("  despite being 'hard' for one cut — it's in P")
