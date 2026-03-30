#!/usr/bin/env python3
"""
EXP 37: Constructive Collision Engineering

PARADIGM SHIFT: Not measuring. Not searching. CONSTRUCTING.

36 experiments measured SHA-256 = random by every metric.
But collision is not a statistical property. It's a CONCRETE OBJECT.

CONSTRUCTION METHOD:
Instead of Wang's "14 rounds De=0, then hope",
ALLOCATE 512 bits of freedom (ΔW[0..15]) to SPECIFIC targets:

Phase 1: Use DW[2..9] for De3..De10=0 (8 zeros, 256 bits used)
Phase 2: Use DW[10..15] to CONSTRUCT specific output bit values
         Target: high bits (28-31) of e-branch (H[4..7]) = 0
         That's 16 target bits, using 192 bits of freedom
Phase 3: W0, W1 = 64 bits remaining for fine-tuning

Total: 256 + 192 + 64 = 512 bits allocated.
       8 + 16 = 24 constraints satisfied.

The key: Phase 2 is NOT random search. It's ANALYTICAL:
compute ∂(H[w]_bit_b) / ∂(DW[k]) and solve the linear system.
"""
import sys, os, random
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def partial_wang(W0, W1, n_zeros=8, DW0=1):
    """Wang cascade with only n_zeros (not 14)."""
    Wn = [W0, W1] + [0]*14
    DWs = [0]*16; DWs[0] = DW0

    # DW2: De3=0
    Wf_tmp = [(Wn[i]+DWs[i])&MASK for i in range(16)]
    sn = sha256_rounds(Wn, 3); sf = sha256_rounds(Wf_tmp, 3)
    DWs[2] = (-de(sn, sf, 3)) & MASK

    # DW3..DW(2+n_zeros-1): cascade
    for step in range(n_zeros - 1):
        wi = step + 3; dt = step + 4
        Wfc = [(Wn[i]+DWs[i])&MASK for i in range(16)]
        tn = sha256_rounds(Wn, dt)
        tf = sha256_rounds(Wfc, dt)
        DWs[wi] = (-de(tn, tf, dt)) & MASK

    return Wn, DWs

def compute_output_jacobian(Wn, DWs, target_words=[4,5,6,7], target_bits=[28,29,30,31],
                             free_words=range(10,16)):
    """
    Compute Jacobian: ∂(H[w]_bit_b) / ∂(DW[k]_bit_j)
    for target output bits and free DW words.

    Returns: matrix J where J[target_idx][input_idx] = 0 or 1 (over GF(2))
    """
    # Base hash
    Wf_base = [(Wn[i]+DWs[i])&MASK for i in range(16)]
    Hn = sha256_compress(Wn)
    Hf_base = sha256_compress(Wf_base)

    # Target bit indices
    targets = [(w, b) for w in target_words for b in target_bits]
    n_targets = len(targets)

    # Free input bits
    free_bits = [(k, j) for k in free_words for j in range(32)]
    n_free = len(free_bits)

    J = np.zeros((n_targets, n_free), dtype=np.int64)

    for fi, (k, j) in enumerate(free_bits):
        # Flip bit j of DW[k]
        DWs_pert = list(DWs)
        DWs_pert[k] ^= (1 << j)
        Wf_pert = [(Wn[i]+DWs_pert[i])&MASK for i in range(16)]
        Hf_pert = sha256_compress(Wf_pert)

        for ti, (w, b) in enumerate(targets):
            # Does this input bit flip the target output bit?
            base_bit = (Hf_base[w] >> b) & 1
            pert_bit = (Hf_pert[w] >> b) & 1
            J[ti][fi] = base_bit ^ pert_bit

    return J, targets, free_bits, Hf_base, Hn

def gf2_solve(J, target_vector):
    """
    Solve J·x = target over GF(2) using Gaussian elimination.
    Returns solution x or None if no solution.
    """
    m, n = J.shape
    # Augmented matrix
    Aug = np.hstack([J.copy() % 2, target_vector.reshape(-1, 1) % 2])

    pivot_cols = []
    rank = 0
    for col in range(n):
        pivot = -1
        for row in range(rank, m):
            if Aug[row, col] % 2 == 1:
                pivot = row; break
        if pivot == -1: continue
        Aug[[rank, pivot]] = Aug[[pivot, rank]]
        for row in range(m):
            if row != rank and Aug[row, col] % 2 == 1:
                Aug[row] = (Aug[row] + Aug[rank]) % 2
        pivot_cols.append(col)
        rank += 1

    # Check consistency
    for row in range(rank, m):
        if Aug[row, -1] % 2 == 1:
            return None  # No solution

    # Back-substitute
    x = np.zeros(n, dtype=np.int64)
    for i, col in enumerate(pivot_cols):
        x[col] = Aug[i, -1] % 2

    return x

