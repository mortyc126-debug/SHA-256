"""
Scaling benchmark: where does each solver break?
"""
import time, sys, json
from mini_sha import gen_IV, gen_K, single_round
from solvers import (
    brute_force_preimage, sat_bit_preimage, sat_bv_preimage, qt_split_preimage
)


def make_instance(n, R, seed_W=None):
    if seed_W is None:
        seed_W = [(3 * (r + 1) * n) & ((1 << n) - 1) for r in range(R)]
    H0 = gen_IV(n)
    mask = (1 << n) - 1
    K = gen_K(n, R)
    state = tuple(H0)
    for r in range(R):
        state = single_round(state, seed_W[r], K[r], n)
    target = [(H0[i] + state[i]) & mask for i in range(8)]
    return H0, target, seed_W


def run(n, R, timeout_ms=60_000, skip_brute=False):
    H0, target, W_true = make_instance(n, R)
    search_bits = n * R

    print(f"\n=== n={n}, R={R}  search space 2^{search_bits} ===")
    print(f"W_true = {W_true}")

    results = {"n": n, "R": R, "search_bits": search_bits, "W_true": W_true}

    # Brute force (only if feasible)
    if not skip_brute and search_bits <= 28:
        try:
            W, t, iters = brute_force_preimage(H0, target, R, n)
            results["brute"] = {"W": W, "time_ms": t*1000, "iters": iters}
            print(f"  brute:    W={W}  {t*1000:8.1f}ms  {iters:>10d} iters")
        except Exception as e:
            results["brute"] = {"error": str(e)}
    else:
        results["brute"] = {"skipped": True, "reason": "too large"}
        print(f"  brute:    (skipped, search space too large)")

    # SAT bit-level
    try:
        W, t, stats = sat_bit_preimage(H0, target, R, n, timeout_ms=timeout_ms)
        results["sat_bit"] = {"W": W, "time_ms": t*1000, "stats": stats}
        if W is not None:
            print(f"  sat_bit:  W={W}  {t*1000:8.1f}ms  vars/C={stats}")
        else:
            print(f"  sat_bit:  TIMEOUT  {t*1000:8.1f}ms  vars/C={stats}")
    except Exception as e:
        results["sat_bit"] = {"error": str(e)}

    # SAT BitVec
    try:
        W, t, _ = sat_bv_preimage(H0, target, R, n, timeout_ms=timeout_ms)
        results["sat_bv"] = {"W": W, "time_ms": t*1000}
        if W is not None:
            print(f"  sat_bv:   W={W}  {t*1000:8.1f}ms")
        else:
            print(f"  sat_bv:   TIMEOUT  {t*1000:8.1f}ms")
    except Exception as e:
        results["sat_bv"] = {"error": str(e)}

    # QT split (same engine, reports linear fraction)
    try:
        W, t, stats = qt_split_preimage(H0, target, R, n, timeout_ms=timeout_ms)
        results["qt_split"] = {"W": W, "time_ms": t*1000, "linear_frac": stats}
        if W is not None:
            lin, nonlin = stats
            print(f"  qt_split: W={W}  {t*1000:8.1f}ms  linear={lin}  nonlinear={nonlin}  ratio={lin/(lin+nonlin):.2%}")
        else:
            print(f"  qt_split: TIMEOUT")
    except Exception as e:
        results["qt_split"] = {"error": str(e)}

    return results


if __name__ == "__main__":
    all_results = []

    # Grid: n x R
    configs = [
        (4, 2), (4, 3), (4, 4), (4, 6),
        (8, 2), (8, 3), (8, 4), (8, 6),
        (12, 2), (12, 3),
        (16, 2), (16, 3),
    ]

    for n, R in configs:
        try:
            r = run(n, R, timeout_ms=30_000)
            all_results.append(r)
        except Exception as e:
            print(f"  FAILED: {e}")
            all_results.append({"n": n, "R": R, "error": str(e)})

    with open("bench_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print("\n\n=== Summary ===")
    print(f"{'n':>3} {'R':>3} {'bits':>5} {'brute':>10} {'sat_bit':>10} {'sat_bv':>10} {'qt_split':>10} {'lin_frac':>10}")
    for r in all_results:
        if "error" in r: continue
        n = r["n"]; R = r["R"]; sb = r["search_bits"]
        bt = r.get("brute", {}).get("time_ms", None)
        st = r.get("sat_bit", {}).get("time_ms", None)
        bv = r.get("sat_bv", {}).get("time_ms", None)
        qt = r.get("qt_split", {}).get("time_ms", None)
        lf = r.get("qt_split", {}).get("linear_frac", None)
        lf_s = f"{lf[0]/(lf[0]+lf[1]):.2%}" if lf else "  -   "
        bt_s = f"{bt:10.1f}" if bt is not None else "       -  "
        st_s = f"{st:10.1f}" if st is not None else "       -  "
        bv_s = f"{bv:10.1f}" if bv is not None else "       -  "
        qt_s = f"{qt:10.1f}" if qt is not None else "       -  "
        print(f"{n:>3} {R:>3} {sb:>5} {bt_s} {st_s} {bv_s} {qt_s}  {lf_s}")
