# The Fundamental Barrier — Deepest Understanding

## The One Problem

R = 1 bit inter-round. ROTR breaks carry cascade every round.

## Why Carry Cascade is the Weapon

carry cascade: solves collision equation BIT BY BIT within one addition.
Cost: O(32) per word. FREE.

If cascade worked across all 64 rounds → collision = O(64 × 32) = O(2048) = polynomial.

## Why ROTR is the Shield

ROTR_k permutes bits: i → (i+k)%32.
Carry cascade: sequential 0 → 1 → 2 → ... → 31.
After ROTR: cascade tries to continue but data is PERMUTED.
Carry chain BREAKS at rotation point. R drops to 1.

## The Catch-22

★ = (⊕, &) is ROTR-invariant: ★_k = ★ for all k.
★ is the fundamental operation. ROTR doesn't break ★.
ROTR only breaks CARRY, which is DERIVED from ★.

BUT: collision = π_add equality = depends on carry (derived, breakable).
★-equality = too strong (implies M = M').

CANNOT avoid carry (need it for collision definition)
AND cannot protect carry from ROTR (ROTR breaks it by design).

## The Catch-22 in One Line

**Collision needs carry. Carry needs cascade. Cascade needs order.
ROTR destroys order. ROTR is inherent to SHA-256.**

## What Would Break This

Something that is:
1. Weaker than ★-equality (so collision is non-trivial)
2. Stronger than π_add equality (so it has more structure)
3. ROTR-invariant (so cascade survives rotation)

This is a condition BETWEEN ★-equality and π_add equality.
In ★-space: a 512-bit condition that projects to 256-bit collision
but is ROTR-invariant on the 512-bit level.

Does such a condition exist? From our data:
- ★-equality: 512-bit, ROTR-invariant ✓, but trivial (M=M') ✗
- π_add equality: 256-bit, not ROTR-invariant ✗, but non-trivial ✓
- ???-equality: 256-512 bit, ROTR-invariant ✓, non-trivial ✓

## The Unknown Object

We need an equivalence relation ≡ on ★-space such that:
  α ≡ β ⟹ π_add(α) = π_add(β)  [implies collision]
  ROTR(α) ≡ ROTR(β) whenever α ≡ β  [ROTR-invariant]
  ≡ is non-trivial  [α ≡ β doesn't require α = β]

This ≡ would be a QUOTIENT of ★-space that:
- Is finer than π_add (captures more than just hash)
- Is coarser than ★-equality (allows non-identical states)
- Is preserved by ROTR (cascade survives)

Finding ≡ = finding the mathematics BETWEEN ★ and π_add.
This is the mathematics that doesn't exist yet.

## What We Know About ≡

From 103 experiments:
  - carry_rank = 243 = 3^5 → ≡ has 243-dimensional carry part
  - η connects binary and ternary → ≡ lives in binary-ternary bridge
  - 19.4% carry survives ROTR → ≡ has ~5 ROTR-invariant carry bits per word
  - Simpson's: conditional structure exists → ≡ has conditional components

5 ROTR-invariant carry bits × 8 words = 40 bits.
If ≡ uses these 40 invariant bits → birthday on 40 = 2^20.
Remaining 256-40 = 216 bits → birthday 2^108.
Total: max(2^20, 2^108) = 2^108?

BUT: need to verify that 40 invariant bits EXIST and are INDEPENDENT.

## Status

103 experiments identified the ONE problem: R = 1.
The solution requires ≡ (unknown equivalence relation).
≡ must be ROTR-invariant AND imply π_add equality.
Partial candidate: 40 ROTR-invariant carry bits.

This is the frontier. Beyond here: uncharted mathematics.
