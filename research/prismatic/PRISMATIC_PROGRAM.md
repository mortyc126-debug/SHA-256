# Prismatic Program for SHA-256: Consolidation

**Session 16 (2026-04): formal consolidation of Sessions 1-15**
**Session 22 (2026-04): updated with Sessions 18-21 theorems — SHA Lie algebra**

---

## Abstract

We attempt to apply the prismatic cohomology framework (Bhatt–Scholze 2019) to the cryptographic hash function SHA-256. Over 21 incremental sessions, we establish:

1. A δ-ring framework centered on Z_2 with truncation to Z/2^n = W_n(F_2).
2. An exact formula for the δ-discrepancy of bitwise XOR: `δ(x⊕y) = δ(x) + δ(y) - xy + 2z(x+y) - 2δ(z) - 3z²` where z = x ∧ y.
3. Two valid prisms for p=2: the crystalline prism (Z_2, (2)) and the q-de Rham prism (Z_2[[q-1]], (1+q)).
4. An obstruction theorem: Z_2[i] (= Z_2[ζ_4]) does not admit a δ-structure lifting Frobenius from F_2[i].
5. A concrete cohomology theorem: for R_d = F_2[s]/(s^d), the de Rham cohomology H^1_{dR}(R_d) = ⊕_{k odd, 1≤k≤d-1} Z/2^{v_2(k+1)}, with total order 2^{d-1} for d = 2^j.
6. Explicit matrices for SHA-256's Σ_0 and Σ_1 as linear operators on H^1(F_2[s]/(s^{32})).
7. A 2-dimensional joint invariant subspace of Σ_0 and Σ_1 on H^1 over F_2.
8. **(NEW)** A genuinely non-abelian Lie algebra framework L_SHA for SHA operators. Rotation-only sub-algebra is abelian (Theorem 18.1); including σ operators (with SHR) gives non-abelian (18.2), non-nilpotent (19.1), **non-solvable** (20.1) Lie algebra.
9. **(NEW)** L_SHA contains a **perfect sub-algebra of dimension 264** inside sl_{32}(F_2), with trivial center and reducible 32-dim representation (Session 21).

The work does **not** constitute a cryptanalytic attack on SHA-256. The 2^{120} classes captured by rotation cohomology (after Künneth for 8 registers) fall short of the 2^{128} birthday bound, and the operations XOR, AND, ADD are not fully integrated into the framework. The non-solvability of L_SHA suggests SHA's linear layer has rich Lie-theoretic structure (supporting security rather than providing attack handle). We document limitations and concrete directions for further work.

---

## Part I: Foundations

### 1.1 δ-Rings (Joyal 1985)

For a prime p (here p = 2), a **δ-ring** is a pair (A, δ) where A is a commutative ring and δ: A → A satisfies:

- (D1) δ(0) = δ(1) = 0
- (D2) δ(x+y) = δ(x) + δ(y) − Σ_{i=1}^{p-1} (C(p,i)/p)·x^i y^{p-i}.  For p=2: δ(x+y) = δ(x) + δ(y) − xy
- (D3) δ(xy) = x^p·δ(y) + y^p·δ(x) + p·δ(x)·δ(y).  For p=2: δ(xy) = x²δ(y) + y²δ(x) + 2δ(x)δ(y)

Equivalently, the map φ(x) := x^p + p·δ(x) is a ring homomorphism lifting Frobenius x ↦ x^p on A/pA.

**Standard example**: Z_p with δ(x) = (x - x^p)/p, φ = identity.

### 1.2 Truncation framework (Session 5-6 correction)

**Lemma (Kedlaya 2.2.6)**: If (A, δ) is a δ-ring and p^n = 0 in A, then A = 0.

**Consequence**: Z/p^n does **not** support a δ-ring structure as an endomap.

Instead, δ on Z_2 descends to a map Z/2^n → Z/2^{n-1} (truncation). For x ∈ Z_2, δ(x) modulo 2^{n-1} depends only on x modulo 2^n. Verified numerically for n = 4, 8, 16, 32.

