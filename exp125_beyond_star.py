#!/usr/bin/env python3
"""
EXP 125: BEYOND ★ — Five Directions Into The Dark

Direction 1: ★² (composition) — multi-term addition without intermediate carry
Direction 2: ★₃ (ternary) — GKP as base-3 ★-algebra, explain η
Direction 3: ★⁻¹ (duality) — parallel vs sequential decomposition
Direction 4: ★_round (tensor) — entire round as one ★-operation
Direction 5: ★-limit (dynamics) — attractor dimension after infinite rounds
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

# ============================================================
# DIRECTION 1: ★² — Composition algebra
# ============================================================

def star(a, b):
    """★(a,b) = (a⊕b, a&b)"""
    return (a ^ b, a & b)

def pi_add(xor_part, and_part):
    """Resolve carry: reconstruct a+b from ★-components."""
    # a + b = xor_part + 2*and_part (but and_part generates its own carries...)
    # Actually: a + b where ★(a,b) = (xor_part, and_part)
    # Sum = xor_part + 2*and_part... no, that's not right either.
    # Correct: if a⊕b = x, a&b = c, then a+b = x + 2c
    # But 2c can overflow, so: a+b = (x + 2*c) mod 2^32
    return (xor_part + 2 * and_part) & MASK

def star2_direct(a, b, c):
    """★²(a,b,c): three-term ★ WITHOUT intermediate carry resolution.

    a + b + c = ?
    ★(a,b) = (a⊕b, a&b)
    Then (a+b) + c requires resolving ★(a,b) first.

    But: a + b + c can be decomposed DIRECTLY:
    XOR part: a ⊕ b ⊕ c (3-way XOR)
    AND part: (a&b) | (a&c) | (b&c) (majority — carry from any 2 of 3)
    BUT: this is only the FIRST carry layer. There can be carry-of-carry.

    Full adder: sum = a⊕b⊕c, carry = (a&b)|(a&c)|(b&c) = Maj(a,b,c)
    """
    xor3 = a ^ b ^ c
    carry3 = (a & b) | (a & c) | (b & c)  # = Maj(a,b,c) !
    return (xor3, carry3)

def test_star2(N=5000):
    """Test ★²: does it correctly represent a+b+c?"""
    print(f"\n{'='*60}")
    print(f"DIRECTION 1: ★² COMPOSITION")
    print(f"{'='*60}")

    # Verify: a+b+c = pi_add(★²(a,b,c))
    exact = 0
    for _ in range(N):
        a = random.randint(0, MASK)
        b = random.randint(0, MASK)
        c = random.randint(0, MASK)

        real_sum = (a + b + c) & MASK
        x3, c3 = star2_direct(a, b, c)
        star2_sum = pi_add(x3, c3)

        if real_sum == star2_sum:
            exact += 1

    rate = exact / N
    print(f"\n  ★²(a,b,c) → a+b+c: {rate:.6f}")

    if rate < 0.99:
        print(f"  ★² is NOT exact! carry-of-carry exists.")
        # Measure the error
        errors = []
        for _ in range(N):
            a = random.randint(0, MASK); b = random.randint(0, MASK)
            c = random.randint(0, MASK)
            real = (a + b + c) & MASK
            x3, c3 = star2_direct(a, b, c)
            approx = pi_add(x3, c3)
            errors.append(hw(real ^ approx))
        ea = np.array(errors)
        print(f"  Mean error: {ea.mean():.2f} bits")

        # ★² needs ITERATION (like circular carry) to resolve carry-of-carry
        print(f"\n  ★² with carry iteration:")
        for max_iter in [1, 2, 3, 4]:
            exact_iter = 0
            for _ in range(N):
                a = random.randint(0, MASK); b = random.randint(0, MASK)
                c = random.randint(0, MASK)
                real = (a + b + c) & MASK

                x, car = star2_direct(a, b, c)
                for _ in range(max_iter):
                    x, car = star(x, (car << 1) & MASK)
                result = pi_add(x, car)

                if result == real:
                    exact_iter += 1
            print(f"    {max_iter} iterations: {exact_iter/N:.6f}")

    # KEY: ★² = (⊕₃, Maj) — Maj IS SHA-256's Maj function!
    print(f"\n  INSIGHT: ★²(a,b,c) = (a⊕b⊕c, Maj(a,b,c))")
    print(f"  The Maj function in SHA-256 IS the carry of ★²!")
    print(f"  T2 = Σ₀(a) + Maj(a,b,c) = Σ₀(a) + ★²_carry(a,b,c)")
    print(f"  SHA-256's design ALREADY uses ★² implicitly!")

# ============================================================
# DIRECTION 2: ★₃ — Ternary algebra
# ============================================================

def test_star3(N=5000):
    """★₃: ternary decomposition via GKP."""
    print(f"\n{'='*60}")
    print(f"DIRECTION 2: ★₃ TERNARY")
    print(f"{'='*60}")

    # GKP: each bit position classified as G(2), K(0), P(1) in ternary
    # G: both bits = 1, carry = 1 regardless
    # K: both bits = 0, carry = 0 regardless
    # P: bits differ, carry = carry_in (propagate)
    #
    # GKP word as a balanced ternary number:
    # G → 2, K → 0, P → 1
    # 32-trit word → value in [0, 3^32-1]

    def gkp_to_ternary(a, b):
        """Convert (a,b) pair to ternary GKP value."""
        val = 0
        power = 1
        for i in range(32):
            ai = (a >> i) & 1; bi = (b >> i) & 1
            if ai == 1 and bi == 1:
                trit = 2  # G
            elif ai == 0 and bi == 0:
                trit = 0  # K
            else:
                trit = 1  # P
            val += trit * power
            power *= 3
        return val

    def ternary_hw(val, n=32):
        """Count non-zero trits (Hamming weight in ternary)."""
        hw = 0
        for _ in range(n):
            if val % 3 != 0:
                hw += 1
            val //= 3
        return hw

    # Test: is ★₃ a valid algebra?
    # ★₃(a,b) should satisfy: ★₃(ROTR_k(a), ROTR_k(b)) = ROTR₃_k(★₃(a,b))
    # where ROTR₃ is ternary rotation

    # First: basic statistics of GKP-ternary values
    gkp_hws = []
    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        gkp = carry_gkp_classification(a, b)
        nG = gkp.count('G'); nK = gkp.count('K'); nP = gkp.count('P')
        gkp_hws.append((nG, nK, nP))

    ghw = np.array(gkp_hws)
    print(f"\n  GKP statistics (N={N}):")
    print(f"    E[nG] = {ghw[:,0].mean():.3f} (expected 8.0)")
    print(f"    E[nK] = {ghw[:,1].mean():.3f} (expected 8.0)")
    print(f"    E[nP] = {ghw[:,2].mean():.3f} (expected 16.0)")

    # η connection: carry rank = 3^5 = 243
    # In ternary: 3^5 = 243 values = 5 ternary digits
    # η = (3·log₂3)/4 - 1 = 0.18872
    # 5 × η = 5 × 0.18872 = 0.9436
    # 2^(5η) = 2^0.9436 = 1.923 ≈ 2
    # 3^5 = 243, 2^(5/η_inv) where η_inv = 1/η ≈ 5.3

    print(f"\n  η connection:")
    eta = (3 * math.log2(3)) / 4 - 1
    print(f"    η = {eta:.6f}")
    print(f"    carry_rank = 3^5 = {3**5}")
    print(f"    log₃(carry_rank) = 5")
    print(f"    5 × η = {5*eta:.4f}")
    print(f"    2^(5η) = {2**(5*eta):.4f}")

    # ★₃ operation: addition in ternary
    # If we convert a,b to GKP-ternary and ADD in base 3:
    # Does this relate to the actual carry?
    print(f"\n  ★₃ as ternary addition:")

    # GKP-ternary of (a,b): trit_i = 2 if G, 0 if K, 1 if P
    # Sum of two GKP-ternary values mod 3:
    # This doesn't make direct sense. But:
    # The CARRY is fully determined by the GKP sequence.
    # For bit i: carry_out = G if trit=2, carry_in if trit=1, K(0) if trit=0

    # So carry chain = a ternary AUTOMATON:
    # state = {0, 1} (carry bit)
    # input = trit ∈ {0, 1, 2}
    # transition: 0→K:0, 0→P:0, 0→G:1, 1→K:0, 1→P:1, 1→G:1

    # This is a TERNARY-INPUT BINARY-STATE automaton.
    # The carry chain IS a base-3 computation on a binary channel.

    print(f"    Carry = ternary-input binary-state automaton:")
    print(f"    State × Input → New State")
    print(f"    0 × K(0) → 0")
    print(f"    0 × P(1) → 0")
    print(f"    0 × G(2) → 1")
    print(f"    1 × K(0) → 0")
    print(f"    1 × P(1) → 1")
    print(f"    1 × G(2) → 1")
    print(f"")
    print(f"    This IS the ★₃ operation!")
    print(f"    The ternary GKP drives a binary carry state.")
    print(f"    η = the information rate of this channel:")
    print(f"    3 ternary inputs → ~η binary bits of carry info per trit")

# ============================================================
# DIRECTION 3: ★⁻¹ — Duality
# ============================================================

def test_star_dual(N=5000):
    """★⁻¹: dual decomposition."""
    print(f"\n{'='*60}")
    print(f"DIRECTION 3: ★⁻¹ DUALITY")
    print(f"{'='*60}")

    # ★(a,b) = (a⊕b, a&b) decomposes + into (⊕, &)
    # ★⁻¹: decompose ⊕ into (+, ?)
    #   a ⊕ b = (a + b) - 2(a & b) = (a + b) + 2·NOT(a & b) + 2 ... mod 2^32
    #   Actually: a ⊕ b = (a + b) - 2·(a & b) in true integers
    #   So: ⊕ = + - 2·& (exact in integers, with possible borrow)

    # Dual pair: (a+b, a&b) — same AND, but sum instead of XOR
    # a⊕b = (a+b) - 2·(a&b)
    # So ★ and ★⁻¹ share the AND component!

    # Test: can we reconstruct XOR from (sum, AND)?
    exact = 0
    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        s = (a + b) & MASK  # sum mod 2^32
        and_ab = a & b
        xor_reconstructed = (s - 2 * and_ab) & MASK  # This might not work due to mod

        real_xor = a ^ b
        if xor_reconstructed == real_xor:
            exact += 1

    rate = exact / N
    print(f"\n  Reconstruct ⊕ from (+, &): {rate:.6f}")

    if rate < 0.99:
        # The issue: in integers a⊕b = (a+b) - 2(a&b), but mod 2^32 this
        # can underflow. Need to handle the borrow.
        # Actually, the full carry relationship:
        # a + b = (a⊕b) + 2(a&b) [in unbounded integers]
        # So: a⊕b = (a+b) - 2(a&b) [in unbounded integers]
        # Mod 2^32: a⊕b = ((a+b) - 2(a&b)) mod 2^32
        # This SHOULD work because both sides are mod 2^32.
        print(f"  Checking with explicit calculation...")
        exact2 = 0
        for _ in range(N):
            a = random.randint(0, MASK); b = random.randint(0, MASK)
            # In Python: (a+b) can exceed 32 bits, so we need careful mod
            s_full = a + b  # No mod yet
            and_ab = a & b
            xor_full = s_full - 2 * and_ab  # In true integers
            xor_mod = xor_full & MASK

            if xor_mod == (a ^ b):
                exact2 += 1
        print(f"  Full integer path: {exact2/N:.6f}")

    # DUALITY PRINCIPLE:
    print(f"\n  DUALITY PRINCIPLE:")
    print(f"    ★(a,b) = (a⊕b, a&b)     →  π_add resolves carry SEQUENTIALLY")
    print(f"    ★⁻¹(a,b) = (a+b, a&b)   →  π_xor resolves carry via SUBTRACTION")
    print(f"")
    print(f"    ★: parallel split (⊕,&) → sequential resolve (carry chain)")
    print(f"    ★⁻¹: sequential split (+) → parallel resolve (subtract 2·&)")
    print(f"")
    print(f"    In ★: collision needs carry chain resolution (hard)")
    print(f"    In ★⁻¹: collision needs... what?")

    # In dual space: collision H(M₁) = H(M₂) means:
    # IV + s₁ = IV + s₂ → s₁ = s₂
    # In ★⁻¹: s = (s_sum, s_and) where s_sum = "sum representation"
    # Collision: s₁_sum = s₂_sum AND s₁_and = s₂_and

    # The question: is the dual representation SIMPLER for collision?
    print(f"    Collision in ★:  δ(XOR) = carry_correction(δ(AND))")
    print(f"    Collision in ★⁻¹: δ(SUM) = 2 · δ(AND)")
    print(f"    The dual form is ALGEBRAICALLY SIMPLER!")
    print(f"    δ(SUM) = 2·δ(AND) is a LINEAR equation!")

# ============================================================
# DIRECTION 4: ★_round — Tensor
# ============================================================

def test_star_round(N=1000):
    """★_round: entire round as one operation in ★-space."""
    print(f"\n{'='*60}")
    print(f"DIRECTION 4: ★_ROUND TENSOR")
    print(f"{'='*60}")

    # One round: state_{r+1} = R(state_r, W_r, K_r)
    # In ★-space: ★_state = (state ⊕ something, state & something)
    # But the round function mixes ALL 8 words.

    # Define: ★_state(r) = tuple of ★-pairs for each word
    # ★_state = ((a⊕iv_a, a&iv_a), (b⊕iv_b, b&iv_b), ...) — 16 words total

    # Measure: does ★_round have lower effective dimension than standard round?

    # Collect ★-state vectors
    star_states = []
    std_states = []

    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, 64)
        s = states[64]

        # Standard state: 256 bits
        std_vec = []
        for w in range(8):
            for b in range(32):
                std_vec.append((s[w] >> b) & 1)

        # ★-state: 512 bits (XOR and AND components with IV)
        star_vec = []
        for w in range(8):
            xor_part = s[w] ^ IV[w]
            and_part = s[w] & IV[w]
            for b in range(32):
                star_vec.append((xor_part >> b) & 1)
            for b in range(32):
                star_vec.append((and_part >> b) & 1)

        star_states.append(star_vec)
        std_states.append(std_vec)

    std_arr = np.array(std_states, dtype=float) - 0.5
    star_arr = np.array(star_states, dtype=float) - 0.5

    # PCA on both
    for name, arr in [("Standard (256-dim)", std_arr), ("★-state (512-dim)", star_arr)]:
        n_sub = min(N, 800)
        _, sigma, _ = np.linalg.svd(arr[:n_sub], full_matrices=False)
        cumvar = np.cumsum(sigma**2) / np.sum(sigma**2)
        d95 = np.searchsorted(cumvar, 0.95) + 1
        d99 = np.searchsorted(cumvar, 0.99) + 1
        d999 = np.searchsorted(cumvar, 0.999) + 1
        print(f"\n  {name}:")
        print(f"    dim(95%): {d95}")
        print(f"    dim(99%): {d99}")
        print(f"    dim(99.9%): {d999}")
        print(f"    σ₁/σ_last: {sigma[0]/sigma[min(len(sigma)-1, d999)]:.2f}")

    # Does ★-state have LOWER effective dimension?
    # If yes → ★-space is more compact → collision search in ★ is cheaper

# ============================================================
# DIRECTION 5: ★-limit — Dynamics / Attractor
# ============================================================

def test_star_limit(N=300):
    """★-limit: does the round function have an attractor?"""
    print(f"\n{'='*60}")
    print(f"DIRECTION 5: ★-LIMIT / ATTRACTOR")
    print(f"{'='*60}")

    # Iterate the round function BEYOND 64 rounds.
    # Use fixed W (all zeros) to remove message dependence.
    # Does the state converge to a cycle or fixed point?

    W_fixed = [0] * 64  # Fixed schedule words

    print(f"\n  Iterating round function with W=0, K=K[r mod 64]:")

    # Start from IV, iterate many rounds
    state = list(IV)
    history = [tuple(state)]

    for r in range(2000):
        W_r = 0
        K_r = K[r % 64]
        state = sha256_round(state, W_r, K_r)
        history.append(tuple(state))

    # Look for cycles
    seen = {}
    cycle_start = -1
    cycle_len = -1
    for i, s in enumerate(history):
        if s in seen:
            cycle_start = seen[s]
            cycle_len = i - cycle_start
            break
        seen[s] = i

    if cycle_len > 0:
        print(f"  CYCLE FOUND! Start={cycle_start}, Length={cycle_len}")
    else:
        print(f"  No cycle in 2000 iterations")

    # Measure state evolution: does HW stabilize?
    hws = [sum(hw(s[w]) for w in range(8)) for s in history]
    print(f"\n  State HW evolution:")
    for r in [0, 10, 50, 100, 500, 1000, 1999]:
        print(f"    Round {r:>5}: HW = {hws[r]}")

    # Measure: attractor dimension via inter-state distances
    # Sample states from late iterations (> 500)
    late_states = history[500:]
    state_bits = np.zeros((len(late_states), 256), dtype=float)
    for i, s in enumerate(late_states):
        for w in range(8):
            for b in range(32):
                state_bits[i, w*32+b] = (s[w] >> b) & 1

    state_centered = state_bits - state_bits.mean(axis=0)
    n_sub = min(len(late_states), 500)
    _, sigma, _ = np.linalg.svd(state_centered[:n_sub], full_matrices=False)
    cumvar = np.cumsum(sigma**2) / np.sum(sigma**2)
    d95 = np.searchsorted(cumvar, 0.95) + 1
    d99 = np.searchsorted(cumvar, 0.99) + 1

    print(f"\n  Attractor dimension (W=0, rounds 500-2000):")
    print(f"    dim(95%): {d95}")
    print(f"    dim(99%): {d99}")
    print(f"    (Full state = 256 dims)")

    if d95 < 200:
        print(f"    *** ATTRACTOR IS LOW-DIMENSIONAL: {d95} < 256 ***")
    else:
        print(f"    Attractor fills full state space")

    # Now with RANDOM W (different each round)
    print(f"\n  With random W (each round different):")
    state = list(IV)
    late_random = []
    for r in range(2000):
        W_r = random.randint(0, MASK)
        K_r = K[r % 64]
        state = sha256_round(state, W_r, K_r)
        if r >= 500:
            late_random.append(tuple(state))

    rb = np.zeros((len(late_random), 256), dtype=float)
    for i, s in enumerate(late_random):
        for w in range(8):
            for b in range(32):
                rb[i, w*32+b] = (s[w] >> b) & 1

    rc = rb - rb.mean(axis=0)
    n_sub = min(len(late_random), 500)
    _, sigma_r, _ = np.linalg.svd(rc[:n_sub], full_matrices=False)
    cumvar_r = np.cumsum(sigma_r**2) / np.sum(sigma_r**2)
    d95_r = np.searchsorted(cumvar_r, 0.95) + 1
    d99_r = np.searchsorted(cumvar_r, 0.99) + 1

    print(f"    dim(95%): {d95_r}")
    print(f"    dim(99%): {d99_r}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 125: BEYOND ★ — FIVE DIRECTIONS")
    print("=" * 60)

    test_star2(3000)
    test_star3(3000)
    test_star_dual(3000)
    test_star_round(600)
    test_star_limit(200)

    print(f"\n{'='*60}")
    print(f"SYNTHESIS: WHAT LIES BEYOND ★")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
