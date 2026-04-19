"""Reverse-window Σ disable: confirm "last rounds do scrambling" hypothesis.

Prefix window [0, w) showed: excess ≈ 0 for w ≤ 16, explodes at w ≥ 19.
  → Early Σ useless, late Σ critical.

Reverse window [24-w, 24) prediction:
  If "last rounds critical": excess should grow RAPIDLY with w
  (disabling top w rounds = disabling w critical rounds)

Also test observation at r=16: where's critical zone when observing earlier?
  Expected: last 5-6 rounds before r=16 (i.e., rounds 10-15).
"""
import json, os, time
import numpy as np
import sha256_chimera as ch


OUT = '/home/user/SHA-256/research/min_entropy/otoc_sigma_reverse_window_results.json'


def state_sigma_window_disabled(M_arr, r_obs, disabled_start, disabled_end):
    """Compute state at r_obs with Σ disabled at rounds [disabled_start, disabled_end)."""
    N = M_arr.shape[0]
    W = np.empty((N, 64), dtype=np.uint32)
    W[:, :16] = M_arr
    for t in range(16, r_obs + 1):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & ch.MASK
    iv = np.broadcast_to(np.array(ch.IV_VANILLA, dtype=np.uint32), (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    for t in range(r_obs):
        if disabled_start <= t < disabled_end:
            s0a = a; s1e = e
        else:
            s0a = ch.Sigma0(a); s1e = ch.Sigma1(e)
        T1 = (h + s1e + ch.Ch(e, f, g) + np.uint32(K_vals[t]) + W[:, t]) & ch.MASK
        T2 = (s0a + ch.Maj(a, b, c)) & ch.MASK
        h = g; g = f; f = e
        e = (d + T1) & ch.MASK
        d = c; c = b; b = a
        a = (T1 + T2) & ch.MASK
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint32)


def state_to_bits(state):
    bytes_be = state.view('<u1').reshape(state.shape[0], 8, 4)[:, :, ::-1].reshape(state.shape[0], 32)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :256]


def measure(r_obs, dis_start, dis_end, N=200, seed=42):
    rng = np.random.default_rng(seed)
    base_msgs = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)
    state_base = state_sigma_window_disabled(base_msgs, r_obs, dis_start, dis_end)
    bits_base = state_to_bits(state_base)
    C = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32; bit = 31 - (i % 32)
        flip_msgs = base_msgs.copy()
        flip_msgs[:, word] ^= np.uint32(1 << bit)
        state_flip = state_sigma_window_disabled(flip_msgs, r_obs, dis_start, dis_end)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# Reverse-window Σ disable + multiple observation rounds\n")

    N = 200
    F_inf = 512 * 256 * 0.25 / N
    print(f"  Theoretical RO limit: {F_inf:.2f}")

    all_results = {}

    # For multiple observation rounds, disable Σ at [r_obs-w, r_obs)
    for r_obs in [16, 20, 24]:
        print(f"\n## r_obs = {r_obs}: disable Σ at [r_obs-w, r_obs)")
        print(f"  {'w':>2}   {'range':>12}   {'||C||²':>10}   {'excess':>10}")
        results_r = {}
        # Baseline (no disable)
        C_base = measure(r_obs, -1, -1, N=N)
        F_base = float((C_base ** 2).sum())
        results_r[0] = {'frob_sq': F_base, 'excess': 0.0, 'range': 'none'}
        print(f"  {0:>2}   {'none':>12}   {F_base:>10.1f}   {0.0:>+10.1f}")

        for w in range(1, r_obs + 1):
            dis_start = r_obs - w
            dis_end = r_obs
            C = measure(r_obs, dis_start, dis_end, N=N)
            F_sq = float((C ** 2).sum())
            excess = F_sq - F_base
            rng_str = f"[{dis_start},{dis_end})"
            results_r[w] = {'frob_sq': F_sq, 'excess': excess, 'range': rng_str}
            print(f"  {w:>2}   {rng_str:>12}   {F_sq:>10.1f}   {excess:>+10.1f}")
        all_results[r_obs] = results_r

    # Compare critical zone positions
    print(f"\n## Critical zone analysis (window width w such that excess > 100):")
    for r_obs, res in all_results.items():
        critical_w = None
        for w in sorted(res):
            if w > 0 and res[w]['excess'] > 100:
                critical_w = w; break
        if critical_w:
            print(f"  r_obs={r_obs}: critical_w = {critical_w}, "
                  f"critical zone = rounds [{r_obs-critical_w}, {r_obs})")

    # For r_obs=24 compare with prefix result
    print(f"\n## Reverse vs Prefix window at r_obs=24:")
    print(f"  (prefix [0,w) from previous experiment)")
    if 24 in all_results:
        for w in [4, 8, 12, 16, 20]:
            if w in all_results[24]:
                rev_exc = all_results[24][w]['excess']
                # Prefix from previous results (inline)
                prefix_reference = {4: -0.1, 8: 1.3, 12: 1.3, 16: 1.0, 20: 307.8}
                pre_exc = prefix_reference.get(w, None)
                if pre_exc is not None:
                    print(f"  w={w:>2}: prefix [0,{w}) excess={pre_exc:+.1f}  "
                          f"vs reverse [{24-w},24) excess={rev_exc:+.1f}")

    out = {
        'N': N, 'F_inf': F_inf,
        'all_results': {str(r): {str(w): v for w, v in res.items()} for r, res in all_results.items()},
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
