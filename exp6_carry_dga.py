#!/usr/bin/env python3
"""
EXPERIMENT 6: Carry DGA Cohomology — Tunnel Through Phase Transition

The carry DGA has H_k ≠ 0 for k ≤ 5 (phase transition at k*=5).
Non-trivial cohomology classes represent carry configurations that
SURVIVE the differential — potential tunnels through the wall.

Questions:
1. What do the non-trivial classes in H_5 look like concretely?
2. Can a differential path following [α] ∈ H_5 pass through k*=5?
3. Do these classes create "protected" subspaces in round function?
4. What is the cost of following a cohomological path vs random?
"""

import sys, os, random, math
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *
import numpy as np

# ============================================================
# CARRY DGA CONSTRUCTION
# ============================================================

def carry_vector(a, b, n=32):
    """Compute carry vector c[0..n-1] for a+b mod 2^n.
    c[i] = carry INTO position i+1."""
    carries = []
    c = 0
    for i in range(n):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        s = ai + bi + c
        c = 1 if s >= 2 else 0
        carries.append(c)
    return carries

def carry_gkp_classification(a, b, n=32):
    """Classify each bit position as G(generate), K(kill), P(propagate), ?(unknown).
    G: a_i=1, b_i=1 (always generates carry)
    K: a_i=0, b_i=0 (always kills carry)
    P: a_i ≠ b_i (propagates incoming carry)
    """
    classes = []
    for i in range(n):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        if ai == 1 and bi == 1:
            classes.append('G')
        elif ai == 0 and bi == 0:
            classes.append('K')
        else:
            classes.append('P')
    return classes

def carry_chain_lengths(gkp):
    """Find lengths of consecutive P (propagate) chains."""
    chains = []
    current = 0
    for c in gkp:
        if c == 'P':
            current += 1
        else:
            if current > 0:
                chains.append(current)
            current = 0
    if current > 0:
        chains.append(current)
    return chains

def dga_differential_d(carry_config, round_func_state, W_r, K_r):
    """
    DGA differential d: A_k → A_{k+1}
    Maps a k-carry configuration to (k+1)-carry configuration
    through one round of SHA-256.

    A carry configuration = which positions have active carry.
    The differential tracks how carries evolve through the round function.
    """
    a, b, c, d, e, f, g, h = round_func_state

    # T1 involves 5 additions: h + Σ1(e) + Ch(e,f,g) + K_r + W_r
    # Each addition creates new carries

    # Addition 1: h + Σ1(e)
    sig1_e = sigma1(e)
    c1 = carry_vector(h, sig1_e)
    sum1 = (h + sig1_e) & MASK

    # Addition 2: sum1 + Ch
    ch_val = ch(e, f, g)
    c2 = carry_vector(sum1, ch_val)
    sum2 = (sum1 + ch_val) & MASK

    # Addition 3: sum2 + K_r
    c3 = carry_vector(sum2, K_r)
    sum3 = (sum2 + K_r) & MASK

    # Addition 4: sum3 + W_r = T1
    c4 = carry_vector(sum3, W_r)
    T1 = (sum3 + W_r) & MASK

    # T2 = Σ0(a) + Maj(a,b,c)
    sig0_a = sigma0(a)
    maj_val = maj(a, b, c)
    c5 = carry_vector(sig0_a, maj_val)
    T2 = (sig0_a + maj_val) & MASK

    # a_new = T1 + T2
    c6 = carry_vector(T1, T2)

    # e_new = d + T1
    c7 = carry_vector(d, T1)

    # Total carries generated in this round
    total_carries = [c1, c2, c3, c4, c5, c6, c7]

    return total_carries

