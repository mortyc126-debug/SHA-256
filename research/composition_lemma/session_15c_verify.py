"""
Session 15c: Extract+verify b-chain k=14, 16, 18, 20 on real single_round.

Test: z3 model claims SAT for these k values. Run on actual mini-SHA round
function to confirm chain holds.
"""
import sys
sys.path.insert(0, '/home/user/SHA-256/research/qt_minimal')
from session_15b_extended_search import search_chain_with_model, verify_chain
import z3


def main():
    print("=== Session 15c: Verification of b-chain z3 SAT solutions ===\n")
    for k in [14, 16, 18, 20]:
        print(f"k = {k}: searching SAT, then verifying on real round function...")
        result, elapsed, W = search_chain_with_model(k, timeout_s=600)
        if result == z3.sat:
            print(f"  z3: SAT in {elapsed:.1f}s")
            ok, actual = verify_chain(W, k)
            if ok:
                print(f"  ✓ VERIFIED: chain holds {actual} rounds on real SHA-256 round function")
                print(f"    W[0]={hex(W[0])}, W[1]={hex(W[1])}, ..., W[{min(k,16)-1}]={hex(W[min(k,16)-1])}")
            else:
                print(f"  ✗ DISCREPANCY: z3 says SAT but real run breaks at round {actual}")
                print(f"    W from z3: {[hex(w) for w in W[:min(k,16)]]}")
        else:
            print(f"  TIMEOUT/UNSAT after {elapsed:.1f}s")
        print()


if __name__ == "__main__":
    main()
