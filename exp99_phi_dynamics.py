#!/usr/bin/env python3
"""
EXP 99: Φ Dynamics — The Self-Referential Collision Map

Collision ⟺ Φ(δ★) = 0.
Φ(δ★) = δα(δ★) ⊕ δC(δ★)
      = (64-round state diff) ⊕ (feedforward carry diff)

Φ is NOT the round function. It's a DERIVED map combining
forward computation + backward carry reconstruction.

Properties of Φ that round function DOESN'T have:
- Self-referential (both sides from same δ★)
- Mixed dynamics (expanding × contracting)
- Carry chain = contracting part

Questions:
1. Is Φ contracting on some subspace? (→ fixed point exists)
2. Does Φ have LOWER D_KY than round function?
3. Does Φ have periodicity? (Φ^k = identity?)
4. Are there NATURAL zeros of Φ (structural fixed points)?
"""
import sys, os, random, math
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def compute_phi(W0, W1, DW0=1):
    """
    Compute Φ(δ★) for one Wang pair.
    Φ = δα ⊕ δC where:
      δα = state[64](M) ⊕ state[64](M') = state XOR difference
      δC = carry(IV,state(M)) ⊕ carry(IV,state(M')) = carry difference
    Returns: Φ as 256-bit vector (8 words × 32 bits)
    """
    Wn, Wf, DWs, sn, sf = wang_cascade(W0, W1, DW0)

    # δα: state XOR difference at round 64
    delta_alpha = [sn[64][w] ^ sf[64][w] for w in range(8)]

    # δC: carry difference of feedforward
    # carry(IV, state) = (IV + state) ^ (IV ^ state) for each word
    delta_C = []
    for w in range(8):
        carry_n = ((IV[w] + sn[64][w]) & MASK) ^ (IV[w] ^ sn[64][w])
        carry_f = ((IV[w] + sf[64][w]) & MASK) ^ (IV[w] ^ sf[64][w])
        delta_C.append(carry_n ^ carry_f)

    # Φ = δα ⊕ δC
    phi = [delta_alpha[w] ^ delta_C[w] for w in range(8)]

    # Also compute δH for reference
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    delta_H = [Hn[w] ^ Hf[w] for w in range(8)]

    return phi, delta_alpha, delta_C, delta_H

def test_phi_properties(N=3000):
    """Basic properties of Φ."""
    print("\n--- Φ PROPERTIES ---")

    phi_hws = []; da_hws = []; dc_hws = []; dh_hws = []

    for _ in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        phi, da, dc, dh = compute_phi(W0, W1)

        phi_hws.append(sum(hw(phi[w]) for w in range(8)))
        da_hws.append(sum(hw(da[w]) for w in range(8)))
        dc_hws.append(sum(hw(dc[w]) for w in range(8)))
        dh_hws.append(sum(hw(dh[w]) for w in range(8)))

    pa = np.array(phi_hws); daa = np.array(da_hws)
    dca = np.array(dc_hws); dha = np.array(dh_hws)

    print(f"E[HW(Φ)]:  {pa.mean():.2f} (collision = 0)")
    print(f"E[HW(δα)]: {daa.mean():.2f}")
    print(f"E[HW(δC)]: {dca.mean():.2f}")
    print(f"E[HW(δH)]: {dha.mean():.2f}")
    print(f"min(HW(Φ)): {pa.min()}")

    # Is Φ = δH? (Should be: hash = state_xor ⊕ carry, so δH = δα ⊕ δC = Φ)
    # Verify
    exact_match = 0
    for _ in range(500):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        phi, _, _, dh = compute_phi(W0, W1)
        if phi == dh:
            exact_match += 1
    print(f"\nΦ = δH exactly: {exact_match}/500")

    if exact_match == 500:
        print("*** Φ ≡ δH! Collision map = hash difference! ***")

    # Correlations
    c_phi_dh = np.corrcoef(pa, dha)[0, 1]
    c_da_dc = np.corrcoef(daa, dca)[0, 1]
    c_phi_da = np.corrcoef(pa, daa)[0, 1]

    print(f"\ncorr(HW(Φ), HW(δH)): {c_phi_dh:+.6f}")
    print(f"corr(HW(δα), HW(δC)): {c_da_dc:+.6f}")
    print(f"corr(HW(Φ), HW(δα)): {c_phi_da:+.6f}")

def test_phi_fixed_points(N=50000):
    """Search for near-zeros of Φ (near-fixed-points)."""
    print(f"\n--- Φ NEAR-ZEROS (N={N}) ---")

    best_phi_hw = 256
    best_pair = None

    phi_distribution = []

    for i in range(N):
        W0 = random.randint(0, MASK); W1 = random.randint(0, MASK)
        phi, _, _, _ = compute_phi(W0, W1)
        phi_hw = sum(hw(phi[w]) for w in range(8))
        phi_distribution.append(phi_hw)

        if phi_hw < best_phi_hw:
            best_phi_hw = phi_hw
            best_pair = (W0, W1)

        if phi_hw == 0:
            print(f"*** Φ = 0 FOUND at i={i}! W0=0x{W0:08x}, W1=0x{W1:08x} ***")
            break

    pd = np.array(phi_distribution)
    birthday = 128 - 8 * math.sqrt(2 * math.log(N))

    print(f"Best HW(Φ): {best_phi_hw}")
    print(f"Birthday expected min HW: ~{birthday:.0f}")
    print(f"E[HW(Φ)]: {pd.mean():.2f}")

def test_phi_iterative(N=100):
    """Can Φ be iterated? Φ(Φ(δ★)) = ?"""
    print(f"\n--- Φ ITERATION ---")

    # Φ maps 256-bit → 256-bit. Can iterate.
    # If Φ^k converges → fixed point exists.

    # Problem: Φ is defined for Wang pairs (M, M').
    # We can't iterate Φ directly on its output.
    # But: Φ = δH. So iterating Φ = finding sequence of pairs
    # where each pair's δH feeds into the next as... what?

    # Actually: Φ(δ★) = δH = hash difference.
    # Φ is NOT a map we can iterate (it's a functional of messages, not of δ★).

    print(f"Φ = δH (collision map = hash difference)")
    print(f"Φ is a FUNCTIONAL of (M, M'), not an iterable map.")
    print(f"Cannot iterate Φ in standard sense.")
    print(f"")
    print(f"BUT: can we define Φ̃: δ★ → δ★ where")
    print(f"  Φ̃(δ) = 'find M,M' with state diff = δ, return hash diff'")
    print(f"  This requires INVERTING 64 rounds → cost 2^128")
    print(f"")
    print(f"Iteration of Φ = iterative collision search = birthday.")

def main():
    random.seed(42)
    print("=" * 60)
    print("EXP 99: Φ DYNAMICS")
    print("The self-referential collision map")
    print("=" * 60)

    test_phi_properties(2000)
    test_phi_fixed_points(30000)
    test_phi_iterative()

    print("\n" + "=" * 60)
    print("RESULT: Φ ≡ δH (collision map = hash difference)")
    print("Collision = δH = 0 = standard problem in ★-language")
    print("=" * 60)

if __name__ == "__main__":
    main()
