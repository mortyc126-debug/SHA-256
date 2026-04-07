"""
TWO IDEAS:

IDEA 1: INVERSION — if self-organization finds WRONG answers consistently,
INVERT them to get right answers. 2/50 wrong → 48/50 right?

IDEA 2: SELECTIVE LISTENING — bits communicate, but ignore
neighbors that seem wrong. Like a racia: only trust clear signals.
"""

import random
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
# IDEA 1: INVERSION — flip the self-organized result
# ============================================================

def magnetic_relaxation(clauses, n, max_steps=50):
    state = [random.randint(0,1) for _ in range(n)]
    for step in range(max_steps * n):
        var = random.randint(0, n-1)
        push_1 = 0; push_0 = 0
        for clause in clauses:
            has_var = False; var_sign = 0; others_satisfy = False
            for v, s in clause:
                if v == var: has_var = True; var_sign = s
                else:
                    if (s==1 and state[v]==1) or (s==-1 and state[v]==0):
                        others_satisfy = True
            if not has_var: continue
            if others_satisfy: continue
            if var_sign == 1: push_1 += 1
            else: push_0 += 1
        if push_1 > push_0: state[var] = 1
        elif push_0 > push_1: state[var] = 0
    return state


def test_inversion():
    print("=" * 70)
    print("IDEA 1: INVERSION — flip the failed result")
    print("=" * 70)

    random.seed(42); n = 12

    for n_test in [12, 16, 20]:
        results = {
            'tension': 0, 'magnetic': 0, 'inverted': 0,
            'per_bit_inv': 0, 'smart_inv': 0, 'total': 0
        }

        n_inst = 100 if n_test <= 16 else 50
        for seed in range(n_inst):
            clauses = random_3sat(n_test, int(4.27*n_test), seed=seed+4000000)
            if n_test <= 16:
                solutions = find_solutions(clauses, n_test)
                if not solutions: continue
            results['total'] += 1

            # Standard tension
            fixed = {}
            for step in range(n_test):
                unfixed = [v for v in range(n_test) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n_test, v, fixed)))
                fixed[best] = 1 if bit_tension(clauses, n_test, best, fixed) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n_test)]) == len(clauses):
                results['tension'] += 1

            # Magnetic relaxation
            state = magnetic_relaxation(clauses, n_test, 50)
            sat_magnetic = evaluate(clauses, state)
            if sat_magnetic == len(clauses):
                results['magnetic'] += 1

            # FULL INVERSION: flip every bit
            inverted = [1 - state[v] for v in range(n_test)]
            if evaluate(clauses, inverted) == len(clauses):
                results['inverted'] += 1

            # PER-BIT INVERSION: compare magnetic with tension, flip disagreements
            tensions = {v: bit_tension(clauses, n_test, v) for v in range(n_test)}
            per_bit_inv = list(state)
            for v in range(n_test):
                tension_pred = 1 if tensions[v] >= 0 else 0
                if state[v] != tension_pred:
                    # Magnetic and tension disagree → flip to tension
                    per_bit_inv[v] = tension_pred
            if evaluate(clauses, per_bit_inv) == len(clauses):
                results['per_bit_inv'] += 1

            # SMART INVERSION: run magnetic MANY times, find bits that
            # consistently go WRONG (always same value). Flip those.
            multi_magnetic = []
            for run in range(10):
                s = magnetic_relaxation(clauses, n_test, 30)
                multi_magnetic.append(s)

            # Per-bit: if magnetic ALWAYS picks same value → it's attracted there
            # But if that value disagrees with tension → INVERT it
            smart = list(state)
            for v in range(n_test):
                mag_vals = [m[v] for m in multi_magnetic]
                mag_frac = sum(mag_vals) / len(mag_vals)

                # If magnetic is very consistent (>80% same) BUT disagrees with tension
                tension_pred = 1 if tensions[v] >= 0 else 0
                mag_pred = 1 if mag_frac > 0.5 else 0

                if abs(mag_frac - 0.5) > 0.3:
                    # Magnetic is confident
                    if mag_pred != tension_pred:
                        # Disagreement: trust TENSION (it's usually right)
                        smart[v] = tension_pred
                    else:
                        smart[v] = mag_pred  # agree: even better
                else:
                    # Magnetic uncertain: use tension
                    smart[v] = tension_pred

            if evaluate(clauses, smart) == len(clauses):
                results['smart_inv'] += 1

        t = results['total']
        print(f"\n  n={n_test} ({t} instances):")
        for name in sorted(results.keys(), key=lambda k: -results.get(k, 0)):
            if name == 'total': continue
            pct = results[name]/t*100
            print(f"    {name:>15}: {results[name]:>3}/{t} ({pct:>5.1f}%)")


