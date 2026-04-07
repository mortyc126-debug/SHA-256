"""
SINGLE FLIP BITS: The 50% accuracy anomaly.

Bits whose tension FLIPS SIGN exactly once during crystallization
have 49.8% accuracy = PURE RANDOM. Why?

Questions:
1. WHEN does the flip happen? Early or late?
2. WHAT causes the flip? Which neighbor fixation triggers it?
3. Was the ORIGINAL direction correct, or the FINAL?
4. Can we DETECT single-flip bits BEFORE crystallization?
5. If we SKIP them (don't fix), does accuracy improve?
6. How many are there? Does this explain our ~30% error rate?
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
# 1. WHEN does the flip happen?
# ============================================================

def when_flip():
    print("=" * 70)
    print("1. WHEN does the single flip happen?")
    print("=" * 70)

    random.seed(42); n = 12

    flip_positions = []  # fraction of trajectory where flip occurs
    flip_early_correct = 0  # was the PRE-flip value correct?
    flip_late_correct = 0   # was the POST-flip value correct?
    total_flips = 0

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        fixed = {}
        trajectories = {v: [] for v in range(n)}
        order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

        for step_var in order:
            for v in range(n):
                if v not in fixed:
                    trajectories[v].append(bit_tension(clauses, n, v, fixed))
            sigma = bit_tension(clauses, n, step_var, fixed)
            fixed[step_var] = 1 if sigma >= 0 else 0

        for var in range(n):
            traj = trajectories[var]
            if len(traj) < 3: continue

            sign_changes = []
            for i in range(1, len(traj)):
                if traj[i] * traj[i-1] < 0:
                    sign_changes.append(i)

            if len(sign_changes) == 1:
                total_flips += 1
                flip_pos = sign_changes[0] / len(traj)
                flip_positions.append(flip_pos)

                # Was pre-flip direction correct?
                pre_dir = 1 if traj[0] >= 0 else 0
                post_dir = 1 if traj[-1] >= 0 else 0
                actual = correct_val[var]

                if pre_dir == actual: flip_early_correct += 1
                if post_dir == actual: flip_late_correct += 1

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Total single-flip bits: {total_flips}")
    print(f"  Avg flip position: {mean(flip_positions):.3f} (0=start, 1=end)")
    print(f"  Pre-flip direction correct:  {flip_early_correct/total_flips*100:.1f}%")
    print(f"  Post-flip direction correct: {flip_late_correct/total_flips*100:.1f}%")

    # Distribution of flip positions
    print(f"\n  Flip position distribution:")
    bins = [0]*5
    for fp in flip_positions:
        b = min(4, int(fp * 5))
        bins[b] += 1
    for i in range(5):
        frac = bins[i]/len(flip_positions)*100 if flip_positions else 0
        bar = "█" * int(frac)
        print(f"    {i*20:>2}-{(i+1)*20:>3}%: {frac:>5.1f}% {bar}")


# ============================================================
# 2. WHAT triggers the flip?
# ============================================================

def what_triggers():
    print("\n" + "=" * 70)
    print("2. WHAT triggers the flip?")
    print("=" * 70)

    random.seed(42); n = 12

    trigger_is_neighbor = 0
    trigger_is_distant = 0
    trigger_shared_clauses = []
    total_analyzed = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        # Build adjacency
        adj = {i: set() for i in range(n)}
        shared = [[0]*n for _ in range(n)]
        for clause in clauses:
            vs = [v for v,s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])
                    shared[vs[a]][vs[b]] += 1
                    shared[vs[b]][vs[a]] += 1

        fixed = {}
        prev_tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
        order = sorted(range(n), key=lambda v: -abs(prev_tensions[v]))
        fix_history = []

        for step_var in order:
            sigma = bit_tension(clauses, n, step_var, fixed)
            fixed[step_var] = 1 if sigma >= 0 else 0
            fix_history.append(step_var)

            # Check: did any unfixed bit flip?
            for v in range(n):
                if v in fixed or v == step_var: continue
                new_sigma = bit_tension(clauses, n, v, fixed)
                if v in prev_tensions and prev_tensions[v] * new_sigma < 0:
                    # v flipped! Was the trigger (step_var) a neighbor?
                    total_analyzed += 1
                    if step_var in adj[v]:
                        trigger_is_neighbor += 1
                        trigger_shared_clauses.append(shared[v][step_var])
                    else:
                        trigger_is_distant += 1

            # Update tensions
            for v in range(n):
                if v not in fixed:
                    prev_tensions[v] = bit_tension(clauses, n, v, fixed)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    if total_analyzed > 0:
        print(f"\n  Flip triggers analyzed: {total_analyzed}")
        print(f"  Triggered by NEIGHBOR:  {trigger_is_neighbor} ({trigger_is_neighbor/total_analyzed*100:.1f}%)")
        print(f"  Triggered by DISTANT:   {trigger_is_distant} ({trigger_is_distant/total_analyzed*100:.1f}%)")
        if trigger_shared_clauses:
            print(f"  Avg shared clauses with trigger: {mean(trigger_shared_clauses):.2f}")


# ============================================================
# 3. Can we DETECT single-flip bits BEFORE crystallization?
# ============================================================

def detect_before():
    print("\n" + "=" * 70)
    print("3. Can we PREDICT single-flip bits from static properties?")
    print("=" * 70)

    random.seed(42); n = 12

    sf_properties = []  # single-flip bits
    nsf_properties = []  # non-single-flip bits

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        fixed = {}
        trajectories = {v: [] for v in range(n)}
        order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))

        for step_var in order:
            for v in range(n):
                if v not in fixed:
                    trajectories[v].append(bit_tension(clauses, n, v, fixed))
            sigma = bit_tension(clauses, n, step_var, fixed)
            fixed[step_var] = 1 if sigma >= 0 else 0

        for var in range(n):
            traj = trajectories[var]
            if len(traj) < 3: continue

            sign_changes = sum(1 for i in range(1, len(traj)) if traj[i]*traj[i-1] < 0)
            is_single_flip = sign_changes == 1

            # Static properties (before crystallization)
            sigma = bit_tension(clauses, n, var)
            degree = sum(1 for cl in clauses if any(v == var for v,s in cl))

            neighbors = set()
            for clause in clauses:
                vs = [v for v,s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)

            # Flip triggers (static)
            base_sign = 1 if sigma >= 0 else -1
            ft = 0
            for nb in list(neighbors)[:6]:
                for val in [0,1]:
                    s = bit_tension(clauses, n, var, {nb: val})
                    if (1 if s >= 0 else -1) != base_sign:
                        ft += 1; break
            fragility = ft / min(6, len(neighbors)) if neighbors else 0

            entry = {
                'abs_sigma': abs(sigma),
                'degree': degree,
                'fragility': fragility,
                'n_neighbors': len(neighbors),
            }

            if is_single_flip:
                sf_properties.append(entry)
            else:
                nsf_properties.append(entry)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  {len(sf_properties)} single-flip, {len(nsf_properties)} others")
    print(f"\n  {'property':>15} | {'single_flip':>11} | {'others':>8} | {'ratio':>7}")
    print("  " + "-" * 50)

    for prop in ['abs_sigma', 'degree', 'fragility', 'n_neighbors']:
        sf = mean([p[prop] for p in sf_properties])
        nsf = mean([p[prop] for p in nsf_properties])
        ratio = sf / nsf if nsf > 0 else 0
        sig = "★" if ratio > 1.3 or ratio < 0.77 else ""
        print(f"  {prop:>15} | {sf:>11.4f} | {nsf:>8.4f} | {ratio:>7.2f} {sig}")


# ============================================================
# 4. SOLVER: Skip single-flip bits, enumerate them
# ============================================================

def skip_solver():
    print("\n" + "=" * 70)
    print("4. SOLVER: Detect trajectory-broken bits, handle separately")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'standard': 0, 'skip_sf': 0, 'anti_flip': 0, 'total': 0}

    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        results['total'] += 1

        # Standard
        fixed = {}
        for step in range(n):
            unfixed = [v for v in range(n) if v not in fixed]
            if not unfixed: break
            best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
            fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0
        if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
            results['standard'] += 1

        # Two-pass: crystallize, detect flips, re-decide flipped bits
        fixed1 = {}
        trajectories = {v: [] for v in range(n)}
        order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))
        for step_var in order:
            for v in range(n):
                if v not in fixed1:
                    trajectories[v].append(bit_tension(clauses, n, v, fixed1))
            sigma = bit_tension(clauses, n, step_var, fixed1)
            fixed1[step_var] = 1 if sigma >= 0 else 0

        # Find single-flip bits
        sf_bits = []
        for var in range(n):
            traj = trajectories[var]
            if len(traj) < 3: continue
            sign_changes = sum(1 for i in range(1, len(traj)) if traj[i]*traj[i-1] < 0)
            if sign_changes == 1:
                sf_bits.append(var)

        # ANTI-FLIP: use pre-flip direction instead of post-flip
        fixed_anti = dict(fixed1)
        for var in sf_bits:
            traj = trajectories[var]
            pre_dir = 1 if traj[0] >= 0 else 0
            fixed_anti[var] = pre_dir  # use ORIGINAL direction
        if evaluate(clauses, [fixed_anti.get(v,0) for v in range(n)]) == len(clauses):
            results['anti_flip'] += 1

        # SKIP + ENUMERATE: remove sf bits, try all combos
        if len(sf_bits) <= 4:
            best_sat = 0; best_assignment = None
            non_sf = {v: fixed1[v] for v in fixed1 if v not in sf_bits}

            for combo in range(2**len(sf_bits)):
                test = dict(non_sf)
                for idx, var in enumerate(sf_bits):
                    test[var] = (combo >> idx) & 1
                assignment = [test.get(v, 0) for v in range(n)]
                sat = evaluate(clauses, assignment)
                if sat > best_sat:
                    best_sat = sat; best_assignment = assignment

            if best_assignment and best_sat == len(clauses):
                results['skip_sf'] += 1
        else:
            # Too many sf bits, fallback
            if evaluate(clauses, [fixed1.get(v,0) for v in range(n)]) == len(clauses):
                results['skip_sf'] += 1

    t = results['total']
    print(f"\n  Standard:            {results['standard']}/{t} ({results['standard']/t*100:.1f}%)")
    print(f"  Anti-flip:           {results['anti_flip']}/{t} ({results['anti_flip']/t*100:.1f}%)")
    print(f"  Skip+enumerate SF:   {results['skip_sf']}/{t} ({results['skip_sf']/t*100:.1f}%)")

    # How many SF bits per instance?
    sf_counts = []
    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        fixed1 = {}
        trajectories = {v: [] for v in range(n)}
        order = sorted(range(n), key=lambda v: -abs(bit_tension(clauses, n, v)))
        for step_var in order:
            for v in range(n):
                if v not in fixed1:
                    trajectories[v].append(bit_tension(clauses, n, v, fixed1))
            sigma = bit_tension(clauses, n, step_var, fixed1)
            fixed1[step_var] = 1 if sigma >= 0 else 0

        sf = 0
        for var in range(n):
            traj = trajectories[var]
            if len(traj) >= 3:
                sc = sum(1 for i in range(1, len(traj)) if traj[i]*traj[i-1] < 0)
                if sc == 1: sf += 1
        sf_counts.append(sf)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Avg single-flip bits per instance: {mean(sf_counts):.1f} out of {n}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    when_flip()
    what_triggers()
    detect_before()
    skip_solver()
