"""OTOC-based differential cryptanalysis of SHA-256.

OTOC matrix C[i, j, r] = P(state[r][j] flips | input bit i flips) - 0.5
Equivalently: P(differential i → j at round r) = 0.5 + C[i, j, r]

Methodology's T_DOM_DIFF: δW[0][15] → δe1[15] with P=0.773
  → expected OTOC at r=1: C[bit_at_W0[15], bit_at_state[1].e[15]] ≈ 0.273

Tasks:
1. Verify methodology T_DOM_DIFF via OTOC at r=1
2. Find ALL best single-bit differentials at r=1, 2, 3
3. Compare to methodology's Wang-chain choices
4. Multi-round differential propagation via chaining
"""
import json, os, time
import numpy as np

import sha256_chimera as ch


OUT = '/home/user/SHA-256/research/min_entropy/otoc_differential_results.json'


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
    bytes_be = state.view('<u1').reshape(state.shape[0], 8, 4)[:, :, ::-1].reshape(state.shape[0], 32)
    return np.unpackbits(bytes_be, axis=1, bitorder='big')[:, :256]


def compute_otoc(r, N=2000, seed=42):
    """High-N OTOC for better differential probability estimate."""
    rng = np.random.default_rng(seed)
    base_msgs = rng.integers(0, 2**32, size=(N, 16), dtype=np.int64).astype(np.uint32)
    state_base = state_at_r_batch(base_msgs, r)
    bits_base = state_to_bits(state_base)
    C = np.zeros((512, 256), dtype=np.float64)
    for i in range(512):
        word = i // 32; bit = 31 - (i % 32)
        flip_msgs = base_msgs.copy()
        flip_msgs[:, word] ^= np.uint32(1 << bit)
        state_flip = state_at_r_batch(flip_msgs, r)
        bits_flip = state_to_bits(state_flip)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def bit_to_word_bit(idx, is_input=True):
    """Convert flat bit index to (word, bit_within_word) — MSB-first convention."""
    if is_input:
        word = idx // 32
        bit = 31 - (idx % 32)  # MSB-first
        return word, bit
    else:
        state_word_idx = idx // 32  # 0=a, 1=b, 2=c, 3=d, 4=e, 5=f, 6=g, 7=h
        bit = 31 - (idx % 32)
        reg_names = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        return reg_names[state_word_idx], bit


