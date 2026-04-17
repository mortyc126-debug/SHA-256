# IT-16 + IT-17: chimera dissection + spectrum truncation

## IT-16 results (8 SHA-256 variants on Omega_3)

| Variant | Description | Ω_3 | sign-test | Verdict |
|---|---|---|---|---|
| V0_vanilla | reference | +0.9985 | 16/16 | baseline |
| V1_no_Sigma | kill big Σ in compress | +0.9761 | 13/16 | survives |
| V2_no_sigma | kill little σ in schedule | +0.9800 | 15/16 | survives |
| V3_no_diffusion | kill all rotation-XOR | +0.8937 | 13/16 | weakened, but stats blow up |
| V5_linear_NLF | Ch/Maj → XOR | +0.9899 | 14/16 | survives |
| V7_almost_linear | V3+V5 | +0.8138 | 10/16 (p=0.45) | NOT significant |
| K_ZERO | K[t]:=0 | +0.9910 | 15/16 | survives |
| K_GOLDEN | K[t]:=t·0x9E3779B9 | +0.9961 | 16/16 | survives |

### Findings

1. **K constants are NOT the source of Ω_3 signal.** K_ZERO and K_GOLDEN give
   essentially identical Ω_3 to vanilla. NSA-magic-K hypothesis falsified
   for this statistic.

2. **No single component carries the signal.** V1, V2, V5 (each killing one
   non-linear component) all leave Ω_3 at ≥ +0.976. Only the FULL
   linearization (V7) brings it down to non-significance.

3. **K affects WHICH bits are biased, not the magnitude.** K_VANILLA top-16
   bits = [10, 210, 38, 34, ...]; K_GOLDEN top-16 bits = [251, 128, 45, ...].
   Different K → different bit-pattern fingerprint.

## IT-17: spectrum truncation to "hot" bits

Hypothesis: top-32 hot state1 bits from IT-14a should carry the signal.
If true, restricting Walsh to those bits should preserve Ω_k.

| k | Ω_k (full 256 bits, IT-6b) | Ω_k (top-32 hot, IT-17) |
|---|---|---|
| 1 | -0.06 | -0.37 |
| 2 | +0.44 | -0.09 |
| 3 | +0.98 | -0.12 |
| 4 | n/a | +0.17 |

### Verdict

**Truncation destroys the signal.** Even though "hot bits" appear most often
in top-50 individual triples (IT-14a), they do NOT carry the aggregate
Ω_3 signal when isolated. The +0.98 correlation requires ALL 256 state1
bits to participate.

## Combined picture

The Ω_3 signal:
- Is real (16-σ deviation, p ≈ 10⁻⁴⁰)
- Is feature-invariant (any input feature gives ~+0.98)
- Is N-invariant (stable from K=16K to K=130K)
- Is K-magnitude-invariant (Vanilla, Zero, Golden all give ~+0.99)
- Is K-pattern-DEPENDENT (top biased bits change with K)
- Is delocalized (cannot be isolated to subset of state1)
- Is composite-architectural (not from any single SHA component)

The "paint in ocean" metaphor is exact: every drop of water carries an
infinitesimal trace of paint, but extract the cumulative collective and
the color is unambiguously visible. Removing any large fraction destroys it.

## Open lever (for IT-18)

K-pattern-DEPENDENCE is the most promising remaining direction:
the bias bit-pattern is a deterministic function of K. Reverse engineering
this map (K → fingerprint) and its inverse (fingerprint → K) could
constitute information leakage from the hash about K.
