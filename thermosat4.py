"""
ThermoSAT v4 — Adaptive Forcing with MiniSat Backend
═════════════════════════════════════════════════════

Key insight: forcing top signal vars gives 10-17× speedup BUT
wrong forces make instances UNSAT (30% wrong → P(all correct)
= 0.89^k → exponentially small for large k).

STRATEGY: Binary search on forcing strength.
  1. Start with aggressive forcing (top 20% signal vars)
  2. Run MiniSat with short timeout
  3. If UNSAT/timeout: halve the forced vars, retry
  4. Until SAT or fall back to raw MiniSat

Also test: POLARITY HINTS via clause structure manipulation.
Instead of forcing (unit clauses), add binary "preference" clauses
that bias MiniSat without constraining it.
"""

import random
import math
import time
import subprocess
import os
from bit_catalog_static import random_3sat


def compute_tension(clauses, n, var):
    p1, p0 = 0.0, 0.0
    for clause in clauses:
        for v, s in clause:
            if v == var:
                w = 1.0 / len(clause)
                if s == 1: p1 += w
                else: p0 += w
    total = p1 + p0
    return (p1 - p0) / total if total > 0 else 0.0


def evaluate(clauses, assignment):
    return sum(1 for c in clauses if any(
        (s==1 and assignment[v]==1) or (s==-1 and assignment[v]==0)
        for v,s in c))


def write_dimacs(filename, clauses, n):
    m = len(clauses)
    with open(filename, 'w') as f:
        f.write(f"p cnf {n} {m}\n")
        for clause in clauses:
            lits = [str((v+1)*s) for v, s in clause]
            f.write(" ".join(lits) + " 0\n")


def run_minisat(filename, timeout=60):
    outfile = filename + ".out"
    try:
        t0 = time.time()
        result = subprocess.run(
            ["minisat", filename, outfile],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - t0
        output = result.stdout + result.stderr
        decisions = 0
        for line in output.split('\n'):
            s = line.strip()
            if s.startswith('decisions'):
                after = s.split(':', 1)[1].strip().split()
                if after:
                    try: decisions = int(after[0])
                    except: pass

        if os.path.exists(outfile):
            with open(outfile) as f:
                r = f.readline().strip()
                if r == "SAT": return "SAT", elapsed, decisions
                elif r == "UNSAT": return "UNSAT", elapsed, decisions
        return "UNKNOWN", elapsed, decisions
    except subprocess.TimeoutExpired:
        return "TIMEOUT", timeout, 0
    finally:
        if os.path.exists(outfile):
            os.remove(outfile)


# ============================================================
# Method 1: Adaptive forcing (binary search)
# ============================================================

def adaptive_force_solve(clauses, n, total_timeout=60):
    """
    Binary search on number of forced variables.
    Start aggressive, back off if UNSAT.
    """
    filename = "/tmp/thermo4_adapt.cnf"
    start = time.time()

    # Compute tensions once
    tensions = {v: compute_tension(clauses, n, v) for v in range(n)}
    sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]), reverse=True)

    # Try different forcing levels
    force_counts = []
    # Start with many, halve each time
    k = min(int(0.25 * n), n)
    while k >= 1:
        force_counts.append(k)
        k = k // 2
    force_counts.append(0)  # fallback: no forcing

    total_decisions = 0

    for k in force_counts:
        remaining = total_timeout - (time.time() - start)
        if remaining <= 0:
            break

        # Build forced instance
        forced_clauses = list(clauses)
        for v in sorted_vars[:k]:
            sign = 1 if tensions[v] >= 0 else -1
            forced_clauses.append([(v, sign)])

        write_dimacs(filename, forced_clauses, n)

        # Run with timeout proportional to remaining time
        # Give more time to less aggressive forcing
        step_timeout = min(remaining, max(remaining / 3, 2))

        result, elapsed, decisions = run_minisat(filename, step_timeout)
        total_decisions += decisions

        if result == "SAT":
            if os.path.exists(filename): os.remove(filename)
            return True, time.time() - start, total_decisions, k

        # If UNSAT: our forcing was wrong, reduce k
        # If TIMEOUT: not enough time at this level

    # Fallback: run raw
    remaining = total_timeout - (time.time() - start)
    if remaining > 1:
        write_dimacs(filename, clauses, n)
        result, elapsed, decisions = run_minisat(filename, remaining)
        total_decisions += decisions
        if result == "SAT":
            if os.path.exists(filename): os.remove(filename)
            return True, time.time() - start, total_decisions, 0

    if os.path.exists(filename): os.remove(filename)
    return False, time.time() - start, total_decisions, -1


