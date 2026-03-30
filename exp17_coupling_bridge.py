#!/usr/bin/env python3
"""
EXPERIMENT 17: Coupling Bridge — Connecting Dark Channel to Output

Carry coupling κ has τ≈8-12 (exp16B) but corr(κ,δH)<0.05.
The channel is alive but disconnected from output.

STRATEGY: Chain our own instruments:
A. Coupling Pipe: does Pipe Conservation carry κ forward?
   κ(a+e)[r] = κ(d+h)[r+3]? If yes → τ_coupling_pipe = ∞
B. Bridge amplification: κ → raw[63] → H[7]
   Methodology: corr(raw63, H7) = -0.097. Can coupling USE this?
C. Selective pairing: choose Wang pairs where coupling chain is strongest
D. Multi-round coupling accumulator: Σ_r κ(r) weighted by bridge strength
"""

import sys, os, random, math
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def carry_vector_full(a, b, n=32):
    """Full carry vector for a+b."""
    carries = []
    c = 0
    for i in range(n):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        s = ai + bi + c
        c = 1 if s >= 2 else 0
        carries.append(c)
    return carries


def compute_coupling_chain(Wn, Wf, num_rounds=64):
    """
    Compute the full coupling chain:
    - κ_eT1[r]: coupling of d+T1 (e-branch main addition)
    - κ_aT2[r]: coupling of T1+T2 (a-branch main addition)
    - κ_pipe[r]: coupling of (a+e) (pipe value)
    - raw_n[r], raw_f[r]: raw T1 values (for bridge to output)
    """
    states_n = sha256_rounds(Wn, num_rounds)
    states_f = sha256_rounds(Wf, num_rounds)
    Wn_exp = schedule(Wn)
    Wf_exp = schedule(Wf)

    chain = {
        'kappa_eT1': [],     # κ for d+T1 → e_new
        'kappa_aT2': [],     # κ for T1+T2 → a_new
        'kappa_pipe': [],    # κ for a+e (pipe value)
        'pipe_n': [],        # (a+e) for normal
        'pipe_f': [],        # (a+e) for faulty
        'raw_n': [],         # raw T1 values normal
        'raw_f': [],         # raw T1 values faulty
        'hw_kappa_eT1': [],
        'hw_kappa_pipe': [],
    }

    for r in range(num_rounds):
        an, bn, cn, dn, en, fn, gn, hn = states_n[r]
        af, bf, cf, df, ef, ff, gf, hf = states_f[r]

        # T1 computation
        raw_n = hn + sigma1(en) + ch(en, fn, gn) + K[r] + Wn_exp[r]
        raw_f = hf + sigma1(ef) + ch(ef, ff, gf) + K[r] + Wf_exp[r]
        T1n = raw_n & MASK
        T1f = raw_f & MASK

        T2n = (sigma0(an) + maj(an, bn, cn)) & MASK
        T2f = (sigma0(af) + maj(af, bf, cf)) & MASK

        # κ for d+T1 → e_new
        cv_eT1_n = carry_vector_full(dn, T1n)
        cv_eT1_f = carry_vector_full(df, T1f)
        kappa_eT1 = [a ^ b for a, b in zip(cv_eT1_n, cv_eT1_f)]

        # κ for T1+T2 → a_new
        cv_aT2_n = carry_vector_full(T1n, T2n)
        cv_aT2_f = carry_vector_full(T1f, T2f)
        kappa_aT2 = [a ^ b for a, b in zip(cv_aT2_n, cv_aT2_f)]

        # Pipe value: a+e
        pipe_n = (an + en) & MASK
        pipe_f = (af + ef) & MASK

        # κ of pipe: carry(a,e) difference
        cv_pipe_n = carry_vector_full(an, en)
        cv_pipe_f = carry_vector_full(af, ef)
        kappa_pipe = [a ^ b for a, b in zip(cv_pipe_n, cv_pipe_f)]

        chain['kappa_eT1'].append(kappa_eT1)
        chain['kappa_aT2'].append(kappa_aT2)
        chain['kappa_pipe'].append(kappa_pipe)
        chain['pipe_n'].append(pipe_n)
        chain['pipe_f'].append(pipe_f)
        chain['raw_n'].append(raw_n)
        chain['raw_f'].append(raw_f)
        chain['hw_kappa_eT1'].append(sum(kappa_eT1))
        chain['hw_kappa_pipe'].append(sum(kappa_pipe))

    return chain