### 1.3 Boolean ring triviality

**Observation**: F_2[t]/(t² - t) (Boolean ring) has every element 2-torsion. By Kedlaya 2.2.6, any δ-ring structure forces the ring to be zero. Hence the Boolean ring admits only the trivial δ-structure.

**Consequence**: naive attempts to apply prismatic cohomology directly to Boolean function rings are trivial. Must use ring lifts in characteristic 0 (Z_2-algebras).

---

## Part II: δ-structure computations

### 2.1 Explicit formula for δ(z) over Z

**Theorem 2.1**: For z ∈ Z with binary expansion z = Σ z_i · 2^i (z_i ∈ {0,1}),
$$\delta(z) = \sum_{i\ge 1} 2^{i-1}(1 - 2^i)\,z_i - \sum_{i<j} 2^{i+j} z_i z_j$$

The formula is **quadratic** in z-bits as a polynomial over Z. Verified exactly for z ∈ [0, 32).

**Proof**: Expand z² = (Σ 2^i z_i)² = Σ 2^{2i} z_i² + 2·Σ_{i<j} 2^{i+j} z_i z_j. Using z_i² = z_i (Boolean), obtain z - z² = Σ(2^i - 2^{2i})z_i - 2·Σ_{i<j}2^{i+j}z_iz_j. Divide by 2. ∎

### 2.2 XOR discrepancy formula (Session 2)

**Theorem 2.2**: For x, y ∈ Z_2 with z = x ∧ y (bitwise),
$$\delta(x \oplus y) = \delta(x) + \delta(y) - xy + 2z(x+y) - 2\delta(z) - 3z^2$$

**Proof**: Use identity x ⊕ y = (x + y) − 2(x ∧ y) and apply D2 recursively:
δ(x+y) = δ(x) + δ(y) − xy (by D2)
δ(2z) = δ(z+z) = 2δ(z) − z² (by D2)
δ(−2z) = −δ(2z) − (2z)² = −2δ(z) + z² − 4z² = −2δ(z) − 3z²
δ(x+y−2z) = δ(x+y) + δ(−2z) − (x+y)(−2z) = δ(x+y) + δ(−2z) + 2z(x+y)
Substitute and simplify. ∎

Verified exactly for all (x, y) ∈ [0, 2^n)² with n = 4, 6, 8, 10.

### 2.3 AND bit-level structure (Sessions 3-4)

δ(x ∧ y) is **not** expressible as a low-degree polynomial in (x, y, δ(x), δ(y)) — verified by rank deficiency for polynomial fits up to degree 3.

However, bit-by-bit ANF has controlled complexity:

**Theorem 2.3**: Output bit k of δ(x ∧ y) mod 2^{n-1} has ANF degree exactly **2(k+1)** in (x_0,...,x_{n-1}, y_0,...,y_{n-1}), with only even-degree terms.

**Proof sketch**: δ(x ∧ y) = δ of quadratic polynomial in (x_i y_i) by Theorem 2.1. Bit k mod 2^{n-1} depends on lower bits through a carry cascade of depth k+1, each cascade adding degree 2. In z-variables, bit k has ANF degree k+1; substituting z_i = x_i y_i doubles. ∎

---

## Part III: Prisms

### 3.1 Definition (Bhatt-Scholze)

A **prism** is a pair (A, I) where:
- A is a δ-ring
- I ⊂ A is an invertible (locally principal) ideal
- A is (p, I)-adically complete
- I is **distinguished**: there exists a generator d ∈ I with δ(d) ∈ A^× (unit)

### 3.2 Crystalline prism (Z_2, (2)) (Session 6)

**Theorem 3.1**: (Z_2, (2)) is a valid prism.

**Verification**:
- Z_2 is the standard δ-ring (δ(x) = (x − x²)/2, φ = identity)
- (2) is principal
- Z_2 is 2-adically complete
- δ(2) = (2 − 4)/2 = −1 ∈ Z_2^× (distinguished)

