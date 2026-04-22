"""Analytical Lyapunov exponent extraction from OTOC curves.

For each hash, fit exponential decay to ||C(r)||_F² - F_inf:
    excess(r) = A · exp(-λ·r) + noise
where:
    λ = Lyapunov-equivalent per-round scrambling rate
    higher λ = faster scrambling per round

This gives ROUND-NORMALIZED cross-architecture comparison independent
of total round count.

Compare to theoretical classical analog of Maldacena-Shenker-Stanford
bound: λ ≤ 2π·ln(2)·T_eff for some discrete analog. For infinite
scrambling speed, λ → ∞. Real hash functions have finite λ.
"""
import json, os
import numpy as np


def load_otoc_data():
    """Load OTOC results from all hash measurements."""
    base = '/home/user/SHA-256/research/min_entropy'
    data = {}
    # SHA-256
    with open(f'{base}/otoc_sha256_results.json') as f:
        d = json.load(f)
        data['SHA-256'] = {
            'N': d['N_messages'],
            'rounds': [int(r) for r in d['results']],
            'frob': [d['results'][r]['frobenius_sq'] for r in d['results']],
            'F_inf': d['theoretical_limit'],
            'total_rounds': 64,
        }
    with open(f'{base}/otoc_sha3_rounds_results.json') as f:
        d = json.load(f)
        data['SHA-3-256'] = {
            'N': d['N'],
            'rounds': [int(r) for r in d['results']],
            'frob': [d['results'][r]['frobenius_sq'] for r in d['results']],
            'F_inf': d['theoretical_limit'],
            'total_rounds': 24,
        }
    with open(f'{base}/otoc_blake2s_rounds_results.json') as f:
        d = json.load(f)
        data['BLAKE2s'] = {
            'N': d['N'],
            'rounds': [int(r) for r in d['results']],
            'frob': [d['results'][r]['frobenius_sq'] for r in d['results']],
            'F_inf': d['theoretical_limit'],
            'total_rounds': 10,
        }
    with open(f'{base}/otoc_blake2b_rounds_results.json') as f:
        d = json.load(f)
        data['BLAKE2b'] = {
            'N': d['N'],
            'rounds': [int(r) for r in d['results']],
            'frob': [d['results'][r]['frobenius_sq'] for r in d['results']],
            'F_inf': d['theoretical_limit'],
            'total_rounds': 12,
        }
    return data


def fit_exponential(rounds, frob, F_inf):
    """Fit excess(r) = A · exp(-λ·r) via log-linear regression.

    Use only points where excess > 2σ_noise (approximate σ ≈ sqrt(F_inf/10)).
    """
    rs = np.array(rounds, dtype=float)
    excess = np.array(frob) - F_inf
    sigma_noise = np.sqrt(F_inf / 10)  # rough estimate
    mask = excess > 2 * sigma_noise
    if mask.sum() < 2:
        return None, None, 0
    r_fit = rs[mask]
    log_excess = np.log(excess[mask])
    slope, intercept = np.polyfit(r_fit, log_excess, 1)
    lambda_ = -slope
    A = np.exp(intercept)
    return lambda_, A, int(mask.sum())


def classical_mss_analog():
    """Discrete classical analog of Maldacena-Shenker-Stanford bound.

    Quantum MSS: λ_L ≤ 2π·k_B·T/ℏ for thermal system at temperature T.
    Classical discrete analog (heuristic):
    For n-bit output with entropy per round increase ≤ n (trivial bound),
    scrambling rate λ_max ≤ n·ln(2)  per round (bits flipped per round limit).

    For our OTOC with output of N_out bits, absolute max:
    λ_max ~ ln(M_avg/σ_limit) in one round where M_avg is initial excess.
    """
    return None  # heuristic bound, not derived rigorously


def main():
    print("# Lyapunov exponent fit across hash families")
    data = load_otoc_data()

    print(f"\n{'Hash':>10}  {'λ (1/round)':>12}  {'A':>10}  {'fit pts':>8}  "
          f"{'scrambling time τ':>18}  {'% of total':>10}")
    results = {}
    for name, d in data.items():
        lam, A, n = fit_exponential(d['rounds'], d['frob'], d['F_inf'])
        if lam is None:
            print(f"  {name:>10}  (insufficient data)")
            continue
        tau = 1 / lam  # e-fold time
        scramble_rounds = np.log(A) / lam  # rounds from initial to log-noise
        pct = scramble_rounds / d['total_rounds'] * 100
        results[name] = {'lambda': lam, 'A': A, 'tau': tau, 'scramble_r': scramble_rounds,
                         'pct_total': pct, 'n_points': n, 'total_rounds': d['total_rounds']}
        print(f"  {name:>10}  {lam:>12.3f}  {A:>10.1e}  {n:>8}  "
              f"τ = {tau:>6.2f} rounds  {pct:>9.1f}%")

    # Per-round mixing power ranking
    print(f"\n## Ranking by per-round scrambling rate λ (higher = faster):")
    sorted_by_lam = sorted(results.items(), key=lambda x: -x[1]['lambda'])
    for rank, (name, info) in enumerate(sorted_by_lam, 1):
        print(f"  {rank}. {name:<10} λ = {info['lambda']:.3f} /round (τ = {info['tau']:.2f} rounds)")

    # Cross-architecture insights
    print(f"\n## Architecture insights:")
    ratios = {}
    if 'SHA-256' in results:
        base_lam = results['SHA-256']['lambda']
        for name, info in results.items():
            if name != 'SHA-256':
                ratios[name] = info['lambda'] / base_lam
                print(f"  {name:<10} is {info['lambda']/base_lam:.1f}× faster per round than SHA-256")

    # Effective scrambling efficiency
    print(f"\n## Design efficiency (total rounds / scramble rounds):")
    for name, info in results.items():
        eff = info['total_rounds'] / info['scramble_r'] if info['scramble_r'] > 0 else 0
        print(f"  {name:<10}: {eff:.1f}× margin (total rounds / scramble rounds)")

    # Save
    out_path = '/home/user/SHA-256/research/min_entropy/otoc_lyapunov_fit_results.json'
    with open(out_path, 'w') as f:
        json.dump({'fits': results, 'ratios_vs_sha256': ratios}, f, indent=2)
    print(f"\nSaved: {out_path}")


if __name__ == '__main__': main()