def main():
    t0 = time.time()
    print("# OTOC-based differential cryptanalysis of SHA-256")

    # Compute OTOC at multiple rounds
    rounds_to_analyze = [1, 2, 3, 4, 6, 8]
    otocs = {}
    for r in rounds_to_analyze:
        print(f"\n## Computing OTOC at r={r} (N=2000)...")
        ts = time.time()
        C = compute_otoc(r, N=2000)
        otocs[r] = C
        print(f"  {time.time()-ts:.0f}s, ||C||²={(C**2).sum():.0f}, max|C|={np.max(np.abs(C)):.4f}")

    # 1. Verify methodology T_DOM_DIFF at r=1
    print(f"\n## 1. Verify T_DOM_DIFF: δW[0][15] → δe1[15] with P=0.773")
    # W[0]-bit 15 = input bit index 0*32 + (31-15) = 16 (MSB-first of W[0][15]=bit position in word)
    # Wait, let me be careful:
    # methodology "δW[0][15]" usually means bit 15 of W[0] using bit-counting convention
    # bit 15 of uint32 = mask 0x8000, MSB-first notation: bit (31-15) = bit 16 in MSB-first
    # Our encoding: input bit i with word=i//32, bit=31-(i%32), so bit_in_word=15 means i%32 = 16.
    # So δW[0][15] corresponds to input index i = 0*32 + 16 = 16.
    # δe1[15] is bit 15 of state1[4]=e, so j = 4*32 + 16 = 144.
    input_i = 16
    output_j = 4*32 + 16  # e register (index 4), bit 15
    C1 = otocs[1]
    p_via_otoc = 0.5 + C1[input_i, output_j]
    print(f"  OTOC at r=1, (W[0] bit 15 → e1 bit 15): P = {p_via_otoc:.4f}")
    print(f"  Methodology T_DOM_DIFF: P = 0.773")
    print(f"  Match: {'✓' if abs(p_via_otoc - 0.773) < 0.01 else '⚠'}")

    # 2. Find all high-probability single-bit differentials at r=1
    print(f"\n## 2. TOP-10 single-bit differentials at r=1 (by |C|):")
    C1 = otocs[1]
    flat_idx = np.argsort(-np.abs(C1.flatten()))[:20]
    for idx in flat_idx[:20]:
        i, j = idx // 256, idx % 256
        iw, ib = bit_to_word_bit(i, True)
        jn, jb = bit_to_word_bit(j, False)
        p = 0.5 + C1[i, j]
        print(f"  δW[{iw}][{ib}] → δ{jn}1[{jb}]: P={p:.4f}, |C|={abs(C1[i,j]):.4f}")

    # 3. Multi-round differential: fix input diff δW[0][15], track over rounds
    print(f"\n## 3. Multi-round propagation: δW[0][15] through rounds 1..8")
    print(f"  {'r':>2}  {'top output (|C|)':>30}  {'P':>8}  {'2nd best':>30}")
    for r in rounds_to_analyze:
        Cr = otocs[r]
        row = Cr[input_i]  # 256 output bits for input_i = δW[0][15]
        abs_row = np.abs(row)
        top2 = np.argsort(-abs_row)[:2]
        best_j, snd_j = top2[0], top2[1]
        best_n, best_b = bit_to_word_bit(best_j, False)
        snd_n, snd_b = bit_to_word_bit(snd_j, False)
        p_best = 0.5 + row[best_j]
        p_snd = 0.5 + row[snd_j]
        print(f"  {r:>2}  δ{best_n}{r}[{best_b}] (|C|={abs(row[best_j]):.3f})  "
              f"P={p_best:.4f}  "
              f"δ{snd_n}{r}[{snd_b}] P={p_snd:.3f}")

    # 4. Average differential probability distribution at each round
    print(f"\n## 4. Differential quality decay (fraction of (i,j) pairs with |C| > threshold):")
    print(f"  {'r':>2}  {'|C|>0.4':>10}  {'|C|>0.3':>10}  {'|C|>0.2':>10}  {'|C|>0.1':>10}")
    for r in rounds_to_analyze:
        Cr = otocs[r]
        tot = Cr.size
        print(f"  {r:>2}  {np.sum(np.abs(Cr)>0.4)/tot*100:>9.2f}%  "
              f"{np.sum(np.abs(Cr)>0.3)/tot*100:>9.2f}%  "
              f"{np.sum(np.abs(Cr)>0.2)/tot*100:>9.2f}%  "
              f"{np.sum(np.abs(Cr)>0.1)/tot*100:>9.2f}%")

    # 5. Comparison with Wang-chain start: δW[0] such that δe1=0x8000 forms first Wang step
    # Methodology uses δW[0]=0x8000 → δe1=0x8000 as starting point
    # OTOC should confirm this is among the strongest r=1 paths involving W[0]
    print(f"\n## 5. Search best (W[0] bit → e1 bit) via OTOC:")
    best_w0_to_e1 = None; best_val = 0
    for i_w0 in range(32):
        i = 0*32 + (31 - i_w0)  # W[0] bit i_w0 in methodology notation
        for j_e1 in range(32):
            j = 4*32 + (31 - j_e1)  # e1 bit j_e1
            v = abs(otocs[1][i, j])
            if v > best_val:
                best_val = v; best_w0_to_e1 = (i_w0, j_e1)
    print(f"  Best: δW[0][{best_w0_to_e1[0]}] → δe1[{best_w0_to_e1[1]}]: P = {0.5 + abs(otocs[1][0*32+(31-best_w0_to_e1[0]), 4*32+(31-best_w0_to_e1[1])]):.4f}")
    print(f"  Methodology choice: δW[0][15] → δe1[15] with P=0.773")

    out = {
        'rounds_analyzed': rounds_to_analyze,
        'T_DOM_DIFF_verification': {
            'methodology_P': 0.773,
            'otoc_P': p_via_otoc,
            'match': bool(abs(p_via_otoc - 0.773) < 0.01),
        },
        'best_W0_to_e1_r1': {
            'bit_W0': best_w0_to_e1[0],
            'bit_e1': best_w0_to_e1[1],
            'probability': 0.5 + best_val,
        },
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