**Feature**: φ = identity on Z_2 ⇒ Frobenius action is trivial. No exploitation of Frobenius on this prism.

### 3.3 q-de Rham prism (Z_2[[q-1]], (1+q)) (Session 7)

**Theorem 3.2**: (Z_2[[q-1]], (1+q)) is a valid prism with non-trivial Frobenius.

**Construction**:
- A = Z_2[[q-1]] (formal power series in (q-1))
- δ-structure via φ(q) = q² (q-Frobenius), giving δ(q) = 0
- I = (1+q) = (2 + (q-1))
- δ(1+q) = δ(1) + δ(q) − 1·q = −q, which is a unit in A (constant term −1 is odd)

**Feature**: φ(q) = q² is non-trivial Frobenius, giving richer structure than crystalline prism.

### 3.4 Obstruction theorem for ramified cyclotomic (Session 8)

**Theorem 3.3**: Z_2[i] (= Z_2[T]/(T²+1) = Z_2[ζ_4]) does **not** admit a δ-structure lifting the Frobenius x ↦ x² on F_2[i] = Z_2[i]/(2).

**Proof**: Any Frobenius lift must satisfy φ(i)² = φ(i²) = −1, so φ(i) ∈ {±i}.
- For φ(i) = i: δ(i) = (i − i²)/2 = (1+i)/2
- For φ(i) = −i: δ(i) = (−i − i²)/2 = (1−i)/2

Both require (1 ± i)/2 ∈ Z_2[i]. But in Z_2[i]:
- 2 = −i·(1+i)² (ramification)
- Uniformizer is π = 1+i with π² = 2i = (unit)·2
- Element (1 ± i) = π·(unit) has exactly **one** factor of π, not two
- Hence (1 ± i) is not divisible by 2 in Z_2[i] ∎

**Consequence**: the natural path "rotations as ζ_n-multiplication in Z_2[ζ_n]" fails at the smallest case. Ramified cyclotomic extensions require either perfectoid completion or absolute prismatic site framework.

---

## Part IV: Cohomology

### 4.1 de Rham cohomology of dual numbers (Session 9)

**Proposition 4.1**: For R = F_2[ε]/(ε²) with lift R̃ = Z_2[ε]/(ε²):
- R̃ is a δ-ring with φ(ε) = 0 (verified D1-D3)
- Ω^1_{R̃/Z_2} ≅ Z_2 ⊕ F_2 (with basis {dε, ε dε} mod relation 2ε dε = 0)
- H^0_{dR}(R) = Z_2
- H^1_{dR}(R) = F_2 (generator ε dε mod Im d)
- H^i_{dR}(R) = 0 for i ≥ 2

### 4.2 Main cohomology theorem (Session 10)

**Theorem 4.2 (Main)**: For R_d = F_2[s]/(s^d) over Z_2:
$$H^1_{dR}(R_d) = \bigoplus_{k=1,3,5,\ldots,d-1} \mathbb{Z}/2^{v_2(k+1)}$$

For d = 2^j: **|H^1(R_d)| = 2^{d-1}**.

**Proof**:
- R̃_d = Z_2[s]/(s^d) with Z_2-basis {1, s, ..., s^{d-1}}
- Kähler differentials: Ω^1 = R̃_d · ds modulo relation d(s^d) = 0, i.e., d·s^{d-1}·ds = 0
- As Z_2-module: Ω^1 = ⊕_{k=0}^{d-2} Z_2·s^k ds ⊕ (Z/d)·s^{d-1} ds
- Differential: d(s^k) = k·s^{k-1}·ds, so Im(d) at position k contributes (k+1)·Z_2
- H^1 at position k: Z_2/(k+1)Z_2 = Z/2^{v_2(k+1)} for k < d-1
- H^1 at position d-1: Z/2^{v_2(d)}

