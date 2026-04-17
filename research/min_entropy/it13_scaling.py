"""
IT-13: N-scaling AND feature-specificity of Omega_3 at full hash.

IT-6 already showed Omega_3 = +0.9795 at full hash on HW=2 exhaustive (N=130816)
with feature f = bit5_max. User hypothesis: even small deviations are real
architectural signal. Test by:

  1. Sub-sampling K in {32768, 130816} of HW=2 inputs. Does Omega_3 stay
     near +0.98 at K=32K, or does it scale with N?
  2. Feature variation: 3 different features of input position-pair.
     If all give similar Omega_3 → universal architectural property.
     If only one → artifact of feature choice.

Re-uses existing it4_q7d_chain3 C binary.
For compute budget, evaluate only TOP 64 bits by |direct_z| (not all 256).

Output table: Omega_3(K, feature), sign_test, corr.
"""

import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

LENGTH_BITS = 512
N_TOP_BITS = 64
WORDS = 2048  # max 131072 bits
C_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7d_chain3')
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it13_scaling.json')

K_LIST = [32768, 130816]
FEATURES = ['bit5_max', 'bit4_max', 'parity_lsb']


def low_hw2():
    L = 64
    inputs, pos = [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        inputs.append(bytes(b))
        pos.append(positions)
    return inputs, pos


def full_sha256_state(messages):
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    pad = bytearray(64); pad[0] = 0x80
    pad[-8:] = (512).to_bytes(8, 'big')
    block2 = np.frombuffer(bytes(pad), dtype=np.uint8).view(dtype='>u4').reshape(1, 16).astype(U32)
    block2 = np.broadcast_to(block2, (N, 16))
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    state = ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return ch.compress(state, block2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)


def state_after_block1(messages):
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    return ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)


def state_to_bits(state):
    N = state.shape[0]
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w * 32 + b] = ((state[:, w] >> np.uint32(31 - b)) & 1).astype(np.uint8)
    return bits


def make_feature(pos, name):
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    min_p = np.asarray([p[0] for p in pos], dtype=np.int64)
    if name == 'bit5_max':
        return ((max_p >> 5) & 1).astype(np.uint8)
    if name == 'bit4_max':
        return ((max_p >> 4) & 1).astype(np.uint8)
    if name == 'parity_lsb':
        return (((min_p & 1) ^ (max_p & 1))).astype(np.uint8)
    raise ValueError(name)


def pack_bitmask(bits_vec, total_bits=WORDS * 64):
    padded = np.zeros(total_bits, dtype=np.uint8)
    padded[:len(bits_vec)] = bits_vec
    pb = np.packbits(padded, bitorder='little')
    return np.frombuffer(pb.tobytes(), dtype=np.uint64)


def write_input_bin(K, state_bits, f_arr, t_arr, path):
    """Write binary file header: N=K, state1[256][WORDS], f_mask[WORDS], t_mask[WORDS]."""
    s1 = state_bits[:K]
    fa = f_arr[:K]
    ta = t_arr[:K]
    with open(path, 'wb') as fp:
        fp.write(np.uint64(K).tobytes())
        for b in range(256):
            fp.write(pack_bitmask(s1[:, b]).tobytes())
        fp.write(pack_bitmask(fa).tobytes())
        fp.write(pack_bitmask(ta).tobytes())


