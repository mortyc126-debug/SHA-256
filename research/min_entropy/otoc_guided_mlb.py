"""OTOC-guided MLB: use OTOC column scores to pick best sort-key positions.

At reduced round r=16, SHA-256 is partially scrambled. OTOC matrix
C[i, j, r=16] reveals which state positions carry MOST input information.

Method:
1. Compute OTOC C for r=16 (512×256 matrix)
2. Per state word (8 words × 32 bits), compute column sum scores
3. Rank words by score — top 3 = OTOC-guided sort-key
4. Run MLB at K=50M with OTOC sort-key vs baseline (a16, e16, b16)
5. Compare minimum HW

If OTOC-guided MLB finds lower HW → validated attack design principle.
If similar HW → OTOC doesn't give MLB advantage, but framework still valid.
"""
import json, os, time
import numpy as np

import sha256_chimera as ch


OUT = '/home/user/SHA-256/research/min_entropy/otoc_guided_mlb_results.json'


def state_at_r_batch(M_arr, r):
    N = M_arr.shape[0]
    W = np.empty((N, 64), dtype=np.uint32)
    W[:, :16] = M_arr
    for t in range(16, 64):
        if t > r + 16: break
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & ch.MASK
    iv = np.broadcast_to(np.array(ch.IV_VANILLA, dtype=np.uint32), (N, 8)).copy()
    a, b, c, d, e, f, g, h = (iv[:, i].copy() for i in range(8))
    K_vals = ch.K_VANILLA
    for t in range(r):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + np.uint32(K_vals[t]) + W[:, t]) & ch.MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & ch.MASK
        h = g; g = f; f = e
        e = (d + T1) & ch.MASK
        d = c; c = b; b = a
        a = (T1 + T2) & ch.MASK
    return np.column_stack([a, b, c, d, e, f, g, h]).astype(np.uint32)


def state_to_bits(state):
    """Convert (N, 8) uint32 → (N, 256) bits, MSB-first per word."""
    bytes_be = state.view('<u1').reshape(state.shape[0], 8, 4)[:, :, ::-1].reshape(state.shape[0], 32)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :256]


def compute_otoc_r16(N=200, seed=42):
    """OTOC matrix for state at r=16. Returns C ∈ R^(512×256)."""
    rng = np.random.default_rng(seed)
    base_msgs = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)
    state_base = state_at_r_batch(base_msgs, 16)
    bits_base = state_to_bits(state_base)

    C = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32; bit = 31 - (i % 32)
        flip_msgs = base_msgs.copy()
        flip_msgs[:, word] ^= np.uint32(1 << bit)
        state_flip = state_at_r_batch(flip_msgs, 16)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def rank_state_words_by_otoc(C):
    """For each of 8 state words, compute sum of |C|² over its 32 bits.
    Higher score = more structure preserved at r=16."""
    word_scores = np.zeros(8)
    for w in range(8):
        bit_range = slice(w*32, (w+1)*32)
        # Sum over all input bits (512) and output bits of word w
        word_scores[w] = np.sum(C[:, bit_range] ** 2)
    return word_scores


