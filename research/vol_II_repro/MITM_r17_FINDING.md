# A verified MITM split of the r=17 Wang barrier — and a correction to П-27C

**Status: ⚡VER (independently coded, 5/5 full-chain verified). Scope: local
barrier-crossing only. Does NOT break SHA-256.**

## The claim being corrected

`T_2D_BIRTHDAY_NEGATIVE` (П-27C, §II.4.10) tested whether the r=17 barrier
value `f17 = δe17 = Da13 + ΔW16` is additively separable over the pair
`(W0, W1)`, found 0/20 separable, and concluded:

> "MITM-атака через разделение параметров НЕВОЗМОЖНА."

The cost of the 17th zero was therefore taken as the birthday figure 2³²
(`T_BIRTHDAY_COST17`, П-27A).

## What is actually true

`W0` and `W1` are **shared** words: both feed `Da13` *and* `ΔW16`
(`ΔW16 = sig1(W14)+W9+sig0(W1)+W0` plus the chain corrections `dW9(W0..W8)`,
`dW14(W0..W13)`). A shared word is non-separable by construction, so П-27C
tested the one split guaranteed to fail.

Choosing words by **disjoint influence** instead, and measuring the
mixed second-difference per bit against a per-input random-oracle control
(Phase 8C rule), a clean split emerges:

- `W10` and `W11` are each **exactly** decoupled from `W14`: the mixed
  second-difference `B(a,c)−B(a,c')−B(a',c)+B(a',c')` is **0 on all 12000
  samples, all 32 bits** (z = −109.5 vs RO control z ≈ 2–3, Bonferroni
  threshold 3.75). Replicated on a second frozen frame (seed 999).
- Words `W2..W8` are only **low-bit** separable from `W14` (bits 0,1 biased
  at z ≈ −6..−9, still decisively beating RO, but high bits couple through
  the round-14 correction `dW14`).

So with all other free words frozen, the barrier is **exactly** additively
separable over the specific split `(W10,W11) | W14`:

```
δe17 = f(W10, W11) + g(W14)   (mod 2^32)
```

Verified: mixed second-difference = 0 for **0/3000** samples (exact identity,
not a statistical bias). Both sides have near-full value-entropy (~2^16
distinct values per 2^16 samples), so neither side is degenerate.

## The MITM and its verification

Separability ⇒ classic meet-in-the-middle on the 32-bit condition `f+g=0`:

```
build  L_A = { f(W10,W11) }            (vary W10,W11)
build  L_B = { -g(W14)    }            (vary W14)
match  L_A ∩ L_B  ⇒  δe17 = 0
```

Run with |L_A| = |L_B| = 2^17 (total ~2^18 chain-evals + a hash map):
**5 candidate δe17=0 found, 5/5 VERIFIED** by running the full Wang chain and
checking `δe2 .. δe17` are all zero.

**Gold-standard check** (`gold_verify.py`): for a MITM hit, reconstruct the
two actual 16-word messages, run the *plain* hashlib-matching SHA-256 on each
(no differential machinery at all), read raw e-registers — `δe2..δe17 = 0`,
all sixteen, confirmed. The pair is a genuine Wang 17-zero pair.

Cost to obtain one 17-zero pair: lists of size ~2^16 (hits ≈ n²/2^32 ≈ 1),
i.e. **~2^16–2^17 work with ~2^16 memory**, against the methodology's stated
**2^32** (`T_BIRTHDAY_COST17`) and П-97's ~2^33 brute-force search for "the
first Wang pair". A ~2^15 time speedup via a standard time–memory tradeoff.
Robustness: **6/8 random frames** yield a gold-verified 17-zero pair at only
2^16 lists (the 2 misses are the expected Poisson(1) zeros, not failures).

## What this is — and is NOT

- **IS**: a verified counterexample to the *conclusion* of П-27C. The 17th
  Wang zero is reachable by MITM far below 2^32. П-27C's specific datum
  (W0,W1 not separable) is correct; the generalization "MITM impossible" is
  not.
- **IS**: a reusable methodological lesson — separability must be probed over
  **disjoint-influence** word splits, derived from the influence map, not
  over arbitrary or shared pairs. The same probe should be re-run on every
  barrier whose decomposition is additive (e.g. De18 = Da14 + ΔW17).
- **IS NOT** a break of SHA-256. This is a *local* improvement on crossing one
  barrier in the e-differential. It does not propagate past r=17: the
  a-register difference is saturated (HW≈16) and W[16..63] are schedule-fixed,
  so the deterministic control still ends at 16 e-zeros. The full-collision
  bound (2^128, `T_COLLISION_LOWER_BOUND_128`) is untouched.

## Honest open question this raises

Does the same disjoint-influence MITM apply one step further —
`δe18 = Da14 + ΔW17` — and can the two MITM layers be *chained* (meet at
state[16], as the unverified "MITM through state[16] = 2^80" gestured at)?
П-27C also dismissed this via the wrong pair. Re-testing `δe18` separability
over a disjoint-influence split is the concrete next probe. If two layers
compose, the cost question past r=17 genuinely reopens. If they don't (the
shared-word coupling at W0,W1,W9 likely blocks composition), the barrier
holds and we have, at minimum, corrected the record.
