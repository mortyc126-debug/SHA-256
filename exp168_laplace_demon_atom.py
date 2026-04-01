#!/usr/bin/env python3
"""
EXP 168: LAPLACE'S DEMON — Disassemble ONE BIT completely

Not attacking. UNDERSTANDING. Every sub-bit dimension of
one specific bit position through one round of SHA-256.

TARGET: Bit 0, Word 0 (register a), Round 0.
IV[0] = 0x6a09e667. Bit 0 = 1.

Map EVERY interaction this bit has in round 0:
- Where it goes through Σ₀
- How it combines in Maj
- How it enters T2 addition (carry chain)
- Where it ends up in a_new
- Its complete 7-dimensional state
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def bit(val, pos):
    """Extract bit at position pos."""
    return (val >> pos) & 1

def bits_str(val, n=32):
    """Binary string, LSB first."""
    return ''.join(str(bit(val, i)) for i in range(n))

def trace_single_bit():
    """Trace bit 0 of word a through round 0 completely."""
    print(f"{'='*70}")
    print(f"LAPLACE'S DEMON: Anatomy of Bit 0, Word a, Round 0")
    print(f"{'='*70}")

    # Initial state = IV
    a = IV[0]  # 0x6a09e667
    b = IV[1]  # 0xbb67ae85
    c = IV[2]  # 0x3c6ef372
    d = IV[3]  # 0xa54ff53a
    e = IV[4]  # 0x510e527f
    f = IV[5]  # 0x9b05688c
    g = IV[6]  # 0x1f83d9ab
    h = IV[7]  # 0x5be0cd19

    W0 = 0  # Assume zero message for clarity
    K0 = K[0]  # 0x428a2f98

    print(f"\n--- INITIAL STATE ---")
    print(f"  a = IV[0] = 0x{a:08x} = ...{bits_str(a, 8)} (LSB first)")
    print(f"  Bit 0 of a = {bit(a, 0)}")

    # ============================
    # Σ₀(a) decomposition
    # ============================
    print(f"\n--- Σ₀(a) = ROTR₂(a) ⊕ ROTR₁₃(a) ⊕ ROTR₂₂(a) ---")

    rotr2_a = rotr(a, 2)
    rotr13_a = rotr(a, 13)
    rotr22_a = rotr(a, 22)
    sigma0_a = sigma0(a)

    print(f"\n  ROTR₂(a):  bit 0 comes from a[2]  = {bit(a, 2)}")
    print(f"  ROTR₁₃(a): bit 0 comes from a[13] = {bit(a, 13)}")
    print(f"  ROTR₂₂(a): bit 0 comes from a[22] = {bit(a, 22)}")
    print(f"  Σ₀(a) bit 0 = {bit(a,2)} ⊕ {bit(a,13)} ⊕ {bit(a,22)} = {bit(a,2) ^ bit(a,13) ^ bit(a,22)}")
    print(f"  Verified: Σ₀(a) bit 0 = {bit(sigma0_a, 0)}")

    # Where does bit 0 of a GO in Σ₀?
    print(f"\n  Where does a[0]={bit(a,0)} appear in Σ₀(a)?")
    print(f"    a[0] → ROTR₂:  appears at Σ₀ position (32-2)=30")
    print(f"    a[0] → ROTR₁₃: appears at Σ₀ position (32-13)=19")
    print(f"    a[0] → ROTR₂₂: appears at Σ₀ position (32-22)=10")
    print(f"    Σ₀(a)[30] = a[0] ⊕ a[{(30+13)%32}] ⊕ a[{(30+22)%32}] = {bit(a,0)} ⊕ {bit(a,11)} ⊕ {bit(a,20)} = {bit(sigma0_a, 30)}")
    print(f"    Σ₀(a)[19] = a[{(19+2)%32}] ⊕ a[0] ⊕ a[{(19+22)%32}] = {bit(a,21)} ⊕ {bit(a,0)} ⊕ {bit(a,9)} = {bit(sigma0_a, 19)}")
    print(f"    Σ₀(a)[10] = a[{(10+2)%32}] ⊕ a[{(10+13)%32}] ⊕ a[0] = {bit(a,12)} ⊕ {bit(a,23)} ⊕ {bit(a,0)} = {bit(sigma0_a, 10)}")
    print(f"\n    Bit a[0] creates 3 copies in Σ₀: positions 10, 19, 30")

    # ============================
    # Maj(a,b,c) decomposition
    # ============================
    print(f"\n--- Maj(a,b,c) ---")
    maj_abc = maj(a, b, c)

    print(f"  Bit 0: a[0]={bit(a,0)}, b[0]={bit(b,0)}, c[0]={bit(c,0)}")
    print(f"  Maj(1,1,0) = (1&1)⊕(1&0)⊕(1&0) = 1⊕0⊕0 = {bit(maj_abc, 0)}")
    print(f"  (= majority vote = 1)")

    # How sensitive is Maj to a[0]?
    # If a[0] flips: Maj(0,1,0) = (0&1)⊕(0&0)⊕(1&0) = 0
    # Maj CHANGES when a[0] flips (from 1 to 0)
    print(f"\n  Sensitivity of Maj to a[0]:")
    print(f"    a[0]=1: Maj = 1")
    print(f"    a[0]=0: Maj = (0&{bit(b,0)})⊕(0&{bit(c,0)})⊕({bit(b,0)}&{bit(c,0)}) = {(0&bit(b,0))^(0&bit(c,0))^(bit(b,0)&bit(c,0))}")
    print(f"    Δ = {bit(maj_abc,0) ^ ((0&bit(b,0))^(0&bit(c,0))^(bit(b,0)&bit(c,0)))}")
    print(f"    Sensitivity formula: δMaj = δa & (b⊕c) = 1 & ({bit(b,0)}⊕{bit(c,0)}) = {1 & (bit(b,0)^bit(c,0))}")

    # ============================
    # T2 = Σ₀(a) + Maj(a,b,c)
    # ============================
    print(f"\n--- T2 = Σ₀(a) + Maj(a,b,c) ---")
    T2 = (sigma0_a + maj_abc) & MASK

    # At bit 0: T2[0] = Σ₀[0] ⊕ Maj[0] ⊕ carry_in
    # carry_in at bit 0 = 0 (always!)
    print(f"  Σ₀(a)[0] = {bit(sigma0_a, 0)}")
    print(f"  Maj[0] = {bit(maj_abc, 0)}")
    print(f"  carry_in[0] = 0 (always, for bit 0)")
    print(f"  T2[0] = {bit(sigma0_a,0)} ⊕ {bit(maj_abc,0)} ⊕ 0 = {bit(sigma0_a,0) ^ bit(maj_abc,0)}")
    print(f"  Verified: T2[0] = {bit(T2, 0)}")

    # GKP at bit 0 of T2 addition
    gkp0 = 'G' if (bit(sigma0_a,0)==1 and bit(maj_abc,0)==1) else ('K' if (bit(sigma0_a,0)==0 and bit(maj_abc,0)==0) else 'P')
    carry_out_0 = bit(sigma0_a,0) & bit(maj_abc,0)
    print(f"\n  GKP at bit 0: {gkp0}")
    print(f"  carry_out[0] = {bit(sigma0_a,0)} & {bit(maj_abc,0)} = {carry_out_0}")

    # ============================
    # T1 and a_new
    # ============================
    print(f"\n--- T1 = h + Σ₁(e) + Ch(e,f,g) + K[0] + W[0] ---")
    sigma1_e = sigma1(e)
    ch_efg = ch(e, f, g)
    T1 = (h + sigma1_e + ch_efg + K0 + W0) & MASK

    print(f"  h[0] = {bit(h, 0)}")
    print(f"  Σ₁(e)[0] = {bit(sigma1_e, 0)}")
    print(f"  Ch(e,f,g)[0] = {bit(ch_efg, 0)}")
    print(f"  K[0][0] = {bit(K0, 0)}")
    print(f"  W[0][0] = {bit(W0, 0)}")
    print(f"  T1 = 0x{T1:08x}, T1[0] = {bit(T1, 0)}")

    print(f"\n--- a_new = T1 + T2 ---")
    a_new = (T1 + T2) & MASK
    print(f"  T1[0] = {bit(T1, 0)}")
    print(f"  T2[0] = {bit(T2, 0)}")
    print(f"  carry_in[0] = 0")
    print(f"  a_new[0] = {bit(T1,0)} ⊕ {bit(T2,0)} ⊕ 0 = {bit(T1,0) ^ bit(T2,0)}")
    print(f"  Verified: a_new[0] = {bit(a_new, 0)}")

    # ============================
    # COMPLETE 7-DIMENSIONAL STATE
    # ============================
    print(f"\n{'='*70}")
    print(f"COMPLETE 7-DIMENSIONAL STATE OF BIT 0, WORD a, ROUND 0")
    print(f"{'='*70}")
    print(f"""
  1. VALUE:      a[0] = {bit(a, 0)}
  2. GKP:        In T2 addition: {gkp0}
                 (Σ₀[0]={bit(sigma0_a,0)}, Maj[0]={bit(maj_abc,0)})
  3. CARRY_IN:   0 (always zero for bit 0)
  4. CARRY_OUT:  {carry_out_0} (feeds into bit 1 of T2)
  5. Σ-ROUTES:   a[0] → Σ₀ positions {{10, 19, 30}}
                 3 copies created (expansion 1→3, Theorem exp150)
  6. Ch/Maj ROLE: Maj(a[0]=1, b[0]=1, c[0]=0) = 1
                 Sensitivity: δMaj = δa[0] & (b[0]⊕c[0]) = 1&1 = 1
                 → Bit 0 is FULLY SENSITIVE in Maj
  7. RESULT:     T2[0] = Σ₀[0] ⊕ Maj[0] = {bit(sigma0_a,0)} ⊕ {bit(maj_abc,0)} = {bit(T2, 0)}
                 a_new[0] = T1[0] ⊕ T2[0] = {bit(T1,0)} ⊕ {bit(T2,0)} = {bit(a_new, 0)}
    """)

    # ============================
    # LIFE HISTORY: Where does a[0] END UP after round 0?
    # ============================
    print(f"--- LIFE HISTORY OF BIT a[0] THROUGH ROUND 0 ---")
    print(f"""
  a[0] = 1 (input, IV[0] bit 0)
    │
    ├─→ Σ₀: creates 3 XOR-copies at positions 10, 19, 30 of Σ₀(a)
    │   Each copy XOR'd with 2 other a-bits at that position
    │   Σ₀[10] = a[12]⊕a[23]⊕a[0] = {bit(a,12)}⊕{bit(a,23)}⊕{bit(a,0)} = {bit(sigma0_a,10)}
    │   Σ₀[19] = a[21]⊕a[0]⊕a[9]  = {bit(a,21)}⊕{bit(a,0)}⊕{bit(a,9)} = {bit(sigma0_a,19)}
    │   Σ₀[30] = a[0]⊕a[11]⊕a[20] = {bit(a,0)}⊕{bit(a,11)}⊕{bit(a,20)} = {bit(sigma0_a,30)}
    │
    ├─→ Maj: AND with b[0] and c[0]
    │   Maj[0] = (1&1)⊕(1&0)⊕(1&0) = 1
    │   Sensitivity = 1 (fully controls Maj output at bit 0)
    │
    ├─→ T2 = Σ₀ + Maj: enters addition at 4 positions
    │   Direct (bit 0): Σ₀[0]={bit(sigma0_a,0)} + Maj[0]={bit(maj_abc,0)} → T2[0]={bit(T2,0)}
    │   Via Σ₀[10]: contributes to T2 bit 10 (through carry chain)
    │   Via Σ₀[19]: contributes to T2 bit 19 (through carry chain)
    │   Via Σ₀[30]: contributes to T2 bit 30 (through carry chain)
    │
    ├─→ a_new = T1 + T2: enters SECOND addition
    │   a_new[0] = T1[0]⊕T2[0] = {bit(T1,0)}⊕{bit(T2,0)} = {bit(a_new,0)}
    │
    └─→ ALSO: a becomes b in next round (shift register)
        So a[0] = b[0] in round 1, c[0] in round 2, d[0] in round 3.
        It "echoes" for 3 more rounds without any change!
    """)

    # Verify with actual round function
    state_after = sha256_round(list(IV), W0, K0)
    assert state_after[0] == a_new, f"Mismatch: {state_after[0]:08x} != {a_new:08x}"
    assert state_after[1] == a, "b_new should be a"
    print(f"  ✓ Verified: a_new = 0x{a_new:08x}, b_new = a = 0x{a:08x}")

    # ============================
    # WHAT'S SMALLER THAN A BIT?
    # ============================
    print(f"\n{'='*70}")
    print(f"WHAT'S SMALLER THAN A BIT?")
    print(f"{'='*70}")
    print(f"""
  A bit is 0 or 1. But its INFLUENCE has STRUCTURE:

  Bit a[0] at round 0 has:
    - 1 direct contribution (to T2[0] and a_new[0])
    - 3 Σ-copies (positions 10, 19, 30)
    - 1 Maj output (AND with neighbors)
    - 4 positions in T2 addition (direct + 3 via Σ)
    - 4 carry chains potentially affected
    - 3 echo rounds (a→b→c→d via shift register)

  TOTAL INFLUENCE FOOTPRINT of ONE bit in ONE round:
    Direct: 1 position
    Via Σ: 3 positions
    Via carry: up to 4 chains × avg 4.3 depth = ~17 carry bits
    Via echo: 3 rounds × same position

  TOTAL: ~24 bit-positions affected by ONE input bit in ONE round.

  After 64 rounds: tree branches ~24^(depth) until saturation.
  Saturation at round τ_★ = 4: ~24^4 ≈ 330,000 paths.
  But state has only 256 bits → massive overlap after 4 rounds.
    """)

def main():
    trace_single_bit()

if __name__ == "__main__":
    main()
