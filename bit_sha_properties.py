"""
SHA-256 BIT PROPERTIES → GENERAL BIT MECHANICS

Testing whether properties discovered in SHA-256 context
apply to bits in SAT / constraint satisfaction:

1. SELF-ANNIHILATION: x ⊕ f(x) = 0. Does this exist in SAT?
2. CONDITIONAL VISIBILITY: one bit gates another's information
3. CARRY CHAINS: sequential irreversible dependencies
4. BIT CLONING: one bit's info spread across multiple locations
5. SELF-CANCELLATION in modular arithmetic → analog in SAT?
"""

import random
import math
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    sat = 0
    for clause in clauses:
        for var, sign in clause:
            if (sign == 1 and assignment[var] == 1) or \
               (sign == -1 and assignment[var] == 0):
                sat += 1
                break
    return sat


def bit_tension(clauses, n, var, fixed=None):
    if fixed is None: fixed = {}
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        sat = False; rem = []
        for v, s in clause:
            if v in fixed:
                if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                    sat = True; break
            else: rem.append((v,s))
        if sat: continue
        for v, s in rem:
            if v == var:
                w = 1.0/max(1,len(rem))
                if s==1: p1 += w
                else: p0 += w
    total = p1+p0
    return (p1-p0)/total if total > 0 else 0.0


# ============================================================
# 1. SELF-ANNIHILATION: Does a bit cancel with its own influence?
# ============================================================

def self_annihilation():
    """
    In SHA-256: x ⊕ f(x) = 0 when f captures x's information.

    In SAT: bit i has tension σ_i. The INFLUENCE of bit i on
    its neighbors creates a "reflection" — the neighbors' response
    to i's fixation. If we combine σ_i with the reflected signal,
    do they cancel?

    Define: reflected_σ_i = avg change in neighbor tensions when i is fixed
    Test: σ_i + reflected_σ_i ≈ 0?
    """
    print("=" * 70)
    print("1. SELF-ANNIHILATION: Does bit cancel with its reflection?")
    print("=" * 70)

    random.seed(42); n = 12

    cancellation_scores = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            val = 1 if sigma >= 0 else 0

            # Reflected signal: how do neighbors change when I'm fixed?
            reflected = 0
            neighbors = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)

            for nb in neighbors:
                sigma_nb_before = bit_tension(clauses, n, nb)
                sigma_nb_after = bit_tension(clauses, n, nb, {var: val})
                reflected += (sigma_nb_after - sigma_nb_before)

            if neighbors:
                reflected /= len(neighbors)

            # Cancellation: σ + reflected ≈ 0?
            cancellation = abs(sigma + reflected)
            cancellation_scores.append({
                'sigma': sigma,
                'reflected': reflected,
                'sum': sigma + reflected,
                'cancellation': cancellation,
            })

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    avg_sigma = mean([abs(c['sigma']) for c in cancellation_scores])
    avg_reflected = mean([abs(c['reflected']) for c in cancellation_scores])
    avg_sum = mean([c['sum'] for c in cancellation_scores])
    avg_cancel = mean([c['cancellation'] for c in cancellation_scores])

    print(f"\n  avg |σ|:        {avg_sigma:.4f}")
    print(f"  avg |reflected|: {avg_reflected:.4f}")
    print(f"  avg (σ + refl):  {avg_sum:+.4f}")
    print(f"  avg |σ + refl|:  {avg_cancel:.4f}")

    if avg_cancel < avg_sigma * 0.5:
        print(f"\n  → PARTIAL CANCELLATION! Signal + reflection ≈ 0")
    elif avg_cancel < avg_sigma * 0.8:
        print(f"\n  → WEAK cancellation")
    else:
        print(f"\n  → No cancellation. Signal and reflection are independent.")


# ============================================================
# 2. CONDITIONAL VISIBILITY: one bit gates another
# ============================================================

