#!/usr/bin/env python3
"""
EXPERIMENT 13: Carry Chain Gradient — Phase Transition in Security

From exp12: hybrid SHA-256 (no carry chains) has E[δH]=20, trivial collisions.
Real SHA-256 (full carry chains) has E[δH]=128, impossible collisions.

KEY QUESTION: How does security grow as we restore carry chains?

Define SHA-256(k): carry chains are broken after k consecutive P-positions.
- k=0: all P-positions use XOR (= hybrid, E[δH]≈20)
- k=32: full carry propagation (= real SHA-256, E[δH]≈128)

If the transition is GRADUAL → intermediate k gives feasible collisions
If the transition is SHARP → phase transition, with exploitable boundary
"""

import sys, os, random, math
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def carry_limited_add(a, b, max_chain):
    """
    Addition with carry chains limited to max_chain length.
    After max_chain consecutive P-positions, carry is killed.

    max_chain=0: pure XOR on P-positions (hybrid)
    max_chain=32: full addition (real)
    """
    if max_chain >= 32:
        return (a + b) & MASK

    n = 32
    result = 0
    carry = 0
    p_chain_length = 0

    for i in range(n):
        ai = (a >> i) & 1
        bi = (b >> i) & 1

        # GKP classification
        if ai == 1 and bi == 1:  # G
            p_chain_length = 0
            s = ai + bi + carry
            carry = 1  # G always generates
            result |= ((s & 1) << i)
        elif ai == 0 and bi == 0:  # K
            p_chain_length = 0
            s = ai + bi + carry
            carry = 0  # K always kills
            result |= ((s & 1) << i)
        else:  # P
            p_chain_length += 1
            if p_chain_length > max_chain:
                # Kill carry: use XOR
                result |= ((ai ^ bi) << i)
                carry = 0
                p_chain_length = 0
            else:
                # Allow carry propagation
                s = ai + bi + carry
                carry = 1 if s >= 2 else 0
                result |= ((s & 1) << i)

    return result & MASK


def sha256_k(W16, max_chain, num_rounds=64):
    """SHA-256 with carry chains limited to max_chain."""
    iv = list(IV)
    W = schedule_k(W16, max_chain)
    state = list(iv)

    for r in range(min(num_rounds, 64)):
        a, b, c, d, e, f, g, h = state

        s1 = carry_limited_add(h, sigma1(e), max_chain)
        s2 = carry_limited_add(s1, ch(e, f, g), max_chain)
        s3 = carry_limited_add(s2, K[r], max_chain)
        T1 = carry_limited_add(s3, W[r], max_chain)

        T2 = carry_limited_add(sigma0(a), maj(a, b, c), max_chain)

        state = [
            carry_limited_add(T1, T2, max_chain),
            a, b, c,
            carry_limited_add(d, T1, max_chain),
            e, f, g,
        ]

    return [(iv[i] + state[i]) & MASK for i in range(8)]


def schedule_k(W16, max_chain):
    """Message schedule with limited carry chains."""
    W = list(W16) + [0] * 48
    for t in range(16, 64):
        W[t] = carry_limited_add(
            carry_limited_add(
                carry_limited_add(sig1(W[t-2]), W[t-7], max_chain),
                sig0(W[t-15]), max_chain),
            W[t-16], max_chain)
    return W


def test_phase_transition(N=2000):
    """Measure E[δH] as function of max_chain length k."""
    print("\n--- TEST 1: SECURITY vs CARRY CHAIN LENGTH ---")

    k_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16, 20, 24, 32]

    print(f"{'k':>4} | {'E[δH]':>8} | {'std':>8} | {'min':>5} | {'P(δH<50)':>10} | Phase")
    print("-" * 60)

    results = {}

    for k in k_values:
        dh_list = []
        for _ in range(N):
            W1 = random_w16()
            W2 = random_w16()

            H1 = sha256_k(W1, k)
            H2 = sha256_k(W2, k)
            dh = sum(hw(H1[i] ^ H2[i]) for i in range(8))
            dh_list.append(dh)

        arr = np.array(dh_list)
        p_low = np.mean(arr < 50)

        phase = "BROKEN" if arr.mean() < 64 else ("TRANSITION" if arr.mean() < 120 else "SECURE")

        print(f"{k:>4} | {arr.mean():>8.2f} | {arr.std():>8.2f} | {arr.min():>5} | "
              f"{p_low:>10.6f} | {phase}")

        results[k] = {'mean': arr.mean(), 'std': arr.std(), 'min': arr.min(),
                       'p_low': p_low, 'dist': arr}

    # Find phase transition point
    for i in range(len(k_values) - 1):
        k1, k2 = k_values[i], k_values[i+1]
        m1, m2 = results[k1]['mean'], results[k2]['mean']
        if m1 < 64 and m2 >= 64:
            print(f"\n*** PHASE TRANSITION between k={k1} and k={k2}! ***")
            print(f"  k={k1}: E[δH]={m1:.2f}")
            print(f"  k={k2}: E[δH]={m2:.2f}")

    return results


