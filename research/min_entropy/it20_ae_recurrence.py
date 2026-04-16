"""IT-20: Omega_3 measured on (a,e) recurrence subspace.

Methodology: SHA-256 = single 8-order recurrence in {a[r]} (e via створочне).
Only 64 bits (a_new + e_new) are fresh per round; b,c,d,f,g,h are shift copies.

If Omega_3 = +0.98 lives PREDOMINANTLY in (a, e) registers (which carry the
recurrence dynamics), then the signal is a property of the RECURRENCE itself,
not of the redundant shift registers. This is the bridge to P6 — a non-birthday
algorithm for the (a,e) recurrence.

Subspaces tested:
  full:    all 256 bits of state1
  a:       state1[a]   = bits 0..31   (32 bits)
  e:       state1[e]   = bits 128..159
  a+e:     state1[a]+state1[e] = 64 bits  ← the recurrence variables
  a+b+c+d: 'top half' = bits 0..127
  e+f+g+h: 'bottom half' = bits 128..255
  random32: random 32 bits as control
  random64: random 64 bits as control

If Omega_3(a+e) ≈ +0.98 while Omega_3(any 64 random bits) ≈ 0 → SMOKING GUN
  for recurrence-localized signal.
"""
import json, math, os, time, random
from itertools import combinations
from math import comb
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'it20_ae_recurrence.json')


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


def compute_omega3(state1_subset_pm, state2_pm, fa_pm, top_out_bits, k_max=3):
    """Compute Omega_k for k=1,2,3 on given state1 subset."""
    n_bits = state1_subset_pm.shape[1]
    sN = math.sqrt(state1_subset_pm.shape[0])
    results = {}
    for k in range(1, k_max + 1):
        if comb(n_bits, k) > 200000:
            results[k] = None  # too many
            continue
        tuples = list(combinations(range(n_bits), k))
        # Compute chi_S for each tuple
        chi_arr = np.empty((len(tuples), state1_subset_pm.shape[0]), dtype=np.int8)
        for i, idx in enumerate(tuples):
            chi = state1_subset_pm[:, idx[0]].copy()
            for j in idx[1:]:
                chi = chi * state1_subset_pm[:, j]
            chi_arr[i] = chi
        z_in = (chi_arr @ fa_pm) / sN
        dz_arr = np.zeros(len(top_out_bits))
        cz_arr = np.zeros(len(top_out_bits))
        for j, ob in enumerate(top_out_bits):
            t_pm = state2_pm[:, ob]
            z_out_b = (chi_arr @ t_pm) / sN
            chain_b = (z_in * z_out_b).sum() / sN
            dz_arr[j] = (fa_pm @ t_pm) / sN
            cz_arr[j] = chain_b
        if np.std(dz_arr) < 1e-10 or np.std(cz_arr) < 1e-10:
            omega = 0.0
        else:
            omega = float(np.corrcoef(dz_arr, cz_arr)[0, 1])
        ss = int((np.sign(dz_arr) == np.sign(cz_arr)).sum())
        results[k] = {'omega': omega, 'ss': ss, 'n_top': len(top_out_bits),
                       'n_tuples': len(tuples), 'n_state1_bits': n_bits}
    return results


def main():
    t0 = time.time()
    inputs, pos = low_hw2(); N = len(inputs)
    print(f"# IT-20: Omega_3 on (a,e) recurrence subspace (N={N})")

    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    b2 = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    b2 = np.broadcast_to(b2, (N, 16))
    s2 = ch.compress(s1, b2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    s1b, s2b = sb(s1, N), sb(s2, N)
    print(f"# states computed")

    mp = np.asarray([p[-1] for p in pos]); fa = ((mp >> 5) & 1).astype(np.uint8)
    fa_pm = fa.astype(np.int8) * 2 - 1
    s1_pm = s1b.astype(np.int8) * 2 - 1
    s2_pm = s2b.astype(np.int8) * 2 - 1

    direct = np.array([(1 - 2*((fa^s2b[:,b]).sum())/N) * math.sqrt(N) for b in range(256)])
    top_out = np.argsort(-np.abs(direct))[:24].tolist()
    print(f"# top-24 output bits: {top_out[:8]}...")

    # SHA-256 register byte mapping (MSB-first within each word):
    # word 0 = a, word 1 = b, ..., word 7 = h. So a-bits = state1_bits[0..31]
    REGS = {
        'a': list(range(0, 32)),
        'b': list(range(32, 64)),
        'c': list(range(64, 96)),
        'd': list(range(96, 128)),
        'e': list(range(128, 160)),
        'f': list(range(160, 192)),
        'g': list(range(192, 224)),
        'h': list(range(224, 256)),
    }

    rng = random.Random(0xAEEDA)
    R32 = rng.sample(range(256), 32)
    R64 = rng.sample(range(256), 64)
    R128 = rng.sample(range(256), 128)

    SUBSETS = [
        ('full_256', list(range(256))),
        ('a_only', REGS['a']),
        ('e_only', REGS['e']),
        ('a+e (recurrence vars)', REGS['a'] + REGS['e']),
        ('b+c+d+f+g+h (shift copies)', REGS['b']+REGS['c']+REGS['d']+REGS['f']+REGS['g']+REGS['h']),
        ('a+b+c+d (top half)', REGS['a']+REGS['b']+REGS['c']+REGS['d']),
        ('e+f+g+h (bottom half)', REGS['e']+REGS['f']+REGS['g']+REGS['h']),
        ('random_32', R32),
        ('random_64', R64),
        ('random_128', R128),
    ]

    all_results = []
    for name, idx in SUBSETS:
        ts = time.time()
        sub_pm = s1_pm[:, idx]
        # k_max depends on size — Omega_3 is what we care about
        kmax = 3 if len(idx) >= 32 else min(3, len(idx))
        if comb(len(idx), 3) > 200000:
            kmax = 2
        r = compute_omega3(sub_pm, s2_pm, fa_pm, top_out, k_max=kmax)
        elapsed = time.time() - ts
        line = f"{name:<32} ({len(idx):>3} bits): "
        for k in [1, 2, 3]:
            if k in r and r[k] is not None:
                line += f"Ω_{k}={r[k]['omega']:+.3f}({r[k]['ss']}/{r[k]['n_top']}) "
            else:
                line += f"Ω_{k}=skip(too_many) "
        line += f" t={elapsed:.0f}s"
        print(line)
        all_results.append({'name': name, 'n_bits': len(idx), 'indices': idx, 'omega_k': r})

    print("\n=== INTERPRETATION ===")
    print("If Ω_3(a+e=64bits) ≫ Ω_3(random 64bits) → SIGNAL IS IN RECURRENCE VARIABLES.")
    print("If Ω_3(shift-copies=192bits) ≪ Ω_3(full=256bits) → shift copies don't carry it.")
    print("This determines whether the signal is a (a,e) recurrence invariant — bridging to P6.")

    with open(OUT, 'w') as f:
        json.dump({'meta': {'N': N, 'top_out': top_out, 'feature': 'bit5_max'},
                   'results': all_results}, f, indent=2)
    print(f"\nWrote {OUT}, total {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
