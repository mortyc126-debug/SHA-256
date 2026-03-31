#!/usr/bin/env python3
"""
EXP 116: Multiverse Collision — Parallel Universes ARE Real

ASSUMPTION: Many-Worlds Interpretation is correct.
Every quantum measurement splits the universe.
We have access to ALL branches simultaneously.

THIS IS NOT SCIENCE FICTION — it's the Deutsch-Jozsa argument:
A quantum computer ALREADY exploits parallel universes (per Deutsch).
The question: can we do BETTER than BHT's 2^85.3?

THREE MODELS:

Model A: "Universe Farming"
  - Set up quantum computer with 256 qubits in superposition
  - Each branch of the multiverse computes a different hash
  - 2^256 branches exist → ALL hashes computed "at once"
  - Problem: how to EXTRACT the collision from 2^256 branches?
  - Answer: Grover search → back to 2^85.3 (BHT)

Model B: "Multiverse Communication"
  - If we could COMMUNICATE between branches (not standard QM!)
  - Each branch checks one pair → 2^128 branches check all pairs
  - One branch finds collision, broadcasts to us → O(1)
  - Problem: QM forbids inter-branch communication (no-signaling theorem)

Model C: "Anthropic Selection"
  - Run the search. In SOME branch, we get lucky early.
  - We only care about branches where WE succeed.
  - "We" = the version of us that found the collision.
  - Expected attempts in OUR branch: still 2^128
  - (Selection bias doesn't help — it's retroactive, not predictive)

SIMULATION: Model all three and measure effective speedup.
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def model_A_quantum_parallelism(hash_bits=24):
    """Model A: Quantum superposition of all inputs.
    The multiverse computes ALL hashes, but extraction requires Grover."""
    print(f"\n--- MODEL A: QUANTUM PARALLELISM ({hash_bits}-bit hash) ---")

    # N possible messages = 2^512 (too many to simulate)
    # Use truncated hash to simulate
    N_total = 2 ** hash_bits

    # Grover search over N_total items for collision:
    # BHT: store 2^(n/3), Grover over rest → 2^(n/3) total
    bht_cost = 2 ** (hash_bits / 3)

    # Standard birthday: 2^(n/2)
    birthday_cost = 2 ** (hash_bits / 2)

    # Multiverse "computes all" but extraction = Grover
    # No better than BHT!

    print(f"  Hash space: 2^{hash_bits}")
    print(f"  Birthday: 2^{hash_bits/2:.1f} = {int(birthday_cost)}")
    print(f"  BHT (quantum): 2^{hash_bits/3:.1f} = {int(bht_cost)}")
    print(f"  Multiverse compute: 2^{hash_bits} (all branches)")
    print(f"  But EXTRACTION: still 2^{hash_bits/3:.1f} (Grover)")
    print(f"")
    print(f"  VERDICT: Multiverse parallelism = Grover = BHT")
    print(f"  The universes compute for free, but READING the answer costs.")

    # Simulate: generate all hashes, find collision (trivial at this scale)
    if hash_bits <= 20:
        hashes = {}
        collisions = 0
        for m in range(min(N_total, 2**20)):
            W16 = [m] + [0] * 15  # Deterministic message from index
            H = sha256_compress(W16)
            h_trunc = H[0] & ((1 << hash_bits) - 1)
            if h_trunc in hashes:
                collisions += 1
                if collisions == 1:
                    print(f"  First collision at message #{m}")
            else:
                hashes[h_trunc] = m

        print(f"  Total collisions in 2^{hash_bits} space: {collisions}")
        print(f"  (Expected by pigeonhole: ~{N_total - 2**hash_bits * (1 - ((2**hash_bits - 1)/2**hash_bits)**N_total):.0f})")

def model_B_communication(hash_bits=24):
    """Model B: What if branches could communicate?
    This violates no-signaling but let's calculate the gain."""
    print(f"\n--- MODEL B: INTER-BRANCH COMMUNICATION ({hash_bits}-bit) ---")
    print(f"  (VIOLATES quantum mechanics — thought experiment only)")

    N = 2 ** hash_bits

    # If K branches work in parallel, each checking 1 pair:
    # Need 2^(n/2) branches for birthday → each branch does O(1) work
    # Total: O(1) per branch, 2^(n/2) branches

    birthday_branches = 2 ** (hash_bits / 2)

    # But with communication: even better
    # All branches report to a coordinator. Coordinator stores all hashes.
    # Need: 2^(n/2) branches to generate enough messages
    # Communication cost per branch: O(n) bits (send hash back)
    # Coordinator: O(2^(n/2) × n) memory

    print(f"  Branches needed: 2^{hash_bits/2:.0f} = {int(birthday_branches)}")
    print(f"  Work per branch: O(1) (compute 1 hash)")
    print(f"  Communication: {hash_bits} bits per branch")
    print(f"  Coordinator memory: 2^{hash_bits/2:.0f} × {hash_bits} bits")
    print(f"  Total time: O(1) parallel (!!)")
    print(f"")
    print(f"  For SHA-256:")
    print(f"    Branches: 2^128")
    print(f"    Work per branch: 1 hash = O(64 rounds)")
    print(f"    Communication: 256 bits per branch")
    print(f"    COLLISION IN O(1) WALL-CLOCK TIME!")
    print(f"")
    print(f"  BUT: no-signaling theorem prevents this.")
    print(f"  The collision EXISTS in the multiverse but we can't READ it.")

    # Simulate with threads-as-branches
    if hash_bits <= 20:
        t0 = time.time()
        # "Parallel" search (sequential simulation)
        hashes = {}
        for branch in range(int(birthday_branches) * 3):
            W16 = random_w16()
            H = sha256_compress(W16)
            h_trunc = H[0] & ((1 << hash_bits) - 1)
            if h_trunc in hashes:
                t1 = time.time()
                print(f"  Simulated: collision at branch #{branch+1} ({t1-t0:.3f}s)")
                print(f"  (Would be O(1) with real parallel universes)")
                return
            hashes[h_trunc] = W16

