"""
BIT MECHANICS — Formal Equations

Building a mathematical framework from empirical laws.
Each equation is derived, then tested against data.
Goal: find inconsistencies or unexpected predictions.
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
# EQUATION 1: Single-bit accuracy
#   A(d, ε) = P(Bin(d, 0.5 + ε) > d/2)
# ============================================================

def eq1_accuracy(d, eps):
    """Predicted accuracy for a bit with degree d and bias ε."""
    p_correct = 0
    pe = 0.5 + eps
    for k in range(d + 1):
        prob_k = math.exp(
            math.lgamma(d+1) - math.lgamma(k+1) - math.lgamma(d-k+1) +
            k*math.log(max(pe, 1e-10)) + (d-k)*math.log(max(1-pe, 1e-10))
        )
        if k > d/2:
            p_correct += prob_k
        elif k == d/2 and d % 2 == 0:
            p_correct += prob_k * 0.5
    return p_correct


# ============================================================
# EQUATION 2: Epsilon as function of ratio
#   ε(r) = ?
#
# From data: ε decreases with ratio.
# Physical reasoning: more clauses → more constraints → less bias per clause
# because each clause constrains less when there are many alternatives.
#
# Hypothesis: ε(r) ≈ c / sqrt(r) or ε(r) ≈ c / r
# ============================================================

def measure_epsilon(n, ratio, n_trials=200):
    epsilons = []
    for seed in range(n_trials):
        clauses = random_3sat(n, int(ratio*n), seed=seed+9000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        for var in range(n):
            actual = 1 if prob_1[var] > 0.5 else 0
            pos = sum(1 for cl in clauses for v, s in cl if v==var and s==1)
            neg = sum(1 for cl in clauses for v, s in cl if v==var and s==-1)
            d = pos+neg
            if d == 0: continue
            if actual == 1: epsilons.append(pos/d - 0.5)
            else: epsilons.append(neg/d - 0.5)
    return sum(epsilons)/len(epsilons) if epsilons else 0


# ============================================================
# EQUATION 3: Amplification under correct fixation
#
# After fixing k bits correctly, remaining bits see a REDUCED problem.
# m_eff = m - (clauses satisfied by fixed bits)
# n_eff = n - k
# r_eff = m_eff / n_eff
#
# If r_eff < r_original, the problem is EASIER → accuracy should increase.
# But: which clauses get satisfied depends on WHICH bits we fix.
# ============================================================

def measure_effective_ratio(clauses, n, k_fixed, correct_val):
    """After fixing k most confident bits correctly, what's the effective ratio?"""
    order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))
    fixed = {order[i]: correct_val[order[i]] for i in range(k_fixed)}

    active_clauses = 0
    for clause in clauses:
        satisfied = False
        for v, s in clause:
            if v in fixed:
                if (s==1 and fixed[v]==1) or (s==-1 and fixed[v]==0):
                    satisfied = True; break
        if not satisfied:
            active_clauses += 1

    n_eff = n - k_fixed
    r_eff = active_clauses / n_eff if n_eff > 0 else 0
    return r_eff, active_clauses, n_eff


# ============================================================
# EQUATION 4: Temperature
#   T = 1 - <|σ|> = 1 - E[|2X/d - 1|] where X ~ Bin(d, 0.5+ε)
#
# Can we derive T from ε and d?
# ============================================================

def eq4_temperature(d, eps):
    """Predicted temperature from d and ε."""
    expected_abs_sigma = 0
    pe = 0.5 + eps
    for k in range(d+1):
        prob_k = math.exp(
            math.lgamma(d+1) - math.lgamma(k+1) - math.lgamma(d-k+1) +
            k*math.log(max(pe, 1e-10)) + (d-k)*math.log(max(1-pe, 1e-10))
        )
        sigma = abs(2*k/d - 1) if d > 0 else 0
        expected_abs_sigma += prob_k * sigma
    return 1 - expected_abs_sigma


