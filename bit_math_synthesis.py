"""
MATHEMATICAL SYNTHESIS: What follows from what?

Map ALL our results as a dependency graph.
Which results are DERIVED? Which are INDEPENDENT?
Where are GAPS that could hide new insights?
"""


def print_synthesis():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              MATHEMATICAL DEPENDENCY MAP                         ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  LEVEL 0: AXIOM (no derivation, verified experimentally)         ║
║                                                                  ║
║    A0. Random 3-SAT: n vars, m=rn clauses, each with 3 random   ║
║        literals with random signs ±1.                            ║
║                                                                  ║
║  LEVEL 1: DERIVED FROM A0 (pure combinatorics)                   ║
║                                                                  ║
║    T1. ε = 1/14                                                  ║
║        FROM: P(sign matches | clause satisfied) = 4/7            ║
║        PROOF: complete, no gaps                                  ║
║                                                                  ║
║    T2. Degree d ~ Poisson(3r)                                    ║
║        FROM: each clause picks 3 of n vars                       ║
║        PROOF: standard                                           ║
║                                                                  ║
║  LEVEL 2: DERIVED FROM T1 + T2                                   ║
║                                                                  ║
║    T3. Accuracy A(d) = P(Bin(d, 4/7) > d/2)                     ║
║        FROM: T1 (ε = 1/14) + T2 (degree d)                      ║
║        PROOF: complete. Majority = Bayes-optimal (PROVEN).       ║
║        VALUE: A(13) = 70.1%, verified.                           ║
║                                                                  ║
║    T4. MI_single = H(1) - H(C|k) = 0.171 bits                  ║
║        FROM: T1 + T2 + Bayesian posterior                        ║
║        PROOF: complete.                                          ║
║                                                                  ║
║    T5. Temperature T = 1 - E[|2Bin(d,4/7)/d - 1|]              ║
║        FROM: T1 + T2                                             ║
║        PROOF: complete. OU dynamics (λ=0.116) — EMPIRICAL.      ║
║        GAP: OU derivation not formal.                            ║
║                                                                  ║
║    T6. UP delay: E[units] = 3mk²(n-k)/(4n³)                    ║
║        FROM: binomial model of clause simplification              ║
║        PROOF: complete. Threshold at k=3 verified.               ║
║                                                                  ║
║    T7. ε(r) convergence: measured ε → 1/14 as d → ∞            ║
║        FROM: T1 + selection bias at small d                      ║
║        PROOF: argument complete, formal bound missing.           ║
║                                                                  ║
║  LEVEL 3: DERIVED FROM LEVEL 2 + EMPIRICAL                      ║
║                                                                  ║
║    T8. V4 accuracy ≈ 81%                                         ║
║        FROM: T4 + denoising (redundancy removal)                 ║
║        HOW: ε_eff = ε × 2.64 (amplification factor)             ║
║        GAP: amplification factor not derived, only measured.     ║
║        CONNECTION: V4 = non-redundant tension = BP (PROVEN).     ║
║                                                                  ║
║    T9. Error lift = 1.20                                         ║
║        FROM: gap field magnitude coherence                        ║
║        GAP: exact formula unknown. Mechanism identified           ║
║        (signed + |gap| correlation), value not derived.          ║
║                                                                  ║
║    T10. Flip trigger ratio = 1.97 = 1.66 × 1.20                ║
║         FROM: margin distribution (T3) × error lift (T9)         ║
║         PROOF: decomposition verified. 1.66 from Bin(d,4/7).    ║
║         1.20 from T9 (not fully derived).                        ║
║                                                                  ║
║    T11. Contradiction rate = 2A(1-A) × 0.88                     ║
║         FROM: T3 (accuracy) × correction from T9 (lift)          ║
║         PROOF: approximate. Correction factor empirical.         ║
║                                                                  ║
║  LEVEL 4: STRUCTURAL (require solution knowledge to verify)      ║
║                                                                  ║
║    T12. Clone fraction ≈ 37% of pairs, effective DOF = n/3       ║
║         FROM: frozen variable fraction at condensation            ║
║         CONNECTION: n/3 = unfrozen fraction (PROVEN: T_D)        ║
║         GAP: frozen fraction not derived from ε.                 ║
║                                                                  ║
║    T13. Eigenmode reconstruction: 4 modes → 86%                  ║
║         FROM: signed Laplacian eigenbasis                         ║
║         CONNECTION: n/3 modes needed (= T12 DOF)                 ║
║         GAP: WHY signed Laplacian works not derived.             ║
║                                                                  ║
║    T14. Weak values = eigenmode projections (r > 0.9)            ║
║         FROM: TSVF applied to SAT                                ║
║         STATUS: EMPIRICAL only. No analytical derivation.        ║
║         THIS IS THE DEEPEST UNPROVEN CONNECTION.                 ║
║                                                                  ║
║  LEVEL 5: WALL THEOREM                                           ║
║                                                                  ║
║    T15. Clause MI ≤ 0.342 bits → accuracy ≤ 83%                 ║
║         FROM: T4 (MI_single) + T8 (denoising bound)             ║
║         + Fano's inequality                                       ║
║         GAP 1: BP optimality not proven for loopy graphs.        ║
║         GAP 2: applies to message-passing only, not DPLL.        ║
║         GAP 3: random instances only, not worst case.            ║
║                                                                  ║
║    T16. k = O(n^0.75) for DPLL+tension                          ║
║         FROM: empirical scaling n=10-100 (our DPLL + MiniSat)   ║
║         STATUS: EMPIRICAL only. No proof.                        ║
║         THIS IS THE MOST IMPORTANT UNPROVEN SCALING LAW.         ║
║                                                                  ║
║    T17. Assembly barrier: need 1-O(1/n) per-bit accuracy        ║
║         FROM: probability theory (union bound)                    ║
║         PROOF: complete.                                          ║
║         BUT: applies to INDEPENDENT assembly, not DPLL cascade.  ║
║                                                                  ║
║  LEVEL 6: PHYSICS CONNECTIONS                                    ║
║                                                                  ║
║    T18. Information conservation: MI_rev + MI_hid = 1.00         ║
║         FROM: definition of MI + H(bit) = 1                      ║
║         PROOF: trivially true by construction.                   ║
║         BUT: the BOUNDARY (what's revealed vs hidden) is the     ║
║         non-trivial part = the Wall.                              ║
║                                                                  ║
║    T19. Non-local correlations: 73% at d=2 don't travel paths   ║
║         STATUS: EMPIRICAL. No theoretical explanation.           ║
║         CONNECTION: related to T13 (eigenmode structure).        ║
║         THIS IS UNEXPLAINED.                                     ║
║                                                                  ║
║    T20. Self-cancellation (from SHA-256 P5)                      ║
║         STATUS: EMPIRICAL. Ratio 0.67 not derived.              ║
║         CONNECTION: related to T9 (error lift) somehow.          ║
║                                                                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  FULLY PROVEN (no gaps):                                         ║
║    T1, T2, T3, T4, T6, T17, T18                                 ║
║    = 7 out of 20 results                                         ║
║                                                                  ║
║  PARTIALLY PROVEN (argument but not formal):                     ║
║    T5 (OU dynamics), T7 (ε convergence), T8 (amplification),    ║
║    T10 (flip decomposition), T11 (contradiction)                 ║
║    = 5 results                                                   ║
║                                                                  ║
║  EMPIRICAL ONLY (no proof):                                      ║
║    T9 (lift 1.20), T12 (clones), T13 (eigenmodes),              ║
║    T14 (weak=eigen), T15 (wall), T16 (k scaling),               ║
║    T19 (non-local), T20 (self-cancel)                            ║
║    = 8 results                                                   ║
║                                                                  ║
║  PRIORITY FOR DERIVATION:                                        ║
║    1. T14 (weak = eigen) — unifies TSVF + spectral + gap field  ║
║    2. T16 (k = O(n^0.75)) — quantifies THE barrier              ║
║    3. T9 (lift 1.20) — needed for T10, T11                      ║
║    4. T12 (n/3 DOF) — connects to condensation theory           ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)