def test_coupling_pipe(N=1500):
    """
    TEST A: Does Pipe Conservation carry coupling forward?

    Pipe: (a+e)[r] = (d+h)[r+3]
    Question: κ_pipe[r] ≈ κ_pipe[r+3]?

    If yes → coupling has a TRANSPORT mechanism with τ=∞
    """
    print("\n--- TEST A: COUPLING PIPE CONSERVATION ---")

    pipe_corrs = {lag: [] for lag in [1, 2, 3, 4, 5, 6, 8, 12]}

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        chain = compute_coupling_chain(Wn, Wf)

        hw_pipe = chain['hw_kappa_pipe']

        for lag in pipe_corrs:
            for r in range(20, 64 - lag):  # Past barrier only
                pipe_corrs[lag].append((hw_pipe[r], hw_pipe[r + lag]))

    print(f"{'Lag':>4} | {'corr(κ_pipe)':>13} | {'Expected (lag=3 pipe)':>22} | Signal")
    print("-" * 65)

    for lag in sorted(pipe_corrs.keys()):
        pairs = pipe_corrs[lag]
        x = np.array([p[0] for p in pairs])
        y = np.array([p[1] for p in pairs])
        c = np.corrcoef(x, y)[0, 1]
        expected = "PIPE MATCH" if lag == 3 else ""
        marker = " ***" if (lag == 3 and c > 0.1) or c > 0.3 else ""
        print(f"{lag:>4} | {c:>13.6f} | {expected:>22} | {marker}")

    # Direct test: κ_pipe[r] vs κ_pipe[r+3] bit-by-bit
    exact_matches = []
    for _ in range(500):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        chain = compute_coupling_chain(Wn, Wf)

        for r in range(20, 60):
            kp_r = chain['kappa_pipe'][r]
            kp_r3 = chain['kappa_pipe'][r + 3]
            match = sum(1 for a, b in zip(kp_r, kp_r3) if a == b)
            exact_matches.append(match / 32)

    avg_match = np.mean(exact_matches)
    print(f"\nBit-by-bit match κ_pipe[r] vs κ_pipe[r+3]: {avg_match:.6f}")
    print(f"Expected (random): 0.500000")
    print(f"Expected (exact pipe): 1.000000")

    if avg_match > 0.55:
        print("*** SIGNAL: Coupling pipe partially conserved! ***")

    return avg_match


