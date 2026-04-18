"""Phase 6C extension: do top phase-locked features survive to r=64 (full SHA)?

If bit8_max Ω_3 stays at +0.6 through r=64 baseline SHA, that's a proper
distinguisher for full SHA-256.

Methodology IT-6 reported Ω_3 = +0.98 (full enum r=64) using bit5_max,
but our cross-hash work showed input→hash probe is RO-like for bit5_max.

Crucial difference: phase 6c uses chi_S basis from STATE r=4 (internal),
not input bits. This is the IT-6 / IT-21 internal probe.

Now testing other features under this protocol at r=64.
"""
import json, os, time
import numpy as np

from oracle_gauge import low_hw2_inputs, build_chi_arr, omega_k_fast
from phase3a_chimera_attribution import compress_partial
from phase6c_phase_locking import make_features


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase6c_r64_extend.json')

# Top features from Phase 6C + bit5_max baseline
TARGET_FEATURES = [
    'bit5_max',  # baseline
    'bit8_max',  # top
    'gap_bit8',  # 2nd
    'bit1_min',  # 3rd
    'bit7_max',  # 4th
    'bit8_min',  # negative-then-positive
]
ROUNDS = [4, 16, 24, 32, 48, 64]


def main():
    t0 = time.time()
    print("# Phase 6C extension: top features at r=64 (full SHA)")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    print(f"# N = {N}")

    features = make_features(pos)

    # Compute baseline states once
    print(f"\n## Computing baseline states at r ∈ {ROUNDS}...")
    states = {}
    for r in ROUNDS:
        ts = time.time()
        states[r] = compress_partial(inputs, r)
        print(f"  r={r}: {time.time()-ts:.0f}s")

    # χ_S basis
    chi_arr, _ = build_chi_arr(states[4], k=3, subset_size=32)
    print(f"\n## χ_S: state r=4, k=3, M={chi_arr.shape[0]}")

    # Measure Ω_3 for target features at all rounds
    print(f"\n## Target features × full round range:")
    print(f"{'feature':12s}  " + "  ".join(f"r={r:>2}" for r in ROUNDS))
    results = {}
    for fname in TARGET_FEATURES:
        if fname not in features:
            print(f"  {fname}: NOT FOUND")
            continue
        fa = features[fname]
        per_r = {}
        for r in ROUNDS:
            omega, ss, _, _, _ = omega_k_fast(chi_arr, states[r], fa)
            per_r[r] = {'omega': float(omega), 'ss': int(ss)}
        results[fname] = per_r
        omegas = [per_r[r]['omega'] for r in ROUNDS]
        print(f"  {fname:12s}: " + "  ".join(f"{o:+.3f}" for o in omegas))

    # RO null check: random target with chi_arr fixed
    print(f"\n## RO null (10 BLAKE2b realizations) for k=3...")
    import hashlib
    nprng = np.random.default_rng(0xBADF00D)
    ro_omegas = []
    for r in range(10):
        key = nprng.bytes(16)
        target_bits = np.zeros((N, 256), dtype=np.uint8)
        for i, m in enumerate(inputs):
            d = hashlib.blake2b(m, key=key, digest_size=32).digest()
            for bi in range(32):
                for bb in range(8):
                    target_bits[i, bi*8+bb] = (d[bi] >> (7-bb)) & 1
        # Use bit5_max for null since it's a fixed feature
        omega, _, _, _, _ = omega_k_fast(chi_arr, target_bits, features['bit5_max'])
        ro_omegas.append(float(omega))
    ro_mean = float(np.mean(ro_omegas))
    ro_std = float(np.std(ro_omegas, ddof=1))
    print(f"  RO Ω_3: mean = {ro_mean:+.3f}, std = {ro_std:.3f}")

    # Compute z-scores at r=64
    print(f"\n## At r=64 (full SHA), z-score vs RO null:")
    for fname, data in results.items():
        omega = data[64]['omega']
        z = (omega - ro_mean) / ro_std if ro_std > 0 else 0
        print(f"  {fname:12s}: Ω_3 = {omega:+.3f}  z = {z:+5.2f}σ  "
              f"{'★ DISTINGUISHER' if abs(z) > 5 else ''}")

    # Verdict
    distinguishers = [(fn, data[64]['omega'])
                      for fn, data in results.items()
                      if abs((data[64]['omega'] - ro_mean) / ro_std) > 5]
    print(f"\n## Verdict:")
    if distinguishers:
        print(f"  ✓✓✓ FULL-SHA DISTINGUISHERS FOUND: {len(distinguishers)} features with |z|>5σ")
        for fn, om in distinguishers:
            print(f"    {fn}: Ω_3(r=64) = {om:+.3f}")
        print(f"  This contradicts IT-24 RO-LIKE result for input→hash probe.")
        print(f"  KEY DIFFERENCE: chi_S from internal state r=4, not input bits.")
    else:
        print(f"  ✗ No full-SHA distinguishers (all features collapse by r=64)")

    out = {
        'N': N,
        'rounds': ROUNDS,
        'results': results,
        'ro_null': {'mean': ro_mean, 'std': ro_std, 'omegas': ro_omegas},
        'distinguishers_at_r64': [
            {'feature': fn, 'omega': data[64]['omega'],
             'z_vs_ro': (data[64]['omega'] - ro_mean) / ro_std}
            for fn, data in results.items()
            if abs((data[64]['omega'] - ro_mean) / ro_std) > 3
        ],
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
