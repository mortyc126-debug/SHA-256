"""Per-bit OTOC anisotropy + Chimera attribution of SHA-256 scrambling.

Part 1: Measure OTOC per output bit vs round.
  Some output bits may scramble faster/slower.
  Potential link to methodology's T_IV_BIT0, schedule structure.

Part 2: Chimera OTOC attribution (replaces IT-2 artifact analysis).
  V0 vanilla: baseline
  V1 no_Sigma: Σ0/Σ1 → identity (kills rotational mixing)
  V2 no_sigma_sched: σ0/σ1 → identity in schedule
  V5 linear_chmaj: Ch, Maj → XOR (kills boolean nonlinearity)
  V7 almost_linear: V2 + V5 (fully linear except carry)
  → measure ||C(r)||_F² for each variant
  → determine which component dominates scrambling

Clean OTOC metric (not ⊘ROLL Pearson).
"""
import json, os, time
import numpy as np

import sha256_chimera as ch


OUT = '/home/user/SHA-256/research/min_entropy/otoc_anisotropy_chimera.json'


def state_at_r_chimera(M_arr, r, flags):
    """State at round r using chimera variant flags."""
    N = M_arr.shape[0]
    sm0 = (lambda x: x) if flags['no_sigma_sched'] else ch.sigma0
    sm1 = (lambda x: x) if flags['no_sigma_sched'] else ch.sigma1
    Sg0 = (lambda x: x) if flags['no_Sigma_compr'] else ch.Sigma0
    Sg1 = (lambda x: x) if flags['no_Sigma_compr'] else ch.Sigma1
    chf = ch.linear3_xor if flags['linear_chmaj'] else ch.Ch
    maf = ch.linear3_xor if flags['linear_chmaj'] else ch.Maj

    W = np.empty((N, 64), dtype=np.uint32)
    W[:, :16] = M_arr
    for t in range(16, 64):
        if t > r + 16: break
        W[:, t] = (sm1(W[:, t-2]) + W[:, t-7]
                   + sm0(W[:, t-15]) + W[:, t-16]) & ch.MASK

    iv = np.broadcast_to(np.array(ch.IV_VANILLA, dtype=np.uint32), (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    for t in range(r):
        T1 = (h + Sg1(e) + chf(e, f, g) + np.uint32(K_vals[t]) + W[:, t]) & ch.MASK
        T2 = (Sg0(a) + maf(a, b, c)) & ch.MASK
        h = g; g = f; f = e
        e = (d + T1) & ch.MASK
        d = c; c = b; b = a
        a = (T1 + T2) & ch.MASK
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint32)


def state_to_bits(state):
    bytes_be = state.view('<u1').reshape(state.shape[0], 8, 4)[:, :, ::-1].reshape(state.shape[0], 32)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :256]


