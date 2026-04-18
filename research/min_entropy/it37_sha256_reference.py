"""IT-37 reference: run SAME protocol as IT-37 SHA-3 probe but on SHA-256.

χ_S basis: state_r1 (after r1 rounds of SHA-256 compression).
Target: state_r for r ∈ {r1, 8, 16, 32, 64}.
Feature: bit5_max of HW=2 input.

If SHA-256 shows Ω_3 conservation across r (stays high after r=r1),
then SHA-3 result (decay to RO by r=6) is REAL difference between
compression/sponge round functions.

If SHA-256 also decays under this protocol, then IT-21's ~0.92
conservation was protocol-specific (using full-compression state1).
"""
import hashlib, json, os, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch
from oracle_gauge import low_hw2_inputs, make_feature, build_chi_arr, omega_k_fast

OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'it37_sha256_reference.json')


def sha256_partial_state(messages, num_rounds):
    """Compute SHA-256 compression state after `num_rounds` of 64-round compression.

    Returns (N, 256) uint8 bits — state (a..h) packed big-endian.
    """
    N = len(messages)
    U32 = ch.U32
    MASK = ch.MASK
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)

    # Expand schedule
    W = np.empty((N, 64), dtype=U32)
    W[:, :16] = block
    for t in range(16, 64):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK

    iv = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    for t in range(min(num_rounds, 64)):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK

    # Pack into 256-bit state
    state = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    state_bytes = state.view('<u1').reshape(N, 8, 4)[:, :, ::-1].reshape(N, 32)
    bits = np.unpackbits(state_bytes, axis=1, bitorder='big')
    return bits


def main():
    t0 = time.time()
    print("# IT-37 reference: SHA-256 compression Ω_3 (same protocol as SHA-3 IT-37)")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    fa = make_feature(pos, 'bit5_max')
    print(f"# N={N}, feature=bit5_max")

    # "state1" analog: after r1=4 rounds of SHA-256 (one round of diffusion)
    r1 = 4
    print(f"\n# χ_S basis: state after r={r1}...")
    state_r1 = sha256_partial_state(inputs, r1)
    chi_arr, _ = build_chi_arr(state_r1, k=3, subset_size=32)
    print(f"  {chi_arr.shape[0]} triples")

    rounds_list = [r1, 8, 16, 32, 48, 64]
    results = {}
    print(f"\n# Target at r ∈ {rounds_list}:")
    for r in rounds_list:
        ts = time.time()
        target_bits = sha256_partial_state(inputs, r)
        omega, ss, dz, cz, n_const = omega_k_fast(chi_arr, target_bits, fa)
        results[r] = {
            'omega3': float(omega),
            'same_sign': int(ss),
            'n_const': int(n_const),
        }
        print(f"  r={r:>2}: Ω_3 = {omega:+.4f}  ss={ss}/256  "
              f"({time.time()-ts:.0f}s)")

    # RO null
    print(f"\n# RO null (10 BLAKE2b realizations)...")
    ts = time.time()
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
        omega, _, _, _, _ = omega_k_fast(chi_arr, target_bits, fa)
        ro_omegas.append(float(omega))
    ro_mean = float(np.mean(ro_omegas))
    ro_std = float(np.std(ro_omegas, ddof=1))
    print(f"  RO band: {ro_mean:+.4f} ± {ro_std:.4f}  ({time.time()-ts:.0f}s)")

    print(f"\n=== SUMMARY ===")
    print(f"RO null: {ro_mean:+.4f} ± {ro_std:.4f}")
    for r in rounds_list:
        res = results[r]
        z = (res['omega3'] - ro_mean) / ro_std if ro_std > 0 else 0
        print(f"  r={r:>2}: Ω_3 = {res['omega3']:+.4f}  ss={res['same_sign']:>3}/256  z={z:>6.2f}σ")

    out = {
        'N': N, 'feature': 'bit5_max', 'chi_r': r1,
        'rounds': rounds_list, 'sha256': results,
        'ro_null': {'mean': ro_mean, 'std': ro_std, 'omegas': ro_omegas},
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