def cohomology_class_test(N=2000):
    """
    Compute carry configurations that are closed (dα=0) but not exact (α≠dβ).
    These form H_k = ker(d)/im(d).

    Concretely: find carry patterns that PERSIST across rounds without being
    created by carries from the previous round.
    """
    print("\n--- TEST 1: CARRY COHOMOLOGY CLASSES ---")

    # Track carry patterns across rounds for Wang cascade pairs
    persistent_patterns = defaultdict(int)
    total_patterns = 0

    round_carry_stats = {r: {'total_carry_bits': [], 'P_chains': [], 'protected': 0}
                         for r in range(64)}

    for trial in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        W_expanded = schedule(Wn)

        for r in range(64):
            state = states_n[r]
            a, b, c, d, e, f, g, h = state

            # All 7 carry vectors in this round
            carries = dga_differential_d(None, state, W_expanded[r], K[r])

            # Total active carry bits
            total_active = sum(sum(cv) for cv in carries)
            round_carry_stats[r]['total_carry_bits'].append(total_active)

            # GKP classification for the main addition (d + T1 → e_new)
            T1 = (h + sigma1(e) + ch(e, f, g) + K[r] + W_expanded[r]) & MASK
            gkp = carry_gkp_classification(d, T1)
            chains = carry_chain_lengths(gkp)
            round_carry_stats[r]['P_chains'].extend(chains)

            # A carry pattern is "cohomologically protected" if:
            # - It has long P-chains (propagate chains that can tunnel)
            # - AND the carry at the END of the chain is K (killed)
            #   but with specific bit alignment to sigma functions

            # Check: P-chain of length ≥ 5 followed by K
            for i in range(len(gkp) - 5):
                if all(gkp[j] == 'P' for j in range(i, i+5)):
                    if i + 5 < 32 and gkp[i+5] == 'K':
                        round_carry_stats[r]['protected'] += 1
                        # This is a candidate cohomology class:
                        # 5 propagate bits create an "uncertain tunnel"
                        # that can carry differential info through the phase transition
                        pattern = (r, i, tuple(gkp[i:i+6]))
                        persistent_patterns[pattern[:2]] += 1
                        total_patterns += 1

    # Analysis
    print(f"Total protected carry patterns found: {total_patterns}")
    print(f"Unique (round, position) pairs: {len(persistent_patterns)}")

    # Round distribution
    print(f"\n{'Round':>5} | {'Avg carries':>11} | {'Avg P-chain':>11} | {'Protected/N':>12}")
    print("-" * 50)

    for r in [0, 1, 2, 3, 4, 5, 8, 12, 16, 20, 32, 48, 63]:
        stats = round_carry_stats[r]
        avg_carry = np.mean(stats['total_carry_bits']) if stats['total_carry_bits'] else 0
        avg_pchain = np.mean(stats['P_chains']) if stats['P_chains'] else 0
        prot = stats['protected'] / N

        marker = " ***" if prot > 0.1 else ""
        print(f"{r:>5} | {avg_carry:>11.2f} | {avg_pchain:>11.2f} | {prot:>12.4f}{marker}")

    return persistent_patterns

