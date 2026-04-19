"""SHA-256 carry cascade analysis (analog Σ cascade but for + → XOR).

Phase 3A: full carry removal V_no_carry gave excess ~0 (small).
Question: при каких rounds carry matters?

Test:
- Prefix [0, w): replace + with XOR ONLY при rounds 0..w-1, keep + after
- Reverse [r-w, r): replace + with XOR при last w rounds

Compare with Σ cascade results.
"""
import json, os, time
import numpy as np
import sha256_chimera as ch


OUT = '/home/user/SHA-256/research/min_entropy/otoc_carry_window_results.json'


def state_at_r_carry_disabled(M_arr, r_obs, disabled_start, disabled_end):
    """State at r_obs with + → XOR at rounds [disabled_start, disabled_end)."""
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
            # XOR instead of +
            T1 = (h ^ ch.Sigma1(e) ^ ch.Ch(e, f, g) ^ np.uint32(K_vals[t]) ^ W[:, t]).astype(np.uint32)
            T2 = (ch.Sigma0(a) ^ ch.Maj(a, b, c)).astype(np.uint32)
            e = (d ^ T1).astype(np.uint32)
            a_new = (T1 ^ T2).astype(np.uint32)
        else:
            T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + np.uint32(K_vals[t]) + W[:, t]) & ch.MASK
            T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & ch.MASK
            e = (d + T1) & ch.MASK
            a_new = (T1 + T2) & ch.MASK
        h = g; g = f; f = e; d = c; c = b; b = a; a = a_new
        # Fix: e was set before shift
    # Note: above has shift issue, redo carefully
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint32)


def state_at_r_carry_disabled_v2(M_arr, r_obs, disabled_start, disabled_end):
    """Correct implementation with proper register shift order."""
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
            T1 = (h ^ ch.Sigma1(e) ^ ch.Ch(e, f, g) ^ np.uint32(K_vals[t]) ^ W[:, t]).astype(np.uint32)
            T2 = (ch.Sigma0(a) ^ ch.Maj(a, b, c)).astype(np.uint32)
            new_e = (d ^ T1).astype(np.uint32)
            new_a = (T1 ^ T2).astype(np.uint32)
        else:
            T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + np.uint32(K_vals[t]) + W[:, t]) & ch.MASK
            T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & ch.MASK
            new_e = (d + T1) & ch.MASK
            new_a = (T1 + T2) & ch.MASK
        h = g; g = f; f = e; e = new_e
        d = c; c = b; b = a; a = new_a
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint32)


def state_to_bits(state):
    bytes_be = state.view('<u1').reshape(state.shape[0], 8, 4)[:, :, ::-1].reshape(state.shape[0], 32)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :256]


def measure(r_obs, dis_start, dis_end, N=200, seed=42):
    rng = np.random.default_rng(seed)
    base_msgs = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)
    state_base = state_at_r_carry_disabled_v2(base_msgs, r_obs, dis_start, dis_end)
    bits_base = state_to_bits(state_base)
    C = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32; bit = 31 - (i % 32)
        flip_msgs = base_msgs.copy()
        flip_msgs[:, word] ^= np.uint32(1 << bit)
        state_flip = state_at_r_carry_disabled_v2(flip_msgs, r_obs, dis_start, dis_end)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# SHA-256 carry cascade analysis (+ → XOR window)")
    N = 200
    r_obs = 24
    F_inf = 512 * 256 * 0.25 / N

    # Baseline (no carry disable)
    C_base = measure(r_obs, -1, -1, N=N)
    F_base = float((C_base ** 2).sum())
    print(f"  Baseline ||C||² = {F_base:.1f} (should match standard OTOC r=24)")

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
    for w in [0, 2, 4, 6, 8, 10, 12, 16, 20, 24]:
        C = measure(r_obs, r_obs - w, r_obs, N=N)
        F_sq = float((C**2).sum())
        excess = F_sq - F_base
        rng_str = f"[{r_obs-w},{r_obs})" if w > 0 else 'none'
        reverse_results[w] = {'frob_sq': F_sq, 'excess': excess, 'range': rng_str}
        print(f"  {w:>2}   {rng_str:>10}   {F_sq:>10.1f}   {excess:>+10.1f}")

    # Critical widths
    def crit_w(res):
        for w in sorted(res):
            if w > 0 and res[w]['excess'] > 100:
                return w
        return None

    pc = crit_w(prefix_results); rc = crit_w(reverse_results)
    print(f"\n## Critical widths (excess > 100):")
    print(f"  Prefix:  w = {pc}")
    print(f"  Reverse: w = {rc}")

    print(f"\n## Comparison:")
    print(f"  Σ cascade (prev): prefix_crit=18-19, reverse_crit=8-9")
    print(f"  Carry cascade:    prefix_crit={pc}, reverse_crit={rc}")

    out = {
        'r_obs': r_obs, 'N': N, 'F_base': F_base,
        'prefix': prefix_results,
        'reverse': reverse_results,
        'prefix_critical_w': pc,
        'reverse_critical_w': rc,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
