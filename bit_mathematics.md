# Bit Mechanics — Mathematical Foundations

## Axioms

**A1. (Bit Field)**
A bit field is a tuple F = (n, m, Φ) where:
- n = number of bits (variables)
- m = number of constraints (clauses)  
- Φ = {C₁, ..., Cₘ} where each Cⱼ = {(v₁,s₁), (v₂,s₂), (v₃,s₃)}
  with vᵢ ∈ {1,...,n} and sᵢ ∈ {+1, -1}

**A2. (Random Field)**
In a random 3-SAT field with ratio r = m/n:
- Each clause selects 3 distinct variables uniformly at random
- Each sign sᵢ is +1 or -1 with equal probability, independent

**A3. (Solution)**
A solution is a vector x ∈ {0,1}ⁿ such that every clause is satisfied:
for each Cⱼ, ∃(v,s) ∈ Cⱼ such that (s=+1 ∧ xᵥ=1) ∨ (s=-1 ∧ xᵥ=0)

**A4. (Tension)**
The tension of bit i in field F with partial assignment π is:
σᵢ(π) = (p⁺ᵢ - p⁻ᵢ) / (p⁺ᵢ + p⁻ᵢ)
where p⁺ᵢ = Σ_{C∋i, C active} (sᵢ/|C_free|) over clauses where sᵢ=+1
and p⁻ᵢ similarly for sᵢ=-1.

---

## Derivations

### Theorem 1: Expected Degree
In a random field with ratio r, each bit appears in d clauses where
d ~ Poisson(3r).

*Proof:* Each clause contains 3 variables from n. Probability that
a specific variable is in a specific clause: 3/n. Expected appearances
in m = rn clauses: 3rn/n = 3r. Independence → Poisson. ∎

### Theorem 2: Sign Distribution  
For bit i appearing in d clauses, the number of positive appearances
k ~ Binomial(d, 1/2).

*Proof:* Each sign is +1 with probability 1/2, independent. ∎

### Theorem 3: Tension Distribution
For a bit with d appearances, k positive:
σ = (k - (d-k)) / d = (2k - d) / d = 2k/d - 1

Therefore σ = 2X/d - 1 where X ~ Binomial(d, 1/2).

*Proof:* Direct from definitions. ∎

### Theorem 4: Expected |σ|
E[|σ|] = E[|2X/d - 1|] where X ~ Bin(d, 1/2)

For d = 3r (using Poisson mean):
- This is a known function of d
- At d=12 (r=4): E[|σ|] ≈ 0.226

*Proof:* Direct computation from binomial distribution. ∎

---

### Theorem 5: The Signal (ε derivation)

**This is the key theorem. Why does tension PREDICT the correct value?**

Let x* be a solution. For bit i with x*ᵢ = 1:
- A clause containing +i is satisfied by x*ᵢ (among other literals)
- A clause containing -i is NOT helped by x*ᵢ

In a random field, clause signs are independent of the solution.
But conditioned on x* being a solution, there is a BIAS:

**Claim:** P(clause satisfied | +i ∈ clause, x*ᵢ=1) > P(clause satisfied | -i ∈ clause, x*ᵢ=1)

This is because +i directly satisfies the clause when x*ᵢ=1.

**The bias ε:** Among clauses containing bit i:
ε = P(sign matches x*ᵢ) - 1/2

For random 3-SAT, this can be computed:
- If x*ᵢ=1 and clause has +i: clause is satisfied (x*ᵢ helps)
- If x*ᵢ=1 and clause has -i: clause must be satisfied by OTHER literals
- Clauses with -i that can't be satisfied by others → UNSAT → not in valid instance

The last point is crucial: we condition on x* being a solution.
This means clauses with -i MUST be satisfiable by other literals.
This doesn't directly bias the signs.

**The real source of ε:**
In a satisfiable instance, bits that are 1 in MOST solutions
tend to appear positive in MORE clauses, because:
- Being positive in a clause means the clause is easier to satisfy
- Bits that make many clauses easy are more likely to be 1 in solutions
- This creates a correlation between sign frequency and solution value