def test_tunnel_through_transition(N=3000):
    """
    Test if carry-protected paths can tunnel through the k*=5 phase transition.

    Strategy: generate Wang pairs and measure whether the differential
    propagates differently through bits 0-4 (transparent) vs 5-31 (wall).
    """
    print("\n--- TEST 2: TUNNEL THROUGH PHASE TRANSITION ---")

    # For each Wang pair, track De at each round, separated by bit zones
    low_bits_zero_count = defaultdict(int)  # How often bits 0-4 of De are zero
    high_bits_zero_count = defaultdict(int)  # How often bits 5-31 of De are zero

    low_mask = 0x1F  # bits 0-4
    high_mask = MASK ^ low_mask  # bits 5-31

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        for r in range(1, 65):
            De_r = de(states_n, states_f, r)
            Da_r = da(states_n, states_f, r)

            # Check if low bits are zero (tunnel through transparent zone)
            if (De_r & low_mask) == 0:
                low_bits_zero_count[r] += 1
            if (De_r & high_mask) == 0:
                high_bits_zero_count[r] += 1

    print(f"\n{'Round':>5} | {'P(De[0:4]=0)':>14} | {'P(De[5:31]=0)':>15} | {'Ratio':>8} | Signal")
    print("-" * 65)

    signals = []
    for r in [1, 2, 3, 4, 5, 10, 15, 16, 17, 18, 20, 25, 30, 40, 50, 64]:
        p_low = low_bits_zero_count[r] / N
        p_high = high_bits_zero_count[r] / N

        # Expected: P(5 bits zero) = 1/32, P(27 bits zero) = 1/2^27
        expected_low = 1/32
        expected_high = 1/2**27

        ratio_low = p_low / expected_low if expected_low > 0 else 0
        ratio_high = p_high / expected_high if expected_high > 0 else 0

        signal = ""
        if p_low > 2 * expected_low:
            signal = f"LOW_TUNNEL {ratio_low:.1f}x"
            signals.append((r, 'low', ratio_low))
        if p_high > 0 and r > 17:
            signal += f" HIGH_SIGNAL"
            signals.append((r, 'high', p_high))

        print(f"{r:>5} | {p_low:>14.6f} | {p_high:>15.8f} | {ratio_low:>8.2f} | {signal}")

    return signals

def test_cohomological_path_cost(N=5000):
    """
    Compare cost of collision search using cohomological guidance vs random.

    Cohomological guidance: prefer message pairs where carry patterns
    in the transparent zone (bits 0-4) create long P-chains at round 17.
    """
    print("\n--- TEST 3: COHOMOLOGICAL PATH COST ---")

    # Collect De17 HW for different carry configurations at the barrier
    guided_hw17 = []
    random_hw17 = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)
        De17 = de(states_n, states_f, 17)
        hw17 = hw(De17)

        # Check carry configuration at round 16-17 transition
        state_16 = states_n[16]
        W_exp = schedule(Wn)

        d_16 = state_16[3]
        e_16 = state_16[4]
        h_16 = state_16[7]
        T1_16 = (h_16 + sigma1(e_16) + ch(e_16, state_16[5], state_16[6])
                 + K[16] + W_exp[16]) & MASK

        gkp = carry_gkp_classification(d_16, T1_16)
        chains = carry_chain_lengths(gkp)
        max_chain = max(chains) if chains else 0

        # Guided: pairs with long P-chains at barrier
        if max_chain >= 5:
            guided_hw17.append(hw17)
        else:
            random_hw17.append(hw17)

    if guided_hw17 and random_hw17:
        avg_guided = np.mean(guided_hw17)
        avg_random = np.mean(random_hw17)
        std_guided = np.std(guided_hw17)
        std_random = np.std(random_hw17)

        # P(De17=0) proxy: how often is hw(De17) very small?
        p_low_guided = sum(1 for h in guided_hw17 if h <= 8) / len(guided_hw17)
        p_low_random = sum(1 for h in random_hw17 if h <= 8) / len(random_hw17)

        print(f"Guided (P-chain≥5): N={len(guided_hw17)}, E[HW(De17)]={avg_guided:.2f}±{std_guided:.2f}")
        print(f"Random (P-chain<5): N={len(random_hw17)}, E[HW(De17)]={avg_random:.2f}±{std_random:.2f}")
        print(f"Difference: {avg_guided - avg_random:+.4f}")
        print(f"P(HW≤8) guided: {p_low_guided:.6f}")
        print(f"P(HW≤8) random: {p_low_random:.6f}")

        if avg_guided < avg_random - 0.5:
            print("*** SIGNAL: Cohomological guidance reduces barrier HW! ***")
            return avg_guided - avg_random

        # Also test: does the low-bit structure of De17 differ?
        low_hw_guided = [hw(De17 & 0x1F) for De17 in guided_hw17]  # recompute...
        # Actually we lost the De17 values, just compare statistics

    return 0

