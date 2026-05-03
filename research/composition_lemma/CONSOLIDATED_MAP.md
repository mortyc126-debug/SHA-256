# Composition Lemma Program — Comprehensive Map (Sessions 13-37)

**Дата**: 2026-04-27
**Цель**: отдалённый взгляд на всю работу + методичку, выявить пропущенные связи, найти неисследованную territory.

---

## Часть I. Что мы установили (Sessions 13-37)

### Структурные теоремы (наш вклад)

1. **Register-Position Theorem (Sessions 18-22)**: SFS k-round collision via adaptive δW for single-bit flip iff
   ```
   k_min(r) = max(3, pos(r) + 1)
   ```
   где pos(h)=0, pos(g)=1, ..., pos(a)=7.
   - h-flip: k=1 (immediate, δW=δh точно cancels)
   - f, g flip: k=3
   - e flip: k=4
   - d flip: k=5
   - c flip: k=6
   - b, a flip: k=7, 8

2. **IV-Independence (Session 23)**: theorem holds for ALL 2^256 IVs.

3. **Schedule UNSAT (Session 24)**: trivial 64-round extension formally blocked z3.

4. **DM Preservation Impossible (Session 26)**: state diff = input diff не возможно at small k.

5. **Adjacent-Bit Carry Cancellation (Sessions 35-36)**: δW = bits (30, 31) at W[0] gives mean HW(δstate) = 84.79 at T=4 (vs random 128, 5σ effect). Persists T ≤ 4-5, then random.

6. **Single-bit δW comprehensive UNSAT map (Sessions 29-30)**:
   - T=5: ALL UNSAT formally (W[0..4] all bits)
   - T=6: 30/32 bits в W[1] UNSAT formal; W[0] TIMEOUT
   - W[2..5] all UNSAT

### Закрытые направления (negative)

- Path-bit conservation (методичка §94.5: refuted at R=2)
- Maj-noise cancellation via δW (only Ch-side controllable)
- Wang barrier r=17 hard limit для δe=0
- Internal differential SHA-2 quasi-period (Session 34)
- Higher HW patterns (HW=3, 4) **не лучше** HW=2 adjacent
- HW=2 absorption via simple adaptive δW (Session 37)

### Z3 практический предел

- T ≤ 4-5 для most decision targets
- T=6 boundary (z3 timeout 30-180s)
- T ≥ 8 uniformly TIMEOUT

---

## Часть II. Что зафиксировано в методичке (контекст)

### Структурные facts (могут быть leveraged)

| # | Theorem / Fact | Detail | Used? |
|---|---|---|---|
| 1 | **τ★ = 4** (★-Algebra) | mixing time, carry depth | Implicitly (matches our Session 36 carry-cancel τ=4) |
| 2 | **Theorem 28.1**: density saturation **0.5156** (NOT 0.5) | T=11 ANF density | Not directly leveraged |
| 3 | **Theorem 49.1-2**: noise floor **1.08% per state** | quadratic noise irreducible | Not leveraged |
| 4 | **Theorem 47.1**: orbit gzip = **0.328** | structural redundancy | Not leveraged |
| 5 | **Lucas-XOR**: nilp(Σ_1)=**11** vs nilp(Σ_0)=**32** | huge asymmetry | Mentioned but not explored |
| 6 | **T_INFO_BARRIER_R1**: MI(W; e_1) = **2.5 bit** | round 1 already kills info | Not leveraged |
| 7 | **Carry-rank 589/592** | 3-bit kernel deficit | Not leveraged |
| 8 | **T_DOUBLE_BARRIER**: r=17 AND r=21 | second barrier at 21 | Not explored |
| 9 | **OTOC SHA-2 family scramble at r=24** | invariant SHA-256/512 | Why r=24 specifically? |
| 10 | **T_PHI_FIBRES**: ~19 inputs per carry-profile | state partition | Not used |
| 11 | **Theorem 33.1**: deg((x+y)_i) = i+1 | carry degree law | Used implicitly |
| 12 | **§132 ANF early-verify 7.6×** | first backward shortcut | Not connected |
| 13 | **Wang pair W0=c97624c6** | concrete attack data | Not extended |

### Open questions in methodology (potentially actionable)

- **Q_LIFTED_POLY** (§II.3): explicit polynomial form of De17 в W[0..15] over Z. Would give closed form, possibly linearizable.
- **Q_NEUTRAL_TREE** (v12+): full search tree of Wang neutral bits. Steps 11, 25 (Σ1 positions) — neutral bits exist?
- **Q1, Q2, Q3 v9**: HW propagation analytics not done.
- **Signal block-2 amplification mechanism** (§III.4.4 IT-4.S4): mechanism studied but not exploited.

---

## Часть III. Connections we found between our findings + methodology

### ✓ Confirmed connections

1. **τ★=4 ↔ adjacent-bit carry-cancel (T=4)**: ★-Algebra mixing time matches our finding that adjacent bit pair structural advantage dies at T=4-5.

2. **Theorem 28.1 (0.5156 density) ↔ Том III χ²-fingerprint (z=-2.5)**: same phenomenon at different orders. Both measure non-uniformity.

3. **Theorem 67.1 ↔ Sessions 13a-b (8-register chain)**: we generalized. Per-bit MSB transitions deterministic only in XOR-trail (additive carry overflow at MSB).

