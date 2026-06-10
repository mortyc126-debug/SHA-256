# (1) Systematic barrier scan — is the П-27C oversight systematic? NO.

Re-tested the methodology's barrier-cost claims with the disjoint-influence
split that cracked r=17. Goal: find out whether other "barrier = 2^N" claims
hide the same crack, or whether r=17 was a one-off.

## Results (`probe_barriers.py`, RO-controlled)

Influence maps (which free words move `delta_e_r`):

```
delta_e_17: inert {12,13,15}   <- W14 active and feeds ONLY ΔW16
delta_e_18: inert {}  (all 16 words active)
delta_e_19: inert {}  (all 16 words active)
delta_e_20: inert {}  (all 16 words active)
```

Single-barrier exact separability over the analytic disjoint split:

```
barrier   split           frac_zero   max|z|   RO frac_zero   verdict
de17      (W10,W11 | W14)    1.000      54.8       0.000      SEPARABLE -> MITM 2^16
de18      (W11,W12 | W15)    0.000       2.3       0.000      coupled (RO noise)
de19      (W11,W12 | W13)    0.000       2.6       0.000      coupled
de20      (W10,W11 | W13)    0.000       2.4       0.000      coupled
```

Joint composition (does one split serve two consecutive barriers?):

```
barriers (17,18)     joint_zero = 0.000   -> does NOT compose
barriers (18,19)     joint_zero = 0.000   -> does NOT compose
barriers (17,18,19)  joint_zero = 0.000   -> does NOT compose
```

## Conclusion: the crack is confined to exactly ONE barrier

The disjoint-influence MITM applies to **delta_e_17 only**. The reason is
sharp and structural: among the 16 free message words, **W14 is the unique
word that feeds only the schedule term ΔW16 and not the carry term Da13**
(it enters at round 14, after Da13 is fixed; and ΔW16's formula
`sig1(W14)+W9+sig0(W1)+W0` contains it). That single clean lever is what
makes delta_e_17 additively separable and MITM-able.

From delta_e_18 onward there is **no such lever**: every free word is active
(no inert words), and the analytic late-word candidate (W15) does NOT
separate the barrier (frac_zero 0.000, at RO noise). The earlier
decomposition `delta_e_18 = Da14 + ΔW17` holds only *conditioned on*
delta_e_17 = 0, and unconditioned the word influences are fully entangled.

**Prediction scorecard (honest):** predicted de18 would crack alone via W15
— it did NOT. The crack is even more local than expected: a single-barrier,
single-lever phenomenon. The methodology's T_2D_BIRTHDAY_NEGATIVE oversight
was a **one-off**, not systematic.

## Net effect on the program

- Corrected: the cost of the **first** 17-zero barrier (2^32 -> ~2^16-2^17
  MITM), and П-27C's over-broad "MITM impossible".
- Unchanged and reconfirmed: T_BARRIER_16 = 2^64 (no composition), all
  barriers delta_e_18+ (coupled), and the global collision bound 2^128.

The 2-list meet-in-the-middle is exhausted here: a single bipartition cannot
serve two coupled barriers. Beating the next wall, if possible at all, needs
a k-list / generalized-birthday (Wagner) approach that does not rely on one
clean split — the natural next direction.