def test_constructive_phase2(N=500):
    """
    Constructive Phase 2: solve for specific output bits.

    For each Wang pair (8 zeros):
    1. Compute Jacobian of target bits w.r.t. free DWs
    2. Set target: H[4..7] bits 28-31 should NOT flip (= 0 in δH)
    3. Solve linear system over GF(2)
    4. Apply solution and measure full δH
    """
    print("\n--- TEST 1: CONSTRUCTIVE PHASE 2 ---")

    solved = 0; improved = 0; total = 0
    dh_before = []; dh_after = []; target_hits = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, DWs = partial_wang(W0, W1, n_zeros=8)

        # Compute Jacobian
        J, targets, free_bits, Hf_base, Hn = compute_output_jacobian(Wn, DWs)

        # Target vector: we want δH[w]_bit_b = 0 for target bits
        # Current δH bits:
        target_vec = np.zeros(len(targets), dtype=np.int64)
        for ti, (w, b) in enumerate(targets):
            target_vec[ti] = ((Hn[w] ^ Hf_base[w]) >> b) & 1

        # Solve: find x such that J·x = target_vec (flip the bits that are currently 1)
        x = gf2_solve(J, target_vec)

        # Measure baseline δH
        Wf_base = [(Wn[i]+DWs[i])&MASK for i in range(16)]
        dh_b = sum(hw(Hn[i]^Hf_base[i]) for i in range(8))
        dh_before.append(dh_b)
        total += 1

        if x is not None:
            solved += 1

            # Apply solution
            DWs_fixed = list(DWs)
            for fi, (k, j) in enumerate(free_bits):
                if x[fi] == 1:
                    DWs_fixed[k] ^= (1 << j)

            Wf_fixed = [(Wn[i]+DWs_fixed[i])&MASK for i in range(16)]
            Hf_fixed = sha256_compress(Wf_fixed)
            dh_a = sum(hw(Hn[i]^Hf_fixed[i]) for i in range(8))
            dh_after.append(dh_a)

            # How many target bits are actually fixed?
            hits = 0
            for ti, (w, b) in enumerate(targets):
                if ((Hn[w] ^ Hf_fixed[w]) >> b) & 1 == 0:
                    hits += 1
            target_hits.append(hits)

            if dh_a < dh_b:
                improved += 1
        else:
            dh_after.append(dh_b)
            target_hits.append(0)

    db = np.array(dh_before); da = np.array(dh_after)
    th = np.array(target_hits)

    print(f"Total pairs: {total}")
    print(f"GF(2) system solvable: {solved}/{total} ({solved/total*100:.1f}%)")
    print(f"Improved δH: {improved}/{total} ({improved/total*100:.1f}%)")
    print(f"\nBefore construction: E[δH]={db.mean():.2f}, min={db.min()}")
    print(f"After construction:  E[δH]={da.mean():.2f}, min={da.min()}")
    print(f"Gain: {db.mean()-da.mean():+.2f}")
    print(f"\nTarget bits fixed: E={th.mean():.2f}/16, max={th.max()}/16")

    # The key question: does fixing 16 specific bits reduce TOTAL δH?
    # Or does it just shuffle bits (fix 16, break 16)?
    if da.mean() < db.mean() - 2:
        print(f"\n*** SIGNAL: Construction reduces δH by {db.mean()-da.mean():.1f} bits! ***")
    elif th.mean() > 8:
        print(f"\n*** SIGNAL: {th.mean():.0f}/16 target bits fixed! ***")
        print(f"But total δH {'improved' if da.mean()<db.mean() else 'worsened'}")

    return db, da, th

