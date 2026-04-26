"""
Find z3's breaking point on mini-SHA preimage.
Previous tests showed z3 ~constant 5ms up to (n=12, R=4).
Now push: n=16 with R=6, 8, 12, 16.  Schedule expansion kicks in at R>16.

Key question: where does z3 go from 'polynomial' to 'exponential'?
If never — mini-SHA is trivially broken even at full 64 rounds.
If at some R* — Q∩T structure doesn't give better tool than SMT.
"""
import time, random, json
from z3 import (BitVec, BitVecVal, RotateRight, LShR, Solver, sat, unsat,
                Extract, Concat)
from mini_sha import gen_IV, gen_K, single_round, sigma_params


def compute_hash_with_schedule(W_in, H0, R, n, M=16):
    """Uses message schedule expansion if R > M."""
    from mini_sha import expand_schedule
    mask = (1 << n) - 1
    K = gen_K(n, R)
    W = expand_schedule(W_in, R, n, M) if R > M else list(W_in[:R])
    state = tuple(H0)
    for r in range(R):
        state = single_round(state, W[r], K[r], n)
    return tuple((H0[i] + state[i]) & mask for i in range(8))


def _Sig_bv(x, rots):
    r1, r2, r3 = rots
    return RotateRight(x, r1) ^ RotateRight(x, r2) ^ RotateRight(x, r3)


def _sigma_bv(x, rots_shr, n):
    r1, r2, s = rots_shr
    return RotateRight(x, r1) ^ RotateRight(x, r2) ^ LShR(x, s)


def sat_preimage_full(H0, target_full, R, n, k_match, M=16, timeout_ms=120_000):
    """Full schedule-expansion preimage."""
    t0 = time.time()
    K = gen_K(n, R)
    Sig0r, Sig1r, sig0r, sig1r = sigma_params(n)

    W_in = [BitVec(f"W_in_{r}", n) for r in range(M)]
    W = list(W_in)
    for r in range(M, R):
        w_new = _sigma_bv(W[r-2], sig1r, n) + W[r-7] + _sigma_bv(W[r-15], sig0r, n) + W[r-16]
        W.append(w_new)
    # For R<M only use first R
    if R < M:
        W = W[:R]

    s = Solver(); s.set("timeout", timeout_ms)
    state = tuple(BitVecVal(H0[i], n) for i in range(8))
    for r in range(R):
        a, b, c, d, e, f, g, h = state
        T1 = h + _Sig_bv(e, Sig1r) + ((e & f) ^ (~e & g)) + BitVecVal(K[r], n) + W[r]
        T2 = _Sig_bv(a, Sig0r) + ((a & b) ^ (a & c) ^ (b & c))
        state = (T1 + T2, a, b, c, d + T1, e, f, g)
    h_out = [BitVecVal(H0[i], n) + state[i] for i in range(8)]

    target_big = 0
    for i, v in enumerate(target_full):
        target_big |= v << (i * n)
    target_k = target_big & ((1 << k_match) - 1)

    concat_h = h_out[0]
    for i in range(1, 8):
        concat_h = Concat(h_out[i], concat_h)
    s.add(Extract(k_match-1, 0, concat_h) == BitVecVal(target_k, k_match))

    res = s.check(); t = time.time() - t0
    if res == sat:
        m = s.model()
        W_out = [m.eval(W_in[r], model_completion=True).as_long() for r in range(M)]
        return W_out, t
    elif res == unsat:
        return "UNSAT", t
    return None, t  # timeout


def run(n, R, k_match, seed=42, timeout_ms=60_000):
    M = 16
    random.seed(seed)
    mask = (1 << n) - 1
    # real anchor W_in (M words)
    W_anchor = [random.randint(0, mask) for _ in range(M)]
    H0 = gen_IV(n)
    # Compute target with schedule
    target = compute_hash_with_schedule(W_anchor, H0, R, n, M)

    print(f"\n--- n={n}, R={R}, k={k_match}  (input {M} words = {n*M} bits; full hash {8*n} bits)")
    res, t = sat_preimage_full(H0, target, R, n, k_match, M=M, timeout_ms=timeout_ms)
    if res is None:
        print(f"    TIMEOUT after {t*1000:.0f}ms")
        return {"n": n, "R": R, "k": k_match, "timeout": True, "time_ms": t*1000}
    elif res == "UNSAT":
        print(f"    UNSAT {t*1000:.0f}ms (shouldn't happen for target from real W)")
        return {"n": n, "R": R, "k": k_match, "unsat": True, "time_ms": t*1000}
    else:
        # Verify
        h = compute_hash_with_schedule(res, H0, R, n, M)
        tb = 0
        for i, v in enumerate(target): tb |= v << (i*n)
        hb = 0
        for i, v in enumerate(h): hb |= v << (i*n)
        tk = tb & ((1 << k_match) - 1)
        hk = hb & ((1 << k_match) - 1)
        ok = tk == hk
        verdict = "✓" if ok else "✗"
        print(f"    {verdict} found in {t*1000:>10.1f}ms")
        return {"n": n, "R": R, "k": k_match, "time_ms": t*1000, "verified": ok, "W_found": res}


if __name__ == "__main__":
    all_data = []
    # Start aggressive: n=16 with growing R
    # k_match = full output = 8n = 128
    # key question: how does time scale with R?
    for (n, R, k) in [
        (16, 4, 32), (16, 4, 64), (16, 4, 96), (16, 4, 128),
        (16, 6, 32), (16, 6, 64), (16, 6, 96), (16, 6, 128),
        (16, 8, 32), (16, 8, 64), (16, 8, 96), (16, 8, 128),
        (16, 12, 64), (16, 12, 96), (16, 12, 128),
        (16, 16, 64), (16, 16, 96), (16, 16, 128),
        (16, 20, 64), (16, 20, 96), (16, 20, 128),
        (16, 24, 64), (16, 24, 128),
        (16, 32, 64), (16, 32, 128),
    ]:
        try:
            all_data.append(run(n, R, k, timeout_ms=120_000))
        except Exception as e:
            print(f"ERR: {e}")
            all_data.append({"n": n, "R": R, "k": k, "error": str(e)})

    with open("breaking_point_results.json", "w") as f:
        json.dump(all_data, f, indent=2)

    print("\n=== Summary (seeking breaking point) ===")
    print(f"{'n':>3} {'R':>3} {'k':>4} {'time_ms':>12}  status")
    for r in all_data:
        if "error" in r: continue
        t = r.get("time_ms", "?")
        s = "TIMEOUT" if r.get("timeout") else ("UNSAT" if r.get("unsat") else "ok")
        t_s = f"{t:12.1f}" if isinstance(t, (int, float)) else "           -"
        print(f"{r['n']:>3} {r['R']:>3} {r['k']:>4} {t_s}  {s}")
