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

## The obstruction, measured and localized (`rotation_carry_obstruction.py`)

We tested directly whether rotation is an automorphism of the addition
(`ROTR(a+b) == ROTR(a)+ROTR(b)`):

```
                 distributes over +mod2^n   over +Mersenne(2^n-1)
  n=16 ROTR_1          0.376                      1.000
  n=16 ROTR_3          0.280                      1.000
  n=16 ROTR_7          0.252                      1.000
```

- In the **Mersenne ring Z/(2^n-1), rotation + carry UNIFY perfectly**
  (rotation = mult by the unit 2^(n-r), verified) -- a single ring in which
  both are linear.
- Under **mod-2^n they do not unify**, and the failure is **localized to the
  dropped-carry boundary**: for n=16, ROTR_3 the discrepancy concentrates on
  bits {0,1,2,3} and {13,14,15} (the boundary bit 0/top and its rotated
  image), decaying 0.44 -> 0.22 -> 0.11 -- exactly the carry-chain reach
  probability from the boundary.

So the obstruction is one nameable feature: **the open top-bit boundary of
mod-2^n addition.** SHA uses mod-2^n (not Mersenne) precisely to break the
cyclic symmetry that would otherwise unify rotation and carry.

## Final crystallization: a characteristic conflict (CRT-orthogonality)

Each layer has a natural home ring:
- **boolean + rotation** -> product ring **F2^n** (char 2): XOR = +, AND = x
  (the ring product), ROTR = coordinate permutation. AND distributes over XOR
  (`a&(b^c) = (a&b)^(a&c)`), NOT over integer addition.
- **rotation + carry** -> **Mersenne ring Z/(2^n-1)** (ODD modulus, char
  coprime to 2): rotation = mult by unit, carry = +.

The two homes have **coprime characteristics (2 vs odd)** -- by CRT they are
orthogonal and cannot be fused into one ordinary ring of a single structure.
That is the precise, elementary form of the wall: not "three incompatible
operations" but **two rings of coprime characteristic, bridged only by the
mod-2^n carry boundary.** A genuine unifier must reconcile a char-2 structure
with an odd-characteristic one -- which is exactly what derived/prismatic
sites are built to do (glue across characteristics cohomologically), and
exactly where prismatic Thm 3.3 says the naive gluing is obstructed.

The search has therefore converted "something beyond understanding" into a
sharp statement: **unify F2^n (char 2) with Z/(2^n-1) (odd) across the mod-2^n
carry boundary.** Either a derived-prismatic object does it -- the new
language, the way past -- or the CRT-orthogonality is provably rigid, which is
itself the strongest possible structural security theorem for SHA-256. Both
outcomes are real results; neither is mysticism.

## The no-go, measured: ramification at 2 (`ramification_nogo.py`)

We measured the strength of the Frobenius-lift obstruction (prismatic
Thm 3.3 analog) rigorously. Rotation lives in the cyclic group C_n, whose
group algebra over F_2 is F_2[x]/(x^n - 1). A delta-structure (Frobenius
lift) exists cleanly iff this is **separable (etale) at 2**, i.e. iff
x^n - 1 is squarefree over F_2. The ramification index is e_2(n) = 2^{v_2(n)}
(verified by repeated square-roots: x^n-1 = (x^m-1)^{2^v}, m odd, x^m-1
squarefree).

```
   n        e=2^v     verdict
   odd        1       ETALE: Frobenius lifts -> rotation+carry UNIFY
   6,10,12    2..4    partially ramified
   16        16       totally ramified
   32        32       TOTALLY RAMIFIED   <== SHA-256 word size
   64        64       TOTALLY RAMIFIED   <== SHA-512 word size
```

**SHA's word sizes are powers of two (32 = 2^5, 64 = 2^6), so the rotation
group is MAXIMALLY ramified at the prime 2 -- exactly the prime where the
carry lives.** This is the precise, measured reason the unifying delta-ring
fails for SHA specifically: rotation (C_{2^k}) and carry (the 2-adic /
delta structure) are forced onto the *same* prime at its point of *maximal*
ramification. An odd word size, or a Mersenne (cyclic-carry) word, would be
etale -> the two structures would unify (and the design would lose the very
incompatibility that resists a single algebraic language).

So the obstruction is now a number, e_2(n), maximized by SHA's power-of-two
word size. The only conceivable "way past" is to *resolve* this ramification
-- a base change / cover / derived prismatic site where Frobenius lifts over
the ramified point. That resolution is genuine research-level prismatic
geometry, beyond elementary computation, but it is now a concrete, named
target rather than a mystery: **resolve the 2-ramification of C_{32} against
the 2-adic carry.**
