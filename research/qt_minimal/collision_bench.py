"""
Collision benchmark: find W1 != W2 with same hash (mini-SHA).

This is the RIGHT test:
  - Brute force: 2^(n*R/2) birthday bound
  - SAT: needs to SEARCH two distinct W, no single-answer constraint-propagation shortcut
  - Q∩T: is there advantage from structural split here?

We'll also track reference "oracle" cost: how fast does SHA-like computation run.
"""
import time, random, json, itertools
from z3 import (BitVec, BitVecVal, RotateRight, Solver, sat, unsat,
                Distinct, Or, And, Not)
from mini_sha import (gen_IV, gen_K, single_round, sigma_params, Ch, Maj)


def compute_hash(W, H0, num_rounds, n):
    mask = (1 << n) - 1
    K = gen_K(n, num_rounds)
    state = tuple(H0)
    for r in range(num_rounds):
        state = single_round(state, W[r], K[r], n)
    return tuple((H0[i] + state[i]) & mask for i in range(8))


def brute_collision(H0, num_rounds, n, max_iters=None):
    """Birthday-style collision search via hash-table."""
    t0 = time.time()
    mask = (1 << n) - 1
    total = (1 << (n * num_rounds))
    if max_iters is None:
        max_iters = total
    seen = {}
    iters = 0
    for idx in range(max_iters):
        W = tuple((idx >> (n*i)) & mask for i in range(num_rounds))
        h = compute_hash(W, H0, num_rounds, n)
        iters += 1
        if h in seen and seen[h] != W:
            return (seen[h], W), time.time() - t0, iters
        seen[h] = W
    return None, time.time() - t0, iters


def brute_collision_random(H0, num_rounds, n, max_iters=5_000_000):
    """Random sampling birthday collision search — more realistic."""
    t0 = time.time()
    mask = (1 << n) - 1
    seen = {}
    rng = random.Random(42)
    for it in range(max_iters):
        W = tuple(rng.randint(0, mask) for _ in range(num_rounds))
        h = compute_hash(W, H0, num_rounds, n)
        if h in seen and seen[h] != W:
            return (seen[h], W), time.time() - t0, it+1
        seen[h] = W
    return None, time.time() - t0, max_iters


def _Sig_bv(x, rots):
    r1, r2, r3 = rots
    return RotateRight(x, r1) ^ RotateRight(x, r2) ^ RotateRight(x, r3)


def sat_collision_bv(H0, num_rounds, n, timeout_ms=60_000):
    """SAT BitVec: find two distinct W vectors with same hash."""
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

    # Require hashes equal
    for i in range(8):
        s.add(h1[i] == h2[i])

    # Require W1 != W2 (at least one differs)
    diff_clauses = [W1[r] != W2[r] for r in range(num_rounds)]
    s.add(Or(diff_clauses))

    result = s.check()
    elapsed = time.time() - t0
    if result == sat:
        m = s.model()
        W1_out = [m.eval(W1[r], model_completion=True).as_long() for r in range(num_rounds)]
        W2_out = [m.eval(W2[r], model_completion=True).as_long() for r in range(num_rounds)]
        return (W1_out, W2_out), elapsed, None
    elif result == unsat:
        return "UNSAT", elapsed, None
    return None, elapsed, None  # timeout


def run(n, R, timeout_ms=60_000, skip_brute_if_above=2**24):
    H0 = gen_IV(n)
    search_bits = n * R
    birthday_bits = search_bits // 2

    print(f"\n=== n={n}, R={R}  search 2^{search_bits}  birthday 2^{birthday_bits} ===")

    results = {"n": n, "R": R, "search_bits": search_bits, "birthday_bits": birthday_bits}

    # Brute birthday
    if 2**birthday_bits <= 5_000_000:
        try:
            res, t, iters = brute_collision_random(H0, R, n, max_iters=10*(2**birthday_bits))
            if res:
                W1, W2 = res
                print(f"  brute:    ({W1} != {W2})  {t*1000:8.1f}ms  iters={iters}")
                results["brute"] = {"W1": list(W1), "W2": list(W2), "time_ms": t*1000, "iters": iters}
            else:
                print(f"  brute:    not found in {iters} iters ({t*1000:.0f}ms)")
                results["brute"] = {"timeout": True, "iters": iters, "time_ms": t*1000}
        except Exception as e:
            print(f"  brute:    ERR {e}")
            results["brute"] = {"error": str(e)}
    else:
        print(f"  brute:    skipped (birthday 2^{birthday_bits} too large)")
        results["brute"] = {"skipped": True}

    # SAT BitVec
    try:
        res, t, _ = sat_collision_bv(H0, R, n, timeout_ms=timeout_ms)
        if res is None:
            print(f"  sat_bv:   TIMEOUT ({t*1000:.0f}ms)")
            results["sat_bv"] = {"timeout": True, "time_ms": t*1000}
        elif res == "UNSAT":
            print(f"  sat_bv:   UNSAT? ({t*1000:.0f}ms)")
            results["sat_bv"] = {"unsat": True, "time_ms": t*1000}
        else:
            W1, W2 = res
            # Verify
            h1 = compute_hash(W1, H0, R, n)
            h2 = compute_hash(W2, H0, R, n)
            assert h1 == h2, f"verification fail: {h1} vs {h2}"
            assert W1 != W2, "same W!"
            print(f"  sat_bv:   ({W1} != {W2})  {t*1000:8.1f}ms  ✓verified")
            results["sat_bv"] = {"W1": W1, "W2": W2, "time_ms": t*1000}
    except Exception as e:
        print(f"  sat_bv:   ERR {e}")
        results["sat_bv"] = {"error": str(e)}

    return results


if __name__ == "__main__":
    all_results = []
    configs = [
        (4, 2), (4, 3), (4, 4),
        (8, 2), (8, 3), (8, 4), (8, 6),
        (12, 2), (12, 3), (12, 4),
        (16, 2), (16, 3),
    ]
    for n, R in configs:
        try:
            all_results.append(run(n, R, timeout_ms=60_000))
        except Exception as e:
            print(f"FAIL: {e}")
            all_results.append({"n": n, "R": R, "fatal_error": str(e)})

    with open("collision_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\n\n=== Summary (collision search) ===")
    print(f"{'n':>3} {'R':>3} {'bits':>5} {'birth':>6} {'brute_ms':>10} {'sat_ms':>10}  verdict")
    for r in all_results:
        if "fatal_error" in r: continue
        n = r["n"]; R = r["R"]; sb = r["search_bits"]; bb = r["birthday_bits"]
        bt = r.get("brute", {}).get("time_ms", None)
        st = r.get("sat_bv", {}).get("time_ms", None)
        bt_s = f"{bt:10.1f}" if bt is not None else "     skip"
        st_s = f"{st:10.1f}" if st is not None else "        -"
        v = ""
        if r.get("sat_bv", {}).get("timeout"): v = "SAT timeout"
        elif r.get("brute", {}).get("skipped"): v = "birth too big"
        print(f"{n:>3} {R:>3} {sb:>5} {bb:>6} {bt_s} {st_s}  {v}")