ε(r) ≈ c/r because:
- At higher r, each clause provides less information (1/m per clause)
- Total information from d ≈ 3r clauses: d × (info/clause) ≈ 3r × (c'/r²) 
- Net ε ≈ c/r

**Empirical verification:** c ≈ 0.30, fit error 0.00012

---

### Theorem 6: Accuracy Equation
The probability that tension correctly predicts bit i's value:

A(d, ε) = P(Binomial(d, 1/2 + ε) > d/2)

*Proof:* Tension σ > 0 when positive appearances > negative.
If each appearance has probability 1/2 + ε of matching the correct value,
then correct predictions = majority of d biased coins. ∎

**Corollary:** At threshold (r=4.27, ε=0.072, d≈13):
A ≈ 69% — verified experimentally.

---

### Theorem 7: Temperature Equation
T = 1 - E[|σ|] = 1 - E[|2·Bin(d, 1/2+ε)/d - 1|]

*Proof:* Temperature = mean frustration = mean (1-|σ|).
Direct from Theorem 3 with biased distribution. ∎

**Corollary (Temperature Conservation):**
During crystallization, fixing a bit:
- Removes ~d/2 clauses (satisfied) → reduces pressure → ΔT > 0
- Simplifies ~d/2 clauses (one fewer literal) → increases pressure → ΔT < 0
These approximately cancel, giving |ΔT| ≈ 0.

---

### Theorem 8: Correlation Length
**ξ = 1 for single-step transmission.**

*Proof sketch:* Fixing bit i changes σ(j) only through shared clauses.
If i and j share no clause: fixing i doesn't change j's tension at all.
If they share clause C: fixing i either satisfies C (removes it from j's pressure)
or removes one literal from C (changes weight).
Both effects are O(1/d_j) per shared clause.

For j and k at distance 2 (no shared clause, but both share clauses with
some intermediate bit m): fixing i changes σ(m), but m is NOT fixed.
Since m is still free, its changed tension doesn't propagate to k.
Therefore T(i,k) = 0 at distance 2. ∎

---

### Theorem 9: Error Correlation
For bits i,j sharing at least one clause:
P(both wrong) ≈ 1.20 × P(i wrong) × P(j wrong)

*Derivation sketch:* 
If i is wrong, its tension majority went opposite to the solution.
For a shared clause C with i and j:
- C's vote for i was "wrong" direction
- C also votes for j
- The vote for j is correlated with the vote for i (same clause structure)
- Therefore j's votes are biased toward being wrong too

The lift factor 1.20 comes from the fraction of j's votes that
share a clause with i: approximately (d_shared / d_j) × correction.

**Saturation at 1 shared clause:** Once any shared clause creates
correlation, additional sharing adds marginally — because one
wrong-biased vote among ~13 total votes has limited impact.

---

### Theorem 10: Tension Blindness (L10)

**Statement:** Tension σ is a function of the CLAUSE STRUCTURE only,
not of the solution space. Formally:

σᵢ(π) depends only on {Cⱼ : Cⱼ active given π}, not on
{x ∈ {0,1}ⁿ : x is a solution compatible with π}.

*Proof:* By definition, σ is computed from clause weights. ∎

**Consequence:** Two instances with identical clause structure
but different solution spaces yield identical tensions.
This means tension CANNOT distinguish:
- An instance with 100 solutions (easy)
- An instance with 1 solution (hard)
if their clause structures are the same.

This is the fundamental limit of clause-based methods.

---

### Theorem 11: Flip Fragility

**Statement:** Let F(i) = fraction of neighbors that can reverse sign(σᵢ).
Then E[F(i) | i wrong] ≈ 2 × E[F(i) | i correct].

*Derivation sketch:*
If bit i has |σᵢ| ≈ 0 (barely decided), almost any perturbation can flip it.
Wrong bits tend to have lower |σᵢ| (weaker signal → more likely wrong).
The relationship between |σ| and flip triggers:

F(i) ≈ P(∃ neighbor nb s.t. fixing nb changes sign(σᵢ))
     ≈ 1 - (1 - p_flip)^d_neighbors

where p_flip per neighbor ≈ (shared_clauses / d_i) × (clause_weight / |σᵢ|)

Since wrong bits have |σ| ≈ 0.57× correct bits (from empirical data),
their p_flip is higher, leading to F(wrong) ≈ 2 × F(correct).

---

## Open Derivations Needed

### O1: Derive c = 0.30 from first principles
ε(r) = c/r. Why c ≈ 0.30?

Hypothesis: c = 3/10. The factor 3 comes from 3-SAT (3 literals per clause).
For k-SAT: c = k/10? This needs verification.

### O2: Derive the amplification delay (4 fixes)
Why does unit propagation kick in at fix #4?
Related to: expected number of unit clauses after k fixes
= (number of 2-literal clauses) × P(one literal killed by a fix)

### O3: Prove the information ceiling
Why is 79% (v4) the maximum for clause-based methods?
Is there a proof that no polynomial-time clause-reading algorithm
can exceed this? Or is v4 suboptimal?

### O4: Connect to P vs NP
Our findings:
- Information exists (88% optimal)
- Extraction from clauses ≤ 79%
- Extraction via solution sampling: 91%
- Solution sampling requires finding solutions (circular?)
  
Is the 9% clause-solution gap provably nonzero for all poly-time methods?
This would be a statement ABOUT P vs NP (not a proof, but a structural result).