# ============================================================
# WHICH GAPS CAN WE CLOSE NOW?
# ============================================================

def closeable_gaps():
    print("""
╔══════════════════════════════════════════════════════════════════╗
║              CLOSEABLE GAPS                                      ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  GAP A: T14 (Weak values = eigenmode projections)                ║
║                                                                  ║
║    Weak value = Σ_sol w(sol) × sol[i] / Σ w(sol)               ║
║    where w(sol) = overlap(tension, sol)^4                        ║
║                                                                  ║
║    Eigenmode proj = Σ_mode <sol|mode><mode|i>                    ║
║                                                                  ║
║    WHY they're equal: both WEIGHT solutions by how well          ║
║    they match tension. Tension ∝ first eigenmode of signed L.    ║
║    So overlap^4 ∝ projection onto eigenspace.                    ║
║                                                                  ║
║    DERIVATION PATH: show that tension vector ≈ linear combo      ║
║    of top eigenvectors of signed Laplacian. Then overlap^power   ║
║    = amplified projection. QED.                                  ║
║                                                                  ║
║    FEASIBILITY: high. Tension IS a graph signal. Eigenvectors    ║
║    ARE the natural basis for graph signals. The connection is     ║
║    almost tautological.                                          ║
║                                                                  ║
║  GAP B: T9 (Error lift = 1.20)                                   ║
║                                                                  ║
║    We showed: lift comes from gap magnitude coherence.            ║
║    Gap = clause_tension - solution_marginal.                      ║
║    Gap is spatially correlated (d=1: +0.006, d=2: -0.005).      ║
║                                                                  ║
║    DERIVATION PATH: Gap = tension - true_signal.                 ║
║    Tension is NOISY version of true signal (85% noise).          ║
║    Noise is correlated because shared clauses → shared noise.    ║
║    Lift = 1 + noise_correlation / noise_variance.                ║
║    noise_correlation ≈ 0.006, noise_variance ≈ 0.43.            ║
║    Predicted: 1 + 0.006/0.43/0.29² ≈ 1.16.                    ║
║    Close to 1.20 but not exact.                                  ║
║                                                                  ║
║    FEASIBILITY: medium. Need better noise model.                 ║
║                                                                  ║
║  GAP C: T12 (n/3 = unfrozen fraction)                            ║
║                                                                  ║
║    We showed: frozen fraction ≈ 64% at threshold.                ║
║    Known from stat physics: freezing transition at αd ≈ 3.86.    ║
║    Frozen fraction = f(r - αd).                                  ║
║                                                                  ║
║    DERIVATION PATH: Use cavity method prediction for frozen      ║
║    fraction. At r=4.27: f_frozen ≈ 0.64 (matches our 57-64%).  ║
║    Then DOF = n(1-f) ≈ n/3.                                     ║
║                                                                  ║
║    FEASIBILITY: high. Known results in stat physics.             ║
║    Just need to CONNECT our measurement to their prediction.     ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    print_synthesis()
    closeable_gaps()
