#!/usr/bin/env python3
"""
EXP 115: Quantum Collision — BHT Algorithm

Classical birthday: 2^128
Quantum (Brassard-Høyer-Tapp 1998): 2^(n/3) = 2^(256/3) ≈ 2^85.3

HOW BHT WORKS:
1. Classically compute 2^(n/3) hashes, store in table
2. Use Grover's quantum search over remaining space
3. Grover finds match in √(2^(2n/3)) = 2^(n/3) quantum queries
4. Total: 2^(n/3) classical + 2^(n/3) quantum = O(2^(n/3))

SIMULATE: We can't run quantum, but we can MODEL the cost structure
and compare with classical birthday at various scales.

Also: what quantum resources are needed?
- Qubits to represent SHA-256: ~216K (one per circuit gate)
- Circuit depth: ~100K quantum gates per SHA-256 evaluation
- Error correction overhead: ~1000x (current tech)
"""
import sys, os, random, math, time
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def simulate_bht_phase1(N_store):
    """Phase 1 of BHT: classically store N hashes."""
    t0 = time.time()
    table = {}
    for i in range(N_store):
        W16 = random_w16()
        H = sha256_compress(W16)
        h_key = tuple(H)
        if h_key in table:
            return i + 1, True, time.time() - t0  # Lucky collision in phase 1
        table[h_key] = W16
    return N_store, False, time.time() - t0

def simulate_bht_phase2(table, N_grover):
    """Phase 2: simulate Grover search (classically, measuring cost).
    Grover would check √N_remaining candidates.
    We simulate by checking N_grover random candidates against table."""
    t0 = time.time()
    for i in range(N_grover):
        W16 = random_w16()
        H = sha256_compress(W16)
        h_key = tuple(H)
        if h_key in table:
            return i + 1, True, time.time() - t0
    return N_grover, False, time.time() - t0

