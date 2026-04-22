"""
Cohomology probe: measure the linear structure of the carry subspace in
mini-SHA rounds.

Motivation (methodology §II.7.7, §II.7.6 BTE T5):
  - Full SHA-256: carry-rank = 589/592 over GF(2).
    3-bit DEFICIT = "obstruction" — measure of how non-linear carry is.
  - Carry is 1-cocycle in H¹(Z/2^n; GF(2)^n), H¹=0 trivially.
  - Non-trivial obstruction may live in H² or higher.

Concrete measurement:
  1. Take mini-SHA round with fixed H0.
  2. Compute MAP  M: W → (all_carry_bits_produced_during_round)
  3. Stack M(W_i) for many random W_i.
  4. Measure rank over GF(2): how many INDEPENDENT linear combinations of
     input bits does carry span?
  5. Measure FULL rank (linear + nonlinear): how large is image of M?

  Gap between "affine linear rank" and "full image rank" = cohomological
  non-triviality. If linear_rank << full_rank, carry has big nonlinear
  component (and attack needs to deal with that).

  If the deficit scales or stabilizes meaningfully, it's worth further study.
"""
import numpy as np
import random, time, json
from mini_sha import (gen_IV, gen_K, sigma_params, Ch, Maj,
                       Sig0 as Sig0_int, Sig1 as Sig1_int)


def gf2_rank(mat):
    """Compute rank over GF(2) of a binary matrix (column-by-column Gauss)."""
    mat = mat.copy().astype(np.uint8) & 1
    rows, cols = mat.shape
    rank = 0
    r = 0
    for col in range(cols):
        if r >= rows:
            break
        # Find pivot in rows r..rows-1
        pivot_row = None
        for rr in range(r, rows):
            if mat[rr, col] == 1:
                pivot_row = rr
                break
        if pivot_row is None:
            continue  # no pivot in this column, try next column (same row)
        if pivot_row != r:
            mat[[r, pivot_row]] = mat[[pivot_row, r]]
        # Eliminate this column in all OTHER rows
        for rr in range(rows):
            if rr != r and mat[rr, col] == 1:
                mat[rr] ^= mat[r]
        rank += 1
        r += 1
    return rank


def extract_carries_single_round(state_in, W_r, K_r, n):
    """Run one mini-SHA round symbolically, extracting ALL carry bits.
    Returns flat array of carry bits in order of ADD operations."""
    mask = (1 << n) - 1
    carries = []

    def adder_carries(terms):
        """Compute carries for sum of terms (list of n-bit ints). Returns
        (sum, list_of_per_step_carry_vecs). Each carry_vec is n bits."""
        acc = terms[0]
        cs = []
        for t in terms[1:]:
            # full-adder cascade between acc and t
            s = 0
            carry = 0
            per_step_carry = []
            for j in range(n):
                a = (acc >> j) & 1
                b = (t >> j) & 1
                bit = a ^ b ^ carry
                s |= (bit << j)
                per_step_carry.append(carry)  # carry INTO bit j
                carry = (a & b) | (a & carry) | (b & carry)
            cs.extend(per_step_carry)
            acc = s & mask
        return acc, cs

    Sig0r, Sig1r, _, _ = sigma_params(n)
    a, b, c, d, e, f, g, h = state_in

    Sig1_e = Sig1_int(e, n)
    Ch_efg = Ch(e, f, g, n)
    Sig0_a = Sig0_int(a, n)
    Maj_abc = Maj(a, b, c, n)

    # T1 = h + Sig1(e) + Ch(e,f,g) + K_r + W_r
    T1, cs1 = adder_carries([h, Sig1_e, Ch_efg, K_r, W_r])
    carries.extend(cs1)
    # T2 = Sig0(a) + Maj(a,b,c)
    T2, cs2 = adder_carries([Sig0_a, Maj_abc])
    carries.extend(cs2)
    # a' = T1 + T2
    a_p, cs3 = adder_carries([T1, T2])
    carries.extend(cs3)
    # e' = d + T1
    e_p, cs4 = adder_carries([d, T1])
    carries.extend(cs4)

    return np.array(carries, dtype=np.uint8)


def compute_full_carries_trace(W_list, H0, R, n):
    """For given (H0, W_list), run R rounds and extract ALL carries produced
    across rounds. Returns a flat GF(2) vector."""
    from mini_sha import single_round
    mask = (1 << n) - 1
    K = gen_K(n, R)
    state = tuple(H0)
    all_carries = []
    for r in range(R):
        cs = extract_carries_single_round(state, W_list[r], K[r], n)
        all_carries.append(cs)
        state = single_round(state, W_list[r], K[r], n)
    return np.concatenate(all_carries)


