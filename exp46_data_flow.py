#!/usr/bin/env python3
"""
EXP 46: Data Flow Decomposition — New Mathematics from Scratch

NOT cryptanalysis. NOT statistics. NOT correlation.
COMPUTATIONAL GRAPH analysis.

SHA-256 = graph of 448 nodes (64 rounds × 7 operations).
Each node: takes 2-3 inputs × 32 bits → 1 output × 32 bits.

DECOMPOSITION BY DATA FLOW:
- Trace which input bits reach which output bits
- Find INDEPENDENT data flow streams
- If streams are weakly coupled → solve collision per-stream
- Recombine → full collision

This has NEVER been done because it's not cryptanalysis.
It's PROGRAM ANALYSIS applied to a hash function.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def trace_input_to_output(W16, input_word, input_bit, num_rounds=64):
    """
    Trace: which output bits does input bit (word, bit) affect?
    Returns 256-bit influence vector.
    """
    base = sha256_compress(W16)

    W_pert = list(W16)
    W_pert[input_word] ^= (1 << input_bit)
    pert = sha256_compress(W_pert)

    influence = []
    for w in range(8):
        d = base[w] ^ pert[w]
        for b in range(32):
            influence.append((d >> b) & 1)

    return np.array(influence, dtype=np.int64)

def build_influence_matrix(W16):
    """
    Full 512×256 influence matrix:
    M[i][j] = 1 if input bit i affects output bit j.

    This is the DATA FLOW GRAPH in matrix form.
    """
    M = np.zeros((512, 256), dtype=np.int64)

    base = sha256_compress(W16)

    for word in range(16):
        for bit in range(32):
            W_pert = list(W16)
            W_pert[word] ^= (1 << bit)
            pert = sha256_compress(W_pert)

            idx_in = word * 32 + bit
            for w in range(8):
                d = base[w] ^ pert[w]
                for b in range(32):
                    M[idx_in][w * 32 + b] = (d >> b) & 1

    return M

def find_independent_streams(M, threshold=0.1):
    """
    Find groups of output bits that depend on DISJOINT sets of input bits.

    If output bits {O1} depend on inputs {I1} and
       output bits {O2} depend on inputs {I2} where I1 ∩ I2 = ∅
    → streams are INDEPENDENT → can solve separately.
    """
    n_out = M.shape[1]

    # For each output bit: which input bits affect it?
    input_sets = []
    for j in range(n_out):
        inputs_j = set(np.where(M[:, j] == 1)[0])
        input_sets.append(inputs_j)

    # Build output-output coupling matrix: how much do their input sets overlap?
    coupling = np.zeros((n_out, n_out))
    for i in range(n_out):
        for j in range(i + 1, n_out):
            if len(input_sets[i]) > 0 and len(input_sets[j]) > 0:
                overlap = len(input_sets[i] & input_sets[j])
                union = len(input_sets[i] | input_sets[j])
                coupling[i][j] = overlap / union if union > 0 else 0
                coupling[j][i] = coupling[i][j]

    return coupling, input_sets

def test_data_flow_structure(N=30):
    """Analyze the data flow graph of SHA-256."""
    print("\n--- TEST 1: DATA FLOW STRUCTURE ---")

    # Build influence matrix for several messages
    all_couplings = []

    for trial in range(N):
        W16 = random_w16()
        M = build_influence_matrix(W16)

        # Basic statistics
        influence_per_output = M.sum(axis=0)  # How many inputs affect each output
        influence_per_input = M.sum(axis=1)   # How many outputs each input affects

        if trial == 0:
            print(f"Influence matrix shape: {M.shape}")
            print(f"Input influence (per input bit):")
            print(f"  Mean: {influence_per_input.mean():.1f}/256 output bits")
            print(f"  Min: {influence_per_input.min()}, Max: {influence_per_input.max()}")
            print(f"Output influence (per output bit):")
            print(f"  Mean: {influence_per_output.mean():.1f}/512 input bits")
            print(f"  Min: {influence_per_output.min()}, Max: {influence_per_output.max()}")

            # GF(2) rank
            rank = np.linalg.matrix_rank(M.astype(np.float64))
            print(f"GF(2)-approximate rank: {rank}/256")

        # Coupling analysis
        if trial < 5:
            coupling, input_sets = find_independent_streams(M)
            avg_coupling = coupling[np.triu_indices(256, k=1)].mean()
            min_coupling = coupling[np.triu_indices(256, k=1)].min()
            max_coupling = coupling[np.triu_indices(256, k=1)].max()

            # How many output bits share < 10% of their inputs?
            weak_pairs = np.sum(coupling[np.triu_indices(256, k=1)] < 0.1)
            total_pairs = 256 * 255 // 2

            print(f"\n  Trial {trial}: avg_coupling={avg_coupling:.4f}, "
                  f"min={min_coupling:.4f}, max={max_coupling:.4f}")
            print(f"  Weakly coupled pairs (<10%): {weak_pairs}/{total_pairs} "
                  f"({weak_pairs/total_pairs*100:.1f}%)")

            # Is coupling MESSAGE-DEPENDENT?
            all_couplings.append(avg_coupling)

    if len(all_couplings) > 1:
        print(f"\nCoupling across messages: mean={np.mean(all_couplings):.4f}, "
              f"std={np.std(all_couplings):.4f}")
        if np.std(all_couplings) > 0.01:
            print("*** Coupling is MESSAGE-DEPENDENT! ***")

def test_stream_decomposition(N=10):
    """
    Attempt to decompose output bits into weakly-coupled streams.
    If possible → collision per-stream is cheaper.
    """
    print("\n--- TEST 2: STREAM DECOMPOSITION ---")

    W16 = random_w16()
    M = build_influence_matrix(W16)
    coupling, input_sets = find_independent_streams(M)

    # Spectral clustering on coupling matrix
    eigvals = np.linalg.eigvalsh(coupling)
    eigvals_sorted = np.sort(eigvals)[::-1]

    print(f"Coupling matrix eigenvalues:")
    print(f"  Top 10: {eigvals_sorted[:10].round(4)}")
    print(f"  Bottom 5: {eigvals_sorted[-5:].round(4)}")

    # How many clusters? (gaps in eigenvalue spectrum)
    gaps = eigvals_sorted[:-1] - eigvals_sorted[1:]
    max_gap_idx = np.argmax(gaps[:20]) + 1
    print(f"  Largest gap at position {max_gap_idx}: gap={gaps[max_gap_idx-1]:.4f}")
    print(f"  Suggested clusters: {max_gap_idx}")

    # Simple thresholding: group output bits with coupling > 0.5
    from collections import defaultdict

    # Find connected components at threshold 0.5
    adj = coupling > 0.5
    visited = [False] * 256
    components = []

    for start in range(256):
        if visited[start]:
            continue
        comp = []
        stack = [start]
        while stack:
            node = stack.pop()
            if visited[node]:
                continue
            visited[node] = True
            comp.append(node)
            for neighbor in range(256):
                if not visited[neighbor] and adj[node][neighbor]:
                    stack.append(neighbor)
        components.append(comp)

    print(f"\nConnected components at coupling > 0.5:")
    print(f"  Number of components: {len(components)}")
    comp_sizes = sorted([len(c) for c in components], reverse=True)
    print(f"  Sizes: {comp_sizes[:10]}")

    if len(components) > 1 and comp_sizes[1] > 10:
        print(f"  *** MULTIPLE large components! Potential stream decomposition! ***")
        # If we have k components of size n_i:
        # collision cost = max(2^(n_i/2)) instead of 2^(256/2) = 2^128
        max_comp = max(comp_sizes)
        print(f"  Largest component: {max_comp} bits → collision cost 2^{max_comp//2}")
    else:
        print(f"  Single giant component → no decomposition advantage")

def test_reduced_round_flow(N=10):
    """
    Data flow structure at REDUCED rounds.
    At which round does the graph become fully connected?
    """
    print("\n--- TEST 3: REDUCED-ROUND DATA FLOW ---")

    W16 = random_w16()

    for R in [1, 2, 4, 8, 16, 32, 64]:
        states = sha256_rounds(W16, R)
        final = states[R]

        # Build influence matrix for R rounds
        M = np.zeros((512, 256), dtype=np.int64)
        for word in range(16):
            for bit in range(32):
                W_p = list(W16)
                W_p[word] ^= (1 << bit)
                states_p = sha256_rounds(W_p, R)
                final_p = states_p[R]

                idx_in = word * 32 + bit
                for w in range(8):
                    d = final[w] ^ final_p[w]
                    for b in range(32):
                        M[idx_in][w*32+b] = (d>>b) & 1

        # Density: what fraction of entries are 1?
        density = M.sum() / (512 * 256)

        # Rank
        rank = np.linalg.matrix_rank(M.astype(np.float64))

        # Number of zero columns (output bits unreachable)
        zero_cols = np.sum(M.sum(axis=0) == 0)

        # Average coupling
        influence_per_output = M.sum(axis=0)
        avg_influence = influence_per_output[influence_per_output > 0].mean()

        print(f"  R={R:>2}: density={density:.4f}, rank={rank:>3}/256, "
              f"zero_cols={zero_cols:>3}, avg_influence={avg_influence:.1f}/512")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 46: DATA FLOW DECOMPOSITION")
    print("Not cryptanalysis. Program analysis.")
    print("="*60)

    test_data_flow_structure(10)
    test_stream_decomposition()
    test_reduced_round_flow()

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
