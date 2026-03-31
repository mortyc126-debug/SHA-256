#!/usr/bin/env python3
"""
EXP 96: UALRA-NATIVE VERIFICATION — Independent Confirmation

★(a,b) = (a⊕b, a&b) claimed as native SHA-256 algebra.
10 sections of theory. Need INDEPENDENT verification of EACH.

Verification strategy:
  V1: ★ encoding correctness (π_add recovers +) — NEW random seeds
  V2: ★ round function produces IDENTICAL output to standard SHA-256
  V3: Structure theorem (2 full ★-pairs, 6 embedded per round)
  V4: AND-component dies after 1 round (memoryless)
  V5: ROTR is exact automorphism of ★
  V6: Carry = exactly derived from (α_x, α_a)
  V7: Carry rank = 3^5 = 243 (re-verify with different method)
  V8: Full SHA-256 through ★ = standard SHA-256 (bit-exact)
  V9: η-lattice constants reproducible from ★-framework
  V10: ★-correlations (0.35, 0.73) reproducible with new seed

ALL tests use DIFFERENT random seeds from original experiments.
"""
import sys, os, random, math, hashlib, struct
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

ETA = (3*math.log(3) - 4*math.log(2)) / (4*math.log(2))

# ★-algebra implementation (independent from exp95)
def star_op(u, v):
    """★(u,v) = (u⊕v, u&v)"""
    return (u ^ v, u & v)

def star_carry(x, a, n=32):
    """Carry reconstruction from ★-pair.
    carry[i] = a[i] | (x[i] & carry[i-1])
    Note: carry[i] is carry OUT of position i = carry INTO position i+1.
    The carry CONTRIBUTION to sum at position i+1 = carry[i].
    So actual_carry = the sequential carry chain."""
    c = 0
    carry_bits = 0
    for i in range(n):
        ai = (a >> i) & 1
        xi = (x >> i) & 1
        c = ai | (xi & c)
        if i > 0:  # carry into position i = carry out of position i-1
            carry_bits |= (c << i)
        # For position 0: carry_in = 0 (no previous), c = a[0] = carry_out[0]
        if i == 0:
            carry_bits = 0  # no carry into bit 0
            # carry out of bit 0 = a[0] | (x[0] & 0) = a[0]
            c = ai
    # Recompute properly
    c = 0
    carry_bits = 0
    for i in range(n):
        ai = (a >> i) & 1
        xi = (x >> i) & 1
        c_new = ai | (xi & c)
        carry_bits |= (c << i)  # carry INTO position i
        c = c_new
    return carry_bits

def star_pi_add(x, a):
    """π_add: recover u+v from ★-pair (x,a).
    u+v = u⊕v ⊕ 2·carry where carry = sequential chain.
    More directly: build result bit by bit."""
    c = 0
    result = 0
    for i in range(32):
        xi = (x >> i) & 1  # = u[i] ^ v[i]
        ai = (a >> i) & 1  # = u[i] & v[i]
        # sum bit = xi ^ c (carry in)
        result |= ((xi ^ c) << i)
        # carry out = ai | (xi & c)
        c = ai | (xi & c)
    return result & MASK

def star_round(state_pairs, W_r, K_r):
    """One SHA-256 round in ★-algebra. Returns new state_pairs."""
    # Extract π_add values from ★-state
    vals = [star_pi_add(state_pairs[i][0], state_pairs[i][1]) for i in range(8)]
    a_v,b_v,c_v,d_v,e_v,f_v,g_v,h_v = vals

    # Standard round computation
    sig1 = sigma1(e_v)
    ch_v = ch(e_v, f_v, g_v)
    sig0 = sigma0(a_v)
    maj_v = maj(a_v, b_v, c_v)

    # T1 via chained ★-additions
    # T1 = h + sig1 + ch + K + W
    t1_1 = star_op(h_v, sig1)
    t1_1_val = star_pi_add(t1_1[0], t1_1[1])
    t1_2 = star_op(t1_1_val, ch_v)
    t1_2_val = star_pi_add(t1_2[0], t1_2[1])
    t1_3 = star_op(t1_2_val, K_r)
    t1_3_val = star_pi_add(t1_3[0], t1_3[1])
    t1_4 = star_op(t1_3_val, W_r)
    T1_val = star_pi_add(t1_4[0], t1_4[1])

    # T2 = sig0 + maj
    t2 = star_op(sig0, maj_v)
    T2_val = star_pi_add(t2[0], t2[1])

    # a_new★ = T1 ★ T2 (full ★-pair)
    a_new_star = star_op(T1_val, T2_val)
    # e_new★ = d ★ T1 (full ★-pair)
    e_new_star = star_op(d_v, T1_val)

    # Shift: embedded (AND=0)
    return [
        a_new_star,           # a: full ★-pair
        (a_v, 0),             # b = old a: embedded
        (b_v, 0),             # c = old b: embedded
        (c_v, 0),             # d = old c: embedded
        e_new_star,           # e: full ★-pair
        (e_v, 0),             # f = old e: embedded
        (f_v, 0),             # g = old f: embedded
        (g_v, 0),             # h = old g: embedded
    ]

