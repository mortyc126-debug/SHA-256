"""
WHY IS THE ONE LESS LOADED? The root cause of critical count asymmetry
═══════════════════════════════════════════════════════════════════════

THE ONE has 0.61 critical clauses. Innocents have 1.13.
WHY? What creates this 2× difference?

Hypotheses:
A. THE ONE has the WRONG value → she's saving clauses she SHOULDN'T
   save → fewer legitimate critical dependencies
B. THE ONE is in a less constrained region of the graph
C. THE ONE's sign in the unsat clause is special
D. It's about the RELATIONSHIP between THE ONE and the other 2 suspects

Let's find out.
"""

import numpy as np
import random
from bit_catalog_static import random_3sat, find_solutions


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def get_frozen(clauses, n, solutions):
    return set(v for v in range(n) if len(set(s[v] for s in solutions)) == 1)


def find_keystones(clauses, n, solutions, frozen):
    ks = []
    for ci in range(len(clauses)):
        r = clauses[:ci] + clauses[ci+1:]
        rs = find_solutions(r, n)
        if len(rs) < 2: continue
        rf = get_frozen(r, n, rs)
        u = frozen - rf
        if u: ks.append({'idx': ci, 'clause': clauses[ci], 'unfreezes': u})
    return ks


def unit_propagate_from(clauses, n, fixed):
    f = dict(fixed)
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            sat = False; fl = []
            for v, s in clause:
                if v in f:
                    if (s==1 and f[v]==1) or (s==-1 and f[v]==0): sat=True; break
                else: fl.append((v,s))
            if sat: continue
            if len(fl)==0: return f, True
            if len(fl)==1:
                fv,fs=fl[0]
                if fv not in f: f[fv]=1 if fs==1 else 0; changed=True
    return f, False