def test_bridge_amplification(N=2000):
    """
    TEST B: Can carry coupling reach the output through the e-branch bridge?

    Chain: κ_eT1[r] → persists → κ_eT1[63] → raw[63] → H[7]

    Measure: corr(κ_accumulated, H[7] specific bits)
    """
    print("\n--- TEST B: BRIDGE AMPLIFICATION ---")

    data = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        chain = compute_coupling_chain(Wn, Wf)

        # Accumulated coupling (weighted by recency — later rounds matter more)
        kappa_acc = 0
        for r in range(64):
            weight = 1.0  # Uniform weight
            kappa_acc += chain['hw_kappa_eT1'][r] * weight

        # Late-round coupling (rounds 56-63 — closest to output)
        kappa_late = sum(chain['hw_kappa_eT1'][r] for r in range(56, 64))

        # κ at round 63 specifically
        kappa_63 = chain['hw_kappa_eT1'][63]

        # Raw value difference at round 63
        raw_diff_63 = chain['raw_n'][63] - chain['raw_f'][63]

        # Carry of last round
        carry_63_n = 1 if chain['raw_n'][63] >= (1 << 32) else 0
        carry_63_f = 1 if chain['raw_f'][63] >= (1 << 32) else 0
        carry_63_diff = carry_63_n ^ carry_63_f

        # Output H[7] difference (bits 30, 31 — from methodology Ch invariant)
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        dH7 = H_n[7] ^ H_f[7]
        dH7_b30 = (dH7 >> 30) & 1
        dH7_b31 = (dH7 >> 31) & 1
        dH7_hw = hw(dH7)

        dH_total = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))

        data.append({
            'kappa_acc': kappa_acc,
            'kappa_late': kappa_late,
            'kappa_63': kappa_63,
            'carry_63_diff': carry_63_diff,
            'dH7_b30': dH7_b30,
            'dH7_b31': dH7_b31,
            'dH7_hw': dH7_hw,
            'dH_total': dH_total,
        })

    # Correlations
    threshold = 3 / np.sqrt(N)

    metrics = ['kappa_acc', 'kappa_late', 'kappa_63', 'carry_63_diff']
    targets = ['dH7_b30', 'dH7_b31', 'dH7_hw', 'dH_total']

    print(f"{'Metric':>15} | {'dH7_b30':>8} | {'dH7_b31':>8} | {'dH7_hw':>8} | {'dH_total':>8}")
    print("-" * 60)

    for metric in metrics:
        m_arr = np.array([d[metric] for d in data], dtype=np.float64)
        corrs = []
        for target in targets:
            t_arr = np.array([d[target] for d in data], dtype=np.float64)
            if m_arr.std() > 0 and t_arr.std() > 0:
                c = np.corrcoef(m_arr, t_arr)[0, 1]
            else:
                c = 0
            corrs.append(c)

        sig = any(abs(c) > threshold for c in corrs)
        marker = " ***" if sig else ""
        print(f"{metric:>15} | {corrs[0]:>+8.4f} | {corrs[1]:>+8.4f} | "
              f"{corrs[2]:>+8.4f} | {corrs[3]:>+8.4f}{marker}")

    print(f"Threshold: {threshold:.4f}")


def test_selective_pairing(N=5000):
    """
    TEST C: Select Wang pairs where coupling chain is strongest.
    Measure if selected pairs have lower δH.
    """
    print("\n--- TEST C: SELECTIVE PAIRING ---")

    pairs = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        chain = compute_coupling_chain(Wn, Wf, 20)  # Only 20 rounds for speed

        # Coupling strength: low κ in rounds 17-19 (just past barrier)
        kappa_17_19 = sum(chain['hw_kappa_eT1'][r] for r in range(16, min(20, len(chain['hw_kappa_eT1']))))

        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        dH = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))

        pairs.append((kappa_17_19, dH, W0, W1))

    k_arr = np.array([p[0] for p in pairs])
    dh_arr = np.array([p[1] for p in pairs])

    # Split into quartiles by coupling strength
    q25 = np.percentile(k_arr, 25)
    q75 = np.percentile(k_arr, 75)

    strong_coupling = dh_arr[k_arr <= q25]  # Low κ = strong coupling
    weak_coupling = dh_arr[k_arr >= q75]    # High κ = weak coupling

    print(f"Strong coupling (κ≤{q25:.0f}): E[δH]={strong_coupling.mean():.4f}, N={len(strong_coupling)}")
    print(f"Weak coupling (κ≥{q75:.0f}):   E[δH]={weak_coupling.mean():.4f}, N={len(weak_coupling)}")
    print(f"Difference: {strong_coupling.mean() - weak_coupling.mean():+.4f}")

    corr = np.corrcoef(k_arr, dh_arr)[0, 1]
    print(f"corr(κ_17-19, δH): {corr:+.6f}")

    # Best 1% by coupling strength
    top1_threshold = np.percentile(k_arr, 1)
    top1 = dh_arr[k_arr <= top1_threshold]
    print(f"\nTop 1% coupling: E[δH]={top1.mean():.4f}, min={top1.min()}, N={len(top1)}")
    print(f"Overall:         E[δH]={dh_arr.mean():.4f}, min={dh_arr.min()}")