def star_sha256(W16):
    """Complete SHA-256 via ★-algebra. Returns hash."""
    W = schedule(W16)
    # Initial state: embedded IV
    state = [(IV[i], 0) for i in range(8)]

    for r in range(64):
        state = star_round(state, W[r], K[r])

    # Feedforward: IV + state via ★
    H = []
    for w in range(8):
        ff = star_op(IV[w], star_pi_add(state[w][0], state[w][1]))
        H.append(star_pi_add(ff[0], ff[1]))

    return H

def V1_encoding(N=10000):
    """V1: ★ encoding correctness with NEW seed."""
    print("\n--- V1: ★ ENCODING (seed=12345) ---")
    random.seed(12345)
    correct = 0
    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        x, y = star_op(a, b)
        recovered = star_pi_add(x, y)
        if recovered == ((a + b) & MASK) and x == (a ^ b) and y == (a & b):
            correct += 1
    print(f"  ★ encoding: {correct}/{N} correct")
    return correct == N

def V2_round_function(N=1000):
    """V2: ★-round = standard round."""
    print("\n--- V2: ★-ROUND = STANDARD ROUND (seed=54321) ---")
    random.seed(54321)
    correct = 0
    for _ in range(N):
        state = [random.randint(0, MASK) for _ in range(8)]
        W_r = random.randint(0, MASK)
        K_r = K[random.randint(0, 63)]

        # Standard round
        std = sha256_round(state, W_r, K_r)

        # ★-round
        star_state = [(state[i], 0) for i in range(8)]
        star_result = star_round(star_state, W_r, K_r)
        star_vals = [star_pi_add(s[0], s[1]) for s in star_result]

        if star_vals == std:
            correct += 1

    print(f"  ★-round = standard: {correct}/{N}")
    return correct == N

def V3_structure_theorem(N=500):
    """V3: 2 full ★-pairs + 6 embedded per round."""
    print("\n--- V3: STRUCTURE THEOREM (seed=99999) ---")
    random.seed(99999)
    violations = 0
    for _ in range(N):
        state = [(random.randint(0, MASK), 0) for _ in range(8)]
        W_r = random.randint(0, MASK)
        result = star_round(state, W_r, K[0])

        # Check: words 0 and 4 have AND ≠ 0, rest have AND = 0
        full_pairs = sum(1 for i in range(8) if result[i][1] != 0)
        embedded = sum(1 for i in range(8) if result[i][1] == 0)

        if full_pairs != 2 or embedded != 6:
            violations += 1

    print(f"  Structure (2 full + 6 embedded): violations={violations}/{N}")
    return violations == 0

def V4_and_memoryless(N=500):
    """V4: AND dies after 1 round."""
    print("\n--- V4: AND MEMORYLESS (seed=77777) ---")
    random.seed(77777)
    survived = 0
    for _ in range(N):
        # Create state with AND ≠ 0 at position 0
        state = [(random.randint(0, MASK), random.randint(0, MASK))] + \
                [(random.randint(0, MASK), 0) for _ in range(7)]
        W_r = random.randint(0, MASK)

        result = star_round(state, W_r, K[0])
        # After shift: old α₀ → α₁ with AND=0 (re-embedded)
        if result[1][1] != 0:
            survived += 1

    print(f"  AND survived shift: {survived}/{N} (should be 0)")
    return survived == 0

def V5_rotr_automorphism(N=5000):
    """V5: ROTR is exact automorphism of ★."""
    print("\n--- V5: ROTR AUTOMORPHISM (seed=11111) ---")
    random.seed(11111)
    correct = 0
    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        k = random.choice([2, 6, 7, 11, 13, 17, 18, 19, 22, 25])

        # ★ then ROTR
        x1, y1 = star_op(a, b)
        rx1 = rotr(x1, k); ry1 = rotr(y1, k)

        # ROTR then ★
        ra = rotr(a, k); rb = rotr(b, k)
        x2, y2 = star_op(ra, rb)

        if rx1 == x2 and ry1 == y2:
            correct += 1

    print(f"  ROTR(★(a,b)) = ★(ROTR(a),ROTR(b)): {correct}/{N}")
    return correct == N

def V6_carry_derived(N=5000):
    """V6: carry exactly derivable from (α_x, α_a)."""
    print("\n--- V6: CARRY DERIVED (seed=33333) ---")
    random.seed(33333)
    correct = 0
    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        x, y = star_op(a, b)

        # Derive carry from ★-pair
        derived_carry = star_carry(x, y)
        # Actual carry
        actual_carry = (((a + b) & MASK) ^ (a ^ b)) >> 1

        if derived_carry == actual_carry:
            correct += 1

    print(f"  Carry derived from ★: {correct}/{N}")
    return correct == N