def model_C_anthropic_selection(N_trials=10000):
    """Model C: Anthropic selection — we only exist in lucky branches.
    Does this help? (Spoiler: no, because it's retroactive)"""
    print(f"\n--- MODEL C: ANTHROPIC SELECTION ---")

    # Simulate: in each "universe", we search for collision
    # on tiny hash (8 bits). Record when each universe finds it.

    hash_bits = 12
    find_times = []

    for trial in range(N_trials):
        hashes = {}
        for step in range(10000):
            W16 = random_w16()
            H = sha256_compress(W16)
            h_trunc = H[0] & ((1 << hash_bits) - 1)
            if h_trunc in hashes:
                find_times.append(step + 1)
                break
            hashes[h_trunc] = W16

    ft = np.array(find_times)
    expected_birthday = 2 ** (hash_bits / 2)

    print(f"  {hash_bits}-bit hash, {N_trials} universes:")
    print(f"  Expected birthday: 2^{hash_bits/2:.0f} = {int(expected_birthday)}")
    print(f"  Mean find time: {ft.mean():.1f}")
    print(f"  Median find time: {np.median(ft):.1f}")
    print(f"  Min find time: {ft.min()} (luckiest universe)")
    print(f"  Max find time: {ft.max()} (unluckiest universe)")

    # Anthropic selection: we ARE the min branch
    print(f"\n  Anthropic argument:")
    print(f"    'We only experience the branch where we found it fast'")
    print(f"    Luckiest branch: {ft.min()} steps (out of {N_trials} universes)")
    print(f"    Expected minimum of {N_trials} exponentials: ~{expected_birthday / math.log(N_trials):.1f}")

    # Scale to SHA-256
    N_universes = 2 ** 128  # Suppose this many branches
    expected_min = 2**128 / (128 * math.log(2))  # min of N exponentials ≈ mean/ln(N)
    print(f"\n  Scaled to SHA-256 with 2^128 universe branches:")
    print(f"    Mean per universe: 2^128")
    print(f"    Expected min of 2^128 universes: 2^128 / ln(2^128)")
    print(f"    = 2^128 / (128 × ln2) ≈ 2^128 / 88.7 ≈ 2^{128 - math.log2(88.7):.1f}")
    print(f"    Still ≈ 2^121.5 — only 6.5 bits improvement!")
    print(f"")
    print(f"  VERDICT: Even living in the luckiest of 2^128 universes")
    print(f"  only saves ~6.5 bits. Still 2^121.5. Not a real shortcut.")

