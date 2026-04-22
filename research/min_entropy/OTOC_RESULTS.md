# OTOC (Out-of-Time-Order Correlator) Analysis of Cryptographic Hash Functions

**Project status (April 2026) — physics-grounded scrambling measurement**

## Headline Result

**First clean, theoretically-grounded cross-architecture scrambling fingerprint**
for cryptographic hash functions, using discrete OTOC framework from quantum chaos.

### Complete Cross-Architecture Table

| Hash | Total rounds | Full scramble at | % of total | Transition character |
|---|---|---|---|---|
| **SHA-256** | 64 | r=24 | **37%** | gradual (r=4..24) |
| **SHA-3** | 24 | r=4 | 17% | sharp (r=2→r=3: 110× drop) |
| **BLAKE2s** | 10 | r=2 | 20% | sharp (r=1→r=2: 100× drop) |

Key quantitative finding: **SHA-256 has 40-round design margin** between full
scrambling (r=24) and total rounds (r=64). Modern hashes tighter: 80% of rounds
are "extra".

## OTOC Definition (Classical Analog)

```
C[i, j, r] = E_msg[ Pr(output[r][j] flips | input bit i flips) - 0.5 ]
||C(r)||_F² = sum over (i, j) of C[i, j, r]²
```

Interpretation:
- C[i, j, r] = ±0.5 → deterministic flip (maximum correlation)
- C[i, j, r] = 0   → fully scrambled (random 50/50)
- ||C(r)||_F² quantifies deviation from scrambled state

**Theoretical RO limit**: ||C_RO||_F² = msg_bits × output_bits × 0.25 / N
For N=200, msg=512, out=256: limit = 163.84.

## Clean Theoretical Baseline

Unlike previously attempted Ω_k probe (⊘ROLL — chi_arr artifact), OTOC converges
to theoretical RO prediction:

| Hash | Measured ||C||_F² (full output) | Theoretical | Diff |
|---|---|---|---|
| MD5 | 81.32 | 81.92 | 0.7% |
| SHA-1 | 101.77 | 102.40 | 0.6% |
| SHA-256 | 163.48 | 163.84 | 0.2% |
| SHA-512 | 328.33 | 327.68 | 0.2% |
| SHA-3-256 | 164.67 | 163.84 | 0.5% |
| BLAKE2b | 163.89 | 163.84 | 0.03% |
| BLAKE2s | 163.37 | 163.84 | 0.3% |

All 8 hashes match within 0.7%. Verifies the OTOC framework is well-calibrated.

## SHA-256 Round-by-Round Evolution

```
r      ||C||_F²      Status
1       32,737      1 round, no scrambling
2       32,434      slow decay
6       26,480      gradual
12      14,249      accelerating
16       6,089      rapid
20         422      phase transition
24         163      ✓ matches RO limit (163.84)
64         164      fully scrambled (no further change)
```

**Phase transition r=17-20** consistent with methodology's T_BARRIER_EQUALS_SCHEDULE
(Wang-barrier at r=17). NOW measured via rigorous framework without artifacts.

**Decay rate** λ ≈ 0.043 per round on log-scale excess over limit.

## SHA-3 Round-by-Round

```
r      ||C||_F²      Status
1       32,338      almost no scrambling
2       20,508      gradual
3          188      PHASE TRANSITION — 110× drop in one round
4          164      ✓ matches RO limit
24         165      saturated
```

SHA-3 Keccak θ-step provides global mixing → near-instant scrambling.
Sharp single-round phase transition at r=3.

## BLAKE2s Round-by-Round

```
r      ||C||_F²      Status
1       17,283      partial
2          164      ✓ PHASE TRANSITION + saturated
3-10       ~164     scrambled
```

