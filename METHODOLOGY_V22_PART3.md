# Part 3: All Attacks Attempted + Results

---

## 5. Attacks: Complete Record

### Standard Cryptanalysis (exp1-53, prior session)

| Attack | Rounds | Result |
|--------|--------|--------|
| Wang differential cascade | 16 | De=0 for 16 rounds, 17th costs 2^32 |
| Coupling-Guided Descent (CGGD) | 64 | = birthday |
| CAIR (carry-aware refinement) | 64 | = birthday |
| Maxwell's Demon | 64 | T_DEMON_FUTILITY: information erased |
| Algebraic (SAT/Gröbner) | 64 | = birthday (≤32r: cheaper) |
| Rotational | 64 | All E[dH]=128 (zero signal) |

### ★-Algebra Native Attacks (exp105-134)

| Attack | Best Result | Scales? |
|--------|------------|---------|
| ROTR-equivariance | Blocked by SHR (624 bits), carry, IV/K | NO |
| Circular carry | EXACT equivariant, but SHR blocks full hash | NO |
| ★⁻¹ Jacobian | Exact for δ=±1 through 19+ rounds, local minima | NO |
| Adaptive solver (5 tools) | random wins by 5.7 bits | NO |
| ★-native tools | dH=87 at 4r (trivial word-swap) | NO |
| ★-enhanced random | V8 multi-target +9.4 bits (more comparisons) | = birthday |
| Cluster search | gain = noise (0-1 bit, oscillates) | NO |
| Kill chain | +27 bits at 4r, dies at 32r | NO |
| ★-weapons (combined) | +2.2 bits Z=5.2 (window artifact) | NO |

### Schedule + Recurrence Attacks (exp146-199)

| Attack | Best Result | Why Failed |
|--------|------------|------------|
| Kill chain scaling | +27b at 4r, +6b at 8r, 0 at 32r+ | τ_★=4 barrier |
| Carry-AND alignment | corr=-0.40 at r=64 only | Too late (costs full hash) |
| 2-adic Newton | 100% at 1r, 0% at 2r+ | Sharp nonlinear transition |
| Damping modes (103/256) | Exist but intersection = dimension formula | Linear algebra tautology |
| Convergence forcing | ae_dist=0 at 8r (trivial from δW=0) | Kill chain |
| Pollard rho (★-aligned) | 6.6× at 20-bit truncated | Inconsistent across sizes |
| Staged attack | +3.8 bits (schedule→killchain→birthday) | Constant factor |
| Judo (δa×δe) | +7.9 bits extra correction | Pulls to δ=32, not δ=0 |
| Self-amplifying cycle | corr(δa[r],δe[r+3])=-0.002 (zero) | T1 drowns signal |
| Survival from δ=2 | δ→32 by round 30 (erased) | Thermalization |
| 11× advantage | FALSE ALARM (N=3000 artifact) | N=20000: ratio=0.97 |
| Schedule nullspace | GF(2) rank=512/512, nullity=0 | Full rank = no collision |

### "Impossible" Ideas (exp113-116)

| Idea | Result |
|------|--------|
| Laplace's Demon (weak PRNG) | Helps preimage, HURTS collision |
| P = NP | Wins if k<7.2, but 64 rounds = 2^128 SAT |
| Quantum BHT | 2^85.3 (12M qubits, 10^17 years) |
| Multiverse | = quantum = 2^85.3 (BBBV theorem floor) |

---

## 6. Why Each Direction Closed

### The 7 Walls of SHA-256

**Wall 1: Schedule Full Rank** (exp199)
```
GF(2) matrix: 1536×512, rank=512/512, nullity=0
Every δM → unique δW. Cannot be cancelled.
```

**Wall 2: Thermostat** (exp186)
```
E[Δ] = -(δ-32). Linear, symmetric, fast (90% recovery in 2 rounds).
Any deviation corrected. Cannot be exploited.
```

**Wall 3: Structural Penalty** (★-Theorem 15, exp198)
```
P(collision | structure) ≤ P(collision | random)
SHA-256 penalizes any structure in δM.
```

**Wall 4: 20-Round Decorrelation** (exp112, exp136)
```
By round 20: all correlations = 0.
Any cheap predictor (< 20 rounds): corr = 0.000 with hash.
Any expensive predictor (> 48 rounds): costs ≈ full hash.
Gap between "cheap but useless" and "useful but expensive" = EMPTY.
```

**Wall 5: White Noise Floor** (exp189)
```
After removing thermostat + δa×δe: residual = white noise σ=4.0.
No autocorrelation. No history dependence. Irreducible.
```

**Wall 6: Carry SNR=1:1** (exp196)
```
Shift register signal (δd = δa[r-3]) drowned by T1 noise.
Even at bit 0 (carry-free): corr = +0.006 (zero).
```

**Wall 7: Architectural Saturation** (exp193)
```
12 rotations cover ALL 32 distances via derivatives.
No "unprotected" distance exists. No blind spots.
```
