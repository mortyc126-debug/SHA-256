"""
IT-4.S2 (surgical): round-by-round emergence of bit5_max signal.

Use chimera framework to truncate SHA-256 at r rounds (r=4..64, step 4).
For each r, compute:
  - all 256 output bits from state after r rounds (+padding block processed fully?)
  - Walsh z for bit5_max against each output bit
  - max|z| and top-2 bits

Key question: at which round does the signal emerge? Does it stay stable
or drift?

We use ONE block only (not the standard two-block padding) to isolate
round-function behavior. Our chimera `hash_messages` already does two
blocks with proper padding. To do single-block reduced rounds, we add
a `n_rounds` parameter.
"""

import hashlib, math, json, os, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
R_NULL = 200
SEED = 0x5210C0DE
ROUND_LIST = [4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 64]
OUT = os.path.join(os.path.dirname(__file__), 'it4_s2_rounds.json')


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


def compress_r_rounds(state, block, n_rounds, flags, K):
    """Vectorized SHA-256 compress for the first n_rounds only.

    Uses a partial schedule: W[0..n_rounds-1] computed lazily but for
    n_rounds ≤ 16 we only use block directly; for n_rounds > 16 we
    compute W[16..n_rounds-1] via schedule.
    """
    N = state.shape[0]
    U32, MASK = ch.U32, ch.MASK
    sm0, sm1 = ch.sigma0, ch.sigma1
    Sg0, Sg1 = ch.Sigma0, ch.Sigma1

    # Schedule up to n_rounds
    W = np.empty((N, max(n_rounds, 16)), dtype=U32)
    W[:, :16] = block
    for t in range(16, n_rounds):
        W[:, t] = (sm1(W[:, t-2]) + W[:, t-7] + sm0(W[:, t-15]) + W[:, t-16]) & MASK

    a, b, c, d, e, f, g, h = (state[:, i].copy() for i in range(8))
    for t in range(n_rounds):
        T1 = (h + Sg1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (Sg0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    new = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    return (new + state) & MASK


def hash_reduced_rounds(messages, n_rounds):
    """Single-block messages (64 bytes), reduced rounds. Returns (N, 8) uint32."""
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    return compress_r_rounds(state, block, n_rounds, None, ch.K_VANILLA)


def state_to_bits(state):
    """Convert (N, 8) uint32 state to (N, 256) binary array, MSB-first per word."""
    N = state.shape[0]
    bits = np.zeros((N, 256), dtype=np.uint8)
    for word_idx in range(8):
        for bit_idx in range(32):
            col = word_idx * 32 + bit_idx
            bits[:, col] = ((state[:, word_idx] >> np.uint32(31 - bit_idx)) & 1).astype(np.uint8)
    return bits


def walsh_z_vec(f_arr, out_bits):
    N = len(f_arr)
    sqrtN = math.sqrt(N)
    equal = (out_bits == f_arr[:, None])
    eq = equal.sum(axis=0)
    return (2.0 * eq - N) / N * sqrtN


def keyed_blake_bits(inputs, key):
    """256-bit keyed BLAKE2b → (N, 256) bits."""
    N = len(inputs)
    bits = np.zeros((N, 256), dtype=np.uint8)
    for i, x in enumerate(inputs):
        d = hashlib.blake2b(x, key=key, digest_size=32).digest()
        arr = np.frombuffer(d, dtype=np.uint8)
        for byte_idx in range(32):
            for bit_in_byte in range(8):
                col = byte_idx * 8 + bit_in_byte
                bits[i, col] = (arr[byte_idx] >> (7 - bit_in_byte)) & 1
    return bits


def main():
    t_total = time.time()
    print("# IT-4.S2: round-by-round emergence of bit5_max signal")
    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f = ((max_p >> 5) & 1).astype(np.uint8)
    print(f"# N = {N}, rounds = {ROUND_LIST}, R_null = {R_NULL}")

    # Verify our reduced-round at r=64 matches SHA-256 single-block...
    # Actually standard SHA-256 does 2 blocks (message + padding block).
    # Reduced-round is only message block. They differ. We run reduced-round
    # on single message block only.

    # Compute per-round Walsh z
    per_round = {}
    for r in ROUND_LIST:
        print(f"\n## r = {r} rounds")
        t0 = time.time()
        state = hash_reduced_rounds(inputs, r)
        bits = state_to_bits(state)
        z_vec = walsh_z_vec(f, bits)
        maxz = float(np.abs(z_vec).max())
        max_idx = int(np.argmax(np.abs(z_vec)))
        sumz2 = float((z_vec ** 2).sum())
        top3 = sorted(enumerate(z_vec), key=lambda kv: -abs(kv[1]))[:3]
        per_round[r] = {
            'max_z': float(z_vec[max_idx]),
            'max_idx': max_idx,
            'sum_z2': sumz2,
            'top3': [{'bit': int(i), 'z': float(v)} for i, v in top3],
            'time': time.time() - t0,
        }
        print(f"  Σz² (256 bits): {sumz2:.1f}")
        print(f"  max |z|: {maxz:.2f} at bit {max_idx}")
        print(f"  top 3: " + ", ".join(f"bit{i} z={v:+.2f}" for i, v in top3))
        print(f"  time: {time.time()-t0:.1f}s")

    # RO null: only need to compute at r=64 since single run gives null baseline
    # for 256-bit output. Here we treat BLAKE2b at 32-byte as RO.
    print(f"\n## RO null: R={R_NULL} keyed-BLAKE2b realizations")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_NULL)]
    ro_maxz = []
    ro_sumz2 = []
    t0 = time.time()
    for r_idx, key in enumerate(keys):
        bits = keyed_blake_bits(inputs, key)
        z_vec = walsh_z_vec(f, bits)
        ro_maxz.append(float(np.abs(z_vec).max()))
        ro_sumz2.append(float((z_vec ** 2).sum()))
        if (r_idx + 1) % 50 == 0:
            print(f"  r={r_idx+1}/{R_NULL} elapsed={time.time()-t0:.1f}s")
    ro_maxz = np.asarray(ro_maxz)
    ro_sumz2 = np.asarray(ro_sumz2)
    print(f"  RO maxz: mean={ro_maxz.mean():.2f} ± {ro_maxz.std(ddof=1):.2f}")
    print(f"  RO Σz²:  mean={ro_sumz2.mean():.2f} ± {ro_sumz2.std(ddof=1):.2f}")

    # Round-by-round verdict
    print(f"\n## Round-by-round summary")
    print(f"  {'round':>5}  {'max|z|':>6}  {'Σz²':>6}  {'max_bit':>7}  {'z_max_norm_vs_RO':>17}")
    ro_mean_max = float(ro_maxz.mean())
    ro_std_max = float(ro_maxz.std(ddof=1))
    ro_mean_sum = float(ro_sumz2.mean())
    ro_std_sum = float(ro_sumz2.std(ddof=1))
    for r in ROUND_LIST:
        info = per_round[r]
        z_maxnorm = (abs(info['max_z']) - ro_mean_max) / ro_std_max
        z_sumnorm = (info['sum_z2'] - ro_mean_sum) / ro_std_sum
        print(f"  {r:>5}  {abs(info['max_z']):>6.2f}  {info['sum_z2']:>6.1f}  "
              f"{info['max_idx']:>7d}  z_max={z_maxnorm:+.2f}  z_sum={z_sumnorm:+.2f}")

    out = {
        'meta': {'N': N, 'R_null': R_NULL, 'rounds': ROUND_LIST},
        'per_round': per_round,
        'ro_maxz': {'mean': ro_mean_max, 'std': ro_std_max},
        'ro_sumz2': {'mean': ro_mean_sum, 'std': ro_std_sum},
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