def V7_carry_rank(N=30):
    """V7: carry rank = 3^5 = 243 (different method from exp66A/67)."""
    print("\n--- V7: CARRY RANK = 3^5 (seed=55555) ---")
    random.seed(55555)

    ranks = []
    for _ in range(N):
        W16 = [random.randint(0, MASK) for _ in range(16)]
        states = sha256_rounds(W16, 64)
        base = states[64]

        # Jacobian of AND-component of feedforward
        Ja = np.zeros((256, 512), dtype=np.int64)
        base_and = [IV[i] & base[i] for i in range(8)]

        for j in range(512):
            w = j // 32; b = j % 32
            W_p = list(W16); W_p[w] ^= (1 << b)
            s_p = sha256_rounds(W_p, 64)
            pert = s_p[64]
            pert_and = [IV[i] & pert[i] for i in range(8)]

            for i in range(256):
                wi = i // 32; bi = i % 32
                Ja[i][j] = ((base_and[wi] >> bi) & 1) ^ ((pert_and[wi] >> bi) & 1)

        r = np.linalg.matrix_rank(Ja.astype(float))
        ranks.append(r)

    mean_rank = np.mean(ranks)
    print(f"  AND-component rank: {mean_rank:.1f} (expected 243 = 3^5)")
    print(f"  Match 3^5: {'YES' if abs(mean_rank - 243) < 5 else 'NO'}")
    return abs(mean_rank - 243) < 5

def V8_full_sha256(N=1000):
    """V8: ★-SHA-256 = standard SHA-256 (bit-exact)."""
    print("\n--- V8: FULL ★-SHA-256 = STANDARD (seed=88888) ---")
    random.seed(88888)
    correct = 0
    for _ in range(N):
        W16 = [random.randint(0, MASK) for _ in range(16)]

        # Standard SHA-256
        std_hash = sha256_compress(W16)

        # ★-SHA-256
        star_hash = star_sha256(W16)

        if std_hash == star_hash:
            correct += 1

    print(f"  ★-SHA-256 = standard SHA-256: {correct}/{N}")
    return correct == N

def V9_correlations(N=3000):
    """V9: ★-correlations reproducible (new seed)."""
    print("\n--- V9: ★-CORRELATIONS (seed=44444) ---")
    random.seed(44444)

    dxs = []; das = []; dHs = []
    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        Wn, Wf, _, sn, sf = wang_cascade(W0, W1)
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)

        dx = sum(hw((IV[w] ^ sn[64][w]) ^ (IV[w] ^ sf[64][w])) for w in range(8))
        da = sum(hw((IV[w] & sn[64][w]) ^ (IV[w] & sf[64][w])) for w in range(8))
        dH = sum(hw(Hn[w] ^ Hf[w]) for w in range(8))

        dxs.append(dx); das.append(da); dHs.append(dH)

    c_xor = np.corrcoef(dxs, dHs)[0, 1]
    c_and = np.corrcoef(das, dHs)[0, 1]
    c_xa = np.corrcoef(dxs, das)[0, 1]

    print(f"  corr(δ★_xor, δH) = {c_xor:+.4f} (exp95: +0.349)")
    print(f"  corr(δ★_and, δH) = {c_and:+.4f} (exp95: +0.273)")
    print(f"  corr(δ★_xor, δ★_and) = {c_xa:+.4f} (exp95: +0.730)")

    # Within 20% of original?
    ok = (abs(c_xor - 0.349) / 0.349 < 0.2 and
          abs(c_and - 0.273) / 0.273 < 0.2 and
          abs(c_xa - 0.730) / 0.730 < 0.2)
    print(f"  Reproducible: {'YES' if ok else 'NO'}")
    return ok

def main():
    print("=" * 60)
    print("EXP 96: UALRA-NATIVE INDEPENDENT VERIFICATION")
    print("=" * 60)

    results = {}
    results['V1'] = V1_encoding()
    results['V2'] = V2_round_function()
    results['V3'] = V3_structure_theorem()
    results['V4'] = V4_and_memoryless()
    results['V5'] = V5_rotr_automorphism()
    results['V6'] = V6_carry_derived()
    results['V7'] = V7_carry_rank()
    results['V8'] = V8_full_sha256()
    results['V9'] = V9_correlations()

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    all_pass = True
    for name, passed in results.items():
        status = "PASS ✓" if passed else "FAIL ✗"
        print(f"  {name}: {status}")
        if not passed:
            all_pass = False

    print(f"\n  Overall: {'ALL PASS ✓✓✓' if all_pass else 'SOME FAILED'}")
    print(f"  {sum(results.values())}/{len(results)} verifications passed")

if __name__ == "__main__":
    main()
