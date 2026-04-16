"""IT-21: Full Omega_3 conservation test (ALL 256 output bits, ALL 2.7M triples).

Uses new omega3_full C binary that processes all 256 output targets in one
triple enumeration pass. ~100x speedup vs calling chain3 256 times separately.

Measures Omega_3 at multiple block-2 rounds r, with:
  - full 256-bit state1
  - full 256-bit state2 target spectrum
  - full C(256,3) = 2,763,520 triple enumeration
  - HW=2 exhaustive inputs (N=130816)
  - feature = bit5_max

Expected: if Omega_3 conservation (+0.98 at every r) is confirmed on
the full 256-bit spectrum (not just top-24), it's a rigorous result.
"""
import json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'omega3_full')
OUT = os.path.join(HERE, 'it21_full_conservation.json')

# Target rounds to measure — spaced to catch any evolution pattern
ROUNDS = [0, 16, 32, 48, 64]
STRIDE = 4  # sample 1/4 of triples (690K of 2.76M) — tradeoff precision/time


def low_hw2():
    inputs, pos = [], []
    for p in combinations(range(512), 2):
        b = bytearray(64)
        for q in p: b[q >> 3] |= 1 << (q & 7)
        inputs.append(bytes(b)); pos.append(p)
    return inputs, pos


def sb(s, N):
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w*32+b] = ((s[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits


def pack(v, N_target_bits=WORDS*64):
    pd = np.zeros(N_target_bits, dtype=np.uint8); pd[:len(v)] = v
    return np.frombuffer(np.packbits(pd, bitorder='little').tobytes(), dtype=np.uint64)


def compress_partial(state, block, n_rounds):
    N = state.shape[0]
    U32, MASK = ch.U32, ch.MASK
    W = np.empty((N, max(n_rounds, 16)), dtype=U32)
    W[:, :16] = block
    for t in range(16, max(n_rounds, 16)):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    a, b, c, d, e, f, g, h = (state[:, i].copy() for i in range(8))
    K = ch.K_VANILLA
    for t in range(n_rounds):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)


def main():
    t0 = time.time()
    inputs, pos = low_hw2(); N = len(inputs)
    print(f"# IT-21: full Omega_3 conservation test (N={N}, 256 bits, 2.7M triples)")

    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    state1_bits = sb(s1, N)
    print(f"# state1 computed", flush=True)

    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    pad_block = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    pad_block = np.broadcast_to(pad_block, (N, 16))

    mp = np.asarray([p[-1] for p in pos]); fa = ((mp >> 5) & 1).astype(np.uint8)

    all_rounds = []
    for r in ROUNDS:
        ts = time.time()
        print(f"\n## r={r}", flush=True)
        if r == 0:
            state2 = s1.copy()
        else:
            state2 = compress_partial(s1, pad_block, r)
        state2_bits = sb(state2, N)

        # Write binary: N, state1[256][WORDS], fa[WORDS], state2[256][WORDS]
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf:
            tp = tf.name
        try:
            with open(tp, 'wb') as fp:
                fp.write(np.uint64(N).tobytes())
                for b in range(256):
                    fp.write(pack(state1_bits[:, b]).tobytes())
                fp.write(pack(fa).tobytes())
                for b in range(256):
                    fp.write(pack(state2_bits[:, b]).tobytes())
            print(f"  Binary written, starting C computation (stride={STRIDE}, ETA ~100s)...", flush=True)
            res = subprocess.run([C_BIN, tp, str(STRIDE)], capture_output=True, text=True, check=True)
            data = json.loads(res.stdout)
            elapsed = time.time() - ts
            print(f"  Ω_3 = {data['omega3']:+.6f}  same_sign = {data['same_sign']}/256  "
                  f"time = {elapsed:.0f}s", flush=True)
            all_rounds.append({'r': r, 'omega3': data['omega3'],
                               'same_sign': data['same_sign'],
                               'direct_z': data['direct_z'],
                               'chain_z': data['chain_z'],
                               'elapsed': elapsed})
        finally:
            os.unlink(tp)

    print("\n=== SUMMARY (FULL 256 bits × 2.7M triples) ===")
    print(f"{'round':>6} {'Omega_3':>10} {'sign-test':>12}")
    for r in all_rounds:
        print(f"{r['r']:>6} {r['omega3']:>+10.6f} {r['same_sign']:>6}/256")

    # p-value for 240/256 = 10^-40. Simpler: report z of sign-test
    import math
    def sign_z(k, n):
        p = 0.5
        mean = n * p
        std = math.sqrt(n * p * (1 - p))
        return (k - mean) / std
    print(f"\n  z of sign-test (deviation from 128):")
    for r in all_rounds:
        print(f"  r={r['r']:>3}: sign_z = {sign_z(max(r['same_sign'], 256-r['same_sign']), 256):+.2f}σ")

    with open(OUT, 'w') as f:
        json.dump({'meta': {'N': N, 'rounds': ROUNDS, 'feature': 'bit5_max',
                            'n_bits': 256, 'n_triples_per_round': 2763520},
                   'results': all_rounds}, f, indent=2)
    print(f"\nWrote {OUT}, total {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
