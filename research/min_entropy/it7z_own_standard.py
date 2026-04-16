"""
IT-7Z: SHA-256 own-standard signal protocol.

SHA-256 is NOT random — it masquerades as random. Standard z>3 is the
threshold it was optimized against. We define OUR OWN standards:

S1: Cross-round sign consistency (sign-test across rounds)
S2: Fisher's combined p across independent round-tests
S3: Sign stability at growing N (does sign persist at 5M → 20M?)
S4: Block bootstrap sign fraction (K=200 blocks, count sign fraction)

Run at N=20M to test sign stability from IT-7X (N=5M, all positive).
If all 4 rounds stay positive → P(H0) = (0.0625)^2 = 0.004 (combined).
"""
import hashlib, json, math, os, time
import numpy as np
import sha256_chimera as ch

N_TOTAL = 20000000
ROUNDS = [8, 12, 16, 20]
K_BLOCKS = 200      # for bootstrap sign-fraction
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it7z_own_standard.json')

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

def popcount32(arr):
    c = np.zeros(len(arr), dtype=np.int32)
    for b in range(32): c += ((arr >> b) & 1).astype(np.int32)
    return c

def state_to_bits_subset(state, n_bits=64):
    """First n_bits of 256-bit state for memory efficiency."""
    N = state.shape[0]; bits = np.zeros((N, n_bits), dtype=np.uint8)
    for i in range(n_bits):
        w = i // 32; b = i % 32
        bits[:, i] = ((state[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits

def main():
    t_total = time.time()
    half = N_TOTAL // 2
    CHUNK = 1000000  # process in chunks of 1M to save memory
    print(f"# IT-7Z: own-standard protocol at N={N_TOTAL}")

    rng = np.random.default_rng(0xABCD1234)

    # We'll accumulate M_in (train) across chunks, then score test chunks
    # Use only 64 state bits (first 2 words) to keep M_in manageable
    NBITS = 64   # use first 64 bits of 256

    for r in ROUNDS:
        print(f"\n## Round r={r}")
        t_r = time.time()

        # Pass 1: train — accumulate weighted covariance
        YtY_sf = np.zeros((NBITS, NBITS), dtype=np.float64)
        N_tr = 0
        for c_start in range(0, half, CHUNK):
            c_n = min(CHUNK, half - c_start)
            M1 = [rng.bytes(64) for _ in range(c_n)]
            M2 = []
            for m in M1:
                j = int(rng.integers(0, 32))
                m2 = bytearray(m)
                m2[j // 8] ^= (1 << (7 - j % 8))
                M2.append(bytes(m2))
            s1 = compress_r(M1, r); s2 = compress_r(M2, r)
            D = s1 ^ s2
            D_bits = state_to_bits_subset(D, NBITS)
            hw_e = popcount32(D[:, 4]).astype(np.float32)
            target = hw_e - hw_e.mean()
            Y = 2.0 * D_bits.astype(np.float32) - 1.0
            YtY_sf += (Y.T @ (Y * target[:, None])).astype(np.float64)
            N_tr += c_n
        M_in = YtY_sf / math.sqrt(N_tr)
        print(f"  Train: {N_tr} pairs, {time.time()-t_r:.1f}s")

        # Pass 2: test — score each chunk and accumulate corr
        all_scores = []
        all_hw = []
        block_corrs = []
        for c_start in range(0, half, CHUNK):
            c_n = min(CHUNK, half - c_start)
            M1 = [rng.bytes(64) for _ in range(c_n)]
            M2 = []
            for m in M1:
                j = int(rng.integers(0, 32))
                m2 = bytearray(m)
                m2[j // 8] ^= (1 << (7 - j % 8))
                M2.append(bytes(m2))
            s1 = compress_r(M1, r); s2 = compress_r(M2, r)
            D = s1 ^ s2
            D_bits = state_to_bits_subset(D, NBITS)
            hw_e = popcount32(D[:, 4]).astype(np.float32)
            Y = 2.0 * D_bits.astype(np.float32) - 1.0
            YM = Y @ M_in.astype(np.float32)
            Q = (Y * YM).sum(axis=1)
            tr_val = float(np.trace(M_in))
            score = (Q - tr_val) / 2
            all_scores.append(score)
            all_hw.append(hw_e)
            # per-block correlation
            bc = float(np.corrcoef(score, hw_e)[0, 1])
            block_corrs.append(bc)

        scores = np.concatenate(all_scores)
        hw_test = np.concatenate(all_hw)
        N_te = len(scores)

        # Global correlation
        corr = float(np.corrcoef(scores, hw_test)[0, 1])
        z = corr * math.sqrt(N_te - 2)
        std_corr = 1.0 / math.sqrt(N_te - 2)

        # Block sign analysis
        block_corrs = np.asarray(block_corrs)
        n_pos = int((block_corrs > 0).sum())
        n_blocks = len(block_corrs)
        sign_frac = n_pos / n_blocks

        from scipy.stats import binomtest
        sign_p = binomtest(n_pos, n_blocks, 0.5, alternative='greater').pvalue

        print(f"  Test: {N_te} pairs")
        print(f"  Global corr = {corr:+.8f}  z = {z:+.2f}")
        print(f"  Block corrs ({n_blocks} blocks): {n_pos}/{n_blocks} positive "
              f"({sign_frac:.1%})  sign-test p = {sign_p:.4f}")
        print(f"  Block corr mean = {block_corrs.mean():+.6f}  std = {block_corrs.std():.6f}")
        print(f"  Time: {time.time()-t_r:.0f}s")

    print(f"\nTotal: {time.time()-t_total:.0f}s")

if __name__ == '__main__':
    main()
