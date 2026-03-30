#!/usr/bin/env python3
"""
EXP 51: Carry-Aware Iterative Refinement (CAIR)

From exp50: quadratic Jacobian has FULL RANK 256.
From exp37: one-shot solve fails (50% decorrelation).

CAIR = damped Newton with recomputed quadratic Jacobian.
At each step:
1. Compute J_q at current point (rank=256)
2. Solve J_q·δx = target (tells us WHICH bits to flip)
3. DON'T flip ALL bits (that's one-shot, fails)
4. Flip bits ONE BY ONE, keep only those that ACTUALLY reduce δH
5. Recompute J_q at new point, repeat

This is NOT standard Newton (full step).
This is NOT greedy (no Jacobian guidance).
This is CAIR: Jacobian-GUIDED, empirically-VERIFIED, iterative.
"""
import sys, os, random, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def partial_wang_free(W0, W1, DW0, DW_free):
    Wn=[W0,W1]+[0]*14; DWs=[0]*16; DWs[0]=DW0
    Wf_tmp=[(Wn[i]+DWs[i])&MASK for i in range(16)]
    sn=sha256_rounds(Wn,3); sf=sha256_rounds(Wf_tmp,3)
    DWs[2]=(-de(sn,sf,3))&MASK
    for step in range(7):
        wi=step+3; dt=step+4
        Wfc=[(Wn[i]+DWs[i])&MASK for i in range(16)]
        tn=sha256_rounds(Wn,dt); tf=sha256_rounds(Wfc,dt)
        DWs[wi]=(-de(tn,tf,dt))&MASK
    for i in range(6): DWs[10+i]=DW_free[i]
    Wf=[(Wn[i]+DWs[i])&MASK for i in range(16)]
    return Wn, Wf

def dH_fast(Wn, Wf):
    Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
    return sum(hw(Hn[i]^Hf[i]) for i in range(8))

def pack_params(W0, W1, DW0, DW_free):
    """Pack 288 bits into parameter vector."""
    return (W0, W1, DW0, list(DW_free))

def flip_param(params, bit_idx):
    """Flip one of the 288 parameter bits."""
    W0, W1, DW0, DW_free = params[0], params[1], params[2], list(params[3])
    if bit_idx < 32:
        W0 ^= (1 << bit_idx)
    elif bit_idx < 64:
        W1 ^= (1 << (bit_idx-32))
    elif bit_idx < 96:
        DW0 ^= (1 << (bit_idx-64))
        if DW0 == 0: DW0 = 1
    else:
        dw_word = (bit_idx-96)//32
        dw_bit = (bit_idx-96)%32
        DW_free[dw_word] ^= (1 << dw_bit)
    return (W0, W1, DW0, DW_free)

def compute_jacobian_column(params, bit_idx, base_dH_bits):
    """Compute one column of the Jacobian (flip one bit, measure change)."""
    p_flipped = flip_param(params, bit_idx)
    try:
        Wn, Wf = partial_wang_free(*p_flipped)
        Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
        dH_bits = []
        for w in range(8):
            d=Hn[w]^Hf[w]
            for b in range(32):
                dH_bits.append((d>>b)&1)
        return np.array(dH_bits, dtype=np.int64) ^ base_dH_bits
    except:
        return np.zeros(256, dtype=np.int64)

def get_dH_bits(Wn, Wf):
    Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
    bits = []
    for w in range(8):
        d=Hn[w]^Hf[w]
        for b in range(32):
            bits.append((d>>b)&1)
    return np.array(bits, dtype=np.int64)

def cair_iteration(params, n_candidates=50):
    """
    One CAIR iteration:
    1. Compute Jacobian at current point (sample n_candidates columns)
    2. For each column: does flipping that bit reduce δH?
    3. Flip the BEST bit (most reduction)
    4. Return new params and new δH
    """
    W0, W1, DW0, DW_free = params
    try:
        Wn, Wf = partial_wang_free(W0, W1, DW0, DW_free)
    except:
        return params, 256

    current_dH = dH_fast(Wn, Wf)
    base_bits = get_dH_bits(Wn, Wf)

    # Sample random candidate bits to flip
    candidates = random.sample(range(288), min(n_candidates, 288))

    best_improvement = 0
    best_bit = -1

    for bit_idx in candidates:
        p_new = flip_param(params, bit_idx)
        try:
            Wn_new, Wf_new = partial_wang_free(*p_new)
            new_dH = dH_fast(Wn_new, Wf_new)
            improvement = current_dH - new_dH
            if improvement > best_improvement:
                best_improvement = improvement
                best_bit = bit_idx
                best_params = p_new
        except:
            pass

    if best_bit >= 0:
        return best_params, current_dH - best_improvement
    else:
        return params, current_dH

