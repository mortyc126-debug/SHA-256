# SHA-256 ★-Algebra: Complete Methodology v22

## Part 1: ★-Algebra Foundation + Core Theorems

---

## 1. ★-Algebra Definition

The native mathematical framework of SHA-256, created during this research.

```
★(a, b) = (a ⊕ b, a & b)

Maps two 32-bit words to a pair:
  - XOR component (linear part)
  - AND component (nonlinear part)

Projection: π_add(x, c) reconstructs addition:
  a + b = π_add(★(a, b))

Verified: 5000/5000 bit-exact (exp95)
```

### Extended ★-Operations

| Operation | Definition | Source |
|-----------|-----------|--------|
| ★(a,b) | (a⊕b, a&b) | exp95 |
| ★²(a,b,c) | (a⊕b⊕c, Maj(a,b,c)) | exp125 — Maj IS ★²-carry |
| ★₃ | GKP ternary automaton (G→1, K→0, P→carry_in) | exp141 |
| ★⁻¹ | Dual: (a+b, a&b), δ(SUM)=2·δ(AND) | exp125 |
| Sub-bits | {0_K, 0_P, 1_P, 1_G} — below binary | exp171 |

### Key Constants

| Constant | Value | Meaning | Source |
|----------|-------|---------|--------|
| η | 0.18872 = (3·log₂3)/4−1 | Spectral gap of GKP automaton (λ₂=1/3) | exp141 |
| τ_★ | 4 rounds | Fundamental timescale: mixing, equilibrium, carry depth | exp157 |
| Carry rank | 3⁵ = 243 | Ternary structure, (1/3)⁵ ≈ 1/243 | exp141 |
| α (thermostat) | 0.69 | Reversion coefficient: δ[r+1] = 0.69·δ[r] + 9.92 | exp186 |
| δ* | 32 = 64/2 | Equilibrium point of δ(a,e) | exp186 |

---

## 2. The 18 ★-Theorems

### Structural Theorems

**★-1: Carry-Free Bit Preservation.** If S₁ and S₂ agree on LSBs 0..j, then δ_XOR is preserved on those bits through addition. (exp136)

**★-2: ROTR Moves Invariant.** Partial ★-invariant on j bits MOVES through ROTR but preserves size. Position shifts by rotation amount. (exp136)

**★-3: Ch/Maj Preserve Invariant.** If all inputs agree at position i, then Ch and Maj agree at position i. (exp136)

**★-4: Shift Register Cascade.** δ_XOR=0 on word a at round r → word d at round r+3 (exact, verified exp136). Words die: a at r+2, b at r+3, c at r+4, d at r+5.

**★-5: Three Nonlinearity Sources.** Carry (degree up to 32), Ch (degree 2), Maj (degree 2). All three needed for full nonlinearity. XOR-SHA-256 is NOT linear (Ch, Maj have AND). (exp123)

### Impossibility Theorems

**★-6: Incompatibility of + and ROTR.** No nontrivial function I(δ) is simultaneously invariant under addition AND rotation. Addition preserves arithmetic diff; ROTR preserves bit permutation. These are incompatible. (exp138)

**★-7: Instant Collapse.** All ★-invariants die at the FIRST round with δW≠0. Not gradual decay — instant decorrelation (corr drops from 1.0 to 0.0 in one round). (exp138-139)

### Quantitative Theorems

**★-8: ★-Invariant Decay Rate.** |I_r| = 256 − 6.5r for r ≤ 20, then |I_r| = 128 for r > 20. Invariant dies at rate 6.5 bits/round. (exp136)

**★-9: Autocatalytic Amplification (EXACT).** δCh = δe & (f⊕g) and δMaj = δa & (b⊕c). Verified 2000/2000. Amplification rate α = HW(f⊕g)/32 = 0.500 universally. (exp140)

### Architectural Theorems

**★-10: Polynomial Representation.** x³²+1 = (x+1)³² in GF(2) — local ring. All Σ polynomials invertible (P(1)=1). Σ₁ minimum weight expansion: 1 bit → 3 bits (ratio 1/3 = λ₂!). (exp150)

**★-11: Two-Ring Structure.** Ring 1 (polynomial, ROTR): Σ functions. Ring 2 (coordinate, AND): Ch, Maj. Ring 3 (arithmetic): addition. ROTR is automorphism of BOTH rings 1,2. No other operation is. (exp151)

**★-12: Chain Spectrum Prediction.** Combined spectrum (HW + max_chain + n_chains + entropy) predicts hash distance with corr=0.487, +41% over Hamming alone. Entropy is strongest factor (coeff=2.69). (exp156)

**★-13: Four-Round Scale.** τ_★ = 4 rounds = XOR-channel death = M₃ entropy saturation = kill chain effectiveness = carry depth average = nonlinear bit count reaching 128. (exp157)

### Dead Zone Theorems

**★-14: M₃ Equilibrium.** GKP reaches G:K:P = 1:1:2 (= 64:64:128) in 4 rounds. M₃ entropy = 1.500 = 3/2 exactly. OVERSHOOT at round 4 (1.578 > 1.500). (exp158)

**★-15: Structural Penalty.** P(dH < k | structured δ) ≤ P(dH < k | random δ). SHA-256 PENALIZES structure. Random = optimal strategy. Verified at N=20000. (exp176, exp198)

**★-16: Thermostat Law.** δ(a,e)[r+1] = 0.69·δ[r] + 9.92 + noise. E[Δ] = -(δ-32). Perfect linear proportional controller. Symmetric (rise=drop, ratio 1.04). Recovery: 90% in 2 rounds. Noise decomposed: 32% = δa×δe (corr=-0.568), 68% = white noise. (exp185-189)

**★-17: Permanent Fingerprints.** Architectural rotation distances (2,6,11,13,17,18,19,22,25) create permanent corr≈0.07-0.09 that APPEAR at round 20 and NEVER FADE. Schedule σ fingerprints 2.3% stronger than round Σ. (exp192)

**★-18: Full Distance Coverage.** 12 rotation numbers + their pairwise sums/differences cover ALL 32 possible bit distances. No "non-architectural" distance exists. (exp193)
