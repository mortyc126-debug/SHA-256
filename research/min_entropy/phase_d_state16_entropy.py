"""Phase D: empirical test of state[16] effective entropy.

Methodology claims "state[16] bottleneck" enabling O(2^80) MITM.
Interpretation: state[16] has < 256 bits effective entropy when varying
M[0..15] from fixed IV.

Test:
- Fix state0 = IV
- Generate N random M[0..15]
- Compute state[16] for each
- Measure unique state[16] count and collision rate

Expected for random 256-bit values at N=2^16:
- Zero collisions (birthday threshold N≈2^128)
- Any collisions → state[16] < 256 bits effective

Also measures:
- N=2^20 if feasible
- Entropy per state word (state1[0], state1[1], etc.)
"""
import json, os, time, hashlib
from collections import Counter
import numpy as np

import sha256_chimera as ch
from sha256_reverse import (forward_compression, expand_schedule, U32, MASK)


OUT = '/home/user/SHA-256/research/min_entropy/phase_d_state16_entropy.json'


def compute_state_at_r_batch(M_list, r, IV):
    """Vectorized state[r] for list of M[0..15] with fixed IV."""
    N = len(M_list)
    M_arr = np.array(M_list, dtype=np.uint32).reshape(N, 16)
    # Expand schedule
    W = np.empty((N, 64), dtype=np.uint32)
    W[:, :16] = M_arr
    for t in range(16, 64):
        if t >= r + 16: break  # don't expand unneeded
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & ch.MASK
    # Compress
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


def measure_collisions(state_arr, tag=""):
    """Check for full 256-bit collisions and per-word statistics."""
    N = state_arr.shape[0]
    # Hash full state to find collisions quickly
    # Use bytes repr for hashing
    state_bytes = state_arr.tobytes()
    # Convert rows to hashable
    state_rows = [state_arr[i].tobytes() for i in range(N)]
    cnt = Counter(state_rows)
    collisions = sum(c - 1 for c in cnt.values() if c > 1)
    unique = len(cnt)
    # Per-word collisions
    per_word = []
    for w in range(8):
        word_cnt = Counter(state_arr[:, w].tolist())
        word_unique = len(word_cnt)
        word_coll = sum(c - 1 for c in word_cnt.values() if c > 1)
        per_word.append({'word_idx': w, 'unique': word_unique, 'collisions': word_coll})
    return {'N': N, 'full_unique': unique, 'full_collisions': collisions,
            'per_word': per_word, 'tag': tag}


def main():
    t0 = time.time()
    print("# Phase D: state[16] effective entropy empirical test")
    IV = [int(x) for x in ch.IV_VANILLA]

    # Generate N random M[0..15] using counter-based deterministic random
    # (reproducible across runs)
    rng = np.random.default_rng(0xABADCAFE)

    for N_log in [14, 16, 18]:
        N = 2 ** N_log
        print(f"\n## N = 2^{N_log} = {N}...", flush=True)
        ts = time.time()
        # Random M's
        M_list = [list(rng.integers(0, 2**32, size=16, dtype=np.int64)) for _ in range(N)]
        print(f"  M gen: {time.time()-ts:.1f}s", flush=True)
        # Batch compute state[16]
        ts = time.time()
        # Split into batches to manage memory
        BATCH = min(N, 100_000)
        states = np.zeros((N, 8), dtype=np.uint32)
        for start in range(0, N, BATCH):
            end = min(start + BATCH, N)
            states[start:end] = compute_state_at_r_batch(M_list[start:end], 16, IV)
        print(f"  state[16] compute: {time.time()-ts:.1f}s", flush=True)
        # Measure collisions
        ts = time.time()
        result = measure_collisions(states, tag=f"N=2^{N_log}")
        result['N_log'] = N_log
        print(f"  Full-256 unique: {result['full_unique']}/{N}, "
              f"collisions: {result['full_collisions']}", flush=True)
        print(f"  Per-word unique (state[0..7]):")
        for w_info in result['per_word']:
            expected_uniform = min(N, 2**32)
            print(f"    word {w_info['word_idx']}: unique={w_info['unique']} "
                  f"(exp. ~{expected_uniform}), coll={w_info['collisions']}", flush=True)
        print(f"  analysis: {time.time()-ts:.1f}s", flush=True)

        # Interpretation
        full_entropy_bits_lower = int(np.log2(result['full_unique'])) if result['full_unique'] > 0 else 0
        if result['full_collisions'] == 0:
            print(f"  ✓ Full uniqueness at N={N} → state[16] entropy ≥ {full_entropy_bits_lower} bits (≥ 2×log2(N) lower bound)", flush=True)
        else:
            print(f"  ⚠ Collisions found! state[16] entropy < full 256 bits", flush=True)

        if N_log == 18:
            # Save big data only for largest N
            pass

    # Summary
    print(f"\n## Theoretical comparison:")
    print(f"  Random 256-bit: expected 0 collisions at N=2^18")
    print(f"  Random 256-bit birthday: N=2^128 for 50% collision probability")

    out = {
        'IV': [int(x) for x in IV],
        'tests_run': [14, 16, 18],
        'state_r': 16,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
