"""IT-15: additive-character Fourier probe (Z/2^32 instead of GF(2)).

Walsh sees XOR-structure (GF(2) characters). Misses carry. Additive
character probe over Z/2^32 sees carry-structure directly.

For each of 8 hash output words W ∈ Z/2^32, scan modular reductions:
  k ∈ {2, 4, 8, 16, 256, 4096, 2^16}
  Compute distribution of (W mod 2^k) over HW=2 inputs (N=130816).
  chi² test vs uniform on 2^k bins.

If for some k the chi² >> df → carry-aware non-uniformity.
Under RO: chi² ~ N(df, 2*df). z = (chi² - df) / sqrt(2*df).
Under SHA-2: any k with z > 5 = real carry-bias.

Also: 2-adic valuation v_2(W) per word, distribution test.

Compares to IT-1.3 chi²-truncation finding (k=12, z=-2.5 for SHA-256, p=10^-7).
"""
import json, math, os, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'it15_additive.json')

def low_hw2():
    inputs = []
    for p in combinations(range(512), 2):
        b = bytearray(64)
        for q in p: b[q >> 3] |= 1 << (q & 7)
        inputs.append(bytes(b))
    return inputs

def chi2_z(counts, expected):
    """chi² statistic and z-score (vs N(df, 2*df) under H0)."""
    chi2 = float(((counts - expected)**2 / expected).sum())
    df = len(counts) - 1
    z = (chi2 - df) / math.sqrt(2 * df)
    return chi2, df, z

def main():
    t0 = time.time()
    inputs = low_hw2(); N = len(inputs)
    print(f"# IT-15: additive Fourier mod 2^k on N={N} HW=2 inputs")

    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    b2 = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    b2 = np.broadcast_to(b2, (N, 16))
    s2 = ch.compress(s1, b2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    H_words = np.asarray(s2, dtype=np.uint64)  # shape (N, 8)
    print(f"# computed full hash words")

    K_LIST = [1, 2, 4, 8, 12, 16, 20]  # mod 2^k bins, up to 2^20 = 1M bins (need N>>1M for chi² so cap at k=14)
    K_LIST = [k for k in K_LIST if (1 << k) <= N // 5]  # need ≥5 expected per bin
    print(f"# K values: {K_LIST}")

    print("\n=== chi² on (H_word mod 2^k) ===")
    print(f"{'word':<6} " + ' '.join(f"k={k:<2}".ljust(13) for k in K_LIST))
    results = {}
    for w in range(8):
        word_data = H_words[:, w]
        row = f"H[{w}]   "
        rdict = {}
        for k in K_LIST:
            mod = word_data & ((1 << k) - 1)
            counts = np.bincount(mod, minlength=(1 << k)).astype(float)
            expected = N / (1 << k)
            chi2, df, z = chi2_z(counts, expected)
            row += f"z={z:+5.2f}     "
            rdict[k] = {'chi2': chi2, 'df': df, 'z': z}
        print(row)
        results[f'H{w}'] = rdict

    # 2-adic valuation: v_2(H[w]) = position of lowest set bit, ∞ if zero.
    # Under uniform: P(v_2 = i) = 2^(-i-1) for i >= 0.
    print("\n=== 2-adic valuation v_2(H[w]) distribution ===")
    print(f"{'word':<6} {'i=0':>7} {'i=1':>7} {'i=2':>7} {'i=3':>7} {'i=4':>7} {'i=5':>7} {'i=6+':>7} {'chi²-z':>8}")
    val_results = {}
    for w in range(8):
        word_data = H_words[:, w]
        # Compute v_2 for each
        v2 = np.zeros(N, dtype=np.int64)
        rem = word_data.copy()
        for i in range(32):
            mask = (rem & 1) == 1
            v2[mask & (v2 == 0)] = i  # not quite right for 0; fix below
        # Simpler: count trailing zeros
        v2 = np.zeros(N, dtype=np.int64)
        for j in range(N):
            x = int(word_data[j])
            v2[j] = (x & -x).bit_length() - 1 if x != 0 else 32
        bins = [int((v2 == i).sum()) for i in range(7)]
        bins.append(int((v2 >= 6).sum()))  # tail
        # Expected probabilities
        expected_p = [2**(-i-1) for i in range(6)] + [2**(-6)]  # P(v >= 6) = 2^(-6)
        expected = np.array([N * p for p in expected_p])
        observed = np.array(bins[:7])
        chi2 = float(((observed - expected)**2 / expected).sum())
        df = 6
        z = (chi2 - df) / math.sqrt(2 * df)
        print(f"H[{w}]   " + ' '.join(f"{b:>7}" for b in bins) + f"  {z:>+8.2f}")
        val_results[f'H{w}'] = {'bins': bins, 'chi2': chi2, 'z': z}

    # Analytic Fourier: |E[exp(2πi · k · H[w] / 2^32)]| for k ∈ {1, 2, 4, ..., 2^15}
    print("\n=== |E[ω^(k·H[w])]| analytic Fourier (k = 2^j) ===")
    print(f"# Under RO: |E| ≈ 1/sqrt(N) = {1/math.sqrt(N):.5f}, 5σ threshold ≈ {5/math.sqrt(N):.5f}")
    print(f"{'word':<6}", end=' ')
    K_FOURIER = [1, 2, 4, 16, 256, 4096, 65536]
    for k in K_FOURIER: print(f"k={k:<6}", end='  ')
    print()
    fourier_results = {}
    for w in range(8):
        word_data = H_words[:, w]
        row = f"H[{w}]   "
        wdict = {}
        for k in K_FOURIER:
            angles = 2 * np.pi * (k * word_data.astype(np.int64) % (1 << 32)) / (1 << 32)
            mean_re = float(np.cos(angles).mean())
            mean_im = float(np.sin(angles).mean())
            mag = math.sqrt(mean_re**2 + mean_im**2)
            z = mag * math.sqrt(N)  # rough
            row += f"{mag:.5f}({z:+4.1f}) "
            wdict[k] = {'mag': mag, 'z': z}
        print(row)
        fourier_results[f'H{w}'] = wdict

    print("\n--- INTERPRETATION ---")
    print("RO baseline: chi²-z ≈ 0, |E[ω^(kH)]|·√N ≈ 1 (expected gaussian).")
    print("|z| > 5: real bias in this carry-aware projection (probe sees what XOR can't).")
    print("Pattern across (w, k): if specific words/moduli show consistent z → carry-structure.")
    print("This complements IT-1.3 (k=12 chi² gave z=-2.5 for SHA-2 family).")

    final = {'meta': {'N': N, 'feature': 'HW=2 exhaustive'},
             'mod_chi2': results, 'twoadic': val_results, 'fourier': fourier_results}
    with open(OUT, 'w') as f: json.dump(final, f, indent=2)
    print(f"\nWrote {OUT}, total {time.time()-t0:.0f}s")

if __name__ == '__main__': main()
