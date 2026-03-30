#!/usr/bin/env python3
"""
EXP 28: XOR-Collision + Carry Correction

INSIGHT: T_CARRY_IS_SUPPRESSOR means SHA-256 = XOR_SHA256 + carry_correction.
XOR_SHA256 is LINEAR over GF(2) → collisions are solvable.
Carry correction is a SMALL perturbation (7 bits at natural coupling).

METHOD:
1. Solve XOR-collision (linear algebra in GF(2))
2. Measure carry residual (how far is XOR-collision from real collision)
3. Iterative correction: adjust message to reduce carry residual

This is NOT standard Newton (which failed). It's OUR method:
- We know carry suppresses uniformly (T_SUPPRESSION_UNIFORM)
- We know it's in high bits 28-31 (exp26)
- We know only late rounds matter (T_LATE_ROUND_DOMINANCE)
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def xor_sha256_compress(W16, iv=None):
    """SHA-256 with ALL additions replaced by XOR. Fully linear over GF(2)."""
    if iv is None:
        iv = list(IV)

    def xor_schedule(W16):
        W = list(W16) + [0]*48
        for t in range(16, 64):
            W[t] = sig1(W[t-2]) ^ W[t-7] ^ sig0(W[t-15]) ^ W[t-16]
        return W

    def xor_round(state, W_r, K_r):
        a,b,c,d,e,f,g,h = state
        T1 = h ^ sigma1(e) ^ ch(e,f,g) ^ K_r ^ W_r
        T2 = sigma0(a) ^ maj(a,b,c)
        return [T1^T2, a, b, c, d^T1, e, f, g]

    W = xor_schedule(W16)
    state = list(iv)
    for r in range(64):
        state = xor_round(state, W[r], K[r])
    return [iv[i] ^ state[i] for i in range(8)]


def build_xor_differential_matrix(iv=None):
    """
    Build the GF(2) differential matrix of XOR-SHA-256.
    M[i][j] = 1 if flipping input bit j flips output bit i.
    512 input bits → 256 output bits.
    """
    if iv is None:
        iv = list(IV)

    # Base computation with zero message
    W_base = [0]*16
    H_base = xor_sha256_compress(W_base, iv)

    matrix = []
    for word in range(16):
        for bit in range(32):
            W_pert = [0]*16
            W_pert[word] = 1 << bit
            H_pert = xor_sha256_compress(W_pert, iv)

            row = []
            for w in range(8):
                d = H_base[w] ^ H_pert[w]
                for b in range(32):
                    row.append((d >> b) & 1)
            matrix.append(row)

    return np.array(matrix, dtype=np.int64)  # 512 × 256


def gf2_rank(M):
    A = M.copy() % 2
    m, n = A.shape
    rank = 0
    for col in range(n):
        pivot = -1
        for row in range(rank, m):
            if A[row,col] % 2 == 1:
                pivot = row; break
        if pivot == -1: continue
        A[[rank,pivot]] = A[[pivot,rank]]
        for row in range(m):
            if row != rank and A[row,col] % 2 == 1:
                A[row] = (A[row] + A[rank]) % 2
        rank += 1
    return rank


def gf2_nullspace(M):
    """Find nullspace of M over GF(2). Returns list of nullspace vectors."""
    A = M.copy() % 2
    m, n = A.shape
    # Augment with identity
    Aug = np.hstack([A, np.eye(m, dtype=np.int64)])

    rank = 0
    pivot_cols = []
    for col in range(n):
        pivot = -1
        for row in range(rank, m):
            if Aug[row,col] % 2 == 1:
                pivot = row; break
        if pivot == -1: continue
        Aug[[rank,pivot]] = Aug[[pivot,rank]]
        for row in range(m):
            if row != rank and Aug[row,col] % 2 == 1:
                Aug[row] = (Aug[row] + Aug[rank]) % 2
        pivot_cols.append(col)
        rank += 1

    # Free columns (not pivot)
    free_cols = [c for c in range(n) if c not in pivot_cols]

    # For each free column, construct nullspace vector
    null_vectors = []
    for fc in free_cols:
        vec = np.zeros(m, dtype=np.int64)
        vec_out = np.zeros(n, dtype=np.int64)
        # This is simplified — proper nullspace from RREF
        pass

    return rank, len(free_cols)


def test_xor_sha256_properties(N=500):
    """Analyze XOR-SHA-256: rank, collision structure."""
    print("\n--- TEST 1: XOR-SHA-256 PROPERTIES ---")

    M = build_xor_differential_matrix()
    rank = gf2_rank(M)
    nullity = 512 - rank

    print(f"XOR-SHA-256 differential matrix: {M.shape}")
    print(f"GF(2) rank: {rank}/256")
    print(f"Nullity: {nullity} (dimension of XOR-collision space)")

    if rank < 256:
        print(f"*** RANK DEFICIT: {256 - rank}! XOR-SHA-256 has non-trivial kernel! ***")
    else:
        print(f"Full rank: XOR-SHA-256 is surjective (every output reachable)")
        print(f"Collision space dimension: {nullity - 256} above minimum")

    # Verify: does XOR-SHA-256 actually produce XOR-collisions?
    print(f"\nSearching for XOR-collisions (random pairs)...")
    min_dh_xor = 256
    for _ in range(N):
        W1 = random_w16()
        W2 = random_w16()
        H1 = xor_sha256_compress(W1)
        H2 = xor_sha256_compress(W2)
        dh = sum(hw(H1[i]^H2[i]) for i in range(8))
        min_dh_xor = min(min_dh_xor, dh)

    print(f"Min δH(XOR-SHA-256) in {N} random pairs: {min_dh_xor}")


def test_carry_residual(N=2000):
    """
    For Wang pairs: measure how much real SHA-256 differs from XOR-SHA-256.
    The difference = carry residual = what we need to correct.
    """
    print("\n--- TEST 2: CARRY RESIDUAL (REAL - XOR) ---")

    residuals = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)

        # Real hashes
        H_n_real = sha256_compress(Wn)
        H_f_real = sha256_compress(Wf)
        dH_real = [H_n_real[i] ^ H_f_real[i] for i in range(8)]

        # XOR hashes
        H_n_xor = xor_sha256_compress(Wn)
        H_f_xor = xor_sha256_compress(Wf)
        dH_xor = [H_n_xor[i] ^ H_f_xor[i] for i in range(8)]

        # Carry residual: what carry CHANGES in the output difference
        residual = [dH_real[i] ^ dH_xor[i] for i in range(8)]
        hw_residual = sum(hw(r) for r in residual)
        hw_real = sum(hw(d) for d in dH_real)
        hw_xor = sum(hw(d) for d in dH_xor)

        residuals.append((hw_real, hw_xor, hw_residual))

    r_arr = np.array(residuals)
    print(f"E[HW(δH_real)]:     {r_arr[:,0].mean():.2f}")
    print(f"E[HW(δH_xor)]:      {r_arr[:,1].mean():.2f}")
    print(f"E[HW(residual)]:     {r_arr[:,2].mean():.2f}")
    print(f"Residual/total:      {r_arr[:,2].mean()/256*100:.1f}%")

    # Correlation: does small XOR-diff predict small real-diff?
    corr_xr = np.corrcoef(r_arr[:,0], r_arr[:,1])[0,1]
    print(f"corr(real_δH, xor_δH): {corr_xr:+.6f}")

    if corr_xr > 0.1:
        print("*** SIGNAL: XOR-collision quality predicts real collision quality! ***")

    # Distribution of residual
    print(f"\nResidual distribution:")
    for thresh in [64, 96, 112, 120, 128]:
        p = np.mean(r_arr[:,2] < thresh)
        print(f"  P(residual < {thresh}): {p:.4f}")


def test_xor_collision_lift(N=3000):
    """
    Find message pairs with small XOR-SHA-256 difference.
    Then measure their REAL SHA-256 difference.
    If XOR-close → real-close, we have a lift strategy.
    """
    print("\n--- TEST 3: XOR-COLLISION LIFT TO REAL ---")

    # Search for small XOR-difference pairs
    pairs = []
    for _ in range(N):
        W1 = random_w16()
        W2 = random_w16()

        H1_xor = xor_sha256_compress(W1)
        H2_xor = xor_sha256_compress(W2)
        dh_xor = sum(hw(H1_xor[i]^H2_xor[i]) for i in range(8))

        H1_real = sha256_compress(W1)
        H2_real = sha256_compress(W2)
        dh_real = sum(hw(H1_real[i]^H2_real[i]) for i in range(8))

        pairs.append((dh_xor, dh_real))

    xor_arr = np.array([p[0] for p in pairs])
    real_arr = np.array([p[1] for p in pairs])

    corr = np.corrcoef(xor_arr, real_arr)[0,1]
    print(f"corr(δH_xor, δH_real): {corr:+.6f}")

    # Split by XOR-quality
    for thresh in [100, 110, 120, 125]:
        good_xor = real_arr[xor_arr < thresh]
        if len(good_xor) > 0:
            print(f"  XOR δH<{thresh} (N={len(good_xor)}): real E[δH]={good_xor.mean():.2f}, min={good_xor.min()}")

    # Best XOR pair
    best_idx = np.argmin(xor_arr)
    print(f"\nBest XOR pair: δH_xor={xor_arr[best_idx]}, δH_real={real_arr[best_idx]}")


def test_iterative_correction(N=200):
    """
    Iterative carry correction:
    1. Start with Wang pair (structured differential)
    2. Compute XOR-prediction of δH
    3. Identify bits where carry flips the prediction
    4. Adjust DWs to compensate
    """
    print("\n--- TEST 4: ITERATIVE CARRY CORRECTION ---")

    results = []
    for trial in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)

        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        dh_start = sum(hw(H_n[i]^H_f[i]) for i in range(8))

        # Iterative correction
        current_DWs = list(DWs)
        current_dh = dh_start

        for iteration in range(50):
            # Compute XOR prediction
            Wf_curr = [(Wn[i]+current_DWs[i])&MASK for i in range(16)]
            H_xor_n = xor_sha256_compress(Wn)
            H_xor_f = xor_sha256_compress(Wf_curr)
            dH_xor = [H_xor_n[i] ^ H_xor_f[i] for i in range(8)]

            # Compute real
            H_real_f = sha256_compress(Wf_curr)
            dH_real = [H_n[i] ^ H_real_f[i] for i in range(8)]

            # Carry residual: bits where real ≠ XOR
            residual = [dH_real[i] ^ dH_xor[i] for i in range(8)]

            # Try to fix: flip a bit in DWs that reduces residual
            # Focus on high bits (28-31) of late words (our knowledge)
            best_improvement = 0
            best_word = -1
            best_bit = -1

            for w in range(8, 16):  # Late words
                for b in [28, 29, 30, 31, 24, 25, 26, 27]:  # High bits first
                    trial_DWs = list(current_DWs)
                    trial_DWs[w] ^= (1 << b)
                    Wf_trial = [(Wn[i]+trial_DWs[i])&MASK for i in range(16)]
                    H_trial = sha256_compress(Wf_trial)
                    dh_trial = sum(hw(H_n[i]^H_trial[i]) for i in range(8))
                    improvement = current_dh - dh_trial
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_word = w
                        best_bit = b

            if best_improvement > 0:
                current_DWs[best_word] ^= (1 << best_bit)
                current_dh -= best_improvement
            else:
                # Try random perturbation
                w = random.randint(0, 15)
                b = random.randint(0, 31)
                trial_DWs = list(current_DWs)
                trial_DWs[w] ^= (1 << b)
                Wf_trial = [(Wn[i]+trial_DWs[i])&MASK for i in range(16)]
                H_trial = sha256_compress(Wf_trial)
                dh_trial = sum(hw(H_n[i]^H_trial[i]) for i in range(8))
                if dh_trial < current_dh:
                    current_DWs = trial_DWs
                    current_dh = dh_trial

        results.append((dh_start, current_dh))

    starts = np.array([r[0] for r in results])
    finals = np.array([r[1] for r in results])

    print(f"Before correction: E[δH]={starts.mean():.2f}")
    print(f"After correction:  E[δH]={finals.mean():.2f}")
    print(f"Average gain: {starts.mean()-finals.mean():.2f} bits")
    print(f"Best: {min(finals)}")

    # Compare with pure random search (same budget)
    random_results = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, _, _ = wang_cascade(W0, W1)
        H_n = sha256_compress(Wn)
        best = sum(hw(H_n[i]^sha256_compress(Wf)[i]) for i in range(8))
        for _ in range(50*8*8):  # Same budget
            trial_DWs = list(DWs)
            trial_DWs[random.randint(0,15)] ^= (1 << random.randint(0,31))
            Wf_t = [(Wn[i]+trial_DWs[i])&MASK for i in range(16)]
            H_t = sha256_compress(Wf_t)
            dh = sum(hw(H_n[i]^H_t[i]) for i in range(8))
            best = min(best, dh)
        random_results.append(best)

    rr = np.array(random_results)
    print(f"\nRandom search (same budget): E[best]={rr.mean():.2f}, min={rr.min()}")
    print(f"Correction advantage: {rr.mean()-finals.mean():+.2f} bits")


def main():
    random.seed(42)
    print("="*60)
    print("EXP 28: XOR-COLLISION + CARRY CORRECTION")
    print("SHA-256 = XOR + carry_correction (our decomposition)")
    print("="*60)

    test_xor_sha256_properties(300)
    test_carry_residual(1500)
    test_xor_collision_lift(2000)
    test_iterative_correction(100)

    print("\n" + "="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