For d = 2^j, position d-1 is odd (since d even), contributing Z/2^j. Sum over all odd k in [1, d-1] gives total exponent Σ v_2(k+1) = d/2 + v_2((d/2)!) = d/2 + (d/2 − 1) = d − 1 by Legendre. ∎

**Verified** for d = 2, 4, 8, 16, 32.

### 4.3 Multi-register Künneth (Session 11)

**Corollary 4.3**: For the rotation ring R = F_2[s]/(s^d) and n-fold tensor product R^{⊗n}:
$$H^1(R^{\otimes n}) = n \cdot H^1(R)$$
(direct sum of n copies).

For SHA-256 (d=32, n=8): |H^1| = (2^{31})^8 = **2^{248}**.

---

## Part V: SHA-256 specific computations

### 5.1 Correct rotation ring (Session 12)

For an n-bit register with cyclic rotation action, the correct ring is the **group algebra**:
$$F_2[\mathbb{Z}/n] = F_2[x]/(x^n - 1)$$

For n = 2^k, x^n - 1 = (x+1)^n in F_2, hence F_2[x]/(x^n - 1) = F_2[s]/(s^n) via s = x+1.

For SHA-256 (n = 32): rotation ring = **F_2[s]/(s^{32})**, applying Theorem 4.2 with d = 32.

### 5.2 ROTR_1 theorem (Session 13)

**Theorem 5.1**: Multiplication by (1+s) = ROTR_1 acts as **identity** on H^1(F_2[s]/(s^n)) for any n = 2^k. More generally, ROTR_r = mult by (1+s)^r acts as identity ⇔ r = 1.

**Proof**: (1+s) · [s^k·ds] = [s^k·ds] + [s^{k+1}·ds]. For k odd (H^1 generator), k+1 is even, so position k+1 contributes Z/2^{v_2(k+2)} = Z/2^0 = 0 in H^1. Hence action = identity.

For r > 1, (1+s)^r expands by Lucas's theorem:
$$(1+s)^r = \sum_{\text{bin}(i) \subseteq \text{bin}(r)} s^i$$
Action on [s^k·ds] sends to sum over i ⊆ r; for identity need all non-zero i ⊂ r odd, which forces r = 1. ∎

**SHA-256 relevance**: all SHA rotations (r ∈ {2,6,7,11,13,17,18,19,22,25}) satisfy r ≥ 2, hence all act non-trivially on H^1.

### 5.3 Σ_0 and Σ_1 matrices (Sessions 14-15)

SHA-256:
- Σ_0 = ROTR_2 ⊕ ROTR_{13} ⊕ ROTR_{22}
- Σ_1 = ROTR_6 ⊕ ROTR_{11} ⊕ ROTR_{25}

As Z_2-linear operators on R = F_2[s]/(s^{32}):
- Σ_0 polynomial (via Lucas + XOR): `1 + s + s^5 + s^6 + s^8 + s^9 + s^{12} + s^{13} + s^{16} + s^{18} + s^{20} + s^{22}`
- Σ_1 polynomial: positions {0, 3, 4, 6, 10, 11, 16, 17, 24, 25}

Even shifts relevant for H^1 action:
- Σ_0: {0, 6, 8, 12, 16, 18, 20, 22}
- Σ_1: {0, 4, 6, 10, 16, 24}

**Theorem 5.2**: Both Σ_0 and Σ_1 are **upper triangular unipotent** 16×16 matrices over F_2 on H^1(F_2[s]/(s^{32})), each of order 16 (as Σ^{16} = I mod 2).

### 5.4 Joint invariants (Session 15)

**Theorem 5.3**: Ker(Σ_0 − I) ∩ Ker(Σ_1 − I) on H^1(F_2[s]/(s^{32})) over F_2 is **2-dimensional**, generated by:
- [s^{29}·ds]
- [s^{31}·ds]

As Z_2-modules: joint invariant group is Z/2 ⊕ Z/32, total order **64**.

