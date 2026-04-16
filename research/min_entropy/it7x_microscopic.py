"""
IT-7X: SHA-256 microscopic bias detection at surgical scale.

KEY INSIGHT: SHA-256 pushes all signals to ~10^-3 scale. Standard
N=200K gives resolution 3/sqrt(N) = 0.007 — barely touches.
Scale to N=5M → resolution 0.001 → detects biases of 0.003+.

Rerun IT-7W2 logic at N=5M (2.5M train, 2.5M test).
Focus on r=16 where corr=-0.00577 was borderline at N=200K.
At N=2.5M test: z = 0.00577 * sqrt(2.5M) = 9.1 (if real).
"""
import hashlib, json, math, os, time
import numpy as np
import sha256_chimera as ch

N_TOTAL = 5000000
ROUNDS = [8, 12, 16, 20]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it7x_microscopic.json')

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
    c = np.zeros(len(arr), dtype=np.int32)
    for b in range(32): c += ((arr >> b) & 1).astype(np.int32)
    return c

def main():
    t0 = time.time()
    rng = np.random.default_rng(0xDEAD5CA1)
    half = N_TOTAL // 2
    print(f"# IT-7X: microscopic bias, N={N_TOTAL} (train={half}, test={half})")

    # Generate Wang pairs in chunks to save memory
    CHUNK = 500000
    results = {r: {'corr_list': [], 'pred_list': []} for r in ROUNDS}

    for chunk_start in range(0, N_TOTAL, CHUNK):
        chunk_n = min(CHUNK, N_TOTAL - chunk_start)
        is_test = chunk_start >= half
        label = "TEST" if is_test else "TRAIN"
        print(f"\n# Chunk {chunk_start//CHUNK + 1}: {label} {chunk_n} pairs")

        t1 = time.time()
        M1 = [rng.bytes(64) for _ in range(chunk_n)]
        M2 = []
        for m in M1:
            j = int(rng.integers(0, 32))
            m2 = bytearray(m)
            m2[j // 8] ^= (1 << (7 - j % 8))
            M2.append(bytes(m2))

        for r in ROUNDS:
            s1 = compress_r(M1, r); s2 = compress_r(M2, r)
            D = s1 ^ s2
            D_bits = state_to_bits(D)
            hw_e = popcount32(D[:, 4]).astype(np.float32)

            if not is_test:
                # Accumulate train data for this round
                if 'Y_accum' not in results[r]:
                    results[r]['Y_accum'] = []
                    results[r]['hw_accum'] = []
                results[r]['Y_accum'].append(D_bits)
                results[r]['hw_accum'].append(hw_e)
            else:
                results[r]['corr_list'].append((D_bits, hw_e))

        print(f"  chunk time: {time.time()-t1:.1f}s")

    # Train Walsh-2 on accumulated train data, predict on test
    print(f"\n# Training and predicting...")
    final = {}
    for r in ROUNDS:
        Y_train = np.vstack(results[r]['Y_accum'])
        hw_train = np.concatenate(results[r]['hw_accum'])
        N_tr = len(hw_train)
        print(f"\n## Round r={r}: N_train={N_tr}")

        Y_s = 2.0 * Y_train.astype(np.float32) - 1.0
        target = hw_train - hw_train.mean()
        M_in = (Y_s.T @ (Y_s * target[:, None])) / math.sqrt(N_tr)
        del Y_train, Y_s  # free memory

        # Predict on all test chunks
        all_scores = []
        all_hw = []
        for D_bits_te, hw_te in results[r]['corr_list']:
            Y_te = 2.0 * D_bits_te.astype(np.float32) - 1.0
            YM = Y_te @ M_in
            Q = (Y_te * YM).sum(axis=1)
            tr_val = float(np.trace(M_in))
            score = (Q - tr_val) / 2
            all_scores.append(score)
            all_hw.append(hw_te)

        scores = np.concatenate(all_scores)
        hw_test = np.concatenate(all_hw)
        N_te = len(scores)

        corr = float(np.corrcoef(scores, hw_test)[0, 1])
        z = corr * math.sqrt(N_te - 2)
        std_corr = 1.0 / math.sqrt(N_te - 2)

        # Percentile
        n5 = N_te // 20
        top = np.argsort(-scores)[:n5]
        bot = np.argsort(scores)[:n5]
        hw_top = hw_test[top].mean()
        hw_bot = hw_test[bot].mean()
        hw_mean = hw_test.mean()
        std_pct = hw_test.std() / math.sqrt(n5)
        z_top = (hw_top - hw_mean) / std_pct
        z_bot = (hw_bot - hw_mean) / std_pct

        print(f"  N_test = {N_te}")
        print(f"  corr(score, HW_e) = {corr:+.8f}  (std_corr = {std_corr:.8f})")
        print(f"  z = {z:+.2f}")
        print(f"  Top 5%: HW = {hw_top:.4f} (z={z_top:+.2f})")
        print(f"  Bot 5%: HW = {hw_bot:.4f} (z={z_bot:+.2f})")
        print(f"  Mean HW = {hw_mean:.4f}")

        final[r] = {
            'corr': corr, 'z': z, 'N_test': N_te, 'std_corr': std_corr,
            'hw_mean': float(hw_mean), 'hw_std': float(hw_test.std()),
            'top5_hw': float(hw_top), 'bot5_hw': float(hw_bot),
            'z_top': float(z_top), 'z_bot': float(z_bot),
        }

    print(f"\n## Summary (|z| > 3 = significant at microscopic scale)")
    print(f"  {'r':>3}  {'corr':>12}  {'z':>8}  {'z_top':>7}  {'z_bot':>7}  {'sig':>4}")
    for r in ROUNDS:
        f = final[r]
        sig = 'YES' if abs(f['z']) > 3 else 'no'
        print(f"  {r:>3}  {f['corr']:>+12.8f}  {f['z']:>+8.2f}  {f['z_top']:>+7.2f}  {f['z_bot']:>+7.2f}  {sig:>4}")

    out = {'meta': {'N_total': N_TOTAL, 'rounds': ROUNDS}, 'results': final}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}\nTotal: {time.time()-t0:.0f}s")

if __name__ == '__main__':
    main()
