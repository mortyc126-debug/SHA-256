#!/usr/bin/env python3
"""
EXPERIMENT 14: Carry Topology Attack (CTA)

Don't attack SHA-256 as a function.
Find INPUTS where SHA-256 attacks ITSELF.

For specific messages M, the GKP pattern may create a carry DAG
with a small min-cut — meaning carry can't propagate effectively.
For such M, SHA-256 ≈ hybrid → weak → collision feasible.

Method:
1. Compute GKP pattern for all 448 additions (7 per round × 64 rounds)
2. Build carry DAG
3. Compute carry flow metrics (chain lengths, bottlenecks)
4. Search for messages with anomalously weak carry topology
5. Test: do weak-topology messages have lower collision resistance?
"""

import sys, os, random, math
import numpy as np
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *


def analyze_carry_topology(W16):
    """
    Full carry topology analysis for one message.
    Returns metrics about carry chain structure across all 64 rounds.
    """
    states = sha256_rounds(W16, 64)
    W = schedule(W16)

    metrics = {
        'total_k': 0,          # Total K-positions (carry killers)
        'total_g': 0,          # Total G-positions (carry generators)
        'total_p': 0,          # Total P-positions (carry propagators)
        'max_p_chain': 0,      # Longest P-chain across all additions
        'avg_p_chain': 0,      # Average P-chain length
        'bottleneck_round': 0, # Round with most K-positions (worst bottleneck)
        'min_k_round': 64,     # Round with fewest K-positions (weakest link)
        'k_per_round': [],     # K-count per round
        'max_chain_per_round': [],  # Max P-chain per round
        'flow_score': 0,       # Overall carry flow score
        'chain_lengths': [],   # All P-chain lengths
    }

    all_chains = []
    k_per_round = []
    max_chain_per_round = []

    for r in range(64):
        a, b, c, d, e, f, g, h = states[r]

        # All 7 additions in this round
        sig1_e = sigma1(e)
        s1 = (h + sig1_e) & MASK
        ch_val = ch(e, f, g)
        s2 = (s1 + ch_val) & MASK
        s3 = (s2 + K[r]) & MASK
        T1 = (s3 + W[r]) & MASK
        sig0_a = sigma0(a)
        maj_val = maj(a, b, c)
        T2 = (sig0_a + maj_val) & MASK

        additions = [
            (h, sig1_e),      # T1 step 1
            (s1, ch_val),     # T1 step 2
            (s2, K[r]),       # T1 step 3
            (s3, W[r]),       # T1 step 4
            (sig0_a, maj_val),# T2
            (T1, T2),         # a_new
            (d, T1),          # e_new
        ]

        round_k = 0
        round_max_chain = 0

        for x, y in additions:
            gkp = carry_gkp_classification(x, y)

            g_count = gkp.count('G')
            k_count = gkp.count('K')
            p_count = gkp.count('P')

            metrics['total_g'] += g_count
            metrics['total_k'] += k_count
            metrics['total_p'] += p_count
            round_k += k_count

            # P-chain analysis
            chain = 0
            for c in gkp:
                if c == 'P':
                    chain += 1
                else:
                    if chain > 0:
                        all_chains.append(chain)
                        round_max_chain = max(round_max_chain, chain)
                    chain = 0
            if chain > 0:
                all_chains.append(chain)
                round_max_chain = max(round_max_chain, chain)

        k_per_round.append(round_k)
        max_chain_per_round.append(round_max_chain)

    metrics['k_per_round'] = k_per_round
    metrics['max_chain_per_round'] = max_chain_per_round
    metrics['chain_lengths'] = all_chains

    if all_chains:
        metrics['max_p_chain'] = max(all_chains)
        metrics['avg_p_chain'] = np.mean(all_chains)

    metrics['bottleneck_round'] = np.argmax(k_per_round)
    metrics['min_k_round'] = np.argmin(k_per_round)

    # Flow score: higher = more carry flow (weaker bottleneck)
    # Based on: product of (1 - k_fraction) across rounds
    k_fractions = [k / (7 * 32) for k in k_per_round]
    metrics['flow_score'] = np.prod([1 - kf for kf in k_fractions])

    # Weakest-link score: the round with fewest K-positions
    metrics['weakest_k'] = min(k_per_round)
    metrics['strongest_k'] = max(k_per_round)

    return metrics


