"""MLB Week 1 — H[7]-collision orbit-birthday + validation of Q156.

Replicates methodology's H[7]-collision setup with N >> 500.
Key claim to validate: E[HW(ΔH[4]) | H[7]-collision] = 12.0 (4-bit compression).

Optimization: compute all H[7] into numpy array, sort, find duplicates.
Much faster than Python dict for large K.

K = 10M scans → expected ~12K H[7]-collision pairs (2M²/2^32).
Target: N=50K pairs for statistical power.
"""
import hashlib, math, os, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_week1_h7_orbit.json')


def sha256_batch_H7_and_full(W0_range_start, W0_range_end):
    """Compute H[7] for W0 in [start, end). Returns uint32 array of H[7] values."""
    N = W0_range_end - W0_range_start
    h7_arr = np.zeros(N, dtype=np.uint32)
    for idx, W0 in enumerate(range(W0_range_start, W0_range_end)):
        m = W0.to_bytes(4, 'big') + b'\x00' * 60
        d = hashlib.sha256(m).digest()
        h7_arr[idx] = int.from_bytes(d[28:32], 'big')
    return h7_arr


def sha256_full_H(W0):
    m = W0.to_bytes(4, 'big') + b'\x00' * 60
    d = hashlib.sha256(m).digest()
    return np.array([int.from_bytes(d[i*4:(i+1)*4], 'big') for i in range(8)], dtype=np.uint32)


def popcount32(x):
    x = int(x)
    x = x - ((x >> 1) & 0x55555555)
    x = (x & 0x33333333) + ((x >> 2) & 0x33333333)
    x = (x + (x >> 4)) & 0x0f0f0f0f
    return (x * 0x01010101 & 0xffffffff) >> 24


def main():
    t0 = time.time()
    K = 10_000_000
    print(f"# MLB Week 1: H[7]-collision orbit-birthday")
    print(f"# Scanning K = {K:,} W[0] values (W[1..15] = 0)")

    # Phase 1: compute all H[7] values into numpy
    print(f"\n# Phase 1: computing {K:,} SHA-256 hashes...")
    ts = time.time()
    h7_arr = np.zeros(K, dtype=np.uint32)
    BATCH = 500_000
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        h7_arr[start:end] = sha256_batch_H7_and_full(start, end)
        el = time.time() - ts
        rate = (end / el) if el > 0 else 0
        print(f"  {end:,}/{K:,} ({el:.0f}s, {rate:.0f} H/s)", flush=True)

    # Phase 2: find H[7] collisions via sort
    print(f"\n# Phase 2: finding collisions via sort...")
    ts = time.time()
    sort_idx = np.argsort(h7_arr)
    h7_sorted = h7_arr[sort_idx]

    # Find consecutive equal H[7] values
    pairs = []  # (W0_a, W0_b, h7)
    i = 0
    while i < K - 1:
        if h7_sorted[i] == h7_sorted[i+1]:
            # Start of collision block
            block_start = i
            while i < K - 1 and h7_sorted[i] == h7_sorted[i+1]:
                i += 1
            block_end = i  # inclusive
            block_indices = sort_idx[block_start:block_end+1]
            h7_val = int(h7_sorted[block_start])
            # Add all pairs from block
            for a in range(len(block_indices)):
                for b in range(a+1, len(block_indices)):
                    pairs.append((int(block_indices[a]), int(block_indices[b]), h7_val))
        i += 1
    print(f"  time {time.time()-ts:.0f}s, total pairs: {len(pairs):,}")

    if len(pairs) == 0:
        print("NO COLLISIONS — increase K"); return

    # Phase 3: full H computation for each pair
    N_pairs = min(len(pairs), 50_000)
    pairs_used = pairs[:N_pairs]
    print(f"\n# Phase 3: computing full ΔH for {N_pairs:,} pairs...")
    ts = time.time()
    hw_deltas = np.zeros((N_pairs, 8), dtype=np.int32)
    for idx, (W0_a, W0_b, h7_val) in enumerate(pairs_used):
        H_a = sha256_full_H(W0_a)
        H_b = sha256_full_H(W0_b)
        for i in range(8):
            hw_deltas[idx, i] = popcount32(int(H_a[i]) ^ int(H_b[i]))
        if (idx + 1) % 10000 == 0:
            print(f"  {idx+1:,}/{N_pairs:,} ({time.time()-ts:.0f}s)", flush=True)
    assert (hw_deltas[:, 7] == 0).all(), f"H[7] collisions must have ΔH[7]=0, got max={hw_deltas[:,7].max()}"

    # Phase 4: stats
    print(f"\n=== MLB Week 1 Results (N = {N_pairs:,} H[7]-collision pairs) ===")
    print(f"{'word':<8} {'mean HW(ΔH)':>13} {'std':>7} {'Δ from 16':>11} {'z-stat':>10}")
    results = {}
    for i in range(8):
        m = float(hw_deltas[:, i].mean())
        s = float(hw_deltas[:, i].std(ddof=1)) if N_pairs > 1 else 0
        delta = m - 16.0
        se = s / math.sqrt(N_pairs) if s > 0 else 0
        z = delta / se if se > 0 else 0
        marker = '★' if abs(z) > 5 else ('⚠' if abs(z) > 3 else ' ')
        print(f"{marker} H[{i}]   {m:>13.4f} {s:>7.3f} {delta:>+11.4f} {z:>+10.2f}")
        results[f'H[{i}]'] = {'mean': m, 'std': s, 'delta': delta, 'z': z}

    print(f"\n=== Methodology predictions (N=500 from П-1253..П-1300) ===")
    meth = {'H[0]': 19.0, 'H[1]': 17.0, 'H[2]': 17.0, 'H[3]': 15.0,
            'H[4]': 12.0, 'H[5]': 16.0, 'H[6]': 16.0, 'H[7]': 0.0}
    print(f"{'word':<8} {'our N='+str(N_pairs):>14} {'meth N=500':>13} {'agree?':>10}")
    for i in range(8):
        our = results[f'H[{i}]']['mean']
        m = meth[f'H[{i}]']
        agree = '★★★' if abs(our - m) < 0.15 else ('✓' if abs(our - m) < 0.3 else ('~' if abs(our - m) < 1.0 else 'DIFFER'))
        print(f"H[{i}]    {our:>14.4f} {m:>13.1f} {agree:>10}")

    total_compression = sum(16.0 - results[f'H[{i}]']['mean'] for i in range(7))  # H[0..6]
    print(f"\nTotal compression H[0..6]:  {total_compression:+.3f} bits  (methodology: +17.0)")
    print(f"Effective birthday exponent: 2^({128 - total_compression/2:.2f}) instead of 2^128")

    out = {'N_pairs': N_pairs, 'K_scanned': K,
           'per_word': results, 'methodology': meth,
           'total_compression': total_compression,
           'effective_birthday_exp': 128 - total_compression/2,
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