def compute_otoc(r, flags, N=500, seed=42):
    rng = np.random.default_rng(seed)
    base_msgs = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)
    state_base = state_at_r_chimera(base_msgs, r, flags)
    bits_base = state_to_bits(state_base)
    C = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32; bit = 31 - (i % 32)
        flip_msgs = base_msgs.copy()
        flip_msgs[:, word] ^= np.uint32(1 << bit)
        state_flip = state_at_r_chimera(flip_msgs, r, flags)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# OTOC: per-bit anisotropy + chimera attribution")

    # Part 1: per-bit OTOC evolution for baseline SHA-256
    print("\n## PART 1: per-output-bit OTOC evolution (SHA-256 baseline)")
    flags_base = ch.VARIANTS['V0_vanilla']
    rounds = [4, 8, 12, 16, 20, 24]
    bit_scores = {}  # round → (256,) array of column |C|² sums
    for r in rounds:
        ts = time.time()
        C = compute_otoc(r, flags_base, N=300)
        # Column scores: sum of |C|² per output bit j
        col = (C ** 2).sum(axis=0)  # shape (256,)
        bit_scores[r] = col
        print(f"  r={r:>2}: ||C||² = {col.sum():.1f}, max_bit = {col.max():.3f}, "
              f"min_bit = {col.min():.3f}, std = {col.std():.3f}  ({time.time()-ts:.0f}s)")

    # Identify slowest-to-scramble bits
    print(f"\n## Bits with slowest scrambling (lowest decay from r=4 to r=20):")
    if 4 in bit_scores and 20 in bit_scores:
        decay_ratio = bit_scores[20] / (bit_scores[4] + 1e-6)
        # Top-10 bits with HIGHEST remaining score at r=20
        rem = bit_scores[20]
        top_idx = np.argsort(-rem)[:10]
        reg_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        for idx in top_idx:
            reg_w = idx // 32
            bit_in = 31 - (idx % 32)
            print(f"  {reg_names[reg_w]}20[{bit_in}]: ||C||² = {rem[idx]:.4f}, "
                  f"decay = {decay_ratio[idx]:.4f}")

    # Part 2: chimera attribution
    print("\n\n## PART 2: Chimera attribution of scrambling")
    variants = [
        ('V0_vanilla', {'no_sigma_sched': False, 'no_Sigma_compr': False, 'linear_chmaj': False}),
        ('V1_no_Sigma_compr', {'no_sigma_sched': False, 'no_Sigma_compr': True, 'linear_chmaj': False}),
        ('V2_no_sigma_sched', {'no_sigma_sched': True, 'no_Sigma_compr': False, 'linear_chmaj': False}),
        ('V5_linear_chmaj', {'no_sigma_sched': False, 'no_Sigma_compr': False, 'linear_chmaj': True}),
        ('V3_no_both_diffusion', {'no_sigma_sched': True, 'no_Sigma_compr': True, 'linear_chmaj': False}),
        ('V7_almost_linear', {'no_sigma_sched': True, 'no_Sigma_compr': True, 'linear_chmaj': True}),
    ]

    print(f"\n  {'Variant':<22}  " + "  ".join(f"{r:>7}" for r in rounds))
    variant_results = {}
    for name, flags in variants:
        row = {}
        row_str = f"  {name:<22}  "
        for r in rounds:
            C = compute_otoc(r, flags, N=300)
            F2 = float((C**2).sum())
            row[r] = F2
            row_str += f"{F2:>7.0f}  "
        variant_results[name] = row
        print(row_str)

    # Baseline comparison
    F_inf = 512 * 256 * 0.25 / 300  # theoretical for N=300
    print(f"\n  Theoretical RO limit (N=300): {F_inf:.2f}")

    print(f"\n## Scrambling speed comparison (smaller ||C||² faster):")
    print(f"  At r=24 (SHA-256 full scramble point):")
    for name in ['V0_vanilla', 'V1_no_Sigma_compr', 'V5_linear_chmaj', 'V2_no_sigma_sched', 'V7_almost_linear']:
        if name in variant_results and 24 in variant_results[name]:
            v = variant_results[name][24]
            excess = v - F_inf
            print(f"    {name:<22}: ||C||² = {v:.1f}  (excess over RO: {excess:+.1f})")

    # Which component slows scrambling MOST?
    print(f"\n## Attribution — excess scrambling at r=16 (early, pre-saturation):")
    if 16 in variant_results['V0_vanilla']:
        base_16 = variant_results['V0_vanilla'][16]
        print(f"  V0 vanilla:                  ||C||² = {base_16:.1f}")
        for name in ['V1_no_Sigma_compr', 'V2_no_sigma_sched', 'V5_linear_chmaj', 'V3_no_both_diffusion', 'V7_almost_linear']:
            if name in variant_results:
                diff = variant_results[name][16] - base_16
                sign = '+' if diff > 0 else ''
                print(f"  {name:<28}: ||C||² = {variant_results[name][16]:.1f}  "
                      f"({sign}{diff:.1f} vs V0)")

    out = {
        'part1_bit_scores': {str(r): bit_scores[r].tolist() for r in rounds},
        'part2_chimera': {k: {str(r): v for r, v in row.items()} for k, row in variant_results.items()},
        'theoretical_RO_limit_N300': F_inf,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