def test_collision_at_transition(N=10000):
    """
    At the phase transition point, actively search for collisions.
    The transition is where collisions are easiest but function
    is closest to real SHA-256.
    """
    print("\n--- TEST 2: COLLISION SEARCH AT TRANSITION ---")

    # First find the transition k
    for k in [3, 4, 5, 6, 7, 8]:
        min_dh = 256
        best_pair = None

        for _ in range(N):
            W1 = random_w16()
            W2 = random_w16()

            H1 = sha256_k(W1, k)
            H2 = sha256_k(W2, k)
            dh = sum(hw(H1[i] ^ H2[i]) for i in range(8))

            if dh < min_dh:
                min_dh = dh
                best_pair = (W1, W2, H1, H2)

        print(f"  k={k}: min δH = {min_dh} in {N} pairs")

        if min_dh == 0:
            W1, W2, H1, H2 = best_pair
            print(f"  *** COLLISION FOUND at k={k}! ***")
            print(f"  W1[0]=0x{W1[0]:08x}, W2[0]=0x{W2[0]:08x}")


def test_distance_from_real(N=1000):
    """
    For each k: how different is SHA-256(k) from real SHA-256?
    The useful region is where SHA-256(k) ≈ SHA-256 but collisions exist.
    """
    print("\n--- TEST 3: DISTANCE SHA-256(k) vs REAL SHA-256 ---")

    print(f"{'k':>4} | {'dist(k, real)':>14} | {'dist(k, k) [δH]':>16} | {'Useful?'}")
    print("-" * 60)

    for k in [0, 1, 2, 3, 4, 5, 6, 8, 10, 16, 32]:
        dists_to_real = []
        dists_self = []

        for _ in range(N):
            W = random_w16()
            H_k = sha256_k(W, k)
            H_real = sha256_compress(W)
            d = sum(hw(H_k[i] ^ H_real[i]) for i in range(8))
            dists_to_real.append(d)

            W2 = random_w16()
            H_k2 = sha256_k(W2, k)
            d2 = sum(hw(H_k[i] ^ H_k2[i]) for i in range(8))
            dists_self.append(d2)

        mean_real = np.mean(dists_to_real)
        mean_self = np.mean(dists_self)

        useful = "YES" if mean_real < 64 and mean_self < 64 else "no"
        print(f"{k:>4} | {mean_real:>14.2f} | {mean_self:>16.2f} | {useful}")


def test_gradual_lift(N=5000):
    """
    The lifting strategy: find collision at k=0, then gradually increase k,
    adjusting the message to maintain collision property.

    At each step k→k+1: the collision BREAKS slightly.
    Can we REPAIR it cheaply?
    """
    print("\n--- TEST 4: GRADUAL LIFTING k=0 → k=32 ---")

    # Step 1: Find near-collision at k=0 (hybrid)
    best_pair = None
    best_dh = 256

    for _ in range(N):
        W1 = random_w16()
        W2 = random_w16()
        H1 = sha256_k(W1, 0)
        H2 = sha256_k(W2, 0)
        dh = sum(hw(H1[i] ^ H2[i]) for i in range(8))

        if dh < best_dh:
            best_dh = dh
            best_pair = (list(W1), list(W2))

    print(f"Best pair at k=0: δH = {best_dh}")

    if best_pair is None:
        print("No pairs found")
        return

    W1, W2 = best_pair

    # Step 2: Increase k and measure how δH changes
    print(f"\n{'k':>4} | {'δH':>6} | {'Δ from k-1':>11} | Status")
    print("-" * 40)

    prev_dh = best_dh
    for k in range(0, 33):
        H1 = sha256_k(W1, k)
        H2 = sha256_k(W2, k)
        dh = sum(hw(H1[i] ^ H2[i]) for i in range(8))

        delta = dh - prev_dh
        status = "COLLISION" if dh == 0 else ("near" if dh < 30 else "")
        print(f"{k:>4} | {dh:>6} | {delta:>+11d} | {status}")
        prev_dh = dh


def main():
    random.seed(42)

    print("=" * 60)
    print("EXPERIMENT 13: CARRY CHAIN GRADIENT")
    print("Phase transition: hybrid → real SHA-256")
    print("=" * 60)

    results = test_phase_transition(1500)
    test_collision_at_transition(5000)
    test_distance_from_real(500)
    test_gradual_lift(3000)

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)

if __name__ == "__main__":
    main()
