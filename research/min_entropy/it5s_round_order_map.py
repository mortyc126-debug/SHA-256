"""
IT-5s: SHA-256 chain spectrum across rounds (round × Walsh-order map).

For each round r ∈ {4, 8, 12, 16, 20, 24, 32, 48, 64} of SHA-256 block 1,
compute chain_k(r) for k ∈ {1, 2, 3} where

    chain_k(r) = (1/√N) · Σ over k-subsets T of state_r bits
                          [z_in(T) × z_out(T)]

with
    f_in  = bit5_max (input feature on HW=2)
    f_out = state2[bit 10]  (target after full SHA-256)

This gives a 9 × 3 map showing HOW the bit5_max signal migrates
through SHA-256 round function between Walsh orders as rounds progress.

Hypothesis: signal starts in low Walsh orders (state_r early rounds)
and migrates to higher orders as rounds progress. chain_1 should peak
early, chain_2 later, chain_3 latest (and still significant at r=64).

RO null: R=30 realizations of keyed BLAKE2b 256-bit output used for
each order's null.
"""

import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
R_RO = 30
WORDS = 2048
SEED = 0x5C5A1AB
ROUND_LIST = [4, 8, 12, 16, 20, 24, 32, 48, 64]

C_BIN3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7d_chain3')
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it5s_results.json')


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


def compress_r_rounds(state, block, n_rounds):
    N = state.shape[0]
    U32, MASK = ch.U32, ch.MASK
    K = ch.K_VANILLA
    W = np.empty((N, max(n_rounds, 16)), dtype=U32)
    W[:, :16] = block
    for t in range(16, n_rounds):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    a, b, c, d, e, f, g, h = (state[:, i].copy() for i in range(8))
    for t in range(n_rounds):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    new = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    return (new + state) & MASK


def state_at_round(messages, n_rounds):
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    return compress_r_rounds(state, block1, n_rounds)


def full_sha256_state(messages):
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    pad = bytearray(64)
    pad[0] = 0x80
    pad[-8:] = (512).to_bytes(8, 'big')
    block2 = np.frombuffer(bytes(pad), dtype=np.uint8).view(dtype='>u4').reshape(1, 16).astype(U32)
    block2 = np.broadcast_to(block2, (N, 16))
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    state = ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return ch.compress(state, block2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)


def state_to_bits(state):
    N = state.shape[0]
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w * 32 + b] = ((state[:, w] >> np.uint32(31 - b)) & 1).astype(np.uint8)
    return bits


def keyed_blake_bits(inputs, key):
    N = len(inputs)
    byte_mat = np.empty((N, 32), dtype=np.uint8)
    for i, x in enumerate(inputs):
        byte_mat[i] = np.frombuffer(hashlib.blake2b(x, key=key, digest_size=32).digest(), dtype=np.uint8)
    return np.unpackbits(byte_mat, axis=1, bitorder='big')


def keyed_blake_single_bit(inputs, key, bit_idx=10):
    N = len(inputs)
    arr = np.zeros(N, dtype=np.uint8)
    byte_idx = bit_idx // 8
    shift = 7 - (bit_idx % 8)
    for i, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=32).digest()
        arr[i] = (d[byte_idx] >> shift) & 1
    return arr


def chain_1(bits, f_in, f_out):
    """Chain-1: Σ z_in(b) · z_out(b) / sqrt(N)"""
    N = bits.shape[0]
    sqrtN = math.sqrt(N)
    y = 2.0 * bits.astype(np.float32) - 1.0
    gi = 2.0 * f_in.astype(np.float32) - 1.0
    go = 2.0 * f_out.astype(np.float32) - 1.0
    z_in = (y.T @ gi) / sqrtN
    z_out = (y.T @ go) / sqrtN
    return float((z_in * z_out).sum() / sqrtN)


def chain_2(bits, f_in, f_out):
    """Chain-2: Σ over a<b of z_in(a,b) · z_out(a,b) / sqrt(N)"""
    N = bits.shape[0]
    sqrtN = math.sqrt(N)
    y = 2.0 * bits.astype(np.float32) - 1.0
    gi = 2.0 * f_in.astype(np.float32) - 1.0
    go = 2.0 * f_out.astype(np.float32) - 1.0
    M_in = (y.T @ (y * gi[:, None])) / sqrtN   # (256, 256)
    M_out = (y.T @ (y * go[:, None])) / sqrtN
    iu = np.triu_indices(256, k=1)
    return float((M_in[iu] * M_out[iu]).sum() / sqrtN)


def pack_bitmask(bits_vec):
    padded = np.zeros(WORDS * 64, dtype=np.uint8)
    padded[:len(bits_vec)] = bits_vec
    pb = np.packbits(padded, bitorder='little')
    return np.frombuffer(pb.tobytes(), dtype=np.uint64)


def write_chain3_bin(state_bits, f_in, f_out, path):
    N = len(f_in)
    with open(path, 'wb') as fp:
        fp.write(np.uint64(N).tobytes())
        for b in range(256):
            fp.write(pack_bitmask(state_bits[:, b]).tobytes())
        fp.write(pack_bitmask(f_in).tobytes())
        fp.write(pack_bitmask(f_out).tobytes())


def chain_3_via_c(state_bits, f_in, f_out):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        path = tmp.name
    try:
        write_chain3_bin(state_bits, f_in, f_out, path)
        res = subprocess.run([C_BIN3, path], capture_output=True, text=True, check=True)
        out = json.loads(res.stdout)
        return out['chain_sum']
    finally:
        os.unlink(path)


