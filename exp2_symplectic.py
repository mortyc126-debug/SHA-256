#!/usr/bin/env python3
"""
EXPERIMENT 2: Symplectic Structure from Pipe Conservation

Pipe Conservation: (a+e)[r] = (d+h)[r+3] — exact for all rounds.
This defines a natural pairing: ω((a,e), (d,h)) = (a+e) - (d+h).

Questions:
1. Is the round function approximately symplectic (preserves ω)?
2. Does the differential δω have exploitable structure?
3. Can Arnold intersection theory give collision navigation?
4. Does the symplectic form survive under differential (Wang) pairs?

NEW: We define a full symplectic form on 8-register state and measure
its preservation under the round function.
"""

import sys, os, random, math
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def pipe_value(state):
    """Pipe invariant: a+e (mod 2^32)."""
    return (state[0] + state[4]) & MASK

def symplectic_form_ae_dh(state):
    """ω = (a+e) - (d+h) mod 2^32."""
    ae = (state[0] + state[4]) & MASK
    dh = (state[3] + state[7]) & MASK
    return (ae - dh) & MASK

def full_symplectic_matrix(state1, state2):
    """
    Define symplectic form on 8-dim state via natural pairing:
    ω(X, Y) = Σ (x_i * y_{i+4} - x_{i+4} * y_i) for i=0..3
    This pairs (a,b,c,d) with (e,f,g,h) — the two branches.
    """
    omega = 0
    for i in range(4):
        omega += state1[i] * state2[i + 4] - state1[i + 4] * state2[i]
    return omega & MASK

def test_pipe_conservation(N=2000):
    """Verify pipe conservation and measure residuals."""
    print("\n--- TEST 1: PIPE CONSERVATION VERIFICATION ---")

    exact_count = 0
    residuals = []

    for _ in range(N):
        W16 = random_w16()
        states = sha256_rounds(W16, 64)

        all_exact = True
        for r in range(60):  # (a+e)[r] = (d+h)[r+3]
            ae_r = pipe_value(states[r])
            dh_r3 = (states[r + 3][3] + states[r + 3][7]) & MASK
            diff = (ae_r - dh_r3) & MASK
            if diff != 0:
                all_exact = False
                residuals.append(diff)

        if all_exact:
            exact_count += 1

    print(f"Exact pipe conservation: {exact_count}/{N} messages")
    if residuals:
        print(f"Violations found: {len(residuals)}")
    else:
        print("PERFECT: 0 violations")

    return exact_count == N

def test_symplectic_preservation(N=2000):
    """Test if round function preserves symplectic form."""
    print("\n--- TEST 2: SYMPLECTIC FORM PRESERVATION UNDER ROUNDS ---")

    # For a pair of states X, Y: does ω(R(X), R(Y)) = ω(X, Y)?
    deviations = []

    for _ in range(N):
        W1 = random_w16()
        W2 = random_w16()

        states1 = sha256_rounds(W1, 64)
        states2 = sha256_rounds(W2, 64)

        for r in range(63):
            omega_before = full_symplectic_matrix(states1[r], states2[r])
            omega_after = full_symplectic_matrix(states1[r + 1], states2[r + 1])
            dev = (omega_after - omega_before) & MASK
            if dev != 0:
                deviations.append((r, dev))

    if not deviations:
        print("EXACT SYMPLECTIC PRESERVATION (unlikely)")
    else:
        print(f"Deviations per round: {len(deviations)} / {N * 63}")
        # Analyze structure of deviations
        round_dev = Counter(r for r, _ in deviations)
        print(f"Rounds with deviations: {len(round_dev)}/63")

        # HW distribution of deviations
        hw_devs = [hw(d) for _, d in deviations[:5000]]
        avg_hw = sum(hw_devs) / len(hw_devs) if hw_devs else 0
        print(f"Average HW of deviation: {avg_hw:.2f} (random=16)")

        return avg_hw, len(deviations) / (N * 63)

    return 0, 0

def test_differential_symplectic(N=2000):
    """Does symplectic form have structure under Wang differential?"""
    print("\n--- TEST 3: SYMPLECTIC FORM UNDER WANG DIFFERENTIAL ---")

    omega_diffs = {r: [] for r in range(65)}

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        for r in range(65):
            # Symplectic form of the DIFFERENCE state
            diff_state = [(states_f[r][i] - states_n[r][i]) & MASK for i in range(8)]
            omega = symplectic_form_ae_dh(diff_state)
            omega_diffs[r].append(omega)

    print(f"{'Round':>5} | {'P(ω=0)':>10} | {'E[HW(ω)]':>10} | {'unique':>8} | {'Signal':>8}")
    print("-" * 55)

    signals = []
    for r in [0, 1, 2, 3, 4, 5, 10, 15, 16, 17, 18, 20, 30, 40, 50, 60, 64]:
        if r > 64:
            continue
        vals = omega_diffs[r]
        p_zero = sum(1 for v in vals if v == 0) / len(vals)
        avg_hw_val = sum(hw(v) for v in vals) / len(vals)
        unique = len(set(vals))

        signal = ""
        if p_zero > 0.01:  # Well above 1/2^32
            signal = f"P(0)={p_zero:.3f}"
            signals.append((r, p_zero))
        if avg_hw_val < 14:
            signal += f" HW={avg_hw_val:.1f}"
            if (r, p_zero) not in [(s[0], s[1]) for s in signals]:
                signals.append((r, avg_hw_val))

        print(f"{r:>5} | {p_zero:>10.6f} | {avg_hw_val:>10.2f} | {unique:>8} | {signal}")

    return signals

