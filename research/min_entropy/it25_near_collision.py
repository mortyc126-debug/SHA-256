"""IT-25: Near-collision search using Omega_3 top-triples as constraints.

From IT-14a: for each output bit b, chain3 gives top-50 triples (a1,a2,a3)
of state1 bit indices, ordered by |z_in × z_out|.

These are the MOST INFORMATIVE state1 3-bit combinations about output bit b.
If χ_{a1,a2,a3}(Δstate1) = 0 for a "positive prod" triple, it predicts
that Δstate2[b] is BIASED toward 0 (with probability > 50%).

Strategy:
  1. For each output bit b, get top-K triples from chain3 (K=20).
  2. For pair (m_A, m_B): compute Δstate1, then score:
      score = Σ_{all (b, triple)} I[χ_triple(Δstate1) = 0] · |prod|
  3. Search random pair space for high-score pairs → expected low HW(Δhash).

Expected: random pair → HW(Δhash) ≈ 128. Top-scored → HW(Δhash) < 128.
Actual reduction gives us measurable attack primitive.
"""
import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'it4_q7d_chain3')


def low_hw2():
    inputs, pos = [], []
    for p in combinations(range(512), 2):
        b = bytearray(64)
        for q in p: b[q >> 3] |= 1 << (q & 7)
        inputs.append(bytes(b)); pos.append(p)
    return inputs, pos


