"""
═══════════════════════════════════════════════════════════════
MATHEMATICAL SYNTHESIS: What derives from what?
═══════════════════════════════════════════════════════════════

Starting from FIRST PRINCIPLES. No code. Pure derivation.
Every number checked against measurement.

═══ AXIOM ═══

  Random 3-SAT: n vars, m = rn clauses (r = 4.267).
  Each clause: 3 random vars, 3 random ±1 signs.
  ε = 1/(2(2³-1)) = 1/14.

═══ WHAT FOLLOWS FROM ε ALONE ═══

Derivation 1: ACCURACY
  Each clause vote correct with prob 1/2 + ε = 4/7.
  d votes (d ≈ 3r ≈ 12.8): K⁺ ~ Bin(d, 4/7).
  Accuracy = P(K⁺ > d/2) = A(d, ε).

  COMPUTED: A(13, 1/14) = 0.7014.
  MEASURED: 0.68-0.71 ✓

Derivation 2: MI
  I(X*; K⁺) = 1 - H(X* | K⁺).

  COMPUTED: MI(13, 1/14) = 0.171 bits.
  MEASURED: 0.17 ✓

Derivation 3: TEMPERATURE
  T = 1 - E[|2·Bin(d, 4/7)/d - 1|]

  COMPUTED: T(13) = 0.747.
  MEASURED: DET/RAND split ≈ 75/25 ✓

Derivation 4: MATCH RATIO
  Correct value: matches sign with prob 4/7 = 0.571.
  Wrong value: matches sign with prob 3/7 = 0.429.

  MEASURED to NEAREST: wrong = 0.576, right = 0.607.
  ANOMALY: both ABOVE predicted!

  Why? Because physics OPTIMIZED — not random assignment.
  Physics pushes match_ratio UP for ALL vars.
  Predicted 3/7 = 0.429 for wrong, measured 0.576. Δ = +0.147!
  Predicted 4/7 = 0.571 for right, measured 0.607. Δ = +0.036.

  Physics amplifies wrong MORE (+0.147) than right (+0.036).
  This IS the overfitting: physics makes wrong vars look better
  than they should.

Derivation 5: CRITICAL COUNT
  A var saves a clause iff:
    (a) its literal is true AND
    (b) no other literal in the clause is true

  P(v saves clause c) = P(v true) × P(others false)

  For correct value: P(v true in c) = 4/7 (average).
  P(other 2 both false) = (3/7)² = 9/49.
  P(v sole saver) ≈ 4/7 × 9/49 = 36/343 = 0.105.
  Expected critical = d × 0.105 ≈ 12.8 × 0.105 = 1.34.

  For wrong value: P(v true in c) = 3/7.
  P(others both false) = (3/7)² = 9/49. [same: independent of v]

  WAIT. P(others false) depends on WHETHER OTHERS ARE CORRECT.
  If others are correct: P(other true) = 4/7 → P(false) = 3/7.
  If others are wrong: P(other true) = 3/7 → P(false) = 4/7.

  This is MORE COMPLEX than simple ε.

  P(v sole saver | v correct) = (4/7) × (3/7)² = 0.105
    → expected critical_correct ≈ 12.8 × 0.105 = 1.34

  P(v sole saver | v wrong) = (3/7) × ?
    ? depends on whether OTHER vars in the clause are correct.
    If 25% of all vars are wrong (to nearest), then:
    P(other is wrong) = 0.25.
    P(other is correct) = 0.75.

    P(other true | other correct) = 4/7.
    P(other true | other wrong) = 3/7. [wrong val matches 3/7]

    WAIT. But physics AMPLIFIED match_ratio.
    Measured: wrong match = 0.576, right match = 0.607.

    So P(other true) = 0.75 × 0.607 + 0.25 × 0.576 = 0.599.
    P(other false) = 1 - 0.599 = 0.401.

    P(v sole saver | v wrong) = 0.576 × (0.401)² = 0.576 × 0.161 = 0.093.
    P(v sole saver | v correct) = 0.607 × (0.401)² = 0.607 × 0.161 = 0.098.

    PREDICTED critical ratio: 0.093 / 0.098 = 0.949.

    Hmm. That predicts ratio ≈ 0.95. We MEASURED 0.85.

    ANOMALY: measured critical ratio (0.85) is STRONGER than
    predicted from match_ratio alone (0.95).

    Δ = 0.10. Critical carries MORE signal than match_ratio explains.

    WHERE does the extra 0.10 come from?

═══ ANOMALY INVESTIGATION ═══

The critical count ratio (0.85) is stronger than match_ratio (0.95)
predicts. The extra signal must come from CORRELATIONS.

Hypothesis: wrong vars tend to appear in clauses with OTHER wrong vars.
If so, their clauses have MORE true literals (wrong covers wrong),
reducing the chance of being SOLE saver.

Wait — that would make critical LOWER for wrong, INCREASING the ratio
difference. Let me recalculate.

If wrong var is in a clause with another wrong var:
  P(other true) = 0.576 (wrong match).
  Higher than average P(true) = 0.599.
  → P(other false) = 0.424. LOWER.

  No wait. Wrong match = 0.576 < average 0.599.
  So P(other false) = 1 - 0.576 = 0.424 > 0.401.

  P(sole saver) = 0.576 × 0.424² = 0.576 × 0.180 = 0.104.
  This is HIGHER than the average (0.093).

  That's wrong direction. If wrong vars cluster with wrong,
  critical should be HIGHER not lower.

Let me reconsider. The measured match ratios:
  wrong (to nearest) = 0.576
  right (to nearest) = 0.607

For a WRONG var in a clause with 2 RIGHT vars:
  P(sole saver) = P(v true) × P(others false)²
  = 0.576 × (1-0.607)² = 0.576 × 0.154 = 0.089

For a WRONG var in a clause with 2 WRONG vars:
  P(sole saver) = 0.576 × (1-0.576)² = 0.576 × 0.180 = 0.104

For a RIGHT var in a clause with 2 RIGHT vars:
  P(sole saver) = 0.607 × (1-0.607)² = 0.607 × 0.154 = 0.094

For a RIGHT var in a clause with 2 WRONG vars:
  P(sole saver) = 0.607 × (1-0.576)² = 0.607 × 0.180 = 0.109

So if wrong vars appear with right vars: P_sole = 0.089 (LOW)
   if right vars appear with wrong vars: P_sole = 0.109 (HIGH)

The MIXING PATTERN matters! If wrong cluster with right:
  critical_wrong goes DOWN, critical_right goes UP → ratio DECREASES

This explains the extra signal! Wrong vars tend to be SURROUNDED
by right vars (since 75% are right), making them the weakest
link in their clauses → critical drops more than match_ratio alone.

PREDICTED ratio with mixing:
  wrong: 0.75 × 0.089 + 0.25 × 0.104 = 0.093
  right: 0.75 × 0.094 + 0.25 × 0.109 = 0.098
  ratio = 0.093/0.098 = 0.949.

Still 0.95. The mixing doesn't explain 0.85.

The REMAINING 0.10 gap must be from PHYSICS AMPLIFICATION.
Physics doesn't just set values — it creates CORRELATIONS
between neighboring vars that go beyond independent match ratios.

═══ WHAT IS INDEPENDENT OF ε? ═══

1. ε → accuracy 70%, MI 0.171, T 0.75, match_ratio diff 0.03
   ALL per-var properties with ratio 0.9-1.0 come from here.

2. PHYSICS AMPLIFICATION: 4.45× info gain.
   This is NOT from ε alone. It's from NONLINEAR DYNAMICS.
   The amplification creates CORRELATIONS between vars.
   These correlations push critical ratio from 0.95 to 0.85.

3. GREEDY PATH flatness (max 8 unsat).
   This is NOT from ε. It's from the STRUCTURE of the solution space.
   The fact that a nearly monotone path EXISTS is a property of
   the instance topology, not of the signal strength.

4. 0 wrong at |tension| > 0.8.
   This IS from ε (high |tension| = many agreeing votes = correct).
   But the SHARPNESS of the cutoff might be physics-amplified.

5. WalkSAT destructiveness (9→21).
   NOT from ε. From the EQUILIBRIUM structure.
   WalkSAT overshoots because it doesn't track global sat.

═══ THE TWO INDEPENDENT SOURCES OF INFORMATION ═══

Source A: ε = 1/14 per clause vote.
  → All per-var features, ratio 0.7-0.95.
  → Fundamental limit. Cannot be exceeded by clause-reading.

Source B: SOLUTION SPACE TOPOLOGY.
  → Greedy path flatness.
  → Cluster structure.
  → Number and arrangement of solutions.
  → NOT encoded in ε. Independent information.

Source B is what SP uses (surveys about cluster structure).
Source A is what physics/tension/WalkSAT use.

WE HAVE BEEN USING ONLY SOURCE A.

Source B is UNEXPLORED in our Bit Mechanics framework.
It's what makes SP work at n=750 where everything else fails.

═══ WHAT WOULD A SOURCE B MEASUREMENT LOOK LIKE? ═══

Not per-var. Not per-clause. Not even per-pair.

It would be a measurement of the TOPOLOGY of the solution space:
  - How many solutions?
  - How are they arranged?
  - What are the cluster boundaries?
  - Where is our assignment relative to cluster centers?

These are GLOBAL properties. Not computable from local features.
They require REASONING ABOUT SOLUTIONS, not about clauses.

This is exactly what SP does: compute surveys about the
PROBABILITY OF BEING IN DIFFERENT CLUSTERS.

═══ CONCLUSION ═══

1. ε = 1/14 is the SOLE source of per-var information.
   All our 30 measurements are f(ε). Ratio 0.7-0.95.
   Cannot improve without new information source.

2. Physics amplification (4.45×) creates CORRELATIONS
   that push critical ratio to 0.85 (beyond ε prediction of 0.95).
   But still insufficient to identify wrong vars reliably.

3. SOLUTION SPACE TOPOLOGY is an independent information source.
   It explains greedy path flatness, SP's success, cluster structure.
   We have NOT tapped this source.

4. The anomaly: critical ratio 0.85 < predicted 0.95.
   The extra 0.10 comes from PHYSICS-CREATED CORRELATIONS.
   These correlations are a SECOND-ORDER effect of ε, amplified
   by nonlinear dynamics. They're real but not new information.

═══ ANOMALIES TO RECHECK ═══

A1: match_ratio wrong=0.576 measured vs 3/7=0.429 predicted.
    Δ = +0.147. HUGE. Physics amplifies wrong MORE than right.
    → VERIFY at larger n. Does the gap grow or shrink?

A2: critical ratio 0.85 vs predicted 0.95.
    Extra 0.10 from correlations.
    → VERIFY: is there a formula that predicts 0.85 exactly?

A3: 0 wrong vars at |tension| > 0.8.
    Sharp cutoff. Is this ε-predicted or emergent?
    → COMPUTE: P(wrong | |tension| > 0.8) from Binomial model.

A4: Greedy path max 8 unsat (nearly flat).
    NOT from ε. From topology.
    → Is there a FORMULA for greedy path height in terms of n, r?
"""
