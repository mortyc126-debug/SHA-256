"""IT-20b: lean Omega_3 on (a,e) recurrence subspace — only small subsets.

Skip large subsets (full 256, 128-bit halves) that cause memory issues.
Focus on 32-bit registers and 64-bit pairs to answer the key question:
  Does Omega_3 live in (a,e) recurrence variables specifically?
"""
import json, math, os, time, random
from itertools import combinations
from math import comb
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'it20b_ae_lean.json')


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


def omega3_on_subset(s1_pm_subset, s2_pm, fa_pm, top_out_bits):
    """Memory-efficient Omega_3 via chunked computation."""
    N, n_bits = s1_pm_subset.shape
    sN = math.sqrt(N)
    tuples = list(combinations(range(n_bits), 3))
    n_t = len(tuples)
    if n_t == 0:
        return None
    z_in = np.zeros(n_t)
    z_out_per_b = np.zeros((n_t, len(top_out_bits)))
    # Chunk: 4000 triples at a time (4000 * 130816 = 0.5GB int8)
    CHUNK = 4000
    for start in range(0, n_t, CHUNK):
        end = min(start + CHUNK, n_t)
        chunk_t = tuples[start:end]
        chi = np.empty((len(chunk_t), N), dtype=np.int8)
        for i, idx in enumerate(chunk_t):
            chi[i] = s1_pm_subset[:, idx[0]] * s1_pm_subset[:, idx[1]] * s1_pm_subset[:, idx[2]]
        # z_in = chi @ fa_pm / sqrt(N)
        z_in[start:end] = chi @ fa_pm / sN
        for j, ob in enumerate(top_out_bits):
            z_out_per_b[start:end, j] = chi @ s2_pm[:, ob] / sN
    # chain_3(b) = sum_S z_in(S) * z_out(S, b) / sqrt(N)
    chain_z = (z_in[:, None] * z_out_per_b).sum(axis=0) / sN
    # direct_z(b) = fa·s2[:,b] / sqrt(N)
    direct_z = np.array([fa_pm @ s2_pm[:, ob] / sN for ob in top_out_bits])
    if np.std(direct_z) < 1e-10 or np.std(chain_z) < 1e-10:
        omega = 0.0
    else:
        omega = float(np.corrcoef(direct_z, chain_z)[0, 1])
    ss = int((np.sign(direct_z) == np.sign(chain_z)).sum())
    return {'omega3': omega, 'ss': ss, 'n_top': len(top_out_bits),
            'n_state1_bits': n_bits, 'n_tuples': n_t,
            'direct_z_max': float(np.abs(direct_z).max()),
            'chain_z_max': float(np.abs(chain_z).max())}


def main():
    t0 = time.time()
    inputs, pos = low_hw2(); N = len(inputs)
    print(f"# IT-20b: lean Omega_3 on subspaces (N={N})")

    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    b2 = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    b2 = np.broadcast_to(b2, (N, 16))
    s2 = ch.compress(s1, b2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    s1b, s2b = sb(s1, N), sb(s2, N)

    mp = np.asarray([p[-1] for p in pos]); fa = ((mp >> 5) & 1).astype(np.uint8)
    fa_pm = fa.astype(np.int8) * 2 - 1
    s1_pm = s1b.astype(np.int8) * 2 - 1
    s2_pm = s2b.astype(np.int8) * 2 - 1

    direct = np.array([(1 - 2*((fa^s2b[:,b]).sum())/N) * math.sqrt(N) for b in range(256)])
    top_out = np.argsort(-np.abs(direct))[:24].tolist()
    print(f"# top-24 output bits: {top_out[:8]}...")

    REGS = {n: list(range(i*32, (i+1)*32)) for n, i in zip('abcdefgh', range(8))}

    rng = random.Random(0xAEEDA)
    R32a = rng.sample(range(256), 32)
    R32b = rng.sample(range(256), 32)
    R64a = rng.sample(range(256), 64)
    R64b = rng.sample(range(256), 64)
    R64c = rng.sample(range(256), 64)

    SUBSETS = [
        # 32-bit single registers
        ('reg_a (32)',  REGS['a']),
        ('reg_b (32)',  REGS['b']),
        ('reg_c (32)',  REGS['c']),
        ('reg_d (32)',  REGS['d']),
        ('reg_e (32)',  REGS['e']),
        ('reg_f (32)',  REGS['f']),
        ('reg_g (32)',  REGS['g']),
        ('reg_h (32)',  REGS['h']),
        ('rand_32_seed1', R32a),
        ('rand_32_seed2', R32b),
        # 64-bit pairs (recurrence!)
        ('a+e (recurr 64)',   REGS['a'] + REGS['e']),
        ('a+b (shift   64)',  REGS['a'] + REGS['b']),
        ('e+f (shift   64)',  REGS['e'] + REGS['f']),
        ('a+h (corner  64)',  REGS['a'] + REGS['h']),
        ('rand_64_seed1', R64a),
        ('rand_64_seed2', R64b),
        ('rand_64_seed3', R64c),
    ]

    results = []
    print(f"\n{'subset':<26} {'bits':>5} {'tuples':>8} {'Omega_3':>10} {'sign':>10} {'|dz|max':>9} {'|cz|max':>10} {'time':>6}")
    for name, idx in SUBSETS:
        ts = time.time()
        sub_pm = s1_pm[:, idx]
        r = omega3_on_subset(sub_pm, s2_pm, fa_pm, top_out)
        elapsed = time.time() - ts
        if r:
            print(f"{name:<26} {r['n_state1_bits']:>5} {r['n_tuples']:>8} "
                  f"{r['omega3']:>+10.4f} {r['ss']:>4}/{r['n_top']:<5} "
                  f"{r['direct_z_max']:>9.2f} {r['chain_z_max']:>10.2f} {elapsed:>5.0f}s", flush=True)
            r['name'] = name; r['indices'] = idx; r['time'] = elapsed
            results.append(r)

    print("\n=== KEY COMPARISONS ===")
    # Find specific entries by name
    by_name = {r['name']: r for r in results}
    print(f"a+e (recurrence vars 64bits):   Ω_3 = {by_name['a+e (recurr 64)']['omega3']:+.4f}")
    print(f"a+b (shift-coupled 64bits):     Ω_3 = {by_name['a+b (shift   64)']['omega3']:+.4f}")
    print(f"random 64 bits (control):       Ω_3 = {by_name['rand_64_seed1']['omega3']:+.4f}, "
          f"{by_name['rand_64_seed2']['omega3']:+.4f}, {by_name['rand_64_seed3']['omega3']:+.4f}")
    print(f"\nIndividual registers (32bits): " +
          ', '.join([f"{r}={by_name[f'reg_{r} (32)']['omega3']:+.3f}" for r in 'abcdefgh']))
    print(f"random 32 (control):  Ω_3 = {by_name['rand_32_seed1']['omega3']:+.4f}, {by_name['rand_32_seed2']['omega3']:+.4f}")

    print("\n--- INTERPRETATION ---")
    print("If a+e standalone gives Ω_3 ≫ random_64 → signal lives in recurrence vars (P6 lever)")
    print("If individual registers a,e are higher than b,c,d,f,g,h → recurrence vars carry it")
    print("If all subsets give similar Ω_3 → signal is delocalized (no localized lever)")

    with open(OUT, 'w') as f:
        json.dump({'meta': {'N': N, 'top_out': top_out, 'feature': 'bit5_max'},
                   'results': results}, f, indent=2)
    print(f"\nWrote {OUT}, total {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
