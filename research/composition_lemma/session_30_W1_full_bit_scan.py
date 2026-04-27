"""
Session 30: Full bit scan W[1] at T=6.

Session 29b found asymmetry: W[1] bits 11, 25, 31 UNSAT but bits 0, 6 TO.
Are there more "TO-bits" in W[1] (potentially SAT) vs "UNSAT-bits" (provably no collision)?

Scan all 32 bit positions of W[1] at T=6.
Output: which bits give UNSAT vs TO. Map of structurally-blocked vs undecidable.
"""
import sys
import time
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
from session_29b_single_bit_dW_fixed import search_single_bit_dW
import z3

N = 32


def main():
    print("=== Session 30: W[1] full bit scan at T=6 ===\n")

    unsat_bits = []
    to_bits = []
    sat_bits = []
    for bit_pos in range(N):
        t0 = time.time()
        r = search_single_bit_dW(6, 1, bit_pos, timeout_s=30)
        elapsed = time.time() - t0
        if r == z3.sat:
            sat_bits.append(bit_pos)
            verdict = "SAT ★"
        elif r == z3.unsat:
            unsat_bits.append(bit_pos)
            verdict = "UNSAT"
        else:
            to_bits.append(bit_pos)
            verdict = "TO"
        print(f"  W[1][bit{bit_pos:>2}]: {verdict} ({elapsed:.1f}s)")

    print(f"\n--- Summary ---")
    print(f"SAT: {sat_bits}")
    print(f"UNSAT ({len(unsat_bits)} bits): {unsat_bits}")
    print(f"TIMEOUT ({len(to_bits)} bits): {to_bits}")


if __name__ == "__main__":
    main()