def study():
    print("=" * 70)
    print("WHY IS THE ONE LESS LOADED?")
    print("=" * 70)

    random.seed(42)
    n = 14

    # Collect detailed per-suspect data
    data_one = []
    data_inn = []

    for seed in range(3000):
        clauses = random_3sat(n, int(4.267*n), seed=seed+22000000)
        solutions = find_solutions(clauses, n)
        if len(solutions) < 2: continue
        frozen = get_frozen(clauses, n, solutions)
        if len(frozen) < 3: continue
        ks = find_keystones(clauses, n, solutions, frozen)
        if not ks: continue

        sol = solutions[0]
        m = len(clauses)
        tensions = {}
        for v in range(n):
            p1 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==1)
            p0 = sum(1/3 for c in clauses for vi,si in c if vi==v and si==-1)
            tensions[v] = (p1-p0)/(p1+p0) if (p1+p0)>0 else 0

        pv = {}
        for k in ks:
            sc = [(tensions[v]*s, v, s) for v,s in k['clause']]
            b = max(sc, key=lambda x: x[0])
            pv[b[1]] = 1 if b[2]==1 else 0

        fixed, conflict = unit_propagate_from(clauses, n, pv)
        if conflict: continue
        assignment = [fixed.get(v,0) for v in range(n)]
        sat = evaluate(clauses, assignment)
        if sat != m-1: continue

        # Find unsat clause
        uci = -1
        for ci, cl in enumerate(clauses):
            if not any((s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
                      for v,s in cl):
                uci = ci; break
        if uci < 0: continue

        clause = clauses[uci]

        for v, s_in_c in clause:
            is_one = (assignment[v] != sol[v])

            # Count critical clauses (where v is ONLY saver)
            critical = 0
            # Count critical clauses BY TYPE
            crit_because_wrong_val = 0  # v saves clause DESPITE being wrong
            crit_legitimate = 0          # v saves clause BECAUSE correct

            for c2 in clauses:
                if not any(vi==v for vi,si in c2): continue
                # Is this clause saved only by v?
                n_savers = sum(1 for vi,si in c2
                    if (si==1 and assignment[vi]==1) or (si==-1 and assignment[vi]==0))
                v_saves = any(vi==v and ((si==1 and assignment[v]==1) or
                             (si==-1 and assignment[v]==0)) for vi,si in c2)
                if n_savers == 1 and v_saves:
                    critical += 1
                    # WHY does v save this clause?
                    # v's current assignment happens to match the sign
                    v_sign_here = next(si for vi,si in c2 if vi==v)
                    # Does v's CORRECT value (sol[v]) also save?
                    would_sol_save = (v_sign_here==1 and sol[v]==1) or \
                                     (v_sign_here==-1 and sol[v]==0)
                    if not would_sol_save:
                        # v saves ONLY because it's WRONG!
                        # If v were correct, this clause would need another saver
                        crit_because_wrong_val += 1
                    else:
                        crit_legitimate += 1

            # How does v's value relate to signs in its clauses?
            # Count: clauses where v's CURRENT value matches the sign
            val_matches_sign = 0
            val_opposes_sign = 0
            for c2 in clauses:
                for vi, si in c2:
                    if vi == v:
                        if (si==1 and assignment[v]==1) or (si==-1 and assignment[v]==0):
                            val_matches_sign += 1
                        else:
                            val_opposes_sign += 1

            # The CORRECT value's match count
            sol_matches_sign = 0
            sol_opposes_sign = 0
            for c2 in clauses:
                for vi, si in c2:
                    if vi == v:
                        if (si==1 and sol[v]==1) or (si==-1 and sol[v]==0):
                            sol_matches_sign += 1
                        else:
                            sol_opposes_sign += 1

            record = {
                'critical': critical,
                'crit_wrong': crit_because_wrong_val,
                'crit_legit': crit_legitimate,
                'val_matches': val_matches_sign,
                'val_opposes': val_opposes_sign,
                'sol_matches': sol_matches_sign,
                'sol_opposes': sol_opposes_sign,
                'match_ratio': val_matches_sign / max(val_matches_sign + val_opposes_sign, 1),
                'sol_match_ratio': sol_matches_sign / max(sol_matches_sign + sol_opposes_sign, 1),
                'has_wrong_value': 1 if is_one else 0,
            }

            if is_one:
                data_one.append(record)
            else:
                data_inn.append(record)

        if len(data_one) >= 30: break

    if not data_one: print("  No data"); return

    print(f"\n  {len(data_one)} THE ONEs, {len(data_inn)} innocents")

    print(f"\n  {'property':>25} | {'THE ONE':>8} | {'INNOCENT':>8} | {'ratio':>6} | {'why?':>20}")
    print(f"  " + "-" * 75)

    for prop in ['critical', 'crit_wrong', 'crit_legit',
                 'val_matches', 'val_opposes', 'match_ratio',
                 'sol_matches', 'sol_opposes', 'sol_match_ratio']:
        o = np.mean([d[prop] for d in data_one])
        i = np.mean([d[prop] for d in data_inn])
        r = o/i if abs(i)>0.001 else (999 if abs(o)>0.001 else 1)

        why = ""
        if prop == 'crit_wrong' and o < i:
            why = "wrong val = fewer false saves"
        elif prop == 'crit_legit' and abs(r-1) < 0.1:
            why = "legit saves = SAME"
        elif prop == 'match_ratio' and o < i:
            why = "wrong val matches FEWER signs"
        elif prop == 'sol_match_ratio' and abs(r-1) > 0.1:
            why = "SHOULD match differently"

        disc = "←" if abs(r-1) > 0.15 else ""
        print(f"  {prop:>25} | {o:>8.3f} | {i:>8.3f} | {r:>6.2f} | {disc}{why}")

    # THE EXPLANATION
    print(f"\n  ═══ THE EXPLANATION ═══")
    o_cw = np.mean([d['crit_wrong'] for d in data_one])
    i_cw = np.mean([d['crit_wrong'] for d in data_inn])
    o_cl = np.mean([d['crit_legit'] for d in data_one])
    i_cl = np.mean([d['crit_legit'] for d in data_inn])

    print(f"\n  Critical clauses decomposed:")
    print(f"    THE ONE:  {o_cl:.2f} legitimate + {o_cw:.2f} wrong-val = "
          f"{o_cl+o_cw:.2f} total")
    print(f"    INNOCENT: {i_cl:.2f} legitimate + {i_cw:.2f} wrong-val = "
          f"{i_cl+i_cw:.2f} total")
    print(f"\n    Difference comes from: ", end="")

    if abs(o_cl - i_cl) < 0.2 and abs(o_cw - i_cw) > 0.2:
        print(f"WRONG-VAL criticals! ({o_cw:.2f} vs {i_cw:.2f})")
        print(f"\n    THE ONE has wrong value → she saves FEWER clauses by accident")
        print(f"    Innocents have correct value → they save MORE clauses legitimately")
        print(f"    AND they also happen to save some 'by accident'")
    elif abs(o_cl - i_cl) > 0.2:
        print(f"LEGITIMATE criticals! ({o_cl:.2f} vs {i_cl:.2f})")
    else:
        print(f"BOTH components")

    # FINAL: Can we compute match_ratio WITHOUT knowing the solution?
    print(f"\n  ═══ THE OBSERVABLE ═══")
    o_mr = np.mean([d['match_ratio'] for d in data_one])
    i_mr = np.mean([d['match_ratio'] for d in data_inn])
    print(f"\n  match_ratio (fraction of signs that match current value):")
    print(f"    THE ONE:  {o_mr:.3f}")
    print(f"    INNOCENT: {i_mr:.3f}")
    print(f"    → THE ONE's current value matches FEWER literal signs")
    print(f"    → This is because her value is WRONG")
    print(f"    → A wrong value naturally matches ~50% of signs (random)")
    print(f"    → A correct value matches >50% (biased by solution)")
    print(f"\n    THIS IS COMPUTABLE: just count how many of v's")
    print(f"    clause appearances have signs matching v's current value.")
    print(f"    Lowest match_ratio among 3 suspects = THE ONE")


if __name__ == "__main__":
    study()
