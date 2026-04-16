"""
IT-7W2: Continuous-target Wang probe.

Fix: delta_e=0 is too rare. Use HW(delta_e[r]) as continuous target.
Train chain-2 score to PREDICT HW(delta_e) at reduced rounds.

If corr(score, HW) > 0 on holdout → state_diff Walsh-2 has predictive
info about e-register proximity, usable for guided search.
"""
import hashlib, json, math, os, time
import numpy as np
import sha256_chimera as ch

N = 200000
ROUNDS = [8, 12, 16, 20]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it7w2_results.json')

def compress_r(messages, r):
    N = len(messages); U32, MASK = ch.U32, ch.MASK; K = ch.K_VANILLA
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    W = np.empty((N, max(r, 16)), dtype=U32); W[:, :16] = block
    for t in range(16, r):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7] + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    a, b, c, d, e, f, g, h = (state[:, i].copy() for i in range(8))
    for t in range(r):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e; e = (d + T1) & MASK; d = c; c = b; b = a; a = (T1 + T2) & MASK
    new = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    return (new + state) & MASK

def state_to_bits(state):
    N = state.shape[0]; bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w*32+b] = ((state[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits

def popcount32(arr):
    """Hamming weight of uint32 array."""
    c = np.zeros(len(arr), dtype=np.int32)
    for b in range(32):
        c += ((arr >> b) & 1).astype(np.int32)
    return c

def main():
    t0 = time.time()
    rng = np.random.default_rng(0xAACC)
    print(f"# IT-7W2: continuous Wang probe, N={N}")

    # Generate Wang pairs: M' = M with single random bit flip in W[0]
    M1 = [rng.bytes(64) for _ in range(N)]
    M2 = []
    for m in M1:
        j = int(rng.integers(0, 32))
        m2 = bytearray(m)
        m2[j // 8] ^= (1 << (7 - j % 8))
        M2.append(bytes(m2))

    results = {}
    for r in ROUNDS:
        print(f"\n## Round r = {r}")
        t1 = time.time()
        s1 = compress_r(M1, r); s2 = compress_r(M2, r)
        D = s1 ^ s2                             # (N, 8) uint32 state diff
        D_bits = state_to_bits(D)               # (N, 256) binary

        # Target: HW of e-register diff (word 4)
        hw_e = popcount32(D[:, 4]).astype(np.float32)
        print(f"  HW(delta_e[{r}]): mean={hw_e.mean():.2f} std={hw_e.std():.2f} "
              f"min={hw_e.min()} max={hw_e.max()}")

        # Also HW of full state diff
        hw_full = D_bits.sum(axis=1).astype(np.float32)

        # Train Walsh-2 score on first half → predict HW(delta_e) on second half
        half = N // 2
        Y_tr = 2.0 * D_bits[:half].astype(np.float32) - 1.0
        target_tr = hw_e[:half]
        # "signed target": center it
        st_tr = target_tr - target_tr.mean()

        M_in = (Y_tr.T @ (Y_tr * st_tr[:, None])) / math.sqrt(half)

        # Score on test half
        Y_te = 2.0 * D_bits[half:].astype(np.float32) - 1.0
        YM = Y_te @ M_in
        Q = (Y_te * YM).sum(axis=1)
        tr_val = float(np.trace(M_in))
        score = (Q - tr_val) / 2

        # Correlation with actual HW on test
        corr_e = float(np.corrcoef(score, hw_e[half:])[0, 1])
        corr_full = float(np.corrcoef(score, hw_full[half:])[0, 1])

        # Also: does score predict HW of a-register diff? (word 0)
        hw_a = popcount32(D[:, 0]).astype(np.float32)
        corr_a = float(np.corrcoef(score, hw_a[half:])[0, 1])

        # Percentile test
        n10 = N // 20   # 5% = 10000
        top = np.argsort(-score)[:n10]
        bot = np.argsort(score)[:n10]
        hw_top = hw_e[half:][top].mean()
        hw_bot = hw_e[half:][bot].mean()
        hw_rnd = hw_e[half:].mean()
        std_pct = hw_e[half:].std() / math.sqrt(n10)
        z_top = (hw_top - hw_rnd) / std_pct
        z_bot = (hw_bot - hw_rnd) / std_pct

        print(f"  corr(score, HW_e_test) = {corr_e:+.6f}")
        print(f"  corr(score, HW_full)   = {corr_full:+.6f}")
        print(f"  corr(score, HW_a)      = {corr_a:+.6f}")
        print(f"  Top 5%: HW_e = {hw_top:.2f} (z={z_top:+.2f})")
        print(f"  Bot 5%: HW_e = {hw_bot:.2f} (z={z_bot:+.2f})")
        print(f"  Random: HW_e = {hw_rnd:.2f}")
        print(f"  ({time.time()-t1:.1f}s)")

        results[r] = {
            'hw_e_mean': float(hw_e.mean()), 'hw_e_std': float(hw_e.std()),
            'corr_e': corr_e, 'corr_full': corr_full, 'corr_a': corr_a,
            'top5_hw': float(hw_top), 'bot5_hw': float(hw_bot),
            'z_top': float(z_top), 'z_bot': float(z_bot),
        }

    print(f"\n## Summary")
    print(f"  {'r':>3}  {'corr_e':>10}  {'corr_full':>10}  {'z_top':>7}  {'z_bot':>7}")
    for r in ROUNDS:
        info = results[r]
        print(f"  {r:>3}  {info['corr_e']:>+10.6f}  {info['corr_full']:>+10.6f}  "
              f"{info['z_top']:>+7.2f}  {info['z_bot']:>+7.2f}")

    out = {'meta': {'N': N, 'rounds': ROUNDS}, 'results': results}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}\nTotal: {time.time()-t0:.0f}s")

if __name__ == '__main__':
    main()