def test_lagrangian_submanifold(N=2000):
    """
    Test if Wang cascade solutions lie on a Lagrangian submanifold.
    A Lagrangian submanifold L satisfies: ω|_L = 0 (symplectic form vanishes ON L).
    """
    print("\n--- TEST 4: LAGRANGIAN SUBMANIFOLD TEST ---")

    # Collect pairs of Wang solutions and test if ω between them vanishes
    solutions = []
    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)
        solutions.append((states_n[17], states_f[17]))  # State at barrier

    # Test ω(sol_i, sol_j) for pairs
    omega_vals = []
    n_pairs = min(N * (N - 1) // 2, 50000)
    tested = 0
    zeros = 0

    for i in range(min(N, 300)):
        for j in range(i + 1, min(N, 300)):
            # ω between normal states of different Wang pairs
            omega = full_symplectic_matrix(solutions[i][0], solutions[j][0])
            omega_vals.append(omega)
            if omega == 0:
                zeros += 1
            tested += 1

    p_zero = zeros / tested if tested > 0 else 0
    avg_hw_omega = sum(hw(v) for v in omega_vals) / len(omega_vals) if omega_vals else 0

    print(f"Pairs tested: {tested}")
    print(f"ω=0 count: {zeros} ({p_zero:.6f})")
    print(f"Average HW(ω): {avg_hw_omega:.2f} (random=16)")
    print(f"Expected P(ω=0) random: {1/2**32:.10f}")

    if p_zero > 10 / 2**32:
        print("*** SIGNAL: Symplectic form vanishes more than random! ***")
        print("Wang solutions may lie near a Lagrangian submanifold!")

    return p_zero, avg_hw_omega

def test_symplectic_gradient(N=1000):
    """
    Test if δω provides navigation toward collision.
    Near-collision: state where most of ΔH is zero.
    Does ω correlate with distance to collision?
    """
    print("\n--- TEST 5: SYMPLECTIC GRADIENT (collision navigation) ---")

    omega_vs_hw = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        # Final hash difference
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        delta_H = [H_n[i] ^ H_f[i] for i in range(8)]
        hw_H = sum(hw(d) for d in delta_H)

        # Symplectic form at various rounds
        for r in [17, 20, 30, 40, 50, 60, 64]:
            if r > len(states_n) - 1:
                continue
            diff_state = [(states_f[r][i] - states_n[r][i]) & MASK for i in range(8)]
            omega = symplectic_form_ae_dh(diff_state)
            omega_vs_hw.append((r, hw(omega), hw_H))

    # Correlation between ω at each round and final δH
    print(f"{'Round':>5} | {'corr(HW(ω), HW(δH))':>22} | {'avg HW(ω)':>10}")
    print("-" * 45)

    for r in [17, 20, 30, 40, 50, 60, 64]:
        data = [(ohw, hhw) for rr, ohw, hhw in omega_vs_hw if rr == r]
        if not data:
            continue
        omega_hws = [d[0] for d in data]
        h_hws = [d[1] for d in data]

        mean_o = sum(omega_hws) / len(omega_hws)
        mean_h = sum(h_hws) / len(h_hws)

        cov = sum((o - mean_o) * (h - mean_h) for o, h in zip(omega_hws, h_hws)) / len(data)
        std_o = math.sqrt(sum((o - mean_o)**2 for o in omega_hws) / len(data))
        std_h = math.sqrt(sum((h - mean_h)**2 for h in h_hws) / len(data))

        corr = cov / (std_o * std_h) if std_o > 0 and std_h > 0 else 0
        print(f"{r:>5} | {corr:>22.6f} | {mean_o:>10.2f}")

def main():
    random.seed(42)

    print("=" * 70)
    print("EXPERIMENT 2: SYMPLECTIC STRUCTURE OF SHA-256")
    print("=" * 70)

    # Test 1: Pipe conservation
    pipe_ok = test_pipe_conservation(1000)

    # Test 2: Symplectic preservation
    avg_hw_dev, dev_rate = test_symplectic_preservation(500)

    # Test 3: Differential symplectic
    signals = test_differential_symplectic(2000)

    # Test 4: Lagrangian submanifold
    p_zero, avg_hw_L = test_lagrangian_submanifold(500)

    # Test 5: Symplectic gradient
    test_symplectic_gradient(1000)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Pipe conservation: {'EXACT' if pipe_ok else 'BROKEN'}")
    print(f"Symplectic preservation deviation rate: {dev_rate:.4f}")
    print(f"Average HW of deviation: {avg_hw_dev:.2f}")
    print(f"Wang differential ω signals: {len(signals)} rounds with structure")
    print(f"Lagrangian test P(ω=0): {p_zero:.8f} (random: {1/2**32:.10f})")

    if signals:
        print("\nSignificant rounds:")
        for r, val in signals:
            print(f"  Round {r}: {val}")

if __name__ == "__main__":
    main()