def run_c(bin_path):
    res = subprocess.run([C_BIN, bin_path], capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def compute_omega3(K, feature_name, inputs, pos, state1_bits, state2_bits, top_bits):
    """Compute Omega_3 over top_bits at subsample size K with given feature."""
    f_arr = make_feature(pos, feature_name)

    direct_z = np.zeros(len(top_bits))
    chain_z  = np.zeros(len(top_bits))

    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        bin_path = tmp.name
    try:
        t0 = time.time()
        for i, b in enumerate(top_bits):
            t_b = state2_bits[:, b].copy()
            direct_walsh = 1 - 2 * ((f_arr[:K] ^ t_b[:K]).sum()) / K
            direct_z[i] = direct_walsh * math.sqrt(K)
            write_input_bin(K, state1_bits, f_arr, t_b, bin_path)
            res = run_c(bin_path)
            chain_z[i] = res['chain_sum']
            if (i + 1) % 16 == 0:
                el = time.time() - t0
                print(f"    K={K} f={feature_name}: {i+1}/{len(top_bits)} bits ({el:.0f}s)")
    finally:
        os.unlink(bin_path)

    # Omega_3 = pearson corr across bits
    corr = float(np.corrcoef(direct_z, chain_z)[0, 1]) if len(top_bits) >= 2 else 0.0
    same_sign = int(np.sum(np.sign(direct_z) == np.sign(chain_z)))
    return {
        'K': K, 'feature': feature_name,
        'corr': corr,
        'same_sign': same_sign,
        'n_bits': len(top_bits),
        'direct_z_mean_abs': float(np.abs(direct_z).mean()),
        'chain_z_mean_abs': float(np.abs(chain_z).mean()),
    }


def main():
    t_total = time.time()
    print("# IT-13: N-scaling + feature-specificity of Omega_3 at full hash")
    inputs, pos = low_hw2()
    N = len(inputs)
    print(f"# HW=2 exhaustive: N={N}")

    print("# Computing state1 and state2 (full hash) bits...")
    state1_bits = state_to_bits(state_after_block1(inputs))
    state2_bits = state_to_bits(full_sha256_state(inputs))

    # Baseline: identify top-N_TOP_BITS by |direct_z| using bit5_max at full N.
    # (Reuse IT-6 baseline to pick same bits across all experiments.)
    print(f"# Ranking 256 output bits by |direct_z| (bit5_max, full N)...")
    f_base = make_feature(pos, 'bit5_max')
    direct_full = np.zeros(256)
    for b in range(256):
        t_b = state2_bits[:, b]
        walsh = 1 - 2 * ((f_base ^ t_b).sum()) / N
        direct_full[b] = walsh * math.sqrt(N)
    top_bits = np.argsort(-np.abs(direct_full))[:N_TOP_BITS].tolist()
    print(f"# Top-{N_TOP_BITS} bits: {top_bits[:10]}... (max|z|={np.abs(direct_full[top_bits[0]]):.2f}, "
          f"min|z|={np.abs(direct_full[top_bits[-1]]):.2f})")

    # Scan all (K, feature) combinations on these top bits
    all_results = []
    for feat in FEATURES:
        for K in K_LIST:
            print(f"\n## K={K}, feature={feat}")
            r = compute_omega3(K, feat, inputs, pos, state1_bits, state2_bits, top_bits)
            print(f"   Omega_3 corr = {r['corr']:+.4f}, same-sign = {r['same_sign']}/{N_TOP_BITS}, "
                  f"mean|direct|={r['direct_z_mean_abs']:.2f}, mean|chain|={r['chain_z_mean_abs']:.2f}")
            all_results.append(r)

    print("\n=== SUMMARY ===")
    print(f"{'feature':<12} {'K':>8} {'Omega_3':>9} {'same_sign':>10} {'p(binom)':>10}")
    from math import comb
    def binom_p(k, n):
        """Two-sided binomial p for same-sign count"""
        if k < n/2: k = n - k
        p = sum(comb(n, i) for i in range(k, n+1)) / 2**n
        return 2*p
    for r in all_results:
        p = binom_p(r['same_sign'], r['n_bits'])
        print(f"{r['feature']:<12} {r['K']:>8} {r['corr']:>+9.4f} {r['same_sign']:>5}/{r['n_bits']:<4} {p:>10.2e}")

    print("\n--- INTERPRETATION ---")
    print("H0 (pure noise): corr=0, same_sign≈n/2, p≈1")
    print("Architectural signal: corr stable near +0.98 across ALL (K, feature)")
    print("Feature-specific artifact: corr high only for bit5_max")
    print("N-scaling dilution: corr drops at K=32K vs K=130K")

    out = {'meta': {'N': N, 'n_top_bits': N_TOP_BITS, 'top_bits': top_bits, 'K_list': K_LIST, 'features': FEATURES},
           'results': all_results}
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT_JSON}")
    print(f"Total time: {time.time() - t_total:.0f}s")


if __name__ == '__main__':
    main()
