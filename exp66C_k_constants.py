#!/usr/bin/env python3
"""
EXP 66C: K-Constant Specific Structure

Gap C: ALL 65 experiments were GENERIC (independent of specific K values).
SHA-256 uses K[r] = floor(2^32 × frac(∛p_r)) for primes p_r.

These K values have SPECIFIC bit patterns. If SHA-256's security
depends on K being "generic" → specific K might be weaker.

Tests:
1. Bit structure of actual K[r] vs random K
2. SHA-256 with RANDOM K vs actual K: is actual K weaker?
3. Specific K relationships (K[r] ⊕ K[r+1], etc.)
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def test_k_bit_structure():
    """Analyze bit structure of actual K constants."""
    print("\n--- K-CONSTANT BIT STRUCTURE ---")

    # HW distribution
    k_hws = [hw(K[r]) for r in range(64)]
    print(f"HW(K[r]): mean={np.mean(k_hws):.2f}, std={np.std(k_hws):.2f}, "
          f"min={min(k_hws)}, max={max(k_hws)}")
    print(f"Expected random: mean=16, std≈2.83")

    # Consecutive K differences
    k_diffs = [hw(K[r] ^ K[r+1]) for r in range(63)]
    print(f"\nHW(K[r]⊕K[r+1]): mean={np.mean(k_diffs):.2f} (expected 16)")

    # K[r] + K[r+1] mod 2^32 structure
    k_sums = [((K[r] + K[r+1]) & MASK) for r in range(63)]
    k_sum_hws = [hw(s) for s in k_sums]
    print(f"HW(K[r]+K[r+1]): mean={np.mean(k_sum_hws):.2f}")

    # Are any K[r] related? (K[i] = f(K[j])?)
    print(f"\nK-constant relationships:")
    for r1 in range(64):
        for r2 in range(r1+1, 64):
            d = hw(K[r1] ^ K[r2])
            if d < 8:  # Very close
                print(f"  K[{r1}]⊕K[{r2}]: HW={d}")

    # GF(2) rank of K matrix (K as 64×32 bit matrix)
    K_matrix = np.zeros((64, 32), dtype=np.int64)
    for r in range(64):
        for b in range(32):
            K_matrix[r][b] = (K[r] >> b) & 1
    rank = np.linalg.matrix_rank(K_matrix.astype(float))
    print(f"\nGF(2) rank of K-matrix (64×32): {rank}/32")

def test_random_k_comparison(N=1000):
    """SHA-256 with actual K vs random K: collision difficulty."""
    print(f"\n--- ACTUAL K vs RANDOM K ---")

    def sha_with_k(W16, k_constants):
        """SHA-256 rounds with custom K constants."""
        iv = list(IV); W = schedule(W16)
        state = list(iv)
        for r in range(64):
            a,b,c,d,e,f,g,h = state
            T1 = (h+sigma1(e)+ch(e,f,g)+k_constants[r]+W[r])&MASK
            T2 = (sigma0(a)+maj(a,b,c))&MASK
            state = [(T1+T2)&MASK,a,b,c,(d+T1)&MASK,e,f,g]
        return [(iv[i]+state[i])&MASK for i in range(8)]

    # Actual K
    actual_dHs = []
    for _ in range(N):
        W1=random_w16(); W2=random_w16()
        H1=sha_with_k(W1, K); H2=sha_with_k(W2, K)
        actual_dHs.append(sum(hw(H1[i]^H2[i]) for i in range(8)))

    # Random K
    K_rand = [random.randint(0, MASK) for _ in range(64)]
    random_dHs = []
    for _ in range(N):
        W1=random_w16(); W2=random_w16()
        H1=sha_with_k(W1, K_rand); H2=sha_with_k(W2, K_rand)
        random_dHs.append(sum(hw(H1[i]^H2[i]) for i in range(8)))

    # All-zero K
    K_zero = [0]*64
    zero_dHs = []
    for _ in range(N):
        W1=random_w16(); W2=random_w16()
        H1=sha_with_k(W1, K_zero); H2=sha_with_k(W2, K_zero)
        zero_dHs.append(sum(hw(H1[i]^H2[i]) for i in range(8)))

    # All-one K
    K_ones = [MASK]*64
    ones_dHs = []
    for _ in range(N):
        W1=random_w16(); W2=random_w16()
        H1=sha_with_k(W1, K_ones); H2=sha_with_k(W2, K_ones)
        ones_dHs.append(sum(hw(H1[i]^H2[i]) for i in range(8)))

    aa=np.array(actual_dHs); ra=np.array(random_dHs)
    za=np.array(zero_dHs); oa=np.array(ones_dHs)

    print(f"Actual K:  E[δH]={aa.mean():.2f}, std={aa.std():.2f}")
    print(f"Random K:  E[δH]={ra.mean():.2f}, std={ra.std():.2f}")
    print(f"Zero K:    E[δH]={za.mean():.2f}, std={za.std():.2f}")
    print(f"All-1s K:  E[δH]={oa.mean():.2f}, std={oa.std():.2f}")

    if aa.mean() < ra.mean() - 1:
        print(f"*** ACTUAL K is WEAKER than random! ***")

def test_k_influence_per_round(N=500):
    """Which K[r] has most influence on output?"""
    print(f"\n--- K-INFLUENCE PER ROUND ---")

    # For each round: replace K[r] with 0 and measure δH change
    base_dHs = []
    W_pairs = [(random_w16(), random_w16()) for _ in range(N)]

    for W1, W2 in W_pairs:
        H1=sha256_compress(W1); H2=sha256_compress(W2)
        base_dHs.append(sum(hw(H1[i]^H2[i]) for i in range(8)))

    def sha_modified_k(W16, r_modify, k_new):
        iv=list(IV); W=schedule(W16); state=list(iv)
        for r in range(64):
            a,b,c,d,e,f,g,h=state
            k_val = k_new if r == r_modify else K[r]
            T1=(h+sigma1(e)+ch(e,f,g)+k_val+W[r])&MASK
            T2=(sigma0(a)+maj(a,b,c))&MASK
            state=[(T1+T2)&MASK,a,b,c,(d+T1)&MASK,e,f,g]
        return [(iv[i]+state[i])&MASK for i in range(8)]

    print(f"{'Round':>5} | {'E[dist to baseline]':>20} | Influence")
    print("-"*40)
    for r_test in [0, 1, 8, 16, 32, 48, 60, 63]:
        dists = []
        for W1, W2 in W_pairs[:100]:
            H1_mod = sha_modified_k(W1, r_test, 0)
            H1_base = sha256_compress(W1)
            d = sum(hw(H1_mod[i]^H1_base[i]) for i in range(8))
            dists.append(d)

        mean_d = np.mean(dists)
        print(f"{r_test:>5} | {mean_d:>20.2f} | {'HIGH' if mean_d > 120 else 'low'}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 66C: K-CONSTANT SPECIFIC STRUCTURE")
    print("="*60)
    test_k_bit_structure()
    test_random_k_comparison(800)
    test_k_influence_per_round(200)

if __name__ == "__main__":
    main()
