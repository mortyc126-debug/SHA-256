"""MLB Week 1 v2: CORRECTED — orbit-birthday on state1 (block-1 output), not final hash.

Initial misinterpretation: methodology's 'H[7]' refers to state1[7] (after
block-1 compression, before padding block), not final SHA-256 hash word.

Verified: W1=0x20ebc576, W2=0xb76cb0b7 both have state1[7] = 0x286e222c
(matches methodology's claimed collision value).

Re-running Q156 validation with correct state definition:
For each W0, compute state1 = compress(IV, block1_of_W0_padded) — 8 uint32.
Collide on state1[7], measure ΔHW on other state1[i].

Methodology predictions (N=500):
  E[HW(Δstate1[0])] = 19.0 (anticorrelation)
  E[HW(Δstate1[4])] = 12.0 (4-bit compression)
  E[HW(Δstate1[3])] = 15.0
  ...

Target: verify at N=50,000 pairs.
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_week1_state1.json')


def state1_batch(W0_start, W0_end):
    """Return state1 (N, 8) uint32 for W0 in [start, end), W[1..15]=0."""
    N = W0_end - W0_start
    block1 = np.zeros((N, 16), dtype=ch.U32)
    block1[:, 0] = np.arange(W0_start, W0_end, dtype=ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), block1,
                     ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return s1


def popcount32_vec(arr):
    """Vectorized popcount on uint32 array."""
    x = arr.astype(np.uint32)
    x = x - ((x >> 1) & 0x55555555)
    x = (x & 0x33333333) + ((x >> 2) & 0x33333333)
    x = (x + (x >> 4)) & 0x0f0f0f0f
    return ((x * np.uint32(0x01010101)) >> 24).astype(np.int32)


def main():
    t0 = time.time()
    K = 10_000_000
    print(f"# MLB Week 1 v2: state1[7]-collision orbit-birthday")
    print(f"# Scanning K = {K:,} W[0] values, W[1..15] = 0")

    # Phase 1: compute state1 for all W0
    print(f"\n# Phase 1: computing {K:,} block-1 compressions (vectorized numpy)...")
    ts = time.time()
    BATCH = 200_000
    state1_7_arr = np.zeros(K, dtype=np.uint32)
    # We only need state1[7] initially
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        s1_batch = state1_batch(start, end)
        state1_7_arr[start:end] = s1_batch[:, 7]
        if (start + BATCH) % 2_000_000 == 0:
            el = time.time() - ts
            print(f"  {end:,}/{K:,} ({el:.0f}s, {end/el:.0f} H/s)", flush=True)
    print(f"  time: {time.time()-ts:.0f}s")

    # Phase 2: find state1[7]-collisions
    print(f"\n# Phase 2: finding state1[7] collisions via sort...")
    ts = time.time()
    sort_idx = np.argsort(state1_7_arr)
    sorted_vals = state1_7_arr[sort_idx]
    pairs = []
    i = 0
    while i < K - 1:
        if sorted_vals[i] == sorted_vals[i+1]:
            block_start = i
            while i < K - 1 and sorted_vals[i] == sorted_vals[i+1]:
                i += 1
            block_end = i
            indices = sort_idx[block_start:block_end+1]
            val = int(sorted_vals[block_start])
            for a in range(len(indices)):
                for b in range(a+1, len(indices)):
                    pairs.append((int(indices[a]), int(indices[b]), val))
        i += 1
    print(f"  time {time.time()-ts:.0f}s, pairs: {len(pairs):,}")

    if len(pairs) == 0:
        print("NO COLLISIONS — increase K"); return

    N_pairs = min(len(pairs), 50_000)
    pairs_used = pairs[:N_pairs]
    print(f"\n# Phase 3: computing full state1 for {N_pairs:,} pairs...")
    ts = time.time()

    # Free the big array
    del state1_7_arr, sort_idx, sorted_vals

    # For each pair, recompute state1 for both W0s
    # Batch for numpy efficiency: collect all W0 values, compute, then pair up
    W0s_a = np.array([p[0] for p in pairs_used], dtype=np.uint32)
    W0s_b = np.array([p[1] for p in pairs_used], dtype=np.uint32)

    def compute_state1_for_W0s(W0_arr):
        N = len(W0_arr)
        block1 = np.zeros((N, 16), dtype=ch.U32)
        block1[:, 0] = W0_arr
        s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), block1,
                         ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
        return s1

    s1_A = compute_state1_for_W0s(W0s_a)
    s1_B = compute_state1_for_W0s(W0s_b)
    print(f"  state1 computation: {time.time()-ts:.0f}s")

    # Compute ΔHW for each word
    hw_deltas = np.zeros((N_pairs, 8), dtype=np.int32)
    for i in range(8):
        diff = s1_A[:, i] ^ s1_B[:, i]
        hw_deltas[:, i] = popcount32_vec(diff)

    # Verify state1[7] collision
    assert (hw_deltas[:, 7] == 0).all(), \
        f"state1[7] collisions must have ΔHW=0, max={hw_deltas[:,7].max()}"

    # Phase 4: statistics
    print(f"\n=== MLB Week 1 v2 Results (N = {N_pairs:,} state1[7]-collision pairs) ===")
    print(f"{'word':<8} {'mean HW(Δ)':>12} {'std':>7} {'Δ from 16':>11} {'z-stat':>10}")
    results = {}
    for i in range(8):
        m = float(hw_deltas[:, i].mean())
        s = float(hw_deltas[:, i].std(ddof=1)) if N_pairs > 1 else 0
        delta = m - 16.0
        se = s / math.sqrt(N_pairs) if s > 0 else 0
        z = delta / se if se > 0 else 0
        marker = '★★★' if abs(z) > 5 else ('⚠' if abs(z) > 3 else ' ')
        print(f"{marker} state1[{i}]  {m:>9.4f} {s:>7.3f} {delta:>+11.4f} {z:>+10.2f}")
        results[f'state1[{i}]'] = {'mean': m, 'std': s, 'delta': delta, 'z': z}

    print(f"\n=== Methodology predictions (N=500) ===")
    meth = {'state1[0]': 19.0, 'state1[1]': 17.0, 'state1[2]': 17.0, 'state1[3]': 15.0,
            'state1[4]': 12.0, 'state1[5]': 16.0, 'state1[6]': 16.0, 'state1[7]': 0.0}
    print(f"{'word':<10} {'our N':>14} {'meth N=500':>12} {'agree?':>10}")
    for i in range(8):
        our = results[f'state1[{i}]']['mean']
        m = meth[f'state1[{i}]']
        agree = '★★★' if abs(our - m) < 0.15 else ('✓' if abs(our - m) < 0.3 else ('~' if abs(our - m) < 1.0 else 'DIFFER'))
        print(f"state1[{i}] {our:>14.4f} {m:>12.1f} {agree:>10}")

    total = sum(16.0 - results[f'state1[{i}]']['mean'] for i in range(7))
    print(f"\nTotal compression state1[0..6]:  {total:+.3f} bits  (methodology claims +17.0)")
    print(f"Effective birthday: 2^{128 - total/2:.2f} (methodology: 2^119.5)")

    out = {'N_pairs': N_pairs, 'K_scanned': K, 'state_def': 'state1 (block-1 output)',
           'per_word': results, 'methodology': meth,
           'total_compression': total,
           'effective_birthday_exp': 128 - total/2,
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total time: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