def conditional_visibility():
    """
    In SHA-256: Ch(e,f,g) — bit e controls whether f or g is visible.

    In SAT: does fixing bit i make bit j's tension VISIBLE (strong)
    or INVISIBLE (collapse to zero)?

    For each pair (i,j): measure |σ_j| before and after fixing i.
    If |σ_j| increases dramatically → i "reveals" j.
    If |σ_j| drops to ~0 → i "hides" j.
    """
    print("\n" + "=" * 70)
    print("2. CONDITIONAL VISIBILITY: Do bits gate each other?")
    print("=" * 70)

    random.seed(42); n = 12

    reveal_cases = 0
    hide_cases = 0
    neutral_cases = 0
    total_pairs = 0

    for seed in range(80):
        clauses = random_3sat(n, int(4.27*n), seed=seed)

        for i in range(n):
            sigma_i = bit_tension(clauses, n, i)
            val_i = 1 if sigma_i >= 0 else 0

            for j in range(n):
                if i == j: continue
                total_pairs += 1

                sigma_j_before = abs(bit_tension(clauses, n, j))
                sigma_j_after = abs(bit_tension(clauses, n, j, {i: val_i}))

                ratio = sigma_j_after / sigma_j_before if sigma_j_before > 0.01 else 1.0

                if ratio > 2.0:
                    reveal_cases += 1  # i REVEALS j
                elif ratio < 0.3:
                    hide_cases += 1    # i HIDES j
                else:
                    neutral_cases += 1

    print(f"\n  Total pairs: {total_pairs}")
    print(f"  Reveals (|σ_j| doubles): {reveal_cases} ({reveal_cases/total_pairs*100:.1f}%)")
    print(f"  Hides (|σ_j| drops 70%): {hide_cases} ({hide_cases/total_pairs*100:.1f}%)")
    print(f"  Neutral: {neutral_cases} ({neutral_cases/total_pairs*100:.1f}%)")


# ============================================================
# 3. CARRY CHAINS: sequential irreversible dependencies
# ============================================================