BLAKE2s ARX G-function with diagonal mixing reaches RO in 2 rounds.
Fastest absolute scrambler (2 rounds vs SHA-3's 4).

## Physics Connections

### Hayden-Preskill Scrambling Time
Black holes are "fast scramblers" — scrambling time ~ t_s = β ln(N).
For hash functions, analog: scrambling rate sets minimum useful rounds.
SHA-256's 37% is "slower than physical bound" → exploitable structure.

### Maldacena-Shenker-Stanford Bound
Quantum chaos has universal bound λ_L ≤ 2π/β.
Our OTOC decay rate is classical analog. SHA-3 and BLAKE2 appear saturated.
SHA-256 below saturation → design has room for further mixing (or room for attacks).

### Yoshida-Kitaev Decoding
Efficient decoder for Hayden-Preskill protocol uses Grover search.
Classical analog: MITM preimage O(2^(n/2)) matches Grover O(2^(n/2)) quantum.
Our OTOC measures what both have to bypass.

### Black-Hole Radiation Decoding ≡ Quantum Cryptography (CRYPTO 2023)
Formal equivalence: BH decoding hardness ↔ quantum crypto primitives.
Classical hash preimage is a "scrambling decoder" in this framework.

## Methodological Win

This OTOC analysis REPLACES our previously attempted Ω_k probe which was
⊘ROLL (chi_arr artifact, 8 retractions documented in §III.7).

**What went wrong with Ω_k**: used chi_arr from input-derived state, which
created systematic alignment between direct_z and chain_z regardless of target.
Led to artifact ≥7σ "distinguishers" for random oracle.

**What works with OTOC**:
- Well-defined theoretical RO baseline (msg×out×0.25/N)
- Empirical verification matches theory within 0.7%
- Reproducible across hash families
- Mathematical foundation in quantum chaos literature

## Files

- `otoc_sha256.py` — SHA-256 round-by-round OTOC (r=1..64)
- `otoc_cross_hash.py` — full-output OTOC for 8 hash families
- `otoc_sha3_rounds.py` — SHA-3 Keccak-f round-by-round
- `otoc_blake2s_rounds.py` — BLAKE2s round-by-round (verified against hashlib)
- `otoc_sha256_results.json` — SHA-256 measurement data
- `otoc_cross_hash_results.json` — cross-hash comparison data
- `otoc_sha3_rounds_results.json` — SHA-3 rounds data
- `otoc_blake2s_rounds_results.json` — BLAKE2s rounds data

## Honest Scope

This is a **scrambling rate measurement**, NOT a distinguishing attack.
All secure hashes (SHA-256, SHA-3, BLAKE2) reach full scrambling at their
respective round counts. Once scrambled, output is indistinguishable from RO.

**What OTOC measures well**:
- Architectural scrambling rate (round-by-round)
- Cross-architecture fingerprint
- Design margin quantification

**What OTOC does NOT measure**:
- Collision resistance (MD5 is broken but RO-like in OTOC)
- Preimage difficulty at full output
- Specific attack paths

OTOC is complementary to attack analysis, not a replacement.

## Publication Framing

"Cross-Architecture Information Scrambling Rates of Cryptographic Hash
Functions via Discrete OTOC Analysis"

Target venue: IACR ePrint, workshop (FSE, CT-RSA) or physics-cryptography
crossover journal (maybe IEEE Quantum).

Main contribution: first systematic OTOC measurement establishing
quantitative round-by-round scrambling curves for SHA-256, SHA-3, BLAKE2s
with theoretical RO baseline verified to 0.7%.

## Next Directions

1. **OTOC rate vs MSS bound**: derive classical analog of 2π/β bound,
   compare measured rates to theoretical maximum
2. **BLAKE2b round analysis**: complete 64-bit variant measurement
3. **ChaCha20/Salsa20 ARX comparison**: same family as BLAKE2, different constants
4. **Structural decomposition**: which components (Σ-rotations, G-function)
   contribute most to scrambling rate? Chimera variants provide answer
5. **Attack-OTOC connection**: do faster-scrambling hashes truly resist
   more attacks? Empirically test on known reduced-round attacks