# ============================================================
# IDEA 2: SELECTIVE LISTENING — ignore "noisy" neighbors
# ============================================================

def selective_consensus(clauses, n, n_rounds=30):
    """
    Like consensus, but each bit IGNORES neighbors whose
    signal is weak or inconsistent.

    Trust metric per neighbor: |σ_neighbor| × self-consistency.
    Only listen to neighbors above threshold.
    """
    tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

    # Self-consistency score
    sc = {}
    for var in range(n):
        nbs = set()
        for clause in clauses:
            vs = [v for v,s in clause]
            if var in vs:
                for v in vs:
                    if v != var: nbs.add(v)
        nb_avg = sum(tensions[nb] for nb in nbs) / len(nbs) if nbs else 0
        sc[var] = abs(tensions[var] + nb_avg)

    # Trust score: |σ| × SC
    trust = {v: abs(tensions[v]) * (0.3 + sc[v]) for v in range(n)}

    state = [1 if tensions[v] >= 0 else 0 for v in range(n)]

    for round_idx in range(n_rounds):
        order = list(range(n))
        random.shuffle(order)

        for var in order:
            # Only listen to TRUSTED neighbors
            push_1 = 0; push_0 = 0

            for clause in clauses:
                has_var = False; var_sign = 0
                trusted_others_satisfy = False
                untrusted_others = 0

                for v, s in clause:
                    if v == var:
                        has_var = True; var_sign = s
                    else:
                        if trust[v] > 0.1:  # trusted threshold
                            if (s==1 and state[v]==1) or (s==-1 and state[v]==0):
                                trusted_others_satisfy = True
                        else:
                            untrusted_others += 1

                if not has_var: continue
                if trusted_others_satisfy: continue

                # Clause not satisfied by trusted neighbors
                # Weight by how many UNTRUSTED are involved (less reliable clause)
                weight = 1.0 / (1 + untrusted_others)

                if var_sign == 1: push_1 += weight
                else: push_0 += weight

            if push_1 > push_0: state[var] = 1
            elif push_0 > push_1: state[var] = 0

        if evaluate(clauses, state) == len(clauses):
            return state, True, round_idx + 1

    return state, evaluate(clauses, state) == len(clauses), n_rounds


def test_selective():
    print("\n" + "=" * 70)
    print("IDEA 2: SELECTIVE LISTENING — trust only reliable neighbors")
    print("=" * 70)

    random.seed(42)

    for n_test in [12, 16, 20]:
        results = {'tension': 0, 'consensus': 0, 'selective': 0, 'total': 0}

        n_inst = 100 if n_test <= 16 else 50
        for seed in range(n_inst):
            clauses = random_3sat(n_test, int(4.27*n_test), seed=seed+4000000)
            if n_test <= 16:
                solutions = find_solutions(clauses, n_test)
                if not solutions: continue
            results['total'] += 1

            # Tension
            fixed = {}
            for step in range(n_test):
                unfixed = [v for v in range(n_test) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n_test, v, fixed)))
                fixed[best] = 1 if bit_tension(clauses, n_test, best, fixed) >= 0 else 0
            if evaluate(clauses, [fixed.get(v,0) for v in range(n_test)]) == len(clauses):
                results['tension'] += 1

            # Standard consensus
            state = [random.randint(0,1) for _ in range(n_test)]
            for r in range(30):
                for var in range(n_test):
                    sat_1=0; sat_0=0
                    for clause in clauses:
                        if not any(v==var for v,s in clause): continue
                        for tv in [0,1]:
                            ts = list(state); ts[var] = tv
                            if any((s==1 and ts[v]==1) or (s==-1 and ts[v]==0) for v,s in clause):
                                if tv==1: sat_1 += 1
                                else: sat_0 += 1
                    if sat_1 > sat_0: state[var] = 1
                    elif sat_0 > sat_1: state[var] = 0
                if evaluate(clauses, state) == len(clauses): break
            if evaluate(clauses, state) == len(clauses):
                results['consensus'] += 1

            # Selective consensus
            state, success, rounds = selective_consensus(clauses, n_test, 30)
            if success: results['selective'] += 1

        t = results['total']
        print(f"\n  n={n_test} ({t} instances):")
        for name in sorted(results.keys(), key=lambda k: -results.get(k, 0)):
            if name == 'total': continue
            pct = results[name]/t*100
            delta = pct - results['tension']/t*100
            print(f"    {name:>15}: {results[name]:>3}/{t} ({pct:>5.1f}%) {delta:>+6.1f}%")


if __name__ == "__main__":
    test_inversion()
    test_selective()
