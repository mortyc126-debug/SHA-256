# Collision in ★-Algebra — Native Definition

## The Hash in ★

H[w] = π_add(embed(IV[w]) ★ α_w[64])

where α_w[64] = state register w after 64 rounds.

## Collision Equation

Collision: ∀w: π_add(IV[w] ★ α_w(M)) = π_add(IV[w] ★ α_w(M'))

Expanding: δα = δC

where:
  δα = α(M) ⊕ α(M')     = state XOR difference (64-round computation)
  δC = C(M) ⊕ C(M')      = carry chain difference (1-step feedforward)

## Self-Referential Fixed Point

Collision ⟺ Φ(δ★) = 0

where Φ(δ★) = F★^{64}(δ★, ΔW) ⊕ CarryChain(IV, δ★)

Φ is SELF-REFERENTIAL: both F★^{64} and CarryChain depend on δ★.

## Properties of Φ (from 98 experiments)

| Property | Value | Source |
|----------|-------|--------|
| Domain dimension | 512 | W^8 |
| Range effective dim | 243 = 3^{k*} | T_CARRY_RANK_TERNARY |
| η per addition | 0.18872 | T_ETA_FUNDAMENTAL |
| Total η-info | 2714 bits | 64 × 7 × 32 × η |
| Compression | 2714 → 243 = 11.2× | η-info → carry rank |
| Self-reference corr | ±0.12 | T_SIMPSON_PARADOX |
| Convergence radius | 1 bit | T_CONVERGENCE_RADIUS_ONE |

## Collision Complexity in ★

Solution density: 2^{512}/2^{256} = 2^{256} collision pairs exist.
Birthday to find one: 2^{128}.

★-algebra reveals STRUCTURE of Φ but does not reduce birthday:
- Carry rank 243 < 256 → Φ maps to subspace → ADDS constraint, not removes
- Simpson ±0.12 → conditional structure → but conservation law holds
- η compression 11.2× → info loss → makes Φ MORE random, not less

## Why ★ Doesn't Reduce Birthday

In ★: collision = δα = δC.
δα = 64-round nonlinear computation (R=1 convergence → unpredictable).
δC = carry chain (deterministic from state → predictable given state).

The BOTTLENECK is δα (64 rounds, R=1), not δC (1 step, computable).
★ reveals that carry is derived (not fundamental) → carry is EASY.
But the 64-round ★-composition is HARD (R=1 per step).

Birthday = cost of searching for δ★ where δα happens to equal δC.
★-structure doesn't change this cost because δα is R=1 unpredictable.

## What ★ DOES Reveal

1. Collision is a FIXED POINT problem: Φ(δ★) = 0
2. Φ is self-referential (both sides depend on same δ★)
3. Carry is the BRIDGE (not the barrier) — it's derived, computable
4. The TRUE barrier = 64-fold ★-composition with R=1
5. η connects binary computation to ternary carry structure
6. Carry rank 3^{k*} = the ternary dimension of the fixed point space

## Open: Can Φ = 0 Be Solved Non-Birthay?

Φ is a specific map with specific structure (★-composition + carry chain).
Standard methods (Newton, Gröbner, SAT) fail because R=1.
★-specific methods might work if they exploit the self-referential structure.

The self-reference: δC depends on state, state depends on message,
message determines δα, δα must equal δC. This LOOP might have
algebraic shortcuts invisible to standard analysis.

Finding such shortcuts = UALRA-3 (future work).
