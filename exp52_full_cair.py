#!/usr/bin/env python3
"""
EXP 52: Full Freedom CAIR — 512 bits, all DW free

exp51: 288 bits → J-guided CAIR beats unguided (+1.5 bits)
but local search loses to global (-4.7 bits).

SCALING UP: 512 bits freedom (ALL DW[0..15] free, no Wang zeros).
More freedom → more directions to escape plateau.
Rank 512→256 = 256 (guaranteed).
Excess: 512-256 = 256 bits → rich landscape for CAIR navigation.

Also: MULTI-START CAIR — combine global exploration with local refinement.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def full_free_pair(W16_base, DW16):
    """Create pair with FULL freedom: Wn=W16_base, Wf=Wn+DW."""
    Wn = list(W16_base)
    Wf = [(Wn[i]+DW16[i])&MASK for i in range(16)]
    return Wn, Wf

def dH_full(W16_base, DW16):
    Wn, Wf = full_free_pair(W16_base, DW16)
    Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
    return sum(hw(Hn[i]^Hf[i]) for i in range(8))

def cair_step_full(W16_base, DW16, n_candidates=40):
    """One CAIR step with full 512-bit DW freedom."""
    current_dH = dH_full(W16_base, DW16)

    best_improvement = 0
    best_DW = DW16
    best_target = 'none'

    # Try flipping bits in DW (512 bits)
    candidates_dw = random.sample(range(512), min(n_candidates, 512))
    for bit_idx in candidates_dw:
        word = bit_idx // 32
        bit = bit_idx % 32
        DW_new = list(DW16)
        DW_new[word] ^= (1 << bit)
        if DW_new[0] == 0: DW_new[0] = 1  # Non-zero differential

        try:
            new_dH = dH_full(W16_base, DW_new)
            imp = current_dH - new_dH
            if imp > best_improvement:
                best_improvement = imp
                best_DW = DW_new
                best_target = f'DW[{word}]b{bit}'
        except:
            pass

    # Also try flipping bits in W16_base (another 512 bits)
    candidates_w = random.sample(range(512), min(n_candidates // 2, 512))
    for bit_idx in candidates_w:
        word = bit_idx // 32
        bit = bit_idx % 32
        W_new = list(W16_base)
        W_new[word] ^= (1 << bit)

        try:
            new_dH = dH_full(W_new, DW16)
            imp = current_dH - new_dH
            if imp > best_improvement:
                best_improvement = imp
                best_DW = DW16
                W16_base = W_new
                best_target = f'W[{word}]b{bit}'
        except:
            pass

    return W16_base, best_DW, current_dH - best_improvement

def jacobian_scored_step(W16_base, DW16, n_jacobian=80, n_verify=25):
    """J-guided CAIR step: score by Jacobian, verify empirically."""
    Wn, Wf = full_free_pair(W16_base, DW16)
    Hn=sha256_compress(Wn); Hf=sha256_compress(Wf)
    base_bits = []
    for w in range(8):
        d=Hn[w]^Hf[w]
        for b in range(32): base_bits.append((d>>b)&1)
    base_bits = np.array(base_bits, dtype=np.int64)
    current_dH = int(base_bits.sum())

    # Sample Jacobian columns (DW bits only for speed)
    candidates = random.sample(range(512), min(n_jacobian, 512))
    scores = {}

    for bit_idx in candidates:
        word = bit_idx // 32; bit = bit_idx % 32
        DW_p = list(DW16); DW_p[word] ^= (1<<bit)
        if DW_p[0]==0: DW_p[0]=1

        try:
            Wn_p, Wf_p = full_free_pair(W16_base, DW_p)
            Hn_p=sha256_compress(Wn_p); Hf_p=sha256_compress(Wf_p)
            p_bits = []
            for w in range(8):
                d=Hn_p[w]^Hf_p[w]
                for b in range(32): p_bits.append((d>>b)&1)
            p_bits = np.array(p_bits, dtype=np.int64)

            col = p_bits ^ base_bits
            fix = int(np.sum(col & base_bits))
            brk = int(np.sum(col & (1 - base_bits)))
            scores[bit_idx] = fix - brk
        except:
            pass

    # Verify top candidates
    ranked = sorted(scores.items(), key=lambda x: -x[1])

    best_improvement = 0
    best_DW = DW16

    for bi, score in ranked[:n_verify]:
        word = bi//32; bit = bi%32
        DW_p = list(DW16); DW_p[word] ^= (1<<bit)
        if DW_p[0]==0: DW_p[0]=1
        try:
            new_dH = dH_full(W16_base, DW_p)
            imp = current_dH - new_dH
            if imp > best_improvement:
                best_improvement = imp
                best_DW = DW_p
        except:
            pass

    return W16_base, best_DW, current_dH - best_improvement

def test_multistart_cair(N_starts=50, steps_per_start=100, budget_random=None):
    """
    Multi-start CAIR: global exploration + local J-guided refinement.
    """
    if budget_random is None:
        budget_random = N_starts * steps_per_start * 60  # Same total evals

    print(f"\n--- MULTI-START J-CAIR ({N_starts}×{steps_per_start} steps) ---")

    cair_bests = []

    for start in range(N_starts):
        W16 = random_w16()
        DW16 = [random.randint(0, MASK) for _ in range(16)]
        DW16[0] = max(DW16[0], 1)

        best = dH_full(W16, DW16)

        for step in range(steps_per_start):
            if step % 3 == 0:
                # J-guided step
                W16, DW16, dH = jacobian_scored_step(W16, DW16, n_jacobian=50, n_verify=15)
            else:
                # Random CAIR step
                W16, DW16, dH = cair_step_full(W16, DW16, n_candidates=30)
            best = min(best, dH)

        cair_bests.append(best)

    # Random baseline
    random_best = 256
    for _ in range(budget_random):
        W16 = random_w16()
        DW16 = [random.randint(0, MASK) for _ in range(16)]
        DW16[0] = max(DW16[0], 1)
        try:
            random_best = min(random_best, dH_full(W16, DW16))
        except: pass

    ca = np.array(cair_bests)
    birthday = 128 - 8*np.sqrt(2*np.log(budget_random))

    print(f"Multi-start J-CAIR: E[best]={ca.mean():.2f}, min={ca.min()}")
    print(f"Random search (N={budget_random}): best={random_best}")
    print(f"Birthday (N={budget_random}): ~{birthday:.1f}")

    if ca.min() < random_best:
        print(f"*** J-CAIR BEATS random: {ca.min()} < {random_best} ***")
    if ca.min() < birthday:
        print(f"*** J-CAIR BEATS birthday: {ca.min()} < {birthday:.0f} ***")

    return ca, random_best

def test_progressive_cair(N=10, max_steps=2000):
    """Long progressive CAIR runs with status reporting."""
    print(f"\n--- PROGRESSIVE CAIR ({max_steps} steps × {N} runs) ---")

    global_best = 256
    all_trajectories = []

    for run in range(N):
        W16 = random_w16()
        DW16 = [random.randint(0, MASK) for _ in range(16)]
        DW16[0] = max(DW16[0], 1)

        best = dH_full(W16, DW16)
        milestones = [best]
        stuck_count = 0

        for step in range(max_steps):
            old_best = best

            if step % 4 == 0:
                W16, DW16, dH = jacobian_scored_step(W16, DW16, n_jacobian=60, n_verify=20)
            else:
                W16, DW16, dH = cair_step_full(W16, DW16, n_candidates=35)
            best = min(best, dH)

            if best == old_best:
                stuck_count += 1
            else:
                stuck_count = 0

            # If stuck for 50 steps: random restart from current best + mutation
            if stuck_count >= 50:
                for i in range(16):
                    DW16[i] ^= random.randint(0, 0xFFFF)  # Small perturbation
                DW16[0] = max(DW16[0], 1)
                stuck_count = 0

            if step % 400 == 399:
                milestones.append(best)

        milestones.append(best)
        global_best = min(global_best, best)
        all_trajectories.append(milestones)

        print(f"  Run {run+1:>2}: {' → '.join(str(m) for m in milestones)}")

    print(f"\nGlobal best: {global_best}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 52: FULL FREEDOM CAIR (512 bits)")
    print("="*60)

    test_multistart_cair(30, 80, budget_random=30*80*60)
    test_progressive_cair(8, 1500)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
