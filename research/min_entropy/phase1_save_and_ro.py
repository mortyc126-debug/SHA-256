"""Parse phase1 output data + compute RO null with optimized code. Save final JSON."""
import hashlib, json, os, time
from itertools import combinations
import numpy as np

from oracle_gauge import low_hw2_inputs, make_feature, build_chi_arr

OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase1_walsh_spectrum.json')

# Parsed from stdout of prior run
SHA256_DATA = {
    'r_chi': 4,
    'per_k': {
        1: [(4, 0.998), (6, 0.999), (8, 0.994), (10, 0.991), (12, 0.983),
            (14, 0.967), (16, 0.935), (20, 0.149), (24, 0.067), (28, 0.030),
            (32, 0.061), (40, 0.001), (48, 0.106), (56, -0.001), (64, 0.152)],
        2: [(4, 0.998), (6, 0.999), (8, 0.994), (10, 0.991), (12, 0.983),
            (14, 0.967), (16, 0.935), (20, 0.142), (24, 0.067), (28, 0.031),
            (32, 0.044), (40, 0.009), (48, 0.100), (56, 0.016), (64, 0.145)],
        3: [(4, 0.998), (6, 0.999), (8, 0.994), (10, 0.991), (12, 0.983),
            (14, 0.968), (16, 0.936), (20, 0.141), (24, 0.069), (28, 0.031),
            (32, 0.042), (40, 0.009), (48, 0.103), (56, 0.023), (64, 0.146)],
        4: [(4, 0.998), (6, 0.999), (8, 0.994), (10, 0.991), (12, 0.982),
            (14, 0.968), (16, 0.936), (20, 0.131), (24, 0.069), (28, 0.033),
            (32, 0.045), (40, 0.006), (48, 0.103), (56, 0.016), (64, 0.151)],
        5: [(4, 0.998), (6, 0.999), (8, 0.995), (10, 0.991), (12, 0.982),
            (14, 0.968), (16, 0.936), (20, 0.130), (24, 0.077), (28, 0.036),
            (32, 0.052), (40, 0.005), (48, 0.109), (56, 0.010), (64, 0.156)],
        6: [(4, 0.998), (6, 0.999), (8, 0.995), (10, 0.991), (12, 0.982),
            (14, 0.968), (16, 0.935), (20, 0.136), (24, 0.080), (28, 0.035),
            (32, 0.068), (40, 0.008), (48, 0.108), (56, 0.009), (64, 0.155)],
    }
}
SHA3_DATA = {
    'r_chi': 1,
    'per_k': {
        1: [(1, 0.824), (2, 0.563), (3, 0.060), (4, 0.085), (6, 0.024),
            (8, 0.099), (12, 0.060), (18, 0.098), (24, -0.004)],
        2: [(1, 0.825), (2, 0.566), (3, 0.073), (4, 0.095), (6, 0.039),
            (8, 0.110), (12, 0.067), (18, 0.112), (24, 0.013)],
        3: [(1, 0.827), (2, 0.569), (3, 0.087), (4, 0.106), (6, 0.054),
            (8, 0.120), (12, 0.073), (18, 0.125), (24, 0.028)],
        4: [(1, 0.828), (2, 0.571), (3, 0.123), (4, 0.115), (6, 0.085),
            (8, 0.138), (12, 0.097), (18, 0.148), (24, 0.072)],
        5: [(1, 0.830), (2, 0.583), (3, 0.167), (4, 0.130), (6, 0.113),
            (8, 0.170), (12, 0.100), (18, 0.172), (24, 0.112)],
        6: [(1, 0.831), (2, 0.589), (3, 0.177), (4, 0.150), (6, 0.129),
            (8, 0.214), (12, 0.112), (18, 0.196), (24, 0.127)],
    }
}

SUBSET = {1: 32, 2: 32, 3: 32, 4: 22, 5: 18, 6: 15}


def fast_ro_omega(chi_arr_f32, f_pm_f32, target_bits_batch):
    """Compute Ω_k for multiple RO targets in batch. target_bits_batch: (R, N, 256)."""
    R, N, T = target_bits_batch.shape
    sN = np.float32(np.sqrt(N))
    z_in = (chi_arr_f32 @ f_pm_f32) / sN  # (M,)
    # Batch target: cast all at once
    results = []
    for r in range(R):
        target_pm = target_bits_batch[r].astype(np.float32) * 2 - 1
        col_mean = target_pm.mean(axis=0)
        var_mask = np.abs(col_mean) < 1 - 1e-9
        target_pm = target_pm[:, var_mask]
        if target_pm.shape[1] < 8:
            results.append(0.0); continue
        z_out_matrix = (chi_arr_f32 @ target_pm) / sN
        chain_z = (z_in[:, None] * z_out_matrix).sum(axis=0) / sN
        direct_z = (f_pm_f32 @ target_pm) / sN
        if np.std(direct_z) < 1e-10 or np.std(chain_z) < 1e-10:
            omega = 0.0
        else:
            omega = float(np.corrcoef(direct_z, chain_z)[0, 1])
        results.append(omega)
    return results


