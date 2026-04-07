"""
NEW INSTRUMENTS: Measuring bit signal with tools from our theory.

Old instrument: σ = clause vote balance (1960s tech).
New instruments built from Bit Mechanics:

I1. ATTRACTION SIGNAL: σ × self-consistency score
I2. CONTEXT SIGNAL: σ conditioned on neighbor states
I3. CLONE SIGNAL: if clone exists, use strongest signal
I4. COLLAPSE SIGNAL: how much does fixing me clarify neighbors?
I5. ANTI-SIGNAL: inverted clause topology
I6. RESONANCE SIGNAL: do neighbors AGREE about my direction?
I7. MULTI-SCALE: combine all instruments

For each: measure per-bit accuracy. Compare to σ.
Then: look for signals σ MISSES.
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


def get_neighbors(clauses, n, var):
    nbs = set()
    for clause in clauses:
        vs = [v for v,s in clause]
        if var in vs:
            for v in vs:
                if v != var: nbs.add(v)
    return nbs


# ============================================================
# INSTRUMENT 1: ATTRACTION SIGNAL
# σ × |σ + avg(nb)| — direction × consistency
# ============================================================

def attraction_signal(clauses, n, var, tensions):
    nbs = get_neighbors(clauses, n, var)
    nb_avg = sum(tensions[nb] for nb in nbs) / len(nbs) if nbs else 0
    consistency = abs(tensions[var] + nb_avg)
    return tensions[var] * (0.3 + consistency)


# ============================================================
# INSTRUMENT 2: CONTEXT SIGNAL
# σ averaged over neighbor-conditioned tensions
# ============================================================

def context_signal(clauses, n, var, tensions):
    nbs = list(get_neighbors(clauses, n, var))[:3]
    if not nbs: return tensions[var]

    # Sample a few neighbor contexts
    context_tensions = []
    for _ in range(8):
        fixed = {nb: (1 if tensions[nb] >= 0 else 0)
                 if random.random() > 0.3
                 else random.randint(0,1)
                 for nb in nbs}
        ct = bit_tension(clauses, n, var, fixed)
        context_tensions.append(ct)

    # Weighted average: weight by |ct| (confident contexts count more)
    w_sum = sum(ct * abs(ct) for ct in context_tensions)
    w_total = sum(abs(ct) for ct in context_tensions)
    return w_sum / w_total if w_total > 0 else tensions[var]


# ============================================================
# INSTRUMENT 3: CLONE SIGNAL
# If clone exists with higher |σ|, use that
# ============================================================

def clone_signal(clauses, n, var, tensions, assignments):
    # Find clone from multi-run agreement
    best_sig = tensions[var]
    for other in range(n):
        if other == var: continue
        agree = sum(1 for a in assignments if a[var] == a[other])
        frac = agree / len(assignments)
        if frac > 0.85 and abs(tensions[other]) > abs(best_sig):
            best_sig = tensions[other]  # clone, use stronger signal
        elif frac < 0.15 and abs(tensions[other]) > abs(best_sig):
            best_sig = -tensions[other]  # anti-clone, invert

    return best_sig


# ============================================================
# INSTRUMENT 4: COLLAPSE SIGNAL
# How much clarity does fixing this bit create?
# ============================================================

def collapse_signal(clauses, n, var, tensions):
    val = 1 if tensions[var] >= 0 else 0
    nbs = get_neighbors(clauses, n, var)

    clarity_1 = 0; clarity_0 = 0
    for nb in list(nbs)[:4]:
        s1 = abs(bit_tension(clauses, n, nb, {var: 1}))
        s0 = abs(bit_tension(clauses, n, nb, {var: 0}))
        clarity_1 += s1
        clarity_0 += s0

    # Direction: which value creates MORE clarity?
    if clarity_1 > clarity_0:
        return abs(tensions[var]) * 1.0  # val=1 is more clarifying → positive
    else:
        return -abs(tensions[var]) * 1.0


# ============================================================
# INSTRUMENT 5: ANTI-SIGNAL
# Inverted clause topology (L15)
# ============================================================

def anti_signal(clauses, n, var, tensions):
    # For each clause pair sharing var: inverted sign pattern
    inv_push_1 = 0; inv_push_0 = 0

    my_clauses = [(ci, clause) for ci, clause in enumerate(clauses)
                  if any(v == var for v, s in clause)]

    for a in range(len(my_clauses)):
        for b in range(a+1, len(my_clauses)):
            ci, cl_a = my_clauses[a]
            cj, cl_b = my_clauses[b]

            signs_a = {v: s for v, s in cl_a}
            signs_b = {v: s for v, s in cl_b}
            shared = set(signs_a.keys()) & set(signs_b.keys()) - {var}

            for sv in shared:
                # Same signs in both clauses → INVERTED → push AGAINST
                if signs_a[sv] == signs_b[sv]:
                    # Shared var has same sign → evidence they're anti-clones
                    # → our bit should go OPPOSITE to what clauses suggest for sv
                    if signs_a[var] == signs_a[sv]:
                        inv_push_0 += 0.1  # push away from matching
                    else:
                        inv_push_1 += 0.1

    total = inv_push_1 + inv_push_0
    return (inv_push_1 - inv_push_0) / total if total > 0 else 0


# ============================================================
# INSTRUMENT 6: RESONANCE SIGNAL
# Do neighbors' tensions COHERENTLY point the same way about me?
# ============================================================

def resonance_signal(clauses, n, var, tensions):
    nbs = get_neighbors(clauses, n, var)
    if not nbs: return tensions[var]

    # Each neighbor "votes" for var's value through shared clauses
    votes = []
    for nb in nbs:
        # In shared clauses: what sign does nb's tension imply for var?
        for clause in clauses:
            signs = {v: s for v, s in clause}
            if var in signs and nb in signs:
                nb_dir = 1 if tensions[nb] >= 0 else -1
                # If nb points same direction as its sign → clause satisfied by nb
                nb_satisfies = (signs[nb] == 1 and nb_dir == 1) or (signs[nb] == -1 and nb_dir == -1)
                if nb_satisfies:
                    # Clause already helped by nb → less pressure on var
                    votes.append(0)
                else:
                    # Clause needs var → var should satisfy it
                    votes.append(signs[var])

    if not votes: return tensions[var]
    return sum(votes) / len(votes)


# ============================================================
# BENCHMARK ALL INSTRUMENTS
# ============================================================

def benchmark():
    random.seed(42); n = 12

    print("=" * 70)
    print("NEW INSTRUMENTS: Per-bit accuracy comparison")
    print("=" * 70)

    instruments = {
        'σ (standard)': 0,
        'I1 attraction': 0,
        'I2 context': 0,
        'I3 clone': 0,
        'I4 collapse': 0,
        'I5 anti-sign': 0,
        'I6 resonance': 0,
        'I7 combined': 0,
    }
    total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # Multi-run assignments for clone detection
        assignments = []
        for run in range(10):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(tensions[v]) + random.gauss(0, 0.15)))
            for var in order:
                if var in fixed: continue
                sigma = bit_tension(clauses, n, var, fixed)
                fixed[var] = 1 if sigma >= 0 else 0
            assignments.append([fixed.get(v,0) for v in range(n)])

        for var in range(n):
            total += 1
            actual = correct_val[var]

            # Standard σ
            s0 = tensions[var]
            if (1 if s0 >= 0 else 0) == actual: instruments['σ (standard)'] += 1

            # I1: attraction
            s1 = attraction_signal(clauses, n, var, tensions)
            if (1 if s1 >= 0 else 0) == actual: instruments['I1 attraction'] += 1

            # I2: context
            s2 = context_signal(clauses, n, var, tensions)
            if (1 if s2 >= 0 else 0) == actual: instruments['I2 context'] += 1

            # I3: clone
            s3 = clone_signal(clauses, n, var, tensions, assignments)
            if (1 if s3 >= 0 else 0) == actual: instruments['I3 clone'] += 1

            # I4: collapse
            s4 = collapse_signal(clauses, n, var, tensions)
            if (1 if s4 >= 0 else 0) == actual: instruments['I4 collapse'] += 1

            # I5: anti-sign
            s5 = anti_signal(clauses, n, var, tensions)
            if abs(s5) > 0.001:
                if (1 if s5 >= 0 else 0) == actual: instruments['I5 anti-sign'] += 1
            else:
                if (1 if s0 >= 0 else 0) == actual: instruments['I5 anti-sign'] += 1

            # I6: resonance
            s6 = resonance_signal(clauses, n, var, tensions)
            if (1 if s6 >= 0 else 0) == actual: instruments['I6 resonance'] += 1

            # I7: combined — weighted vote of all
            signals = [s0, s1, s2, s3, s6]
            combined = sum(s * abs(s) for s in signals)  # weight by confidence
            if (1 if combined >= 0 else 0) == actual: instruments['I7 combined'] += 1

    print(f"\n  Total bits tested: {total}")
    print(f"\n  {'instrument':>20} | {'accuracy':>8} | {'vs σ':>8}")
    print("  " + "-" * 40)

    base = instruments['σ (standard)'] / total * 100
    for name in sorted(instruments.keys(), key=lambda k: -instruments[k]):
        acc = instruments[name] / total * 100
        delta = acc - base
        marker = " ★" if delta > 2 else (" ★★" if delta > 5 else "")
        print(f"  {name:>20} | {acc:>7.1f}% | {delta:>+7.1f}%{marker}")

    # For bits where σ is WRONG: which instrument gets them right?
    print(f"\n  WRONG-σ RESCUE: Which instrument saves wrong bits?")
    wrong_saves = {name: 0 for name in instruments if name != 'σ (standard)'}
    wrong_total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        assignments = []
        for run in range(10):
            fixed = {}
            order = list(range(n))
            order.sort(key=lambda v: -(abs(tensions[v]) + random.gauss(0, 0.15)))
            for var in order:
                if var in fixed: continue
                fixed[var] = 1 if bit_tension(clauses, n, var, fixed) >= 0 else 0
            assignments.append([fixed.get(v,0) for v in range(n)])

        for var in range(n):
            actual = correct_val[var]
            if (1 if tensions[var] >= 0 else 0) == actual: continue  # σ correct, skip
            wrong_total += 1

            s1 = attraction_signal(clauses, n, var, tensions)
            if (1 if s1 >= 0 else 0) == actual: wrong_saves['I1 attraction'] += 1

            s2 = context_signal(clauses, n, var, tensions)
            if (1 if s2 >= 0 else 0) == actual: wrong_saves['I2 context'] += 1

            s3 = clone_signal(clauses, n, var, tensions, assignments)
            if (1 if s3 >= 0 else 0) == actual: wrong_saves['I3 clone'] += 1

            s6 = resonance_signal(clauses, n, var, tensions)
            if (1 if s6 >= 0 else 0) == actual: wrong_saves['I6 resonance'] += 1

    print(f"\n  Wrong-σ bits: {wrong_total}")
    print(f"  {'instrument':>20} | {'rescues':>8}")
    print("  " + "-" * 35)
    for name in sorted(wrong_saves.keys(), key=lambda k: -wrong_saves[k]):
        pct = wrong_saves[name]/wrong_total*100 if wrong_total > 0 else 0
        print(f"  {name:>20} | {pct:>7.1f}%")


if __name__ == "__main__":
    benchmark()
