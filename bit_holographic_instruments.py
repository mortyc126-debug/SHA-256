"""
HOLOGRAPHIC INSTRUMENTS: Reading global geometry of constraint network.

73% of solution correlations are non-local.
Information is in the SHAPE of the system, not in local properties.

New instruments that read GLOBAL structure:
H1. SPECTRAL POSITION: where does bit sit in eigenvector space?
H2. GRAPH CURVATURE: local curvature at each bit's position
H3. FLOW FIELD: if we send "current" through the graph, where does it go?
H4. HOLOGRAPHIC BOUNDARY: bits at the "edge" vs "center" of solution space
H5. RESONANT MODES: which eigenmodes of the Laplacian carry solution info?
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


def build_signed_laplacian(clauses, n):
    """
    Signed Laplacian: L[i][j] = -sign_weight, L[i][i] = degree.
    Sign weight: +1 if same signs in clause, -1 if different.
    This encodes the FULL clause sign topology.
    """
    L = [[0.0]*n for _ in range(n)]
    for clause in clauses:
        lits = [(v,s) for v,s in clause]
        for a in range(len(lits)):
            for b in range(a+1, len(lits)):
                vi, si = lits[a]; vj, sj = lits[b]
                sign_weight = 1.0 if si == sj else -1.0
                L[vi][vj] -= sign_weight
                L[vj][vi] -= sign_weight
                L[vi][vi] += abs(sign_weight)
                L[vj][vj] += abs(sign_weight)
    return L


def power_iteration(matrix, n, n_vectors=4, n_iter=200):
    """Extract top eigenvectors via power iteration with deflation."""
    vectors = []
    eigenvalues = []
    residual = [row[:] for row in matrix]

    for idx in range(n_vectors):
        vec = [random.gauss(0,1) for _ in range(n)]
        norm = math.sqrt(sum(v*v for v in vec))
        vec = [v/norm for v in vec]

        for it in range(n_iter):
            new = [sum(residual[i][j]*vec[j] for j in range(n)) for i in range(n)]
            # Orthogonalize against previous
            for prev in vectors:
                dot = sum(new[i]*prev[i] for i in range(n))
                new = [new[i] - dot*prev[i] for i in range(n)]
            ev = math.sqrt(sum(v*v for v in new))
            if ev > 1e-10:
                vec = [v/ev for v in new]

        vectors.append(vec)
        eigenvalues.append(ev)

        # Deflate
        for i in range(n):
            for j in range(n):
                residual[i][j] -= ev * vec[i] * vec[j]

    return eigenvalues, vectors


# ============================================================
# H1. SPECTRAL POSITION: bit's coordinates in eigenvector space
# ============================================================

def spectral_position():
    """
    Each bit gets coordinates (v1[i], v2[i], v3[i]) in the
    top eigenvectors of the SIGNED Laplacian.

    Does position in spectral space predict correct value?
    """
    print("=" * 70)
    print("H1. SPECTRAL POSITION in signed Laplacian")
    print("=" * 70)

    random.seed(42); n = 12

    spectral_correct = 0; tension_correct = 0; total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # Signed Laplacian eigenvectors
        L = build_signed_laplacian(clauses, n)
        eigenvalues, vectors = power_iteration(L, n, 4)

        for var in range(n):
            total += 1
            actual = correct_val[var]

            # Tension
            if (1 if tensions[var] >= 0 else 0) == actual:
                tension_correct += 1

            # Spectral: use sign of SECOND eigenvector (Fiedler-like)
            # multiplied by tension direction
            if len(vectors) >= 2:
                spectral_sign = vectors[1][var]
                # Combine: tension direction × spectral position
                combined = tensions[var] * (1 + abs(spectral_sign))
                if (1 if combined >= 0 else 0) == actual:
                    spectral_correct += 1

    print(f"\n  Tension:              {tension_correct/total*100:.1f}%")
    print(f"  Spectral-enhanced:    {spectral_correct/total*100:.1f}%")


# ============================================================
# H2. GRAPH CURVATURE: Ollivier-Ricci curvature at each bit
# ============================================================

def graph_curvature():
    """
    Ollivier-Ricci curvature: measures local geometry.
    Positive curvature = bits cluster together (sphere-like).
    Negative curvature = bits spread apart (hyperbolic).
    Zero = flat.

    Approximation: for edge (i,j):
    κ(i,j) = 1 - d(N(i), N(j)) / d(i,j)
    where N = neighborhood.

    Does curvature predict correct/wrong?
    """
    print("\n" + "=" * 70)
    print("H2. GRAPH CURVATURE at each bit")
    print("=" * 70)

    random.seed(42); n = 12

    correct_curv = []; wrong_curv = []

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        adj = {i: set() for i in range(n)}
        for clause in clauses:
            vs = [v for v,s in clause]
            for a in range(len(vs)):
                for b in range(a+1, len(vs)):
                    adj[vs[a]].add(vs[b])
                    adj[vs[b]].add(vs[a])

        for var in range(n):
            pred = 1 if tensions[var] >= 0 else 0
            is_correct = pred == correct_val[var]

            # Average curvature of edges incident to var
            curvatures = []
            for nb in adj[var]:
                # Shared neighbors
                shared = len(adj[var] & adj[nb])
                total_possible = min(len(adj[var])-1, len(adj[nb])-1)
                if total_possible > 0:
                    kappa = shared / total_possible  # proxy for curvature
                else:
                    kappa = 0
                curvatures.append(kappa)

            avg_curv = sum(curvatures)/len(curvatures) if curvatures else 0

            if is_correct:
                correct_curv.append(avg_curv)
            else:
                wrong_curv.append(avg_curv)

    mean = lambda lst: sum(lst)/len(lst) if lst else 0
    print(f"\n  Correct bits: avg curvature = {mean(correct_curv):.4f}")
    print(f"  Wrong bits:   avg curvature = {mean(wrong_curv):.4f}")
    ratio = mean(wrong_curv)/mean(correct_curv) if mean(correct_curv) > 0 else 0
    print(f"  Ratio: {ratio:.2f}")


# ============================================================
# H3. FLOW FIELD: Send tension-weighted current through graph
# ============================================================

def flow_field():
    """
    Inject "current" proportional to tension at each bit.
    Let it flow through the signed graph.
    Where current ACCUMULATES = important for solution.

    Like electric current: tension = voltage, graph = resistor network.
    Steady-state current = solution to Kirchhoff's equations.
    """
    print("\n" + "=" * 70)
    print("H3. FLOW FIELD: Current through signed graph")
    print("=" * 70)

    random.seed(42); n = 12

    flow_correct = 0; tension_correct = 0; total = 0

    for seed in range(150):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # Build conductance matrix from clause signs
        G = [[0.0]*n for _ in range(n)]
        for clause in clauses:
            lits = [(v,s) for v,s in clause]
            for a in range(len(lits)):
                for b in range(a+1, len(lits)):
                    vi, si = lits[a]; vj, sj = lits[b]
                    # Conductance: positive if same sign, negative if different
                    # (inverted because of L15: same signs → anti-clones)
                    conductance = -1.0 if si == sj else 1.0  # INVERTED!
                    G[vi][vj] += conductance
                    G[vj][vi] += conductance

        # Flow: iteratively propagate tension through signed conductance
        flow = [tensions[v] for v in range(n)]
        for _ in range(5):
            new_flow = [0.0]*n
            for i in range(n):
                incoming = sum(G[i][j] * flow[j] for j in range(n) if j != i)
                degree = sum(abs(G[i][j]) for j in range(n) if j != i)
                if degree > 0:
                    new_flow[i] = 0.5 * flow[i] + 0.5 * incoming / degree
                else:
                    new_flow[i] = flow[i]
            flow = new_flow

        for var in range(n):
            total += 1
            actual = correct_val[var]

            if (1 if tensions[var] >= 0 else 0) == actual:
                tension_correct += 1
            if (1 if flow[var] >= 0 else 0) == actual:
                flow_correct += 1

    print(f"\n  Tension:    {tension_correct/total*100:.1f}%")
    print(f"  Flow field: {flow_correct/total*100:.1f}%")
    print(f"  Delta:      {(flow_correct-tension_correct)/total*100:+.1f}%")


# ============================================================
# H4. HOLOGRAPHIC PROJECTION: project solution onto eigenbasis
# ============================================================

def holographic_projection():
    """
    If solution info is holographic, it should be concentrated
    in specific EIGENMODES of the signed Laplacian.

    Project the correct assignment onto each eigenmode.
    Which modes carry the most signal?
    Can we reconstruct from top-k modes?
    """
    print("\n" + "=" * 70)
    print("H4. HOLOGRAPHIC PROJECTION: Solution in eigenbasis")
    print("=" * 70)

    random.seed(42); n = 12

    mode_accuracy = {k: 0 for k in range(1, 5)}
    total = 0

    for seed in range(100):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if not solutions: continue

        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]
        sol_vec = [2*correct_val[v]-1 for v in range(n)]  # ±1 encoding

        L = build_signed_laplacian(clauses, n)
        eigenvalues, vectors = power_iteration(L, n, 4)

        total += 1

        # Project solution onto each eigenmode
        for k in range(1, min(5, len(vectors)+1)):
            # Reconstruct from top-k modes
            reconstruction = [0.0]*n
            for mode in range(k):
                projection = sum(sol_vec[i]*vectors[mode][i] for i in range(n))
                for i in range(n):
                    reconstruction[i] += projection * vectors[mode][i]

            # Accuracy of reconstruction
            correct = sum(1 for v in range(n)
                         if (1 if reconstruction[v] >= 0 else 0) == correct_val[v])
            mode_accuracy[k] += correct / n

    print(f"\n  Reconstruction accuracy from top-k signed Laplacian modes:")
    print(f"  {'k modes':>8} | {'accuracy':>8}")
    print("  " + "-" * 20)
    for k in range(1, 5):
        acc = mode_accuracy[k]/total*100 if total > 0 else 0
        print(f"  {k:>8} | {acc:>7.1f}%")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    spectral_position()
    graph_curvature()
    flow_field()
    holographic_projection()