# ============================================================
# Method 2: Preference clauses (soft guidance)
# ============================================================

def preference_clause_solve(clauses, n, timeout=60):
    """
    Instead of unit clauses (hard forcing), add BINARY preference clauses.

    For each signal var v with tension > 0:
      Add clauses that CONTAIN v positively alongside other positive-tension vars.
      This biases VSIDS to choose v=1 but doesn't force it.

    Technique: For top vars v1, v2 with same predicted sign:
      Add (v1 OR v2) — both positive means "prefer both true"
      This is ALWAYS satisfiable → can't break the instance.
    """
    filename = "/tmp/thermo4_pref.cnf"

    tensions = {v: compute_tension(clauses, n, v) for v in range(n)}
    sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]), reverse=True)

    # Take top 30% of vars
    top_k = int(0.3 * n)
    top_vars = sorted_vars[:top_k]

    # Group by predicted sign
    pos_vars = [v for v in top_vars if tensions[v] > 0]
    neg_vars = [v for v in top_vars if tensions[v] < 0]

    # Add preference clauses: pairs of same-sign vars
    pref_clauses = list(clauses)
    n_pref = 0

    # For positive vars: add (vi OR vj) for random pairs
    random.seed(42)
    for _ in range(min(len(pos_vars) * 2, n)):
        if len(pos_vars) < 2: break
        v1, v2 = random.sample(pos_vars, 2)
        pref_clauses.append([(v1, 1), (v2, 1)])
        n_pref += 1

    # For negative vars: add (-vi OR -vj) for random pairs
    for _ in range(min(len(neg_vars) * 2, n)):
        if len(neg_vars) < 2: break
        v1, v2 = random.sample(neg_vars, 2)
        pref_clauses.append([(v1, -1), (v2, -1)])
        n_pref += 1

    write_dimacs(filename, pref_clauses, n)
    result, elapsed, decisions = run_minisat(filename, timeout)

    if os.path.exists(filename): os.remove(filename)
    return result == "SAT", elapsed, decisions, n_pref


# ============================================================
# Method 3: Failed literal probing guided by tension
# ============================================================

def probe_guided_solve(clauses, n, timeout=60):
    """
    Probe variables in tension order.
    For each var: try v=0 and v=1, run UP.
    If one leads to conflict → the other is forced.
    These are SOUND inferences (can't break anything).
    Then feed the reduced instance to MiniSat.
    """
    filename = "/tmp/thermo4_probe.cnf"
    start = time.time()

    tensions = {v: compute_tension(clauses, n, v) for v in range(n)}
    sorted_vars = sorted(range(n), key=lambda v: abs(tensions[v]), reverse=True)

    # Probe top vars
    forced = {}
    max_probe = min(int(0.3 * n), 50)  # limit probing time

    for v in sorted_vars[:max_probe]:
        if time.time() - start > timeout * 0.3:
            break

        # Try v = 1
        fixed1 = dict(forced)
        fixed1[v] = 1
        conflict1 = False
        f = dict(fixed1)
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                sat = False; free = []
                for cv, cs in clause:
                    if cv in f:
                        if (cs==1 and f[cv]==1) or (cs==-1 and f[cv]==0):
                            sat = True; break
                    else: free.append((cv, cs))
                if sat: continue
                if len(free) == 0:
                    conflict1 = True; break
                if len(free) == 1:
                    fv, fs = free[0]
                    if fv not in f:
                        f[fv] = 1 if fs == 1 else 0
                        changed = True
            if conflict1: break

        # Try v = 0
        fixed0 = dict(forced)
        fixed0[v] = 0
        conflict0 = False
        f = dict(fixed0)
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                sat = False; free = []
                for cv, cs in clause:
                    if cv in f:
                        if (cs==1 and f[cv]==1) or (cs==-1 and f[cv]==0):
                            sat = True; break
                    else: free.append((cv, cs))
                if sat: continue
                if len(free) == 0:
                    conflict0 = True; break
                if len(free) == 1:
                    fv, fs = free[0]
                    if fv not in f:
                        f[fv] = 1 if fs == 1 else 0
                        changed = True
            if conflict0: break

        if conflict1 and not conflict0:
            forced[v] = 0  # v=1 fails → force v=0
        elif conflict0 and not conflict1:
            forced[v] = 1  # v=0 fails → force v=1
        elif conflict0 and conflict1:
            # Both fail → UNSAT with current forced vars
            break

    # Add forced vars as unit clauses (these are SOUND)
    forced_clauses = list(clauses)
    for v, val in forced.items():
        sign = 1 if val == 1 else -1
        forced_clauses.append([(v, sign)])

    remaining = timeout - (time.time() - start)
    write_dimacs(filename, forced_clauses, n)
    result, elapsed, decisions = run_minisat(filename, remaining)

    if os.path.exists(filename): os.remove(filename)
    total_time = time.time() - start
    return result == "SAT", total_time, decisions, len(forced)


