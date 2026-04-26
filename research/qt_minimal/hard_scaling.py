"""
Hard-regime scaling test.

Observation from earlier:
  near-collision with small k is EASY (many solutions exist, z3 finds one fast).
  To force hardness, need:
    (a) full collision: often UNSAT for small mini-SHA (injective)
    (b) target-preimage where specific output chosen far from reachable space
    (c) LARGE k relative to search space

This test does (c): fix (n, R) and grow k to saturation.
Also adds TARGET-PREIMAGE with specific target (requires SAT to actually search).

We plot time vs k to see if it stays flat (polynomial propagation) or blows up
(exponential search).
"""
import time, random, json
from z3 import (BitVec, BitVecVal, RotateRight, Solver, sat, unsat,
                Or, Extract, Concat)
from mini_sha import gen_IV, gen_K, single_round, sigma_params


def compute_hash(W, H0, R, n):
    K = gen_K(n, R); mask = (1 << n) - 1
    state = tuple(H0)
    for r in range(R):
        state = single_round(state, W[r], K[r], n)
    return tuple((H0[i] + state[i]) & mask for i in range(8))


def _Sig_bv(x, rots):
    r1, r2, r3 = rots
    return RotateRight(x, r1) ^ RotateRight(x, r2) ^ RotateRight(x, r3)


def sat_preimage_bv(H0, target_full, R, n, k_match, timeout_ms=60_000):
    """Find W such that first k_match bits of hash equal first k_match bits of target_full."""
    t0 = time.time()
    K = gen_K(n, R)
    Sig0r, Sig1r, _, _ = sigma_params(n)
    W_v = [BitVec(f"W_{r}", n) for r in range(R)]
    s = Solver(); s.set("timeout", timeout_ms)

    state = tuple(BitVecVal(H0[i], n) for i in range(8))
    for r in range(R):
        a, b, c, d, e, f, g, h = state
        T1 = h + _Sig_bv(e, Sig1r) + ((e & f) ^ (~e & g)) + BitVecVal(K[r], n) + W_v[r]
        T2 = _Sig_bv(a, Sig0r) + ((a & b) ^ (a & c) ^ (b & c))
        state = (T1 + T2, a, b, c, d + T1, e, f, g)
    h_out = [BitVecVal(H0[i], n) + state[i] for i in range(8)]

    concat_h = h_out[0]
    for i in range(1, 8):
        concat_h = Concat(h_out[i], concat_h)
    # target as single big int
    target_big = 0
    for i, v in enumerate(target_full):
        target_big |= (v << (i * n))
    target_k = target_big & ((1 << k_match) - 1)

    s.add(Extract(k_match-1, 0, concat_h) == BitVecVal(target_k, k_match))

    res = s.check(); t = time.time() - t0
    if res == sat:
        m = s.model()
        W_out = [m.eval(W_v[r], model_completion=True).as_long() for r in range(R)]
        return W_out, t
    elif res == unsat:
        return "UNSAT", t
    return None, t  # timeout


def brute_preimage(H0, target_full, R, n, k_match, max_iters=10_000_000):
    t0 = time.time()
    mask = (1 << n) - 1
    target_big = 0
    for i, v in enumerate(target_full):
        target_big |= (v << (i * n))
    target_k = target_big & ((1 << k_match) - 1)
    rng = random.Random(7)
    for it in range(max_iters):
        W = tuple(rng.randint(0, mask) for _ in range(R))
        h = compute_hash(W, H0, R, n)
        hk = 0
        for i, v in enumerate(h):
            hk |= (v << (i * n))
        hk &= (1 << k_match) - 1
        if hk == target_k:
            return list(W), time.time() - t0, it + 1
    return None, time.time() - t0, max_iters


def run_scaling(n, R, timeout_ms=30_000):
    """Fix (n,R); sweep k_match from small to large.
    Reports: brute iters/time vs SAT time.
    At k near n*R, problem becomes hard (preimage constraint is strong).
    """
    H0 = gen_IV(n)
    # fix some random target
    random.seed(99)
    W_anchor = [random.randint(0, (1<<n)-1) for _ in range(R)]
    target = compute_hash(W_anchor, H0, R, n)

    print(f"\n=== n={n}  R={R}  (search 2^{n*R} bits; 8n={8*n} output)")
    print(f"    target (from W_anchor={W_anchor}): {target}")
    results = []

    max_k = min(8*n, 64)  # don't go above 64 for practical timing
    ks = list(range(8, max_k+1, 4))
    for k in ks:
        # brute preimage (random)
        max_brute = 500_000
        W_b, tb, iters = brute_preimage(H0, target, R, n, k, max_iters=max_brute)
        found_b = W_b is not None

        # SAT
        W_s, ts = sat_preimage_bv(H0, target, R, n, k, timeout_ms=timeout_ms)
        sat_status = "ok" if isinstance(W_s, list) else str(W_s)

        print(f"  k={k:3d}  brute: iters={iters:>8d} {'ok' if found_b else 'none'} {tb*1000:>8.1f}ms  |  sat: {ts*1000:>10.1f}ms {sat_status}")
        results.append({"k": k, "brute_iters": iters, "brute_found": found_b,
                        "brute_ms": tb*1000, "sat_ms": ts*1000, "sat_status": sat_status})
    return results


if __name__ == "__main__":
    all_data = {}
    # Pick one size big enough: n=16, R=4 → 64 bits input, 128 bits output
    for n, R in [(8, 4), (12, 4), (16, 4), (16, 6)]:
        try:
            d = run_scaling(n, R, timeout_ms=20_000)
            all_data[f"n{n}_R{R}"] = d
        except Exception as e:
            print(f"ERR: {e}")
            all_data[f"n{n}_R{R}"] = {"error": str(e)}

    with open("hard_scaling_results.json", "w") as f:
        json.dump(all_data, f, indent=2)
