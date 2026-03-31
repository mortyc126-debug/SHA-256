#!/usr/bin/env python3
"""
EXP 81: UALRA Operator Decomposition

SHA-256 round = Γ ∘ Ch ∘ Shift ∘ ROTR (4 operators).
Each operator has its own eigenstructure.
SHA-256 security comes from [Γ, ROTR] maximal non-commutativity.

BUT: CR-group = ALL maps. So collision-creating map EXISTS.
Question: WHERE in CR-group is SHA-256? And how to navigate TO collision?

Approach: decompose SHA-256 round into Γ, Ch, Shift, ROTR components.
Measure: how much of the round function comes from each component?
If one component DOMINATES → collision reduces to that component.

Also: what is the COMMUTATOR [Γ,Ch]? Not studied before.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def round_without_carry(state, W_r, K_r):
    """Round function with + replaced by ⊕ (remove Γ component)."""
    a,b,c,d,e,f,g,h = state
    T1 = h ^ sigma1(e) ^ ch(e,f,g) ^ K_r ^ W_r
    T2 = sigma0(a) ^ maj(a,b,c)
    return [T1^T2, a, b, c, d^T1, e, f, g]

def round_without_ch(state, W_r, K_r):
    """Round function with Ch replaced by XOR (remove Ch component)."""
    a,b,c,d,e,f,g,h = state
    ch_linearized = e ^ f ^ g  # Linear approximation of Ch
    T1 = (h + sigma1(e) + ch_linearized + K_r + W_r) & MASK
    T2 = (sigma0(a) + maj(a,b,c)) & MASK
    return [(T1+T2)&MASK, a, b, c, (d+T1)&MASK, e, f, g]

def round_without_rotation(state, W_r, K_r):
    """Round function with Σ0,Σ1 = 0 (remove ROTR component)."""
    a,b,c,d,e,f,g,h = state
    T1 = (h + 0 + ch(e,f,g) + K_r + W_r) & MASK  # Σ1=0
    T2 = (0 + maj(a,b,c)) & MASK  # Σ0=0
    return [(T1+T2)&MASK, a, b, c, (d+T1)&MASK, e, f, g]

def round_without_shift(state, W_r, K_r):
    """Round function without shift register (all words recomputed)."""
    a,b,c,d,e,f,g,h = state
    T1 = (h + sigma1(e) + ch(e,f,g) + K_r + W_r) & MASK
    T2 = (sigma0(a) + maj(a,b,c)) & MASK
    # Instead of shifting, recompute all from T1, T2
    return [(T1+T2)&MASK, (T1+T2)&MASK, (T1+T2)&MASK, (T1+T2)&MASK,
            (d+T1)&MASK, (d+T1)&MASK, (d+T1)&MASK, (d+T1)&MASK]

def sha_variant(W16, round_fn, R=64):
    """Run SHA-256 with modified round function."""
    iv = list(IV); W = schedule(W16)
    state = list(iv)
    for r in range(R):
        state = round_fn(state, W[r], K[r])
    return [(iv[i]+state[i])&MASK for i in range(8)]

def test_component_contribution(N=2000):
    """How much does each component contribute to hash output?"""
    print("\n--- COMPONENT CONTRIBUTION ---")

    dists = {'no_carry': [], 'no_ch': [], 'no_rotr': [], 'full': []}

    for _ in range(N):
        W16 = random_w16()
        H_full = sha256_compress(W16)

        H_nc = sha_variant(W16, round_without_carry)
        H_nch = sha_variant(W16, round_without_ch)
        H_nr = sha_variant(W16, round_without_rotation)

        dists['no_carry'].append(sum(hw(H_full[i]^H_nc[i]) for i in range(8)))
        dists['no_ch'].append(sum(hw(H_full[i]^H_nch[i]) for i in range(8)))
        dists['no_rotr'].append(sum(hw(H_full[i]^H_nr[i]) for i in range(8)))

    for name in ['no_carry', 'no_ch', 'no_rotr']:
        arr = np.array(dists[name])
        contribution = arr.mean() / 256 * 100
        print(f"  Remove {name:>10}: dist to full = {arr.mean():.1f}/256 ({contribution:.1f}%)")

    # Which component dominates?
    nc = np.mean(dists['no_carry'])
    nch = np.mean(dists['no_ch'])
    nr = np.mean(dists['no_rotr'])
    print(f"\n  Carry contribution: {nc:.1f} bits ({nc/256*100:.0f}%)")
    print(f"  Ch contribution: {nch:.1f} bits ({nch/256*100:.0f}%)")
    print(f"  ROTR contribution: {nr:.1f} bits ({nr/256*100:.0f}%)")
    print(f"  Total would be: {nc+nch+nr:.1f} (if independent, vs max 256)")

def test_commutator_gamma_ch(N=1000):
    """Measure [Γ, Ch] commutator."""
    print(f"\n--- COMMUTATOR [Γ, Ch] ---")

    # [Γ, Ch] = Γ∘Ch - Ch∘Γ
    # In SHA-256 terms: does order of carry and Ch matter?
    # Test: (a + Ch(e,f,g)) vs (Ch(e,f,g) + a) — mod add is commutative!
    # But the DIFFERENTIAL is not: δ(a + Ch) ≠ δ(Ch + a) through carry

    commutator_norms = []
    for _ in range(N):
        e = random.randint(0,MASK); f = random.randint(0,MASK)
        g = random.randint(0,MASK); a = random.randint(0,MASK)

        # Order 1: first Ch, then add with a
        ch_val = ch(e, f, g)
        result1 = (a + ch_val) & MASK

        # Order 2: same result (addition is commutative!)
        result2 = (ch_val + a) & MASK

        # Commutator of the VALUES is 0 (addition commutative)
        # But commutator of the CARRY is NOT 0

        carry1 = ((a + ch_val) & MASK) ^ (a ^ ch_val)  # carry of a+Ch
        carry2 = ((ch_val + a) & MASK) ^ (ch_val ^ a)  # carry of Ch+a (same!)

        # Actually commutative in values AND carry. Need DIFFERENTIAL commutator.

        # Perturb e: δe
        de = random.randint(1, MASK)
        ch_pert = ch(e^de, f, g)

        # Path 1: Ch(e+δe) then add: a + Ch(e+δe)
        p1 = (a + ch_pert) & MASK
        # Path 2: first add a+Ch(e), then "add" δCh: (a+Ch(e)) + δCh
        dch = ch_val ^ ch_pert
        p2 = (result1 ^ dch) & MASK  # XOR δCh (would be + in add context)

        # But in UALRA: path 2 should use + not ⊕ for δCh:
        p2_add = (result1 + (dch)) & MASK  # This is wrong conceptually but let's see

        comm = hw(p1 ^ p2)  # Commutator = distance between two paths
        commutator_norms.append(comm)

    cn = np.array(commutator_norms)
    print(f"  ||[Γ, Ch]|| (differential): mean={cn.mean():.2f}, std={cn.std():.2f}")
    print(f"  Expected if commutative: 0")
    print(f"  Expected if maximally non-commutative: 16")

def test_eigenspace_overlap(N=500):
    """
    Do eigenspaces of different components OVERLAP?
    If yes → shared eigenspace = invariant subspace → collision easier in it.
    """
    print(f"\n--- EIGENSPACE OVERLAP ---")

    # Measure: does Γ's structure (carry chains) align with ROTR's structure?
    # Carry: lower-triangular (bit i depends on 0..i-1)
    # ROTR: cyclic (bit i → bit (i+k)%32)
    # Overlap: bits where both have specific structure

    # For SHA-256's specific rotations:
    rotations = [2, 6, 11, 13, 22, 25]  # All ROTR constants

    # Carry "eigenpositions": bit 0 (always free), bit 31 (max carry)
    # ROTR "eigenpositions": bit 0 (fixed by ROTR_32=identity)

    # Test: for each rotation k, does carry(ROTR_k(a), b) have special structure?
    for k in rotations:
        carry_hws = []
        for _ in range(N):
            a = random.randint(0, MASK)
            b = random.randint(0, MASK)
            a_rot = rotr(a, k)
            c_normal = hw(((a+b)&MASK) ^ (a^b))
            c_rotated = hw(((a_rot+b)&MASK) ^ (a_rot^b))
            carry_hws.append(abs(c_normal - c_rotated))

        mean_diff = np.mean(carry_hws)
        print(f"  ROTR_{k:>2}: |carry(a,b) - carry(ROTR(a),b)| = {mean_diff:.4f}")

    print(f"\n  If all ≈ 0: carry invariant under rotation (eigenspace overlap)")
    print(f"  If all ≈ 8: carry maximally changed (no overlap)")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 81: UALRA OPERATOR DECOMPOSITION")
    print("="*60)
    test_component_contribution(1000)
    test_commutator_gamma_ch(800)
    test_eigenspace_overlap(500)

    print("\n"+"="*60)
    print("UALRA STRUCTURE:")
    print("  3 operators: Γ (carry), Ch (boolean), ROTR (rotation)")
    print("  + Shift register (structural)")
    print("  + Bijectivity (constraint)")
    print("="*60)

if __name__ == "__main__":
    main()