# ============================================================
# BENCHMARK
# ============================================================

def benchmark():
    print("=" * 75)
    print("ThermoSAT v4: Adaptive / Preference / Probe")
    print("=" * 75)

    random.seed(42)
    filename = "/tmp/thermo4_raw.cnf"

    for n in [50, 100, 200, 300, 500]:
        print(f"\n  n={n}, ratio=4.27:")
        n_inst = 30 if n <= 200 else 15
        timeout = 30 if n <= 200 else 120

        raw = {'solved': 0, 'times': [], 'dec': []}
        adapt = {'solved': 0, 'times': [], 'dec': [], 'force_k': []}
        pref = {'solved': 0, 'times': [], 'dec': []}
        probe = {'solved': 0, 'times': [], 'dec': [], 'forced': []}

        actual = 0
        for seed in range(n_inst * 5):
            clauses = random_3sat(n, int(4.27 * n), seed=seed + 66000000)

            # Raw MiniSat
            write_dimacs(filename, clauses, n)
            r, t, d = run_minisat(filename, timeout)
            if r == "SAT":
                raw['solved'] += 1
                raw['times'].append(t)
                raw['dec'].append(d)

            # Adaptive forcing
            ok, t, d, k = adaptive_force_solve(clauses, n, timeout)
            if ok:
                adapt['solved'] += 1
                adapt['times'].append(t)
                adapt['dec'].append(d)
                adapt['force_k'].append(k)

            # Preference clauses
            ok, t, d, np = preference_clause_solve(clauses, n, timeout)
            if ok:
                pref['solved'] += 1
                pref['times'].append(t)
                pref['dec'].append(d)

            # Probe-guided
            ok, t, d, nf = probe_guided_solve(clauses, n, timeout)
            if ok:
                probe['solved'] += 1
                probe['times'].append(t)
                probe['dec'].append(d)
                probe['forced'].append(nf)

            actual += 1
            if actual >= n_inst:
                break

        print(f"    {'method':>15} | {'solved':>6} | {'avg ms':>8} | "
              f"{'avg dec':>10} | {'notes':>20}")
        print("    " + "-" * 70)

        raw_time = sum(raw['times'])/len(raw['times']) if raw['times'] else 999

        for label, res, notes_fn in [
            ('raw MiniSat', raw, lambda: ''),
            ('adaptive', adapt, lambda: f"avg k={sum(adapt['force_k'])/len(adapt['force_k']):.0f}" if adapt['force_k'] else ''),
            ('preference', pref, lambda: ''),
            ('probe', probe, lambda: f"avg forced={sum(probe['forced'])/len(probe['forced']):.0f}" if probe['forced'] else ''),
        ]:
            if res['times']:
                avg_t = sum(res['times'])/len(res['times'])
                avg_d = sum(res['dec'])/len(res['dec'])
                speedup = raw_time/avg_t if avg_t > 0 else 0
                notes = notes_fn()
                print(f"    {label:>15} | {res['solved']:>6} | "
                      f"{1000*avg_t:>7.0f}ms | {avg_d:>10.0f} | "
                      f"{speedup:>5.2f}× {notes}")
            else:
                print(f"    {label:>15} | {res['solved']:>6} |      N/A |"
                      f"        N/A |")

    if os.path.exists(filename): os.remove(filename)


if __name__ == "__main__":
    benchmark()
