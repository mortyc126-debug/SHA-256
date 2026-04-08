"""
CONTEXT ATTACK: Instead of solving SAT, CRACK THE CONTEXT.

Context of bit i = values of its 3-4 direct neighbors.
With correct context: bit accuracy = 95%.

Question: is recovering LOCAL context easier than solving SAT?

If we need context of ALL bits → that IS the solution.
But what if we need context of only a FEW bits →
those bits become correct → cascade → solution?

Strategy:
1. How many bits need correct context to trigger cascade?
2. Can we recover LOCAL context (3-4 bits) cheaper than GLOBAL?
3. Context of ONE bit = 2^4 = 16 possibilities. Try all?
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
# 1. LOCAL CONTEXT ATTACK: enumerate 2^k contexts for one bit
# ============================================================

def local_context_attack():
    """
    For one bit: its context = values of ~10 neighbors.
    2^10 = 1024 possibilities. For each: compute σ(bit | context).
    Pick the context where |σ| is MAXIMUM → most confident → likely correct.

    Then: use that bit + context as seed → propagate.
    """
    print("=" * 70)
    print("1. LOCAL CONTEXT ATTACK: enumerate neighbor contexts")
    print("=" * 70)

    random.seed(42); n = 12

    solved = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        total += 1

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # Pick the MOST CONFIDENT bit as starting point
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}
        start_bit = max(range(n), key=lambda v: abs(tensions[v]))
        nbs = sorted(get_neighbors(clauses, n, start_bit))[:6]  # limit to 6 neighbors

        # Enumerate all contexts of these neighbors
        best_assignment = None
        best_sat = 0

        for combo in range(2**len(nbs)):
            fixed = {}
            for idx, nb in enumerate(nbs):
                fixed[nb] = (combo >> idx) & 1

            # With this context, compute tension of start_bit
            sigma = bit_tension(clauses, n, start_bit, fixed)
            fixed[start_bit] = 1 if sigma >= 0 else 0

            # Cascade: crystallize the rest using tension
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
                fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0

            assignment = [fixed.get(v, 0) for v in range(n)]
            sat = evaluate(clauses, assignment)
            if sat > best_sat:
                best_sat = sat
                best_assignment = assignment

            if best_sat == len(clauses):
                break

        if best_sat == len(clauses):
            solved += 1

    print(f"\n  n=12: Local context attack (6 neighbors, 64 combos)")
    print(f"  Solved: {solved}/{total} ({solved/total*100:.1f}%)")


# ============================================================
# 2. MULTI-SEED CONTEXT: attack context of K bits simultaneously
# ============================================================

def multi_seed_context():
    """
    Instead of 1 bit's context: attack K bits' joint context.
    If K bits are chosen carefully (most influential):
    fix their values → cascade → solution.

    This is DIFFERENT from clone reduction:
    - Clone reduction: find independent bits, enumerate THEM
    - Context attack: find influential bits, enumerate their NEIGHBORS
    """
    print("\n" + "=" * 70)
    print("2. MULTI-SEED CONTEXT: Attack K most influential bits")
    print("=" * 70)

    random.seed(42); n = 12

    for k_seeds in [1, 2, 3]:
        solved = 0; total = 0; total_combos = 0

        for seed in range(100):
            clauses = random_3sat(n, int(4.27*n), seed=seed)
            solutions = find_solutions(clauses, n)
            if not solutions: continue
            total += 1

            tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

            # Pick K most confident bits
            seeds = sorted(range(n), key=lambda v: -abs(tensions[v]))[:k_seeds]

            # Enumerate all value combos for these K bits
            best_sat = 0
            combos_tried = 0

            for combo in range(2**k_seeds):
                fixed = {}
                for idx, var in enumerate(seeds):
                    fixed[var] = (combo >> idx) & 1

                # Cascade from these seeds
                for step in range(n):
                    unfixed = [v for v in range(n) if v not in fixed]
                    if not unfixed: break
                    best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
                    fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0

                assignment = [fixed.get(v,0) for v in range(n)]
                sat = evaluate(clauses, assignment)
                combos_tried += 1

                if sat > best_sat:
                    best_sat = sat

                if best_sat == len(clauses):
                    break

            total_combos += combos_tried
            if best_sat == len(clauses):
                solved += 1

        avg_combos = total_combos / total if total > 0 else 0
        print(f"  K={k_seeds}: {solved}/{total} ({solved/total*100:.1f}%), "
              f"avg {avg_combos:.1f} combos")


# ============================================================
# 3. CONTEXT vs SOLUTION: cost comparison
# ============================================================

def context_vs_solution():
    """
    Compare:
    A. Enumerate K seed VALUES (2^K combos, each cascades)
    B. Standard DPLL
    C. Context attack (enumerate neighbor values around seeds)

    Which needs fewer total evaluations?
    """
    print("\n" + "=" * 70)
    print("3. COST COMPARISON: Context attack vs DPLL vs seed enumeration")
    print("=" * 70)

    random.seed(42); n = 12

    results = {'dpll': [], 'seed_enum': [], 'context_6nb': []}

    for seed in range(80):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # DPLL calls
        calls = [0]
        def up(fixed):
            f=dict(fixed);ch=True
            while ch:
                ch=False
                for clause in clauses:
                    sat=False;free=[]
                    for v,s in clause:
                        if v in f:
                            if (s==1 and f[v]==1) or (s==-1 and f[v]==0): sat=True;break
                        else: free.append((v,s))
                    if not sat and len(free)==1:
                        v,s=free[0]
                        if v not in f: f[v]=1 if s==1 else 0;ch=True
                    if not sat and len(free)==0: return f,True
            return f,False

        def dpll(fixed):
            calls[0]+=1
            if calls[0]>10000: return None
            fixed,c=up(fixed)
            if c: return None
            uf=[v for v in range(n) if v not in fixed]
            if not uf:
                a=[fixed.get(v,0) for v in range(n)]
                return a if evaluate(clauses,a)==len(clauses) else None
            best=max(uf,key=lambda v:abs(bit_tension(clauses,n,v,fixed)))
            sigma=bit_tension(clauses,n,best,fixed)
            fv=1 if sigma>=0 else 0
            f=dict(fixed);f[best]=fv
            r=dpll(f)
            if r: return r
            f=dict(fixed);f[best]=1-fv
            return dpll(f)

        dpll({})
        results['dpll'].append(calls[0])

        # Seed enumeration (3 seeds)
        seeds3 = sorted(range(n), key=lambda v: -abs(tensions[v]))[:3]
        seed_combos = 0
        for combo in range(8):
            seed_combos += 1
            fixed = {seeds3[idx]: (combo>>idx)&1 for idx in range(3)}
            for step in range(n):
                uf=[v for v in range(n) if v not in fixed]
                if not uf: break
                best=max(uf,key=lambda v:abs(bit_tension(clauses,n,v,fixed)))
                fixed[best]=1 if bit_tension(clauses,n,best,fixed)>=0 else 0
            if evaluate(clauses,[fixed.get(v,0) for v in range(n)])==len(clauses):
                break
        results['seed_enum'].append(seed_combos * n)  # each combo costs ~n evaluations

        # Context attack (6 neighbors of best bit)
        start = max(range(n), key=lambda v: abs(tensions[v]))
        nbs = sorted(get_neighbors(clauses, n, start))[:6]
        ctx_combos = 0
        for combo in range(64):
            ctx_combos += 1
            fixed = {nbs[idx]: (combo>>idx)&1 for idx in range(min(6,len(nbs)))}
            fixed[start] = 1 if bit_tension(clauses,n,start,fixed)>=0 else 0
            for step in range(n):
                uf=[v for v in range(n) if v not in fixed]
                if not uf: break
                best=max(uf,key=lambda v:abs(bit_tension(clauses,n,v,fixed)))
                fixed[best]=1 if bit_tension(clauses,n,best,fixed)>=0 else 0
            if evaluate(clauses,[fixed.get(v,0) for v in range(n)])==len(clauses):
                break
        results['context_6nb'].append(ctx_combos * n)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Method          | Avg evaluations")
    print(f"  " + "-" * 35)
    print(f"  DPLL:           | {mean(results['dpll']):>10.1f}")
    print(f"  Seed enum (3):  | {mean(results['seed_enum']):>10.1f}")
    print(f"  Context (6 nb): | {mean(results['context_6nb']):>10.1f}")


# ============================================================
# 4. THE KEY: Does correct local context TRIGGER cascade?
# ============================================================

def context_cascade():
    """
    If we give CORRECT context to ONE bit:
    Does the cascade from that bit solve the whole problem?

    This measures: is one correct local context ENOUGH?
    """
    print("\n" + "=" * 70)
    print("4. Does ONE correct context trigger a FULL cascade?")
    print("=" * 70)

    random.seed(42); n = 12

    solved_from_context = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue
        total += 1

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        # For EACH bit: give it correct context, cascade, check
        any_solved = False
        for start in range(n):
            nbs = list(get_neighbors(clauses, n, start))

            # Fix neighbors to CORRECT values (oracle context)
            fixed = {nb: correct_val[nb] for nb in nbs}
            # Now bit should "know" its answer (95%)
            sigma = bit_tension(clauses, n, start, fixed)
            fixed[start] = 1 if sigma >= 0 else 0

            # Cascade
            for step in range(n):
                unfixed = [v for v in range(n) if v not in fixed]
                if not unfixed: break
                best = max(unfixed, key=lambda v: abs(bit_tension(clauses, n, v, fixed)))
                fixed[best] = 1 if bit_tension(clauses, n, best, fixed) >= 0 else 0

            if evaluate(clauses, [fixed.get(v,0) for v in range(n)]) == len(clauses):
                any_solved = True
                break

        if any_solved:
            solved_from_context += 1

    print(f"\n  Give ANY bit its correct context → cascade → solve?")
    print(f"  {solved_from_context}/{total} ({solved_from_context/total*100:.1f}%)")


if __name__ == "__main__":
    local_context_attack()
    multi_seed_context()
    context_vs_solution()
    context_cascade()