def model_D_quantum_many_worlds():
    """Model D: Deutsch's argument — quantum IS multiverse."""
    print(f"\n--- MODEL D: DEUTSCH INTERPRETATION ---")
    print(f"""
  David Deutsch's argument (1985, 1997):

  A quantum computer with N qubits processes 2^N branches simultaneously.
  Each branch is a "parallel universe" computing independently.
  The quantum algorithm's power comes from INTERFERENCE between branches.

  For collision search (BHT):
    - 256 qubits → 2^256 branches, each with a different message
    - All branches compute SHA-256 in parallel
    - Grover's interference amplifies branches with collision
    - After 2^85.3 interference steps → collision found

  WHAT THE MULTIVERSE GIVES:  2^256 parallel computations
  WHAT INTERFERENCE EXTRACTS: answer in 2^85.3 steps
  EXTRACTION OVERHEAD:         2^85.3 / 2^256 = tiny fraction

  The gap between "computed" (2^256) and "extracted" (2^85.3)
  is the INFORMATION-THEORETIC COST of finding a needle in a haystack.
  Even with all universes computing, POINTING TO the right one costs work.

  FUNDAMENTAL LIMIT (BBBV theorem, 1997):
    Quantum search requires Ω(√N) queries.
    For collision on 2^256: Ω(2^85.3) queries minimum.
    No interpretation of QM can beat this.
    Not many-worlds, not Copenhagen, not pilot wave — NONE.
""")

    print(f"  SHA-256 collision costs:")
    print(f"  {'Method':>25} | {'Cost':>12} | {'Needs'}")
    print(f"  " + "-" * 60)
    print(f"  {'Classical birthday':>25} | {'2^128':>12} | {'computer'}")
    print(f"  {'Quantum BHT':>25} | {'2^85.3':>12} | {'12M qubits'}")
    print(f"  {'Multiverse (Deutsch)':>25} | {'2^85.3':>12} | {'= quantum'}")
    print(f"  {'Multiverse + comms':>25} | {'O(1)':>12} | {'violates QM'}")
    print(f"  {'Anthropic luck':>25} | {'2^121.5':>12} | {'2^128 branches'}")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 116: MULTIVERSE COLLISION")
    print("Parallel universes are real. Can they help?")
    print("=" * 60)

    model_A_quantum_parallelism(20)
    model_B_communication(20)
    model_C_anthropic_selection(5000)
    model_D_quantum_many_worlds()

    print(f"\n{'='*60}")
    print(f"FINAL VERDICT: MULTIVERSE")
    print(f"{'='*60}")
    print(f"  Parallel universes DO exist (per Deutsch/Everett)")
    print(f"  They DO compute in parallel (quantum computers prove this)")
    print(f"  But EXTRACTING the answer still costs 2^85.3 (Grover)")
    print(f"  Inter-branch communication would give O(1) but violates QM")
    print(f"  Anthropic selection: -6.5 bits (negligible)")
    print(f"  MULTIVERSE = QUANTUM = 2^85.3 for SHA-256 collision")

if __name__ == "__main__":
    main()
