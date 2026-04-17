"""Phase 3A: which compression component drives Ω_3 collapse at r=17-20?

Chimera attribution — replace individual SHA-256 components with null
(identity, XOR, no-K) and measure whether Ω_3 still collapses.

Component variants to test:
  V0 baseline:      Full SHA-256 compression
  V1 no_Sigma:      Σ0/Σ1 in compression → identity (kills rotational mixing)
  V5 linear_chmaj:  Ch, Maj → XOR (kills nonlinear boolean mixing)
  V_no_carry:       All ADD (+) → XOR (kills carry propagation)
  V_no_K:           K[t] = 0 for all t (kills round-constant diversification)
  V_all_linear:     V1 + V5 + V_no_carry (fully linear compression)

Prediction: if one component dominates the collapse, killing it should
push collapse to later rounds (or eliminate it). Multiple components
contributing → all variants collapse but at different rates.
"""
import hashlib, json, os, time
import numpy as np

import sha256_chimera as ch
from oracle_gauge import low_hw2_inputs, make_feature, build_chi_arr, omega_k_fast


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase3a_chimera_attribution.json')

ROUNDS = [4, 8, 12, 16, 17, 18, 19, 20, 22, 24, 32, 64]

U32 = ch.U32
MASK = ch.MASK


def compress_partial(messages, num_rounds,
                      no_Sigma=False, linear_chmaj=False,
                      no_carry=False, no_K=False):
    """SHA-256 compression to arbitrary round with component ablations.

    Returns (N, 256) uint8 bits packed big-endian.
    """
    N = len(messages)
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)

    # Schedule always standard (Phase 2 showed it doesn't matter)
    W = np.empty((N, 64), dtype=U32)
    W[:, :16] = block
    for t in range(16, 64):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK

    Sg0 = (lambda x: x) if no_Sigma else ch.Sigma0
    Sg1 = (lambda x: x) if no_Sigma else ch.Sigma1
    chf = ch.linear3_xor if linear_chmaj else ch.Ch
    maf = ch.linear3_xor if linear_chmaj else ch.Maj
    K_vals = np.zeros(64, dtype=U32) if no_K else ch.K_VANILLA

    # ADD or XOR
    if no_carry:
        def add(*args):
            # Broadcast scalars to array shape
            arr_args = [np.broadcast_to(np.asarray(a, dtype=U32), args[0].shape)
                        if np.isscalar(a) or getattr(a, 'ndim', 1) == 0 else a
                        for a in args]
            r = arr_args[0].astype(U32).copy()
            for x in arr_args[1:]:
                r = (r ^ x.astype(U32))
            return r.astype(U32)
    else:
        def add(*args):
            r = args[0].astype(np.uint64).copy()
            for x in args[1:]:
                r = r + np.asarray(x, dtype=np.uint64)
            return (r & MASK).astype(U32)

    iv = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))

    for t in range(min(num_rounds, 64)):
        T1 = add(h, Sg1(e), chf(e, f, g), U32(K_vals[t]), W[:, t])
        T2 = add(Sg0(a), maf(a, b, c))
        h = g; g = f; f = e
        e = add(d, T1)
        d = c; c = b; b = a
        a = add(T1, T2)

    state = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    state_bytes = state.view('<u1').reshape(N, 8, 4)[:, :, ::-1].reshape(N, 32)
    bits = np.unpackbits(state_bytes, axis=1, bitorder='big')
    return bits


def run_variant(inputs, fa, variant_name, flags, verbose=True):
    """Run Ω_3 probe on a variant."""
    # χ_S basis: state at r=4 with SAME variant flags
    state_chi = compress_partial(inputs, 4, **flags)
    chi_arr, _ = build_chi_arr(state_chi, k=3, subset_size=32)

    results = []
    for r in ROUNDS:
        ts = time.time()
        target_bits = compress_partial(inputs, r, **flags)
        omega, ss, _, _, _ = omega_k_fast(chi_arr, target_bits, fa)
        results.append({'r': r, 'omega': float(omega), 'ss': int(ss)})
        if verbose:
            print(f"  [{variant_name:16s}] r={r:>2}: Ω_3 = {omega:+.3f}  "
                  f"ss={ss:>3}/256  ({time.time()-ts:.0f}s)")
    return results


def main():
    t0 = time.time()
    print("# Phase 3A: chimera attribution of Ω_3 collapse")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    fa = make_feature(pos, 'bit5_max')
    print(f"# N = {N}, k=3, ROUNDS = {ROUNDS}")

    variants = [
        ('V0_baseline',    dict()),
        ('V1_no_Sigma',    dict(no_Sigma=True)),
        ('V5_linear_ChMaj',dict(linear_chmaj=True)),
        ('V_no_carry',     dict(no_carry=True)),
        ('V_no_K',         dict(no_K=True)),
        ('V_all_linear',   dict(no_Sigma=True, linear_chmaj=True, no_carry=True)),
    ]

    results = {}
    for name, flags in variants:
        print(f"\n## {name}: flags = {flags}")
        results[name] = run_variant(inputs, fa, name, flags)

    # Analysis: find collapse round (Ω drops from >0.7 to <0.3)
    def find_collapse(res):
        above = False
        for e in res:
            if e['omega'] > 0.7: above = True
            if above and e['omega'] < 0.3: return e['r']
        return None

    # Summary
    print(f"\n=== PHASE 3A RESULTS ===")
    header = ['r'] + [n for n, _ in variants]
    print(f"{'r':>3} | " + " | ".join(f"{n:>16}" for n in [n for n, _ in variants]))
    print(f"{'-'*3}-+-" + "-+-".join("-"*16 for _ in variants))
    for r in ROUNDS:
        row = [f"{r:>3}"]
        for name, _ in variants:
            e = next(x for x in results[name] if x['r'] == r)
            row.append(f"{e['omega']:>+16.3f}")
        print(" | ".join(row))

    print(f"\n## Collapse round (Ω: 0.7→0.3):")
    for name, _ in variants:
        rc = find_collapse(results[name])
        print(f"  {name:16s}: r_collapse = {rc}")

    # Compute "final Ω at r=24" as persistence metric
    print(f"\n## Final Ω_3 at r=24 (should be RO-like ≈0.05 for normal SHA):")
    for name, _ in variants:
        e = next(x for x in results[name] if x['r'] == 24)
        print(f"  {name:16s}: Ω_3(r=24) = {e['omega']:+.3f}")

    out = {
        'N': N,
        'rounds': ROUNDS,
        'variants': {n: r for (n, _), r in zip(variants, [results[n] for n, _ in variants])},
        'collapse_round': {n: find_collapse(results[n]) for n, _ in variants},
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