def cair_with_jacobian_guidance(params, n_jacobian=100, n_verify=30):
    """
    CAIR with Jacobian guidance:
    1. Compute partial Jacobian (n_jacobian columns)
    2. GF(2) solve → get priority ORDER for bit flips
    3. Try top-n_verify bits in priority order
    4. Accept best
    """
    W0, W1, DW0, DW_free = params
    try:
        Wn, Wf = partial_wang_free(W0, W1, DW0, DW_free)
    except:
        return params, 256

    base_bits = get_dH_bits(Wn, Wf)
    current_dH = int(base_bits.sum())

    # Compute Jacobian columns for random subset
    bit_indices = random.sample(range(288), min(n_jacobian, 288))
    J_cols = {}
    for bi in bit_indices:
        col = compute_jacobian_column(params, bi, base_bits)
        J_cols[bi] = col

    # Score each column: how many TARGET bits (currently=1) would it flip to 0?
    # Score = number of base=1 bits that column=1 (would flip)
    # MINUS number of base=0 bits that column=1 (would break)
    scores = {}
    for bi, col in J_cols.items():
        fix = np.sum(col & base_bits)       # Bits that are 1 and would flip to 0 (good)
        brk = np.sum(col & (1 - base_bits)) # Bits that are 0 and would flip to 1 (bad)
        scores[bi] = fix - brk

    # Sort by score (highest = most beneficial)
    ranked = sorted(scores.items(), key=lambda x: -x[1])

    # Try top candidates
    best_improvement = 0
    best_params = params

    for bi, score in ranked[:n_verify]:
        p_new = flip_param(params, bi)
        try:
            Wn_new, Wf_new = partial_wang_free(*p_new)
            new_dH = dH_fast(Wn_new, Wf_new)
            improvement = current_dH - new_dH
            if improvement > best_improvement:
                best_improvement = improvement
                best_params = p_new
        except:
            pass

    return best_params, current_dH - best_improvement

def test_cair(N_runs=30, max_steps=300):
    """Run CAIR and compare with baselines."""
    print(f"\n--- CAIR ({max_steps} steps × {N_runs} runs) ---")

    cair_results = []
    guided_results = []
    random_results = []

    for run in range(N_runs):
        # Same starting point for all 3 methods
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        DW0=random.randint(1,MASK)
        DW_free=[random.randint(0,MASK) for _ in range(6)]
        params = (W0, W1, DW0, DW_free)

        try:
            Wn, Wf = partial_wang_free(*params)
            start_dH = dH_fast(Wn, Wf)
        except:
            continue

        # Method 1: CAIR (random bit selection, no Jacobian)
        p1 = params; best1 = start_dH
        for step in range(max_steps):
            p1, dH1 = cair_iteration(p1, n_candidates=20)
            best1 = min(best1, dH1)

        # Method 2: Jacobian-guided CAIR
        p2 = params; best2 = start_dH
        for step in range(max_steps // 5):  # 5× fewer steps (each more expensive)
            p2, dH2 = cair_with_jacobian_guidance(p2, n_jacobian=60, n_verify=20)
            best2 = min(best2, dH2)

        # Method 3: Pure random search (same budget)
        best3 = start_dH
        for step in range(max_steps * 20):  # Same total evaluations
            p_rand = (random.randint(0,MASK), random.randint(0,MASK),
                     random.randint(1,MASK),
                     [random.randint(0,MASK) for _ in range(6)])
            try:
                Wn_r, Wf_r = partial_wang_free(*p_rand)
                best3 = min(best3, dH_fast(Wn_r, Wf_r))
            except: pass

        cair_results.append(best1)
        guided_results.append(best2)
        random_results.append(best3)

    ca=np.array(cair_results); ga=np.array(guided_results); ra=np.array(random_results)

    print(f"CAIR (random):     E[best]={ca.mean():.2f}, min={ca.min()}")
    print(f"CAIR (J-guided):   E[best]={ga.mean():.2f}, min={ga.min()}")
    print(f"Random search:     E[best]={ra.mean():.2f}, min={ra.min()}")

    print(f"\nCAIR vs Random: {ra.mean()-ca.mean():+.2f}")
    print(f"J-CAIR vs Random: {ra.mean()-ga.mean():+.2f}")
    print(f"J-CAIR vs CAIR: {ca.mean()-ga.mean():+.2f}")

    if ga.mean() < ca.mean() - 1:
        print(f"*** Jacobian guidance HELPS! ***")
    if ga.mean() < ra.mean() - 1:
        print(f"*** J-CAIR BEATS random search! ***")

def test_long_cair(N_runs=10, max_steps=1000):
    """Long CAIR runs — push toward minimum δH."""
    print(f"\n--- LONG CAIR ({max_steps} steps × {N_runs} runs) ---")

    for run in range(N_runs):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        DW0=random.randint(1,MASK)
        DW_free=[random.randint(0,MASK) for _ in range(6)]
        params = (W0, W1, DW0, DW_free)

        try:
            Wn, Wf = partial_wang_free(*params)
            best = dH_fast(Wn, Wf)
        except:
            continue

        trajectory = [best]

        for step in range(max_steps):
            # Alternate: 80% random CAIR, 20% J-guided
            if random.random() < 0.8:
                params, dH = cair_iteration(params, n_candidates=30)
            else:
                params, dH = cair_with_jacobian_guidance(params, n_jacobian=40, n_verify=15)
            best = min(best, dH)

            if step % 200 == 199:
                trajectory.append(best)

        print(f"  Run {run+1:>2}: start={trajectory[0]} → "
              f"{' → '.join(str(t) for t in trajectory[1:])} → final={best}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 51: CARRY-AWARE ITERATIVE REFINEMENT (CAIR)")
    print("Jacobian-guided, empirically-verified, iterative")
    print("="*60)

    test_cair(20, 200)
    test_long_cair(10, 800)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
