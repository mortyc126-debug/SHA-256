"""Per-round Σ contribution to scrambling.

Replace Σ with identity ONLY at round k (keep Σ everywhere else),
measure OTOC ||C(r=24)||².

Round k where disabling Σ causes biggest increase = Σ most important there.
"""
import json, os, time
import numpy as np

import sha256_chimera as ch


OUT = '/home/user/SHA-256/research/min_entropy/otoc_sigma_per_round_results.json'


def state_at_r24_sigma_disabled_at_k(M_arr, k_disabled):
    N = M_arr.shape[0]
    r = 24
    W = np.empty((N, 64), dtype=np.uint32)
    W[:, :16] = M_arr
    for t in range(16, r + 1):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & ch.MASK
    iv = np.broadcast_to(np.array(ch.IV_VANILLA, dtype=np.uint32), (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    for t in range(r):
        if t == k_disabled:
            s0a = a; s1e = e  # identity
        else:
            s0a = ch.Sigma0(a); s1e = ch.Sigma1(e)
        T1 = (h + s1e + ch.Ch(e, f, g) + np.uint32(K_vals[t]) + W[:, t]) & ch.MASK
        T2 = (s0a + ch.Maj(a, b, c)) & ch.MASK
        h = g; g = f; f = e
        e = (d + T1) & ch.MASK
        d = c; c = b; b = a
        a = (T1 + T2) & ch.MASK
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint32)


def state_to_bits(state):
    bytes_be = state.view('<u1').reshape(state.shape[0], 8, 4)[:, :, ::-1].reshape(state.shape[0], 32)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :256]


def measure(k_disabled, N=200, seed=42):
    rng = np.random.default_rng(seed)
    base_msgs = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)
    state_base = state_at_r24_sigma_disabled_at_k(base_msgs, k_disabled)
    bits_base = state_to_bits(state_base)
    C = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32; bit = 31 - (i % 32)
        flip_msgs = base_msgs.copy()
        flip_msgs[:, word] ^= np.uint32(1 << bit)
        state_flip = state_at_r24_sigma_disabled_at_k(flip_msgs, k_disabled)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# Per-round Σ contribution (disable at single round k, measure r=24 OTOC)")

    N = 200
    F_inf = 512 * 256 * 0.25 / N
    print(f"  Theoretical RO limit: {F_inf:.2f}")
    print(f"  Baseline r=24: ||C||² ≈ 108 (scrambled)")
    print(f"  V1 all-Σ-removed at r=24: ||C||² ≈ 5935 (unscrambled)")
    print(f"  All-Σ excess over baseline: ~5827\n")

    print(f"  Computing baseline (k=-1 = none disabled)...")
    ts = time.time()
    C_base = measure(-1, N=N)
    F_base = float((C_base ** 2).sum())
    print(f"  baseline ||C||² = {F_base:.1f} ({time.time()-ts:.1f}s)")

    print(f"\n  k   ||C(r=24)||²   excess    rank")
    results = {}
    for k in range(24):
        ts = time.time()
        C = measure(k, N=N)
        F_sq = float((C ** 2).sum())
        excess = F_sq - F_base
        results[k] = {'frobenius_sq': F_sq, 'excess': excess}
        print(f"  {k:>2}     {F_sq:>10.1f}   {excess:>+8.1f}")

    # Rank by criticality
    print(f"\n## Rounds ranked by Σ-importance (excess when Σ disabled there):")
    by_excess = sorted(results.items(), key=lambda x: -x[1]['excess'])
    for rank, (k, info) in enumerate(by_excess[:10], 1):
        print(f"  #{rank}  round {k:>2}: excess = {info['excess']:+.1f}")

    total_excess = sum(info['excess'] for info in results.values())
    print(f"\n## Total single-round excess: {total_excess:.1f}")
    print(f"   Full Σ-removal excess: 5827")
    print(f"   Ratio: {total_excess/5827:.2f} (≥1 means super-additive)")

    # Identify critical zone
    thresh = 100
    critical = [k for k, v in results.items() if v['excess'] > thresh]
    print(f"\n## Critical rounds (excess > {thresh}): {critical}")

    out = {
        'N': N, 'baseline_frob_sq': F_base,
        'per_round': {str(k): v for k, v in results.items()},
        'total_excess': total_excess,
        'reference_all_sigma_excess': 5827,
        'critical_rounds': critical,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
