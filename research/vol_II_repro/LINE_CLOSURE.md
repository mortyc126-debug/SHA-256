# Closure of the differential e-zero / MITM line

This file summarizes a self-contained investigation that re-examined the
r=17 Wang barrier and its cost claims, with from-scratch verified code
(Volume II had none on disk). The line is now **fully mapped and closed**.

## What was established (all gold-verified on raw SHA-256)

1. **Vol II reproducible**: SHA-256 == hashlib, 6/6 base constants,
   T_WANG_CHAIN 1000/1000, barrier 0/1000, T_DE17_DECOMPOSITION 2000/2000.
2. **П-27C correction**: δe17 = f(W10,W11) + g(W14) is *exactly* separable
   over a disjoint-influence split; T_2D_BIRTHDAY_NEGATIVE's "MITM impossible"
   was drawn from testing only the shared pair (W0,W1).
3. **17 e-zeros**: 2^16 time / 2^16 memory (vs T_BIRTHDAY_COST17's 2^32).
4. **18 e-zeros**: 2^33 time / 2^32 memory (vs T_BARRIER_16's 2^64); δe18
   verified uniform over MITM pairs.

## Why it is NOT a break — three tested walls

- **Time-memory tradeoff, product preserved.** 2^16·2^16 = 2^32 ;
  2^33·2^32 ≈ 2^64. Total work is unchanged; cost only moves time↔memory.
- **No composition.** No single bipartition separates δe17 *and* δe18
  (compose_test: δe18 at RO noise across every split that separates δe17).
- **No Wagner / k-list product reduction.** `wagner_test.py`: for every
  k≥3 partition tried, the worst group-pair separability of δe18 is **0.000**,
  identical to the RO control — no k-group additive structure exists. The
  nonlinear carry coupling forbids the decomposition a generalized-birthday
  attack would require. So the 2^64 *product* for 18 e-zeros holds.

```
partition                          worst de17  worst de18   Wagner?
k=2 (W10,W11 | W14)                  1.000       0.000        no
k=3 (W10,W11 | W14 | W15)            1.000       0.000        no
k=3 (W2,W3 | W10,W11 | W14,W15)      0.000       0.000        no
k=4 (.. | W10,W11 | W14,W15)         0.000       0.000        no
RO control                           0.000       0.000        -
```

## Net result for the program

- Two methodology cost claims corrected: T_BIRTHDAY_COST17 (2^32) and
  T_BARRIER_16 (2^64) are **time-memory products**, not memoryless time
  walls. П-27C's "MITM impossible" is refuted.
- The corrections are **local**: e-differential zeros are necessary but not
  sufficient; the a-register stays saturated (HW≈16) and W[16..63] are
  schedule-fixed. The **2^128 collision bound is untouched**, and no
  classical 2-list or k-list reshuffle of this differential reduces the
  total work toward a collision.

## Why the e-zero paradigm cannot reach a collision (structural)

A collision needs all eight register differences to vanish at the output.
Controlling δe for 16 rounds (Wang) costs nothing, but each message word
gives exactly **one** additive degree of freedom (T_ONE_CONSTRAINT), so δa
cannot be controlled simultaneously with δe — δa saturates by round 5 and
never returns. Past round 16 there are no free words left to correct with.
The MITM/Wagner analysis here confirms the only leverage (additive
separability) exists for a single e-barrier and does not extend. This line
is exhausted.

## Genuinely different directions left (outside this line)

- **c-world / Q∩T global solver** (Vol II's own "only promising direction"):
  solve the quadratic(GF2) ∩ threshold system globally rather than via
  differentials. Different paradigm; not touched here.
- **Multi-block setups** where block 1 forces a favorable midstate.

Both are long shots and partially explored in the corpus, but they are not
this (now-closed) differential line.