# ============================================================
# EQUATION 5: Contradiction rate
#
# Two-step path i → j → k.
# Path 1: fix i, read j's tension, fix j, read k's tension.
# Path 2: fix i, read j2's tension, fix j2, read k's tension.
#
# Contradiction = paths give opposite directions for k.
#
# If j and j2 are independent given i, and each has accuracy A,
# then:
#   P(both point same way) = A² + (1-A)²
#   P(contradict) = 2A(1-A)
# ============================================================

def eq5_contradiction_rate(accuracy):
    """Predicted contradiction rate from single-step accuracy."""
    return 2 * accuracy * (1 - accuracy)


# ============================================================
# EQUATION 6: Error clustering
#
# If errors are independent: P(both wrong) = p_wrong²
# If clustered: P(both wrong | neighbors) = p_wrong² * lift
# We measured lift ≈ 1.23 for neighbors, 1.15 cross-instance.
#
# Can we derive the lift from ε?
# ============================================================

def eq6_error_lift(eps, d_shared):
    """
    Two bits sharing d_shared clauses.
    If bit A is wrong, its clauses voted opposite to correct.
    Bits in those shared clauses see "wrong" votes too.
    This increases P(B wrong | A wrong).

    Model: B's effective ε is reduced by the shared wrong influence.
    """
    # If A is wrong, the d_shared shared clauses have signs opposite to A's correct value.
    # For B, these clauses push B in A's wrong direction.
    # B has d_B total clauses. d_shared of them are "corrupted".
    # B's effective ε ≈ ε * (d_B - 2*d_shared) / d_B
    # (because shared clauses now vote wrong for B too, with prob proportional to correlation)
    pass  # Complex — derive empirically below


# ============================================================
# EQUATION 7: v4 convergence
#
# v4 iteratively refines tension using neighbor info.
# Each iteration is like one round of belief propagation.
# How fast does it converge?
#
# Model: accuracy after t iterations ≈ A_inf - (A_inf - A_0) * λ^t
# where λ is the convergence rate.
# ============================================================

def measure_v4_convergence(clauses, n, solutions):
    """Measure accuracy at each iteration of v4."""
    if not solutions: return None
    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
    results = []

    for iteration in range(20):
        correct = sum(1 for v in range(n) if (1 if tensions[v] >= 0 else 0) == correct_val[v])
        results.append(correct / n)

        # One v4 step
        new_t = {}
        for var in range(n):
            push_1, push_0 = 0.0, 0.0
            for clause in clauses:
                rem = []; vs = None
                for v, s in clause:
                    rem.append((v,s))
                    if v == var: vs = s
                if vs is None: continue
                oh = 0.0
                for v, s in rem:
                    if v == var: continue
                    t = tensions.get(v, 0)
                    p = (1+t)/2 if s == 1 else (1-t)/2
                    oh = 1-(1-oh)*(1-p)
                need = 1.0-oh
                if vs == 1: push_1 += need
                else: push_0 += need
            tot = push_1+push_0
            new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
        for v in tensions:
            tensions[v] = 0.5*tensions[v] + 0.5*new_t.get(v, 0)

    return results


