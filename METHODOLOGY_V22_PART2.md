# Part 2: 8-Level Anatomy + Dead Zone

---

## 3. SHA-256: 8-Level Anatomy

```
Level 0: HASH (256 bits)
  └ Level 1: RECURRENCE on (a,e) — 64 bits, 4th order (exp181)
       └ Level 2: THERMOSTAT E[Δ]=-(δ-32) — R²=0.48 (exp186)
            └ Level 3: NONLINEAR δa×δe — corr=-0.568 (exp188)
                 └ Level 4: WHITE NOISE σ=4.0, autocorr=0 (exp189)
                      └ Level 5: 64-bit δ-VECTOR, PCA=64/64 (exp190)
                           └ Level 6: 16 PREDICTABLE BITS (exp191)
                                └ Level 7: Σ/σ FINGERPRINTS (exp192)
                                     └ Level 8: 32/32 DISTANCES (exp193)
```

### Level 1: SHA-256 = Recurrence on (a,e)

Verified 300/300 (exp181):
```
a[r+1] = F(a[r], a[r-1], a[r-2], e[r], e[r-1], e[r-2], e[r-3], W[r], K[r])
e[r+1] = G(a[r-3], e[r], e[r-1], e[r-2], e[r-3], W[r], K[r])

75% of state = shift register copies (b=a[-1], c=a[-2], d=a[-3], f=e[-1], etc.)
Only 64 fresh bits per round (a_new, e_new)
64×64 Jacobian: 22/64 damping modes (σ<1), σ_min=0.020
Recurrence INVERTIBLE: W[r] = e[r+1] - a[r-3] - e[r-3] - Σ₁ - Ch - K (100% exact)
```

### Level 2-3: Thermostat + Nonlinear Correction

```
δ(a,e)[r+1] = 0.69 × δ[r] + 9.92 + NOISE

NOISE decomposition:
  32% = -0.042 × δa × δe (corr=-0.568, explains ALL autocorrelation)
  68% = white noise (σ=4.0, zero autocorrelation, irreducible)

After removing δa×δe: noise autocorrelation drops from -0.43 to -0.03 (zero)
History terms: R²=0.0016 (nothing)
K-modulation: F=0.23 (nothing)
Schedule correlation: +0.009 (nothing)
```

---

## 4. Dead Zone (Rounds 21-64): Complete Inventory

### Five Phases of SHA-256

```
FROZEN (r=0):      δH=0,   G=136, K=120, P=0
MELTING (r=2):     δH=25,  G=116, K=115, P=25
MIXING (r=3-5):    δH=54→114
CHAOS (r=6-7):     δH=124-128, G≈64, K≈64, P≈128
EQUILIBRIUM (r=8+): δH=128±1 (stable forever)
```

Full mixing in 6 rounds. Equilibrium by round 7. Dead zone = rounds 8-64.

### What Lives in the Dead Zone

| Feature | Value | Exploitable? |
|---------|-------|-------------|
| Temporal memory lag-1 | corr=0.75 | NO (= thermostat) |
| Positional churn | 62%/round | NO (random direction) |
| 5 resonant periods | 16.1, 9.3, 21.3, 44.6r | NO (message-dependent) |
| 64-cycle K-sync | period=65.4≈64 | NO (weak amplitude) |
| K-fingerprints | HW range=7.6 | NO (F-ratio=0.23) |
| Carry highways (bit 11) | 80.6% alive | NO (structural, not exploitable) |
| Carry deserts (bit 7) | 69.2% alive | NO |
| dH dips (don't bounce) | E[next]=115 after dip | NO (regression to mean) |
| Bit 18 memory | lag-1=0.113 | NO (1.1% advantage, non-accumulative) |
| Bit 15 predictability | 2.7% advantage | NO (non-accumulative) |
| IV permanent mask | 136 G-positions, 120 K-positions | NO (tautological from IV) |

### Spatial Structure: ZERO

```
Direction of δ-vector: cosine=0.500 at ALL lags (fully random)
Persistence: 0.504 ≈ random (0.500)
Inter-message correlation: -0.001 (zero)
```

Thermostat controls MAGNITUDE. Direction = fully random.

### Carry Organism Ecology

```
Population: 191.6 ± 7.1 (stable)
Births: 48.4/round, Deaths: 48.0/round (balanced)
Net growth: +0.42/round (≈0)
Species diversity: 10.8 ± 1.2
Average lifetime: 3.7 positions ≈ τ_★
Length distribution: L=1 (27%), L=2 (20%), L=3 (14%), L=4 (11%)...
```