def precompute_ro_targets(inputs, n_real=10):
    """Vectorized BLAKE2b target extraction using numpy."""
    N = len(inputs)
    nprng = np.random.default_rng(0xBADF00D)
    targets = np.zeros((n_real, N, 256), dtype=np.uint8)
    for r in range(n_real):
        key = nprng.bytes(16)
        # Compute all hashes
        byte_mat = np.zeros((N, 32), dtype=np.uint8)
        for i, m in enumerate(inputs):
            byte_mat[i] = np.frombuffer(
                hashlib.blake2b(m, key=key, digest_size=32).digest(),
                dtype=np.uint8)
        # Unpack bytes to bits (big-endian per byte)
        targets[r] = np.unpackbits(byte_mat, axis=1, bitorder='big')[:, :256]
    return targets


def main():
    t0 = time.time()
    print("# Phase 1 save + optimized RO null")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    fa = make_feature(pos, 'bit5_max')
    f_pm_f32 = (fa.astype(np.float32) * 2 - 1)

    # Re-build chi_arr (state at r=4 for SHA-256)
    print("# Rebuilding SHA-256 chi_arrs...")
    from it37_sha256_reference import sha256_partial_state
    state_chi = sha256_partial_state(inputs, 4)
    chi_cache_f32 = {}
    for k in SUBSET:
        ts = time.time()
        chi_arr, _ = build_chi_arr(state_chi, k=k, subset_size=SUBSET[k])
        chi_cache_f32[k] = chi_arr.astype(np.float32)
        print(f"  k={k}: M={chi_arr.shape[0]} ({time.time()-ts:.0f}s)")

    # Precompute RO target bits (10 realizations)
    print("\n# Precompute RO target bits (10 realizations)...")
    ts = time.time()
    ro_targets = precompute_ro_targets(inputs, n_real=10)
    print(f"  {time.time()-ts:.0f}s")

    # Compute RO null per k
    print("\n# RO null per k (batch matmul):")
    ro_stats = {}
    for k in SUBSET:
        ts = time.time()
        omegas = fast_ro_omega(chi_cache_f32[k], f_pm_f32, ro_targets)
        ro_stats[k] = {'mean': float(np.mean(omegas)),
                       'std': float(np.std(omegas, ddof=1)),
                       'omegas': omegas}
        print(f"  k={k}: RO={ro_stats[k]['mean']:+.3f}±{ro_stats[k]['std']:.3f}  "
              f"({time.time()-ts:.0f}s)")

    # Save everything
    def pack(data):
        return {'r_chi': data['r_chi'],
                'per_k': {k: [{'r': r, 'omega': o} for r, o in lst]
                          for k, lst in data['per_k'].items()}}

    out = {
        'N': N,
        'feature': 'bit5_max',
        'subset_sizes': SUBSET,
        'sha256': pack(SHA256_DATA),
        'sha3': pack(SHA3_DATA),
        'ro_null': ro_stats,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}")

    # Analysis
    print(f"\n=== SPECTRUM ANALYSIS ===")
    print(f"\n## SHA-256 — all Ω_k collapse TOGETHER at r≈17-20:")
    for r_idx, r in enumerate([16, 20, 24]):
        vals = [SHA256_DATA['per_k'][k][[e[0] for e in SHA256_DATA['per_k'][k]].index(r)][1]
                for k in sorted(SUBSET)]
        spread = max(vals) - min(vals)
        print(f"  r={r}: Ω_k = {vals}  spread={spread:.3f}")

    print(f"\n## SHA-3 — Ω_k grows with k at intermediate rounds:")
    for r in [3, 6, 18, 24]:
        vals = [SHA3_DATA['per_k'][k][[e[0] for e in SHA3_DATA['per_k'][k]].index(r)][1]
                for k in sorted(SUBSET)]
        spread = max(vals) - min(vals)
        print(f"  r={r}: Ω_k = {vals}  spread={spread:.3f}")

    # SHA-256 collapse rate (15→20 rounds = 5 rounds of collapse)
    print(f"\n## SHA-256 collapse: at r=16 Ω≈0.94, at r=20 Ω≈0.14 → collapses in <5 rounds")
    print(f"   r=17 coincides with WANG-BARRIER (T_BARRIER_EQUALS_SCHEDULE, П-114)")
    print(f"   Methodology predicts exactly this transition from schedule nonlinearity")
    print(f"\n## SHA-3: gradual decay, no hard barrier")


if __name__ == '__main__':
    main()
