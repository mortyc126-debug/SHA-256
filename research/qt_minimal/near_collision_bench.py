"""
Near-collision benchmark: find W1 != W2 such that first k bits of hash match.

This is the real test because:
  - Full collision of 8*n bit hash is UNSAT for small n*R (mini-SHA injective)
  - Partial collision (first k bits) always exists, and cost scales as 2^(k/2) birthday
  - This matches what methodology actually does (T_DMIN_97, MLB HW=80)

Parameter: k = number of matching bits required.
           n*R >= k  (else infeasible)
"""
import time, random, json
from z3 import (BitVec, BitVecVal, RotateRight, Solver, sat, unsat,
                Or, Extract, Concat, And)
from mini_sha import gen_IV, gen_K, single_round, sigma_params


def compute_hash(W, H0, num_rounds, n):
    mask = (1 << n) - 1
    K = gen_K(n, num_rounds)
    state = tuple(H0)
    for r in range(num_rounds):
        state = single_round(state, W[r], K[r], n)
    return tuple((H0[i] + state[i]) & mask for i in range(8))


def first_k_bits(h_tuple, k, n):
    """Take first k bits of concatenated h_tuple (h[0] LSB to h[7] MSB within each word)."""
    # Concatenate all 8 words MSB-first as a big integer
    big = 0
    for i, w in enumerate(h_tuple):
        big |= (w << (i * n))
    return big & ((1 << k) - 1)


def brute_near_collision(H0, num_rounds, n, k, max_iters=5_000_000):
    t0 = time.time()
    mask = (1 << n) - 1
    seen = {}
    rng = random.Random(17)
    for it in range(max_iters):
        W = tuple(rng.randint(0, mask) for _ in range(num_rounds))
        h = compute_hash(W, H0, num_rounds, n)
        key = first_k_bits(h, k, n)
        if key in seen and seen[key] != W:
            return (seen[key], W), time.time() - t0, it + 1
        seen[key] = W
    return None, time.time() - t0, max_iters


def _Sig_bv(x, rots):
    r1, r2, r3 = rots
    return RotateRight(x, r1) ^ RotateRight(x, r2) ^ RotateRight(x, r3)


def sat_near_collision(H0, num_rounds, n, k, timeout_ms=60_000):
    t0 = time.time()
    K = gen_K(n, num_rounds)
    Sig0r, Sig1r, _, _ = sigma_params(n)

    W1 = [BitVec(f"W1_{r}", n) for r in range(num_rounds)]
    W2 = [BitVec(f"W2_{r}", n) for r in range(num_rounds)]
    s = Solver()
    s.set("timeout", timeout_ms)

    def compress_sym(W_vars):
        state = tuple(BitVecVal(H0[i], n) for i in range(8))
        for r in range(num_rounds):
            a, b, c, d, e, f, g, h = state
            T1 = h + _Sig_bv(e, Sig1r) + ((e & f) ^ (~e & g)) + BitVecVal(K[r], n) + W_vars[r]
            T2 = _Sig_bv(a, Sig0r) + ((a & b) ^ (a & c) ^ (b & c))
            state = (T1 + T2, a, b, c, d + T1, e, f, g)
        return [BitVecVal(H0[i], n) + state[i] for i in range(8)]

    h1 = compress_sym(W1)
    h2 = compress_sym(W2)

    # Build concatenated hashes as n*8-bit bitvectors and compare bottom k bits
    concat1 = h1[0]
    for i in range(1, 8):
        concat1 = Concat(h1[i], concat1)  # MSB..LSB
    concat2 = h2[0]
    for i in range(1, 8):
        concat2 = Concat(h2[i], concat2)

    s.add(Extract(k-1, 0, concat1) == Extract(k-1, 0, concat2))

    # W1 != W2
    s.add(Or([W1[r] != W2[r] for r in range(num_rounds)]))

    result = s.check()
    elapsed = time.time() - t0
    if result == sat:
        m = s.model()
        W1_out = [m.eval(W1[r], model_completion=True).as_long() for r in range(num_rounds)]
        W2_out = [m.eval(W2[r], model_completion=True).as_long() for r in range(num_rounds)]
        return (W1_out, W2_out), elapsed
    elif result == unsat:
        return "UNSAT", elapsed
    return None, elapsed


