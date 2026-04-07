"""
DEEPEST LEVEL: What's below sub-bit?

The bit's tension σ is a single number.
But the bit's COMPLETE state is a FUNCTION:
  σ(context) = tension given any possible set of fixed bits

This function has 2^n possible inputs. But maybe it has
low-dimensional structure — a few parameters capture it.

Also: what about the CONNECTION between bit and clause?
Not the bit, not the clause — the BOND between them.
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
# 1. THE RESPONSE FUNCTION: σ(context) as a surface
# ============================================================

def response_function(clauses, n, var, n_samples=100):
    """
    Sample many random contexts (partial fixations).
    For each: compute σ(var | context).
    This maps out the "response surface" of the bit.

    Measure: mean, variance, skewness, higher moments.
    Also: does σ correlate with the NUMBER of fixed bits?
    """
    responses = []

    for _ in range(n_samples):
        # Random context: fix random subset
        k = random.randint(0, n-2)
        others = random.sample([v for v in range(n) if v != var], k)
        fixed = {v: random.randint(0, 1) for v in others}

        sigma = bit_tension(clauses, n, var, fixed)
        responses.append({
            'sigma': sigma,
            'k_fixed': k,
            'context_size': k,
        })

    sigmas = [r['sigma'] for r in responses]
    if not sigmas:
        return None

    mean_s = sum(sigmas) / len(sigmas)
    var_s = sum((s - mean_s)**2 for s in sigmas) / len(sigmas)
    std_s = math.sqrt(var_s)

    # Skewness
    if std_s > 0:
        skew = sum((s - mean_s)**3 for s in sigmas) / (len(sigmas) * std_s**3)
    else:
        skew = 0

    # Kurtosis
    if std_s > 0:
        kurt = sum((s - mean_s)**4 for s in sigmas) / (len(sigmas) * std_s**4) - 3
    else:
        kurt = 0

    # How σ depends on context size
    by_k = {}
    for r in responses:
        k = r['k_fixed']
        if k not in by_k:
            by_k[k] = []
        by_k[k].append(abs(r['sigma']))

    return {
        'mean': mean_s,
        'std': std_s,
        'skewness': skew,
        'kurtosis': kurt,
        'n_sign_changes': sum(1 for i in range(1, len(sigmas))
                             if sigmas[i] * sigmas[i-1] < 0),
        'frac_positive': sum(1 for s in sigmas if s > 0) / len(sigmas),
        'by_k': by_k,
    }


# ============================================================
# 2. THE BOND: properties of the bit-clause CONNECTION
# ============================================================

def bond_analysis(clauses, n, var):
    """
    For each clause containing var:
    - What ROLE does var play in the clause?
    - Is var the "protagonist" (clause mainly depends on var)?
    - Or the "supporter" (clause is mainly satisfied by others)?

    The bond is not the bit and not the clause — it's the relationship.
    """
    bonds = []
    for ci, clause in enumerate(clauses):
        var_sign = None
        others = []
        for v, s in clause:
            if v == var:
                var_sign = s
            else:
                others.append((v, s, bit_tension(clauses, n, v)))

        if var_sign is None:
            continue

        # Role analysis
        # How essential is var for this clause?
        # If others have strong tension in the satisfying direction → var is supporter
        # If others have weak or wrong tension → var is protagonist

        others_strength = 0
        for v, s, t in others:
            # Does this other literal help satisfy the clause?
            if s == 1 and t > 0:  # positive literal, tension toward 1
                others_strength += abs(t)
            elif s == -1 and t < 0:  # negative literal, tension toward 0
                others_strength += abs(t)
            # else: this literal probably won't help

        var_tension = abs(bit_tension(clauses, n, var))
        total_strength = others_strength + var_tension

        if total_strength > 0:
            var_role = var_tension / total_strength  # 0=pure supporter, 1=pure protagonist
        else:
            var_role = 0.5

        # Bond "tension": does the clause PULL or PUSH the variable?
        # Pull = clause needs var, var is the critical literal
        # Push = clause is already satisfied, var is free
        bond_tension = (1 - others_strength / max(1, others_strength + 0.5)) * var_sign

        bonds.append({
            'clause_idx': ci,
            'var_role': var_role,
            'bond_tension': bond_tension,
            'others_strength': others_strength,
        })

    return bonds


# ============================================================
# 3. RESPONSE DERIVATIVES: how fast does σ change?
# ============================================================

def response_derivatives(clauses, n, var):
    """
    Compute "derivatives" of σ with respect to fixing each neighbor.

    dσ/d(neighbor=1) vs dσ/d(neighbor=0)

    This gives the GRADIENT of the response function.
    Also compute the SECOND derivative: how much does the gradient change?
    """
    sigma_base = bit_tension(clauses, n, var)

    first_derivs = []
    second_derivs = []

    neighbors = set()
    for clause in clauses:
        vs = [v for v, s in clause]
        if var in vs:
            for v in vs:
                if v != var:
                    neighbors.add(v)

    for nb in neighbors:
        # First derivative: σ(nb=1) - σ(nb=0)
        s0 = bit_tension(clauses, n, var, {nb: 0})
        s1 = bit_tension(clauses, n, var, {nb: 1})
        d1 = s1 - s0
        first_derivs.append(d1)

        # Second derivative: for another neighbor nb2,
        # how does d1 change when nb2 is also fixed?
        for nb2 in neighbors:
            if nb2 == nb:
                continue
            s00 = bit_tension(clauses, n, var, {nb: 0, nb2: 0})
            s01 = bit_tension(clauses, n, var, {nb: 0, nb2: 1})
            s10 = bit_tension(clauses, n, var, {nb: 1, nb2: 0})
            s11 = bit_tension(clauses, n, var, {nb: 1, nb2: 1})

            # Second derivative: (s11 - s10) - (s01 - s00)
            d2 = (s11 - s10) - (s01 - s00)
            second_derivs.append(d2)
            break  # just one second deriv per neighbor

    return {
        'first_derivs': first_derivs,
        'avg_abs_d1': sum(abs(d) for d in first_derivs) / len(first_derivs) if first_derivs else 0,
        'max_abs_d1': max(abs(d) for d in first_derivs) if first_derivs else 0,
        'second_derivs': second_derivs,
        'avg_abs_d2': sum(abs(d) for d in second_derivs) / len(second_derivs) if second_derivs else 0,
        'nonlinearity': sum(abs(d) for d in second_derivs) / (sum(abs(d) for d in first_derivs) + 0.001)
                        if first_derivs else 0,
    }


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    instances = []
    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions:
            instances.append((clauses, solutions))

    # --- 1. Response function ---
    print("=" * 70)
    print("1. RESPONSE FUNCTION: The shape of σ(context)")
    print("=" * 70)

    correct_responses = []
    wrong_responses = []

    for clauses, solutions in instances[:80]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            actual = correct_val[var]

            resp = response_function(clauses, n, var, 50)
            if resp is None: continue

            if pred == actual:
                correct_responses.append(resp)
            else:
                wrong_responses.append(resp)

    print(f"\n  {len(correct_responses)} correct, {len(wrong_responses)} wrong")
    print(f"\n  {'property':>20} | {'correct':>10} | {'wrong':>10} | {'ratio':>7} | sig")
    print("  " + "-" * 65)

    for prop in ['std', 'skewness', 'kurtosis', 'n_sign_changes', 'frac_positive']:
        c = mean([r[prop] for r in correct_responses])
        w = mean([r[prop] for r in wrong_responses])
        ratio = w / c if abs(c) > 0.001 else (999 if abs(w) > 0.001 else 1.0)
        sig = "***" if ratio > 1.3 or ratio < 0.77 else ("*" if ratio > 1.15 or ratio < 0.87 else "")
        print(f"  {prop:>20} | {c:>10.4f} | {w:>10.4f} | {ratio:>7.2f} | {sig}")

    # --- 2. Bond analysis ---
    print("\n" + "=" * 70)
    print("2. BONDS: The bit-clause connection")
    print("=" * 70)

    correct_roles = []
    wrong_roles = []

    for clauses, solutions in instances[:80]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            actual = correct_val[var]

            bonds = bond_analysis(clauses, n, var)
            avg_role = mean([b['var_role'] for b in bonds])
            avg_bond_t = mean([abs(b['bond_tension']) for b in bonds])

            entry = {'avg_role': avg_role, 'avg_bond_tension': avg_bond_t}
            if pred == actual:
                correct_roles.append(entry)
            else:
                wrong_roles.append(entry)

    for prop in ['avg_role', 'avg_bond_tension']:
        c = mean([r[prop] for r in correct_roles])
        w = mean([r[prop] for r in wrong_roles])
        ratio = w / c if c > 0 else 1
        print(f"  {prop:>20}: correct={c:.4f}, wrong={w:.4f}, ratio={ratio:.2f}")

    # --- 3. Derivatives ---
    print("\n" + "=" * 70)
    print("3. RESPONSE DERIVATIVES: Gradient and curvature of σ")
    print("=" * 70)

    correct_derivs = []
    wrong_derivs = []

    for clauses, solutions in instances[:60]:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)
            pred = 1 if sigma >= 0 else 0
            actual = correct_val[var]

            derivs = response_derivatives(clauses, n, var)
            if pred == actual:
                correct_derivs.append(derivs)
            else:
                wrong_derivs.append(derivs)

    print(f"\n  {'property':>20} | {'correct':>10} | {'wrong':>10} | {'ratio':>7} | sig")
    print("  " + "-" * 65)

    for prop in ['avg_abs_d1', 'max_abs_d1', 'avg_abs_d2', 'nonlinearity']:
        c = mean([d[prop] for d in correct_derivs])
        w = mean([d[prop] for d in wrong_derivs])
        ratio = w / c if c > 0 else 1
        sig = "***" if ratio > 1.3 or ratio < 0.77 else ("*" if ratio > 1.15 or ratio < 0.87 else "")
        print(f"  {prop:>20} | {c:>10.4f} | {w:>10.4f} | {ratio:>7.2f} | {sig}")

    # --- 4. σ by context size ---
    print("\n" + "=" * 70)
    print("4. HOW σ CHANGES WITH CONTEXT SIZE (# bits fixed)")
    print("=" * 70)

    by_k_correct = {}
    by_k_wrong = {}

    for resp in correct_responses:
        for k, vals in resp['by_k'].items():
            if k not in by_k_correct: by_k_correct[k] = []
            by_k_correct[k].extend(vals)

    for resp in wrong_responses:
        for k, vals in resp['by_k'].items():
            if k not in by_k_wrong: by_k_wrong[k] = []
            by_k_wrong[k].extend(vals)

    print(f"\n  {'k_fixed':>7} | {'|σ| correct':>12} | {'|σ| wrong':>10} | {'ratio':>7}")
    print("  " + "-" * 45)

    for k in sorted(set(list(by_k_correct.keys()) + list(by_k_wrong.keys()))):
        if k > 8: break
        c_vals = by_k_correct.get(k, [])
        w_vals = by_k_wrong.get(k, [])
        if not c_vals or not w_vals: continue
        c = mean(c_vals)
        w = mean(w_vals)
        ratio = w / c if c > 0 else 1
        print(f"  {k:>7} | {c:>12.4f} | {w:>10.4f} | {ratio:>7.2f}")
