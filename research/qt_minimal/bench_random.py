"""
Bench with RANDOM W — to check the regular-pattern was not making it trivial.
Also: increase R to probe where SAT-BV starts struggling.
"""
import time, random, json
from mini_sha import gen_IV, gen_K, single_round
from solvers import sat_bv_preimage, sat_bit_preimage

def make_random_instance(n, R, seed):
    random.seed(seed)
    mask = (1 << n) - 1
    W_true = [random.randint(0, mask) for _ in range(R)]
    H0 = gen_IV(n)
    K = gen_K(n, R)
    state = tuple(H0)
    for r in range(R):
        state = single_round(state, W_true[r], K[r], n)
    target = [(H0[i] + state[i]) & mask for i in range(8)]
    return H0, target, W_true

def run_trial(n, R, trials=5, timeout_ms=120_000):
    bv_times = []
    bit_times = []
    for trial in range(trials):
        H0, target, W_true = make_random_instance(n, R, seed=trial*17+R*n)
        try:
            W, t, _ = sat_bv_preimage(H0, target, R, n, timeout_ms=timeout_ms)
            bv_times.append(t*1000)
            ok = " ok" if W is not None else " TIMEOUT"
        except Exception as e:
            bv_times.append(None); ok = f"err:{e}"
        print(f"  n={n} R={R} trial={trial} W_true={W_true} bv_time={bv_times[-1]}ms{ok}")
    return bv_times

if __name__ == "__main__":
    print("=== SAT BitVec with RANDOM W ===\n")
    results = {}
    # Push R up to find breaking point
    for n in [8, 12, 16]:
        for R in [3, 4, 6, 8, 12]:
            key = f"n{n}_R{R}"
            print(f"\n-- n={n}, R={R}, search 2^{n*R} --")
            times = run_trial(n, R, trials=3, timeout_ms=60_000)
            results[key] = times

    with open("bench_random_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n\n=== Median BV times (ms) ===")
    print(f"{'':>6}", end="")
    for R in [3, 4, 6, 8, 12]: print(f"  R={R:<3}", end="")
    print()
    for n in [8, 12, 16]:
        print(f"n={n:<3}", end="  ")
        for R in [3, 4, 6, 8, 12]:
            key = f"n{n}_R{R}"
            ts = results.get(key, [])
            valid = [t for t in ts if t is not None and t < 60_000]
            if valid:
                med = sorted(valid)[len(valid)//2]
                print(f"{med:>6.0f}", end="  ")
            else:
                print(f"   T/O", end="  ")
        print()
