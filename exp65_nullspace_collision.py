#!/usr/bin/env python3
"""
EXP 65: Schedule Nullspace Collision

Schedule has 32-dim nullspace over GF(2) (exp63).
Messages differing by nullvector have IDENTICAL XOR-schedule.
Their REAL schedule differs only in carry (50%).

If carry-only schedule difference → simpler round function dynamics
→ potentially easier collision.

Strategy: restrict search to W' = W + nullvec (over GF2).
This is a 32-bit search (not 512-bit) with structured schedule diff.

Cost: 2^32 evaluations for 32-dim nullspace search.
If this finds collision → 2^32 << 2^128 = enormous speedup.
If not → the 32-dim subspace doesn't contain collisions.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def build_schedule_nullspace():
    """Build basis of schedule nullspace (M+I)·x = 0 over GF(2)."""

    # Build M: W[16..31] = M · W[0..15] over GF(2)
    # We need to find nullspace of (M + I) where I maps W[0..15] → W[0..15]

    # Simpler: compute numerically by finding vectors x where
    # xor_schedule(W ⊕ x) = xor_schedule(W) ⊕ xor_schedule(x) and
    # xor_schedule(x)[16..31] = x[0..15] (fixed point)

    # Build 512×512 matrix M+I directly
    MI = np.zeros((512, 512), dtype=np.int64)

    # For each bit: compute schedule output and XOR with identity
    for j in range(512):
        w_idx = j // 32; b_idx = j % 32

        # Create unit vector
        W_unit = [0] * 16
        W_unit[w_idx] = 1 << b_idx

        # XOR schedule
        W_exp = list(W_unit) + [0] * 48
        for t in range(16, 64):
            W_exp[t] = sig1(W_exp[t-2]) ^ W_exp[t-7] ^ sig0(W_exp[t-15]) ^ W_exp[t-16]

        # M maps W[0..15] to W[16..31]
        # (M+I) maps W[0..15] to W[16..31] ⊕ W[0..15]
        for i in range(512):
            wi = i // 32; bi = i % 32
            if wi < 16:
                # Output word from W[16..31]
                out_bit = (W_exp[16 + wi] >> bi) & 1
                # XOR with identity (W[0..15])
                id_bit = (W_unit[wi] >> bi) & 1
                MI[i][j] = (out_bit ^ id_bit) % 2

    # Find nullspace via Gaussian elimination
    A = MI.copy()
    n = 512
    pivot_cols = []
    rank = 0

    for col in range(n):
        pivot = -1
        for row in range(rank, n):
            if A[row, col] % 2 == 1:
                pivot = row; break
        if pivot == -1: continue
        A[[rank, pivot]] = A[[pivot, rank]]
        for row in range(n):
            if row != rank and A[row, col] % 2 == 1:
                A[row] = (A[row] + A[rank]) % 2
        pivot_cols.append(col)
        rank += 1

    # Free columns
    free_cols = [c for c in range(n) if c not in pivot_cols]
    nullity = len(free_cols)

    # Construct nullspace basis
    null_basis = []
    for fc in free_cols:
        vec = np.zeros(n, dtype=np.int64)
        vec[fc] = 1
        # Back-substitute
        for i, pc in reversed(list(enumerate(pivot_cols))):
            if A[i, fc] % 2 == 1:
                vec[pc] = 1
        null_basis.append(vec)

    return null_basis, nullity

def nullvec_to_W16(vec):
    """Convert 512-bit nullspace vector to 16 words."""
    W = [0] * 16
    for i in range(512):
        if vec[i]:
            W[i//32] ^= (1 << (i%32))
    return W

def test_nullspace_collision_search():
    """Search for collision within schedule nullspace."""
    print("\n--- SCHEDULE NULLSPACE COLLISION SEARCH ---")

    null_basis, nullity = build_schedule_nullspace()
    print(f"Nullspace dimension: {nullity}")
    print(f"Search space: 2^{nullity} = {2**nullity}")

    if nullity == 0:
        print("No nullspace — nothing to search")
        return

    # For a base message W, try all 2^nullity perturbations
    # and check if any gives collision
    W_base = random_w16()
    H_base = sha256_compress(W_base)

    # If nullity ≤ 20: exhaustive search feasible
    search_bits = min(nullity, 20)
    n_search = 2 ** search_bits

    print(f"Searching {n_search} nullspace perturbations...")

    best_dH = 256
    hashes_seen = {}

    for mask in range(n_search):
        # Construct perturbation from nullspace basis
        pert = np.zeros(512, dtype=np.int64)
        for b in range(search_bits):
            if (mask >> b) & 1:
                pert = (pert + null_basis[b]) % 2

        W_pert = nullvec_to_W16(pert)

        # Apply perturbation (XOR)
        W_new = [(W_base[i] ^ W_pert[i]) for i in range(16)]

        if W_new == W_base:
            continue

        H_new = sha256_compress(W_new)
        dH = sum(hw(H_base[i] ^ H_new[i]) for i in range(8))

        if dH < best_dH:
            best_dH = dH
            if dH == 0:
                print(f"*** COLLISION FOUND at mask={mask}! ***")
                break

        h_key = tuple(H_new)
        if h_key in hashes_seen:
            prev_mask = hashes_seen[h_key]
            if prev_mask != mask:
                print(f"*** INTERNAL COLLISION: mask {prev_mask} and {mask} ***")
                break
        hashes_seen[h_key] = mask

    birthday = 128 - 8*np.sqrt(2*np.log(max(n_search,2)))
    print(f"\nBest δH in nullspace: {best_dH}")
    print(f"Birthday for N={n_search}: ~{birthday:.0f}")
    print(f"Unique hashes: {len(hashes_seen)}/{n_search}")

    # Also: measure schedule difference for nullspace perturbations
    print(f"\nSchedule difference for nullspace perturbations:")
    sample_masks = random.sample(range(1, min(n_search, 1000)), min(50, n_search-1))
    sched_diffs = []
    for mask in sample_masks:
        pert = np.zeros(512, dtype=np.int64)
        for b in range(search_bits):
            if (mask >> b) & 1:
                pert = (pert + null_basis[b]) % 2
        W_pert = nullvec_to_W16(pert)
        W_new = [(W_base[i] ^ W_pert[i]) for i in range(16)]

        S_base = schedule(W_base)
        S_new = schedule(W_new)
        diff = sum(hw(S_base[t] ^ S_new[t]) for t in range(16, 64))
        sched_diffs.append(diff)

    sd = np.array(sched_diffs)
    # Expected for random: 48*16 = 768
    print(f"  Schedule diff (nullspace): mean={sd.mean():.1f}, std={sd.std():.1f}")
    print(f"  Expected (random pairs):   768")
    print(f"  Ratio: {sd.mean()/768:.4f}")

    if sd.mean() < 768 * 0.9:
        print(f"  *** Nullspace pairs have SMALLER schedule diff! ***")

def test_multiple_bases(N_bases=10):
    """Try nullspace search from multiple base messages."""
    print(f"\n--- NULLSPACE SEARCH: {N_bases} BASE MESSAGES ---")

    null_basis, nullity = build_schedule_nullspace()
    search_bits = min(nullity, 18)
    n_search = 2 ** search_bits

    all_bests = []
    for base in range(N_bases):
        W_base = random_w16()
        H_base = sha256_compress(W_base)

        best_dH = 256
        for mask in range(n_search):
            pert = np.zeros(512, dtype=np.int64)
            for b in range(search_bits):
                if (mask >> b) & 1:
                    pert = (pert + null_basis[b]) % 2
            W_pert = nullvec_to_W16(pert)
            W_new = [(W_base[i] ^ W_pert[i]) for i in range(16)]
            if W_new == W_base: continue

            H_new = sha256_compress(W_new)
            dH = sum(hw(H_base[i] ^ H_new[i]) for i in range(8))
            best_dH = min(best_dH, dH)

        all_bests.append(best_dH)
        print(f"  Base {base}: best δH = {best_dH}")

    birthday = 128 - 8*np.sqrt(2*np.log(n_search))
    print(f"\nOverall: E[best]={np.mean(all_bests):.1f}, min={min(all_bests)}")
    print(f"Birthday (N={n_search}): ~{birthday:.0f}")

    # Compare with random search of same size
    random_bests = []
    for _ in range(N_bases):
        W_r = random_w16()
        H_r = sha256_compress(W_r)
        best_r = 256
        for _ in range(n_search):
            W_t = random_w16()
            H_t = sha256_compress(W_t)
            dH = sum(hw(H_r[i]^H_t[i]) for i in range(8))
            best_r = min(best_r, dH)
        random_bests.append(best_r)

    print(f"Random search: E[best]={np.mean(random_bests):.1f}, min={min(random_bests)}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 65: SCHEDULE NULLSPACE COLLISION")
    print("="*60)
    test_nullspace_collision_search()
    test_multiple_bases(5)

if __name__ == "__main__":
    main()
