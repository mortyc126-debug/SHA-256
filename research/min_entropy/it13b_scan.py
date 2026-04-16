"""
IT-13b: Two-arm Omega_3 scan (lean).

Arm 1 (K-scan): bit5_max feature, K ∈ {16K, 32K, 65K, 130K}.
  Does Omega_3 stay near +0.98 at smaller K? If yes → architectural
  persistence even at 8× less data. If drops → sampling-sensitive.

Arm 2 (feature-scan): K=130K, features ∈ {bit4_max, parity_lsb}.
  Is +0.98 bit5_max-specific or universal? Any well-defined feature
  gives +0.98 → structural property of SHA-2 block-2 compression.

24 top bits ranked by |direct_z| under bit5_max@full-N (reused from IT-6).
Total: 6 conditions × 24 bits × 2.6s = 6.2 min.

Reuses it4_q7d_chain3 C binary.
"""
import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
from math import comb
import numpy as np
import sha256_chimera as ch

LENGTH_BITS = 512
WORDS = 2048
N_TOP_BITS = 24
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'it4_q7d_chain3')
OUT_JSON = os.path.join(HERE, 'it13b_scan.json')


def low_hw2():
    inputs, pos = [], []
    for p in combinations(range(LENGTH_BITS), 2):
        b = bytearray(64)
        for q in p: b[q >> 3] |= 1 << (q & 7)
        inputs.append(bytes(b)); pos.append(p)
    return inputs, pos


def sbits(state, N):
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w * 32 + b] = ((state[:, w] >> np.uint32(31 - b)) & 1).astype(np.uint8)
    return bits


def pack(v):
    pad = np.zeros(WORDS * 64, dtype=np.uint8)
    pad[:len(v)] = v
    return np.frombuffer(np.packbits(pad, bitorder='little').tobytes(), dtype=np.uint64)


def make_feature(pos, name):
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    min_p = np.asarray([p[0] for p in pos], dtype=np.int64)
    return {
        'bit5_max': ((max_p >> 5) & 1).astype(np.uint8),
        'bit4_max': ((max_p >> 4) & 1).astype(np.uint8),
        'parity_lsb': (((min_p & 1) ^ (max_p & 1))).astype(np.uint8),
    }[name]