### ⊘ Disconnections (we found, not in methodology)

- Adjacent-bit (30, 31) at W[0] specifically — not in methodology directly
- IV-independence theorem — generalizes Session 21 but with corrected formula
- Schedule UNSAT formal proof — concrete formal block

---

## Часть IV. Genuinely missed directions / splinters

### (M1) Lucas-XOR asymmetry exploitation

**Methodology**: Σ_1 nilp=11 vs Σ_0 nilp=32. Massive asymmetry never directly attacked.

**Hypothesis**: trail through Σ_1-dominated component cycles faster (period 11) vs Σ_0 (period 32). Periodic structures in 64-round SHA might align with these periods.

**Concrete experiment**: measure state evolution along Σ_1 vs Σ_0 axes separately. Does period 11 (Σ_1 reset point) give state structural similarity?

**Status**: not tried.

### (M2) Carry kernel 3-dim exit holes

**Methodology**: rank(carry) = 589/592 → 3-dim kernel.

**Hypothesis**: 3-dim subspace where carry mapping is degenerate. Inputs hitting this subspace might give predictable carry → controllable trail extensions.

**Concrete experiment**: extract this 3-dim kernel explicitly. Test if specific message patterns project into it. If yes, those messages might give better-than-random differential probabilities.

**Status**: methodology has carry analysis but exit holes not extracted.

### (M3) T_DOUBLE_BARRIER r=21 second wall

**Methodology**: barriers at r=17 AND r=21. We studied r=17. r=21 = one of Φ-free rounds.

**Hypothesis**: r=21 wall has different structure than r=17. Differential trails may behave differently at r=21.

**Concrete experiment**: replicate trail search structure between r=17 and r=21, see if specific patterns survive specifically through r=18..21.

**Status**: not explored.

### (M4) OTOC scramble at r=24 — algebraic explanation

**Methodology**: SHA-2 family scrambles at exactly r=24, regardless of word size.

**Hypothesis**: r=24 corresponds to specific algebraic event (e.g., orbit of round operator hits identity component for first time).

**Concrete experiment**: compute round-operator orbits (in some specific subspace) and check if r=24 corresponds to specific algebraic milestone.

**Status**: empirical fact, no analytical explanation.

### (M5) Q_LIFTED_POLY: explicit polynomial De17 in W

**Methodology**: open question. Express De17 as explicit polynomial over Z in W[0..15]. Maybe linearizable.

**Concrete experiment**: use Sympy to symbolically compute De17 as polynomial. If degree is bounded → closed-form analysis. If high — confirms previously believed.

**Status**: methodology open, not attempted.

### (M6) Multi-block dynamics

**Methodology**: T_MULTIBLOCK_PREDICT ✗NEG (predict_delta doesn't generalize across blocks).

**Status**: closed for SAME differential. But multi-block FOR COLLISION (Mendel 2-block style) is the real attack mode и closer connected to our findings.

**Concrete experiment**: implement 2-block search via z3 — first block produces specific intermediate state, second block uses theorem to absorb.

**Status**: discussed but not coded.

### (M7) Truncated hash collision (k=64 bit output)

**Hypothesis**: SHA-256 truncated to 64 bits has birthday cost 2^32. SAT might find collision much easier than full 256.

**Concrete experiment**: same z3 setup, target only first 64 bits of state diff = 0 (instead of all 256).

**Status**: not tried.

### (M8) §132 ANF early-verify 7.6× backward shortcut + our forward analysis

**Methodology**: §132 ANF early-verify gives 7.6× cumulative speedup для INVERSION (preimage). Our work focuses on collision (forward direction).

**Hypothesis**: §132 ANF mechanism может also help collision via SHARED ANF degree saturation argument.

**Concrete experiment**: integrate §132 ANF approach into our z3 trail search. Maybe ANF-aware encoding gives extension.

**Status**: not tried.

---

## Часть V. Recommended next direction

Из 8 missed directions, наиболее productive для session-level work:

**Priority 1**: (M2) **Carry kernel 3-dim exit holes** — concrete computation, manageable scope, может connect to multiple findings.

**Priority 2**: (M7) **Truncated hash collision** — z3-tractable, gives concrete result, useful baseline.

**Priority 3**: (M5) **Q_LIFTED_POLY** explicit polynomial form — analytic, не SAT-bound.

**Priority 4**: (M1) **Lucas-XOR asymmetry** — period 11 vs 32 exploitation experiment.

**Priority 5**: (M4) **r=24 algebraic explanation** — connects OTOC + Lie algebra structure.

---

## Часть VI. Honest meta-assessment

**После 37 sessions:**

- Structural map очень comprehensive. Multiple formal theorems и UNSAT proofs.
- Никакой attack на full SHA-256 (Composition Lemma intact).
- z3 vanilla limit: T≤5-6 for decision targets.
- Real attacks (EUROCRYPT 2024-2026: 31-37 steps) require specialized SAT.

**Pattern: forward motion productive but bounded by tooling**.

8 missed directions выше — largely structural/analytic, не SAT-search-bound. Therefore session-level achievable.

**Most exciting is (M2)** — carry kernel 3-dim exit holes. It's a concrete number (3) with concrete kernel that we could extract. May reveal structural attack handle.

Если согласен — переходим к (M2).
