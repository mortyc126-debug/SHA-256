"""SHA-512 Σ cascade analysis — compare with SHA-256 pattern.

Test same prefix/reverse window experiment on SHA-512.
SHA-512 scrambles at r=24 (same as SHA-256!) so use same r_obs.

Hypothesis: similar cascade structure. Possible differences:
- Different Σ constants (28,34,39) vs (2,13,22) for Σ₀
- 64-bit vs 32-bit state
- If SHA-512 has SAME critical zone → pattern architectural
- If different → rotation constants matter

Uses SHA-512 implementation from otoc_sha512_rounds.py.
"""
import json, os, time
import numpy as np

from otoc_sha512_rounds import (SHA512_IV, SHA512_K, MASK64,
                                  rotr64, shr64, Sigma0_512, Sigma1_512,
                                  sigma0_512, sigma1_512, Ch64, Maj64)


OUT = '/home/user/SHA-256/research/min_entropy/otoc_sha512_sigma_window_results.json'


def state_sha512_sigma_window_disabled(M_arr, r_obs, disabled_start, disabled_end):
    N = M_arr.shape[0]
    W = np.empty((N, 80), dtype=np.uint64)
    W[:, :16] = M_arr
    for t in range(16, r_obs + 1):
        W[:, t] = (sigma1_512(W[:, t-2]) + W[:, t-7]
                   + sigma0_512(W[:, t-15]) + W[:, t-16]) & MASK64

    iv = np.broadcast_to(SHA512_IV, (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    for t in range(r_obs):
        if disabled_start <= t < disabled_end:
            s0a = a; s1e = e
        else:
            s0a = Sigma0_512(a); s1e = Sigma1_512(e)
        T1 = (h + s1e + Ch64(e, f, g) + SHA512_K[t] + W[:, t]) & MASK64
        T2 = (s0a + Maj64(a, b, c)) & MASK64
        h = g; g = f; f = e
        e = (d + T1) & MASK64
        d = c; c = b; b = a
        a = (T1 + T2) & MASK64
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint64)


def state_to_bits(state):
    N = state.shape[0]
    bytes_be = state.byteswap().view('<u1').reshape(N, 64)
    bits = np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :512]
    return bits


def measure(r_obs, dis_start, dis_end, N=100, seed=42, msg_bytes=128):
    rng = np.random.default_rng(seed)
    base_arr = rng.integers(0, 256, size=(N, msg_bytes), dtype=np.uint8)
    M_base = np.zeros((N, 16), dtype=np.uint64)
    for i in range(N):
        m = base_arr[i].tobytes()
        for w in range(16):
            M_base[i, w] = int.from_bytes(m[8*w:8*(w+1)], 'big')

    state_base = state_sha512_sigma_window_disabled(M_base, r_obs, dis_start, dis_end)
    bits_base = state_to_bits(state_base)

    msg_bits = msg_bytes * 8
    C = np.zeros((msg_bits, 512), dtype=np.float64)
    for i in range(msg_bits):
        byte_idx = i // 8; bit_idx = 7 - (i % 8)
        flip_arr = base_arr.copy()
        flip_arr[:, byte_idx] ^= np.uint8(1 << bit_idx)
        M_flip = np.zeros((N, 16), dtype=np.uint64)
        for j in range(N):
            m = flip_arr[j].tobytes()
            for w in range(16):
                M_flip[j, w] = int.from_bytes(m[8*w:8*(w+1)], 'big')
        state_flip = state_sha512_sigma_window_disabled(M_flip, r_obs, dis_start, dis_end)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# SHA-512 Σ cascade analysis (prefix + reverse window)")

    N = 100
    r_obs = 24  # same as SHA-256 scramble point
    F_inf = 1024 * 512 * 0.25 / N
    print(f"  N={N}, r_obs={r_obs}, F_inf={F_inf:.2f}")

    # Baseline
    C_base = measure(r_obs, -1, -1, N=N)
    F_base = float((C_base**2).sum())
    print(f"  Baseline ||C||² = {F_base:.1f}")

    # Prefix windows
    print(f"\n## Prefix window [0, w) at r_obs={r_obs}")
    print(f"  {'w':>2}   {'||C||²':>10}   {'excess':>10}")
    prefix_results = {}
    for w in [0, 4, 8, 12, 16, 18, 20, 22, 24]:
        C = measure(r_obs, 0, w, N=N)
        F_sq = float((C**2).sum())
        excess = F_sq - F_base
        prefix_results[w] = {'frob_sq': F_sq, 'excess': excess}
        print(f"  {w:>2}   {F_sq:>10.1f}   {excess:>+10.1f}")

    # Reverse windows
    print(f"\n## Reverse window [r_obs-w, r_obs) at r_obs={r_obs}")
    print(f"  {'w':>2}   {'range':>10}   {'||C||²':>10}   {'excess':>10}")
    reverse_results = {}
    for w in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24]:
        C = measure(r_obs, r_obs - w, r_obs, N=N)
        F_sq = float((C**2).sum())
        excess = F_sq - F_base
        rng_str = f"[{r_obs-w},{r_obs})" if w > 0 else 'none'
        reverse_results[w] = {'frob_sq': F_sq, 'excess': excess, 'range': rng_str}
        print(f"  {w:>2}   {rng_str:>10}   {F_sq:>10.1f}   {excess:>+10.1f}")

    # Find critical w for each direction
    prefix_critical = None
    for w in sorted(prefix_results):
        if w > 0 and prefix_results[w]['excess'] > 100:
            prefix_critical = w; break
    reverse_critical = None
    for w in sorted(reverse_results):
        if w > 0 and reverse_results[w]['excess'] > 100:
            reverse_critical = w; break

    print(f"\n## Critical windows (excess > 100):")
    print(f"  Prefix [0, w) critical at w = {prefix_critical}")
    if prefix_critical:
        print(f"     → early rounds useless up to w = {prefix_critical}")
    print(f"  Reverse [r-w, r) critical at w = {reverse_critical}")
    if reverse_critical:
        print(f"     → last {reverse_critical} rounds are scrambling zone")

    print(f"\n## Comparison with SHA-256 at r_obs=24:")
    print(f"  SHA-256 prefix critical w: 18-19 (matches Wang-barrier r=17)")
    print(f"  SHA-512 prefix critical w: {prefix_critical}")
    print(f"  SHA-256 reverse critical w: 8-9 (last 8-9 rounds)")
    print(f"  SHA-512 reverse critical w: {reverse_critical}")

    out = {
        'N': N, 'r_obs': r_obs, 'F_inf': F_inf, 'F_base': F_base,
        'prefix': prefix_results,
        'reverse': reverse_results,
        'prefix_critical_w': prefix_critical,
        'reverse_critical_w': reverse_critical,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