def run(n, R, k, timeout_ms=60_000):
    H0 = gen_IV(n)
    search_bits = n * R
    birthday_k = k // 2

    print(f"\n=== n={n} R={R} k={k}  search 2^{search_bits}  birthday 2^{birthday_k} ===")
    results = {"n": n, "R": R, "k": k, "search_bits": search_bits, "birthday_k": birthday_k}

    # Brute (if birthday feasible)
    if birthday_k <= 22:
        try:
            limit = min(200 * (1 << birthday_k), 20_000_000)
            res, t, iters = brute_near_collision(H0, R, n, k, max_iters=limit)
            if res:
                W1, W2 = res
                print(f"  brute:    iter={iters:>10d}  time={t*1000:>10.1f}ms  W1={W1[:3]}...  W2={W2[:3]}...")
                results["brute"] = {"iters": iters, "time_ms": t*1000, "W1": list(W1), "W2": list(W2)}
            else:
                print(f"  brute:    no collision in {iters} iters (t={t*1000:.0f}ms)")
                results["brute"] = {"iters": iters, "time_ms": t*1000, "not_found": True}
        except Exception as e:
            print(f"  brute err: {e}")
            results["brute"] = {"error": str(e)}
    else:
        print(f"  brute:    skipped (2^{birthday_k})")
        results["brute"] = {"skipped": True}

    # SAT BV
    try:
        res, t = sat_near_collision(H0, R, n, k, timeout_ms=timeout_ms)
        if res is None:
            print(f"  sat_bv:   TIMEOUT (t={t*1000:.0f}ms)")
            results["sat_bv"] = {"timeout": True, "time_ms": t*1000}
        elif res == "UNSAT":
            print(f"  sat_bv:   UNSAT (t={t*1000:.0f}ms)")
            results["sat_bv"] = {"unsat": True, "time_ms": t*1000}
        else:
            W1, W2 = res
            h1 = compute_hash(W1, H0, R, n)
            h2 = compute_hash(W2, H0, R, n)
            k1 = first_k_bits(h1, k, n)
            k2 = first_k_bits(h2, k, n)
            assert k1 == k2, f"verify fail: {k1:x} vs {k2:x}"
            assert W1 != W2, "same W!"
            print(f"  sat_bv:   {t*1000:>10.1f}ms  ✓verified W1={W1[:3]}...  W2={W2[:3]}...")
            results["sat_bv"] = {"time_ms": t*1000, "W1": W1, "W2": W2}
    except Exception as e:
        print(f"  sat_bv err: {e}")
        results["sat_bv"] = {"error": str(e)}

    return results


if __name__ == "__main__":
    all_results = []
    # k-near collision: vary k to test birthday scaling
    # For n=8, R=4 (search 2^32), try k=8,16,24
    configs = [
        # (n, R, k)
        (8, 4, 8),
        (8, 4, 16),
        (8, 4, 24),
        (8, 4, 32),
        (12, 4, 16),
        (12, 4, 24),
        (12, 4, 32),
        (12, 4, 40),
        (16, 4, 24),
        (16, 4, 32),
        (16, 4, 40),
        (16, 6, 48),
    ]
    for n, R, k in configs:
        all_results.append(run(n, R, k, timeout_ms=60_000))

    with open("near_collision_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n\n=== Summary ===")
    print(f"{'n':>3} {'R':>3} {'k':>3} {'birth':>6} {'brute_ms':>12} {'sat_ms':>12}  speedup")
    for r in all_results:
        n=r['n']; R=r['R']; k=r['k']; bk=r['birthday_k']
        bt = r.get('brute', {}).get('time_ms')
        st = r.get('sat_bv', {}).get('time_ms')
        if bt and st and not r.get('brute', {}).get('not_found'):
            ratio = bt / st
            tag = f"{ratio:>7.2f}x"
        else:
            tag = ""
        bt_s = f"{bt:12.1f}" if bt is not None else "     skipped"
        st_s = f"{st:12.1f}" if st is not None else "           -"
        print(f"{n:>3} {R:>3} {k:>3} {bk:>6} {bt_s} {st_s}  {tag}")
