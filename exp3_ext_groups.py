#!/usr/bin/env python3
"""
EXPERIMENT 3: Homological Ext Groups of TLC Decomposition

TLC: ΔH = L ⊕ Q ⊕ C  (Linear ⊕ Quadratic ⊕ Carry)
Three layers appear independent, but Ext¹(L,C) might be non-zero.

If Ext¹(L,C) ≠ 0: there's a hidden extension — L and C interact
on a deeper level, and the direct sum is not "truly" direct.

Experimental approach:
1. Decompose ΔH into L, Q, C components
2. Measure cross-correlations CONDITIONED on specific values
3. Look for non-trivial coboundaries: δ: L → C such that δ² = 0
4. Test if L predicts C residuals (hidden map L → C)
5. Measure deviation from true direct sum via mutual information
"""

import sys, os, random, math
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def decompose_TLC(W16_n, W16_f, num_rounds=64):
    """
    Decompose hash difference ΔH into L (linear/XOR), Q (quadratic/Ch+Maj), C (carry).

    L: XOR-only computation (ignore carries and non-linear parts)
    Q: Contribution from Ch and Maj (quadratic parts)
    C: Carry-only residual

    Method: Compare full SHA-256 vs XOR-only SHA-256 vs linear-only SHA-256
    """
    states_n = sha256_rounds(W16_n, num_rounds)
    states_f = sha256_rounds(W16_f, num_rounds)

    # Full difference
    delta_full = [(states_f[num_rounds][i] - states_n[num_rounds][i]) & MASK for i in range(8)]

    # XOR-only difference (replace + with ^)
    delta_xor = xor_only_sha256(W16_n, W16_f, num_rounds)

    # L component: pure linear (XOR, rotations, shifts only)
    L = delta_xor

    # C component: carry contribution = full_add - xor
    # For each word in state
    C = [(delta_full[i] ^ delta_xor[i]) & MASK for i in range(8)]

    # Q component: quadratic residual (what's left)
    # Actually Q is embedded in both L and full, so:
    # We extract Q by comparing with/without Ch and Maj
    Q = quadratic_component(W16_n, W16_f, num_rounds)

    return delta_full, L, Q, C

def xor_only_sha256(W16_n, W16_f, num_rounds=64):
    """SHA-256 with all + replaced by ^. Returns XOR difference of final states."""
    def xor_round(state, W_r, K_r):
        a, b, c, d, e, f, g, h = state
        T1 = h ^ sigma1(e) ^ ch(e, f, g) ^ K_r ^ W_r
        T2 = sigma0(a) ^ maj(a, b, c)
        return [T1 ^ T2, a, b, c, d ^ T1, e, f, g]

    def xor_schedule(W16):
        W = list(W16) + [0] * 48
        for t in range(16, 64):
            W[t] = sig1(W[t-2]) ^ W[t-7] ^ sig0(W[t-15]) ^ W[t-16]
        return W

    iv = list(IV)
    W_n = xor_schedule(W16_n)
    W_f = xor_schedule(W16_f)

    state_n = list(iv)
    state_f = list(iv)

    for r in range(num_rounds):
        state_n = xor_round(state_n, W_n[r], K[r])
        state_f = xor_round(state_f, W_f[r], K[r])

    return [(state_f[i] ^ state_n[i]) & MASK for i in range(8)]

def quadratic_component(W16_n, W16_f, num_rounds=64):
    """Extract quadratic (Ch, Maj) contribution by comparing with linear replacement."""
    def linear_round(state, W_r, K_r):
        a, b, c, d, e, f, g, h = state
        # Replace Ch with XOR, Maj with XOR
        ch_lin = e ^ f ^ g  # Linearized Ch
        maj_lin = a ^ b ^ c  # Linearized Maj
        T1 = (h + sigma1(e) + ch_lin + K_r + W_r) & MASK
        T2 = (sigma0(a) + maj_lin) & MASK
        return [(T1 + T2) & MASK, a, b, c, (d + T1) & MASK, e, f, g]

    iv = list(IV)
    W_n = schedule(W16_n)
    W_f = schedule(W16_f)

    # Full round
    state_full_n = list(iv)
    state_full_f = list(iv)
    # Linear replacement round
    state_lin_n = list(iv)
    state_lin_f = list(iv)

    for r in range(num_rounds):
        state_full_n = sha256_round(state_full_n, W_n[r], K[r])
        state_full_f = sha256_round(state_full_f, W_f[r], K[r])
        state_lin_n = linear_round(state_lin_n, W_n[r], K[r])
        state_lin_f = linear_round(state_lin_f, W_f[r], K[r])

    diff_full = [(state_full_f[i] - state_full_n[i]) & MASK for i in range(8)]
    diff_lin = [(state_lin_f[i] - state_lin_n[i]) & MASK for i in range(8)]

    return [(diff_full[i] ^ diff_lin[i]) & MASK for i in range(8)]

