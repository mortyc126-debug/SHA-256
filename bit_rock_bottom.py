"""
ROCK BOTTOM: Is there anything below the response function?

We found: σ(context) has volatility, skewness, role.
Below that:
1. Meta-response: how does VOLATILITY change with context depth?
2. Flip triggers: WHAT causes σ to change sign? Which neighbor?
3. Context correlations: are there PATTERNS in which contexts help/hurt?
4. Trajectory shape: sequence σ₁,σ₂,σ₃... as we fix bits one by one
5. Individual clause response: how each clause's contribution changes
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
# 1. META-RESPONSE: volatility of volatility
# ============================================================

def meta_response(clauses, n, var, n_outer=20, n_inner=15):
    """
    For each random context depth k:
      Sample many contexts of size k
      Compute volatility of σ at this depth

    Does volatility CHANGE with depth? Is it smooth or jumpy?
    """
    volatility_by_depth = {}

    for k in range(0, min(n-1, 8)):
        sigmas = []
        for _ in range(n_inner):
            others = random.sample([v for v in range(n) if v != var], k) if k > 0 else []
            fixed = {v: random.randint(0, 1) for v in others}
            sigmas.append(bit_tension(clauses, n, var, fixed))

        if len(sigmas) > 1:
            mean_s = sum(sigmas) / len(sigmas)
            vol = math.sqrt(sum((s-mean_s)**2 for s in sigmas) / len(sigmas))
            sign_flips = sum(1 for i in range(1, len(sigmas)) if sigmas[i]*sigmas[i-1] < 0)
            volatility_by_depth[k] = {
                'volatility': vol,
                'sign_flips': sign_flips / (len(sigmas)-1),
                'mean_sigma': mean_s,
                'mean_abs_sigma': sum(abs(s) for s in sigmas) / len(sigmas),
            }

    return volatility_by_depth


# ============================================================
# 2. FLIP TRIGGERS: what specific neighbor causes σ to flip?
# ============================================================

def flip_triggers(clauses, n, var):
    """
    For each neighbor nb:
    - Does fixing nb=0 vs nb=1 FLIP σ's sign?
    - If yes, nb is a "flip trigger" for var.

    How many flip triggers does each bit have?
    """
    sigma_base = bit_tension(clauses, n, var)
    base_sign = 1 if sigma_base >= 0 else -1

    triggers = []
    neighbors = set()
    for clause in clauses:
        vs = [v for v, s in clause]
        if var in vs:
            for v in vs:
                if v != var: neighbors.add(v)

    for nb in neighbors:
        s0 = bit_tension(clauses, n, var, {nb: 0})
        s1 = bit_tension(clauses, n, var, {nb: 1})

        sign0 = 1 if s0 >= 0 else -1
        sign1 = 1 if s1 >= 0 else -1

        flips_at_0 = (sign0 != base_sign)
        flips_at_1 = (sign1 != base_sign)

        if flips_at_0 or flips_at_1:
            triggers.append({
                'neighbor': nb,
                'flips_at_0': flips_at_0,
                'flips_at_1': flips_at_1,
                'delta_0': s0 - sigma_base,
                'delta_1': s1 - sigma_base,
            })

    return len(triggers), len(neighbors), triggers


# ============================================================
# 3. TRAJECTORY: σ as we fix bits one by one
# ============================================================

def sigma_trajectory(clauses, n, var, correct_val, n_trajectories=10):
    """
    Fix bits in RANDOM order (all correct values), record σ(var) at each step.
    Does σ converge smoothly or oscillate? Is there a "jump"?
    """
    trajectories = []

    for _ in range(n_trajectories):
        order = list(range(n))
        order.remove(var)
        random.shuffle(order)

        fixed = {}
        traj = [bit_tension(clauses, n, var)]

        for step_var in order:
            fixed[step_var] = correct_val[step_var]
            traj.append(bit_tension(clauses, n, var, fixed))

        trajectories.append(traj)

    return trajectories


# ============================================================
# 4. PER-CLAUSE response decomposition
# ============================================================

def clause_response(clauses, n, var, n_contexts=20):
    """
    For each clause containing var:
    Track its contribution to σ across random contexts.
    Does each clause respond independently or are they correlated?
    """
    my_clauses = []
    for ci, clause in enumerate(clauses):
        for v, s in clause:
            if v == var:
                my_clauses.append((ci, s))
                break

    if len(my_clauses) < 2:
        return None

    # For each context, compute each clause's contribution
    contributions = {ci: [] for ci, s in my_clauses}

    for _ in range(n_contexts):
        k = random.randint(0, n-2)
        others = random.sample([v for v in range(n) if v != var], k) if k > 0 else []
        fixed = {v: random.randint(0, 1) for v in others}

        for ci, my_sign in my_clauses:
            clause = clauses[ci]
            already_sat = False
            remaining = []
            for v, s in clause:
                if v in fixed:
                    if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                        already_sat = True; break
                else:
                    remaining.append((v,s))

            if already_sat:
                contributions[ci].append(0)  # clause satisfied, no vote
            else:
                w = 1.0 / max(1, len(remaining))
                contributions[ci].append(my_sign * w)

    # Correlation between clause contributions
    clause_ids = [ci for ci, s in my_clauses]
    correlations = []
    for i in range(len(clause_ids)):
        for j in range(i+1, len(clause_ids)):
            ci, cj = clause_ids[i], clause_ids[j]
            vi = contributions[ci]
            vj = contributions[cj]
            mi = sum(vi)/len(vi)
            mj = sum(vj)/len(vj)
            si = math.sqrt(sum((v-mi)**2 for v in vi)/len(vi))
            sj = math.sqrt(sum((v-mj)**2 for v in vj)/len(vj))
            if si > 0.001 and sj > 0.001:
                cov = sum((vi[k]-mi)*(vj[k]-mj) for k in range(len(vi)))/len(vi)
                correlations.append(cov/(si*sj))

    return {
        'n_clauses': len(my_clauses),
        'avg_clause_corr': sum(correlations)/len(correlations) if correlations else 0,
        'max_clause_corr': max(correlations) if correlations else 0,
        'min_clause_corr': min(correlations) if correlations else 0,
        'frac_positive_corr': sum(1 for c in correlations if c > 0.1)/len(correlations) if correlations else 0,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    instances = []
    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions:
            instances.append((clauses, solutions))

    # --- 1. Meta-response ---
    print("=" * 70)
    print("1. META-RESPONSE: How does volatility change with depth?")
    print("=" * 70)

    correct_vol = {k: [] for k in range(8)}
    wrong_vol = {k: [] for k in range(8)}

    for clauses, solutions in instances[:50]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            is_correct = pred == correct_val[var]

            meta = meta_response(clauses, n, var)
            target = correct_vol if is_correct else wrong_vol
            for k, data in meta.items():
                if k < 8:
                    target[k].append(data['volatility'])

    print(f"\n  {'depth':>5} | {'vol correct':>11} | {'vol wrong':>10} | {'ratio':>7}")
    print("  " + "-" * 45)
    for k in range(8):
        c = mean(correct_vol[k])
        w = mean(wrong_vol[k])
        ratio = w / c if c > 0 else 1
        print(f"  {k:>5} | {c:>11.4f} | {w:>10.4f} | {ratio:>7.2f}")

    # --- 2. Flip triggers ---
    print("\n" + "=" * 70)
    print("2. FLIP TRIGGERS: How many neighbors can flip σ?")
    print("=" * 70)

    correct_triggers = []
    wrong_triggers = []

    for clauses, solutions in instances[:80]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0

            n_triggers, n_neighbors, _ = flip_triggers(clauses, n, var)
            frac = n_triggers / n_neighbors if n_neighbors > 0 else 0

            if pred == correct_val[var]:
                correct_triggers.append(frac)
            else:
                wrong_triggers.append(frac)

    print(f"\n  Fraction of neighbors that can flip σ:")
    print(f"    Correct bits: {mean(correct_triggers):.4f}")
    print(f"    Wrong bits:   {mean(wrong_triggers):.4f}")
    print(f"    Ratio: {mean(wrong_triggers)/mean(correct_triggers):.2f}"
          if mean(correct_triggers) > 0 else "")

    # --- 3. Trajectory ---
    print("\n" + "=" * 70)
    print("3. TRAJECTORY: σ path as we fix bits correctly")
    print("=" * 70)

    correct_traj_smoothness = []
    wrong_traj_smoothness = []

    for clauses, solutions in instances[:40]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0

            trajectories = sigma_trajectory(clauses, n, var, correct_val, 5)

            for traj in trajectories:
                # Smoothness: how many direction changes?
                changes = sum(1 for i in range(1, len(traj)) if traj[i]*traj[i-1] < 0)
                smoothness = 1 - changes / (len(traj) - 1) if len(traj) > 1 else 1

                if pred == correct_val[var]:
                    correct_traj_smoothness.append(smoothness)
                else:
                    wrong_traj_smoothness.append(smoothness)

    print(f"\n  Trajectory smoothness (1=never flips, 0=always flips):")
    print(f"    Correct bits: {mean(correct_traj_smoothness):.4f}")
    print(f"    Wrong bits:   {mean(wrong_traj_smoothness):.4f}")
    print(f"    Ratio: {mean(wrong_traj_smoothness)/mean(correct_traj_smoothness):.2f}"
          if mean(correct_traj_smoothness) > 0 else "")

    # --- 4. Clause correlations ---
    print("\n" + "=" * 70)
    print("4. CLAUSE RESPONSE CORRELATIONS")
    print("=" * 70)

    correct_corrs = []
    wrong_corrs = []

    for clauses, solutions in instances[:60]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0

            cr = clause_response(clauses, n, var, 20)
            if cr is None: continue

            if pred == correct_val[var]:
                correct_corrs.append(cr)
            else:
                wrong_corrs.append(cr)

    print(f"\n  {'property':>25} | {'correct':>10} | {'wrong':>10} | {'ratio':>7}")
    print("  " + "-" * 60)

    for prop in ['avg_clause_corr', 'max_clause_corr', 'frac_positive_corr']:
        c = mean([r[prop] for r in correct_corrs])
        w = mean([r[prop] for r in wrong_corrs])
        ratio = w / c if abs(c) > 0.001 else 1
        sig = "***" if ratio > 1.3 or ratio < 0.77 else ""
        print(f"  {prop:>25} | {c:>10.4f} | {w:>10.4f} | {ratio:>7.2f} {sig}")
