"""Phase 2: Test if Ω_k collapse at r=17-20 is caused by schedule nonlinearity.

Three schedule variants:
  A. Standard: W[16..63] = σ1(W[i-2]) + W[i-7] + σ0(W[i-15]) + W[i-16]
     (baseline, reproduces Phase 1)
  B. Fixed random: W[16..63] = fixed values, seeded from constant.
     Input-independent but W-diverse. Breaks input→schedule coupling.
  C. Zero: W[16..63] = 0. Simplest null — no schedule dynamics.

Hypothesis: if Ω_k collapse is due to schedule nonlinearity, then
variants B and C should NOT show collapse at r=17-20 (Ω_k stays high).

Measure Ω_3 at k=3 only (fastest) across rounds for each variant.
"""
import hashlib, json, os, time
import numpy as np

import sha256_chimera as ch
from oracle_gauge import low_hw2_inputs, make_feature, build_chi_arr, omega_k_fast


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase2_schedule_nonlinearity.json')

ROUNDS = [4, 8, 12, 16, 17, 18, 19, 20, 24, 32, 48, 64]


def sha256_partial_custom(messages, num_rounds, W_override=None):
    """Compute SHA-256 state after num_rounds with optional W[16..63] override.

    W_override: None (standard) or np.array (64,) dtype=U32 for W[16..63] values.
    """
    N = len(messages)
    U32 = ch.U32
    MASK = ch.MASK
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)

    W = np.empty((N, 64), dtype=U32)
    W[:, :16] = block

    if W_override is None:
        # Standard schedule
        for t in range(16, 64):
            W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                       + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    else:
        # Override: W[t] = W_override[t] for t=16..63 (broadcast across N)
        for t in range(16, 64):
            W[:, t] = W_override[t]

    iv = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    for t in range(min(num_rounds, 64)):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK

    state = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    state_bytes = state.view('<u1').reshape(N, 8, 4)[:, :, ::-1].reshape(N, 32)
    bits = np.unpackbits(state_bytes, axis=1, bitorder='big')
    return bits


def run_variant(inputs, fa, W_override, label, verbose=True):
    """Run Ω_3 probe on a schedule variant."""
    N = len(inputs)

    # χ_S basis: state at r=4 with SAME schedule variant
    state_chi = sha256_partial_custom(inputs, 4, W_override)
    chi_arr, _ = build_chi_arr(state_chi, k=3, subset_size=32)
    chi_arr_f32 = chi_arr.astype(np.float32)

    results = []
    for r in ROUNDS:
        ts = time.time()
        target_bits = sha256_partial_custom(inputs, r, W_override)
        omega, ss, _, _, _ = omega_k_fast(chi_arr, target_bits, fa)
        results.append({'r': r, 'omega': float(omega), 'ss': int(ss)})
        if verbose:
            print(f"  [{label:20s}] r={r:>2}: Ω_3 = {omega:+.3f}  ss={ss}/256  ({time.time()-ts:.0f}s)")
    return results


def main():
    t0 = time.time()
    print("# Phase 2: Schedule nonlinearity as cause of Ω_k collapse at r=17")
    inputs, pos = low_hw2_inputs()
    N = len(inputs)
    fa = make_feature(pos, 'bit5_max')
    print(f"# N = {N}, k=3, ROUNDS = {ROUNDS}")

    variants = {}

    # A. Standard schedule (baseline)
    print("\n## A. Standard schedule (baseline, should show collapse at r=17-20)")
    variants['A_standard'] = run_variant(inputs, fa, None, 'A_standard')

    # B. Fixed random W[16..63] — seeded
    print("\n## B. Fixed random W[16..63] (input-independent constants)")
    rng = np.random.default_rng(0x5C4EDED1)
    W_random = np.zeros(64, dtype=ch.U32)
    W_random[16:] = rng.integers(0, 2**32, size=48, dtype=np.int64).astype(ch.U32)
    variants['B_fixed_random'] = run_variant(inputs, fa, W_random, 'B_fixed_random')

    # C. Zero W[16..63]
    print("\n## C. Zero W[16..63]")
    W_zero = np.zeros(64, dtype=ch.U32)
    variants['C_zero'] = run_variant(inputs, fa, W_zero, 'C_zero')

    # Analysis
    print(f"\n=== PHASE 2 ANALYSIS ===")
    print(f"{'r':>3} | {'A_standard':>11} | {'B_fixed_rand':>12} | {'C_zero':>8}")
    print(f"{'-'*3}-+-{'-'*11}-+-{'-'*12}-+-{'-'*8}")
    for r in ROUNDS:
        a = next(e['omega'] for e in variants['A_standard'] if e['r'] == r)
        b = next(e['omega'] for e in variants['B_fixed_random'] if e['r'] == r)
        c = next(e['omega'] for e in variants['C_zero'] if e['r'] == r)
        print(f"{r:>3} | {a:>+11.3f} | {b:>+12.3f} | {c:>+8.3f}")

    # Phase transition test: does collapse (Ω drop from >0.5 to <0.3) occur at r=17-20?
    def finds_collapse(res):
        """Returns first r where Ω drops below 0.3 after being above 0.7."""
        above = False
        for e in res:
            if e['omega'] > 0.7: above = True
            if above and e['omega'] < 0.3: return e['r']
        return None

    print(f"\n## Collapse detection (r at which Ω drops 0.7→0.3):")
    for label, res in variants.items():
        r_coll = finds_collapse(res)
        print(f"  {label:20s}: r_collapse = {r_coll}")

    # Verdict
    a_collapse = finds_collapse(variants['A_standard'])
    b_collapse = finds_collapse(variants['B_fixed_random'])
    c_collapse = finds_collapse(variants['C_zero'])

    print(f"\n## Verdict:")
    if a_collapse and a_collapse <= 20:
        print(f"  ✓ Standard schedule collapses at r={a_collapse} (reproduces Phase 1)")
    else:
        print(f"  ✗ Standard did NOT collapse as expected!")

    if b_collapse is None or b_collapse > 25:
        print(f"  ✓ Fixed-random schedule does NOT collapse (or late) — confirms schedule nonlinearity is causal")
    else:
        print(f"  ✗ Fixed-random also collapses at r={b_collapse} — schedule nonlinearity NOT the sole cause")

    if c_collapse is None or c_collapse > 25:
        print(f"  ✓ Zero schedule does NOT collapse (or late)")
    else:
        print(f"  ✗ Zero schedule also collapses at r={c_collapse}")

    out = {
        'N': N,
        'rounds': ROUNDS,
        'variants': variants,
        'W_random_seed': '0x5C4EDED1',
        'r_collapse': {k: finds_collapse(v) for k, v in variants.items()},
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
