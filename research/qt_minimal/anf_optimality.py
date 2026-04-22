"""
Проверка: даёт ли stacking ortho-checks на разных позициях
ДОПОЛНИТЕЛЬНЫЙ speedup, или это просто эквивалент одиночного проверяющего
большего k?

Теоретически: оптимальный k = log2(V·ln2) где V = стоимость полной
верификации. Выше этого — checks стоят дороже, чем экономят full-verify.

Если stacking != merge, то должна быть численная разница.
"""
import time, random
from anf_early_verify import (
    forward, invert_early_k, invert_stacked_k, build_M_inv
)


def cost_model(L, V_full, k_or_positions, n_candidates):
    """Return (ops_baseline, ops_early).
    V_full = cost of 1 full-verify (in some unit).
    k_or_positions = scalar k or list of positions."""
    if isinstance(k_or_positions, int):
        k = k_or_positions
        positions = list(range(1, k + 1))
    else:
        positions = k_or_positions
        k = len(positions)
    early_walk_cost = max(positions)  # walk to highest position
    ops_baseline = n_candidates * V_full
    # Expected pass rate for uncorrelated bits: 0.5^k
    expected_full = n_candidates * 0.5**k
    ops_early = n_candidates * early_walk_cost + expected_full * V_full
    return ops_baseline, ops_early, ops_baseline / ops_early


def run_at_L(L, V_fulls=(16, 100, 1000)):
    N = 1 << (L - 1)  # candidates
    print(f"\n=== L={L}  (candidates = 2^{L-1} = {N}) ===")

    configs = [
        ("k=2 low", [1,2]),
        ("k=4 low", [1,2,3,4]),
        ("k=6 low", [1,2,3,4,5,6]),
        ("k=8 low", [1,2,3,4,5,6,7,8]),
        ("k=10 low", list(range(1,11))),
        (f"k=3 spread 0+{L//2}+{L-1}", [1,2,3, L//2, L//2+1, L//2+2, L-3, L-2, L-1] if L >= 9 else None),
        (f"2× k=3: low+high", [1,2,3, L-3, L-2, L-1] if L >= 7 else None),
    ]
    for V in V_fulls:
        print(f"\n  -- V (full-verify cost unit) = {V} --")
        print(f"  {'config':<30} {'early_walk':>11} {'effective_k':>12} {'speedup':>10}")
        for label, positions in configs:
            if positions is None: continue
            _, _, speedup = cost_model(L, V, positions, N)
            k_eff = len(positions)
            walk = max(positions)
            print(f"  {label:<30} {walk:>11d} {k_eff:>12d} {speedup:>10.2f}x")


def stacked_independence_scale(L, n_trials=20, seed=42):
    """Verify: at higher L, does stacking still give independent pass rates?
    Test triple stack: low+mid+high, 3 bits each = 9 effective."""
    random.seed(seed)
    mask = (1 << L) - 1
    pos_low = [1, 2, 3]
    pos_mid = [L//2, L//2+1, L//2+2]
    pos_high = [L-3, L-2, L-1]

    print(f"\n=== L={L} Triple-stacking independence test ===")
    # We need to modify: do THREE checks. Write inline.
    total_full = 0
    total_p1 = 0
    total_p2_given_1 = 0
    total_p3_given_12 = 0
    for t in range(n_trials):
        x_true = random.randint(0, mask)
        K = random.randint(0, mask)
        y, C = forward(x_true, K, L)
        # enumerate
        M_inv = build_M_inv(L)
        from anf_early_verify import gf2_matvec, M_apply, carry_chain_partial
        pos1_mask = sum(1<<p for p in pos_low)
        pos2_mask = sum(1<<p for p in pos_mid)
        pos3_mask = sum(1<<p for p in pos_high)
        p1_passes = p2_passes = p3_passes = 0
        full = 0
        for C_idx in range(1 << (L - 1)):
            C_cand = C_idx << 1
            x_add = (y ^ K ^ C_cand) & mask
            x = gf2_matvec(M_inv, x_add, L)
            if carry_chain_partial(M_apply(x, L), K, L, pos_low) != (C_cand & pos1_mask):
                continue
            p1_passes += 1
            if carry_chain_partial(M_apply(x, L), K, L, pos_mid) != (C_cand & pos2_mask):
                continue
            p2_passes += 1
            if carry_chain_partial(M_apply(x, L), K, L, pos_high) != (C_cand & pos3_mask):
                continue
            p3_passes += 1
            full += 1
        total_full += full
        total_p1 += p1_passes
        total_p2_given_1 += p2_passes
        total_p3_given_12 += p3_passes

    n_total = n_trials * (1 << (L-1))
    p1 = total_p1 / n_total
    p2 = total_p2_given_1 / max(total_p1, 1)
    p3 = total_p3_given_12 / max(total_p2_given_1, 1)
    print(f"  P(low pass)          = {p1:.4f}  (expect 0.5^3={0.5**3:.4f})")
    print(f"  P(mid pass | low)    = {p2:.4f}  (expect 0.5^3)")
    print(f"  P(high pass | l+m)   = {p3:.4f}  (expect 0.5^3)")
    print(f"  Joint pass rate       = {total_p3_given_12/n_total:.6f}  (expect 0.5^9={0.5**9:.6f})")
    print(f"  avg full after 9-bit = {total_full / n_trials:.1f}")


if __name__ == "__main__":
    print("=== ANF Early-verify Optimality Analysis ===")

    # Scenario 1: cost-model projection across L
    for L_test in [16, 24, 32]:
        run_at_L(L_test)

    # Scenario 2: empirical triple-stack independence
    stacked_independence_scale(16, n_trials=10)