def carry_chains():
    """
    In SHA-256: carry creates A→B→C→D chain.

    In SAT: are there CHAINS where fixing bit A forces B,
    B forces C, C forces D? How long are these chains?

    Chain = sequence where unit propagation cascades.
    """
    print("\n" + "=" * 70)
    print("3. CARRY CHAINS: Sequential dependency cascades")
    print("=" * 70)

    random.seed(42); n = 12

    chain_lengths = []

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # For each starting bit: how long is the UP cascade?
        for start in range(n):
            fixed = {start: correct_val[start]}
            chain = [start]

            changed = True
            while changed:
                changed = False
                for clause in clauses:
                    satisfied = False; free = []
                    for v, s in clause:
                        if v in fixed:
                            if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                                satisfied = True; break
                        else: free.append((v,s))
                    if not satisfied and len(free) == 1:
                        v, s = free[0]
                        if v not in fixed:
                            fixed[v] = 1 if s==1 else 0
                            chain.append(v)
                            changed = True

            chain_lengths.append(len(chain) - 1)  # exclude starting bit

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Average chain length: {mean(chain_lengths):.2f}")
    print(f"  Max chain length: {max(chain_lengths)}")

    # Distribution
    from collections import Counter
    dist = Counter(chain_lengths)
    print(f"\n  {'length':>6} | {'count':>6} | visual")
    print("  " + "-" * 30)
    for length in sorted(dist.keys()):
        if dist[length] < 5: continue
        bar = "█" * min(50, dist[length]//5)
        print(f"  {length:>6} | {dist[length]:>6} | {bar}")


# ============================================================
# 4. BIT CLONING: information spread across multiple bits
# ============================================================

def bit_cloning():
    """
    In SHA-256: shift register clones a bit to 4 locations.

    In SAT: is one bit's information DUPLICATED in others?
    If bit i and bit j always have the same value in all solutions,
    then j is a "clone" of i.

    How many "clone pairs" exist?
    """
    print("\n" + "=" * 70)
    print("4. BIT CLONING: Duplicated information")
    print("=" * 70)

    random.seed(42); n = 12

    perfect_clones = 0
    anti_clones = 0
    partial_clones = 0
    total_pairs = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions or len(solutions) < 2: continue

        for i in range(n):
            for j in range(i+1, n):
                total_pairs += 1
                # How often do i and j have same value across solutions?
                same = sum(1 for s in solutions if s[i] == s[j])
                frac_same = same / len(solutions)

                if frac_same > 0.95:
                    perfect_clones += 1
                elif frac_same < 0.05:
                    anti_clones += 1
                elif frac_same > 0.8 or frac_same < 0.2:
                    partial_clones += 1

    print(f"\n  Total pairs: {total_pairs}")
    print(f"  Perfect clones (>95% same): {perfect_clones} ({perfect_clones/total_pairs*100:.2f}%)")
    print(f"  Anti-clones (<5% same):     {anti_clones} ({anti_clones/total_pairs*100:.2f}%)")
    print(f"  Partial (>80% or <20%):     {partial_clones} ({partial_clones/total_pairs*100:.2f}%)")


# ============================================================
# 5. SELF-CANCELLATION: bit + nonlinear function of itself
# ============================================================

def self_cancellation():
    """
    In Z/2^n: x + f(x) can cancel when f captures x's information.

    In SAT: define f(x_i) = majority vote of x_i's NEIGHBORS' tensions.
    Does σ_i + f(σ_i) cancel?

    More precisely: σ_i is the direct signal.
    f(σ_i) = how neighbors RESPOND to σ_i.
    If the system is "self-consistent": σ_i + response should be stable.
    If σ_i + response ≈ 0: the bit CANCELS itself through the network.
    """
    print("\n" + "=" * 70)
    print("5. SELF-CANCELLATION: σ + network_response(σ)")
    print("=" * 70)

    random.seed(42); n = 12

    cancellation_data = []

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)

            # Network response: average neighbor tension × coupling
            neighbors = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)

            if not neighbors: continue

            # f(σ_i) = weighted sum of neighbor tensions
            nb_response = sum(bit_tension(clauses, n, nb) for nb in neighbors) / len(neighbors)

            # Self-cancellation score
            cancel = sigma + nb_response
            is_correct = (1 if sigma >= 0 else 0) == correct_val[var]

            cancellation_data.append({
                'sigma': sigma,
                'response': nb_response,
                'cancel': cancel,
                'abs_cancel': abs(cancel),
                'is_correct': is_correct,
            })

    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    # Do correct and wrong bits cancel differently?
    correct = [d for d in cancellation_data if d['is_correct']]
    wrong = [d for d in cancellation_data if not d['is_correct']]

    print(f"\n  σ + neighbor_response:")
    print(f"    Correct bits: avg |σ+resp| = {mean([d['abs_cancel'] for d in correct]):.4f}")
    print(f"    Wrong bits:   avg |σ+resp| = {mean([d['abs_cancel'] for d in wrong]):.4f}")
    print(f"    All bits:     avg (σ+resp) = {mean([d['cancel'] for d in cancellation_data]):+.4f}")

    # Does cancellation predict correctness?
    ratio = mean([d['abs_cancel'] for d in wrong]) / mean([d['abs_cancel'] for d in correct])
    print(f"    Wrong/Correct ratio: {ratio:.2f}")

    if ratio < 0.8:
        print(f"    → Wrong bits cancel MORE (closer to 0)")
        print(f"    → Self-cancellation = indicator of ERROR")
    elif ratio > 1.2:
        print(f"    → Wrong bits cancel LESS")
    else:
        print(f"    → Similar cancellation for both")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    self_annihilation()
    conditional_visibility()
    carry_chains()
    bit_cloning()
    self_cancellation()
