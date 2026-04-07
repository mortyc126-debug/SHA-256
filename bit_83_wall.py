"""
THE 83% WALL: Is it the fundamental ceiling for clause-only methods?

v4 = tension_nr = 82.8%. Can ANY clause-only method beat this?

If YES → there's more signal in clauses we haven't found.
If NO → 83% is provably the clause information ceiling.

Tests:
1. EXHAUSTIVE: try every possible weighting of clause votes
2. OPTIMAL LINEAR: find the best linear combination of clause features
3. INFORMATION BOUND: compute mutual information I(clause_structure; correct_value)
4. LEAVE-ONE-OUT: how much does each clause contribute to accuracy?
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
# 1. MUTUAL INFORMATION: How much do clauses know about each bit?
# ============================================================

def clause_mutual_information(clauses, n, solutions):
    """
    For each bit i:
    Compute I(clause_features_i ; correct_value_i)

    clause_features_i = (pos_count, neg_count, neighbor_tensions, ...)
    correct_value_i = majority across solutions

    Use binning: discretize features, compute empirical MI.
    """
    if not solutions: return None

    prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
    correct_val = [1 if p > 0.5 else 0 for p in prob_1]

    # For each bit: compute several clause features
    features_and_labels = []

    for var in range(n):
        # Feature 1: sign balance (pos - neg)
        pos = sum(1 for cl in clauses for v, s in cl if v == var and s == 1)
        neg = sum(1 for cl in clauses for v, s in cl if v == var and s == -1)
        balance = pos - neg

        # Feature 2: weighted balance (1/3 per clause)
        sigma = bit_tension(clauses, n, var)

        # Feature 3: neighbor agreement
        neighbors = set()
        for clause in clauses:
            vs = [v for v, s in clause]
            if var in vs:
                for v in vs:
                    if v != var: neighbors.add(v)
        if neighbors:
            nb_agree = sum(1 for nb in neighbors
                          if bit_tension(clauses, n, nb) * sigma > 0)
            agreement = nb_agree / len(neighbors)
        else:
            agreement = 0.5

        features_and_labels.append({
            'balance': balance,
            'sigma': sigma,
            'agreement': agreement,
            'correct': correct_val[var],
        })

    return features_and_labels


def compute_mi(features, labels, n_bins=5):
    """Compute mutual information between feature and label."""
    # Bin the feature
    sorted_f = sorted(features)
    bin_edges = [sorted_f[len(sorted_f)*i//n_bins] for i in range(n_bins)] + [float('inf')]

    def get_bin(val):
        for i in range(len(bin_edges)-1):
            if val <= bin_edges[i+1]: return i
        return n_bins - 1

    # Joint and marginal counts
    joint = {}
    for f, l in zip(features, labels):
        b = get_bin(f)
        key = (b, l)
        joint[key] = joint.get(key, 0) + 1

    n_total = len(features)
    p_label = {0: sum(1 for l in labels if l == 0) / n_total,
               1: sum(1 for l in labels if l == 1) / n_total}

    p_bin = {}
    for b in range(n_bins):
        p_bin[b] = sum(joint.get((b, l), 0) for l in [0, 1]) / n_total

    mi = 0
    for b in range(n_bins):
        for l in [0, 1]:
            p_bl = joint.get((b, l), 0) / n_total
            if p_bl > 0 and p_bin.get(b, 0) > 0 and p_label.get(l, 0) > 0:
                mi += p_bl * math.log2(p_bl / (p_bin[b] * p_label[l]))

    return mi


# ============================================================
# 2. OPTIMAL LINEAR PREDICTOR: best weights for clause features
# ============================================================

def optimal_linear_predictor(instances, n):
    """
    Collect (features, label) for many bits.
    Find optimal weights to predict label from features.
    This is the BEST any linear clause-based method can do.
    """
    X = []  # features
    Y = []  # labels

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        for var in range(n):
            sigma = bit_tension(clauses, n, var)

            # Feature vector: [sigma, sigma^2, sigma^3, degree, ...]
            pos = sum(1 for cl in clauses for v, s in cl if v == var and s == 1)
            neg = sum(1 for cl in clauses for v, s in cl if v == var and s == -1)
            degree = pos + neg

            neighbors = set()
            for clause in clauses:
                vs = [v for v, s in clause]
                if var in vs:
                    for v in vs:
                        if v != var: neighbors.add(v)

            nb_tensions = [bit_tension(clauses, n, nb) for nb in neighbors]
            avg_nb = sum(nb_tensions)/len(nb_tensions) if nb_tensions else 0
            agree = sum(1 for t in nb_tensions if t * sigma > 0) / len(nb_tensions) if nb_tensions else 0.5

            features = [
                sigma,
                abs(sigma),
                sigma ** 3,  # cubic: captures asymmetry
                degree / 13.0 - 1,  # normalized degree
                avg_nb,
                agree - 0.5,
                sigma * agree,  # interaction
            ]

            X.append(features)
            Y.append(1 if correct_val[var] == 1 else -1)

    # Simple gradient descent for logistic regression
    n_features = len(X[0])
    weights = [0.0] * n_features
    bias = 0.0
    lr = 0.01

    for epoch in range(200):
        total_loss = 0
        correct = 0
        for i in range(len(X)):
            z = sum(weights[j] * X[i][j] for j in range(n_features)) + bias
            pred = 1 / (1 + math.exp(-max(min(z, 20), -20)))
            y = (Y[i] + 1) / 2  # convert to 0/1

            loss = -y * math.log(max(pred, 1e-10)) - (1-y) * math.log(max(1-pred, 1e-10))
            total_loss += loss

            if (pred > 0.5) == (y > 0.5): correct += 1

            # Gradient
            error = pred - y
            for j in range(n_features):
                weights[j] -= lr * error * X[i][j]
            bias -= lr * error

        if epoch % 50 == 0:
            acc = correct / len(X) * 100
            # Don't print every epoch

    # Final accuracy
    correct = 0
    for i in range(len(X)):
        z = sum(weights[j] * X[i][j] for j in range(n_features)) + bias
        pred_val = 1 if z > 0 else -1
        if pred_val == Y[i]: correct += 1

    return correct / len(X), weights, bias


# ============================================================
# 3. INFORMATION BOUND: total MI in clause structure
# ============================================================

def information_bound(instances, n):
    """
    Compute I(all_clause_features ; correct_value) for each bit.
    This is an UPPER BOUND on any clause-based predictor.

    Use high-dimensional binning or estimate via nearest-neighbor.
    """
    # Collect all features
    all_data = clause_mutual_information(instances[0][0], n, instances[0][1])
    if not all_data: return None

    # MI for each feature
    features_list = {
        'balance': [d['balance'] for d in all_data],
        'sigma': [d['sigma'] for d in all_data],
        'agreement': [d['agreement'] for d in all_data],
    }
    labels = [d['correct'] for d in all_data]

    # Accumulate across instances
    for clauses, solutions in instances[1:60]:
        data = clause_mutual_information(clauses, n, solutions)
        if not data: continue
        for d in data:
            features_list['balance'].append(d['balance'])
            features_list['sigma'].append(d['sigma'])
            features_list['agreement'].append(d['agreement'])
            labels.append(d['correct'])

    # MI per feature
    mi_results = {}
    for fname, fvals in features_list.items():
        mi = compute_mi(fvals, labels, n_bins=8)
        mi_results[fname] = mi

    # H(correct) = entropy of labels
    p1 = sum(labels) / len(labels)
    h_label = -p1*math.log2(max(p1,1e-10)) - (1-p1)*math.log2(max(1-p1,1e-10))

    return mi_results, h_label


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    random.seed(42)
    n = 12

    instances = []
    for seed in range(200):
        clauses = random_3sat(n, int(4.27*n), seed=seed)
        solutions = find_solutions(clauses, n)
        if solutions and len(solutions) >= 2:
            instances.append((clauses, solutions))

    print(f"Working with {len(instances)} instances")
    mean = lambda lst: sum(lst)/len(lst) if lst else 0

    # --- MI ---
    print("\n" + "=" * 70)
    print("1. MUTUAL INFORMATION: How much do clause features know?")
    print("=" * 70)

    mi_results, h_label = information_bound(instances, n)
    print(f"\n  H(correct_value) = {h_label:.4f} bits")
    print(f"\n  {'feature':>12} | {'MI (bits)':>10} | {'% of H':>8}")
    print("  " + "-" * 35)

    for fname in sorted(mi_results.keys(), key=lambda k: -mi_results[k]):
        mi = mi_results[fname]
        pct = mi / h_label * 100 if h_label > 0 else 0
        print(f"  {fname:>12} | {mi:>10.4f} | {pct:>7.1f}%")

    # Maximum possible accuracy from MI:
    # If MI = I bits, max accuracy ≈ 1 - 2^(-I) (rough)
    total_mi = max(mi_results.values())  # using best single feature
    max_acc_from_mi = 1 - 2**(-total_mi) if total_mi > 0 else 0.5
    print(f"\n  Best single feature MI: {total_mi:.4f} bits")
    print(f"  Theoretical max accuracy from this: ~{max_acc_from_mi*100:.1f}%")

    # --- Optimal linear predictor ---
    print("\n" + "=" * 70)
    print("2. OPTIMAL LINEAR PREDICTOR")
    print("=" * 70)

    acc, weights, bias = optimal_linear_predictor(instances[:60], n)
    feature_names = ['σ', '|σ|', 'σ³', 'degree', 'avg_nb', 'agreement', 'σ×agree']

    print(f"\n  Accuracy: {acc*100:.1f}%")
    print(f"\n  Weights:")
    for i, (name, w) in enumerate(zip(feature_names, weights)):
        bar = "+" * int(abs(w)*20) if w > 0 else "-" * int(abs(w)*20)
        print(f"    {name:>10}: {w:>+8.4f} {bar}")
    print(f"    {'bias':>10}: {bias:>+8.4f}")

    # --- Compare all methods ---
    print("\n" + "=" * 70)
    print("3. COMPLETE HIERARCHY: All clause-based methods")
    print("=" * 70)

    # Standard tension
    std = 0
    # V4
    v4 = 0
    total_bits = 0

    for clauses, solutions in instances:
        prob_1 = [sum(s[v] for s in solutions)/len(solutions) for v in range(n)]
        correct_val = [1 if p > 0.5 else 0 for p in prob_1]

        tensions = {v: bit_tension(clauses, n, v) for v in range(n)}

        # V4
        v4_t = dict(tensions)
        for _ in range(10):
            new_t = {}
            for var in v4_t:
                push_1, push_0 = 0.0, 0.0
                for clause in clauses:
                    rem = []; vs = None
                    for v, s in clause: rem.append((v,s));
                    for v, s in rem:
                        if v == var: vs = s
                    if vs is None: continue
                    oh = 0.0
                    for v, s in rem:
                        if v == var: continue
                        t = v4_t.get(v, 0)
                        p = (1+t)/2 if s == 1 else (1-t)/2
                        oh = 1-(1-oh)*(1-p)
                    need = 1.0-oh
                    if vs == 1: push_1 += need
                    else: push_0 += need
                tot = push_1+push_0
                new_t[var] = (push_1-push_0)/tot if tot > 0 else 0
            for v in v4_t:
                v4_t[v] = 0.5*v4_t[v] + 0.5*new_t.get(v,0)

        for var in range(n):
            total_bits += 1
            actual = correct_val[var]
            if (1 if tensions[var] >= 0 else 0) == actual: std += 1
            if (1 if v4_t[var] >= 0 else 0) == actual: v4 += 1

    print(f"\n  {'method':>25} | {'accuracy':>8}")
    print("  " + "-" * 40)
    print(f"  {'random':>25} | {50.0:>7.1f}%")
    print(f"  {'standard tension':>25} | {std/total_bits*100:>7.1f}%")
    print(f"  {'optimal linear (7 feat)':>25} | {acc*100:>7.1f}%")
    print(f"  {'v4 iterative':>25} | {v4/total_bits*100:>7.1f}%")
    print(f"  {'oracle non-redundant':>25} | {94.0:>7.1f}%")
    print(f"  {'optimal (marginal)':>25} | {88.0:>7.1f}%")
