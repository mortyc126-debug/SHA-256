"""Phase D part 2: state[16] entropy on STRUCTURED M inputs (HW=2 like MLB).

Previous test (random M): state[16] has full 256-bit entropy.
Methodology's O(2^80) claim may only apply to structured M.

Test with M restricted to:
- W[0] varies over [0, 2^18)
- W[1..15] = 0 (same as MLB restricted form)

If state[16] has reduced entropy under this restriction, that's the
structural bottleneck methodology references.
"""
import json, os, time
from collections import Counter
import numpy as np

import sha256_chimera as ch


OUT = '/home/user/SHA-256/research/min_entropy/phase_d_structured_state16.json'


def compute_state_at_r_batch_mlb(W0_start, W0_end, r, IV):
    """State[r] for M = (W[0] ∈ [start,end), W[1..15]=0)."""
    N = W0_end - W0_start
    M_arr = np.zeros((N, 16), dtype=np.uint32)
    M_arr[:, 0] = np.arange(W0_start, W0_end, dtype=np.uint32)
    W = np.empty((N, 64), dtype=np.uint32)
    W[:, :16] = M_arr
    for t in range(16, 64):
        if t >= r + 16: break
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & ch.MASK
    iv = np.broadcast_to(np.array(IV, dtype=np.uint32), (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    for t in range(r):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + np.uint32(K_vals[t]) + W[:, t]) & ch.MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & ch.MASK
        h = g; g = f; f = e
        e = (d + T1) & ch.MASK
        d = c; c = b; b = a
        a = (T1 + T2) & ch.MASK
    state = np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint32)
    return state


def measure(states, tag=""):
    N = states.shape[0]
    state_rows = [states[i].tobytes() for i in range(N)]
    cnt = Counter(state_rows)
    collisions = sum(c - 1 for c in cnt.values() if c > 1)
    unique = len(cnt)
    per_word = []
    for w in range(8):
        word_cnt = Counter(states[:, w].tolist())
        word_unique = len(word_cnt)
        word_coll = sum(c - 1 for c in word_cnt.values() if c > 1)
        per_word.append({'word': w, 'unique': word_unique, 'coll': word_coll})
    return {'tag': tag, 'N': N, 'full_unique': unique, 'full_coll': collisions, 'per_word': per_word}


def main():
    t0 = time.time()
    print("# Phase D part 2: state[r] entropy with structured M (HW=2 like MLB)")
    IV = [int(x) for x in ch.IV_VANILLA]

    # Note: M = [W0, 0, 0, ..., 0] - only W[0] varies. Input entropy = log2(N)
    # Ideal random state[r]: has entropy = min(256, log2(N))
    # If state[r] entropy = log2(N) strictly → no information loss
    # If < log2(N) → structural collapse (THE bottleneck)

    for r in [4, 8, 12, 16, 20, 24, 32]:
        print(f"\n## r = {r}", flush=True)
        for N_log in [16, 18, 20]:
            N = 2**N_log
            ts = time.time()
            # Compute state[r] for W[0] in [0, N)
            BATCH = min(N, 200_000)
            states = np.zeros((N, 8), dtype=np.uint32)
            for start in range(0, N, BATCH):
                end = min(start + BATCH, N)
                states[start:end] = compute_state_at_r_batch_mlb(start, end, r, IV)
            # Measure
            state_rows_b = [states[i].tobytes() for i in range(N)]
            cnt = Counter(state_rows_b)
            full_unique = len(cnt)
            full_coll = sum(c - 1 for c in cnt.values() if c > 1)
            print(f"  N=2^{N_log}={N}, full_unique={full_unique}/{N}, "
                  f"collisions={full_coll}  ({time.time()-ts:.1f}s)", flush=True)
            if full_coll > 0:
                # Get example colliding M values
                examples = [(k, v) for k, v in cnt.items() if v > 1][:3]
                for k, v in examples:
                    s = np.frombuffer(k, dtype=np.uint32)
                    print(f"    collision x{v}: state[r] = {' '.join(f'{int(x):08x}' for x in s)}", flush=True)

    out = {
        'protocol': 'M = [W0, 0, 0, ..., 0], W[0] in [0, N)',
        'IV': IV,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