def run_mlb(key_selector, key_names, K, T, r=16):
    """Run MLB at round r using key_selector(state_r) returning 3-tuple of uint32 per sample.

    Returns (min_hw, n_pairs, best_pair).
    """
    print(f"  MLB with keys {key_names}, K={K:,}, T={T:,}", flush=True)
    # Phase 1: keys
    ts = time.time()
    all_k = [np.zeros(K, dtype=np.uint32) for _ in range(3)]
    BATCH = 500_000
    for start in range(0, K, BATCH):
        end = min(start + BATCH, K)
        M_batch = np.zeros((end-start, 16), dtype=np.uint32)
        M_batch[:, 0] = np.arange(start, end, dtype=np.uint32)
        state = state_at_r_batch(M_batch, r)
        keys = key_selector(state)
        for i in range(3): all_k[i][start:end] = keys[i]
    print(f"    keys: {time.time()-ts:.0f}s")

    # Phase 2: bucketing
    ts = time.time()
    k1b = (all_k[0].astype(np.uint64) // T)
    k2b = (all_k[1].astype(np.uint64) // T)
    k3b = (all_k[2].astype(np.uint64) // T)
    bkey = (k1b << 40) | (k2b << 20) | k3b
    sort_idx = np.argsort(bkey)
    sorted_keys = bkey[sort_idx]
    diff = sorted_keys[1:] != sorted_keys[:-1]
    cp = np.where(diff)[0] + 1
    rs_ = np.concatenate(([0], cp)); re_ = np.concatenate((cp, [K]))
    rl_ = re_ - rs_; mm = rl_ >= 2
    ms = rs_[mm]; me = re_[mm]; ml = rl_[mm]
    print(f"    buckets: {time.time()-ts:.0f}s, {len(ms):,} multi-buckets")

    # Phase 3: candidates
    ts = time.time()
    cands = []
    for rs__, re__, rl__ in zip(ms, me, ml):
        ids = sort_idx[rs__:re__]
        L = min(rl__, 12)
        for ii in range(L):
            for jj in range(ii+1, L):
                i, j = int(ids[ii]), int(ids[jj])
                if abs(int(all_k[0][i]) - int(all_k[0][j])) >= T: continue
                if abs(int(all_k[1][i]) - int(all_k[1][j])) >= T: continue
                if abs(int(all_k[2][i]) - int(all_k[2][j])) >= T: continue
                cands.append((i, j))
    print(f"    cands: {len(cands):,} ({time.time()-ts:.0f}s)")

    if not cands:
        return None, 0, None

    # Phase 4: recompute full state at r for candidates
    ts = time.time()
    unique = list(set(i for p in cands for i in p))
    states = {}
    BATCH = 50_000
    for bi in range(0, len(unique), BATCH):
        batch = unique[bi:bi+BATCH]
        M_arr = np.zeros((len(batch), 16), dtype=np.uint32)
        M_arr[:, 0] = np.array(batch, dtype=np.uint32)
        sb = state_at_r_batch(M_arr, r)
        for k, w0 in enumerate(batch): states[w0] = sb[k].copy()
    print(f"    states: {time.time()-ts:.0f}s")

    # Phase 5: HW
    ts = time.time()
    best_hw = None; best_pair = None
    for i, j in cands:
        sA, sB = states[i], states[j]
        hw = sum(bin(int(sA[w]) ^ int(sB[w])).count('1') for w in range(8))
        if best_hw is None or hw < best_hw:
            best_hw = hw; best_pair = (i, j)
    print(f"    HW: {time.time()-ts:.0f}s, min HW = {best_hw}")
    return best_hw, len(cands), best_pair


def main():
    t0 = time.time()
    print("# OTOC-guided MLB at reduced round r=16")

    # Step 1: compute OTOC at r=16
    print("\n## Computing OTOC matrix for r=16...")
    ts = time.time()
    C = compute_otoc_r16(N=200)
    print(f"  OTOC C shape: {C.shape}, ||C||_F² = {(C**2).sum():.2f} ({time.time()-ts:.0f}s)")

    # Step 2: rank words by OTOC score
    scores = rank_state_words_by_otoc(C)
    print(f"\n## State word OTOC scores at r=16:")
    word_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    ranked = sorted(enumerate(scores), key=lambda x: -x[1])
    for rank, (w, s) in enumerate(ranked):
        marker = " ←" if rank < 3 else ""
        print(f"  word {w} ({word_names[w]}16): score = {s:.2f}{marker}")

    top3_words = [w for w, _ in ranked[:3]]
    top3_names = [f"{word_names[w]}16" for w in top3_words]
    print(f"\n  OTOC top-3 words: {top3_names}")
    print(f"  Baseline:         ['a16', 'e16', 'b16']  (per current MLB convention)")

    # Step 3: run MLB with OTOC-guided keys vs baseline
    K = 20_000_000  # smaller for quick comparison
    T = 2_000_000

    print(f"\n## Running MLB at r=16, K={K:,}, T={T:,}")

    # Baseline keys
    print("\n### Baseline: (a16, e16, b16)")
    def baseline_selector(state):
        return (state[:, 0], state[:, 4], state[:, 1])
    bhw, bn, bpair = run_mlb(baseline_selector, ['a16', 'e16', 'b16'], K, T, r=16)

    # OTOC-guided keys
    print(f"\n### OTOC-guided: {top3_names}")
    def otoc_selector(state):
        return tuple(state[:, w] for w in top3_words)
    ohw, on, opair = run_mlb(otoc_selector, top3_names, K, T, r=16)

    # Compare
    print(f"\n## Comparison at r=16, K=20M:")
    print(f"  Baseline (a16,e16,b16):       HW={bhw}, pairs={bn}")
    print(f"  OTOC-guided ({','.join(top3_names)}): HW={ohw}, pairs={on}")

    if ohw is not None and bhw is not None:
        diff = bhw - ohw
        if diff > 0: print(f"  ★ OTOC wins: {diff} bit lower HW")
        elif diff < 0: print(f"  baseline wins: {-diff} bit lower HW")
        else: print(f"  tied")

    out = {
        'otoc_word_scores': {word_names[w]: float(scores[w]) for w in range(8)},
        'otoc_top3': top3_names,
        'baseline_result': {'min_hw': bhw, 'n_pairs': bn, 'pair': list(bpair) if bpair else None},
        'otoc_result': {'min_hw': ohw, 'n_pairs': on, 'pair': list(opair) if opair else None},
        'K': K, 'T': T, 'r': 16,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
