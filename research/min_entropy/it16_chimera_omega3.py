"""IT-16: Which SHA-256 component encodes the Omega_3 = +0.98 signal?

Use sha256_chimera variants to swap individual components, measure Omega_3
on each variant. Variant where Omega_3 → 0 = component responsible for the
architectural bias. This identifies the SOURCE of the "paint in ocean" —
necessary first step to design a counter-extractor.

Variants tested:
  V0  vanilla (baseline, expect +0.98)
  V1  no Σ in compress
  V2  no σ in schedule
  V3  no Σ AND no σ
  V5  Ch/Maj → linear XOR (kill non-linear)
  V7  V3 + V5 (almost-linear SHA-256)

  Plus K-replacements:
  K_GOLDEN  K[t] := t * 0x9E3779B9 (alternative round constants)
  K_ZERO    K[t] := 0 (no constants)

Per variant: compute Omega_3 on top-16 output bits (top-50 triples each).
Each variant takes ~16 × 2.6s = 42s for chain3. 8 variants × 42s = 5.6 min.
"""
import json, math, os, subprocess, tempfile, time
from itertools import combinations
from math import comb
import numpy as np
import sha256_chimera as ch

WORDS = 2048
N_TOP = 16
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'it4_q7d_chain3')
OUT = os.path.join(HERE, 'it16_chimera_omega3.json')


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


def compute_states(inputs, flags, K, IV=ch.IV_VANILLA):
    """Run two-block SHA on inputs with given variant; return state1 and state2 bits."""
    N = len(inputs)
    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(IV, (N, 8)).copy(), b1, flags, K)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    b2 = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    b2 = np.broadcast_to(b2, (N, 16))
    s2 = ch.compress(s1, b2, flags, K)
    return sb(s1, N), sb(s2, N)


def measure_omega3(s1b, s2b, fa, top_bits, label):
    dz = np.zeros(len(top_bits)); cz = np.zeros(len(top_bits))
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as t: tp = t.name
    N = s1b.shape[0]
    try:
        for i, b in enumerate(top_bits):
            tb = s2b[:, b]
            dz[i] = (1 - 2*((fa^tb).sum())/N) * math.sqrt(N)
            cz[i] = runc(N, s1b, fa, tb, tp)['chain_sum']
    finally:
        os.unlink(tp)
    if np.std(dz) < 1e-10 or np.std(cz) < 1e-10:
        return {'label': label, 'corr': 0.0, 'ss': 0, 'n': len(top_bits),
                'dz_max': float(np.abs(dz).max()), 'cz_max': float(np.abs(cz).max())}
    corr = float(np.corrcoef(dz, cz)[0, 1])
    ss = int((np.sign(dz) == np.sign(cz)).sum())
    return {'label': label, 'corr': corr, 'ss': ss, 'n': len(top_bits),
            'dz_max': float(np.abs(dz).max()), 'cz_max': float(np.abs(cz).max()),
            'dz_mean_abs': float(np.abs(dz).mean()), 'cz_mean_abs': float(np.abs(cz).mean())}


def binom_p(k, n):
    if k < n - k: k = n - k
    return 2*sum(comb(n, i) for i in range(k, n+1))/(1<<n)


def main():
    t0 = time.time()
    inputs, pos = low_hw2(); N = len(inputs)
    mp = np.asarray([p[-1] for p in pos])
    fa = ((mp >> 5) & 1).astype(np.uint8)
    print(f"# IT-16: SHA-256 chimera Omega_3 dissection (N={N})")

    # Identify top bits using V0 vanilla baseline
    print("# computing V0 vanilla baseline to rank top-16 bits...")
    s1b_v0, s2b_v0 = compute_states(inputs, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    direct = np.array([(1 - 2*((fa^s2b_v0[:,b]).sum())/N) * math.sqrt(N) for b in range(256)])
    top_bits = np.argsort(-np.abs(direct))[:N_TOP].tolist()
    print(f"# top-{N_TOP}: {top_bits}")

    # Test conditions
    conditions = [
        ('V0_vanilla',       ch.VARIANTS['V0_vanilla'],       ch.K_VANILLA),
        ('V1_no_Sigma',      ch.VARIANTS['V1_no_Sigma_compr'], ch.K_VANILLA),
        ('V2_no_sigma',      ch.VARIANTS['V2_no_sigma_sched'], ch.K_VANILLA),
        ('V3_no_diffusion',  ch.VARIANTS['V3_no_both_diffusion'], ch.K_VANILLA),
        ('V5_linear_NLF',    ch.VARIANTS['V5_linear_chmaj'],   ch.K_VANILLA),
        ('V7_almost_linear', ch.VARIANTS['V7_almost_linear'],  ch.K_VANILLA),
        ('K_ZERO',           ch.VARIANTS['V0_vanilla'],        ch.K_ZERO),
        ('K_GOLDEN',         ch.VARIANTS['V0_vanilla'],        ch.K_GOLDEN),
    ]

    results = []
    for label, flags, K in conditions:
        ts = time.time()
        print(f"\n## {label}")
        s1b, s2b = compute_states(inputs, flags, K)
        # For each variant, re-rank or use V0 ranking? Use V0 ranking for fair comparison
        # of "what happens to those specific bits' direct/chain z under the variant".
        r = measure_omega3(s1b, s2b, fa, top_bits, label)
        r['p'] = binom_p(r['ss'], r['n'])
        print(f"   Ω_3={r['corr']:+.4f}  ss={r['ss']}/{r['n']}  p={r['p']:.2e}  "
              f"dz_max={r['dz_max']:.2f} cz_max={r['cz_max']:.2f}  t={time.time()-ts:.0f}s", flush=True)
        results.append(r)

    print("\n=== SUMMARY ===")
    print(f"{'variant':<22} {'Omega_3':>10} {'ss':>10} {'p':>11} {'|dz|max':>10} {'|cz|max':>10}")
    for r in results:
        print(f"{r['label']:<22} {r['corr']:>+10.4f} {r['ss']:>3}/{r['n']:<6} "
              f"{r['p']:>11.2e} {r['dz_max']:>10.2f} {r['cz_max']:>10.2f}")

    print("\n--- INTERPRETATION ---")
    print("V0 baseline: should give +0.98 (matches IT-13).")
    print("Variant where Omega_3 → 0 reveals the COMPONENT responsible for the bias.")
    print("V1 (no Σ): if Omega_3 dies → big Sigma rotations create the structure.")
    print("V2 (no σ): if Omega_3 dies → message schedule rotations.")
    print("V5 (linear NLF): if Omega_3 dies → Ch/Maj is the carrier.")
    print("K_ZERO/K_GOLDEN: if Omega_3 changes → K constants encode it (NSA design choice).")

    with open(OUT, 'w') as f:
        json.dump({'meta': {'N': N, 'top_bits': top_bits, 'feature': 'bit5_max'},
                   'results': results}, f, indent=2)
    print(f"\nWrote {OUT}, total {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