**Structural reason**: min shifts are 6 (for Σ_0) and 4 (for Σ_1). Positions k ≥ 28 odd (i.e., 29 and 31) are beyond shift reach of both operators, hence fixed.

---

## Part VI: SHA Lie algebra (Sessions 18-21)

Shifting framework from H^1 cohomology (Part V) to **Lie algebra structure** of SHA's linear operators. This part gives strongest structural characterization to date.

### 6.1 Definition and setup

**Definition 6.1**: Let L_SHA ⊆ End_{F_2}(F_2^{32}) be the Z_2-Lie sub-algebra generated by:

$$\{N_{\Sigma_0}, N_{\Sigma_1}, N_{\sigma_0}, N_{\sigma_1}\}$$

where N_* = Σ_* − I or σ_* − I, with bracket [A, B] = AB − BA = AB + BA (char 2).

Ambient: gl_{32}(F_2), dimension 1024.

### 6.2 Rotation-only sub-algebra

**Theorem 6.1** (Session 18.1): The sub-algebra L_rot = ⟨N_{Σ_0}, N_{Σ_1}⟩ is **abelian**.

**Proof**: Both Σ_0 and Σ_1 are polynomial multiplications in commutative ring R = F_2[x]/(x^{32} − 1). Any two ring multiplications commute: Σ_0(Σ_1(x)) = Σ_0_poly · Σ_1_poly · x = Σ_1_poly · Σ_0_poly · x = Σ_1(Σ_0(x)). Hence [Σ_0, Σ_1] = 0 as linear maps. Follows for their N parts. ∎

**Corollary**: L_rot is nilpotent (abelian + generators nilpotent).

### 6.3 Adding σ breaks commutativity

**Theorem 6.2** (Session 18.2): L_SHA including σ operators (with SHR) is **non-abelian**.

**Evidence**:
- [N_{Σ_0}, N_{σ_0}] has rank 6 over F_2 (418 non-zero entries in 32×32 matrix)
- [ROTR_2 − I, SHR_3 − I] has rank 4
- [SHR_3, SHR_10] = 0 (shifts commute among themselves)

**Structural reason**: SHR (shift without wrap) is NOT a ring multiplication in F_2[x]/(x^{32} − 1). It is a lower-triangular operator in x-basis, whereas ROTR multiplications are upper-triangular. The combined operator σ_i = ROTR + ROTR + SHR is neither, breaking the commutative ring structure.

### 6.4 L_SHA is not nilpotent

**Theorem 6.3** (Session 19.1): L_SHA is **not nilpotent**.

**Proof**: By Engel's theorem, L_SHA is nilpotent iff every element acts nilpotently on F_2^{32}. Empirically:
- N_{Σ_0}^{32} = 0 ✓
- N_{Σ_1}^{11} = 0 ✓
- N_{σ_0} **not nilpotent** within 32 steps
- N_{σ_1} **not nilpotent** within 32 steps

Since generators N_{σ_0}, N_{σ_1} are not nilpotent as matrices, Engel's condition fails. Hence L_SHA not nilpotent. ∎

**Structural explanation**: σ_i − I has contributions from both upper-triangular (ROTR) and lower-triangular (SHR) parts, producing operators with non-zero eigenvalues in the algebraic closure of F_2 — not nilpotent.

### 6.5 L_SHA is not solvable (main structural theorem)

**Theorem 6.4** (Session 20.1, MAIN): L_SHA is **not solvable**.

**Proof**: We compute the derived series $D^{k+1}(L) = [D^k(L), D^k(L)]$ starting from generators:

| k | dim D^k(L_SHA) |
|---|---|
| 0 (span of generators) | 4 |
| 1 | 5 |
| 2 | 10 |
| 3 | 43 |
| 4 | **264** |
| 5 | **264** (stabilized) |

Since $D^5 = D^4 \ne 0$, the derived series stabilizes at a non-zero fixed point. This means the 264-dimensional sub-algebra $L' := D^4$ satisfies $[L', L'] = L'$, i.e., L' is **perfect**. Non-zero perfect Lie algebras are **not solvable**. Hence L_SHA not solvable. ∎

