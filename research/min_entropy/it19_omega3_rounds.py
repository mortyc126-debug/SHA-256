"""IT-19: Omega_3 evolution through block-2 rounds.

Measure Omega_3 between state1 (fixed = output of block 1) and state2_at_r
(partial output after r rounds of block 2 compression on PAD with state1 as IV).

For each r in {0, 8, 16, 24, 32, 40, 48, 56, 64}:
  Compute state2_at_r for all HW=2 inputs
  Measure Omega_3 on top-24 output bits (re-ranked per r since top bits change)

If Omega_3 stable across r → conserved quantity = algebraic invariant (lever)
If Omega_3 emerges from 0 → diffusion-created (property of round function)
If Omega_3 dips/recovers → specific rounds break/rebuild it

Cost: 9 rounds * 24 bits * 2.6s = ~9 min.
"""
import json, math, os, subprocess, tempfile, time
from itertools import combinations
from math import comb
import numpy as np
import sha256_chimera as ch

WORDS = 2048
N_TOP = 24
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'it4_q7d_chain3')
OUT = os.path.join(HERE, 'it19_omega3_rounds.json')

ROUNDS = [0, 8, 16, 24, 32, 40, 48, 56, 64]


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


def runc(N, s1b, fa, tb, p):
    with open(p, 'wb') as fp:
        fp.write(np.uint64(N).tobytes())
        for b in range(256): fp.write(pack(s1b[:, b]).tobytes())
        fp.write(pack(fa).tobytes()); fp.write(pack(tb).tobytes())
    return json.loads(subprocess.run([C_BIN, p], capture_output=True, text=True, check=True).stdout)


def compress_partial(state, block, n_rounds, flags=None, K=None):
    """Run partial SHA compression: n_rounds, return inner state (no feed-forward sum)."""
    if flags is None: flags = ch.VARIANTS['V0_vanilla']
    if K is None: K = ch.K_VANILLA
    N = state.shape[0]
    U32, MASK = ch.U32, ch.MASK
    W = np.empty((N, max(n_rounds, 16)), dtype=U32)
    W[:, :16] = block
    for t in range(16, max(n_rounds, 16)):
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
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)


def binom_p(k, n):
    if k < n - k: k = n - k
    return 2*sum(comb(n, i) for i in range(k, n+1))/(1<<n)


def main():
    t0 = time.time()
    inputs, pos = low_hw2(); N = len(inputs)
    print(f"# IT-19: Omega_3 evolution through block-2 rounds (N={N})")

    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    state1_bits = sb(s1, N)
    print(f"# state1 computed for all {N} inputs")

    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    pad_block = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    pad_block = np.broadcast_to(pad_block, (N, 16))

    mp = np.asarray([p[-1] for p in pos]); fa = ((mp >> 5) & 1).astype(np.uint8)

    results = []
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as t: tp = t.name
    try:
        for r in ROUNDS:
            ts = time.time()
            print(f"\n## r={r} of block 2")
            if r == 0:
                # state2_at_r = state1 (no rounds yet)
                state2_partial = s1.copy()
            else:
                state2_partial = compress_partial(s1, pad_block, r)
            state2_bits = sb(state2_partial, N)

            # Re-rank top bits at this r
            direct = np.array([(1 - 2*((fa^state2_bits[:,b]).sum())/N) * math.sqrt(N) for b in range(256)])
            top = np.argsort(-np.abs(direct))[:N_TOP].tolist()
            print(f"   top-{N_TOP}: max|z|={abs(direct[top[0]]):.2f} min|z|={abs(direct[top[-1]]):.2f}")

            dz = np.zeros(N_TOP); cz = np.zeros(N_TOP)
            for i, b in enumerate(top):
                tb = state2_bits[:, b]
                dz[i] = direct[b]
                cz[i] = runc(N, state1_bits, fa, tb, tp)['chain_sum']
            corr = float(np.corrcoef(dz, cz)[0, 1]) if np.std(dz) > 1e-10 and np.std(cz) > 1e-10 else 0.0
            ss = int((np.sign(dz) == np.sign(cz)).sum())
            p = binom_p(ss, N_TOP)
            elapsed = time.time() - ts
            print(f"   Ω_3 = {corr:+.4f}  ss={ss}/{N_TOP}  p={p:.2e}  "
                  f"|dz|max={np.abs(dz).max():.2f} |cz|max={np.abs(cz).max():.2f}  ({elapsed:.0f}s)")
            results.append({'r': r, 'omega3': corr, 'ss': ss, 'n': N_TOP, 'p': p,
                            'top_bits': top, 'dz_max': float(np.abs(dz).max()),
                            'cz_max': float(np.abs(cz).max())})
    finally:
        os.unlink(tp)

    print("\n=== SUMMARY: Ω_3 evolution through block 2 ===")
    print(f"{'round':>6} {'Omega_3':>10} {'sign-test':>12} {'p':>10} {'|dz|max':>9} {'|cz|max':>9}")
    for r in results:
        print(f"{r['r']:>6} {r['omega3']:>+10.4f} {r['ss']:>5}/{r['n']:<6} {r['p']:>10.2e} "
              f"{r['dz_max']:>9.2f} {r['cz_max']:>9.2f}")

    print("\n--- INTERPRETATION ---")
    print("Stable +0.98 across all r → CONSERVED QUANTITY of round function (lever!)")
    print("Grows 0 → +0.98 → emerges from diffusion (property of round func)")
    print("Dips and recovers → specific round breaks, others rebuild (structural barrier)")
    print("Drops monotonically → signal IS being destroyed by deeper rounds")

    with open(OUT, 'w') as f:
        json.dump({'meta': {'N': N, 'rounds': ROUNDS, 'feature': 'bit5_max'},
                   'results': results}, f, indent=2)
    print(f"\nWrote {OUT}, total {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
