"""Phase 6A: analytical diagonalization of the Σ-only round matrix.

Goals:
1. Compute minimal polynomial of M over GF(2) to reveal cycle structure
2. Compute complex eigenvalues of M (as real matrix) to quantify damping
3. Connect eigenspectrum to observed Ω_3 oscillation pattern

The V_sigma_only round matrix is built in phase4a. Minimal polynomial
μ(x) gives the smallest polynomial over F_2 killing M: μ(M)=0.
Its factorization tells us cycle lengths of M-action.
"""
import json, os, time
import numpy as np

from phase4a_gf2_mixing import build_round_matrix


OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'phase6a_diagonalization.json')


def gf2_minimal_polynomial(M):
    """Compute minimal polynomial of M over GF(2) using iterative approach.

    Iteratively computes M^0, M^1, ... as flattened vectors in GF(2)^(n²),
    finds smallest r such that {vec(M^i)}_{i=0}^{r} is linearly dependent.
    That gives minimal polynomial of degree ≤ r.
    """
    n = M.shape[0]
    powers = [np.eye(n, dtype=np.uint8)]
    vecs = [powers[0].flatten()]
    # Incrementally build basis
    basis = [vecs[0].copy()]
    basis_echelon = [vecs[0].copy()]  # row-reduced
    max_deg = n  # minimal poly degree ≤ n
    M_pow = np.eye(n, dtype=np.uint8)
    for i in range(1, max_deg + 1):
        M_pow = (M_pow @ M) % 2
        v = M_pow.flatten().copy()
        # Try to reduce v against echelon basis
        reduction_coeffs = np.zeros(i, dtype=np.uint8)
        w = v.copy()
        for j, ref in enumerate(basis_echelon):
            pivot_col = np.argmax(ref != 0)
            if ref[pivot_col] and w[pivot_col]:
                w ^= ref
                reduction_coeffs[j] = 1
        if not w.any():
            # v is linear combination — minimal polynomial found
            # μ(x) = x^i + Σ_{j: reduction_coeffs[j]=1} x^j
            coeffs = np.zeros(i + 1, dtype=np.uint8)
            coeffs[i] = 1
            for j in range(i):
                coeffs[j] = reduction_coeffs[j]
            return coeffs
        # Add w to echelon
        basis_echelon.append(w)
        basis.append(v)
    return None  # not found within degree n


def gf2_poly_factor_candidates(coeffs):
    """Enumerate small irreducible factors: (x+1), (x^2+x+1), etc., check divisibility."""
    # Just check whether (x+1) is a factor: μ(1) should be 0
    # And (x^2+x+1) factor: μ(ω) = 0 where ω^2+ω+1=0
    n = len(coeffs) - 1

    # Check μ(1)
    mu_at_1 = sum(int(c) for c in coeffs) % 2
    has_x_plus_1 = (mu_at_1 == 0)

    # For small factor tests — compute polynomial at GF(2^k) roots
    # Simpler: just report degree and whether (x+1) divides
    return {
        'degree': n,
        'divides_by_x_plus_1': has_x_plus_1,
        'num_nonzero_coeffs': int(sum(int(c) for c in coeffs)),
    }


def complex_eigenvalue_analysis(M):
    """Treat M (GF(2)) as real {0,1} matrix and compute complex eigenvalues.

    This is not literally M's GF(2) spectrum, but the complex eigenvalues
    of the linear operator view — connects to observed damped oscillator.
    """
    M_real = M.astype(np.float64)
    eigvals = np.linalg.eigvals(M_real)
    # Sort by |λ|
    order = np.argsort(-np.abs(eigvals))
    eigvals = eigvals[order]
    return eigvals


def characterize_oscillation(eigvals):
    """Find eigenvalues near unit circle with nonzero imaginary part — candidate oscillators."""
    oscillator_modes = []
    for i, λ in enumerate(eigvals):
        mag = abs(λ)
        phase = np.angle(λ)
        # Non-real eigenvalue (imaginary part > small threshold)
        if abs(phase) > 0.01 and abs(phase) < np.pi - 0.01:
            # Period of oscillation (rounds per cycle)
            period = 2 * np.pi / abs(phase) if abs(phase) > 0 else float('inf')
            # Damping: decay factor per round
            damping = -np.log(mag) if mag > 0 else float('inf')
            oscillator_modes.append({
                'index': i,
                'magnitude': mag,
                'phase_rad': phase,
                'period_rounds': period,
                'damping_per_round': damping,
            })
    return oscillator_modes


