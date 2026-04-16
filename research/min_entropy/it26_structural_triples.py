"""IT-26: Structural analysis of top-triples — are they aligned with SHA-2 rotation distances?

From IT-14a: top-50 triples per output bit, total ~800 triples.

Each triple (a, b, c) with a, b, c ∈ [0, 256) state1 bit indices.
Compute structural properties:

1. PAIRWISE BIT DISTANCES: for each triple, compute (|a-b|, |a-c|, |b-c|).
   Are these clustered near SHA-2 rotation amounts {2, 6, 11, 13, 17, 18, 19, 22, 25}?

2. WORD LOCALITY: bits within same 32-bit register vs across registers.
   Random expectation: P(within-word) ≈ 31/255.
   SHA-2 round operates on words → may favor within-word triples.

3. SHIFT-REGISTER ALIGNMENT: state has 8 registers as shift copies (b=a[-1], c=a[-2], etc.).
   Triples spanning 'related' registers may be over-represented.

4. POSITION-WITHIN-WORD: SHA-2 has rotations Σ0=(2,13,22), Σ1=(6,11,25), σ0=(7,18,3),
   σ1=(17,19,10). Are top triples concentrated at these rotation-related positions?

If ANY of these structural alignments shows up → we have the "alien antenna direction"
that SHA-2 round function exposes.
"""
import json, math, os
from collections import Counter, defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

# Load IT-14a triples
it14a = json.load(open(os.path.join(HERE, 'it14a_triples.json')))

# Extract all triples with their products (sign + magnitude)
triples = []
for ob_str, data in it14a['by_bit'].items():
    ob = int(ob_str)
    for t in data['top10']:
        triples.append((ob, t['a'], t['b'], t['c'], t['prod']))
print(f"Loaded {len(triples)} triples from IT-14a")

# State1 bit layout: bit 0..31 = register a, bit 32..63 = b, ... bit 224..255 = h
# Within a word: positions 0..31 (MSB to LSB in our convention)

def bit_to_word(b): return b // 32  # 0..7 (a=0, b=1, ..., h=7)
def bit_to_offset(b): return b % 32  # MSB-offset within word

REG_NAMES = list('abcdefgh')

print("\n=== Analysis 1: PAIRWISE BIT DISTANCES ===")
SHA2_ROTS = {2, 6, 11, 13, 17, 18, 19, 22, 25}
SHA2_ROTS_FULL = SHA2_ROTS | {32-r for r in SHA2_ROTS}  # mod 32 reflections
print(f"SHA-2 rotation amounts: {sorted(SHA2_ROTS)}")
print(f"With mod-32 reflections: {sorted(SHA2_ROTS_FULL)}")

distance_counts = Counter()
all_distances = []
for _, a, b, c, _ in triples:
    for x, y in [(a,b), (a,c), (b,c)]:
        d = abs(x - y)
        distance_counts[d] += 1
        all_distances.append(d)

print(f"\nTotal pairwise distances: {len(all_distances)}")
print("Top 20 most common distances:")
for d, cnt in distance_counts.most_common(20):
    flag = "★" if (d % 32) in SHA2_ROTS_FULL else " "
    print(f"  {flag} dist {d:>3}: {cnt:>4} ({100*cnt/len(all_distances):.2f}%)")

# Compare to uniform expectation: P(distance=d) for two random bits in [0,256)
# = (256-d)/(C(256,2)) for d≥1
print("\nObserved vs expected (uniform random) for SHA-2 rotation distances:")
total_pairs = len(all_distances)
for d in sorted(SHA2_ROTS):
    obs = distance_counts.get(d, 0)
    expected = (256 - d) / 32640 * total_pairs
    z = (obs - expected) / math.sqrt(expected * (1 - expected/total_pairs)) if expected > 1 else 0
    flag = "★" if abs(z) > 3 else " "
    print(f"  dist {d:>3}: obs={obs:>4} exp={expected:>5.1f} z={z:>+6.2f} {flag}")

print("\n=== Analysis 2: WORD LOCALITY ===")
# Within-word: all 3 bits in same word
# 2-of-3-same: 2 bits in same word
# All-different: 3 bits in 3 different words

within_word = 0
two_same = 0
all_diff = 0
for _, a, b, c, _ in triples:
    wa, wb, wc = bit_to_word(a), bit_to_word(b), bit_to_word(c)
    n_distinct = len(set([wa, wb, wc]))
    if n_distinct == 1: within_word += 1
    elif n_distinct == 2: two_same += 1
    else: all_diff += 1