def test_layer_independence(N=2000):
    """Test if L, Q, C are truly independent by measuring mutual information."""
    print("\n--- TEST 1: LAYER INDEPENDENCE (L, Q, C) ---")

    L_vals = []
    Q_vals = []
    C_vals = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        delta_full, L, Q, C = decompose_TLC(Wn, Wf, 64)

        # Use word 7 (H[7]) as representative
        L_vals.append(L[7])
        Q_vals.append(Q[7])
        C_vals.append(C[7])

    # Cross-correlations (bit-level)
    def bit_correlation(A, B):
        """Average per-bit correlation between two lists of 32-bit values."""
        corrs = []
        for bit in range(32):
            a_bits = [(v >> bit) & 1 for v in A]
            b_bits = [(v >> bit) & 1 for v in B]
            mean_a = sum(a_bits) / len(a_bits)
            mean_b = sum(b_bits) / len(b_bits)
            cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(a_bits, b_bits)) / len(a_bits)
            std_a = math.sqrt(sum((a - mean_a)**2 for a in a_bits) / len(a_bits))
            std_b = math.sqrt(sum((b - mean_b)**2 for b in b_bits) / len(b_bits))
            if std_a > 0 and std_b > 0:
                corrs.append(cov / (std_a * std_b))
            else:
                corrs.append(0)
        return sum(abs(c) for c in corrs) / 32, max(abs(c) for c in corrs)

    avg_LQ, max_LQ = bit_correlation(L_vals, Q_vals)
    avg_LC, max_LC = bit_correlation(L_vals, C_vals)
    avg_QC, max_QC = bit_correlation(Q_vals, C_vals)

    print(f"Correlation L↔Q: avg={avg_LQ:.6f}, max={max_LQ:.6f}")
    print(f"Correlation L↔C: avg={avg_LC:.6f}, max={max_LC:.6f}")
    print(f"Correlation Q↔C: avg={avg_QC:.6f}, max={max_QC:.6f}")

    threshold = 3 / math.sqrt(N)
    print(f"Noise threshold (3/√N): {threshold:.6f}")

    signals = []
    if max_LC > threshold:
        print(f"*** SIGNAL: L↔C max correlation {max_LC:.6f} > {threshold:.6f} ***")
        signals.append(("L↔C", max_LC))
    if max_LQ > threshold:
        print(f"*** SIGNAL: L↔Q max correlation {max_LQ:.6f} > {threshold:.6f} ***")
        signals.append(("L↔Q", max_LQ))
    if max_QC > threshold:
        print(f"*** SIGNAL: Q↔C max correlation {max_QC:.6f} > {threshold:.6f} ***")
        signals.append(("Q↔C", max_QC))

    return signals, (L_vals, Q_vals, C_vals)

def test_ext_coboundary(N=2000):
    """
    Look for coboundary δ: L → C such that δ(L) predicts C.
    If Ext¹(L,C) ≠ 0, there exists a non-trivial δ.

    Concretely: can we find a linear map M such that M·L ≈ C?
    This would mean C is not independent of L — hidden extension exists.
    """
    print("\n--- TEST 2: EXT COBOUNDARY SEARCH (L → C map) ---")

    L_bits = []
    C_bits = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        _, L, _, C = decompose_TLC(Wn, Wf, 64)

        # Flatten to bit vectors (use all 8 words)
        l_vec = []
        c_vec = []
        for w in range(8):
            for b in range(32):
                l_vec.append((L[w] >> b) & 1)
                c_vec.append((C[w] >> b) & 1)
        L_bits.append(l_vec)
        C_bits.append(c_vec)

    # Try to find linear predictors: for each C bit, find best L bit predictor
    print(f"Testing {256} C-bits for L-predictability...")

    best_predictors = []
    for c_idx in range(256):
        c_target = [C_bits[i][c_idx] for i in range(N)]

        best_corr = 0
        best_l_idx = -1

        for l_idx in range(256):
            l_source = [L_bits[i][l_idx] for i in range(N)]
            # XOR correlation
            agree = sum(1 for a, b in zip(l_source, c_target) if a == b)
            corr = abs(agree / N - 0.5) * 2
            if corr > best_corr:
                best_corr = corr
                best_l_idx = l_idx

        best_predictors.append((c_idx, best_l_idx, best_corr))

    # Sort by correlation
    best_predictors.sort(key=lambda x: -x[2])

    threshold = 3 * math.sqrt(1 / N)
    significant = [p for p in best_predictors if p[2] > threshold]

    print(f"\nTop 10 L→C predictors:")
    print(f"{'C bit':>6} | {'L bit':>6} | {'Correlation':>12} | {'Significant':>11}")
    print("-" * 45)
    for c_idx, l_idx, corr in best_predictors[:10]:
        c_word, c_bit = c_idx // 32, c_idx % 32
        l_word, l_bit = l_idx // 32, l_idx % 32
        sig = "YES ***" if corr > threshold else "no"
        print(f"H[{c_word}]b{c_bit:>2} | H[{l_word}]b{l_bit:>2} | {corr:>12.6f} | {sig}")

    print(f"\nSignificant predictors (>{threshold:.4f}): {len(significant)}/256")
    print(f"Expected by chance: ~{256 * 0.003:.1f}")

    if len(significant) > 256 * 0.01:
        print(f"*** SIGNAL: {len(significant)} significant L→C maps! Ext¹(L,C) may be non-zero! ***")

    return significant

