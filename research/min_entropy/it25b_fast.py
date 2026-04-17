"""IT-25b: FAST near-collision attack using IT-14a's cached triples.

Uses already-collected 800 triples (16 top output bits × 50 triples each)
from IT-14a. Scores random message pairs, looks for correlation between
Ω_3-constraint score and HW(Δhash).

If corr(score, HW) < 0 significantly: constraint satisfaction PREDICTS
low-HW pairs → attack primitive. If corr ≈ 0: Ω_3 doesn't translate.
"""
import hashlib, json, math, os, random, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# Load IT-14a top triples
it14a = json.load(open(os.path.join(HERE, 'it14a_triples.json')))
print(f"# IT-14a by_bit: {list(it14a['by_bit'].keys())[:5]}...")

# Extract all triples (top-10 per output bit)
triples = []
for ob_str, data in it14a['by_bit'].items():
    ob = int(ob_str)
    for t in data['top10']:
        triples.append((ob, t['a'], t['b'], t['c'], t['prod']))
print(f"# Total triples from IT-14a: {len(triples)} (16 bits × 10 triples)")

# Full SHA using hashlib for correctness
def sha_state1(m):
    """Block-1 state via manual compression (we need intermediate state for χ-test)."""
    import sha256_chimera as ch
    import numpy as np
    N = 1
    M = np.frombuffer(m, dtype=np.uint8).reshape(1, 64)
    b1 = M.view('>u4').reshape(1, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (1, 8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return s1[0]  # shape (8,)


def state_to_bits256(state):
    """256-bit vector from state (8 × uint32) — MSB-first per word."""
    bits = np.zeros(256, dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[w*32+b] = (int(state[w]) >> (31-b)) & 1
    return bits


def score_pair(m_A, m_B, triples):
    """Score pair by how many triple constraints satisfied."""
    s1_A = sha_state1(m_A); s1_B = sha_state1(m_B)
    bits_A = state_to_bits256(s1_A)
    bits_B = state_to_bits256(s1_B)
    delta = bits_A ^ bits_B
    score = 0.0
    for b, a1, a2, a3, prod in triples:
        chi = int(delta[a1]) ^ int(delta[a2]) ^ int(delta[a3])
        if prod > 0 and chi == 0:
            score += abs(prod)
        elif prod < 0 and chi == 1:
            score += abs(prod)
    return score


def main():
    t0 = time.time()
    print(f"\n# IT-25b: pair scoring with {len(triples)} Ω_3-constraints")

    rng = random.Random(0xCAFE)
    N_PAIRS = 5000
    results = []
    for i in range(N_PAIRS):
        # Random message
        m_A = bytes(rng.randint(0, 255) for _ in range(64))
        # Small diff (1-8 bit flips)
        hw_in = rng.randint(1, 8)
        diff_bits = rng.sample(range(512), hw_in)
        m_B_arr = bytearray(m_A)
        for b in diff_bits: m_B_arr[b >> 3] ^= 1 << (b & 7)
        m_B = bytes(m_B_arr)
        # Full hash via hashlib
        hA = int.from_bytes(hashlib.sha256(m_A).digest(), 'big')
        hB = int.from_bytes(hashlib.sha256(m_B).digest(), 'big')
        hw_hash = bin(hA ^ hB).count('1')
        # Score via Ω_3 constraints
        s = score_pair(m_A, m_B, triples)
        results.append({'score': s, 'hw_hash': hw_hash, 'hw_in': hw_in})
        if (i+1) % 500 == 0:
            el = time.time() - t0
            print(f"  {i+1}/{N_PAIRS} pairs ({el:.0f}s)", flush=True)

    scores = np.array([r['score'] for r in results])
    hws = np.array([r['hw_hash'] for r in results])
    corr = float(np.corrcoef(scores, hws)[0, 1])
    z = corr * np.sqrt(len(scores) - 2)

    print(f"\n## CORRELATION TEST")
    print(f"  corr(score, HW(Δhash)) = {corr:+.6f}")
    print(f"  z-score = {z:+.2f}")
    print(f"  p-value ≈ {2*math.erfc(abs(z)/math.sqrt(2))/2:.2e}")

    # Top and bottom score brackets
    idx = np.argsort(scores)
    bot = hws[idx[:500]]; top = hws[idx[-500:]]
    print(f"\n## HW(Δhash) by score bracket:")
    print(f"  All {N_PAIRS}:     mean={hws.mean():.2f} std={hws.std():.2f} min={hws.min()}")
    print(f"  Bottom 10%:      mean={bot.mean():.2f} std={bot.std():.2f} min={bot.min()}")
    print(f"  Top 10%:         mean={top.mean():.2f} std={top.std():.2f} min={top.min()}")
    print(f"  Signal: {top.mean() - bot.mean():+.2f} bits (< 0 = HIGH SCORE → LOW HW = ATTACK WORKS)")

    # Best near-collision
    best = np.argmin(hws)
    r = results[best]
    score_rank = int(np.where(idx == best)[0][0])
    print(f"\n## Best pair found:")
    print(f"  HW(Δhash) = {r['hw_hash']} (input HW={r['hw_in']})")
    print(f"  score rank = {score_rank+1}/{N_PAIRS}")
    # With ~10M random pairs we'd expect a HW≈90 pair by birthday

    # Also: top-scored pairs stats
    print(f"\n## Top-20 scored pairs HW stats:")
    top20 = sorted(results, key=lambda r: -r['score'])[:20]
    for r in top20[:5]:
        print(f"  score={r['score']:.1f}  HW(Δhash)={r['hw_hash']}")

    json.dump(results, open(os.path.join(HERE, 'it25b_results.json'), 'w'))
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
