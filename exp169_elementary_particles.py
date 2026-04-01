#!/usr/bin/env python3
"""
EXP 169: ELEMENTARY PARTICLES OF SHA-256

Below the bit: K, P, G particles and their 9 interactions.
Decompose one SPECIFIC carry chain into particle physics.

K = absorber (both bits 0, kills carry)
P = wire (bits differ, propagates carry)
G = source (both bits 1, generates carry)

The 9 interactions form the M₃ monoid.
Map the EXACT particle sequence for T2 = Σ₀(a) + Maj(a,b,c) at round 0.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def bit(val, pos):
    return (val >> pos) & 1

def particle_sequence(a, b):
    """Convert addition a+b to particle sequence."""
    particles = []
    for i in range(32):
        ai = bit(a, i); bi = bit(b, i)
        if ai == 1 and bi == 1:
            particles.append('G')
        elif ai == 0 and bi == 0:
            particles.append('K')
        else:
            particles.append('P')
    return particles

def carry_chain_physics(a, b):
    """Full particle physics of one carry chain."""
    particles = particle_sequence(a, b)
    carries = []
    c = 0  # carry_in = 0
    events = []

    for i in range(32):
        p = particles[i]
        c_in = c

        if p == 'G':
            c_out = 1
            if c_in == 0:
                event = "BIRTH"      # G creates carry from nothing
            else:
                event = "SUSTAIN"    # G continues existing carry
        elif p == 'K':
            c_out = 0
            if c_in == 1:
                event = "KILL"       # K kills incoming carry
            else:
                event = "VOID"       # K in dead zone, nothing happens
        else:  # P
            c_out = c_in
            if c_in == 1:
                event = "FLOW"       # P transmits carry (LIFE!)
            else:
                event = "IDLE"       # P has nothing to transmit

        carries.append(c_out)
        events.append(event)
        c = c_out

    return particles, carries, events

def analyze_round0_T2():
    """Complete particle physics of T2 = Σ₀(a) + Maj(a,b,c) at round 0."""
    print(f"{'='*70}")
    print(f"PARTICLE PHYSICS: T2 = Σ₀(IV[0]) + Maj(IV[0], IV[1], IV[2])")
    print(f"{'='*70}")

    a = IV[0]; b = IV[1]; c = IV[2]
    sigma0_a = sigma0(a)
    maj_abc = maj(a, b, c)

    print(f"\n  Σ₀(a) = 0x{sigma0_a:08x}")
    print(f"  Maj    = 0x{maj_abc:08x}")
    print(f"  T2     = 0x{(sigma0_a + maj_abc) & MASK:08x}")

    particles, carries, events = carry_chain_physics(sigma0_a, maj_abc)

    # Count particle types
    nG = particles.count('G')
    nK = particles.count('K')
    nP = particles.count('P')

    print(f"\n  PARTICLE CENSUS: G={nG}, K={nK}, P={nP}")

    # Count event types
    from collections import Counter
    event_counts = Counter(events)
    print(f"  EVENT CENSUS: {dict(event_counts)}")

    # Display particle chain
    print(f"\n  PARTICLE CHAIN (bit 0 → bit 31):")
    print(f"  {'Bit':>4} | {'Σ₀':>2} {'Maj':>3} | {'Particle':>8} | {'c_in':>4} {'c_out':>5} | {'Event':>8} | Visual")
    print(f"  " + "-" * 65)

    # Identify carry CHAINS (consecutive flow/sustain events)
    chain_lengths = []
    current_chain = 0

    for i in range(32):
        s0_bit = bit(sigma0_a, i)
        maj_bit = bit(maj_abc, i)
        c_in = carries[i-1] if i > 0 else 0
        c_out = carries[i]

        # Visual representation
        if events[i] == "BIRTH":
            visual = "★→"       # Carry born
        elif events[i] == "FLOW":
            visual = "──→"      # Carry flowing
        elif events[i] == "KILL":
            visual = "──✕"      # Carry killed
        elif events[i] == "SUSTAIN":
            visual = "══→"      # Carry sustained by G
        elif events[i] == "VOID":
            visual = "   "      # Dead zone
        elif events[i] == "IDLE":
            visual = "···"      # P waiting, nothing to carry

        print(f"  {i:>4} |  {s0_bit} {maj_bit:>3} | {particles[i]:>8} | {c_in:>4} {c_out:>5} | {events[i]:>8} | {visual}")

        # Track chain lengths
        if events[i] in ("BIRTH", "FLOW", "SUSTAIN"):
            current_chain += 1
        else:
            if current_chain > 0:
                chain_lengths.append(current_chain)
            current_chain = 0

    if current_chain > 0:
        chain_lengths.append(current_chain)

    print(f"\n  CARRY CHAINS (living segments):")
    print(f"    Chains: {chain_lengths}")
    print(f"    Longest: {max(chain_lengths) if chain_lengths else 0}")
    print(f"    Total carry-alive bits: {sum(chain_lengths)}")
    print(f"    Total carry-dead bits: {32 - sum(chain_lengths)}")

    return particles, carries, events

def analyze_interaction_matrix():
    """The 9 fundamental interactions at round 0."""
    print(f"\n{'='*70}")
    print(f"9 FUNDAMENTAL INTERACTIONS")
    print(f"{'='*70}")

    # For T2 addition: count how many times each pair (prev, current) occurs
    a = IV[0]; b = IV[1]; c = IV[2]
    sigma0_a = sigma0(a)
    maj_abc = maj(a, b, c)

    particles, carries, events = carry_chain_physics(sigma0_a, maj_abc)

    # Count transitions
    transitions = {}
    for i in range(1, 32):
        pair = (particles[i-1], particles[i])
        transitions[pair] = transitions.get(pair, 0) + 1

    print(f"\n  Transition matrix (T2 at round 0):")
    print(f"        → K    P    G")
    for p1 in ['K', 'P', 'G']:
        print(f"    {p1} |", end="")
        for p2 in ['K', 'P', 'G']:
            count = transitions.get((p1, p2), 0)
            print(f"  {count:>3}", end="")
        print()

    # What does the transition matrix MEAN for carry?
    print(f"\n  INTERPRETATION:")
    print(f"    P→P = carry wire (LIFE extends)")
    print(f"    G→P = carry birth then flow (LIFE begins)")
    print(f"    P→K = carry killed (DEATH)")
    print(f"    G→K = carry born and immediately killed (STILLBORN)")

    # Life expectancy of carry in this specific chain
    life_events = []
    alive = False
    life = 0
    for i in range(32):
        if events[i] in ("BIRTH", "FLOW", "SUSTAIN"):
            alive = True
            life += 1
        else:
            if alive:
                life_events.append(life)
                life = 0
                alive = False
    if alive:
        life_events.append(life)

    if life_events:
        print(f"\n  Carry life events: {life_events}")
        print(f"  Average carry lifetime: {sum(life_events)/len(life_events):.1f} positions")
        print(f"  This specific chain has {len(life_events)} carry 'organisms'")

def sub_particle_analysis():
    """What's BELOW the particle? The TRANSITION itself."""
    print(f"\n{'='*70}")
    print(f"SUB-PARTICLE: THE TRANSITION OPERATOR")
    print(f"{'='*70}")

    print(f"""
  A particle (K, P, G) has a value. A transition has a DIRECTION.

  The transition K→G means: dead zone ends, carry is born.
  This transition has properties:
    - Position: bit i where it occurs
    - Carry state change: 0 → 1
    - Information content: 1 bit created

  The transition G→K means: carry dies.
    - Carry state change: 1 → 0
    - Information content: 1 bit destroyed

  The transition P→P means: carry flows unchanged.
    - Carry state change: c → c (identity)
    - Information content: 0 bits created/destroyed
    - BUT: 1 bit of POSITION information encoded
      (the carry "remembers" it was born k positions ago)

  SUB-PARTICLES = TRANSITIONS:
    Birth:   K→G or K→P→...→P→G (carry appears)
    Death:   G→K or P→K (carry disappears)
    Flow:    P→P (carry transmits)
    Wall:    K→K (dead zone continues)
    Restart: G→G (carry refreshed)

  SHA-256 = a sequence of births, flows, and deaths of carry organisms.
  Each organism lives for some number of positions (P-chain length).

  The ECOLOGY of these organisms = the chain spectrum (exp156)!
  Low entropy = few species = regular ecology = near-collision.
  High entropy = diverse species = chaotic ecology = random hash.

  We have arrived at the BOTTOM:
    SHA-256 = ecology of carry organisms
    Each organism: born at G, lives through P, dies at K
    The ecosystem's entropy = the chain spectrum entropy
    Collision = two ecosystems producing the same hash
    """)

def main():
    print("=" * 70)
    print("EXP 169: ELEMENTARY PARTICLES — K, P, G")
    print("=" * 70)

    analyze_round0_T2()
    analyze_interaction_matrix()
    sub_particle_analysis()

if __name__ == "__main__":
    main()
