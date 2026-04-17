# IT-22: Vector-level analysis — refines IT-21 interpretation

## What we did

Computed direct_z[256] and chain_z[256] VECTORS at r ∈ {0, 16, 32, 48, 64}
using omega3_full C binary (stride=8, ~345K triples per round).

## What we expected (from IT-21)

If Omega_3 = +0.92 conserved across rounds implies a CONSERVED VECTOR
(Noether-analog symmetry), then cross-round chain_z vectors should be
highly correlated — the same "direction" reappearing at each round.

## What we found

**Cross-round correlations are essentially ZERO:**
```
chain_z cross-round:    all |corr| ≤ 0.25, typical < 0.1
direct_z cross-round:   all |corr| ≤ 0.20
```

**SVD of 5×256 stack: nearly full rank.**
```
direct_z singular values: [18.3, 17.6, 15.5, 14.6, 13.4]  — σ1/σ2 = 1.04
chain_z singular values:  [454, 409, 396, 356, 339]      — σ1/σ2 = 1.11
Rank-1 variance fraction: 26% (of theoretical 20% if all equal)
```

**Top-20 bits per round have empty intersection across 5 rounds.**
- Top bits completely reshuffle each round
- No persistent "weak bits"

## Revised interpretation

Omega_3 is a **scalar** invariant but NOT a **vector** invariant.

Round function R: state[r] → state[r+1] acts like an ORTHOGONAL
TRANSFORMATION in the Walsh-3 subspace:
- Rotates direct_z vector (new bits become top)
- Rotates chain_z vector (new triples become top)
- PRESERVES the angle between them (cos θ ≈ 0.9 at every round)

This is a WEAKER constraint than Noether-style conservation:
- Many operators preserve scalar products
- Doesn't fix specific bit values
- Can't directly construct collisions from it

## Level of result (revised, honest)

- **Distinguisher**: SHA-2 family vs RO with p < 10⁻²⁷ at every round (new)
- **Rotational symmetry in Walsh-3**: if the group of rotations can be
  characterized, could lead to attack primitive (but open direction,
  not proven here)
- **Methodological contribution**: Omega_k as analysis framework for
  hash functions (new invariant class)

**Publishable level**: FSE or CT-RSA workshop, not Crypto.

## Open questions this raises

1. **What is the group of rotations?** Round function is deterministic
   for fixed W, K. Can we characterize the orbit structure?

2. **Is there a higher-order invariant?** Maybe Omega_4 or Omega_5
   captures a stronger conservation (e.g., vector-level).

3. **Does the scalar invariance constrain message schedule?** The
   conservation requires specific relationships between W and K.
   Analyzing which W-patterns violate conservation may yield weak
   message classes.

## Honest update to session summary

The headline "Omega_3 is a conserved invariant" STANDS, but with refined
interpretation:
- ✓ Scalar invariant (inner product angle preserved)
- ✗ Vector invariant (vectors themselves change)
- ✓ Universal across features, K, sample size
- ✓ Specific to SHA-2 family
- ? Rotational symmetry structure (open, future work)
