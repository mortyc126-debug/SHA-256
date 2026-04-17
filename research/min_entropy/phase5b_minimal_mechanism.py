"""Phase 5B: minimal mechanism — isolate single-component contributions.

Two missing variants to complete the 2×2×2 component matrix:
  V_only_carry: Σ→identity, Ch/Maj→XOR, carry kept. Tests carry alone.
  V_only_chmaj: Σ→identity, carry→XOR, Ch/Maj kept. Tests Ch/Maj alone.

Plus fine-grained trace of V_sigma_only (every round r=1..32) to map
sign-flip pattern.

Prior findings:
  Σ + carry + Ch/Maj   (baseline)         → destroyed    |Ω|=0.07
  Σ + carry            (V5)               → destroyed    |Ω|=0.06
  Σ + Ch/Maj           (V_no_carry)       → destroyed    |Ω|=0.05
  Σ alone              (V_sigma_only)     → shuffled     |Ω|=0.47
  — + carry + Ch/Maj   (V1_no_Sigma)      → preserved    |Ω|=0.74
  — + —  + —           (V_all_linear)     → preserved    |Ω|=0.87

Missing:
  — + carry            (V_only_carry)     → ?
  — + Ch/Maj           (V_only_chmaj)     → ?

Question: do carry OR Ch/Maj destroy Ω_3 without Σ partner?
"""
import json, os, time
import numpy as np

from oracle_gauge import low_hw2_inputs, make_feature, build_chi_arr, omega_k_fast
from phase3a_chimera_attribution import compress_partial


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase5b_minimal_mechanism.json')

COARSE_ROUNDS = [4, 8, 16, 20, 24, 32, 48, 64]
FINE_ROUNDS = list(range(4, 33))  # every round r=4..32


def run_variant(inputs, fa, name, flags, rounds, verbose=True):
    state_chi = compress_partial(inputs, 4, **flags)
    chi_arr, _ = build_chi_arr(state_chi, k=3, subset_size=32)
    results = []
    for r in rounds:
        ts = time.time()
        target = compress_partial(inputs, r, **flags)
        omega, ss, _, _, _ = omega_k_fast(chi_arr, target, fa)
        results.append({'r': r, 'omega': float(omega), 'ss': int(ss)})
        if verbose:
            print(f"  [{name:20s}] r={r:>2}: Ω_3 = {omega:+.4f}  ss={ss:>3}/256  ({time.time()-ts:.0f}s)")
    return results


def main():
    t0 = time.time()
    print("# Phase 5B: minimal mechanism + fine sign-flip trace")
    inputs, pos = low_hw2_inputs()
    fa = make_feature(pos, 'bit5_max')

    # Two missing variants
    print("\n## V_only_carry (no Σ, XOR Ch/Maj, keep +)")
    only_carry = run_variant(
        inputs, fa, 'V_only_carry',
        dict(no_Sigma=True, linear_chmaj=True, no_carry=False),
        COARSE_ROUNDS)

    print("\n## V_only_chmaj (no Σ, XOR +, keep Ch/Maj)")
    only_chmaj = run_variant(
        inputs, fa, 'V_only_chmaj',
        dict(no_Sigma=True, linear_chmaj=False, no_carry=True),
        COARSE_ROUNDS)

    # Fine-grained trace of V_sigma_only to map sign-flip
    print("\n## V_sigma_only fine trace (every round r=4..32)")
    sigma_only_fine = run_variant(
        inputs, fa, 'V_sigma_only',
        dict(no_Sigma=False, linear_chmaj=True, no_carry=True),
        FINE_ROUNDS)

    # Analysis
    print(f"\n=== RESULTS ===")
    print(f"{'r':>3} | {'V_only_carry':>13} | {'V_only_chmaj':>13}")
    for r in COARSE_ROUNDS:
        a = next(e['omega'] for e in only_carry if e['r'] == r)
        b = next(e['omega'] for e in only_chmaj if e['r'] == r)
        print(f"{r:>3} | {a:>+13.4f} | {b:>+13.4f}")

    print(f"\n=== V_sigma_only fine trace: sign pattern ===")
    print(f"{'r':>3}  {'Omega_3':>9}  sign")
    prev_sign = 1
    sign_flips = []
    for e in sigma_only_fine:
        sign = +1 if e['omega'] >= 0 else -1
        marker = "  SIGN FLIP!" if sign != prev_sign else ""
        print(f"{e['r']:>3}  {e['omega']:>+8.4f}  {'+' if sign>0 else '-'}{marker}")
        if sign != prev_sign:
            sign_flips.append(e['r'])
        prev_sign = sign

    print(f"\n## Sign flips in V_sigma_only: {sign_flips}")

    # Interpretation
    print(f"\n## Interpretation of single-component tests:")
    only_carry_r24 = next(e['omega'] for e in only_carry if e['r'] == 24)
    only_chmaj_r24 = next(e['omega'] for e in only_chmaj if e['r'] == 24)
    print(f"  V_only_carry(r=24) = {only_carry_r24:+.4f}")
    print(f"  V_only_chmaj(r=24) = {only_chmaj_r24:+.4f}")
    if abs(only_carry_r24) > 0.3:
        print(f"  ✓ carry alone without Σ preserves some |Ω_3|")
    else:
        print(f"  ✗ carry alone destroys Ω_3 even without Σ")
    if abs(only_chmaj_r24) > 0.3:
        print(f"  ✓ Ch/Maj alone without Σ preserves some |Ω_3|")
    else:
        print(f"  ✗ Ch/Maj alone destroys Ω_3 even without Σ")

    out = {
        'V_only_carry': only_carry,
        'V_only_chmaj': only_chmaj,
        'V_sigma_only_fine': sigma_only_fine,
        'sign_flips_sigma_only': sign_flips,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
