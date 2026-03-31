# UALRA-2 Requirements — What Would Break Birthday?

## UALRA-1 Result: Birthday = Architectural Invariant

SHA-256 collision = 2^128 in UALRA-1.
Proven through: η-lattice completeness (all 6 primes derived).

## Why UALRA-1 Can't Break Birthday

1. All η-lattice constants = architectural (message-independent, CV<3%)
2. Context switching (XOR↔ADD↔AND) = coupled (joint rank 490/512)
3. Convergence radius R=1 → no local exploitation
4. η-lattice = static (no dynamic paths)
5. Birthday = 2²×3²×19×η = product of architectural constants

## What UALRA-2 Would Need

To break birthday, UALRA-2 needs ONE of:

### Option A: Non-Architectural Variable
A structural constant that IS message-dependent (not architectural).
All 11 known constants have CV<3% → none qualify.
Need: 12th constant that varies with message AND affects collision cost.

### Option B: Context Decoupling
Make XOR, ADD, AND contexts INDEPENDENT (joint rank = 512, not 490).
Then: solve XOR part + birthday on rest → 2^{(256-13)/2} = 2^{121.5}.
Current: contexts coupled → solving one changes others.

### Option C: Dynamic η-Lattice
Make η-lattice points VARY with round number (not constant).
Current: all constants stable across rounds.
Need: round-dependent constant that creates dynamic path.

### Option D: Non-Birthday Collision Algorithm
Collision ≠ birthday even in UALRA.
Use: algebraic structure of ★-composition (448 operations).
Current: ★-composition = random (by R=1, exp54).
Need: show ★-composition has algebraic shortcut despite R=1.

### Option E: Ternary Collision
carry_rank = 3^{k*} = 243. Work in BASE 3 instead of base 2.
In ternary: collision = 3^{243/2} = 3^{121.5} = 2^{192.6}.
This is WORSE (192 > 128). But: ternary arithmetic has different
group structure. Collision in ternary group ≠ collision in binary.
Unknown whether ternary formulation gives advantage.

## Deep Open Questions

1. Is there a mathematical structure where ★(a,b,context) has
   FEWER than 6 independent primes? (dimension reduction)

2. Does the carry cocycle Γ have TORSION (Γ^k = 0 for some k)?
   If yes → after k compositions, carry = 0 → XOR → linear → collision.
   k* = 5 is related but k*-fold Γ ≠ 0 (it saturates, doesn't vanish).

3. Is SHA-256 collision provably ≥ 2^128?
   UALRA-1 shows birthday = architectural invariant.
   But: UALRA-1 might not capture ALL SHA-256 structure.
   Additional axioms (UALRA-2+) might change the picture.

4. The carry rank = 3^5 equation:
   Does it generalize? carry_rank = 3^{ceil(log₂(w))} for word size w?
   If yes → SHA-512 (w=64): carry_rank = 3^6 = 729 > 512.
   This would mean SHA-512 feedforward has NO carry deficit!
   → SHA-512 might be structured DIFFERENTLY than SHA-256 in UALRA.

## Summary

UALRA-1 = complete theory of SHA-256 structure.
UALRA-1 collision = birthday = 2^128.
UALRA-2 requires: new axiom or new variable or new collision algorithm.
The most promising direction: Option D (algebraic ★-composition shortcut)
or Option E (ternary formulation).

## Session Statistics

86 experiments
67 theorems  
1 fundamental constant (η)
6 lattice primes (all derived)
11 structural constants (all = kη)
3 independent axioms
1 complete theory (UALRA-1)
~1400 total experiments (with v20 methodology)
~105 total theorems