def test_coupling_accumulator(N=2000):
    """
    TEST D: Multi-round coupling accumulator.

    Define: Φ = Σ_r w(r) · κ(r)  where w(r) is a weight function.

    Optimize w(r) to maximize corr(Φ, δH).
    If optimal Φ has significant correlation → coupling IS connected to output,
    just through a specific (possibly nonlinear) combination.
    """
    print("\n--- TEST D: COUPLING ACCUMULATOR OPTIMIZATION ---")

    # Collect full coupling data
    kappas = []
    dHs = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        chain = compute_coupling_chain(Wn, Wf)

        kappas.append(chain['hw_kappa_eT1'])

        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        dH = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))
        dHs.append(dH)

    K_matrix = np.array(kappas)  # N × 64
    dH_arr = np.array(dHs)

    # Per-round correlation
    print(f"Per-round corr(κ_r, δH):")
    per_round_corr = []
    for r in range(64):
        c = np.corrcoef(K_matrix[:, r], dH_arr)[0, 1]
        per_round_corr.append(c)

    # Print notable rounds
    prc = np.array(per_round_corr)
    top_rounds = np.argsort(np.abs(prc))[::-1][:10]
    for r in top_rounds:
        print(f"  Round {r:>2}: corr = {prc[r]:+.6f}")

    # Optimal linear combination: w = (K^T K)^{-1} K^T dH
    # This gives the weight vector that maximizes corr(K·w, dH)
    try:
        KtK = K_matrix.T @ K_matrix
        KtdH = K_matrix.T @ dH_arr
        w_optimal = np.linalg.solve(KtK + 0.01 * np.eye(64), KtdH)

        Phi_optimal = K_matrix @ w_optimal
        corr_optimal = np.corrcoef(Phi_optimal, dH_arr)[0, 1]

        print(f"\nOptimal accumulator:")
        print(f"  corr(Φ_opt, δH) = {corr_optimal:+.6f}")
        print(f"  Top weight rounds: {np.argsort(np.abs(w_optimal))[::-1][:5]}")
        print(f"  Weight range: [{w_optimal.min():.4f}, {w_optimal.max():.4f}]")

        # Is this significant? Compare with random target
        random_corrs = []
        for _ in range(100):
            dH_rand = np.random.permutation(dH_arr)
            w_rand = np.linalg.solve(KtK + 0.01 * np.eye(64),
                                     K_matrix.T @ dH_rand)
            Phi_rand = K_matrix @ w_rand
            random_corrs.append(np.corrcoef(Phi_rand, dH_rand)[0, 1])

        rc = np.array(random_corrs)
        print(f"  Random baseline: {rc.mean():.6f} ± {rc.std():.6f}")
        print(f"  Z-score: {(corr_optimal - rc.mean()) / rc.std():.2f}")

        if corr_optimal > rc.mean() + 3 * rc.std():
            print("  *** SIGNAL: Accumulator significantly above random! ***")

    except np.linalg.LinAlgError:
        print("  Matrix solve failed")

    # Nonlinear: try κ² and κ·κ_{r+1} terms
    print(f"\nNonlinear coupling features:")
    # κ squared
    K_sq = K_matrix**2
    for r in [16, 17, 32, 63]:
        c = np.corrcoef(K_sq[:, r], dH_arr)[0, 1]
        if abs(c) > 0.05:
            print(f"  corr(κ²_{r}, δH) = {c:+.6f} ***")

    # Product κ_r · κ_{r+1}
    for r in [16, 17, 32, 48]:
        if r + 1 < 64:
            prod = K_matrix[:, r] * K_matrix[:, r + 1]
            c = np.corrcoef(prod, dH_arr)[0, 1]
            if abs(c) > 0.05:
                print(f"  corr(κ_{r}·κ_{r+1}, δH) = {c:+.6f} ***")


def main():
    random.seed(42)

    print("=" * 60)
    print("EXPERIMENT 17: COUPLING BRIDGE")
    print("Connecting the dark channel to output")
    print("=" * 60)

    pipe_match = test_coupling_pipe(1000)
    test_bridge_amplification(1500)
    test_selective_pairing(3000)
    test_coupling_accumulator(1500)

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    print(f"Pipe conservation of coupling: {pipe_match:.4f} (0.5=random, 1.0=exact)")

if __name__ == "__main__":
    main()