def test_topology_distribution(N=3000):
    """Measure distribution of carry topology metrics across random messages."""
    print("\n--- TEST 1: CARRY TOPOLOGY DISTRIBUTION ---")

    all_metrics = []

    for _ in range(N):
        W16 = random_w16()
        m = analyze_carry_topology(W16)
        all_metrics.append(m)

    # Analyze distributions
    max_chains = [m['max_p_chain'] for m in all_metrics]
    avg_chains = [m['avg_p_chain'] for m in all_metrics]
    weakest_k = [m['weakest_k'] for m in all_metrics]
    strongest_k = [m['strongest_k'] for m in all_metrics]
    total_k = [m['total_k'] for m in all_metrics]

    print(f"Max P-chain:  mean={np.mean(max_chains):.2f}, std={np.std(max_chains):.2f}, "
          f"min={min(max_chains)}, max={max(max_chains)}")
    print(f"Avg P-chain:  mean={np.mean(avg_chains):.4f}, std={np.std(avg_chains):.4f}")
    print(f"Weakest K:    mean={np.mean(weakest_k):.2f}, std={np.std(weakest_k):.2f}, "
          f"min={min(weakest_k)}, max={max(weakest_k)}")
    print(f"Strongest K:  mean={np.mean(strongest_k):.2f}")
    print(f"Total K:      mean={np.mean(total_k):.1f}, std={np.std(total_k):.1f}")
    print(f"Expected K:   {7 * 32 * 64 * 0.25:.1f} (25% of {7*32*64})")

    # Distribution of max P-chain
    print(f"\nMax P-chain distribution:")
    chain_counter = defaultdict(int)
    for mc in max_chains:
        chain_counter[mc] += 1
    for length in sorted(chain_counter.keys()):
        count = chain_counter[length]
        bar = "#" * min(count * 50 // N, 50)
        print(f"  {length:>3}: {count:>5} ({count/N*100:>5.1f}%) {bar}")

    return all_metrics


def test_topology_collision_correlation(N=3000):
    """
    KEY TEST: Does weak carry topology correlate with lower δH?
    If yes → CTA works.
    """
    print("\n--- TEST 2: TOPOLOGY ↔ COLLISION CORRELATION ---")

    data = []

    for _ in range(N):
        W0 = random.randint(0, MASK)
        W1 = random.randint(0, MASK)

        Wn, Wf, DWs, states_n, states_f = wang_cascade(W0, W1)

        # Topology of normal message
        m = analyze_carry_topology(Wn)

        # Hash difference
        H_n = sha256_compress(Wn)
        H_f = sha256_compress(Wf)
        delta_H = [H_n[i] ^ H_f[i] for i in range(8)]
        hw_delta = sum(hw(d) for d in delta_H)

        data.append({
            'hw_delta': hw_delta,
            'max_p_chain': m['max_p_chain'],
            'weakest_k': m['weakest_k'],
            'total_k': m['total_k'],
            'avg_p_chain': m['avg_p_chain'],
        })

    # Correlations
    hw_arr = np.array([d['hw_delta'] for d in data])
    max_chain_arr = np.array([d['max_p_chain'] for d in data])
    weakest_k_arr = np.array([d['weakest_k'] for d in data])
    total_k_arr = np.array([d['total_k'] for d in data])
    avg_chain_arr = np.array([d['avg_p_chain'] for d in data])

    corr_chain = np.corrcoef(hw_arr, max_chain_arr)[0, 1]
    corr_weak_k = np.corrcoef(hw_arr, weakest_k_arr)[0, 1]
    corr_total_k = np.corrcoef(hw_arr, total_k_arr)[0, 1]
    corr_avg = np.corrcoef(hw_arr, avg_chain_arr)[0, 1]

    threshold = 3 / np.sqrt(N)

    print(f"corr(δH, max_P_chain):  {corr_chain:+.6f} {'***' if abs(corr_chain) > threshold else ''}")
    print(f"corr(δH, weakest_K):    {corr_weak_k:+.6f} {'***' if abs(corr_weak_k) > threshold else ''}")
    print(f"corr(δH, total_K):      {corr_total_k:+.6f} {'***' if abs(corr_total_k) > threshold else ''}")
    print(f"corr(δH, avg_P_chain):  {corr_avg:+.6f} {'***' if abs(corr_avg) > threshold else ''}")
    print(f"Threshold (3/√N):       {threshold:.6f}")

    # Split by topology quality
    median_k = np.median(total_k_arr)
    weak_topo = hw_arr[total_k_arr < median_k]  # Less K = more carry flow
    strong_topo = hw_arr[total_k_arr >= median_k]

    print(f"\nWeak topology (few K):  E[δH]={weak_topo.mean():.4f}, N={len(weak_topo)}")
    print(f"Strong topology (many K): E[δH]={strong_topo.mean():.4f}, N={len(strong_topo)}")
    print(f"Difference: {weak_topo.mean() - strong_topo.mean():+.4f}")

    # Also split by max P-chain
    median_chain = np.median(max_chain_arr)
    long_chain = hw_arr[max_chain_arr > median_chain]
    short_chain = hw_arr[max_chain_arr <= median_chain]

    print(f"\nLong P-chains:  E[δH]={long_chain.mean():.4f}")
    print(f"Short P-chains: E[δH]={short_chain.mean():.4f}")
    print(f"Difference: {long_chain.mean() - short_chain.mean():+.4f}")

    return data


def test_search_weak_topology(N=5000):
    """
    Actively search for messages with anomalously weak carry topology.
    Then test if these messages are easier to collide.
    """
    print("\n--- TEST 3: SEARCH FOR WEAK-TOPOLOGY MESSAGES ---")

    # Score: lower total_K + longer max_P_chain = weaker topology
    best_score = -float('inf')
    best_W = random_w16()
    scores = []

    for _ in range(N):
        W16 = random_w16()
        m = analyze_carry_topology(W16)

        # Score: maximize P-chain length, minimize K-count
        score = m['max_p_chain'] * 100 - m['total_k']
        scores.append(score)

        if score > best_score:
            best_score = score
            best_W = list(W16)

    best_m = analyze_carry_topology(best_W)

    print(f"Score distribution: mean={np.mean(scores):.1f}, std={np.std(scores):.1f}")
    print(f"Best score: {best_score:.1f}")
    print(f"Best message topology:")
    print(f"  max_P_chain = {best_m['max_p_chain']}")
    print(f"  total_K = {best_m['total_k']}")
    print(f"  weakest_K round = {best_m['weakest_k']}")

    # Hill-climb to improve
    current_W = list(best_W)
    current_score = best_score
    improvements = 0

    for step in range(3000):
        trial_W = list(current_W)
        word = random.randint(0, 15)
        bit = random.randint(0, 31)
        trial_W[word] ^= (1 << bit)

        m = analyze_carry_topology(trial_W)
        trial_score = m['max_p_chain'] * 100 - m['total_k']

        if trial_score > current_score:
            current_score = trial_score
            current_W = trial_W
            improvements += 1

    m_final = analyze_carry_topology(current_W)
    print(f"\nAfter hill-climb ({improvements} improvements):")
    print(f"  Score: {current_score:.1f}")
    print(f"  max_P_chain = {m_final['max_p_chain']}")
    print(f"  total_K = {m_final['total_k']}")

    # Test collision resistance of best message
    print(f"\nTesting collision resistance of weak-topology message...")
    dh_weak = []
    dh_random = []

    for _ in range(2000):
        # Weak topology
        Wf = list(current_W)
        Wf[0] = (Wf[0] + 1) & MASK
        H_n = sha256_compress(current_W)
        H_f = sha256_compress(Wf)
        dh = sum(hw(H_n[i] ^ H_f[i]) for i in range(8))
        dh_weak.append(dh)

        # Random baseline
        W_rand = random_w16()
        W_rand_f = list(W_rand)
        W_rand_f[0] = (W_rand_f[0] + 1) & MASK
        H_rn = sha256_compress(W_rand)
        H_rf = sha256_compress(W_rand_f)
        dh_r = sum(hw(H_rn[i] ^ H_rf[i]) for i in range(8))
        dh_random.append(dh_r)

    print(f"Weak topology: E[δH]={np.mean(dh_weak):.2f}, min={min(dh_weak)}")
    print(f"Random:        E[δH]={np.mean(dh_random):.2f}, min={min(dh_random)}")

    if np.mean(dh_weak) < np.mean(dh_random) - 1:
        print("*** SIGNAL: Weak-topology messages have lower collision resistance! ***")

    return current_W, m_final


def test_per_round_bottleneck(N=1000):
    """
    Analyze the carry bottleneck structure round by round.
    Is there a specific round where the bottleneck is exploitable?
    """
    print("\n--- TEST 4: PER-ROUND BOTTLENECK ANALYSIS ---")

    round_k_distributions = [[] for _ in range(64)]

    for _ in range(N):
        W16 = random_w16()
        m = analyze_carry_topology(W16)

        for r in range(64):
            round_k_distributions[r].append(m['k_per_round'][r])

    print(f"{'Round':>5} | {'Mean K':>8} | {'Std K':>8} | {'Min K':>6} | {'Max K':>6}")
    print("-" * 45)

    for r in [0,1,2,3,4,5,8,16,17,20,32,48,63]:
        arr = np.array(round_k_distributions[r])
        print(f"{r:>5} | {arr.mean():>8.2f} | {arr.std():>8.2f} | {arr.min():>6} | {arr.max():>6}")

    # Find: which round has the LOWEST minimum K?
    min_k_by_round = [np.min(d) for d in round_k_distributions]
    weakest_round = np.argmin(min_k_by_round)
    print(f"\nWeakest round (lowest min-K): round {weakest_round} (min K = {min_k_by_round[weakest_round]})")

    # K-count depends on K constants — analyze K[r] structure
    print(f"\nK-constant influence:")
    for r in [0, 1, 16, 17, weakest_round]:
        k_hw = hw(K[r])
        print(f"  Round {r:>2}: K[r]=0x{K[r]:08x}, HW(K)={k_hw}, "
              f"mean round K-positions={np.mean(round_k_distributions[r]):.2f}")


def test_cross_round_carry_flow(N=500):
    """
    Measure CROSS-ROUND carry flow: does carry from round r
    influence the GKP pattern of round r+1?

    If yes → carry topology is NOT independent per round,
    and a bottleneck in one round propagates.
    """
    print("\n--- TEST 5: CROSS-ROUND CARRY FLOW ---")

    cross_correlations = []

    for _ in range(N):
        W16 = random_w16()
        m = analyze_carry_topology(W16)

        k_per_round = m['k_per_round']

        # Correlation between K-count in consecutive rounds
        for r in range(63):
            cross_correlations.append((k_per_round[r], k_per_round[r+1]))

    k_curr = np.array([c[0] for c in cross_correlations])
    k_next = np.array([c[1] for c in cross_correlations])

    corr = np.corrcoef(k_curr, k_next)[0, 1]
    print(f"Correlation K[r] ↔ K[r+1]: {corr:+.6f}")

    # Longer range
    for lag in [1, 2, 3, 4, 5, 8, 16]:
        pairs = []
        for _ in range(N):
            W16 = random_w16()
            m = analyze_carry_topology(W16)
            k_pr = m['k_per_round']
            for r in range(64 - lag):
                pairs.append((k_pr[r], k_pr[r + lag]))

        k1 = np.array([p[0] for p in pairs])
        k2 = np.array([p[1] for p in pairs])
        c = np.corrcoef(k1, k2)[0, 1]
        marker = " ***" if abs(c) > 0.05 else ""
        print(f"  Lag {lag:>2}: corr = {c:+.6f}{marker}")


def main():
    random.seed(42)

    print("=" * 60)
    print("EXPERIMENT 14: CARRY TOPOLOGY ATTACK (CTA)")
    print("Find inputs where SHA-256 attacks itself")
    print("=" * 60)

    all_metrics = test_topology_distribution(2000)
    data = test_topology_collision_correlation(2000)
    best_W, best_m = test_search_weak_topology(3000)
    test_per_round_bottleneck(500)
    test_cross_carry = test_cross_round_carry_flow(500)

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)

if __name__ == "__main__":
    main()
