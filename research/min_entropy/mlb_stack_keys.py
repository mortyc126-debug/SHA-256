"""MLB Week 1 Day 2: stack multi-sort-keys — test independence.

From Day 1: all 8 round-63 registers give ~9-bit gap. Are they redundant
copies of same signal, or genuinely independent?

Test: for sort by PAIR of keys (joint sort) or MAJORITY-vote on keys:
  close = all N keys within threshold simultaneously
  far = all N keys exceed threshold
  Measure gap.

If gap > 9 → signals stack → better distinguisher possible.
If gap = 9 → duplicates (expected from shift-register structure).

Also test:
- d63 AND e63 (fresh values — a-branch and e-branch)
- g62 AND h63 (cross-register cross-round)
- All 8 round-63 registers combined
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_stack_keys.json')

K = 2_000_000
REG_NAMES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']


def compute_registers_at_63_and_62_and_state1(W0_start, W0_end):
    N = W0_end - W0_start
    block1 = np.zeros((N, 16), dtype=ch.U32)
    block1[:, 0] = np.arange(W0_start, W0_end, dtype=ch.U32)
    U32, MASK = ch.U32, ch.MASK
    W = np.empty((N, 64), dtype=U32); W[:, :16] = block1
    for t in range(16, 64):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    iv = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    r62 = {}; r63 = {}
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
        if t == 62:
            for n, v in zip(REG_NAMES, [a, b, c, d, e, f, g, h]):
                r62[n] = v.copy()
        if t == 63:
            for n, v in zip(REG_NAMES, [a, b, c, d, e, f, g, h]):
                r63[n] = v.copy()
    state1 = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    state1 = (state1 + ch.IV_VANILLA) & MASK
    return r62, r63, state1


def measure_joint(keys_list, state1, threshold_close, threshold_far, n_target, rng):
    """Sample close/far pairs where ALL keys satisfy threshold simultaneously."""
    K_total = len(keys_list[0])
    close_hw = []; far_hw = []
    attempts = 0
    while (len(close_hw) < n_target or len(far_hw) < n_target) and attempts < 2_000_000:
        i = rng.integers(0, K_total)
        j = rng.integers(0, K_total)
        if i == j: attempts += 1; continue
        diffs = [abs(int(k[i]) - int(k[j])) for k in keys_list]
        max_d = max(diffs)
        min_d = min(diffs)
        if max_d < threshold_close and len(close_hw) < n_target:
            hw = 0
            for w in range(8):
                hw += bin(int(state1[i, w]) ^ int(state1[j, w])).count('1')
            close_hw.append(hw)
        elif min_d > threshold_far and len(far_hw) < n_target:
            hw = 0
            for w in range(8):
                hw += bin(int(state1[i, w]) ^ int(state1[j, w])).count('1')
            far_hw.append(hw)
        attempts += 1
    return close_hw, far_hw


def main():
    t0 = time.time()
    print(f"# MLB Stack Keys: test independence of sort-keys")

    print(f"\n# Computing registers at round 62, 63, and state1 for K={K:,}...")
    ts = time.time()
    BATCH = 200_000
    r62_all = {n: np.zeros(K, dtype=np.uint32) for n in REG_NAMES}
    r63_all = {n: np.zeros(K, dtype=np.uint32) for n in REG_NAMES}
    state1_all = np.zeros((K, 8), dtype=np.uint32)
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        r62, r63, s1 = compute_registers_at_63_and_62_and_state1(start, end)
        for n in REG_NAMES:
            r62_all[n][start:end] = r62[n]
            r63_all[n][start:end] = r63[n]
        state1_all[start:end] = s1
    print(f"  time: {time.time()-ts:.0f}s")

    rng = np.random.default_rng(0xBEEF)
    N_PAIRS = 10_000

    test_configs = [
        ('g62 (methodology)', [r62_all['g']]),
        ('d63 (best from scan)', [r63_all['d']]),
        ('a-branch stack (a63, b63, c63)', [r63_all['a'], r63_all['b'], r63_all['c']]),
        ('e-branch stack (e63, f63, g63, h63)', [r63_all['e'], r63_all['f'], r63_all['g'], r63_all['h']]),
        ('all 8 round-63', [r63_all[n] for n in REG_NAMES]),
        ('a63 + e63 (both fresh branches)', [r63_all['a'], r63_all['e']]),
        ('g62 + d63 (cross-round)', [r62_all['g'], r63_all['d']]),
        ('d63 + e63 + f63', [r63_all['d'], r63_all['e'], r63_all['f']]),
    ]

    results = {}
    print(f"\n{'config':<45} {'N_close':>8} {'N_far':>8} {'close_mean':>11} {'far_mean':>10} {'gap':>8}")
    for label, keys_list in test_configs:
        ts = time.time()
        close, far = measure_joint(keys_list, state1_all, 10_000, 10_000_000, N_PAIRS, rng)
        if not close or not far:
            print(f"  {label}: FAILED (could not sample)")
            continue
        c = np.array(close); f = np.array(far)
        cm, fm = float(c.mean()), float(f.mean())
        cs, fs = float(c.std(ddof=1)), float(f.std(ddof=1))
        gap = cm - fm
        z = gap / math.sqrt(cs**2/len(c) + fs**2/len(f))
        results[label] = {'n_close': len(c), 'n_far': len(f),
                          'close_mean': cm, 'far_mean': fm, 'gap': gap, 'z': z}
        effect = '★' if abs(gap) > 15 else ('+' if abs(gap) > 10 else '-')
        print(f"{effect} {label:<43} {len(c):>8} {len(f):>8} {cm:>11.3f} {fm:>10.3f} {gap:>+8.3f}")

    # Summary
    print(f"\n=== ANALYSIS ===")
    gaps = [(lbl, r['gap']) for lbl, r in results.items()]
    best_lbl, best_gap = min(gaps, key=lambda x: x[1])
    print(f"Best single: g62 = {results['g62 (methodology)']['gap']:+.2f}")
    print(f"Best stack:  {best_lbl} = {best_gap:+.2f}")
    print(f"Stacking gain over g62: {best_gap - results['g62 (methodology)']['gap']:+.2f} bits")
    if abs(best_gap) > abs(results['g62 (methodology)']['gap']) + 2:
        print(f"  → Signals ARE somewhat independent — combined > single")
        print(f"  → Effective birthday: 2^({128 + best_gap/2:.2f})")
    else:
        print(f"  → Signals appear REDUNDANT — combined ≈ single")

    with open(OUT, 'w') as f:
        json.dump({'K': K, 'N_PAIRS': N_PAIRS, 'results': results,
                   'best_stack': best_lbl, 'best_gap': best_gap}, f, indent=2)
    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