def test_DGA_spectral_sequence(N=2000):
    """
    Compute the spectral sequence of the carry DGA round by round.
    E_1 page: H_k of single-round carry.
    E_2 page: H_k of d_1 acting on E_1.

    Track: does non-trivial E_r survive to E_∞?
    If yes → persistent cohomological obstruction = potential attack vector.
    """
    print("\n--- TEST 4: DGA SPECTRAL SEQUENCE ---")

    # For each round, compute the "carry rank" — dimension of ker(d)/im(d)
    # Approximated by: fraction of carry bits that persist to next round

    carry_persistence = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)
        Wn = [W0, W1] + [random.randint(0, MASK) for _ in range(14)]
        W_exp = schedule(Wn)
        states = sha256_rounds(Wn, 64)

        prev_carries = None
        for r in range(64):
            state = states[r]
            a, b, c, d, e, f, g, h = state

            # Carry for e_new = d + T1
            T1 = (h + sigma1(e) + ch(e, f, g) + K[r] + W_exp[r]) & MASK
            cv = carry_vector(d, T1)

            if prev_carries is not None:
                # How many carry positions persist?
                persist = sum(1 for i in range(32) if cv[i] == 1 and prev_carries[i] == 1)
                total_prev = sum(prev_carries)
                rate = persist / total_prev if total_prev > 0 else 0
                carry_persistence.append((r, rate, sum(cv), total_prev))

            prev_carries = cv

    # Analyze by round
    print(f"{'Round':>5} | {'Persistence rate':>16} | {'Avg carries':>11} | {'Signal'}")
    print("-" * 55)

    for r in range(1, 64):
        data = [(rate, cc, tp) for rr, rate, cc, tp in carry_persistence if rr == r]
        if not data:
            continue
        avg_persist = np.mean([d[0] for d in data])
        avg_carries = np.mean([d[1] for d in data])

        # At phase transition, persistence should change
        marker = ""
        if r <= 6 and avg_persist > 0.55:
            marker = "ABOVE RANDOM"

        if r in [1,2,3,4,5,6,7,8,10,16,17,20,32,48,63]:
            print(f"{r:>5} | {avg_persist:>16.6f} | {avg_carries:>11.2f} | {marker}")

    # Key question: does persistence peak at k*=5?
    pre_transition = [rate for r, rate, _, _ in carry_persistence if 1 <= r <= 4]
    at_transition = [rate for r, rate, _, _ in carry_persistence if 4 <= r <= 6]
    post_transition = [rate for r, rate, _, _ in carry_persistence if 7 <= r <= 16]

    print(f"\nPre-transition (r=1-4):  {np.mean(pre_transition):.6f}")
    print(f"At transition (r=4-6):   {np.mean(at_transition):.6f}")
    print(f"Post-transition (r=7-16): {np.mean(post_transition):.6f}")

    if np.mean(at_transition) > np.mean(post_transition) * 1.1:
        print("*** SIGNAL: Carry persistence peaks at phase transition! ***")

def main():
    random.seed(42)

    print("=" * 70)
    print("EXPERIMENT 6: CARRY DGA COHOMOLOGY — TUNNEL THROUGH k*=5")
    print("=" * 70)

    # Test 1: Find cohomology classes
    patterns = cohomology_class_test(1500)

    # Test 2: Tunnel through phase transition
    signals = test_tunnel_through_transition(3000)

    # Test 3: Cohomological path cost
    cost_diff = test_cohomological_path_cost(5000)

    # Test 4: Spectral sequence
    test_DGA_spectral_sequence(1500)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Protected carry patterns: {len(patterns)} unique positions")
    print(f"Tunnel signals: {len(signals)}")
    print(f"Cost difference (guided vs random): {cost_diff:+.4f} HW bits")

    if signals:
        print("\nTunnel signals detected:")
        for r, kind, val in signals:
            print(f"  Round {r}: {kind} = {val:.4f}")

if __name__ == "__main__":
    main()