### 6.6 Structural analysis of perfect sub-algebra

**Facts about D^4 = L_SHA^{perfect}** (Session 21):

1. **D^4 ⊆ sl_{32}(F_2)**: all 264 elements have zero trace (automatic for brackets).
2. **Z(D^4) = 0**: the center is trivial (no non-zero elements commuting with all).
3. **F_2^{32} is reducible as D^4-module**: cyclic submodules generated by basis vectors have dimensions 3, 8, 8, 22, 21 (at minimum).
4. **dim 264 = 8 × 33 = 2³ × 3 × 11** does not match any classical simple Lie algebra over F_2:
   - sl_32 has dim 1023
   - sp_32 has dim 528
   - so_32 ~ 496 (char 2 subtleties)
   - Chevalley types give different dims

**Conjecture 6.5** (Session 21.1): D^4 is semisimple over F_2 in generalized sense (possibly modulo char-2 pathologies), decomposing as direct sum of simple Lie ideals:

$$D^4 \cong \bigoplus_i L_i$$

with F_2^{32} = ⊕ V_i correspondingly decomposing into irreducible L_i-modules.

### 6.7 Cryptanalytic interpretation

**Non-solvability is structurally favorable for SHA** (against attack):

- Cryptanalysis generally benefits from **solvable** Lie algebras which admit normal series: $L \supset L^{(1)} \supset L^{(2)} \supset \ldots \supset 0$ with abelian quotients. Each layer can potentially be "peeled off" in sequence.
- L_SHA is **non-solvable**: no such normal series. Cannot systematically reduce attack through commutator hierarchy.
- Presence of 264-dim perfect sub-algebra shows SHA's linear layer has rich mixing, not reducible to step-by-step structure.

**However**: this characterizes only the LINEAR layer of SHA (ROTR + SHR + XOR). Full cryptographic strength includes non-linear operations (AND in Ch/Maj, ADD carries), which are not in this Lie algebra framework.

The non-solvability result is a **structural invariant** — a mathematical fact about SHA-256 that is independent of specific attack attempts.

---

## Limitations

The following operations are **not** integrated into the cohomology framework:

### XOR (bitwise, on words)

XOR on Z/2^n is **not** a ring operation. Session 2 formula gives δ-discrepancy, but integration with rotation ring cohomology requires treating XOR as Z_2-module morphism or via tensor product with Boolean ring.

### AND (bitwise)

AND is bit-wise ("Hadamard product"), not convolution-like. F_2^n with pointwise multiplication is the product ring F_2 × ... × F_2, whose cohomology is trivial. Real AND structure requires either:
- Multi-variable rings F_2[ε_1,...,ε_n]/(ε_i²-ε_i), but Boolean ring is trivial (Kedlaya)
- Extended frameworks (λ-rings or similar)

### ADD mod 2^n

Respects δ-structure on Z_2 (Theorem D2) but we have **not** explicitly integrated it with the rotation ring cohomology. The carry-cascade formulas (Section 2) encode ADD δ-behavior, but connection to H^1(R^{⊗n}) is open.

### SHR (shift right without wrap)

Does **not** live in cyclic group algebra F_2[x]/(x^n - 1) (breaks cyclic structure). SHA message schedule uses SHR in σ_0, σ_1. **Partially addressed** in Part VI via Lie algebra framework (SHR included as linear operator, generating non-abelian structure).

### Size mismatch

Rotation cohomology for full SHA-256 state: **2^{248}**. SHA birthday: **2^{128}**. Our cohomology captures MORE classes than needed for birthday, but:
- This counts classification structure, not computational advantage
- SHA round function's action on cohomology needs to be understood to derive attack
- Joint invariants (Σ_0, Σ_1) = 2^6 per register, 2^{48} total — much smaller than birthday

