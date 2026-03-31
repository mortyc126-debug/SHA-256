#!/usr/bin/env python3
"""
EXP 107: Circular Carry — Making Carry EXACTLY ROTR-Equivariant

From exp106: carry(ROTR_k(a), ROTR_k(b)) = ROTR_k(carry(a,b)) ⊕ ε
where ε has HW ≈ 1.9 (boundary error at bit-0/31).

The 1.9-bit error comes from carry chains crossing the
non-circular boundary (carry stops at bit 31, doesn't wrap to 0).

IDEA: Define CIRCULAR carry where bit 31 feeds into bit 0.
Then carry_circ IS exactly ROTR-equivariant:
  carry_circ(ROTR_k(a), ROTR_k(b)) = ROTR_k(carry_circ(a,b))

If carry_circ approximates standard carry well enough,
and carry_circ IS ROTR-equivariant, then:
  ≡ defined via carry_circ → cascade continues across ROTR!

PROBLEMS:
1. Circular carry may not converge (infinite loop if all P)
2. Circular carry ≠ standard carry → collision definition changes
3. Need to measure: how different IS circular from standard?

ALSO TEST:
- Boundary carry decomposition: carry = carry_bulk + carry_boundary
- carry_bulk IS ROTR-equivariant, carry_boundary has ~1.9 bits
- Can we solve collision on carry_bulk + correct for boundary?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def carry_word(a, b):
    """Standard linear carry as 32-bit word."""
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def carry_bits_linear(a, b):
    """Standard linear carry: bit 0 carry_in = 0."""
    c = 0
    carries = []
    for i in range(32):
        ai = (a >> i) & 1; bi = (b >> i) & 1
        c = (ai & bi) | ((ai ^ bi) & c)
        carries.append(c)
    return carries

def carry_bits_circular(a, b, max_iter=64):
    """Circular carry: bit 31 feeds back to bit 0.
    Iterate until convergence."""
    # Start with c_in = 0
    carries = [0] * 32
    for iteration in range(max_iter):
        new_carries = [0] * 32
        c_in = carries[31]  # Circular: carry from bit 31 feeds bit 0
        c = c_in
        for i in range(32):
            ai = (a >> i) & 1; bi = (b >> i) & 1
            c = (ai & bi) | ((ai ^ bi) & c)
            new_carries[i] = c
        if new_carries == carries:
            return carries, iteration + 1
        carries = new_carries
    return carries, max_iter  # Didn't converge

def carry_to_word(carries):
    """Convert carry bit list to 32-bit word."""
    w = 0
    for i in range(32):
        w |= (carries[i] << i)
    return w

def test_circular_convergence(N=10000):
    """Does circular carry converge? How fast?"""
    print(f"\n--- CIRCULAR CARRY CONVERGENCE (N={N}) ---")

    iter_counts = []
    converged = 0

    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        _, iters = carry_bits_circular(a, b)
        iter_counts.append(iters)
        if iters < 64:
            converged += 1

    ic = np.array(iter_counts)
    print(f"Convergence rate: {converged/N:.6f}")
    print(f"Mean iterations: {ic.mean():.3f}")
    print(f"Max iterations: {ic.max()}")
    print(f"Distribution:")
    for t in [1, 2, 3, 4, 5, 10, 20, 64]:
        pct = np.sum(ic <= t) / N
        print(f"  ≤ {t:>2} iters: {pct:.4f}")

    # When does it NOT converge? → all P bits (carry propagates forever)
    non_conv = 0
    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        gkp = carry_gkp_classification(a, b)
        nP = gkp.count('P')
        _, iters = carry_bits_circular(a, b)
        if iters >= 64:
            non_conv += 1
            print(f"  Non-convergent: nP={nP}, a=0x{a:08x}, b=0x{b:08x}")
            if non_conv >= 5:
                break

    return converged / N

def test_circular_vs_linear(N=10000):
    """How different is circular carry from linear?"""
    print(f"\n--- CIRCULAR vs LINEAR CARRY (N={N}) ---")

    diffs = []
    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        linear = carry_bits_linear(a, b)
        circular, _ = carry_bits_circular(a, b)
        diff = sum(linear[i] != circular[i] for i in range(32))
        diffs.append(diff)

    da = np.array(diffs)
    print(f"HW(circular ⊕ linear):")
    print(f"  Mean: {da.mean():.4f}")
    print(f"  Exact match: {np.sum(da == 0)/N:.4f}")
    print(f"  Distribution:")
    for d in range(8):
        print(f"    diff={d}: {np.sum(da == d)/N:.4f}")

    return da.mean()

def test_circular_rotr_equivariance(N=10000):
    """Is circular carry EXACTLY ROTR-equivariant?"""
    print(f"\n--- CIRCULAR CARRY ROTR-EQUIVARIANCE (N={N}) ---")

    rotations = [2, 6, 11, 13, 22, 25]
    equivariant = {k: 0 for k in rotations}
    errors = {k: [] for k in rotations}

    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        cc, _ = carry_bits_circular(a, b)
        cc_word = carry_to_word(cc)

        for k in rotations:
            a_rot = rotr(a, k); b_rot = rotr(b, k)
            cc_rot, _ = carry_bits_circular(a_rot, b_rot)
            cc_rot_word = carry_to_word(cc_rot)

            # Expected: ROTR_k(cc_word) should equal cc_rot_word
            expected = rotr(cc_word, k)
            diff = hw(cc_rot_word ^ expected)
            errors[k].append(diff)
            if diff == 0:
                equivariant[k] += 1

    print(f"Circular carry ROTR-equivariance:")
    for k in rotations:
        rate = equivariant[k] / N
        err = np.array(errors[k])
        print(f"  ROTR-{k:>2}: exact={rate:.6f}, mean_error={err.mean():.4f}")

    # Compare with linear carry
    print(f"\nLinear carry ROTR-equivariance (for comparison):")
    for k in rotations:
        count = 0
        for _ in range(min(N, 3000)):
            a = random.randint(0, MASK); b = random.randint(0, MASK)
            cw = carry_word(a, b)
            a_rot = rotr(a, k); b_rot = rotr(b, k)
            cw_rot = carry_word(a_rot, b_rot)
            if hw(cw_rot ^ rotr(cw, k)) == 0:
                count += 1
        print(f"  ROTR-{k:>2}: exact={count/min(N,3000):.6f}")

    avg_exact = np.mean([equivariant[k]/N for k in rotations])
    print(f"\n  Circular avg exact equivariance: {avg_exact:.6f}")
    return avg_exact

def test_boundary_decomposition(N=10000):
    """Decompose carry = carry_bulk + carry_boundary.
    carry_bulk should be ROTR-equivariant."""
    print(f"\n--- BOUNDARY DECOMPOSITION (N={N}) ---")

    rotations = [2, 6, 11, 13, 22, 25]

    # carry_boundary = carry_linear ⊕ carry_circular
    # carry_bulk = carry_circular (ROTR-equivariant part)
    # carry_linear = carry_bulk ⊕ carry_boundary

    boundary_hws = []
    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        linear = carry_bits_linear(a, b)
        circular, _ = carry_bits_circular(a, b)
        boundary = [linear[i] ^ circular[i] for i in range(32)]
        boundary_hws.append(sum(boundary))

    bhw = np.array(boundary_hws)
    print(f"Boundary carry HW: mean={bhw.mean():.4f}, std={bhw.std():.4f}")
    print(f"Boundary = 0 (circular = linear): {np.sum(bhw==0)/N:.4f}")

    # Which bit positions are boundary-sensitive?
    boundary_bits = np.zeros(32)
    for _ in range(N):
        a = random.randint(0, MASK); b = random.randint(0, MASK)
        linear = carry_bits_linear(a, b)
        circular, _ = carry_bits_circular(a, b)
        for i in range(32):
            if linear[i] != circular[i]:
                boundary_bits[i] += 1

    boundary_bits /= N
    print(f"\nBoundary-sensitive bit positions:")
    for i in range(32):
        if boundary_bits[i] > 0.01:
            print(f"  Bit {i:>2}: {boundary_bits[i]:.4f}")

    print(f"\nTotal boundary bits: {boundary_bits.sum():.3f}")
    print(f"Boundary entropy: {bhw.mean():.3f} bits per word")
    print(f"Per 8 words: {bhw.mean() * 8:.1f} boundary bits total")

def test_collision_via_circular(N=5000):
    """Can collision be reformulated using circular carry?

    Standard: H = IV + state → collision = (IV + s1) = (IV + s2)
    In carry: (IV ⊕ s1) ⊕ carry(IV, s1) = (IV ⊕ s2) ⊕ carry(IV, s2)

    Circular version: replace carry with carry_circ.
    How much does this change the collision equation?"""
    print(f"\n--- COLLISION VIA CIRCULAR CARRY (N={N}) ---")

    # Compute: for Wang pairs, how does δH change under circular carry?
    dH_linear = []; dH_circular = []

    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        Wn, Wf, _, sn, sf = wang_cascade(W0, W1)

        # Linear (standard) hash difference
        Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
        dh_lin = sum(hw(Hn[w] ^ Hf[w]) for w in range(8))
        dH_linear.append(dh_lin)

        # Circular hash: H_circ = (IV ⊕ state) ⊕ carry_circ(IV, state)
        Hn_circ = []; Hf_circ = []
        for w in range(8):
            cc_n, _ = carry_bits_circular(IV[w], sn[64][w])
            cc_f, _ = carry_bits_circular(IV[w], sf[64][w])
            hn_circ = (IV[w] ^ sn[64][w]) ^ carry_to_word(cc_n)
            hf_circ = (IV[w] ^ sf[64][w]) ^ carry_to_word(cc_f)
            Hn_circ.append(hn_circ)
            Hf_circ.append(hf_circ)

        dh_circ = sum(hw(Hn_circ[w] ^ Hf_circ[w]) for w in range(8))
        dH_circular.append(dh_circ)

    dl = np.array(dH_linear); dc = np.array(dH_circular)
    corr = np.corrcoef(dl, dc)[0, 1]

    print(f"δH linear:   mean={dl.mean():.2f}, std={dl.std():.2f}")
    print(f"δH circular: mean={dc.mean():.2f}, std={dc.std():.2f}")
    print(f"corr(δH_lin, δH_circ): {corr:+.6f}")
    print(f"E[|δH_lin - δH_circ|]: {np.mean(np.abs(dl - dc)):.3f}")

    # KEY: how many MORE zeros does circular have?
    n_zero_lin = np.sum(dl == 0)
    n_zero_circ = np.sum(dc == 0)
    print(f"\nδH = 0 (collision):")
    print(f"  Linear:   {n_zero_lin}/{N}")
    print(f"  Circular: {n_zero_circ}/{N}")

    # Effective dimension comparison
    for arr, name in [(dl, "linear"), (dc, "circular")]:
        mean = arr.mean(); std = arr.std()
        n_eff = 2 * (mean/std)**2 if std > 0 else 256
        print(f"  {name}: n_eff = {n_eff:.1f}, birthday = 2^{n_eff/2:.0f}")

def test_equivariant_cascade_cost(N=2000):
    """If we use circular carry, what's the cascade cost?

    Standard carry: R=1 (ROTR breaks cascade)
    Circular carry: R=? (ROTR-equivariant → cascade may continue)

    Test: for Wang pairs, how many rounds does the circular carry
    cascade sustain before information loss?"""
    print(f"\n--- EQUIVARIANT CASCADE COST (N={N}) ---")

    # Measure: mutual information between circular carry at round r
    # and circular carry at round r+1, for the SAME message

    carry_persistence = []
    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        Wn, Wf, _, sn, sf = wang_cascade(W0, W1)

        # Track circular carry difference across rounds
        prev_cc_diff = None
        round_persist = []

        for r in range(16, min(25, len(sn))):
            # Circular carry at this round (e-branch: word 4)
            cc_n, _ = carry_bits_circular(sn[r][3], sn[r][4])  # d + e
            cc_f, _ = carry_bits_circular(sf[r][3], sf[r][4])

            cc_diff = carry_to_word(cc_n) ^ carry_to_word(cc_f)

            if prev_cc_diff is not None:
                # How many bits persist?
                persist = 32 - hw(cc_diff ^ prev_cc_diff)
                round_persist.append(persist)

            prev_cc_diff = cc_diff

        if round_persist:
            carry_persistence.append(round_persist)

    if not carry_persistence:
        print("No data")
        return

    # Average persistence per round step
    max_steps = max(len(cp) for cp in carry_persistence)
    for step in range(min(max_steps, 8)):
        vals = [cp[step] for cp in carry_persistence if step < len(cp)]
        avg = np.mean(vals)
        print(f"  Round {16+step}→{17+step}: carry persistence = {avg:.2f}/32 bits")

    # Inter-round carry information (bits surviving per round)
    all_vals = [v for cp in carry_persistence for v in cp]
    R_circ = np.mean(all_vals)
    print(f"\nAverage carry persistence (circular): {R_circ:.2f}/32 = {R_circ/32:.4f}")
    print(f"Compare: standard carry R ≈ 1 bit inter-round")
    print(f"Circular carry R ≈ {R_circ:.1f} bits inter-round")

    if R_circ > 5:
        print(f"\n*** CIRCULAR CARRY ACHIEVES R = {R_circ:.1f} > 1 ***")
        print(f"This means equivariant cascade CONTINUES across rounds!")
        cascade_rounds = 256 / R_circ
        print(f"Cascade covers 256 bits in ≈ {cascade_rounds:.0f} rounds")

    return R_circ

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 107: CIRCULAR CARRY")
    print("Making carry EXACTLY ROTR-equivariant")
    print("=" * 60)

    conv = test_circular_convergence(5000)
    diff = test_circular_vs_linear(5000)
    equiv = test_circular_rotr_equivariance(5000)
    test_boundary_decomposition(5000)
    test_collision_via_circular(3000)
    R = test_equivariant_cascade_cost(2000)

    print(f"\n{'='*60}")
    print(f"VERDICT: Circular Carry")
    print(f"  Convergence rate: {conv:.6f}")
    print(f"  Diff from linear: {diff:.4f} bits")
    print(f"  ROTR-equivariance: {equiv:.6f}")
    if R is not None:
        print(f"  Inter-round R: {R:.2f} bits")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
