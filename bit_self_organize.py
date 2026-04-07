"""
LET BITS ORGANIZE THEMSELVES

Instead of ASKING each bit (σ) or FIXING bits (crystallization):
Let bits EVOLVE freely toward their natural attractor.

Like a physical system: release it from random state,
let attraction field pull bits to equilibrium.
DON'T fix anything — let them FLOW.

Methods:
1. MAGNETIC RELAXATION: start random, update each bit to match
   its local tension, repeat until stable.
2. SIMULATED ANNEALING: add noise, gradually reduce.
3. NATURAL OSCILLATION: let bits freely oscillate, observe
   where they SETTLE.
4. CONSENSUS: each bit asks neighbors, updates. Like birds flocking.
5. RESONANCE CASCADE: amplify bits that are "in tune" with neighbors.
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
# 1. MAGNETIC RELAXATION: Let bits align to local field
# ============================================================

def magnetic_relaxation(clauses, n, max_steps=100):
    """
    Start random. Each step: pick a random bit, set it to
    whichever value its CURRENT local field prefers.
    No fixing — every bit can change at any time.
    Like Ising model with Glauber dynamics.
    """
    # Start random
    state = [random.randint(0,1) for _ in range(n)]

    for step in range(max_steps * n):
        # Pick random bit
        var = random.randint(0, n-1)

        # Compute local field: how many clauses prefer 0 vs 1?
        push_1 = 0; push_0 = 0
        for clause in clauses:
            has_var = False; var_sign = 0
            others_satisfy = False
            for v, s in clause:
                if v == var:
                    has_var = True; var_sign = s
                else:
                    if (s==1 and state[v]==1) or (s==-1 and state[v]==0):
                        others_satisfy = True

            if not has_var: continue
            if others_satisfy: continue  # clause already satisfied

            # Clause needs us
            if var_sign == 1: push_1 += 1  # setting to 1 satisfies
            else: push_0 += 1  # setting to 0 satisfies

        # Align to field
        if push_1 > push_0:
            state[var] = 1
        elif push_0 > push_1:
            state[var] = 0
        # else: keep current (tie)

    return state


# ============================================================
# 2. SOFT RELAXATION: Continuous beliefs, not binary
# ============================================================

def soft_relaxation(clauses, n, n_steps=50, damping=0.3):
    """
    Each bit has a BELIEF in [0,1]. Not binary.
    Update: belief(var) = σ(var | neighbors' beliefs).
    Like BP but simpler — direct field computation.
    """
    beliefs = [0.5] * n  # start uncertain

    for step in range(n_steps):
        new_beliefs = [0.0] * n

        for var in range(n):
            push_1 = 0.0; push_0 = 0.0

            for clause in clauses:
                var_sign = None
                others = []
                for v, s in clause:
                    if v == var: var_sign = s
                    else: others.append((v, s))
                if var_sign is None: continue

                # P(others DON'T satisfy) = Π(1 - P(lit_j true))
                p_others_fail = 1.0
                for v, s in others:
                    if s == 1:
                        p_lit = beliefs[v]
                    else:
                        p_lit = 1 - beliefs[v]
                    p_others_fail *= (1 - p_lit)

                # Need for var = p_others_fail
                need = p_others_fail

                if var_sign == 1: push_1 += need
                else: push_0 += need

            total = push_1 + push_0
            if total > 0:
                new_beliefs[var] = push_1 / total
            else:
                new_beliefs[var] = 0.5

        # Damped update
        for var in range(n):
            beliefs[var] = damping * beliefs[var] + (1 - damping) * new_beliefs[var]
            beliefs[var] = max(0.01, min(0.99, beliefs[var]))

    return beliefs


# ============================================================
# 3. CONSENSUS: Each bit asks neighbors and updates
# ============================================================

def consensus(clauses, n, n_rounds=20):
    """
    Each round: each bit surveys its neighbors' current values.
    Updates to the value that satisfies most shared clauses.
    Like bird flocking — align with neighbors.
    """
    state = [random.randint(0,1) for _ in range(n)]

    for round_idx in range(n_rounds):
        # Random order each round
        order = list(range(n))
        random.shuffle(order)

        for var in order:
            # Count: how many clauses satisfied if var=1 vs var=0
            sat_1 = 0; sat_0 = 0
            for clause in clauses:
                has_var = False; var_sign = 0
                for v, s in clause:
                    if v == var: has_var = True; var_sign = s

                if not has_var: continue

                for test_val in [0, 1]:
                    test_state = list(state)
                    test_state[var] = test_val
                    satisfied = False
                    for v, s in clause:
                        if (s==1 and test_state[v]==1) or (s==-1 and test_state[v]==0):
                            satisfied = True; break
                    if satisfied:
                        if test_val == 1: sat_1 += 1
                        else: sat_0 += 1

            if sat_1 > sat_0: state[var] = 1
            elif sat_0 > sat_1: state[var] = 0

        # Check if solved
        if evaluate(clauses, state) == len(clauses):
            return state, True, round_idx + 1

    return state, evaluate(clauses, state) == len(clauses), n_rounds


# ============================================================
# 4. ATTRACTION CASCADE: amplify confident bits, let them pull
# ============================================================

def attraction_cascade(clauses, n, n_rounds=30):
    """
    Start from tension-guided assignment.
    Each round: find the bit MOST ATTRACTED to its current value
    (highest |σ| given current state). Lock it.
    Then: let remaining bits RE-ALIGN to new state.
    Like crystal growth — seed from strongest point, let it spread.
    """
    # Initial: soft beliefs from tension
    beliefs = [0.5 + 0.5 * bit_tension(clauses, n, v) for v in range(n)]

    locked = set()
    state = [1 if b > 0.5 else 0 for b in beliefs]

    for round_idx in range(n):
        # Find strongest unlocked bit (most attracted)
        best_var = None; best_strength = -1
        for var in range(n):
            if var in locked: continue

            # Strength = how many clauses NEED me in current direction
            push_current = 0
            for clause in clauses:
                has_var = False; var_sign = 0
                for v, s in clause:
                    if v == var: has_var = True; var_sign = s
                if not has_var: continue

                others_satisfy = False
                for v, s in clause:
                    if v == var: continue
                    if (s==1 and state[v]==1) or (s==-1 and state[v]==0):
                        others_satisfy = True; break

                if not others_satisfy:
                    # Clause needs me. Does my current value satisfy?
                    if (var_sign==1 and state[var]==1) or (var_sign==-1 and state[var]==0):
                        push_current += 1

            if push_current > best_strength:
                best_strength = push_current
                best_var = var

        if best_var is not None:
            locked.add(best_var)

        # Re-align unlocked bits to current state
        for var in range(n):
            if var in locked: continue
            sat_1 = 0; sat_0 = 0
            for clause in clauses:
                has_var = False
                for v, s in clause:
                    if v == var: has_var = True
                if not has_var: continue
                for test_val in [0, 1]:
                    ts = list(state); ts[var] = test_val
                    if any((s==1 and ts[v]==1) or (s==-1 and ts[v]==0) for v,s in clause):
                        if test_val==1: sat_1 += 1
                        else: sat_0 += 1

            if sat_1 > sat_0: state[var] = 1
            elif sat_0 > sat_1: state[var] = 0

        if evaluate(clauses, state) == len(clauses):
            return state, True, round_idx + 1

    return state, evaluate(clauses, state) == len(clauses), n


# ============================================================
# BENCHMARK
# ============================================================

if __name__ == "__main__":
    random.seed(42)

    print("=" * 70)
    print("SELF-ORGANIZATION: Let bits find their own solution")
    print("=" * 70)

    for n in [12, 16, 20]:
        results = {
            'tension': 0,
            'magnetic': 0,
            'soft_relax': 0,
            'consensus': 0,
            'attraction_cascade': 0,
        }
        total = 0

        n_inst = 100 if n <= 16 else 50
        for seed in range(n_inst):
            clauses = random_3sat(n, int(4.27*n), seed=seed+3000000)
            if n <= 16:
                solutions = find_solutions(clauses, n)
                if not solutions: continue
            total += 1

            # Standard tension
            fixed = {}
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
                fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                results['tension'] += 1

            # Magnetic relaxation
            state = magnetic_relaxation(clauses, n, 50)
            if evaluate(clauses, state) == len(clauses):
                results['magnetic'] += 1

            # Soft relaxation
            beliefs = soft_relaxation(clauses, n, 30, 0.3)
            assignment = [1 if b > 0.5 else 0 for b in beliefs]
            if evaluate(clauses, assignment) == len(clauses):
                results['soft_relax'] += 1

            # Consensus
            state, success, rounds = consensus(clauses, n, 30)
            if success: results['consensus'] += 1

            # Attraction cascade
            state, success, rounds = attraction_cascade(clauses, n, n)
            if success: results['attraction_cascade'] += 1

        print(f"\n  n={n} ({total} instances):")
        for name in sorted(results.keys(), key=lambda k: -results[k]):
            pct = results[name]/total*100
            delta = pct - results['tension']/total*100
            print(f"    {name:>22}: {results[name]:>3}/{total} ({pct:>5.1f}%) {delta:>+6.1f}%")