### Identification of L_SHA^{perfect}

Session 21 determined that D^4 = L_SHA^{perfect} has dimension 264, is ⊆ sl_{32}(F_2), has trivial center, and F_2^{32} is reducible under it. But **exact decomposition into simple ideals is not determined**. Classification would require specialist knowledge of simple Lie algebras over F_2 in characteristic 2 (Chevalley types, Brown, Melikian, etc.). This is open.

---

## Honest assessment

After 21 sessions:

**What we have**:
1. Two valid prisms computed (Parts III.2-3)
2. Main cohomology theorem with rigorous proof (Theorem 4.2)
3. Explicit matrix computations for SHA's Σ_0, Σ_1 on H^1 (Theorems 5.2-5.3)
4. Joint invariant subspace identified (2-dim per register)
5. δ-structure formulas for ADD (D2), XOR (Theorem 2.2), AND (partial, Theorem 2.3)
6. Obstruction theorem ruling out naive ramified approach (Theorem 3.3)
7. **L_SHA Lie algebra framework (Part VI): abelian rotation core + non-abelian/non-nilpotent/non-solvable full algebra**
8. **Perfect sub-algebra D^4 of dimension 264 in sl_{32}(F_2)** (Theorem 6.4, Session 21 structural analysis)

**What we don't have**:
1. Cryptanalytic attack or even partial advantage
2. Integration of all SHA operations into single framework (AND still separate)
3. Full SHA round function as cohomology morphism
4. Treatment of ADD at cohomology level (only at δ-ring level)
5. Identification of L_SHA^{perfect} as specific classical or exotic simple Lie algebra(s)

**Realistic outlook**:

After 21 sessions, the programme has reached a **stable plateau of session-level capability**. Further progress requires specialist expertise in one of:

- **Bhatt-Scholze absolute prismatic cohomology** (modern $\infty$-categorical framework) to handle AND via derived tensor products or bialgebra structures
- **Simple Lie algebra classification over F_2 in characteristic 2** to identify L_SHA^{perfect} (Sessions 18-21 framework)
- **Bialgebra/Fourier theory on F_2^n** to simultaneously treat rotation (convolution) + boolean (pointwise) structures

A **real breakthrough** via this direction would require specialist expertise plus years of focused research. The session-level work has built a **concrete foundation** with specific computed objects (matrices, cohomology groups, formulas, Lie algebra structure) that a specialist could pick up and extend.

**Two major frameworks now in place**:
1. **Cohomology framework** (Parts IV-V): rotation ring H^1, matrices of Σ_0, Σ_1, joint invariants
2. **Lie algebra framework** (Part VI): L_SHA structural characterization, non-solvability, perfect sub-algebra

These complement each other: cohomology gives invariants, Lie algebra gives operators' algebraic structure. Together they form the session-level picture of SHA-256's linear layer.

---

## Summary of theorems

After 21 sessions, the following theorems have been established (all empirically verified; proofs sketched or complete in respective sessions):

