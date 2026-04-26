"""
Session 55: Persistent homology of mini-SHA orbit cloud.

WILD: For a small SHA variant (8-bit state space, 256 nodes), compute
persistent homology of the orbit graph as the threshold ε grows.

Setup:
- 8 input bits, 8 output bits.
- All 256 input states → all 256 output states (= permutation OR functional graph).
- Build distance matrix: d(x, y) = Hamming(R(x), R(y)) — distance in OUTPUT space.
- For each ε, build Vietoris-Rips complex: edge between (x, y) if d(R(x), R(y)) ≤ ε.
- Compute Betti numbers β_0 (connected components), β_1 (1-cycles).

Persistent features = topological invariants surviving across ε ranges.

For ideal random function: VR complex transitions sharply at ε = N/2 = 4.
For structured SHA: may show plateaus (persistent topology).
"""
import numpy as np
from collections import defaultdict


# Mini-SHA on 8-bit state (4 registers of 2 bits each)
N_REG = 2
NUM_REGS = 4


def mini_round(state):
    a, b, c, d = state
    mask = (1 << N_REG) - 1
    rot = lambda x, r: ((x >> r) | (x << (N_REG - r))) & mask
    Σ_a = rot(a, 1)
    Σ_c = rot(c, 1)
    Maj = (a & b) ^ (a & c) ^ (b & c)
    Ch = (c & d) ^ ((~c & mask) & a)
    T1 = (d + Σ_c + Ch) & mask
    T2 = (Σ_a + Maj) & mask
    return ((T1 + T2) & mask, a, b, (c + T1) & mask)


def state_to_int(s):
    return s[0] | (s[1] << N_REG) | (s[2] << 2 * N_REG) | (s[3] << 3 * N_REG)


def int_to_state(x):
    mask = (1 << N_REG) - 1
    return (x & mask, (x >> N_REG) & mask, (x >> (2 * N_REG)) & mask, (x >> (3 * N_REG)) & mask)


def hamming_int(a, b, n_bits):
    return bin(a ^ b).count('1')


def main():
    print("=== Session 55: Persistent homology of mini-SHA ===\n")
    n_bits = N_REG * NUM_REGS
    n_states = 2 ** n_bits
    print(f"  Mini-SHA: {n_bits}-bit state, {n_states} nodes.\n")

    # Build round permutation
    image = np.zeros(n_states, dtype=int)
    for x in range(n_states):
        image[x] = state_to_int(mini_round(int_to_state(x)))

    # Distance matrix d[x, y] = Hamming(R(x), R(y))
    d = np.zeros((n_states, n_states), dtype=int)
    for x in range(n_states):
        for y in range(n_states):
            d[x, y] = hamming_int(image[x], image[y], n_bits)

    print(f"  Distance matrix shape {d.shape}, mean d = {d.mean():.2f}, std = {d.std():.2f}")
    print(f"  Expected ideal: mean = {n_bits/2}, std ≈ {np.sqrt(n_bits)/2:.2f}\n")

    # Persistent homology via threshold scan
    print(f"  Vietoris-Rips persistence (threshold ε from 0 to {n_bits}):")
    print(f"  {'ε':>3}  {'#edges':>7}  {'β_0 (components)':>17}  {'β_1 (cycles, est.)':>20}")
    print(f"  {'-'*60}")

    for eps in range(n_bits + 1):
        # Edges: pairs (x, y) with d[x, y] ≤ eps and x < y
        edges = []
        for x in range(n_states):
            for y in range(x + 1, n_states):
                if d[x, y] <= eps:
                    edges.append((x, y))

        # Connected components via union-find
        parent = list(range(n_states))
        def find(u):
            while parent[u] != u:
                parent[u] = parent[parent[u]]
                u = parent[u]
            return u
        for u, v in edges:
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
        beta_0 = len(set(find(u) for u in range(n_states)))

        # β_1 estimate: |E| - |V| + β_0 (Euler-like, accurate for graphs after triangle filling).
        # For full β_1 need 2-simplex (triangle) count. Approximate by graph estimate.
        beta_1_graph = len(edges) - n_states + beta_0

        print(f"  {eps:>3}  {len(edges):>7}  {beta_0:>17}  {beta_1_graph:>20}")

    print(f"""

=== Theorem 55.1 (TDA of mini-SHA) ===

The output cloud {{R(x) : x ∈ F_2^{n_bits}}} has connected-components count
β_0 evolving with threshold ε:
  - ε = 0: all isolated (β_0 = {n_states})
  - ε = {n_bits}: fully connected (β_0 = 1)

The transition shape reveals topological structure:
  - Sharp cliff at ε ≈ n/2: random-like (no persistent features beyond β_0).
  - Gradual transition: structural clustering present.

For full SHA-256 on F_2^256: would need TDA library (gudhi/ripser) on
sampled states; expect cliff at ε ≈ 128.
""")


if __name__ == "__main__":
    main()
