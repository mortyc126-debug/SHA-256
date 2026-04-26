"""
Session 23: Orders and minimal polynomials of SHA operators.

Goal: compute order (smallest k such that M^k = I), minimal polynomial,
and nilpotency index for each SHA rotation/shift operator.

Σ_0 = Id + N_Σ_0 is unipotent → Σ_0^{2^m} = I + N^{2^m}.
Order of Σ_0 = smallest 2^m with N^{2^m} = 0.

σ_0 = Id + N_σ_0 with SHR. N_σ_0 not nilpotent (Session 19). So σ_0
has non-trivial cycling, order may be > 32 or not a power of 2.

This gives concrete "mixing time" characterization of each operator.
"""
import numpy as np
from session_18b_shr import shr_matrix_in_s_basis
from session_14_sigma0 import lucas_expansion
from session_17_and import change_of_basis_x_to_s, change_of_basis_s_to_x

N = 32


def rotr_full(r, n):
    coeffs = set(lucas_expansion(r, n - 1))
    M = np.zeros((n, n), dtype=np.uint8)
    for j in range(n):
        for pos in coeffs:
            t = j + pos
            if t < n:
                M[t, j] ^= 1
    return M


def matrix_power_mod2(M, k):
    """Compute M^k mod 2 via repeated squaring."""
    n = M.shape[0]
    if k == 0:
        return np.eye(n, dtype=np.uint8)
    result = np.eye(n, dtype=np.uint8)
    base = M.copy() & 1
    while k > 0:
        if k & 1:
            result = (result @ base) & 1
        base = (base @ base) & 1
        k >>= 1
    return result


def find_order(M, max_order=1024):
    """Find smallest k > 0 with M^k = I."""
    n = M.shape[0]
    I = np.eye(n, dtype=np.uint8)
    current = M.copy() & 1
    for k in range(1, max_order + 1):
        if np.array_equal(current, I):
            return k
        current = (current @ M) & 1
    return -1


def find_nilpotency_index(N, max_power=1024):
    """Find smallest k with N^k = 0."""
    n = N.shape[0]
    current = N.copy() & 1
    for k in range(1, max_power + 1):
        if current.sum() == 0:
            return k
        current = (current @ N) & 1
    return -1


def minimal_polynomial_degree(M, max_deg=1024):
    """Find degree of minimal polynomial of M over F_2.
    = smallest k such that I, M, M^2, ..., M^k are linearly dependent."""
    n = M.shape[0]
    powers = [np.eye(n, dtype=np.uint8)]  # M^0
    for i in range(1, max_deg + 1):
        next_power = (powers[-1] @ M) & 1
        # Check linear dependence: is next_power in span of previous powers?
        flattened = [p.flatten() for p in powers] + [next_power.flatten()]
        mat = np.array(flattened, dtype=np.uint8)
        # Row-reduce
        rows, cols = mat.shape
        reduced = mat.copy()
        r = 0
        for c in range(cols):
            if r >= rows: break
            pivot = None
            for rr in range(r, rows):
                if reduced[rr, c] == 1:
                    pivot = rr; break
            if pivot is None: continue
            if pivot != r:
                reduced[[r, pivot]] = reduced[[pivot, r]]
            for rr in range(rows):
                if rr != r and reduced[rr, c] == 1:
                    reduced[rr] ^= reduced[r]
            r += 1
        if r < rows:  # dependent
            return i
        powers.append(next_power)
    return -1


def characterize_operator(name, M):
    """Full characterization."""
    print(f"\n=== {name} ===")
    I = np.eye(M.shape[0], dtype=np.uint8)
    N = (M ^ I) & 1  # M - I (nilpotent part if M is unipotent)

    # Is M - I nilpotent?
    nilp = find_nilpotency_index(N)
    if nilp > 0:
        print(f"  M = I + N with N nilpotent, N^{nilp} = 0")
        # Then M^{2^m} = I + N^{2^m}. Order = smallest 2^m ≥ nilp.
        # Actually order of unipotent M over F_2: smallest 2^m such that 2^m ≥ nilp
        # (since (I + N)^{2^m} = I + N^{2^m} over F_2)
        import math
        log_nilp = math.ceil(math.log2(nilp)) if nilp > 1 else 0
        order_predicted = 2 ** log_nilp
        print(f"  Predicted order: 2^{log_nilp} = {order_predicted}")
    else:
        print(f"  M - I NOT nilpotent (N^1024 ≠ 0)")

    # Find actual order
    order = find_order(M, max_order=256)
    if order > 0:
        print(f"  Order: M^{order} = I")
    else:
        print(f"  Order > 256 (not found in 256 steps)")

    # Min poly degree
    min_deg = minimal_polynomial_degree(M, max_deg=64)
    if min_deg > 0:
        print(f"  Minimal polynomial degree: {min_deg}")
    else:
        print(f"  Min poly degree > 64")


def connection_to_wang_barrier():
    print("""

=== Connection to SHA's Wang-barrier ===

Methodology's T_BARRIER_EQUALS_SCHEDULE (r=17):
  Wang-chain deterministically controls e-register for 16 rounds
  At r=17, schedule adds NEW information (W[16] = σ_1(W[14]) + ...)
  This breaks deterministic control.

Could this "16 rounds" be related to our computed nilpotency/order?

  N_Σ_0^32 = 0 → Σ_0^32 = I over F_2
  N_Σ_1^11 = 0 → Σ_1^16 = I (2^4 ≥ 11)

If we apply Σ-operators repeatedly (as SHA does), they CYCLE.
Combined with message schedule, cycling may connect to 16-17 barrier.

This is SPECULATIVE — would need detailed analysis of actual round composition
tracking across 17 rounds. But the numerical coincidence with 16 (= order of Σ_1
acting) is suggestive.
""")


def main():
    print("=== Session 23: SHA operator orders & min polys ===")

    # Build operators
    S0 = np.zeros((N, N), dtype=np.uint8)
    for r in [2, 13, 22]: S0 ^= rotr_full(r, N)
    S0 &= 1
    S1 = np.zeros((N, N), dtype=np.uint8)
    for r in [6, 11, 25]: S1 ^= rotr_full(r, N)
    S1 &= 1
    sig0 = np.zeros((N, N), dtype=np.uint8)
    for r in [7, 18]: sig0 ^= rotr_full(r, N)
    sig0 ^= shr_matrix_in_s_basis(3, N)
    sig0 &= 1
    sig1 = np.zeros((N, N), dtype=np.uint8)
    for r in [17, 19]: sig1 ^= rotr_full(r, N)
    sig1 ^= shr_matrix_in_s_basis(10, N)
    sig1 &= 1

    for name, M in [("Σ_0", S0), ("Σ_1", S1), ("σ_0", sig0), ("σ_1", sig1)]:
        characterize_operator(name, M)

    # Compositions
    print("\n\n=== Composition orders ===")
    for name, op1, op2 in [
        ("Σ_0 ∘ Σ_1", S0, S1),
        ("Σ_0 ∘ σ_0", S0, sig0),
        ("σ_0 ∘ σ_1", sig0, sig1),
    ]:
        comp = (op1 @ op2) & 1
        order = find_order(comp, max_order=256)
        print(f"  {name}: order = {order}")

    connection_to_wang_barrier()


if __name__ == "__main__":
    main()
