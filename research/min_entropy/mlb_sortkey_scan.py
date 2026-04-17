"""MLB Week 1 Day 1: scan sort-keys beyond g62.

Methodology focused on g62. But maybe a,b,c,d,e,f,h at round 62
OR any register at earlier/later rounds gives BETTER sort-key.

For each (register R ∈ {a..h}, round r ∈ {55, 58, 60, 62, 63}):
  Record R_r value for K=2M W[0] scan
  Sample 10K close pairs (|ΔR_r| < 10K) vs 10K far pairs (|ΔR_r| > 10M)
  Measure HW(Δstate1) difference

Best sort-key = biggest close-far gap.
If multiple registers give independent advantages → stack them.

This is systematic characterization, not just replication.
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_sortkey_scan.json')

K = 2_000_000
REG_NAMES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
ROUND_POINTS = [55, 58, 60, 62, 63]
N_PAIRS = 10_000


def popcount32_vec(arr):
    x = arr.astype(np.uint32)
    x = x - ((x >> 1) & 0x55555555)
    x = (x & 0x33333333) + ((x >> 2) & 0x33333333)
    x = (x + (x >> 4)) & 0x0f0f0f0f
    return ((x * np.uint32(0x01010101)) >> 24).astype(np.int32)


def compute_all_registers_and_state1(W0_start, W0_end):
    """For W0 range, compute all (a,b,c,d,e,f,g,h) at rounds in ROUND_POINTS,
    plus final state1. Returns dict {(reg, round): array} and state1 (N, 8)."""
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

    snapshots = {}  # (reg_name, round) -> array
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
        if t in ROUND_POINTS:
            for reg_name, val in zip(REG_NAMES, [a, b, c, d, e, f, g, h]):
                snapshots[(reg_name, t)] = val.copy()

    state1 = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    state1 = (state1 + ch.IV_VANILLA) & MASK
    return snapshots, state1


def measure_sort_key(keys, state1, n_close, n_far, rng):
    """Given 1D sort-key array and state1 (K, 8), measure close-far HW gap."""
    K_total = len(keys)
    sort_idx = np.argsort(keys)
    keys_sorted = keys[sort_idx]
    state1_sorted = state1[sort_idx]

    # Close pairs
    close_hw = []
    attempts = 0
    while len(close_hw) < n_close and attempts < 200_000:
        i = rng.integers(0, K_total - 1)
        diff = int(keys_sorted[i+1]) - int(keys_sorted[i])
        if diff < 10_000:
            hw = 0
            for w in range(8):
                hw += bin(int(state1_sorted[i, w]) ^ int(state1_sorted[i+1, w])).count('1')
            close_hw.append(hw)
        attempts += 1

    # Far pairs
    far_hw = []
    attempts = 0
    while len(far_hw) < n_far and attempts < 200_000:
        i = rng.integers(0, K_total)
        j = rng.integers(0, K_total)
        if i == j: continue
        diff = abs(int(keys[i]) - int(keys[j]))
        if diff > 10_000_000:
            hw = 0
            for w in range(8):
                hw += bin(int(state1[i, w]) ^ int(state1[j, w])).count('1')
            far_hw.append(hw)
        attempts += 1

    if not close_hw or not far_hw: return None
    c_arr, f_arr = np.array(close_hw), np.array(far_hw)
    return {
        'n_close': len(c_arr), 'n_far': len(f_arr),
        'close_mean': float(c_arr.mean()), 'close_std': float(c_arr.std(ddof=1)),
        'far_mean': float(f_arr.mean()), 'far_std': float(f_arr.std(ddof=1)),
        'gap': float(c_arr.mean() - f_arr.mean()),
    }


def main():
    t0 = time.time()
    print(f"# MLB Sort-Key Scan: all registers × rounds {ROUND_POINTS}")
    print(f"# K = {K:,} W[0], pairs per config: {N_PAIRS:,} close + {N_PAIRS:,} far")

    # Phase 1: compute all snapshots + state1
    print(f"\n# Phase 1: computing register snapshots...")
    ts = time.time()
    BATCH = 200_000
    snapshots = {(r, t): np.zeros(K, dtype=np.uint32) for r in REG_NAMES for t in ROUND_POINTS}
    state1_all = np.zeros((K, 8), dtype=np.uint32)
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        snaps, s1 = compute_all_registers_and_state1(start, end)
        for key, arr in snaps.items():
            snapshots[key][start:end] = arr
        state1_all[start:end] = s1
        if (start + BATCH) % 500_000 == 0:
            print(f"  {end:,}/{K:,} ({time.time()-ts:.0f}s)", flush=True)

    # Phase 2: evaluate each (register, round)
    print(f"\n# Phase 2: evaluating {len(REG_NAMES)*len(ROUND_POINTS)} sort-keys...")
    rng = np.random.default_rng(777)
    results = {}
    for round_t in ROUND_POINTS:
        print(f"\n## round = {round_t}")
        for reg in REG_NAMES:
            ts = time.time()
            r = measure_sort_key(snapshots[(reg, round_t)], state1_all, N_PAIRS, N_PAIRS, rng)
            if r is None:
                print(f"  {reg}{round_t}: FAILED"); continue
            results[f'{reg}{round_t}'] = r
            effect = 'STRONG' if r['gap'] < -5 else ('WEAK' if r['gap'] < -1 else 'NONE')
            print(f"  {reg}{round_t}: close={r['close_mean']:.2f} "
                  f"far={r['far_mean']:.2f} gap={r['gap']:+.2f} [{effect}] "
                  f"t={time.time()-ts:.0f}s", flush=True)

    # Phase 3: rank
    print(f"\n=== RANKED RESULTS (best sort-keys) ===")
    sorted_res = sorted(results.items(), key=lambda kv: kv[1]['gap'])
    print(f"{'sort-key':<10} {'close':>10} {'far':>10} {'gap':>10} {'z-diff':>10}")
    for key, r in sorted_res[:10]:
        se = math.sqrt(r['close_std']**2/r['n_close'] + r['far_std']**2/r['n_far'])
        z = r['gap'] / se if se > 0 else 0
        print(f"{key:<10} {r['close_mean']:>10.3f} {r['far_mean']:>10.3f} "
              f"{r['gap']:>+10.3f} {z:>+10.2f}")

    print(f"\n=== Best sort-key: {sorted_res[0][0]} with gap {sorted_res[0][1]['gap']:+.2f} bits ===")
    print(f"Methodology only tested g62 → gap 9.09 (our) or 18.2 (their claim)")
    print(f"Best in this scan gives effective birthday 2^({128 + sorted_res[0][1]['gap']/2:.2f})")

    out = {'K': K, 'N_pairs': N_PAIRS, 'rounds': ROUND_POINTS,
           'results': results,
           'best_key': sorted_res[0][0],
           'best_gap': sorted_res[0][1]['gap'],
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
