"""
ANF early-verify scoping (§132/§133 extension).

§132 model (reproduced from METHODOLOGY.md):
  - Simplified "round":  y = M·x + K + C(x, K)  (mod 2^L)
    where M is GF(2) linear (rotation+XOR, like Σ), K round constant,
    C = carry-chain from adding (M·x) + K.
  - Inversion problem: given y, find x.
  - Baseline: enumerate 2^{L-1} candidates for C, solve M·x = y - K - C.
  - §132 shortcut: for each candidate C, verify first k bits of
    C_actual(x_derived) == C[0..k-1] cheaply. Reject 63/64 candidates
    without full round verify.

We test:
  1. Baseline §132 at L=16 → expect ~9× at full recall (per §133).
  2. Scale to L=32 (real SHA register width).
  3. Stacking: k-bit check at position 0 + k-bit check at position L/2
     — are they independent, do they multiply speedup?
  4. Optimal k selection for different L.
"""
import time, random
import numpy as np


def rotr(x, r, L):
    mask = (1 << L) - 1
    return ((x >> r) | (x << (L - r))) & mask


def M_apply(x, L):
    """Simplified M: three rotations XORed (like Σ). Rotations scaled by L."""
    # Choose rotations: approximately L/8, L/2.5, L*0.7 but ensuring <L
    r1, r2, r3 = 2, max(L // 3, 3), max(2 * L // 3 - 1, 5)
    # Clamp so all < L
    r1 = r1 % L if L > 1 else 0
    r2 = r2 % L if L > 1 else 0
    r3 = r3 % L if L > 1 else 0
    return rotr(x, r1, L) ^ rotr(x, r2, L) ^ rotr(x, r3, L)


def carry_chain(x_add, K, L):
    """Compute carry vector of adding x_add + K mod 2^L.
    Returns (y, C) where y = (x_add + K) mod 2^L and
    C is an L-bit vector where C[i] = carry INTO bit i.
    C[0] = 0 always; C[L-1] is last carry, discarded (mod 2^L)."""
    mask = (1 << L) - 1
    y = 0
    carry = 0
    C = 0
    for i in range(L):
        a = (x_add >> i) & 1
        b = (K >> i) & 1
        s = a ^ b ^ carry
        y |= (s << i)
        if i > 0:
            C |= (carry << i)  # carry INTO bit i
        carry = (a & b) | (a & carry) | (b & carry)
    return y & mask, C


def forward(x, K, L):
    """y = M·x + K + C(x, K) mod 2^L, returning also the full carry vector C."""
    mask = (1 << L) - 1
    x_add = M_apply(x, L)
    y, C = carry_chain(x_add, K, L)
    return y, C


def invert_baseline(y, K, L):
    """Baseline: enumerate all 2^{L-1} candidate C values (LSB always 0,
    so 2^{L-1} not 2^L).  For each:
      compute  x_add = y - K - C  (mod 2^L)
      solve  M·x = x_add  for x (GF(2) linear inverse — if M invertible)
      check forward(x, K) == (y, C)
    Count full verifies.
    """
    mask = (1 << L) - 1
    M_inv = build_M_inv(L)
    full_verifies = 0
    solutions = []
    for C_idx in range(1 << (L - 1)):
        C = C_idx << 1  # bit 0 of carry is always 0
        x_add = (y ^ K ^ C) & mask  # y[i] = x_add[i] XOR K[i] XOR carry[i]
        x = gf2_matvec(M_inv, x_add, L)
        # Full verify
        y_check, C_check = forward(x, K, L)
        full_verifies += 1
        if y_check == y and C_check == C:
            solutions.append(x)
    return solutions, full_verifies


def invert_early_k(y, K, L, k, positions=None):
    """§132 shortcut: for each candidate C, cheaply compute first-k bits of
    C_actual(x) and compare to C[0..k-1].  Only full-verify passing candidates.

    positions: list of k bit positions to check (default = [1, 2, ..., k]).
               We need k ≥ 1 (bit 0 is trivially 0 in C).
    """
    mask = (1 << L) - 1
    M_inv = build_M_inv(L)
    if positions is None:
        # default: check bits 1..k (bit 0 always 0)
        positions = list(range(1, k + 1))
    pos_mask = 0
    for p in positions:
        pos_mask |= (1 << p)

    full_verifies = 0
    early_checks = 0
    solutions = []
    for C_idx in range(1 << (L - 1)):
        C = C_idx << 1
        x_add = (y ^ K ^ C) & mask  # y[i] = x_add[i] XOR K[i] XOR carry[i]
        x = gf2_matvec(M_inv, x_add, L)
        # Early check: compute just the needed bits of actual C
        early_checks += 1
        C_actual_at_positions = carry_chain_partial(M_apply(x, L), K, L, positions)
        C_at_positions = C & pos_mask
        if C_actual_at_positions != C_at_positions:
            continue  # reject early
        # Full verify
        full_verifies += 1
        y_check, C_check = forward(x, K, L)
        if y_check == y and C_check == C:
            solutions.append(x)
    return solutions, full_verifies, early_checks


def invert_stacked_k(y, K, L, k1, pos1, k2, pos2):
    """Stack two k-bit checks at DIFFERENT bit positions.
    If independent over wrong candidates, combined pass-rate = 0.5^(k1+k2).
    """
    mask = (1 << L) - 1
    M_inv = build_M_inv(L)
    pos1_mask = 0
    for p in pos1: pos1_mask |= (1 << p)
    pos2_mask = 0
    for p in pos2: pos2_mask |= (1 << p)

    full_verifies = 0
    early1_passes = 0
    early2_passes = 0
    solutions = []
    for C_idx in range(1 << (L - 1)):
        C = C_idx << 1
        x_add = (y ^ K ^ C) & mask  # y[i] = x_add[i] XOR K[i] XOR carry[i]
        x = gf2_matvec(M_inv, x_add, L)
        # Early check 1
        C_at_1 = carry_chain_partial(M_apply(x, L), K, L, pos1)
        if C_at_1 != (C & pos1_mask):
            continue
        early1_passes += 1
        # Early check 2
        C_at_2 = carry_chain_partial(M_apply(x, L), K, L, pos2)
        if C_at_2 != (C & pos2_mask):
            continue
        early2_passes += 1
        # Full verify
        full_verifies += 1
        y_check, C_check = forward(x, K, L)
        if y_check == y and C_check == C:
            solutions.append(x)
    return solutions, full_verifies, early1_passes, early2_passes


def carry_chain_partial(x_add, K, L, positions):
    """Compute only carry bits at specified positions (in order).
    Cost: O(max(positions)) — still walks carry chain to highest position."""
    if not positions:
        return 0
    max_pos = max(positions)
    out = 0
    carry = 0
    for i in range(max_pos + 1):
        a = (x_add >> i) & 1
        b = (K >> i) & 1
        if i in positions:
            out |= (carry << i)
        carry = (a & b) | (a & carry) | (b & carry)
    return out


def build_M_inv(L):
    """Inverse of M over GF(2)^L: M(x) = rotr(x,2) ⊕ rotr(x,7) ⊕ rotr(x,13)."""
    # Build M as L×L matrix over GF(2)
    M = np.zeros((L, L), dtype=np.uint8)
    for i in range(L):
        # rotr by r: bit j of output = bit (j+r)%L of input
        #   Here "rotr" as defined in rotr(x, r, L): result = (x >> r) | (x << (L-r))
        #   bit j of (x >> r) = bit (j + r) of x (for j+r < L)
        # So M[j][i] = 1 iff bit j of output comes from bit i via one of the rotations
        for rshift in (2, 7, 13):
            # bit j of rotr(x, rshift) = bit (j+rshift) % L of x
            src = (i - rshift) % L  # bit src of input → bit src+rshift mod L of output... let me redo
            pass
    # Simpler: construct M row-by-row by applying M_apply on unit vectors
    for i in range(L):
        unit = 1 << i
        col = M_apply(unit, L)
        for j in range(L):
            M[j, i] = (col >> j) & 1

    # Invert over GF(2)
    aug = np.hstack([M.copy(), np.eye(L, dtype=np.uint8)])
    # Gaussian elimination
    for c in range(L):
        # Find pivot
        pivot = None
        for r in range(c, L):
            if aug[r, c] == 1:
                pivot = r
                break
        if pivot is None:
            raise ValueError(f"M is not invertible over GF(2) for L={L}")
        if pivot != c:
            aug[[c, pivot]] = aug[[pivot, c]]
        for r in range(L):
            if r != c and aug[r, c] == 1:
                aug[r] ^= aug[c]
    M_inv = aug[:, L:]
    return M_inv


def gf2_matvec(M_inv, x_add, L):
    """Compute M^{-1} · x_add over GF(2) — returns int."""
    result = 0
    for j in range(L):
        bit = 0
        for i in range(L):
            if M_inv[j, i]:
                bit ^= (x_add >> i) & 1
        result |= (bit << j)
    return result


def test_correctness(L):
    """Sanity: forward/inverse pair. Random x, K → y. Inverse should recover x."""
    random.seed(1)
    for _ in range(5):
        x = random.randint(0, (1 << L) - 1)
        K = random.randint(0, (1 << L) - 1)
        y, C = forward(x, K, L)
        # Baseline invert should find x
        sols, fv = invert_baseline(y, K, L)
        assert x in sols, f"x={x} not in sols={sols}"
    print(f"  L={L} correctness: OK")


def bench_single(L, n_trials=20, seed=42):
    """Measure baseline vs §132 early-verify at optimal k for given L."""
    random.seed(seed)

    # Theoretical optimum k: solve 0.5^k = 1/(V*ln2) where V ~ L (full verify cost unit)
    # Approximately k ≈ log2(L)
    # We try several k values
    results = []
    for k in [2, 4, 6, 8, 10, 12]:
        if k >= L: continue
        total_full = 0
        total_early = 0
        t0 = time.time()
        for t in range(n_trials):
            x_true = random.randint(0, (1 << L) - 1)
            K = random.randint(0, (1 << L) - 1)
            y, C = forward(x_true, K, L)
            sols, full, early = invert_early_k(y, K, L, k)
            assert x_true in sols, "recall fail!"
            total_full += full
            total_early += early
        dt = time.time() - t0
        avg_full = total_full / n_trials
        avg_early = total_early / n_trials
        # Speedup vs baseline: baseline does 2^{L-1} full verifies
        baseline_full = 1 << (L - 1)
        # Cost model: full_verify = L ops, early_check = k ops
        ops_baseline = baseline_full * L
        ops_early = avg_early * k + avg_full * L
        speedup = ops_baseline / ops_early
        results.append((k, avg_early, avg_full, speedup, dt))
        print(f"  k={k:2d}: early={avg_early:>8.0f} full={avg_full:>8.0f}  "
              f"speedup={speedup:>7.2f}x  (trials {n_trials} in {dt:.1f}s)")
    return results


def bench_stacked(L, n_trials=20, seed=42):
    """Test stacking: k-bit at LOW positions vs k-bit at MIDDLE vs HIGH."""
    random.seed(seed)

    print(f"\n--- Stacking test L={L} ---")
    # Choose positions
    k_each = 3  # 3 bits per check
    pos_low = [1, 2, 3]
    pos_mid = [L//2, L//2 + 1, L//2 + 2]
    pos_high = [L - 3, L - 2, L - 1]

    for (label, p1, p2) in [
        ("low+mid", pos_low, pos_mid),
        ("low+high", pos_low, pos_high),
        ("mid+high", pos_mid, pos_high),
    ]:
        total_full = 0
        total_early1 = 0
        total_early2 = 0
        for t in range(n_trials):
            x_true = random.randint(0, (1 << L) - 1)
            K = random.randint(0, (1 << L) - 1)
            y, C = forward(x_true, K, L)
            sols, full, e1, e2 = invert_stacked_k(y, K, L, k_each, p1, k_each, p2)
            assert x_true in sols, "recall fail!"
            total_full += full
            total_early1 += e1
            total_early2 += e2
        avg_full = total_full / n_trials
        pass_rate_1 = total_early1 / (n_trials * (1 << (L - 1)))
        pass_rate_2_given_1 = total_early2 / max(total_early1, 1)
        # If independent, pass_rate_1 ~ 0.5^k1, pass_rate_2_given_1 ~ 0.5^k2
        print(f"  {label}: P(check1)={pass_rate_1:.3f} (≈0.5^{k_each}={0.5**k_each:.3f})  "
              f"P(check2|check1)={pass_rate_2_given_1:.3f}  avg_full={avg_full:.1f}")


if __name__ == "__main__":
    print("=== §132 ANF early-verify scoping ===\n")
    for L in [8, 12, 16]:
        print(f"\n--- L={L} ---")
        test_correctness(L)
        bench_single(L, n_trials=30 if L<=12 else 15)

    bench_stacked(16, n_trials=15)