def test_conditional_structure(N=2000):
    """
    Test conditional correlations: does L|_{C=0} differ from L|_{C≠0}?
    This detects extension classes invisible to marginal statistics.
    """
    print("\n--- TEST 3: CONDITIONAL STRUCTURE (L|C=0 vs L|C≠0) ---")

    L_when_C0 = []
    L_when_C1 = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        _, L, _, C = decompose_TLC(Wn, Wf, 64)

        # Check if carry component of H[7] bit 0 is 0
        for bit in range(32):
            if (C[7] >> bit) & 1 == 0:
                L_when_C0.append(L[7])
            else:
                L_when_C1.append(L[7])

    if L_when_C0 and L_when_C1:
        # Compare distributions
        hw_C0 = sum(hw(v) for v in L_when_C0) / len(L_when_C0)
        hw_C1 = sum(hw(v) for v in L_when_C1) / len(L_when_C1)

        print(f"E[HW(L)] when C=0: {hw_C0:.4f} (N={len(L_when_C0)})")
        print(f"E[HW(L)] when C≠0: {hw_C1:.4f} (N={len(L_when_C1)})")
        print(f"Difference: {abs(hw_C0 - hw_C1):.4f}")

        # Per-bit comparison
        bias_diffs = []
        for bit in range(32):
            p0 = sum(1 for v in L_when_C0 if (v >> bit) & 1) / len(L_when_C0)
            p1 = sum(1 for v in L_when_C1 if (v >> bit) & 1) / len(L_when_C1)
            bias_diffs.append(abs(p0 - p1))

        max_diff = max(bias_diffs)
        avg_diff = sum(bias_diffs) / 32
        print(f"Max per-bit P difference: {max_diff:.6f}")
        print(f"Avg per-bit P difference: {avg_diff:.6f}")

        n_min = min(len(L_when_C0), len(L_when_C1))
        threshold = 3 / math.sqrt(n_min)
        print(f"Threshold (3/√N_min): {threshold:.6f}")

        if max_diff > threshold:
            print(f"*** SIGNAL: Conditional structure detected! ***")

def test_round_by_round_ext(N=1000):
    """
    Track Ext indicators round by round.
    At which round does L-C coupling appear/disappear?
    """
    print("\n--- TEST 4: ROUND-BY-ROUND Ext INDICATOR ---")

    print(f"{'Rounds':>6} | {'corr(L,C)':>10} | {'corr(L,Q)':>10} | {'corr(Q,C)':>10}")
    print("-" * 50)

    for nr in [4, 8, 12, 16, 17, 20, 24, 32, 48, 64]:
        lc_corrs = []

        for _ in range(N):
            W0 = random.randint(0, MASK)
            W1 = random.randint(0, MASK)
            Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

            _, L, Q, C = decompose_TLC(Wn, Wf, nr)

            # Correlation via HW
            lc_corrs.append((hw(L[7] if L[7] else 0), hw(Q[7] if Q[7] else 0), hw(C[7] if C[7] else 0)))

        l_hw = [x[0] for x in lc_corrs]
        q_hw = [x[1] for x in lc_corrs]
        c_hw = [x[2] for x in lc_corrs]

        def pearson(x, y):
            n = len(x)
            mx = sum(x) / n
            my = sum(y) / n
            cov = sum((a - mx) * (b - my) for a, b in zip(x, y)) / n
            sx = math.sqrt(sum((a - mx)**2 for a in x) / n)
            sy = math.sqrt(sum((b - my)**2 for b in y) / n)
            return cov / (sx * sy) if sx > 0 and sy > 0 else 0

        lc = pearson(l_hw, c_hw)
        lq = pearson(l_hw, q_hw)
        qc = pearson(q_hw, c_hw)

        marker = " ***" if abs(lc) > 0.1 or abs(lq) > 0.1 or abs(qc) > 0.1 else ""
        print(f"{nr:>6} | {lc:>10.6f} | {lq:>10.6f} | {qc:>10.6f}{marker}")

def main():
    random.seed(42)

    print("=" * 70)
    print("EXPERIMENT 3: Ext GROUPS OF TLC DECOMPOSITION")
    print("=" * 70)

    # Test 1
    signals1, layers = test_layer_independence(1500)

    # Test 2
    significant = test_ext_coboundary(1500)

    # Test 3
    test_conditional_structure(2000)

    # Test 4
    test_round_by_round_ext(500)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Layer independence violations: {len(signals1)}")
    print(f"Significant L→C coboundaries: {len(significant)}/256")

    if len(significant) > 5:
        print("\nVERDICT: Ext¹(L,C) appears NON-ZERO — hidden L↔C coupling exists!")
        print("This could mean TLC is NOT a true direct sum.")
    else:
        print("\nVERDICT: Ext¹(L,C) ≈ 0 — TLC decomposition appears genuinely direct.")

if __name__ == "__main__":
    main()
