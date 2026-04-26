"""
Scaling of local Jacobian deficit vs (n, R).

Tests:
  1. Deficit(n, R) for n in {4,8,12,16,20,24,28,32}, R in {1,2,4,8}
  2. Fit formula: does deficit ≈ f(n) independent of R?
  3. Distinguish TRIVIAL part (MSB arithmetic) from state-dependent.
"""
import numpy as np
import random, time
from cohomology_probe import compute_full_carries_trace, gf2_rank
from mini_sha import gen_IV


def jacobian_deficit(n, R, n_anchors=30, seed=42):
    random.seed(seed)
    mask = (1 << n) - 1
    H0 = gen_IV(n)
    input_bits = n * R

    deficits = []
    # Also track: are MSBs of each W word consistently in kernel?
    msb_contributes = {r: 0 for r in range(R)}

    for a in range(n_anchors):
        W_base = [random.randint(0, mask) for _ in range(R)]
        cs_base = compute_full_carries_trace(W_base, H0, R, n)
        total_bits = len(cs_base)
        J = np.zeros((input_bits, total_bits), dtype=np.uint8)
        for i in range(input_bits):
            r = i // n; b = i % n
            W_flip = list(W_base)
            W_flip[r] ^= (1 << b)
            cs_flip = compute_full_carries_trace(W_flip, H0, R, n)
            J[i] = cs_flip ^ cs_base
        rank = gf2_rank(J)
        deficit = input_bits - rank
        deficits.append(deficit)

        # Check MSB contribution: do MSB rows of J have zero sum?
        for r in range(R):
            msb_idx = r * n + (n - 1)
            if J[msb_idx].sum() == 0:
                msb_contributes[r] += 1

    import statistics
    mean = statistics.mean(deficits)
    std = statistics.stdev(deficits) if len(deficits) > 1 else 0
    msb_always_zero = [r for r in range(R) if msb_contributes[r] == n_anchors]
    return {
        "n": n, "R": R, "input_bits": input_bits,
        "mean_deficit": mean, "std_deficit": std,
        "min_deficit": min(deficits), "max_deficit": max(deficits),
        "msb_always_in_kernel": msb_always_zero,
    }


if __name__ == "__main__":
    print(f"{'n':>3} {'R':>3} {'input':>6} {'mean_d':>8} {'std':>6} {'min':>4} {'max':>4}  msb_always_zero_words")
    results = []
    for n in [4, 8, 12, 16, 20, 24, 28, 32]:
        for R in [1, 2, 4, 6]:
            try:
                t0 = time.time()
                res = jacobian_deficit(n, R, n_anchors=20)
                dt = time.time() - t0
                print(f"{n:>3} {R:>3} {res['input_bits']:>6d} {res['mean_deficit']:>8.2f} "
                      f"{res['std_deficit']:>6.2f} {res['min_deficit']:>4d} {res['max_deficit']:>4d}  "
                      f"{res['msb_always_in_kernel']}  ({dt:.1f}s)")
                results.append(res)
            except Exception as e:
                print(f"{n:>3} {R:>3}  ERR: {e}")

    # Fit deficit ~ n
    print("\n--- Mean deficit aggregated across R ---")
    print(f"{'n':>3} {'mean_across_R':>15}")
    from collections import defaultdict
    n_means = defaultdict(list)
    for r in results:
        n_means[r['n']].append(r['mean_deficit'])
    for n in sorted(n_means.keys()):
        avg = sum(n_means[n]) / len(n_means[n])
        print(f"{n:>3} {avg:>15.2f}")