# ============================================================
# MAIN: Build equations, derive predictions, test
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    print("=" * 75)
    print("BIT MECHANICS — FORMAL EQUATIONS")
    print("=" * 75)

    # --- Eq 2: ε(r) ---
    print("\n## Equation 2: ε as function of ratio")
    print(f"  {'ratio':>6} | {'ε measured':>10} | {'c/sqrt(r)':>9} | {'c/r':>9}")
    print("  " + "-" * 45)

    eps_data = []
    for ratio_10 in range(15, 55, 5):
        ratio = ratio_10 / 10.0
        eps = measure_epsilon(n, ratio, 200)
        eps_data.append((ratio, eps))

    # Fit c/sqrt(r) and c/r
    c_sqrt = sum(eps * math.sqrt(r) for r, eps in eps_data) / len(eps_data)
    c_lin = sum(eps * r for r, eps in eps_data) / len(eps_data)

    for ratio, eps in eps_data:
        pred_sqrt = c_sqrt / math.sqrt(ratio)
        pred_lin = c_lin / ratio
        print(f"  {ratio:>6.1f} | {eps:>+10.4f} | {pred_sqrt:>+9.4f} | {pred_lin:>+9.4f}")

    # Which fits better?
    err_sqrt = sum((eps - c_sqrt/math.sqrt(r))**2 for r, eps in eps_data)
    err_lin = sum((eps - c_lin/r)**2 for r, eps in eps_data)
    print(f"\n  Fit error: c/sqrt(r) = {err_sqrt:.6f}, c/r = {err_lin:.6f}")
    print(f"  Better fit: {'c/sqrt(r)' if err_sqrt < err_lin else 'c/r'}")
    print(f"  Constants: c_sqrt = {c_sqrt:.4f}, c_lin = {c_lin:.4f}")

    # --- Eq 1+2: Combined accuracy prediction ---
    print("\n## Equations 1+2: Predicted vs measured accuracy")
    print(f"  {'ratio':>6} | {'measured':>8} | {'predicted':>9} | {'error':>7}")
    print("  " + "-" * 40)

    for ratio, eps in eps_data:
        d = int(round(3 * ratio))
        predicted = eq1_accuracy(d, eps)

        # Measure actual
        correct = 0; total = 0
        for seed in range(200):
            clauses = random_3sat(n, int(ratio*n), seed=seed+9000)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            for var in range(n):
                sigma = bit_tension(clauses, n, var)
                actual = 1 if prob_1[var] > 0.5 else 0
                if (1 if sigma >= 0 else 0) == actual: correct += 1
                total += 1

        measured = correct/total if total > 0 else 0
        error = abs(predicted - measured) * 100
        print(f"  {ratio:>6.1f} | {measured*100:>7.1f}% | {predicted*100:>8.1f}% | {error:>6.1f}%")

    # --- Eq 3: Amplification via effective ratio ---
    print("\n## Equation 3: Amplification = effective ratio reduction")
    print(f"  {'k':>4} | {'r_eff':>6} | {'ε(r_eff)':>8} | {'pred_acc':>9} | {'meas_acc':>9}")
    print("  " + "-" * 50)

    for k in range(7):
        r_effs = []
        measured_accs = []

        for seed in range(200):
            clauses = random_3sat(n, int(4.27*n), seed=seed+9000)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
            correct_val = [1 if p > 0.5 else 0 for p in prob_1]

            r_eff, _, n_eff = measure_effective_ratio(clauses, n, k, correct_val)
            r_effs.append(r_eff)

            # Measure accuracy of remaining
            order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))
            fixed = {order[i]: correct_val[order[i]] for i in range(k)}
            correct = 0; rem_total = 0
            for var in range(n):
                if var in fixed: continue
                sigma = bit_tension(clauses, n, var, fixed)
                if (1 if sigma >= 0 else 0) == correct_val[var]: correct += 1
                rem_total += 1
            if rem_total > 0:
                measured_accs.append(correct/rem_total)

        avg_r_eff = sum(r_effs)/len(r_effs) if r_effs else 0
        avg_meas = sum(measured_accs)/len(measured_accs) if measured_accs else 0

        # Predict from effective ratio
        d_eff = int(round(3 * avg_r_eff))
        eps_eff = c_lin / avg_r_eff if avg_r_eff > 0 else 0.1
        pred_acc = eq1_accuracy(max(d_eff, 1), min(eps_eff, 0.49))

        print(f"  {k:>4} | {avg_r_eff:>6.2f} | {eps_eff:>+8.4f} | "
              f"{pred_acc*100:>8.1f}% | {avg_meas*100:>8.1f}%")

    # --- Eq 4: Temperature derivation ---
    print("\n## Equation 4: Temperature from ε and d")
    print(f"  {'ratio':>6} | {'T measured':>10} | {'T predicted':>11} | {'error':>7}")
    print("  " + "-" * 45)

    for ratio, eps in eps_data:
        d = int(round(3 * ratio))
        T_pred = eq4_temperature(d, eps)

        # Measure
        T_vals = []
        for seed in range(200):
            clauses = random_3sat(n, int(ratio*n), seed=seed+9000)
            for var in range(n):
                sigma = bit_tension(clauses, n, var)
                T_vals.append(1 - abs(sigma))

        T_meas = sum(T_vals)/len(T_vals) if T_vals else 0
        error = abs(T_pred - T_meas) * 100
        print(f"  {ratio:>6.1f} | {T_meas:>10.4f} | {T_pred:>11.4f} | {error:>6.1f}%")

    # --- Eq 5: Contradiction rate ---
    print("\n## Equation 5: Contradiction rate from accuracy")
    print(f"  {'ratio':>6} | {'accuracy':>8} | {'pred_contr':>10} | {'meas_contr':>10}")
    print("  " + "-" * 50)

    for ratio in [2.0, 3.0, 4.0, 4.27]:
        # Measure accuracy and contradiction rate
        correct_count = 0; total_count = 0
        consistent = 0; contradictory = 0

        for seed in range(100):
            clauses = random_3sat(n, int(ratio*n), seed=seed+9000)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]

            for var in range(n):
                sigma = bit_tension(clauses, n, var)
                actual = 1 if prob_1[var] > 0.5 else 0
                if (1 if sigma >= 0 else 0) == actual: correct_count += 1
                total_count += 1

            # Contradiction measurement (simplified)
            adj = {i: set() for i in range(n)}
            for clause in clauses:
                vs = [v for v, s in clause]
                for a in range(len(vs)):
                    for b in range(a+1, len(vs)):
                        adj[vs[a]].add(vs[b])
                        adj[vs[b]].add(vs[a])

            for src in range(min(n, 4)):
                sigma_s = bit_tension(clauses, n, src)
                v_s = 1 if sigma_s >= 0 else 0
                for tgt in range(n):
                    if tgt == src: continue
                    intermediaries = [j for j in adj[src] if j in adj[tgt] and j != src and j != tgt]
                    if len(intermediaries) < 2: continue
                    sigs = []
                    for j in intermediaries:
                        sj = bit_tension(clauses, n, j, {src: v_s})
                        vj = 1 if sj >= 0 else 0
                        sk = bit_tension(clauses, n, tgt, {src: v_s, j: vj})
                        sigs.append(sk)
                    dirs = [1 if s > 0.01 else (-1 if s < -0.01 else 0) for s in sigs]
                    nz = [d for d in dirs if d != 0]
                    if nz and all(d == nz[0] for d in nz): consistent += 1
                    elif nz and len(set(nz)) > 1: contradictory += 1

        acc = correct_count/total_count if total_count > 0 else 0.5
        total_paths = consistent + contradictory
        meas_contr = contradictory/total_paths if total_paths > 0 else 0
        pred_contr = eq5_contradiction_rate(acc)

        print(f"  {ratio:>6.1f} | {acc*100:>7.1f}% | {pred_contr*100:>9.1f}% | "
              f"{meas_contr*100:>9.1f}%")

    # --- Eq 7: v4 convergence ---
    print("\n## Equation 7: v4 convergence curve")

    all_curves = []
    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed+9000)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        curve = measure_v4_convergence(clauses, n, solutions)
        if curve: all_curves.append(curve)

    if all_curves:
        max_iter = min(len(c) for c in all_curves)
        print(f"\n  {'iter':>4} | {'accuracy':>8} | {'Δ':>8}")
        print("  " + "-" * 25)
        prev = 0
        for t in range(max_iter):
            avg = sum(c[t] for c in all_curves) / len(all_curves)
            delta = avg - prev
            print(f"  {t:>4} | {avg*100:>7.1f}% | {delta*100:>+7.2f}%")
            prev = avg
