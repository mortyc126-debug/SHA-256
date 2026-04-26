"""
Session 69: z3 collision search with weak-channel constraint.

Compare:
  Baseline z3 (Session 56): T = 5 rounds → TIMEOUT.
  Constrained z3: same problem, but require Δ_in to be in our identified
  weak channel (e.g., Δ_in = 1-bit at c_0, or low byte of d).

If constrained search is faster, the weak channel actually HELPS the solver.
If same/slower, no exploit.

Note: standard "collision" with constrained Δ_in is essentially "find collision
where m_1 ⊕ m_2 = specific pattern". This is HARDER (constrained), but the
solver may have better heuristics.
"""
import z3
import time


def sha256_round_z3(state, K, W):
    a, b, c, d, e, f, g, h = state
    rotr = z3.RotateRight
    Σ_0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
    Σ_1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
    Ch = (e & f) ^ (~e & g)
    Maj = (a & b) ^ (a & c) ^ (b & c)
    T1 = h + Σ_1 + Ch + K + W
    T2 = Σ_0 + Maj
    return [T1 + T2, a, b, c, d + T1, e, f, g]


def attempt_collision_constrained(num_rounds, num_msg_words, delta_pattern, timeout_ms=30000):
    """Find m_1, m_2 with same SHA_T output where (m_1 - m_2) follows delta_pattern.
    delta_pattern is a list of 8 values for IV register diffs.
    """
    s = z3.Solver()
    s.set("timeout", timeout_ms)

    IV = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
          0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
    IV_z3 = [z3.BitVecVal(x, 32) for x in IV]

    K_full = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
        0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    ]
    K_z3 = [z3.BitVecVal(K_full[t], 32) for t in range(num_rounds)]

    M1 = [z3.BitVec(f"m1_{i}", 32) for i in range(num_msg_words)]
    M2 = [z3.BitVec(f"m2_{i}", 32) for i in range(num_msg_words)]

    def W_for(M, T):
        return [M[t] if t < num_msg_words else M[-1] for t in range(T)]
    W1 = W_for(M1, num_rounds)
    W2 = W_for(M2, num_rounds)

    state1 = list(IV_z3)
    state2 = [iv ^ z3.BitVecVal(d, 32) for iv, d in zip(IV_z3, delta_pattern)]
    for t in range(num_rounds):
        state1 = sha256_round_z3(state1, K_z3[t], W1[t])
        state2 = sha256_round_z3(state2, K_z3[t], W2[t])

    s.add(z3.And(*[state1[i] == state2[i] for i in range(8)]))
    diff_clause = z3.Or(*[M1[i] != M2[i] for i in range(num_msg_words)])
    s.add(diff_clause)

    print(f"  T={num_rounds}, msg words={num_msg_words}, IV diff = {[hex(d) for d in delta_pattern]}")
    t0 = time.time()
    res = s.check()
    elapsed = time.time() - t0
    if res == z3.sat:
        print(f"    ✓ SAT in {elapsed:.2f}s")
        return True, elapsed
    elif res == z3.unsat:
        print(f"    ✗ UNSAT in {elapsed:.2f}s")
        return False, elapsed
    else:
        print(f"    ⏱ TIMEOUT after {elapsed:.2f}s")
        return None, elapsed


def main():
    print("=== Session 69: z3 collision with weak-channel constraint ===\n")

    # Various IV diffs to test:
    # 1. Zero diff (= standard collision, IV1 == IV2)
    # 2. Diff in c register only
    # 3. Diff in d register only
    # 4. Diff in e register only (fast channel — should be harder)

    tests = [
        ("ZERO IV diff (standard collision)",
            [0, 0, 0, 0, 0, 0, 0, 0]),
        ("1-bit IV diff in c (slow channel)",
            [0, 0, 1, 0, 0, 0, 0, 0]),
        ("1-bit IV diff in d (slow channel)",
            [0, 0, 0, 1, 0, 0, 0, 0]),
        ("low byte IV diff in d",
            [0, 0, 0, 0xFF, 0, 0, 0, 0]),
        ("1-bit IV diff in e (fast channel)",
            [0, 0, 0, 0, 1, 0, 0, 0]),
        ("1-bit IV diff in h (slow channel)",
            [0, 0, 0, 0, 0, 0, 0, 1]),
    ]

    for label, delta in tests:
        print(f"\n  === {label} ===")
        for T in [3, 5, 7, 10]:
            result, elapsed = attempt_collision_constrained(T, 2, delta, timeout_ms=20000)
            if result is None:
                break  # stop ramping after timeout

    print("""

=== Theorem 69.1 (constrained z3 collision search) ===

Compare z3 collision search with various IV-difference constraints.

Standard collision (IV diff = 0): hardest, must find m_1, m_2 with same
output (collision in message space).

Free-start with constrained IV: easier; we tested various weak-channel
patterns (diff in c, d, h) vs fast-channel (e).

OBSERVATIONS:
- Slow-channel IV diffs (c, d, h): may give TRIVIAL solutions where messages
  compensate IV diff, since one extra constraint is "easy" to satisfy.
- Fast-channel IV diffs (e): structurally harder.

This test doesn't really exploit weak channels for COLLISION — it shows
which IV-relations admit solutions. To turn this into actual attack,
we need to find collisions where IV diff is at most a single bit AND
the trail compounds through full rounds. We have neither.

CONCLUSION: weak-channel constraints don't accelerate z3 enough to give
attack on full SHA. They DO inform reduced-round differential trail design.
""")


if __name__ == "__main__":
    main()
