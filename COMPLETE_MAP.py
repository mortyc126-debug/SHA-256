"""
═══════════════════════════════════════════════════════════════════════
COMPLETE MAP OF EVERYTHING WE KNOW
═══════════════════════════════════════════════════════════════════════

This is for US. Not publication. Raw truth.

Every finding, every number, every connection. All in one place.
Looking for the pattern we're missing.
═══════════════════════════════════════════════════════════════════════


═══ LAYER 1: THE INSTANCE ═══

Random 3-SAT at threshold r=4.267:
  n vars, m=4.267n clauses, each has 3 vars with random ±1 signs

Sign matrix S: m×n, entries {-1,0,+1}, 3 nonzero per row
  Full rank. Condition number ~2.5.
  Channel capacity 57.6 bits but only 2.1 used (3.6%).
  97% of capacity wasted on noise.

Fundamental constants:
  ε = 1/14 = 0.0714    signal per clause vote
  h_comp = 0.013       bits per edge (Planck constant)
  T = 0.747             temperature

Signs + topology = 50/50 information interaction.
Neither alone carries any signal. Only their COMBINATION.


═══ LAYER 2: TENSION AND ACCURACY ═══

Tension σ_v = weighted sum of clause votes for var v.
  Bayes-optimal predictor. Accuracy = 70.1% at threshold.

Wall theorem: clause-reading accuracy ≤ 83% (conditional on BP optimality).
  Tension = vacuum force (r=0.986 correlation with force at x=0.5).

MI per variable: 0.171 bits out of 1 bit needed.
  MI per edge: 0.013 bits = h_comp.
  Information amplification through physics: 4.45×.


═══ LAYER 3: THE α = T THEOREM ═══

DPLL/CDCL explores 2^(c·n^T) nodes.
  k=3: T=0.747, c=0.27. k=4: T=0.864.
  Each k has its OWN exponent.

Mechanism (5 steps):
  1. Signal/noise split by T (75% signal, 25% noise)
  2. UP cascade supercritical at f=1-T
  3. Decision accuracy cliff: 89% → 29%
  4. DPLL intelligence δ → 0 at threshold
  5. α = β - δ = T

Verified: k/n^T constant at n=20-300. 8/8 predictions.


═══ LAYER 4: PHYSICS ═══

PhysicsSAT: particles in clause force field.
  Reaches 99% satisfaction in O(n²).
  Beats MiniSat at n=500 (4/20 vs 0/20).
  Pure physics solves at n≤75.

Sub-bit physics:
  75% DET / 25% RAND = temperature split.
  E/S ≈ 0.6 = const (conservation law).
  Speed of information: 1 hop / 10 steps.
  Phase space: all trajectories → fixed points.
  Decoherence: sigmoid → step function.


═══ LAYER 5: FROZEN CORE ═══

Structure:
  50-60% of vars frozen at threshold.
  1 giant component. Diameter 1.5. ALL boundary (no interior).

Keystone clauses: 18-20% of clauses hold entire core.
  Removing all keystones → 11 frozen → 1.
  Keystones have 1 correct sign / 3 (barely satisfied).
  Forbidden point distance 1.3 (close to solution).
  Keystones = WALLS between solution clusters.

Passes through keystones:
  Tension identifies pass at 58% (1.74× random).
  Pass vars: 95% correct by critical count predictor.
  All 3 literals wrong in every unsat clause.


═══ LAYER 6: THE EQUILIBRIUM ═══

After physics + WalkSAT: ~√n unsat clauses.

Pendulum: period 2. One variable oscillates between 2 clauses.
  Fix 1 = break 1. ALWAYS. No single flip improves.

The equilibrium IS the frozen core's final defense.
  Not rigidity. Not complexity. BALANCE.
  Every fix exactly counterbalanced by a break.

1-hop bypass: removes 33-40% of unsat.
2-5 hop bypass: 0% additional.
k-flip diminishing: 1-flip 35%, +2-flip 10%, +3-flip 5% → ceiling 46%.


═══ LAYER 7: GHOST VARIABLES ═══

HC vars = "ghosts":
  Counterfactual Δsat: 0.36 vs 1.76 (5× cheaper to flip).
  Multi-run disagreement: 43% (vs 23% for non-HC).
  Cross-reality correlation: -0.026 (vs +0.069).
  Match ratio: 0.486 (below 0.5 = wrong value).

  Ghosts are PRESENT but DON'T CONTRIBUTE.
  Their value doesn't help their clauses.
  The system would prefer to release them.

Detection:
  |force| > 0 at stuck point: PERFECT detector (100%).
  Critical count: r=1.000 predictor among 3 suspects.
  Commit time: HC vars commit 25% later in physics.
  HC neighbor fraction: 30% higher clustering.


═══ LAYER 8: THE MULTIVERSE ═══

20 cold starts at n=500:
  Hamming between starts: 33% (genuinely different valleys).
  0 always-unsat clauses. 249 sometimes-unsat.
  167 split vars (different value in different realities).
  148 always-same vars (consensus zone).

Majority vote: WORSE than best single.
Best single: 9-15 unsat (sometimes almost solves alone).

Warm start kills diversity (agreement → 100%).
Cold starts explore DIFFERENT valleys.

Cherry-pick methods: local expert, agree+best, weighted, clause-optimal.
  All give ~same after WalkSAT (17-42 unsat at n=500).

WalkSAT is DESTRUCTIVE on good starts (9 → 21).


═══ LAYER 9: THE BARRIER ═══

17 methods tested. ALL give ~1/10 at n=500, 0 at n=750.

Hard core geometry:
  12% of n. Density 0.35. Diameter 1.5.
  Sparse archipelago of tiny islands.
  Components ≈ clauses (each island = 1 clause).

Not fractal (1-hop takes all, 2+ adds zero).
Components interfere (fix one → break 1.2 in others).

Incremental constraint addition: works at ≤5 unsat.
Feedback physics: = restart with bias.
Instance surgery: mixed results.


═══ CONNECTIONS WE SEE ═══

ε = 1/14 → accuracy 70% → Wall 83% → T = 0.75 → α = T
                                                    ↓
h_comp = 0.013 → 97% waste → hard core → pendulum → equilibrium
                                 ↓                      ↓
                          keystones 18%            fix 1 = break 1
                          pass 58%                      ↓
                          critical r=1.000       1-hop 35% ceiling
                                                       ↓
                                                  ghosts 5× cheap
                                                  disagreement 43%
                                                  all-3-wrong
                                                       ↓
                                                  multiverse 33%
                                                  0 always-unsat
                                                  WalkSAT destructive
                                                       ↓
                                                  BARRIER n=750


═══ WHAT WE'RE MISSING ═══

1. We can get to 9 unsat. We need 0. Gap = 9.
   But WalkSAT from 9 WORSENS to 21.

2. Every unsat clause has ALL 3 wrong.
   So the correct assignment is the OPPOSITE for all HC vars.
   But flipping all HC vars creates 50+ new unsat (catastrophic).

3. 20 cold starts give 0 always-unsat.
   EVERY clause CAN be satisfied. Just not ALL simultaneously
   from ANY single assignment we've found.

4. Majority HURTS. Best single is better than any combination.
   The solution is not an AVERAGE of realities.

5. Ghost vars have |force| > 0 but can't move.
   Physics KNOWS the direction but equilibrium prevents motion.

6. Feedback changes landscape but finds same-quality valleys.
   The valleys are STRUCTURAL, not accidental.

The pattern:
  - Information EXISTS (0 always-unsat)
  - Direction IS KNOWN (force field, all-3-wrong)
  - Individual steps CAN'T improve (equilibrium)
  - The barrier is COLLECTIVE, not individual
  - No LOCAL operation works (1-5 hop = zero after 1st)
  - No GLOBAL operation works (majority hurts, inversion catastrophic)
  - The answer is not LOCAL and not GLOBAL but... WHAT?


═══ THE QUESTION ═══

What TYPE of operation is neither local (flip 1-5 vars)
nor global (flip 33% of vars) but gives net > 0?

We haven't found it. But we know its properties:
  - It must flip ~5-15 vars simultaneously (between 1% and 3% of n)
  - Those vars must be CHOSEN, not random
  - The choice requires NON-LOCAL information (no single-var feature works)
  - But not fully GLOBAL either (majority and inversion fail)

  This is a MESOSCALE operation.
  Not micro (1 var). Not macro (33% vars). MESO (~2%).

  The frozen core lives at the MESOSCALE.
  Our tools are either micro (flips) or macro (physics).
  We have no MESOSCALE tool.
"""
