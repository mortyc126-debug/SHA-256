"""Σ disabling window analysis.

Single-round Σ disable: ~2 excess (negligible).
All Σ removed: ~5827 excess.
→ Scrambling is SUPER-ADDITIVE.

Test: disable Σ at CONSECUTIVE rounds [k, k+1, ..., k+w-1].
How does excess scale with window width w?

Hypothesis: exponential growth with w (matching cascade expectation).
Concrete test: for fixed start k=0, vary w=1..12.
"""
import json, os, time
import numpy as np
import sha256_chimera as ch


OUT = '/home/user/SHA-256/research/min_entropy/otoc_sigma_window_results.json'


def state_at_r24_sigma_disabled_in_window(M_arr, k_start, w):
    N = M_arr.shape[0]
    r = 24
    W = np.empty((N, 64), dtype=np.uint32)
    W[:, :16] = M_arr
    for t in range(16, r + 1):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & ch.MASK
    iv = np.broadcast_to(np.array(ch.IV_VANILLA, dtype=np.uint32), (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    k_end = k_start + w
    for t in range(r):
        if k_start <= t < k_end:
            s0a = a; s1e = e  # identity
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


def measure_window(k_start, w, N=200, seed=42):
    rng = np.random.default_rng(seed)
    base_msgs = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)
    state_base = state_at_r24_sigma_disabled_in_window(base_msgs, k_start, w)
    bits_base = state_to_bits(state_base)
    C = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32; bit = 31 - (i % 32)
        flip_msgs = base_msgs.copy()
        flip_msgs[:, word] ^= np.uint32(1 << bit)
        state_flip = state_at_r24_sigma_disabled_in_window(flip_msgs, k_start, w)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# Σ-window disabling: cascade growth analysis")
    print(f"  Disable Σ at rounds [k_start, k_start+w), measure OTOC r=24\n")

    N = 200
    k_start = 0
    widths = list(range(0, 25))

    print(f"  {'w':>2}   {'range':>12}   {'||C||²':>10}   {'excess':>10}")
    results = {}
    F_base = None
    for w in widths:
        ts = time.time()
        C = measure_window(k_start, w, N=N)
        F_sq = float((C ** 2).sum())
        if w == 0: F_base = F_sq
        excess = F_sq - F_base
        rng_str = f"[{k_start},{k_start+w})" if w > 0 else "none"
        results[w] = {'frob_sq': F_sq, 'excess': excess, 'range': rng_str,
                      'time': time.time()-ts}
        print(f"  {w:>2}   {rng_str:>12}   {F_sq:>10.1f}   {excess:>+10.1f}")

    # Analyze growth pattern
    print(f"\n## Growth analysis (excess vs window width):")
    print(f"  Single-round (w=1) excess:  {results[1]['excess']:.2f}")
    print(f"  w=2 excess: {results[2]['excess']:.2f} ({results[2]['excess']/results[1]['excess']:.1f}× w=1)")
    print(f"  w=4 excess: {results[4]['excess']:.2f}")
    print(f"  w=8 excess: {results[8]['excess']:.2f}")
    print(f"  w=12 excess: {results[12]['excess']:.2f}")
    print(f"  w=16 excess: {results[16]['excess']:.2f}")
    print(f"  w=24 excess: {results[24]['excess']:.2f} (all Σ disabled)")

    # Check if exponential
    es = [results[w]['excess'] for w in widths if w >= 2 and results[w]['excess'] > 1]
    ws = [w for w in widths if w >= 2 and results[w]['excess'] > 1]
    if len(es) >= 3:
        log_e = np.log(es)
        slope, intercept = np.polyfit(ws, log_e, 1)
        print(f"\n  Exponential fit: excess ≈ {np.exp(intercept):.2f} · exp({slope:.3f} · w)")
        print(f"  → scrambling loss rate per disabled round: {slope:.3f} per round")
        print(f"  → e-fold increase every {1/slope:.2f} disabled rounds")

    out = {
        'N': N, 'k_start': k_start,
        'widths': widths,
        'per_width': {str(w): v for w, v in results.items()},
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
