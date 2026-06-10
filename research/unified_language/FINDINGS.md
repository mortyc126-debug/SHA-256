# The unified-language search: where the "new math" must live

Goal: find (or rule out) a single mathematical structure in which SHA-256's
three incompatible operations -- rotation (convolution), boolean Ch/Maj
(pointwise), and modular addition (carry) -- are simultaneously simple.

## Measured result (n=8 toy, `seesaw.py`, `mersenne_seesaw.py`)

Complexity (degree) of each primitive in three representations:

```
op        deg_F2     deg_Z/2^n   deg_Z/2^n-1 (Mersenne)
XOR c        1          48           254
ROTR 3       1          36             1
ADD c        6           1           254
AND c        1         128           254
```

Structural ops (XOR, ROTR, ADD) that are simultaneously **linear**:

```
F2        : 2/3   (XOR, ROTR linear; ADD = carry is the lone obstruction)
Z/2^n     : 1/3   (only ADD)
Z/2^n-1   : 1/3   (only ROTR -- it is literally mult by 2^(n-r), verified)
```

Two hard facts:
- **Max ANF degree is invariant under any F2-linear basis change** (verified
  5/5 on ADD): no linear re-coordinatization lowers the carry's degree.
- **Mersenne is not a unifier**: it linearizes rotation but turns mod-2^n
  addition into degree 254 (the wrap-correction is the nonlinear cost -- this
  is exactly the methodology's "592 corrections", §II.7.8).

## What this pins down

The bit field **F2 is already the optimal single language**: XOR and rotation
are linear there, and the *only* irreducible obstruction is the carry. So the
unified language, if it exists, is not some exotic third basis -- it is a
structure that **extends F2-linearity to also absorb carry, without
de-linearizing rotation**.

The structure that linearizes carry is well known: **Witt vectors / delta-ring
(2-adic)** -- carry-addition is precisely Witt-vector addition, the ring "+".
But the Witt coordinate is the integer coordinate (Z/2^n column above), where
rotation jumps to degree 36. Same seesaw.

So the precise open problem is:

> Does there exist a single structure that is simultaneously an
> **F2[Z/n]-module** (rotation & XOR linear -- the convolution/position
> structure) **and** a **delta-ring / Witt structure** (carry = the ring
> addition)?

## Why this is the prismatic frontier (and likely obstructed)

This is exactly the question the repo's `research/prismatic/` program reached
from the top down:
- Sigma/sigma (rotations) act **unipotently** on prismatic H^1 (Session 5.2)
  -- the position/convolution structure.
- The **delta-ring** structure (Frobenius lift) encodes the carry.
- **Theorem 3.3 (prismatic)** is a *no-go* for the naive combination:
  `Z_2[i]` admits no delta-structure lifting Frobenius from `F_2[i]` -- i.e.,
  you cannot freely put the carry's delta-structure on the cyclotomic /
  group-ring (rotation) structure.

So both ends of the corpus -- the elementary seesaw here and the prismatic
cohomology there -- converge on the same wall, now stated precisely: **the
carry delta-structure and the rotation group-algebra structure do not
combine into one ordinary ring.** That is the obstruction, not a vague
"incompatibility".

## Is there an escape? (honest)

In prismatic geometry, structures that refuse to combine into one ring are
handled not by a single ring but by a **site / derived (∞-categorical)
object** (the prismatic site), where the two structures live on different
faces of a diagram and are glued cohomologically. That is the only place a
genuine "new language" could exist -- and it is exactly what the prismatic
program flagged as requiring specialist absolute-prismatic expertise, beyond
elementary computation.

**Net:** the "new paradigm" is real, precisely located, and not mystical: it
would be a derived/prismatic structure unifying convolution and the carry
delta-structure. The elementary obstruction is now measured (F2 optimal at
2/3, carry irreducible) and matches a known prismatic no-go (Thm 3.3). A true
unifier, if it exists, lives in the derived prismatic site -- a concrete,
nameable open problem, not a leap beyond understanding.
