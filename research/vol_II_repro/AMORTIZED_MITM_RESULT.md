# Amortized MITM and T_BARRIER_16 — a time-memory tradeoff, not a break

**Status: ⚡VER (gold-verified end-to-end on raw SHA-256). The headline number
is a TIME-MEMORY TRADEOFF; the total work (time-memory product) is unchanged,
and SHA-256 is NOT weakened.**

## Result

Building on the r=17 MITM (`MITM_r17_FINDING.md`), the 17-zero pairs it
produces are **amortized-cheap** (large lists of size n yield n²/2³² pairs at
~2n cost), and `delta_e_18` is **uniform** over those pairs. Therefore an
18-e-zero pair (`delta_e_2..18 = 0`) costs:

```
~2^33 TIME  +  2^32 MEMORY     (amortized MITM)
vs   2^64 TIME                  (T_BARRIER_16, П-15)
```

## Evidence

1. **Premise — `delta_e_18` uniform over MITM pairs** (`amortized_mitm.py`):
   62 pairs → 61 distinct; 252 pairs → 248 distinct; per-bit max|z| ≈ 2–3
   (RO noise); no value repeated > 2×.
2. **Scaling** (`scaling_demo.py`): max trailing-zeros of `delta_e_18` over N
   pairs tracks log₂(N) (N=56→7, N=258→7; the N=19→13 row is a verified tail
   fluke, not structure). Extrapolating, full `delta_e_18 = 0` needs ~2³²
   pairs ⇒ lists ~2³² ⇒ ~2³³ time, 2³² memory.
3. **Gold-verified end-to-end**: a MITM-found pair, run through *plain*
   hashlib-matching SHA-256 (raw e-registers, no differential logic), has
   `delta_e_2..17 = 0` and `delta_e_18 = 0xf4dca000` exactly as the
   differential predicted.

## The caveat that matters most

This is the standard **birthday ↔ MITM time-memory tradeoff**:

```
17 e-zeros:  2^32 time, O(1) mem   <->   2^16 time, 2^16 mem   (product 2^32)
18 e-zeros:  2^64 time, O(1) mem   <->   2^33 time, 2^32 mem   (product ~2^64)
```

The **time-memory product is preserved**. Against an attacker who charges for
memory, there is **no reduction in total work**. By the standard cryptanalytic
convention (memory counted cheap), 2³³ time is a legitimate improvement over
2⁶⁴ time, and it refutes П-27C's "MITM via parameter separation impossible" —
which is what made the methodology read 2⁶⁴ as a memoryless time bound.

## What it does NOT do

- It does **not** break SHA-256. `delta_e` zeros are *necessary, not
  sufficient* for a collision: the a-register difference stays saturated
  (HW≈16) and `W[16..63]` are schedule-fixed. The full-state/output coincidence
  needed for a collision remains **2^128** (`T_COLLISION_LOWER_BOUND_128`).
- It does **not** reduce total work — only shifts it from time into memory.

## Net correction to the program

The П-27C error ("MITM impossible") propagates one step: it makes
`T_BIRTHDAY_COST17` (2³²) and `T_BARRIER_16` (2⁶⁴) **time-memory tradeable**,
not fixed time bounds. Both should be restated as time-memory products. The
crack is otherwise local (barrier scan: `delta_e_18+` individually coupled,
no composition) and the global bound is untouched.

## The one frontier left (real (3))

A 2-list MITM can only trade time for memory; it cannot lower the **product**.
The only tool that could is a k-list / generalized-birthday (Wagner) algorithm,
which lowers the product for problems decomposing into k *independent* sums.
The barrier scan strongly suggests the nonlinear carry coupling forbids such a
decomposition for the joint (`delta_e_17, delta_e_18, ...`) condition — but that
is worth a direct k-group decomposition test rather than an assertion. Honest
prior: it will not reduce the product either, and the wall holds in the metric
that counts.
