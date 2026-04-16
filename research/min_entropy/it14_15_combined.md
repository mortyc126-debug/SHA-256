# IT-14a + IT-15 Combined Results — "alien antenna" probes

## IT-14a: structural lever search (top-triple aggregation)

For top-16 output bits ranked by |direct_z|, extract top-50 (a,b,c) state1
triples from chain3 binary. Aggregate which state1 bits are "hot".

### Hot bit distribution
- Top single bit appearances: 17 (vs 9.4 uniform) — mild 1.8× overrepresentation
- Top bit-pair appearances: 3 (vs 0.07 uniform) — but only one pair at this level
- Word distribution: 11.3% to 13.5% across 8 state1 words (uniform = 12.5%)

### Verdict
**No structural concentration.** Hot bits are essentially uniformly distributed
across all 8 state1 register words. The Walsh-3 signal is **delocalized** —
every bit of state1 carries a piece, no bit carries a "key".

This means: Omega_3 = +0.98 is detectable as collective statistic but cannot
be exploited via localized constraint construction.

## IT-15: additive Fourier mod 2^k (carry-aware probe)

Tests whether SHA-256 hash is uniform under carry-aware projections that XOR-based
Walsh cannot see.

### Probes
1. chi² of (H[w] mod 2^k) for k ∈ {1, 2, 4, 8, 12}
2. 2-adic valuation v_2(H[w]) distribution
3. Analytic Fourier |E[ω^(k·H[w])]| for k ∈ {1, 2, 4, 16, 256, 4096, 65536}

### Results (corrected; original code had bug in 2-adic chi² expected counts)
- chi² mod 2^k: all z ∈ [-1.8, +1.8] across 8 words × 5 moduli (40 tests, none significant)
- 2-adic chi²: z = +2.5, +0.8, +0.7, +0.9, +0.1, -0.6, -1.1, -0.8 (one borderline)
- Fourier |E|: all |z| < 2.5 (8 words × 7 frequencies = 56 tests, none significant)

### Verdict
**No carry-aware bias.** SHA-256 hash is uniform mod 2^k and in 2-adic norm
on HW=2 inputs. The carry mixing in the last 64 rounds (block 2) effectively
randomizes any modular residual.

## Combined finding

The "alien antenna" hypothesis (look in non-XOR algebra) does not break
through the wall on its own. But it confirms IT-13's finding:

- Real architectural signal exists (Omega_3 = +0.98, 16-sigma deviation)
- It's delocalized (every state1 bit carries a piece)
- It does not manifest in single-probe carry-aware statistics

SHA-256 design appears to spread non-randomness across the maximum-dimension
collective statistic (3rd-order Walsh tensor), making it detectable but not
locally exploitable. This is consistent with the methodology v20 conclusion:
"SHA-256 = thermostat + carry expander, every metric is controlled."

## Note on IT-15 bug

The first version of it15_additive.py had incorrect expected[6] in the 2-adic
chi² test (used 2^-6 for tail probability paired with single-bin observed,
yielding spurious z = +130 to +170). The corrected analysis above uses proper
7-category split (i=0..5 single + i>=6 tail) with matched expected probabilities.
The corrected z values are uniformly small (|z| <= 2.5).
