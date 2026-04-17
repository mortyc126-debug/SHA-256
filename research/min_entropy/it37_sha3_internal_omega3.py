"""IT-37: SHA-3 internal state Ω_3 conservation probe.

Parallel to IT-21 (SHA-256 internal state): does Ω_3 conservation
generalize to Keccak-f[1600], or is it SHA-2 family-specific?

Method:
- HW=2 exhaustive inputs (N=130816, 64-byte)
- Absorb into Keccak state (SHA-3-256 padding)
- Measure state at r ∈ {0, 6, 12, 18, 24} Keccak-f rounds
- χ_S over first 32 bits of r=1 state (non-trivial transformation)
- For each r: direct_z[b], chain_3[b] across target 256 bits (first 4 lanes)
- Ω_3(r) = Pearson(direct_z, chain_3) across 256 bits

For comparison: re-run same protocol on SHA-256 to verify methodology
reproduces IT-21 ~0.92 conservation.

If Keccak gives Ω_3 ≈ 0: SHA-2 specific invariant (not sponge).
If Keccak gives Ω_3 ≈ 0.85: universal property of cryptographic
round functions.
"""
import hashlib, json, math, os, time
from itertools import combinations
import numpy as np

from oracle_gauge import low_hw2_inputs, make_feature, build_chi_arr, omega_k_fast
from keccak_vec import keccak_f, absorb_sha3_256

OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'it37_sha3_internal_omega3.json')


def extract_state_bits(state, n_bits=256):
    """Extract first n_bits from Keccak state (N, 5, 5) as (N, n_bits) uint8.

    Output order: lane (x=0,y=0), (x=1,y=0), ..., little-endian bytes,
    big-endian bits — matches SHA-3 output convention.
    """
    N = state.shape[0]
    n_lanes = (n_bits + 63) // 64
    lanes_out = np.zeros((N, n_lanes), dtype=np.uint64)
    for idx in range(n_lanes):
        x = idx % 5; y = idx // 5
        lanes_out[:, idx] = state[:, y, x]
    out_bytes = lanes_out.view(dtype='<u1').reshape(N, n_lanes * 8)[:, :n_bits // 8]
    bits = np.unpackbits(out_bytes, axis=1, bitorder='big')[:, :n_bits]
    return bits


def probe_sha3(inputs, fa, rounds_list, verbose=True):
    """Run Ω_3 probe at multiple round counts. Returns dict of {r: result}."""
    N = len(inputs)
    print(f"  absorb {N} inputs...")
    ts = time.time()
    state0 = absorb_sha3_256(inputs)
    print(f"    {time.time()-ts:.1f}s")

    # Use state after 1 Keccak round as "state1" for χ_S basis
    # (ensures non-trivial transformation from raw input)
    print(f"  compute state1 (r=1)...")
    ts = time.time()
    state1 = keccak_f(state0, num_rounds=1)
    print(f"    {time.time()-ts:.1f}s")

    state1_bits = extract_state_bits(state1, 256)
    chi_arr_k3, _ = build_chi_arr(state1_bits, k=3, subset_size=32)
    print(f"  χ_S k=3: {chi_arr_k3.shape[0]} triples")

    results = {}
    # Cumulative apply rounds
    curr_state = state0.copy()
    last_r = 0
    for r in sorted(rounds_list):
        # Apply (r - last_r) more rounds
        if r > last_r:
            curr_state = keccak_f(curr_state, num_rounds=r - last_r)
        last_r = r
        target_bits = extract_state_bits(curr_state, 256)
        omega, ss, dz, cz, n_const = omega_k_fast(chi_arr_k3, target_bits, fa)
        results[r] = {
            'omega3': float(omega),
            'same_sign': int(ss),
            'n_const': int(n_const),
            'direct_z_mean': float(np.mean(dz)),
            'chain_z_mean': float(np.mean(cz)),
        }
        if verbose:
            print(f"    r={r:>2}: Ω_3 = {omega:+.4f}  ss={ss}/256  (const={n_const})")
    return results


def main():
    t0 = time.time()
    print("# IT-37: SHA-3 internal state Ω_3 conservation probe")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    fa = make_feature(pos, 'bit5_max')
    print(f"# N = {N} HW=2 exhaustive, feature=bit5_max")

    print(f"\n# SHA-3-256 Keccak-f rounds:")
    rounds_list = [0, 1, 6, 12, 18, 24]
    sha3_results = probe_sha3(inputs, fa, rounds_list)

    # RO null: same probe but target = keyed BLAKE2b output per round
    print(f"\n# RO null (10 BLAKE2b realizations)...")
    ts = time.time()
    # Use same state1 for chi_arr (arbitrary but fixed)
    state1_for_chi = keccak_f(absorb_sha3_256(inputs), num_rounds=1)
    state1_bits = extract_state_bits(state1_for_chi, 256)
    chi_arr_k3, _ = build_chi_arr(state1_bits, k=3, subset_size=32)

    nprng = np.random.default_rng(0xBADF00D)
    ro_omegas = []
    for rr in range(10):
        key = nprng.bytes(16)
        target_bits = np.zeros((N, 256), dtype=np.uint8)
        for i, m in enumerate(inputs):
            d = hashlib.blake2b(m, key=key, digest_size=32).digest()
            for bi in range(32):
                for bb in range(8):
                    target_bits[i, bi*8+bb] = (d[bi] >> (7-bb)) & 1
        omega, _, _, _, _ = omega_k_fast(chi_arr_k3, target_bits, fa)
        ro_omegas.append(float(omega))
    ro_mean = float(np.mean(ro_omegas))
    ro_std = float(np.std(ro_omegas, ddof=1))
    print(f"  RO band: mean={ro_mean:+.4f} std={ro_std:.4f} ({time.time()-ts:.0f}s)")

    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"RO null: {ro_mean:+.4f} ± {ro_std:.4f}")
    print(f"")
    print(f"SHA-3-256 internal Ω_3:")
    for r in rounds_list:
        res = sha3_results[r]
        z = (res['omega3'] - ro_mean) / ro_std if ro_std > 0 else 0
        print(f"  r={r:>2}: Ω_3 = {res['omega3']:+.4f}  ss={res['same_sign']:>3}/256  z={z:>6.2f}σ")

    out = {
        'N': N,
        'feature': 'bit5_max',
        'rounds': rounds_list,
        'sha3_256': sha3_results,
        'ro_null': {'mean': ro_mean, 'std': ro_std, 'omegas': ro_omegas},
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT_JSON}  (total {time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