def main():
    t_total = time.time()
    print(f"# IT-5s: chain spectrum across rounds")
    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f_in = ((max_p >> 5) & 1).astype(np.uint8)

    # Target from full SHA-256
    print("# Computing full SHA-256 output for target...")
    s2 = state_to_bits(full_sha256_state(inputs))
    f_out = s2[:, 10].copy()

    # ---- SHA-256 side: chain_k(r) for each round ----
    print(f"\n# SHA-256: state_r bits at rounds {ROUND_LIST}")
    sha_chain = {r: {} for r in ROUND_LIST}
    for r in ROUND_LIST:
        t0 = time.time()
        state_r_bits = state_to_bits(state_at_round(inputs, r))
        c1 = chain_1(state_r_bits, f_in, f_out)
        c2 = chain_2(state_r_bits, f_in, f_out)
        c3 = chain_3_via_c(state_r_bits, f_in, f_out)
        sha_chain[r] = {'chain_1': c1, 'chain_2': c2, 'chain_3': c3,
                        'time': time.time() - t0}
        print(f"  r={r:>2}: chain_1={c1:+11.2f}  chain_2={c2:+11.2f}  "
              f"chain_3={c3:+11.2f}  ({time.time()-t0:.1f}s)")

    # ---- RO null: R realizations of keyed BLAKE2b 256 bits ----
    print(f"\n# RO null: R={R_RO} keyed-BLAKE2b 256-bit states")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_RO)]
    ro_c1, ro_c2, ro_c3 = [], [], []
    t0_loop = time.time()
    for r_idx, key in enumerate(keys):
        t0 = time.time()
        bits = keyed_blake_bits(inputs, key)
        c1 = chain_1(bits, f_in, f_out)
        c2 = chain_2(bits, f_in, f_out)
        c3 = chain_3_via_c(bits, f_in, f_out)
        ro_c1.append(c1); ro_c2.append(c2); ro_c3.append(c3)
        if (r_idx + 1) % 5 == 0:
            el = time.time() - t0_loop
            eta = el / (r_idx + 1) * (R_RO - r_idx - 1)
            print(f"  r={r_idx+1}/{R_RO}  c1={c1:+.2f} c2={c2:+.2f} c3={c3:+.2f}  "
                  f"elapsed={el:.0f}s  eta={eta:.0f}s")

    ro_c1 = np.asarray(ro_c1); ro_c2 = np.asarray(ro_c2); ro_c3 = np.asarray(ro_c3)
    print(f"\n## RO band stats:")
    print(f"  chain_1: mean={ro_c1.mean():+.2f}  std={ro_c1.std(ddof=1):.2f}")
    print(f"  chain_2: mean={ro_c2.mean():+.2f}  std={ro_c2.std(ddof=1):.2f}")
    print(f"  chain_3: mean={ro_c3.mean():+.2f}  std={ro_c3.std(ddof=1):.2f}")

    # ---- Build z-norm map (r × k) ----
    ro_means = [ro_c1.mean(), ro_c2.mean(), ro_c3.mean()]
    ro_stds  = [ro_c1.std(ddof=1), ro_c2.std(ddof=1), ro_c3.std(ddof=1)]

    print("\n## Chain z_norm map (rows = round r, cols = Walsh order k)")
    print(f"  {'r':>3}  {'|chain_1|':>9}  {'z_1':>6}   {'|chain_2|':>9}  {'z_2':>6}   {'|chain_3|':>9}  {'z_3':>6}")
    zmap = {}
    for r in ROUND_LIST:
        c1 = sha_chain[r]['chain_1']
        c2 = sha_chain[r]['chain_2']
        c3 = sha_chain[r]['chain_3']
        z1 = (c1 - ro_means[0]) / ro_stds[0]
        z2 = (c2 - ro_means[1]) / ro_stds[1]
        z3 = (c3 - ro_means[2]) / ro_stds[2]
        zmap[r] = {'z1': float(z1), 'z2': float(z2), 'z3': float(z3)}
        print(f"  {r:>3}  {abs(c1):>9.1f}  {z1:>+6.2f}   "
              f"{abs(c2):>9.1f}  {z2:>+6.2f}   {abs(c3):>9.1f}  {z3:>+6.2f}")

    # ---- Migration analysis ----
    print("\n## Migration analysis (where does each order peak?):")
    for k in [1, 2, 3]:
        zs = [(r, zmap[r][f'z{k}']) for r in ROUND_LIST]
        peak_r, peak_z = max(zs, key=lambda pr: abs(pr[1]))
        print(f"  chain_{k}: peak at r={peak_r}, |z|={abs(peak_z):.2f}")

    # Save
    out = {
        'meta': {'N': N, 'R_RO': R_RO, 'rounds': ROUND_LIST,
                 'feature': 'bit5_max', 'target': 'state2[bit 10]'},
        'sha_chain': sha_chain,
        'ro_band': {
            'chain_1': {'mean': float(ro_c1.mean()), 'std': float(ro_c1.std(ddof=1)),
                        'values': ro_c1.tolist()},
            'chain_2': {'mean': float(ro_c2.mean()), 'std': float(ro_c2.std(ddof=1)),
                        'values': ro_c2.tolist()},
            'chain_3': {'mean': float(ro_c3.mean()), 'std': float(ro_c3.std(ddof=1)),
                        'values': ro_c3.tolist()},
        },
        'zmap': zmap,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT_JSON}")
    print(f"Total: {time.time()-t_total:.0f}s")


if __name__ == '__main__':
    main()
