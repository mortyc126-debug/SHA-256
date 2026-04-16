"""IT-22: Deeper analysis of Omega_3 conservation — is chain_z VECTOR itself conserved?

Omega_3 = corr(direct_z, chain_z) = +0.92 at every round.
But direct_z and chain_z both CHANGE round-to-round (different output bits).

Key question: is there a structural invariant BEYOND the scalar Omega_3?

Test 1: cross-round correlations of chain_z vectors.
  If chain_z(r=0) ~ chain_z(r=16), signal direction is PRESERVED.
  If chain_z(r=0) ~ 0 with chain_z(r=16), signal is REGENERATED each round.

Test 2: linear transformation chain_z(r+1) = A · chain_z(r)?
  Invariant linear structure → structural attack primitive.

Test 3: do the same bits anomalously deviate from Omega_3 across rounds?
  Residual (direct_z - β · chain_z) pattern persistence.

Test 4: top bits across rounds — same bits hot?
  Bit 10 was top-|direct_z| in IT-6 (bit5_max feature at r=64).
  Is bit 10 also top at r=0, r=16, r=32, r=48?

All analysis uses the chain_z[256] vectors saved in it21_r48_r64.json
plus what we can reconstruct from IT-21 python wrapper log.
"""
import json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))

# Re-collect from JSON files
r48_r64 = json.load(open(os.path.join(HERE, 'it21_r48_r64.json')))

# IT-21 also saved the first 3 rounds in /tmp/it21.out as text — let me re-run those too
# Since we have the C binary and data, easier to recompute all 5 rounds cleanly.
# Reuse existing IT-21 wrapper to save direct_z/chain_z from each round.

WORDS = 2048
C_BIN = os.path.join(HERE, 'omega3_full')


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


def pack(v):
    pd = np.zeros(WORDS*64, dtype=np.uint8); pd[:len(v)] = v
    return np.frombuffer(np.packbits(pd, bitorder='little').tobytes(), dtype=np.uint64)


def compress_partial(state, block, nr):
    N = state.shape[0]
    U32, MASK = ch.U32, ch.MASK
    W = np.empty((N, max(nr, 16)), dtype=U32); W[:, :16] = block
    for t in range(16, max(nr, 16)):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    a, b, c, d, e, f, g, h = (state[:, i].copy() for i in range(8))
    for t in range(nr):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(ch.K_VANILLA[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)


def main():
    t0 = time.time()
    inputs, pos = low_hw2(); N = len(inputs)
    print(f"# IT-22: vector-level analysis of Omega_3 conservation")

    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1,
                     ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    state1_bits = sb(s1, N)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    pad_block = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    pad_block = np.broadcast_to(pad_block, (N, 16))
    mp = np.asarray([p[-1] for p in pos]); fa = ((mp >> 5) & 1).astype(np.uint8)

    # Gather chain_z and direct_z for each round (use higher stride for speed)
    ROUNDS = [0, 16, 32, 48, 64]
    STRIDE = 8   # ~345K triples/round ~45s × 5 = 4 min
    data = {}  # r -> {'direct_z': vec, 'chain_z': vec}
    for r in ROUNDS:
        print(f"\n## r={r}", flush=True)
        if r == 64:
            s2 = ch.compress(s1, pad_block, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
        elif r == 0:
            s2 = s1.copy()
        else:
            s2 = compress_partial(s1, pad_block, r)
        state2_bits = sb(s2, N)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf: tp = tf.name
        try:
            with open(tp, 'wb') as fp:
                fp.write(np.uint64(N).tobytes())
                for b in range(256): fp.write(pack(state1_bits[:, b]).tobytes())
                fp.write(pack(fa).tobytes())
                for b in range(256): fp.write(pack(state2_bits[:, b]).tobytes())
            ts = time.time()
            res = subprocess.run([C_BIN, tp, str(STRIDE)], capture_output=True, text=True, check=True, timeout=200)
            dt = time.time() - ts
            d = json.loads(res.stdout)
            print(f"  Ω_3={d['omega3']:+.4f}  ss={d['same_sign']}/256  t={dt:.0f}s", flush=True)
            data[r] = {'direct_z': np.array(d['direct_z']), 'chain_z': np.array(d['chain_z']),
                       'omega3': d['omega3'], 'ss': d['same_sign']}
        finally:
            os.unlink(tp)

    print("\n=== ANALYSIS 1: Cross-round chain_z alignment ===")
    print("(If chain_z vector is preserved round-to-round, pairwise corr → high)\n")
    rs = ROUNDS
    print("       " + " ".join(f"r={r:>3}" for r in rs))
    for r1 in rs:
        row = f"r={r1:>3}: "
        for r2 in rs:
            corr = float(np.corrcoef(data[r1]['chain_z'], data[r2]['chain_z'])[0, 1])
            row += f"{corr:+.3f} "
        print(row)

    print("\n=== ANALYSIS 2: Cross-round direct_z alignment ===\n")
    print("       " + " ".join(f"r={r:>3}" for r in rs))
    for r1 in rs:
        row = f"r={r1:>3}: "
        for r2 in rs:
            corr = float(np.corrcoef(data[r1]['direct_z'], data[r2]['direct_z'])[0, 1])
            row += f"{corr:+.3f} "
        print(row)

    print("\n=== ANALYSIS 3: Does direct_z(r) = A · direct_z(0)? ===")
    # Rank of stacked direct_z matrix
    DZ = np.stack([data[r]['direct_z'] for r in rs])  # 5 x 256
    u, sv, vh = np.linalg.svd(DZ, full_matrices=False)
    print(f"Singular values of direct_z stack (5x256): {sv}")
    print(f"  Rank ≥ 4σ above noise: first few σ: {sv[:5]}")

    CZ = np.stack([data[r]['chain_z'] for r in rs])
    u2, sv2, vh2 = np.linalg.svd(CZ, full_matrices=False)
    print(f"Singular values of chain_z stack: {sv2}")

    print("\n=== ANALYSIS 4: Top bits persistence ===")
    for r in rs:
        top = np.argsort(-np.abs(data[r]['direct_z']))[:10]
        print(f"r={r:>3} top-10 |direct_z| bits: {top.tolist()}")

    print("\n=== ANALYSIS 5: Stable bits (same top bits across rounds) ===")
    all_tops = {r: set(np.argsort(-np.abs(data[r]['direct_z']))[:20].tolist()) for r in rs}
    intersection = set.intersection(*all_tops.values())
    print(f"Bits in top-20 at EVERY round: {sorted(intersection)} (size {len(intersection)})")
    print(f"Under H0 (5 independent rounds): expected |intersection| ≈ 20⁵/256⁴ ≈ 0.07")

    # Save full data
    out = {'meta': {'N': N, 'rounds': ROUNDS, 'stride': STRIDE},
           'data': {str(r): {'direct_z': data[r]['direct_z'].tolist(),
                             'chain_z': data[r]['chain_z'].tolist(),
                             'omega3': data[r]['omega3'], 'ss': data[r]['ss']} for r in rs},
           'cross_chain_corr': [[float(np.corrcoef(data[r1]['chain_z'], data[r2]['chain_z'])[0,1])
                                 for r2 in rs] for r1 in rs],
           'cross_direct_corr': [[float(np.corrcoef(data[r1]['direct_z'], data[r2]['direct_z'])[0,1])
                                 for r2 in rs] for r1 in rs],
           'dz_singular_values': sv.tolist(),
           'cz_singular_values': sv2.tolist(),
           'stable_top20_bits': sorted(intersection)}
    with open(os.path.join(HERE, 'it22_vector_analysis.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