n = len(triples)
# Random expectation: P(all in same word) = 8 × (32/256)^3 = 8/512 = 1.5%
# P(2 in same word) = 3 × 8 × (32/256)^2 × (224/256) = need full calc
# Simpler: count via combinatorics
import math as m
p_same = 8 * m.comb(32, 3) / m.comb(256, 3)  # all in 1 word
p_two = 8 * 7 * m.comb(32, 2) * 32 / m.comb(256, 3)  # 2 in word A, 1 in word B
p_all = 1 - p_same - p_two
print(f"Within-word triples (all 3 in same register): {within_word}/{n} ({100*within_word/n:.2f}%) "
      f"vs expected {100*p_same:.2f}%")
print(f"Two-of-three (2 in same word):                {two_same}/{n} ({100*two_same/n:.2f}%) "
      f"vs expected {100*p_two:.2f}%")
print(f"All-different words:                          {all_diff}/{n} ({100*all_diff/n:.2f}%) "
      f"vs expected {100*p_all:.2f}%")

# z for within-word
exp_count = p_same * n
z_within = (within_word - exp_count) / math.sqrt(exp_count * (1 - p_same)) if exp_count > 1 else 0
print(f"\nz-score within-word: {z_within:+.2f}")

print("\n=== Analysis 3: REGISTER PAIR FREQUENCY ===")
# Which (word, word, word) combinations are most common in top triples?
word_combos = Counter()
for _, a, b, c, _ in triples:
    wa, wb, wc = bit_to_word(a), bit_to_word(b), bit_to_word(c)
    key = tuple(sorted([wa, wb, wc]))
    word_combos[key] += 1

print("Top 10 word combinations (a-h registers):")
for combo, cnt in word_combos.most_common(10):
    name = '+'.join(REG_NAMES[w] for w in combo)
    expected = (n / m.comb(8+2, 3) * (3 if len(set(combo))==2 else 1 if len(set(combo))==1 else 6))  # rough
    print(f"  ({name}): {cnt} ({100*cnt/n:.1f}%)")

print("\n=== Analysis 4: WITHIN-WORD POSITION DISTRIBUTION ===")
# For within-word triples (or any triple), look at the bit-OFFSETS within word
# E.g., for triple (5, 10, 22), offsets are (5, 10, 22)
# Are these clustered at specific rotation positions?

within_offsets = []
for _, a, b, c, _ in triples:
    wa, wb, wc = bit_to_word(a), bit_to_word(b), bit_to_word(c)
    if wa == wb == wc:
        within_offsets.append(tuple(sorted([bit_to_offset(a), bit_to_offset(b), bit_to_offset(c)])))

print(f"Within-word triples: {len(within_offsets)}")
if within_offsets:
    offset_counter = Counter(within_offsets)
    print("Top 10 within-word position triples (offsets):")
    for off, cnt in offset_counter.most_common(10):
        # Check if offsets are SHA-2 rotation amounts
        offs = sorted(off)
        diffs = [offs[1]-offs[0], offs[2]-offs[1], offs[2]-offs[0]]
        flag = "★" if any(d in SHA2_ROTS_FULL for d in diffs) else " "
        print(f"  {flag} ({off[0]:>2}, {off[1]:>2}, {off[2]:>2}) diffs=({diffs[0]:>2},{diffs[1]:>2},{diffs[2]:>2}): {cnt}")

print("\n=== Analysis 5: SIGNED PROD distribution ===")
prods = [t[4] for t in triples]
prods_sorted = sorted(prods, key=abs, reverse=True)
print(f"Top 10 |prod|: {[f'{p:+.2f}' for p in prods_sorted[:10]]}")
print(f"Mean |prod|: {np.mean([abs(p) for p in prods]):.2f}")
print(f"Sign of top 50: {sum(1 for p in prods_sorted[:50] if p > 0)} positive of 50")

# Save analysis
with open(os.path.join(HERE, 'it26_structural.json'), 'w') as f:
    json.dump({
        'distance_top20': distance_counts.most_common(20),
        'sha2_rotations_check': {d: distance_counts.get(d, 0) for d in sorted(SHA2_ROTS)},
        'word_locality': {'within_word': within_word, 'two_same': two_same, 'all_diff': all_diff,
                          'expected_within_word': exp_count},
        'word_combo_top10': [(list(c), n) for c, n in word_combos.most_common(10)],
        'within_word_z': z_within,
    }, f, indent=2)
print("\n--- KEY INTERPRETATION ---")
print("If within-word z > 5: top triples cluster IN single registers → word-local structure.")
print("If specific rotation distances {2,6,11,13,17,18,19,22,25} dominate: rotation-aligned.")
print("Either of these = 'alien antenna direction' identified.")
