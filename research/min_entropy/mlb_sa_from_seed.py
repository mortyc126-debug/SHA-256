"""MLB Attack Development Day 1: SA refinement from HW=80 seed.

We have a concrete pair with HW(Δstate1) = 80:
  W0_a = 28,954,919
  W0_b = 13,417,849

Goal: local search to reduce HW below 80. If we find HW=75 or lower
from this seed, we've validated that near-collision attack can be
refined iteratively beyond the filter's initial min.

Strategy: simulated annealing / random walk.
  Start: (W0_a, W0_b) with HW=80
  Propose: flip random bit in W0_a (or W0_b) → W0_new
  Compute new state1_diff, new HW
  Accept if: HW_new < HW_current (greedy) or with Metropolis probability

Run ~20K iterations, track best HW.
"""
import math, os, json, time
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mlb_sa_from_seed.json')


def sha256_state1_single(W0):
    block1 = np.zeros((1, 16), dtype=ch.U32)
    block1[0, 0] = W0
    U32, MASK = ch.U32, ch.MASK
    W = np.empty((1, 64), dtype=U32); W[0, :16] = block1
    for t in range(16, 64):
        W[0, t] = (ch.sigma1(W[0:1, t-2]) + W[0:1, t-7]
                   + ch.sigma0(W[0:1, t-15]) + W[0:1, t-16]) & MASK
    iv = ch.IV_VANILLA.copy()
    a, b, c, d, e, f, g, h = int(iv[0]), int(iv[1]), int(iv[2]), int(iv[3]), int(iv[4]), int(iv[5]), int(iv[6]), int(iv[7])
    K_vals = ch.K_VANILLA
    for t in range(64):
        T1 = (h + (int(ch.Sigma1(np.uint32(e)))) + ((e & f) ^ ((~e) & g)) + int(K_vals[t]) + int(W[0, t])) & 0xFFFFFFFF
        T2 = (int(ch.Sigma0(np.uint32(a))) + ((a & b) ^ (a & c) ^ (b & c))) & 0xFFFFFFFF
        h, g, f = g, f, e
        e = (d + T1) & 0xFFFFFFFF
        d, c, b = c, b, a
        a = (T1 + T2) & 0xFFFFFFFF
    s1 = np.array([a, b, c, d, e, f, g, h], dtype=np.uint32)
    return (s1 + ch.IV_VANILLA) & 0xFFFFFFFF


def sha256_state1_batch(W0_list):
    """Batch state1 for list of W[0]s."""
    N = len(W0_list)
    block1 = np.zeros((N, 16), dtype=ch.U32)
    block1[:, 0] = np.array(W0_list, dtype=ch.U32)
    U32, MASK = ch.U32, ch.MASK
    W = np.empty((N, 64), dtype=U32); W[:, :16] = block1
    for t in range(16, 64):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    iv = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    for t in range(64):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_vals[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    s1 = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    return (s1 + ch.IV_VANILLA) & MASK


def hw256(s_A, s_B):
    hw = 0
    for i in range(8):
        hw += bin(int(s_A[i]) ^ int(s_B[i])).count('1')
    return hw


def main():
    t0 = time.time()
    print(f"# MLB Attack Day 1: SA refinement from HW=80 seed")

    # Initial seed from Week 2 Day 2
    W0_a = 28_954_919
    W0_b = 13_417_849
    s1_a = sha256_state1_batch([W0_a])[0]
    s1_b = sha256_state1_batch([W0_b])[0]
    initial_hw = hw256(s1_a, s1_b)
    print(f"Initial: W0_a={W0_a}, W0_b={W0_b}, HW={initial_hw}")

    # Strategy: greedy local search + occasional restarts
    best_hw = initial_hw
    best_pair = (W0_a, W0_b)
    # Current state
    cur_a, cur_b, cur_hw = W0_a, W0_b, initial_hw
    cur_s1_a, cur_s1_b = s1_a, s1_b

    N_ITERS = 30_000
    rng = np.random.default_rng(0xABCDEF)
    print(f"\n# Running {N_ITERS} SA iterations...")

    accept_count = 0
    improvement_count = 0
    history = []

    for it in range(N_ITERS):
        # Propose: flip random bit in either W0_a or W0_b
        which = rng.integers(0, 2)
        bit_pos = rng.integers(0, 32)
        if which == 0:
            new_a = cur_a ^ (1 << bit_pos)
            new_b = cur_b
        else:
            new_a = cur_a
            new_b = cur_b ^ (1 << bit_pos)

        # Compute new state1 (for changed one)
        if which == 0:
            new_s1_a = sha256_state1_batch([new_a])[0]
            new_s1_b = cur_s1_b
        else:
            new_s1_a = cur_s1_a
            new_s1_b = sha256_state1_batch([new_b])[0]

        new_hw = hw256(new_s1_a, new_s1_b)

        # Accept: greedy or Metropolis
        # Temperature schedule: T starts at 3, cool to 0.1
        T = 3.0 * (1 - it / N_ITERS) + 0.1
        delta = new_hw - cur_hw
        if delta < 0:
            accept = True
        else:
            accept = rng.random() < math.exp(-delta / T)

        if accept:
            cur_a, cur_b, cur_hw = new_a, new_b, new_hw
            cur_s1_a, cur_s1_b = new_s1_a, new_s1_b
            accept_count += 1
            if cur_hw < best_hw:
                best_hw = cur_hw
                best_pair = (cur_a, cur_b)
                improvement_count += 1
                print(f"  iter {it+1:>6}: HW = {best_hw} ★ (accept rate {accept_count/(it+1):.2f})", flush=True)

        if (it + 1) % 5000 == 0:
            print(f"  iter {it+1:>6}: cur HW = {cur_hw}, best HW = {best_hw}, T = {T:.2f}")
        history.append({'iter': it, 'hw': cur_hw, 'best': best_hw})

    print(f"\n=== SA RESULT ===")
    print(f"Initial: HW = {initial_hw}")
    print(f"Best:    HW = {best_hw} (pair: W0_a={best_pair[0]}, W0_b={best_pair[1]})")
    print(f"Improvement: {initial_hw - best_hw} bits")
    print(f"Accept rate: {accept_count/N_ITERS:.3f}")
    print(f"Number of improvements: {improvement_count}")

    # Verify best pair
    s1_check_a = sha256_state1_batch([best_pair[0]])[0]
    s1_check_b = sha256_state1_batch([best_pair[1]])[0]
    verify_hw = hw256(s1_check_a, s1_check_b)
    print(f"Verification HW: {verify_hw} {'✓' if verify_hw == best_hw else 'MISMATCH!'}")

    out = {'seed': {'W0_a': W0_a, 'W0_b': W0_b, 'HW': initial_hw},
           'best': {'W0_a': int(best_pair[0]), 'W0_b': int(best_pair[1]), 'HW': best_hw},
           'improvement': initial_hw - best_hw,
           'accept_rate': accept_count/N_ITERS,
           'n_improvements': improvement_count,
           'n_iters': N_ITERS,
           'runtime_sec': time.time() - t0}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
