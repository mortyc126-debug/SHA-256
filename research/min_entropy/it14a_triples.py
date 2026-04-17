"""IT-14a: top-triple aggregator across multiple output bits.

For each top-K output bit (by |direct_z|), get top-50 (a,b,c) state1 triples
from chain3 binary. Aggregate which state1 bit indices appear most often
in top triples — these are the 'hot bits' that carry the Walsh-3 signal.

If hot bits cluster on specific positions (within a state1 word, or following
sigma rotation pattern) → structural lever for attack construction.
"""
import json, math, os, subprocess, tempfile, time
from itertools import combinations
from collections import Counter
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'it4_q7d_chain3')
OUT = os.path.join(HERE, 'it14a_triples.json')

N_OUT_BITS = 16  # top 16 output bits

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

def runc(N, s1b, fa, tb, p):
    with open(p, 'wb') as fp:
        fp.write(np.uint64(N).tobytes())
        for b in range(256): fp.write(pack(s1b[:, b]).tobytes())
        fp.write(pack(fa).tobytes()); fp.write(pack(tb).tobytes())
    return json.loads(subprocess.run([C_BIN, p], capture_output=True, text=True, check=True).stdout)

def main():
    t0 = time.time()
    inputs, pos = low_hw2(); N = len(inputs)
    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    b2 = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    b2 = np.broadcast_to(b2, (N, 16))
    s2 = ch.compress(s1, b2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    s1b, s2b = sb(s1, N), sb(s2, N)

    mp = np.asarray([p[-1] for p in pos])
    fa = ((mp >> 5) & 1).astype(np.uint8)
    direct = np.array([(1 - 2*((fa^s2b[:,b]).sum())/N) * math.sqrt(N) for b in range(256)])
    top_bits = np.argsort(-np.abs(direct))[:N_OUT_BITS].tolist()
    print(f"# Top {N_OUT_BITS} output bits: {top_bits}")

    bit_counter = Counter()  # state1 bit index → count of appearances in top-50 triples
    pair_counter = Counter() # (state1_bit_a, state1_bit_b) → count
    by_bit = {}

    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tt: tp = tt.name
    try:
        for ob in top_bits:
            tb = s2b[:, ob]
            r = runc(N, s1b, fa, tb, tp)
            triples = r['top_k']
            by_bit[ob] = {'direct_z': float(direct[ob]), 'chain_sum': r['chain_sum'],
                          'best': triples[0], 'top10': triples[:10]}
            for t in triples:
                a, bb, c = t['a'], t['b'], t['c']
                bit_counter[a] += 1; bit_counter[bb] += 1; bit_counter[c] += 1
                pair_counter[tuple(sorted([a, bb]))] += 1
                pair_counter[tuple(sorted([a, c]))] += 1
                pair_counter[tuple(sorted([bb, c]))] += 1
            print(f"  bit {ob:>3}: chain={r['chain_sum']:+.1f}, best=({triples[0]['a']},{triples[0]['b']},{triples[0]['c']}) prod={triples[0]['prod']:+.2f}")
    finally:
        os.unlink(tp)

    # Aggregation: which state1 bits appear most?
    print("\n## Top-30 'hot' state1 bits across all output bits' top-50 triples:")
    for bit, cnt in bit_counter.most_common(30):
        word = bit // 32; offset = 31 - (bit % 32)  # MSB-first
        print(f"  state1 bit {bit:>3} (word {word}, MSB-offset {offset:>2}): appears {cnt} times")

    # Word-distribution
    word_counter = Counter()
    for bit, cnt in bit_counter.items():
        word_counter[bit // 32] += cnt
    print("\n## Bit appearance by state1 register word (a,b,c,d,e,f,g,h):")
    names = ['a','b','c','d','e','f','g','h']
    total = sum(word_counter.values())
    for w in range(8):
        c = word_counter.get(w, 0)
        print(f"  word {names[w]} (bits {w*32}-{w*32+31}): {c} appearances ({100*c/total:.1f}%)")

    # Pair structure
    print("\n## Top-15 'hot' state1 bit-pairs:")
    for p, cnt in pair_counter.most_common(15):
        print(f"  ({p[0]:>3}, {p[1]:>3}): {cnt} (Δ={abs(p[0]-p[1])})")

    out = {'top_bits': top_bits, 'by_bit': by_bit,
           'bit_counter': dict(bit_counter), 'pair_counter': {f"{p[0]},{p[1]}":c for p,c in pair_counter.items()},
           'word_counter': {names[w]: word_counter.get(w,0) for w in range(8)}}
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}, total {time.time()-t0:.0f}s")

if __name__ == '__main__': main()