def sb(s, N):
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w*32+b] = ((s[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits


def pack(v):
    pd = np.zeros(WORDS*64, dtype=np.uint8); pd[:len(v)] = v
    return np.frombuffer(np.packbits(pd, bitorder='little').tobytes(), dtype=np.uint64)


def full_sha(inputs):
    N = len(inputs)
    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    b2 = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    b2 = np.broadcast_to(b2, (N, 16))
    s2 = ch.compress(s1, b2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return s1, s2


def gather_top_triples(state1_bits, state2_bits, fa, top_k=20):
    """For each output bit b, call chain3 C binary and extract top-K triples."""
    all_triples = []  # list of (bit, a1, a2, a3, prod)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf: tp = tf.name
    try:
        for ob in range(256):
            t_b = state2_bits[:, ob]
            with open(tp, 'wb') as fp:
                fp.write(np.uint64(len(fa)).tobytes())
                for b in range(256): fp.write(pack(state1_bits[:, b]).tobytes())
                fp.write(pack(fa).tobytes()); fp.write(pack(t_b).tobytes())
            res = json.loads(subprocess.run([C_BIN, tp], capture_output=True, text=True, check=True).stdout)
            for t in res['top_k'][:top_k]:
                all_triples.append((ob, t['a'], t['b'], t['c'], t['prod']))
            if ob % 32 == 31:
                print(f"  collected top-{top_k} triples for {ob+1}/256 output bits", flush=True)
    finally:
        os.unlink(tp)
    return all_triples


def score_pair(m_A, m_B, triples):
    """Compute score for a pair using top-triples constraint satisfaction."""
    s1_A, _ = full_sha([m_A])
    s1_B, _ = full_sha([m_B])
    s1_A_bits = sb(s1_A, 1)[0]
    s1_B_bits = sb(s1_B, 1)[0]
    delta = s1_A_bits ^ s1_B_bits
    score = 0.0
    # For each triple: χ_{a1,a2,a3}(delta) = delta[a1] XOR delta[a2] XOR delta[a3]
    # If 0 (same parity) → constraint satisfied → add |prod| weighted
    for b, a1, a2, a3, prod in triples:
        chi = delta[a1] ^ delta[a2] ^ delta[a3]
        if prod > 0 and chi == 0:    # positive prod wants χ=0
            score += abs(prod)
        elif prod < 0 and chi == 1:  # negative prod wants χ=1
            score += abs(prod)
    return score


def main():
    t0 = time.time()
    print(f"# IT-25: Near-collision search via Omega_3 top-triples")
    inputs, pos = low_hw2(); N = len(inputs)
    mp = np.asarray([p[-1] for p in pos]); fa = ((mp >> 5) & 1).astype(np.uint8)
    s1, s2 = full_sha(inputs)
    s1b, s2b = sb(s1, N), sb(s2, N)

    # Step 1: collect top-20 triples for each of 256 output bits (~11 min)
    # OR load from existing IT-14a JSON if matches (only top-16 bits saved there)
    # Skip if exists
    triples_path = os.path.join(HERE, 'it25_top_triples.json')
    if os.path.exists(triples_path):
        print(f"# Loading cached triples from {triples_path}")
        triples = json.load(open(triples_path))
        # Format fixup
        triples = [(t[0], t[1], t[2], t[3], t[4]) for t in triples]
    else:
        print(f"# Collecting top-20 triples for all 256 output bits...")
        triples = gather_top_triples(s1b, s2b, fa, top_k=20)
        json.dump([[t[0], t[1], t[2], t[3], t[4]] for t in triples], open(triples_path, 'w'))
        print(f"# Saved {len(triples)} triples to {triples_path}")
    print(f"# Total constraints: {len(triples)}")

    # Step 2: score 2000 random pairs, find top-scoring ones
    import random as rnd
    rng = rnd.Random(0xDEADBEEF)
    print("\n# Scoring 2000 random pairs...")
    pair_scores = []
    for i in range(2000):
        m_A = bytes([rng.randint(0, 255) for _ in range(64)])
        # small random difference (HW=1 to 8)
        hw_diff = rng.randint(1, 8)
        bits_to_flip = rng.sample(range(512), hw_diff)
        m_B_arr = bytearray(m_A)
        for b in bits_to_flip:
            m_B_arr[b >> 3] ^= 1 << (b & 7)
        m_B = bytes(m_B_arr)
        # Compute HW(Δhash) for ground truth
        hA = int.from_bytes(hashlib.sha256(m_A).digest(), 'big')
        hB = int.from_bytes(hashlib.sha256(m_B).digest(), 'big')
        hw_hash = bin(hA ^ hB).count('1')
        # Score
        score = score_pair(m_A, m_B, triples)
        pair_scores.append({'m_A': m_A.hex(), 'm_B': m_B.hex(),
                            'hw_diff_input': hw_diff, 'score': score, 'hw_hash': hw_hash})
        if (i+1) % 200 == 0:
            print(f"  {i+1}/2000 pairs scored", flush=True)

    # Step 3: analyze correlation score ↔ HW(Δhash)
    scores = np.array([p['score'] for p in pair_scores])
    hws = np.array([p['hw_hash'] for p in pair_scores])
    corr = float(np.corrcoef(scores, hws)[0, 1])
    print(f"\n## Correlation(score, HW(Δhash)) = {corr:+.4f}")
    print(f"  Expected under H0 (no signal): 0 ± 1/√2000 = ±0.022")
    print(f"  z-score: {corr * np.sqrt(2000-2):+.2f}")

    # Step 4: top-scored vs bottom-scored HW
    idx = np.argsort(scores)
    bottom10 = hws[idx[:200]]  # lowest score
    top10 = hws[idx[-200:]]    # highest score
    print(f"\n## HW(Δhash) stats:")
    print(f"  All 2000 pairs:   mean={hws.mean():.2f} std={hws.std():.2f}")
    print(f"  Bottom 10% score: mean={bottom10.mean():.2f} std={bottom10.std():.2f} min={bottom10.min()}")
    print(f"  Top 10% score:    mean={top10.mean():.2f} std={top10.std():.2f} min={top10.min()}")
    print(f"  Signal: {top10.mean() - bottom10.mean():+.2f} bits difference in HW(Δhash)")

    # Step 5: find lowest HW(Δhash) in dataset (best near-collision)
    best_idx = np.argmin(hws)
    best = pair_scores[best_idx]
    print(f"\n## Best near-collision found:")
    print(f"  HW(Δhash) = {best['hw_hash']}")
    print(f"  HW(Δinput) = {best['hw_diff_input']}")
    print(f"  m_A = {best['m_A'][:32]}...")
    print(f"  m_B = {best['m_B'][:32]}...")
    print(f"  score rank = {np.where(idx == best_idx)[0][0]+1}/2000")

    with open(os.path.join(HERE, 'it25_pairs.json'), 'w') as f:
        json.dump(pair_scores, f)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