def test_iterative_construction(N=200):
    """
    Iterative: fix 16 bits → measure → choose new 16 targets → fix → repeat.
    Each iteration fixes 16 bits. After K iterations, 16K bits fixed?
    Or does fixing some break others?
    """
    print("\n--- TEST 2: ITERATIVE CONSTRUCTION ---")

    results = []
    for trial in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, DWs = partial_wang(W0, W1, n_zeros=8)
        Hn = sha256_compress(Wn)

        current_DWs = list(DWs)
        trajectory = []

        for iteration in range(5):
            # Current δH
            Wf = [(Wn[i]+current_DWs[i])&MASK for i in range(16)]
            Hf = sha256_compress(Wf)
            dh = sum(hw(Hn[i]^Hf[i]) for i in range(8))
            trajectory.append(dh)

            # Find worst 16 bits (those that ARE flipped)
            flipped = []
            for w in range(8):
                d = Hn[w] ^ Hf[w]
                for b in range(32):
                    if (d >> b) & 1:
                        flipped.append((w, b))

            if not flipped:
                break  # COLLISION!

            # Pick 16 target bits to fix (random subset of flipped)
            targets_to_fix = random.sample(flipped, min(16, len(flipped)))
            tw = [t[0] for t in targets_to_fix]
            tb = [t[1] for t in targets_to_fix]

            # Compute Jacobian for these specific targets
            J, targets, free_bits, _, _ = compute_output_jacobian(
                Wn, current_DWs,
                target_words=list(set(tw)),
                target_bits=list(set(tb)),
                free_words=range(10, 16)
            )

            # Target: flip all currently-flipped target bits to 0
            target_vec = np.ones(len(targets), dtype=np.int64)

            x = gf2_solve(J, target_vec)
            if x is not None:
                for fi, (k, j) in enumerate(free_bits):
                    if x[fi] == 1:
                        current_DWs[k] ^= (1 << j)

        # Final δH
        Wf = [(Wn[i]+current_DWs[i])&MASK for i in range(16)]
        Hf = sha256_compress(Wf)
        final_dh = sum(hw(Hn[i]^Hf[i]) for i in range(8))
        trajectory.append(final_dh)
        results.append(trajectory)

    # Analyze trajectories
    print(f"{'Iter':>4} | {'E[δH]':>8} | {'min':>5}")
    print("-"*25)
    for it in range(6):
        vals = [r[it] for r in results if len(r) > it]
        if vals:
            print(f"{it:>4} | {np.mean(vals):>8.2f} | {min(vals):>5}")

    # Did any reach δH < 50?
    finals = [r[-1] for r in results]
    print(f"\nFinal: E[δH]={np.mean(finals):.2f}, min={min(finals)}")

def test_full_budget_construction(N=200):
    """
    Use ALL 512 bits: no Wang zeros, pure constructive targeting.

    Instead of De=0 at intermediate rounds,
    directly target output bits for collision.
    """
    print("\n--- TEST 3: FULL-BUDGET CONSTRUCTION (no Wang) ---")

    results = []
    for _ in range(N):
        Wn = random_w16()
        DWs = [0]*16; DWs[0] = 1  # Minimal differential
        Hn = sha256_compress(Wn)

        # Compute Jacobian: all 16 DW words, all 256 output bits
        # This is a 256×512 GF(2) system
        Wf_base = [(Wn[i]+DWs[i])&MASK for i in range(16)]
        Hf_base = sha256_compress(Wf_base)

        # Build 256×512 Jacobian (expensive but doable)
        J = np.zeros((256, 512), dtype=np.int64)
        for k in range(16):
            for j in range(32):
                fi = k*32 + j
                DWs_p = list(DWs)
                DWs_p[k] ^= (1 << j)
                Wf_p = [(Wn[i]+DWs_p[i])&MASK for i in range(16)]
                Hf_p = sha256_compress(Wf_p)
                for w in range(8):
                    d = Hf_base[w] ^ Hf_p[w]
                    for b in range(32):
                        J[w*32+b][fi] = (d >> b) & 1

        # Target: make ALL δH bits = 0 (full collision)
        target = np.zeros(256, dtype=np.int64)
        for w in range(8):
            d = Hn[w] ^ Hf_base[w]
            for b in range(32):
                target[w*32+b] = (d >> b) & 1

        # Solve
        x = gf2_solve(J, target)

        if x is not None:
            # Apply solution
            DWs_sol = list(DWs)
            for k in range(16):
                for j in range(32):
                    if x[k*32+j] == 1:
                        DWs_sol[k] ^= (1 << j)

            Wf_sol = [(Wn[i]+DWs_sol[i])&MASK for i in range(16)]
            Hf_sol = sha256_compress(Wf_sol)
            dh = sum(hw(Hn[i]^Hf_sol[i]) for i in range(8))
            results.append(('solved', dh))
        else:
            results.append(('no_solution', None))

    solved = sum(1 for r in results if r[0] == 'solved')
    print(f"GF(2) full system solvable: {solved}/{N} ({solved/N*100:.1f}%)")

    if solved > 0:
        dhs = [r[1] for r in results if r[0] == 'solved']
        print(f"After GF(2) solution: E[δH]={np.mean(dhs):.2f}, min={min(dhs)}")

        if min(dhs) == 0:
            print("*** COLLISION FOUND!!! ***")
        elif min(dhs) < 50:
            print(f"*** NEAR-COLLISION: δH={min(dhs)}! ***")
        else:
            print("GF(2) solution doesn't give real collision — nonlinearity gap")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 37: CONSTRUCTIVE COLLISION ENGINEERING")
    print("Not search. Construction.")
    print("="*60)

    db, da, th = test_constructive_phase2(300)
    test_iterative_construction(150)
    test_full_budget_construction(100)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
