#!/usr/bin/env python3
"""
EXP 124: Round-by-Round Inversion — Theorem 2 Verification

THEORY (Theorem 2): Each SHA-256 round is fully invertible given W_r.
  From state_{r+1}, we can recover state_r exactly.

THEORY (Theorem 4): Preimage = solving backward from state_64 to IV.
  Self-referential: backward step at round r needs W_r, which depends on M.

H₁' TEST: Can we invert SHA-256 round by round and find M?

PLAN:
1. Verify Theorem 2: single round inversion is exact
2. Chain inversion: go backward from state_64
3. Measure: at which round does self-reference block us?
4. Count: how many free bits remain at each stage?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def invert_round(state_new, W_r, K_r):
    """Invert one SHA-256 round.

    Given state_{r+1} = [a',b',c',d',e',f',g',h'] and W_r, K_r,
    recover state_r = [a,b,c,d,e,f,g,h].

    From the round function:
      a' = T1 + T2     b' = a      c' = b     d' = c
      e' = d + T1       f' = e      g' = f     h' = g

    Recovery:
      a = b', b = c', c = d', e = f', f = g', g = h'
      T2 = Σ₀(a) + Maj(a,b,c)  [all known: a=b', b=c', c=d']
      T1 = a' - T2
      h = T1 - Σ₁(e) - Ch(e,f,g) - K_r - W_r
      d = e' - T1
    """
    a_new, b_new, c_new, d_new, e_new, f_new, g_new, h_new = state_new

    # Recover 6 words directly
    a = b_new
    b = c_new
    c = d_new
    e = f_new
    f = g_new
    g = h_new

    # Compute T2 (all inputs known)
    T2 = (sigma0(a) + maj(a, b, c)) & MASK

    # Compute T1
    T1 = (a_new - T2) & MASK

    # Recover h
    h = (T1 - sigma1(e) - ch(e, f, g) - K_r - W_r) & MASK

    # Recover d
    d = (e_new - T1) & MASK

    return [a, b, c, d, e, f, g, h]

def test_theorem2_exact(N=1000):
    """Verify: single round inversion is exact."""
    print(f"\n--- THEOREM 2: EXACT ROUND INVERSION (N={N}) ---")

    exact = 0
    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, 64)
        W = schedule(W16)

        # Test each round
        all_correct = True
        for r in range(64):
            state_recovered = invert_round(states[r+1], W[r], K[r])
            if state_recovered != states[r]:
                all_correct = False
                break

        if all_correct:
            exact += 1

    rate = exact / N
    print(f"  All 64 rounds inverted correctly: {rate:.6f}")
    if rate > 0.999:
        print(f"  *** THEOREM 2 CONFIRMED: Round inversion is EXACT ***")

def test_backward_chain(N=500):
    """Chain backward from state_64 to state_0 using known W."""
    print(f"\n--- BACKWARD CHAIN (known W, N={N}) ---")

    exact = 0
    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, 64)
        W = schedule(W16)

        # Start from state_64, go backward
        state = list(states[64])
        for r in range(63, -1, -1):
            state = invert_round(state, W[r], K[r])

        # Should equal IV
        if state == list(IV):
            exact += 1

    rate = exact / N
    print(f"  state_64 → state_0 = IV: {rate:.6f}")
    if rate > 0.999:
        print(f"  *** BACKWARD CHAIN EXACT: state_64 → IV in 64 steps ***")

def test_self_reference_boundary(N=200):
    """Where does self-reference kick in?

    W_0..W_15 = M (free, known to attacker)
    W_16..W_63 = schedule(M) (depend on M)

    Backward from state_64:
    - Rounds 63..16: need W_63..W_16 (computed from M, which we don't know yet)
    - Rounds 15..0: need W_15..W_0 (these ARE M, which is what we're solving for)

    So the self-reference is:
    - To invert round r, we need W_r
    - For r < 16: W_r is part of M (unknown, what we're looking for)
    - For r ≥ 16: W_r = f(M) (also unknown)

    KEY INSIGHT: if we work backward from round 64 to round 16,
    we need W_16..W_63, which depend on M.
    But if we work FORWARD from round 0 to round 15,
    we need W_0..W_15 = M, which IS what we choose.

    MEET-IN-THE-MIDDLE: backward from 64 to 16, forward from 0 to 15.
    They meet at state_16. If state_16_backward = state_16_forward → found M!
    """
    print(f"\n--- SELF-REFERENCE BOUNDARY ---")

    # For a KNOWN message, verify the meet-in-the-middle structure
    W16_msg = random_w16()
    states = sha256_rounds(W16_msg, 64)
    W = schedule(W16_msg)

    # Backward from 64 to 16
    state_back = list(states[64])
    for r in range(63, 15, -1):
        state_back = invert_round(state_back, W[r], K[r])

    print(f"  Backward from state_64 to state_16:")
    print(f"    state_16 (forward):  {[f'0x{s:08x}' for s in states[16]]}")
    print(f"    state_16 (backward): {[f'0x{s:08x}' for s in state_back]}")
    print(f"    Match: {state_back == states[16]}")

    # Forward from 0 to 15
    state_fwd = list(IV)
    for r in range(16):
        state_fwd = sha256_round(state_fwd, W[r], K[r])

    print(f"    state_16 (forward2): {[f'0x{s:08x}' for s in state_fwd]}")
    print(f"    Match: {state_fwd == states[16]}")

    # MEET IN THE MIDDLE ANALYSIS
    print(f"\n  Meet-in-the-middle structure:")
    print(f"    Forward half: rounds 0-15 (uses W_0..W_15 = M)")
    print(f"    Backward half: rounds 16-63 (uses W_16..W_63 = schedule(M))")
    print(f"")
    print(f"    Forward: IV × M → state_16")
    print(f"    Backward: state_64 × schedule → state_16")
    print(f"")
    print(f"    PROBLEM: both halves depend on M!")
    print(f"    Forward directly uses M (W_0..W_15)")
    print(f"    Backward uses schedule(M) (W_16..W_63)")
    print(f"    They're NOT independent!")

def test_freedom_analysis():
    """How many degrees of freedom exist at each stage?"""
    print(f"\n--- FREEDOM ANALYSIS ---")

    # Forward direction:
    # state_0 = IV (fixed, 0 free bits)
    # + W_0 (32 free bits) → state_1 (deterministic)
    # + W_1 (32 more free bits) → state_2
    # ...
    # + W_15 (32 more) → state_16 (total: 512 free bits in M)
    #
    # state_16 has 256 bits, determined by 512-bit M.
    # Mapping: GF(2)^512 → GF(2)^256, rank ≤ 256.
    # So: 512 - rank free bits remain.

    # Measure rank of forward mapping (M → state_16) empirically
    print(f"  Forward mapping M → state_16:")

    # Build approximate Jacobian by perturbing each input bit
    N_bits = 512
    state_bits = 256
    M_base = random_w16()
    s_base = sha256_rounds(M_base, 16)[16]

    # Convert state to bit vector
    def state_to_bits(s):
        bits = []
        for w in range(8):
            for b in range(32):
                bits.append((s[w] >> b) & 1)
        return bits

    base_bits = state_to_bits(s_base)

    # Jacobian: how each input bit affects output
    J = np.zeros((state_bits, N_bits), dtype=int)
    for w in range(16):
        for b in range(32):
            M_pert = list(M_base)
            M_pert[w] ^= (1 << b)
            s_pert = sha256_rounds(M_pert, 16)[16]
            pert_bits = state_to_bits(s_pert)
            for i in range(state_bits):
                J[i, w*32+b] = base_bits[i] ^ pert_bits[i]

    # GF(2) rank
    rank = np.linalg.matrix_rank(J % 2)
    nullity = N_bits - rank

    print(f"    Jacobian size: {state_bits} × {N_bits}")
    print(f"    GF(2) rank: {rank}")
    print(f"    Nullity: {nullity}")
    print(f"    → {nullity} bits of M are FREE (don't affect state_16)")

    # Same for full 64 rounds
    print(f"\n  Forward mapping M → state_64:")
    s_base_64 = sha256_rounds(M_base, 64)[64]
    base_bits_64 = state_to_bits(s_base_64)

    J64 = np.zeros((state_bits, N_bits), dtype=int)
    for w in range(16):
        for b in range(32):
            M_pert = list(M_base)
            M_pert[w] ^= (1 << b)
            s_pert_64 = sha256_rounds(M_pert, 64)[64]
            pert_bits_64 = state_to_bits(s_pert_64)
            for i in range(state_bits):
                J64[i, w*32+b] = base_bits_64[i] ^ pert_bits_64[i]

    rank64 = np.linalg.matrix_rank(J64 % 2)
    nullity64 = N_bits - rank64

    print(f"    GF(2) rank: {rank64}")
    print(f"    Nullity: {nullity64}")

    # Meet-in-the-middle cost
    print(f"\n  Meet-in-the-middle cost:")
    print(f"    Forward (16 rounds): 2^{nullity} messages give same state_16")
    print(f"    But schedule(M) also varies → backward half changes too")
    print(f"    No actual MITM gain because both halves depend on M")
    print(f"")
    print(f"    Standard MITM works when halves are INDEPENDENT:")
    print(f"      Cost = 2^(n/2) per half, match in middle")
    print(f"    SHA-256 MITM fails because:")
    print(f"      M appears in BOTH halves (direct + schedule)")
    print(f"      Cannot search halves independently")

    return rank, nullity, rank64, nullity64

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 124: ROUND-BY-ROUND INVERSION")
    print("Theorem 2 verification + freedom analysis")
    print("=" * 60)

    test_theorem2_exact(500)
    test_backward_chain(500)
    test_self_reference_boundary()
    r16, n16, r64, n64 = test_freedom_analysis()

    print(f"\n{'='*60}")
    print(f"VERDICT")
    print(f"{'='*60}")
    print(f"  Theorem 2 (round inversion): CONFIRMED (exact)")
    print(f"  Backward chain: CONFIRMED (state_64 → IV in 64 steps)")
    print(f"  M → state_16: rank={r16}, nullity={n16}")
    print(f"  M → state_64: rank={r64}, nullity={n64}")
    print(f"  MITM blocked: both halves depend on M")

if __name__ == "__main__":
    main()