1. **Theorem 2.1**: δ(z) = Σ_{i≥1} 2^{i-1}(1 − 2^i) z_i − Σ_{i<j} 2^{i+j} z_i z_j over Z (quadratic in z-bits)
2. **Theorem 2.2**: δ(x⊕y) = δ(x) + δ(y) − xy + 2z(x+y) − 2δ(z) − 3z² where z = x ∧ y
3. **Theorem 2.3**: Output bit k of δ(x ∧ y) mod 2^{n-1} has ANF degree exactly 2(k+1) in (x, y) variables
4. **Theorem 3.1**: (Z_2, (2)) is a valid prism (crystalline prism for p=2)
5. **Theorem 3.2**: (Z_2[[q-1]], (1+q)) is a valid prism (q-de Rham prism)
6. **Theorem 3.3**: Z_2[i] does NOT admit a δ-structure lifting Frobenius from F_2[i]
7. **Proposition 4.1**: H^0_{dR}(F_2[ε]/(ε²)) = Z_2, H^1 = F_2, H^≥2 = 0
8. **Theorem 4.2 (MAIN)**: H^1_{dR}(F_2[s]/(s^d)) = ⊕_{k odd, 1≤k≤d-1} Z/2^{v_2(k+1)}, with |H^1| = 2^{d-1} for d = 2^j
9. **Corollary 4.3**: H^1(R^{⊗n}) = n · H^1(R) via Künneth
10. **Theorem 5.1**: Multiplication by (1+s) acts as identity on H^1(F_2[s]/(s^n)). ROTR_r acts non-trivially for r ≥ 2
11. **Theorem 5.2**: Σ_0, Σ_1 are 16×16 upper triangular unipotent matrices on H^1 over F_2, order 16
12. **Theorem 5.3**: Joint kernel of (Σ_0 − I) and (Σ_1 − I) on H^1 is 2-dimensional over F_2, generators Z/2 ⊕ Z/32
13. **Theorem 6.1 (18.1)**: L_rot = ⟨N_{Σ_0}, N_{Σ_1}⟩ is abelian (nilpotent)
14. **Theorem 6.2 (18.2)**: L_SHA (including σ's) is non-abelian
15. **Theorem 6.3 (19.1)**: L_SHA is not nilpotent (σ's not nilpotent as matrices)
16. **Theorem 6.4 (20.1, MAIN)**: L_SHA is **not solvable**; contains perfect sub-algebra D^4 of dimension 264

**Conjecture 6.5 (21.1)**: D^4 = L_SHA^{perfect} is semisimple over F_2 (in generalized sense), decomposing as direct sum of simple Lie ideals.

---

## References

- Bhatt, B. and Scholze, P., "Prisms and Prismatic Cohomology" (2019), arXiv:1905.08229
- Bhatt, B., Columbia lectures on δ-rings, Lecture 2: https://public.websites.umich.edu/~bhattb/teaching/prismatic-columbia/lecture2-delta-rings.pdf
- Kedlaya, K.S., "Notes on Prismatic Cohomology": https://kskedlaya.org/prismatic/
- Joyal, A. "δ-anneaux et vecteurs de Witt" (1985)
- Kothari, C., "Motivating Witt Vectors and Delta Rings"

---

## Artifacts

All code and session notes in `/home/user/SHA-256/research/prismatic/`:

- `SESSION_1.md` through `SESSION_21.md` — incremental development (21 sessions)
- `delta_rings.py` — δ-ring definition, examples (Session 1)
- `session_2_compat.py`, `session_2_formula.py` — δ-axioms on Z/2^n, XOR formula (Session 2)
- `session_3_and_structure.py` — AND structural analysis (Session 3)
- `session_4_anf_proof.py` — δ(z) quadratic formula (Session 4)
- `session_6_framework.py` — truncation framework + crystalline prism (Session 6)
- `session_7_qwitt.py` — q-Witt prism (Session 7)
- `session_8_zi.py` — obstruction theorem (Session 8)
- `session_9_dual.py` — dual numbers cohomology (Session 9)
- `session_10_thickening.py` — main cohomology theorem (Session 10)
- `session_11_kunneth.py` — Künneth formula (Session 11)
- `session_12_xor.py` — correction + XOR setup (Session 12)
- `session_13_rotation_action.py` — ROTR_1 theorem (Session 13)
- `session_14_sigma0.py` — Σ_0 matrix (Session 14)
- `session_15_joint.py` — joint invariants (Session 15)
- `session_17_and.py` — AND bilinear analysis (Session 17)
- `session_18_lie.py`, `session_18b_shr.py` — Lie algebra setup, SHR commutators (Session 18)
- `session_19_nilpotent.py` — nilpotency test (Session 19)
- `session_20b_derived.py` — derived series computation (Session 20)
- `session_21_perfect.py` — perfect sub-algebra structural analysis (Session 21)

Total lines: ~5000 across 21 sessions. Full version control history in git log.