def measure_rank(n, R, N_samples=2000, seed=42):
    """Measure rank(carry-matrix) when varying W (and only W).
    H0 fixed. Matrix: N_samples x total_carry_bits."""
    random.seed(seed)
    mask = (1 << n) - 1
    H0 = gen_IV(n)

    # Determine total carry bits
    W_probe = [0] * R
    cs_probe = compute_full_carries_trace(W_probe, H0, R, n)
    total_bits = len(cs_probe)

    # Sample N random W vectors, stack carries
    mat = np.zeros((N_samples, total_bits), dtype=np.uint8)
    for i in range(N_samples):
        W = [random.randint(0, mask) for _ in range(R)]
        mat[i] = compute_full_carries_trace(W, H0, R, n)

    # Raw image rank: how many distinct carry-vectors we see?
    unique = len(set(tuple(row) for row in mat.tolist()))

    # Affine-linear rank: center on first sample, compute rank of differences
    mat_diff = mat ^ mat[0]
    lin_rank = gf2_rank(mat_diff)

    # Input-space rank for reference (how many bits of W vary)
    input_bits = n * R

    return {
        "n": n, "R": R, "N_samples": N_samples,
        "total_carry_bits": total_bits,
        "input_bits": input_bits,
        "unique_carry_vectors": unique,
        "gf2_affine_rank": lin_rank,
        "deficit_vs_total": total_bits - lin_rank,
        "deficit_vs_input": input_bits - lin_rank if input_bits < total_bits else 0,
    }


def jacobian_local_rank(n, R, N_samples=200, seed=99):
    """Compute LOCAL linearization rank via discrete Jacobian.
    For each W, flip each bit individually, measure carry change.
    Stack flips into matrix, compute rank. This is the "Jacobian-of-carry" rank."""
    random.seed(seed)
    mask = (1 << n) - 1
    H0 = gen_IV(n)
    input_bits = n * R

    # For a SINGLE W, flip each input bit and see carry change
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

    # Multi-sample over different anchors
    ranks = [gf2_rank(J)]
    for s in range(N_samples - 1):
        W_base = [random.randint(0, mask) for _ in range(R)]
        cs_base = compute_full_carries_trace(W_base, H0, R, n)
        Js = np.zeros((input_bits, total_bits), dtype=np.uint8)
        for i in range(input_bits):
            r = i // n; b = i % n
            W_flip = list(W_base)
            W_flip[r] ^= (1 << b)
            cs_flip = compute_full_carries_trace(W_flip, H0, R, n)
            Js[i] = cs_flip ^ cs_base
        ranks.append(gf2_rank(Js))

    import statistics
    return {
        "jacobian_rank_mean": statistics.mean(ranks),
        "jacobian_rank_min": min(ranks),
        "jacobian_rank_max": max(ranks),
        "jacobian_rank_samples": len(ranks),
        "total_carry_bits": total_bits,
        "input_bits": input_bits,
    }


if __name__ == "__main__":
    print("=== Carry structure probe (mini-SHA) ===\n")
    results = []
    for n in [4, 8, 12, 16]:
        for R in [1, 2, 3, 4, 6]:
            print(f"-- n={n} R={R} --")
            t0 = time.time()
            global_r = measure_rank(n, R, N_samples=min(4000, 2 ** (n*R)) )
            jac_r = jacobian_local_rank(n, R, N_samples=50)
            res = {**global_r, **jac_r, "time_s": time.time() - t0}
            results.append(res)
            print(f"  total_carry_bits = {res['total_carry_bits']:>5d}  input_bits = {res['input_bits']:>4d}")
            print(f"  affine_rank(global) = {res['gf2_affine_rank']:>5d}  unique vectors = {res['unique_carry_vectors']}")
            print(f"  deficit_vs_total = {res['deficit_vs_total']:>4d}   deficit_vs_input = {res['deficit_vs_input']:>4d}")
            print(f"  jacobian_rank mean = {res['jacobian_rank_mean']:.1f}  min={res['jacobian_rank_min']} max={res['jacobian_rank_max']}")
            print(f"  time = {res['time_s']:.1f}s\n")

    with open("cohomology_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n=== Summary ===")
    print(f"{'n':>3} {'R':>3} {'carry':>6} {'input':>6} {'gl_rank':>8} {'gl_def':>7} {'jac_mean':>9}")
    for r in results:
        print(f"{r['n']:>3} {r['R']:>3} "
              f"{r['total_carry_bits']:>6d} {r['input_bits']:>6d} "
              f"{r['gf2_affine_rank']:>8d} {r['deficit_vs_total']:>7d} "
              f"{r['jacobian_rank_mean']:>9.1f}")