def test_bht_simulation(N=50000):
    """Simulate BHT at small scale to verify cost structure."""
    print(f"\n--- BHT SIMULATION (classical proxy, N={N}) ---")

    # At scale N, optimal BHT split:
    # Phase 1: N^(2/3) stored classically
    # Phase 2: N^(1/3) Grover iterations (≈ N^(2/3) classical equivalent)

    # For collision among N-bit hashes truncated to B bits:
    # Birthday: 2^(B/2)
    # BHT: 2^(B/3)

    for B in [16, 20, 24]:
        birthday_cost = 2 ** (B / 2)
        bht_cost = 2 ** (B / 3)
        phase1_size = int(2 ** (B / 3))
        grover_iters = int(2 ** (B / 3))  # Quantum, but simulated classically

        print(f"\n  B={B}-bit truncated hash:")
        print(f"    Birthday: 2^{B/2:.1f} = {int(birthday_cost)}")
        print(f"    BHT: 2^{B/3:.1f} = {int(bht_cost)}")

        # Simulate
        # Phase 1: store phase1_size hashes (of B-bit truncated hash)
        table = {}
        found_p1 = False
        for i in range(min(phase1_size, N)):
            W16 = random_w16()
            H = sha256_compress(W16)
            # Truncate to B bits
            h_trunc = 0
            for w in range(min(B // 32 + 1, 8)):
                h_trunc ^= H[w] & ((1 << min(B, 32)) - 1)
            h_key = h_trunc & ((1 << B) - 1)

            if h_key in table:
                found_p1 = True
                print(f"    Phase 1: collision at step {i+1}!")
                break
            table[h_key] = W16

        if not found_p1:
            # Phase 2: Grover search (simulated classically)
            found_p2 = False
            for i in range(min(grover_iters * 10, N)):  # Extra budget for classical sim
                W16 = random_w16()
                H = sha256_compress(W16)
                h_trunc = 0
                for w in range(min(B // 32 + 1, 8)):
                    h_trunc ^= H[w] & ((1 << min(B, 32)) - 1)
                h_key = h_trunc & ((1 << B) - 1)

                if h_key in table:
                    found_p2 = True
                    print(f"    Phase 2: collision at step {i+1} (Grover would: ~{grover_iters})")
                    break

            if not found_p2:
                print(f"    No collision found (budget exhausted)")

def quantum_resource_estimate():
    """Estimate quantum resources needed for SHA-256 collision."""
    print(f"\n--- QUANTUM RESOURCE ESTIMATE ---")

    # SHA-256 circuit: ~107,520 classical gates
    # Each classical gate → ~1-3 quantum gates (Toffoli decomposition)
    # Toffoli → 7 T-gates in standard decomposition
    sha256_gates = 107520
    quantum_gates = sha256_gates * 3  # Conservative
    t_gates = sha256_gates * 7

    # Qubits needed:
    # - Input: 512 (message)
    # - State: 256 (working state)
    # - Ancilla for carry: ~256
    # - Schedule workspace: ~2048
    # Total logical qubits ≈ 3000-5000
    logical_qubits = 4000

    # Error correction overhead (surface code):
    # Each logical qubit → ~1000-10000 physical qubits (depending on error rate)
    physical_per_logical = 3000  # Moderate estimate
    total_physical = logical_qubits * physical_per_logical

    # BHT iterations: 2^85.3
    grover_iterations = 2 ** 85.3

    # Total quantum gates: iterations × gates per SHA-256
    total_qgates = grover_iterations * quantum_gates

    # Time: at 1 MHz gate rate (optimistic for error-corrected)
    gate_rate = 1e6  # Hz
    total_seconds = total_qgates / gate_rate

    print(f"  SHA-256 circuit:")
    print(f"    Classical gates: {sha256_gates:,}")
    print(f"    Quantum gates (per evaluation): {quantum_gates:,}")
    print(f"    T-gates: {t_gates:,}")
    print(f"")
    print(f"  Qubit requirements:")
    print(f"    Logical qubits: ~{logical_qubits:,}")
    print(f"    Physical qubits (surface code): ~{total_physical:,}")
    print(f"    = {total_physical/1e6:.1f} million physical qubits")
    print(f"")
    print(f"  BHT algorithm:")
    print(f"    Phase 1 (classical): 2^85.3 hash computations")
    print(f"    Phase 1 memory: 2^85.3 × 32 bytes ≈ 2^90 bytes = 10^27 bytes")
    print(f"    Phase 2 (Grover): 2^85.3 quantum iterations")
    print(f"    Total quantum gates: 2^85.3 × {quantum_gates:,} ≈ 2^103.6")
    print(f"")
    print(f"  Time estimate (1 MHz logical gate rate):")
    print(f"    2^103.6 gates / 10^6 Hz = 2^103.6 / 2^20 = 2^83.6 seconds")
    print(f"    = 2^83.6 / (3.15×10^7) years = 2^83.6 / 2^24.9 = 2^58.7 years")
    print(f"    ≈ 10^17.7 years")
    print(f"    Universe age: 1.38 × 10^10 years ≈ 10^10.1 years")
    print(f"    Need: 10^7.6 ≈ 40 MILLION universe lifetimes")
    print(f"")
    print(f"  COMPARISON:")
    print(f"    Classical birthday: 2^128 SHA-256 ops")
    print(f"    Quantum BHT: 2^85.3 quantum SHA-256 ops")
    print(f"    Quantum speedup: 2^42.7 ≈ 7 trillion times faster")
    print(f"    But still: 40 million universe lifetimes")

def quantum_vs_classical_table():
    """Comparison table at various hash sizes."""
    print(f"\n--- QUANTUM vs CLASSICAL vs HASH SIZE ---")
    print(f"{'Hash bits':>10} | {'Classical':>12} | {'Quantum BHT':>12} | {'Speedup':>10}")
    print("-" * 55)

    for n in [32, 64, 128, 160, 192, 224, 256, 384, 512]:
        classical = n / 2
        quantum = n / 3
        speedup = classical - quantum
        print(f"{n:>10} | {'2^'+f'{classical:.0f}':>12} | {'2^'+f'{quantum:.1f}':>12} | {'2^'+f'{speedup:.1f}':>10}")

    print(f"""
  SHA-256: quantum gives 2^42.7 speedup (from 2^128 to 2^85.3)
  SHA-512: quantum gives 2^85.3 speedup (from 2^256 to 2^170.7)

  For SHA-256 to be quantum-safe at 128-bit security:
    Need n/3 ≥ 128 → n ≥ 384 bits
    SHA-384 or SHA-512 would be needed for post-quantum 128-bit security
""")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 115: QUANTUM BHT ALGORITHM")
    print("2^(n/3) instead of 2^(n/2)")
    print("=" * 60)

    test_bht_simulation(50000)
    quantum_resource_estimate()
    quantum_vs_classical_table()

    print(f"\n{'='*60}")
    print(f"VERDICT: Quantum BHT")
    print(f"  SHA-256 collision: 2^85.3 (vs classical 2^128)")
    print(f"  Speedup: 2^42.7 ≈ 7 trillion×")
    print(f"  Needs: 12M physical qubits, 10^17 years")
    print(f"  Status: THEORETICALLY optimal, PRACTICALLY impossible (2026)")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