def run_chain(K, state1_bits, f_arr, t_arr, tmp_path):
    with open(tmp_path, 'wb') as fp:
        fp.write(np.uint64(K).tobytes())
        for b in range(256):
            fp.write(pack(state1_bits[:K, b]).tobytes())
        fp.write(pack(f_arr[:K]).tobytes())
        fp.write(pack(t_arr[:K]).tobytes())
    res = subprocess.run([C_BIN, tmp_path], capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def compute_omega3(K, feature_name, top_bits, state1_bits, state2_bits, pos):
    f = make_feature(pos, feature_name)
    direct_z = np.zeros(len(top_bits))
    chain_z = np.zeros(len(top_bits))
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp: p = tmp.name
    try:
        t0 = time.time()
        for i, b in enumerate(top_bits):
            t_b = state2_bits[:, b]
            walsh = 1 - 2 * ((f[:K] ^ t_b[:K]).sum()) / K
            direct_z[i] = walsh * math.sqrt(K)
            r = run_chain(K, state1_bits, f, t_b, p)
            chain_z[i] = r['chain_sum']
            if (i + 1) % 8 == 0:
                print(f"    {i+1}/{len(top_bits)}  elapsed={time.time()-t0:.0f}s", flush=True)
    finally:
        os.unlink(p)
    corr = float(np.corrcoef(direct_z, chain_z)[0, 1]) if len(top_bits) >= 2 else 0.0
    same_sign = int(np.sum(np.sign(direct_z) == np.sign(chain_z)))
    return {
        'K': K, 'feature': feature_name,
        'corr': corr, 'same_sign': same_sign, 'n_bits': len(top_bits),
        'direct_z': direct_z.tolist(), 'chain_z': chain_z.tolist(),
        'direct_z_mean_abs': float(np.abs(direct_z).mean()),
        'chain_z_mean_abs': float(np.abs(chain_z).mean()),
    }


def binom_p_twoside(k, n):
    if k < n - k: k = n - k
    tail = sum(comb(n, i) for i in range(k, n + 1))
    return 2 * tail / (1 << n)


def main():
    t_total = time.time()
    print("# IT-13b: lean Omega_3 scan — K-scan + feature-scan")
    inputs, pos = low_hw2()
    N = len(inputs)
    print(f"# HW=2 exhaustive: N={N}")

    # Compute state bits once
    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view(dtype='>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1,
                     ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    b2 = np.frombuffer(bytes(pad), dtype=np.uint8).view(dtype='>u4').reshape(1, 16).astype(ch.U32)
    b2 = np.broadcast_to(b2, (N, 16))
    s2 = ch.compress(s1, b2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    state1_bits = sbits(s1, N)
    state2_bits = sbits(s2, N)
    print(f"# state1/state2 computed")

    # Rank top bits by |direct_z| at full-N bit5_max
    f0 = make_feature(pos, 'bit5_max')
    direct_full = np.zeros(256)
    for b in range(256):
        walsh = 1 - 2 * ((f0 ^ state2_bits[:, b]).sum()) / N
        direct_full[b] = walsh * math.sqrt(N)
    top_bits = np.argsort(-np.abs(direct_full))[:N_TOP_BITS].tolist()
    print(f"# top-{N_TOP_BITS}: max|z|={np.abs(direct_full[top_bits[0]]):.2f}, "
          f"min|z|={np.abs(direct_full[top_bits[-1]]):.2f}")

    results = []

    # ARM 1: K-scan with bit5_max
    print(f"\n### ARM 1: K-scan (feature=bit5_max)")
    for K in [16384, 32768, 65536, 130816]:
        print(f"\n## K={K}")
        r = compute_omega3(K, 'bit5_max', top_bits, state1_bits, state2_bits, pos)
        p = binom_p_twoside(r['same_sign'], r['n_bits'])
        r['p_binom'] = p
        print(f"   Ω_3 corr={r['corr']:+.4f}  same-sign={r['same_sign']}/{r['n_bits']}  p={p:.2e}")
        results.append(r)

    # ARM 2: feature-scan at K=130816
    print(f"\n### ARM 2: feature-scan (K=130816)")
    for feat in ['bit4_max', 'parity_lsb']:
        print(f"\n## feature={feat}")
        r = compute_omega3(N, feat, top_bits, state1_bits, state2_bits, pos)
        p = binom_p_twoside(r['same_sign'], r['n_bits'])
        r['p_binom'] = p
        print(f"   Ω_3 corr={r['corr']:+.4f}  same-sign={r['same_sign']}/{r['n_bits']}  p={p:.2e}")
        results.append(r)

    print("\n=== SUMMARY ===")
    print(f"{'feature':<12} {'K':>8} {'Omega_3':>9} {'same_sign':>12} {'p(binom)':>10}")
    for r in results:
        print(f"{r['feature']:<12} {r['K']:>8} {r['corr']:>+9.4f} "
              f"{r['same_sign']:>6}/{r['n_bits']:<5} {r['p_binom']:>10.2e}")

    print("\n--- INTERPRETATION ---")
    print("K-scan: if Ω_3 stable across 16K → 130K, signal is architectural, not N-dependent.")
    print("Feature-scan: if Ω_3 high for bit4_max and parity_lsb too, signal is feature-universal.")
    print("Combined: stable + universal = STRUCTURAL PROPERTY of SHA-2 block-2 compression.")

    with open(OUT_JSON, 'w') as f:
        json.dump({'meta': {'N': N, 'top_bits': top_bits, 'n_top': N_TOP_BITS},
                   'results': results}, f, indent=2)
    print(f"\nWrote {OUT_JSON}")
    print(f"Total time: {time.time() - t_total:.0f}s")


if __name__ == '__main__':
    main()
