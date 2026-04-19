"""MITM (Meet-in-the-Middle) demonstration on reduced-round SHA-256.

Free-start MITM: find (state0, W) such that compress_r(state0, W) has a
specific 32-bit prefix matching. Splits at middle round.

For r=24 split at round 12:
  Forward: random (state0, W[0..11]) → state[12]_prefix32
  Backward: target T + random W[12..23] → state[12]_prefix32 (via reverse_compress)
  Match in 32-bit slice → preimage candidate

Theoretical: birthday on 32-bit slice with N forward + N backward needs
N ≈ 2^16 each for ~1 expected match.

This is a TECHNIQUE DEMO showing reverse_compression works in attack context.
Measures actual cost vs theoretical 2 × N = 2^17 round-evaluations.
"""
import hashlib, json, os, time
from collections import defaultdict
import numpy as np

import sha256_chimera as ch
from sha256_reverse import (forward_compression, reverse_compression,
                             expand_schedule, U32, MASK)


OUT = '/home/user/SHA-256/research/min_entropy/mitm_demo_results.json'


def random_state(rng):
    return tuple(U32(x) for x in rng.integers(0, 2**32, size=8))


def random_W16(rng):
    return [int(x) for x in rng.integers(0, 2**32, size=16, dtype=np.int64)]


def state_prefix32(state):
    """First 32 bits of state = state[0]."""
    return int(state[0])


def mitm_attack_demo(target_prefix, r=24, N_forward=2**16, N_backward=2**16, seed=0):
    """MITM attack demo: find (state0, W) giving state[r][0] == target_prefix.

    Returns: (state0, W_full, state_at_r) or None if not found.
    """
    rng_f = np.random.default_rng(seed)
    rng_b = np.random.default_rng(seed + 1)
    K = ch.K_VANILLA
    r_mid = r // 2  # split at middle

    # === Forward phase ===
    # For each forward sample: random (state0, W[0..r_mid-1]).
    # Need to expand schedule for these W's, but full W[16..63] depend on W[0..15].
    # For simplicity, we pick W[0..r_mid-1] random and need W[16..63] for forward to round r_mid only.
    # But forward to round r_mid only needs W[0..r_mid-1]. So just pick those random.
    # Note: this is FREE-SCHEDULE MITM (not standard SHA), legitimate as building block demo.

    print(f"  Forward phase: {N_forward} samples...", flush=True)
    forward_table = defaultdict(list)
    ts = time.time()
    for i in range(N_forward):
        state0 = random_state(rng_f)
        # Random W for forward part
        W_fwd = [int(x) for x in rng_f.integers(0, 2**32, size=r_mid, dtype=np.int64)]
        # Forward r_mid rounds
        s_mid = state0
        for t in range(r_mid):
            s_mid = forward_round_simple(s_mid, W_fwd[t], int(K[t]))
        prefix = state_prefix32(s_mid)
        forward_table[prefix].append((state0, W_fwd))
    print(f"    {time.time()-ts:.1f}s, {len(forward_table)} unique prefixes", flush=True)

    # === Backward phase ===
    # For each backward sample: random target_state[r] with target prefix, W[r_mid..r-1] random.
    # Note: target_state[r] partially determined (must have prefix=target_prefix), other bits random.
    # Reverse from state[r] to state[r_mid].

    print(f"  Backward phase: {N_backward} samples...", flush=True)
    matches = []
    prefix_match_count = 0
    ts = time.time()
    for i in range(N_backward):
        # Construct target state[r] with desired prefix in first word
        target_state = [target_prefix] + [int(x) for x in rng_b.integers(0, 2**32, size=7, dtype=np.int64)]
        target_state = tuple(U32(x) for x in target_state)
        # Random W for backward part (indices r_mid..r-1)
        W_bwd = [int(x) for x in rng_b.integers(0, 2**32, size=r-r_mid, dtype=np.int64)]
        # Reverse r-r_mid rounds: state[r] → state[r_mid]
        s = target_state
        for t in range(r-1, r_mid-1, -1):
            s = reverse_round_simple(s, W_bwd[t-r_mid], int(K[t]))
        prefix = state_prefix32(s)
        # Look up in forward table
        if prefix in forward_table:
            for (state0, W_fwd) in forward_table[prefix]:
                prefix_match_count += 1
                # FULL match check (all 256 bits)
                full_fwd = forward_compress(state0, W_fwd + W_bwd, r, K)
                if full_fwd == target_state:
                    matches.append({
                        'state0': [int(x) for x in state0],
                        'W': W_fwd + W_bwd,
                        'state_at_r': [int(x) for x in target_state],
                    })
    print(f"    {time.time()-ts:.1f}s, {prefix_match_count} prefix-32 matches, "
          f"{len(matches)} full-256 matches", flush=True)
    return matches, prefix_match_count


