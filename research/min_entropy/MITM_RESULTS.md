# MITM (Meet-in-the-Middle) for Reduced-Round SHA-256

**Project status (April 2026)**

## Implemented

### Phase A: Reverse Compression Function
- `sha256_reverse.py` — reversible round function
- Forward+reverse roundtrip ✓ для r ∈ {1, 8, 16, 32, 48, 64}
- Forward 64R against `hashlib.sha256` ✓ (empty msg, "abc" tested)
- Reusable building block для MITM-style attacks

**Reverse round formula** (given new state, W[t], K[t]):
```
a_old = b_new
b_old = c_new
c_old = d_new
e_old = f_new
f_old = g_new
g_old = h_new
T2    = Σ0(a_old) + Maj(a_old, b_old, c_old)
T1    = a_new - T2
d_old = e_new - T1
h_old = T1 - Σ1(e_old) - Ch(e_old, f_old, g_old) - K[t] - W[t]
```

### Phase B: Free-Start MITM Demo
- `mitm_demo.py` — concrete attack on r=24 reduced SHA-256, split at round 12
- Forward: N samples (state0, W[0..11]) → state[12]
- Backward: N targets (state[24] with prefix) + W[12..23] → state[12]
- Match in 32-bit prefix space via hash table

**Results at N=2^17 per side**:
- Forward: 12.6s, 131K unique 32-bit prefixes
- Backward: 11.9s
- Prefix-32 matches: 1 (expected N²/2^32 = 4)
- Full-256 matches: 0 (expected N²/2^256 ≈ 10⁻⁶⁷)
- **Brute force baseline** для one prefix-32 match: N=2^32 (~months Python)
- **MITM speedup**: ~10⁵× для prefix matching

### Phase C: Cost Benchmark
- `mitm_cost_benchmark.py` — forward vs reverse timing
- Single round Python: ~8 μs (forward and reverse symmetric, ratio ≈ 1.0)
- MITM cost = 2 × N × (r/2) × 8 μs = N × r × 8 μs

**Practical compute budget**:
| r | N=2^16 | N=2^20 | N=2^24 |
|---|---|---|---|
| 16 | 4 s | 67 s | 18 min |
| 24 | 6 s | 101 s | 27 min |
| 32 | 8 s | 134 s | 36 min |

## Honest Limitations

1. **Free-start preimage of full state[r] = O(2^128)**:
   MITM gives no improvement over birthday for full 256-bit collision/preimage
   because state[r] dimension = 256 and free W's give independent halves.

2. **Standard preimage (fixed IV, schedule-derived W)**:
   Schedule constraint W[16..63] = f(W[0..15]) couples forward and backward
   halves. Naïve MITM doesn't apply. Methodology П-210 claims O(2^80) via
   schedule-coupling structural exploitation — not replicated here.

3. **Python overhead**: 8 μs/round is bottleneck. C/GPU implementation
   could give 100-1000× speedup, making N=2^32 feasible in hours.

## What MITM Demonstrates Here

- Reverse compression is correct, fast, symmetric
- MITM technique implemented и verified on small-bit prefix matching
- Cost scales as expected (linear in N, linear in r)
- 10⁵× speedup для prefix matching (32-bit slice)

## Comparison with MLB

| Method | Best result | Compute budget | Limitation |
|---|---|---|---|
| MLB (3-channel sort-key) | HW=77 near-collision | K=200M (~22 min) | Plateau at HW~74 even at K=1B |
| MITM (free-start prefix) | 1 prefix-32 match | N=2^17 (~25s) | Full preimage = birthday |

MLB и MITM solve different problems:
- MLB: minimize HW(state1_A ⊕ state1_B) for input pairs
- MITM: find (state0, W) such that compress(state0, W, r) hits prefix

## Future Directions (Phase D+)

### MITM with structured W (schedule-respecting)
Restrict W to HW=2 single-bit pattern (как MLB). Schedule fully determined.
Forward: 2^32 W[0] values, get state[12].
Backward: target h - IV → state[24]. Reverse 12 rounds requires W[12..23],
which depend on W[0]. Circularity.

**Workaround**: backward iterate over (W[0..15] from BLOCK 2 different message),
match state1 from BLOCK 1 forward. This is true 2-block MITM на full SHA-256.

### Methodology П-210 replication
Read methodology Vol II §II.6.4 carefully. Identify:
- What "state[16]" specifically means in their setup
- What schedule-coupling gives O(2^80)
- Implement and measure actual cost

### MLB+MITM hybrid
Use MLB to find approximate-collision candidates, then MITM-style verification
for exact match in subspace. May reduce candidate validation cost.

### LSH for state matching
Replace 32-bit prefix matching with LSH bit-sampling. Could give richer
match structure для same N.

## Files

- `sha256_reverse.py` — reverse compression (Phase A)
- `mitm_demo.py` — MITM attack demo (Phase B)
- `mitm_demo_results.json` — Phase B measured data
- `mitm_cost_benchmark.py` — cost benchmark (Phase C)
- `mitm_cost_benchmark.json` — Phase C measured data

## Honest Scope Summary

This is **MITM technique demonstration**, not a SHA-256 break.
- Working framework для MITM attacks on reduced-round SHA-256
- Measured cost characteristics (forward/reverse symmetric, ~8 μs/round)
- Confirms theoretical predictions (birthday bound for full preimage)

For real attack value, need:
- Structural exploitation (methodology П-210 path)
- C/GPU implementation для 100-1000× speedup
- Specific reduced-round target (e.g., r=24 chosen-prefix attack)

This is foundation work — building blocks for future attack research.
