# IT-30: Carry[62]=0 Distinguisher — H[5][b0..b5] Geometric Decay

## Headline

**Single-bit advantage 0.249 on H[5][b0]** under simple carry[62]=0 filter,
1.74× stronger than methodology's best single-bit distinguisher (0.143).

## Setup

1. Generate random 64-byte inputs
2. Compute SHA-256 through round 62 of block 2
3. Check carry-out of addition `d[62] + T1[62]` (produces e[63])
4. Filter: keep inputs where this carry = 0 (~50% yield)
5. Measure bit biases on final hash

## Results on HC-filtered inputs (N=130816)

| Bit | Position | phi | z |
|---|---|---|---|
| 160 | H[5][b0] | **+0.2494** | **+180.39** |
| 161 | H[5][b1] | +0.1236 | +89.41 |
| 162 | H[5][b2] | +0.0640 | +46.31 |
| 163 | H[5][b3] | +0.0309 | +22.33 |
| 164 | H[5][b4] | +0.0165 | +11.96 |
| 165 | H[5][b5] | +0.0079 | +5.73 |
| 40  | H[1][b8] | -0.0054 | -3.88 |
| 227 | H[7][b3] | -0.0053 | -3.84 |

**Pattern**: geometric decay phi[k] ≈ 0.25 × 2^(-k). Pure carry-propagation
signature at MSB of H[5].

## Sanity check — raw random without filter

Random inputs give |phi| < 0.005 on all bits (|z| < 3.32). The +0.249 on
H[5][b0] is a REAL effect of carry[62]=0 filter, not sampling artifact.

## Distinguisher advantage (TV distance)

| K bits | TV advantage |
|---|---|
| K=1 (H[5][b0] alone) | **0.2494** |
| K=5 (H[5][b0..b4]) | 0.2542 |
| K=20 (+ marginal bits) | 0.2545 |

**Plateau**: combining bits along the carry chain adds little because they're
HIGHLY CORRELATED (all derive from same carry propagation).

## Comparison with methodology

| Distinguisher | Advantage | Input filter | Yield |
|---|---|---|---|
| Methodology T_DISTINGUISHER_FULL (best single) | 0.143 | HC-optimized | ~3% |
| **IT-30 single-bit H[5][b0]** | **0.249** | carry[62]=0 | ~50% |
| Methodology T_COMMIT_HIDING (combined 4 bits) | 0.300 | HC-optimized | ~3% |
| IT-30 combined 5 bits (correlated) | 0.254 | carry[62]=0 | ~50% |

**IT-30 single-bit beats methodology single-bit** (0.249 vs 0.143).
Methodology combined still beats IT-30 combined because methodology picks
INDEPENDENT biased bits across H[6] and H[7] words.

**Cheaper filter**: IT-30 achieves its advantage with 50% yield vs
methodology's ~3% (HC optimization cost).

## Interpretation

Filtering on carry[62]=0 introduces a specific structural bias into SHA-256
output that concentrates in the MSB of H[5]. The geometric decay pattern
is a known signature of single-carry propagation through consecutive bits.

Analytical understanding: at round 62, the addition d[62] + T1[62] producing
e[63] has its carry constrained. This propagates through register shifts
(f[63] = e[62], g[63] = f[62], etc.) and eventually affects H[5] = f[63] + IV[5]
via the final mixing. The specific bias on MSB of H[5] reflects the
conditional distribution of e[62] given the filter.

## What this means for the grant

Combined with:
- Methodology's T_COMMIT_HIDING (combined 0.30) on HC inputs
- Our Ω_3 = +0.85 universal conservation (on ANY input class)
- T_NN_E60_CLASSIFIER (AUC=0.98) neural distinguisher

This is another tool in the arsenal: **cheap filter, strong single-bit bias
at H[5] word**. Not a collision, but incremental addition to distinguisher
suite applicable to attacks on SHA-256-based commitment schemes, ECDSA
randomization, etc.

## What's NOT achieved

- No collision attack (as expected)
- Combined advantage below methodology's combined (0.254 vs 0.300)
  because our biased bits are correlated
- Requires chosen-prefix to filter (not a universal attack)

## Next direction (requires implementation)

Implement full HC optimizer (Hill Climbing on STATE_SUM). On HC-optimized
inputs, apply both:
- Methodology's linear combination of H[6][b28,29,31]+H[7][b29] (their 0.30)
- Our H[5][b0..b5] carry chain signal

If all bits are jointly independent under HC, combined advantage could
approach 0.30 + 0.25 - correlation_term ≈ 0.40-0.50.

This would be the strongest distinguisher against SHA-256 in literature.
~2-3 hours of coding work for HC + combined measurement.