# Inline simple forward/reverse for speed (avoid module overhead)
def forward_round_simple(state, W_t, K_t):
    a, b, c, d, e, f, g, h = state
    T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_t) + U32(W_t)) & MASK
    T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
    return ((T1+T2) & MASK, a, b, c, (d+T1) & MASK, e, f, g)


def reverse_round_simple(state_n, W_t, K_t):
    a_n, b_n, c_n, d_n, e_n, f_n, g_n, h_n = state_n
    a_o = b_n; b_o = c_n; c_o = d_n
    e_o = f_n; f_o = g_n; g_o = h_n
    T2 = (ch.Sigma0(a_o) + ch.Maj(a_o, b_o, c_o)) & MASK
    T1 = (a_n - T2) & MASK
    d_o = (e_n - T1) & MASK
    h_o = (T1 - ch.Sigma1(e_o) - ch.Ch(e_o, f_o, g_o)
           - U32(K_t) - U32(W_t)) & MASK
    return (a_o, b_o, c_o, d_o, e_o, f_o, g_o, h_o)


def forward_compress(state0, W_full, r, K):
    s = state0
    for t in range(r):
        s = forward_round_simple(s, W_full[t], int(K[t]))
    return s


def measure_brute_force(target_prefix, r=24, N=2**16, seed=0):
    """Brute force baseline: random (state0, W) until 32-bit prefix matches."""
    rng = np.random.default_rng(seed)
    K = ch.K_VANILLA
    ts = time.time()
    found = 0
    for i in range(N):
        state0 = random_state(rng)
        W = [int(x) for x in rng.integers(0, 2**32, size=r, dtype=np.int64)]
        s = state0
        for t in range(r):
            s = forward_round_simple(s, W[t], int(K[t]))
        if int(s[0]) == target_prefix:
            found += 1
    el = time.time() - ts
    return el, found


def main():
    t0 = time.time()
    print("# MITM demo on free-start reduced SHA-256, 32-bit slice match")

    target_prefix = 0xCAFEBABE
    r = 24
    N = 2**17  # 131072 each side; expect N²/2^32 = 4 prefix matches

    print(f"\nTarget prefix (state[r][0]): 0x{target_prefix:08X}, r={r}")
    print(f"N_forward = N_backward = 2^{int(np.log2(N))} = {N}")

    # Brute force baseline
    print(f"\n## Brute force baseline (N samples random):")
    bf_time, bf_found = measure_brute_force(target_prefix, r=r, N=N)
    print(f"  Time: {bf_time:.1f}s, found: {bf_found} (expected ≈ N/2^32 = {N/2**32:.4f})")

    # MITM
    print(f"\n## MITM (split at round {r//2}):")
    matches, prefix_matches = mitm_attack_demo(target_prefix, r=r, N_forward=N, N_backward=N)
    print(f"\n## MITM results:")
    print(f"  prefix-32 matches: {prefix_matches} (expected ≈ N²/2^32 = {N*N/2**32:.2f})")
    print(f"  full-256 matches: {len(matches)} (expected ≈ N²/2^256 = {N*N/2**256:.2e})")
    if matches:
        m = matches[0]
        print(f"  First full match: state0[0..3]={m['state0'][:4]}")
        print(f"                    state[r][0]={hex(m['state_at_r'][0])} (target {hex(target_prefix)})")

    # Theoretical analysis
    print(f"\n## Theoretical:")
    print(f"  N_fwd × N_bwd / 2^32 = {N*N/2**32:.2f} expected 32-bit prefix matches")
    print(f"  Of those: 1/2^224 are full 256-bit collisions = {N*N/2**256:.2e} expected")
    print(f"  → MITM finds 32-bit-aligned candidates at rate {N*N/2**32:.2f}")

    out = {
        'target_prefix': hex(target_prefix),
        'r': r, 'N': N,
        'brute_force_time_s': bf_time,
        'brute_force_found': bf_found,
        'mitm_full_matches': len(matches),
        'mitm_prefix32_matches': prefix_matches,
        'mitm_first_match': matches[0] if matches else None,
        'theoretical_prefix32_matches': N*N/2**32,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
