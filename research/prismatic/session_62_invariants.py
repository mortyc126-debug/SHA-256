"""
Session 62: Conservation laws / mod-q invariants of SHA round.

INVERSE CRYPTANALYSIS HYPOTHESIS:
  If R preserves some quantity Q(state) (modulo something), then:
    R(x) and R(x') with same Q(x) = Q(x') will have same Q(R(x)) = Q(R(x')).
  Different Q-classes never mix → collisions only WITHIN same class.

  This narrows collision search from full 2^256 to size of one Q-class.
  If Q has n distinct values, search is 2^256 / n.

Test for various candidate invariants:
1. Q(state) = popcount(state) mod q for q = 2, 3, 5, 7
2. Q(state) = sum of register values mod q
3. Q(state) = XOR of registers
4. Q(state) = quadratic forms

For uniform random R: only trivial invariants exist (Q = constant).
"""
import numpy as np
from session_46_correct_round import correct_round


def state_popcount(state):
    return sum(bin(int(x)).count('1') for x in state)


def state_sum(state):
    return sum(int(x) for x in state) & 0xFFFFFFFF


def state_xor(state):
    out = 0
    for x in state:
        out ^= int(x)
    return out


def first_register(state):
    return int(state[0])


def main():
    print("=== Session 62: Conservation laws / invariants of SHA round ===\n")
    rng = np.random.default_rng(0)
    NUM_SAMPLES = 1000

    print(f"  Test: for each candidate quantity Q, check if Q(state) ≡ Q(R(state)) mod q")
    print(f"        across {NUM_SAMPLES} random states.\n")

    candidates = {
        'popcount': state_popcount,
        'register_sum (32-bit add)': state_sum,
        'register XOR': state_xor,
        'first register value': first_register,
    }

    print(f"  {'invariant':<28}  {'mod q':>8}  {'preserved?':>15}")
    print(f"  {'-'*60}")

    for q in [2, 3, 5, 7, 11, 17, 257, 1<<32, None]:
        for name, Q in candidates.items():
            preserved = 0
            for _ in range(NUM_SAMPLES):
                state = [int(rng.integers(0, 2**32)) for _ in range(8)]
                Q_in = Q(state) if q is None else Q(state) % q
                new_state = correct_round(state)
                Q_out = Q(new_state) if q is None else Q(new_state) % q
                if Q_in == Q_out:
                    preserved += 1
            label = f"q = {q}" if q else "exact"
            verdict = f"{preserved}/{NUM_SAMPLES}"
            mark = ""
            if q is not None:
                expected_random = NUM_SAMPLES / q
                if preserved > expected_random * 1.5:
                    mark = " ⚠ ANOMALY"
                if preserved == NUM_SAMPLES:
                    mark = " ⚠ INVARIANT FOUND"
            else:
                if preserved == NUM_SAMPLES:
                    mark = " ⚠ INVARIANT FOUND"
            print(f"  {name:<28}  {label:>8}  {verdict:>15}{mark}")

    print(f"""

=== Theorem 62.1 (invariants test) ===

For each tested quantity Q and modulus q:
  - If Q(state) ≡ Q(R(state)) for ALL random samples: Q is an INVARIANT.
  - If preserved at random rate (1/q): no invariant.

Common candidate invariants:
  popcount, register sum, register XOR, single-register value.

For SHA-256: a "good" hash should have NO non-trivial invariants. Any
invariant would partition 2^256 states into Q-classes, narrowing collision
search to one class.

If we find Q with k classes preserved by R: collision search reduces from
2^128 to 2^128 / √k (since collisions cluster within classes).

For SHA-256 design: NO invariant should exist beyond trivial.
""")


if __name__ == "__main__":
    main()
