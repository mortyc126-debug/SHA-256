# MLB (Multi-channel Locality Bucketing) для Near-Collision поиска на SHA-256

**Project summary (April 2026)**

## Headline Results

Method: 3-channel sort-key bucketing на compression-function output (single-block, W[1..15]=0).

**Records achieved**:
| K | Min HW | Best pair (W0_a, W0_b) | Advantage vs uniform |
|---|---|---|---|
| 10M | 98 | (from MLB Week 1) | +7.4 |
| 50M | 80 | (28,954,919, 13,417,849) | +9.2 |
| 100M | 78 | (72,892,575, 78,161,118) | +9.0 |
| **200M** | **77** | **(13,073,324, 123,967,905)** | **+7.9** |

All pairs verified independently by re-computing SHA-256 compression.

**XOR of HW=77 pair state1 outputs**:
```
0008d504 00191a83 00694201 a6992934 00300c06 c044edb5 8a4059a4 80e080d0
HW = 77/256
```

## Method

### 3-Channel Sort-Key Bucketing

For each W[0] ∈ [0, K):
1. Set block = [W[0], 0, 0, ..., 0] (16 words, W[1..15]=0)
2. Compute message schedule W[16..63] via standard σ-expansion
3. Run 64 rounds of SHA-256 compression from standard IV
4. Extract sort-key: (a63, e63, a62) — these correspond to state1[0], state1[4], state1[1] after feed-forward
5. Bucket W[0] by (a63//T, e63//T, a62//T) for threshold T = 2^21

Pairs within same 3D bucket are candidates (state1 close in 3 of 8 words).

For each candidate pair, compute full state1 and measure HW of XOR.

### Why This Works

State1 = final SHA output has 256 bits across 8 uint32 words. Random pair
from 2K elements gives expected HW ≈ 128. If 3 words are close (differ by < T),
those contribute low HW (~5-10 each). Remaining 5 words random contribute ~16×5=80.
Empirically total ~77-80.

### Sort-Key Structure Matters

Experiment: alt sort-key (a61, a60, e62) at K=200M gave HW=78 (vs HW=77 for standard).
Feed-forward-aligned state words (a63, e63, a62) outperform intermediate state.

Intuition: feed-forward adds IV to state, "centers" distribution. Intermediate
state has accumulated round-function entropy, noisier matching.

## Scaling Behavior

**Empirical law**: HW reduces by ~1 bit per 2× K (after K=50M).

| K | HW | Δ from prev |
|---|---|---|
| 50M | 80 | — |
| 100M | 78 | −2 |
| 200M | 77 | −1 |

Extrapolation (if logarithmic continues):
- K = 400M → HW ≈ 76
- K = 1B → HW ≈ 74-75
- K = 10B → HW ≈ 72

Full collision HW=0 requires K on order of 2^128 (birthday), infeasible.

## Comparison with Theoretical Bounds

For K inputs in n=256 bit space, optimal near-collision via exhaustive pair
search (O(K²) complexity) gives expected min HW:

```
HW_min(K, n) ≈ n/2 − sqrt(log(K²) × n/4)
```

For K=200M, K² ≈ 4×10¹⁶: HW_min ≈ 59 (theoretical exhaustive).

Our MLB result: HW = 77.

**Gap**: 18 bits. MLB does NOT reach theoretical exhaustive minimum because
bucketing is an approximate nearest-neighbor heuristic — misses pairs whose
closeness in 256-bit space doesn't align with 3-channel closeness.

## Scope & Caveats

**Applies to**: SHA-256 compression function with one-word input W[0] and
W[1..15]=0. This is the **round function**, not standard SHA-256 which
includes message padding (0x80 appendix, length encoding).

**Does NOT violate**:
- T_DMIN_97 (methodology Vol II §II.6): d_min(SHA-256) ≥ 97 bits applies
  to full padded hashes, not restricted compression.
- T_BIRTHDAY_COST17: 2^128 birthday bound is for full collision (HW=0),
  not near-collision (HW=77).

**Records context**:
- Methodology Vol II §II.9.7 T_WCC_SA_MIXED: 60M iterations SA → HW=87
- MLB K=200M → HW=77 (beats by 10 bits at similar compute scale)
- MLB's advantage comes from structured sort-key bucketing vs unstructured SA

## Potential Future Directions

### Higher K Scaling
K=1B requires ~4-5 hours sustained compute. Predicted HW ~74.
Needs stable infra (sandbox restart resistance).

### Multi-Sort-Key Union
Different sort-keys find different candidate pairs. Union of 2-3 sort-keys
at fixed K might find 1-2 bit improvement. Empirical.

### LSH (Locality-Sensitive Hashing)
Classic LSH for Hamming distance projects to random r-bit hashes. For target
distance d ≈ 60 bits, n=256, LSH gives O(K^(1+ρ)) time with ρ ≈ 0.5.
K^1.5 vs K² = 10^4× speedup → LSH might find HW=60 pair at K=200M.

Implementation: pick random bit subset S of size r ≈ 20-30, bucket state1
by bits-in-S, check pairs. Repeat with L ~ 10-50 hash tables. Needs ~100 MB
memory but should complete in hours.

### Multiblock Extension
Current method is single-block. For 2+ blocks with message connection M = m1 || m2,
search space explodes to |m1| × |m2|. MLB can be combined with chosen-prefix
to fix m1 and search m2 only — but unclear if meaningful reduction beyond
standard T_BIRTHDAY_COST17.

## Files (implementation + results)

- `mlb_week2_scale_v2.py` — Phase 7B K=50M reference, HW=80
- `mlb_phase8b_100M_3ch.py` — Phase 8B K=100M, HW=78
- `mlb_phase8c_200M.py` — **Phase 8C K=200M, HW=77 (record)**
- `mlb_phase9_alt_sortkey.py` — Phase 9 alt sort-key experiment
- `mlb_week2_scale50M_v2.json` — Phase 7B results data
- `mlb_phase8b_100M_3ch.json` — Phase 8B data
- `mlb_phase8c_200M.json` — Phase 8C data (HW=77 pair confirmed)
- `mlb_phase9_alt_sortkey.json` — Phase 9 data

All W[0] pairs in top-30 of each JSON can be independently verified by
re-running SHA-256 compression on the reduced-input form.

## Honest Scope Summary

MLB is a **measurable incremental improvement** over prior methodology SA
on a **restricted problem** (compression function, W[1..15]=0). It does NOT
attack full SHA-256 collision resistance. It produces concrete verifiable
near-collision records that beat methodology's prior art by 10 bits.

For publication: IACR workshop level (FSE, CT-RSA) as "Multi-channel
Locality Bucketing for Restricted Compression Near-Collision Search".