def main():
    t0 = time.time()
    print("# Phase 6A: diagonalization of Σ-only round matrix")

    M = build_round_matrix()
    print(f"# Matrix 256×256, density = {M.sum()/M.size:.3f}")

    # Compute minimal polynomial
    print(f"\n## Computing minimal polynomial over GF(2)...")
    ts = time.time()
    mu = gf2_minimal_polynomial(M)
    if mu is None:
        print(f"  minimal polynomial: NOT FOUND (within deg ≤ 256)")
    else:
        print(f"  minimal polynomial: degree {len(mu) - 1}, Hamming weight {int(mu.sum())}")
        print(f"  coeffs: {mu.tolist()}")
        info = gf2_poly_factor_candidates(mu)
        print(f"  info: {info}")
    print(f"  time: {time.time()-ts:.1f}s")

    # Compute complex eigenvalues
    print(f"\n## Computing complex eigenvalues of M (as real {{0,1}} matrix)...")
    ts = time.time()
    eigvals = complex_eigenvalue_analysis(M)
    print(f"  {len(eigvals)} eigenvalues, max |λ| = {abs(eigvals[0]):.4f}, "
          f"min |λ| = {abs(eigvals[-1]):.4f}  ({time.time()-ts:.1f}s)")

    # Top 10 by magnitude
    print(f"\n  Top 10 eigenvalues by |λ|:")
    for i in range(min(10, len(eigvals))):
        λ = eigvals[i]
        print(f"    #{i+1}: |λ|={abs(λ):.4f}  phase={np.angle(λ):+.4f} rad "
              f"({np.angle(λ)*180/np.pi:+.1f}°)")

    # Characterize oscillator modes
    oscillators = characterize_oscillation(eigvals)
    print(f"\n## Oscillator modes (non-real eigenvalues):")
    print(f"  Total: {len(oscillators)}")
    # Sort by |magnitude| to find dominant oscillations
    oscillators.sort(key=lambda x: -x['magnitude'])
    print(f"\n  Top 10 by |λ|:")
    for o in oscillators[:10]:
        print(f"    |λ|={o['magnitude']:.3f}  "
              f"period={o['period_rounds']:.2f} rounds  "
              f"damping={o['damping_per_round']:.4f}/round")

    # Find period-2 candidate (phase ≈ π)
    period_2 = [o for o in oscillators
                if 1.9 < o['period_rounds'] < 2.1]
    print(f"\n  Period-2 oscillators (|phase| ≈ π): {len(period_2)}")
    for o in period_2[:5]:
        print(f"    |λ|={o['magnitude']:.3f}, period={o['period_rounds']:.3f}")

    # Prediction: at what round does largest oscillator damp to |Ω|<0.1?
    if oscillators:
        top = oscillators[0]
        if top['magnitude'] < 1:
            rounds_to_decay = -np.log(0.1 / 1.0) / top['damping_per_round']
            print(f"\n## Prediction from top oscillator (|λ|={top['magnitude']:.3f}):")
            print(f"   Rounds for |Ω| to drop from 1.0 to 0.1: {rounds_to_decay:.1f}")
            print(f"   Observed: V_sigma_only |Ω|=0.47 at r=24, ≈0.02 at r=30")

    out = {
        'minimal_polynomial': {
            'degree': len(mu) - 1 if mu is not None else None,
            'hamming_weight': int(mu.sum()) if mu is not None else None,
            'coeffs': mu.tolist() if mu is not None else None,
        },
        'eigenvalues': [
            {'real': float(λ.real), 'imag': float(λ.imag),
             'magnitude': float(abs(λ)), 'phase': float(np.angle(λ))}
            for λ in eigvals[:50]
        ],
        'oscillator_modes_top': [
            {'magnitude': o['magnitude'],
             'period_rounds': o['period_rounds'],
             'damping_per_round': o['damping_per_round']}
            for o in oscillators[:20]
        ],
        'period_2_count': len(period_2),
        'runtime_sec': time.time() - t0,
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\n# Saved: {OUT_JSON}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__':
    main()
