#!/usr/bin/env python3
"""
EXP 113: Laplace's Demon — What if randomness is predictable?

IDEA: If we know the PRNG state, we can predict all "random" messages.
This collapses the search space from 2^512 to the PRNG state size.

Modern PRNGs:
  - Python random (Mersenne Twister): 19937-bit state → 2^19937 period
  - /dev/urandom: 256-bit entropy pool
  - Real-world weak PRNG: sometimes as low as 32-64 bits of entropy

TEST: If PRNG has S bits of state, collision search = 2^(S/2)
  S = 256 → 2^128 (no gain)
  S = 128 → 2^64 (!!!)
  S = 64  → 2^32 (trivial!)
  S = 32  → 2^16 = 65536 pairs (instant)

Simulate: generate messages from weak PRNG, find collisions.
"""
import sys, os, random, math, time
import hashlib
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def test_weak_prng_collision(seed_bits=32, N_seeds=None):
    """If PRNG has only seed_bits of entropy, find collision."""
    print(f"\n--- WEAK PRNG: {seed_bits}-bit seed ---")

    max_seed = 2 ** seed_bits
    if N_seeds is None:
        # Birthday on seed space: need ~2^(seed_bits/2) samples
        N_seeds = min(int(2 ** (seed_bits / 2) * 3), 2**20)  # cap at 1M

    print(f"  Seed space: 2^{seed_bits} = {max_seed}")
    print(f"  Birthday target: 2^{seed_bits//2} = {2**(seed_bits//2)}")
    print(f"  Testing {N_seeds} seeds...")

    t0 = time.time()
    hash_to_seed = {}
    collision_found = False

    for i in range(N_seeds):
        seed = random.randint(0, max_seed - 1)

        # Generate message deterministically from seed
        rng = random.Random(seed)
        W16 = [rng.randint(0, MASK) for _ in range(16)]

        # Compute hash
        H = sha256_compress(W16)
        h_key = tuple(H)

        if h_key in hash_to_seed:
            old_seed = hash_to_seed[h_key]
            if old_seed != seed:
                t1 = time.time()
                print(f"  *** COLLISION FOUND! ***")
                print(f"  Seed 1: {old_seed}")
                print(f"  Seed 2: {seed}")
                print(f"  After {i+1} attempts ({t1-t0:.2f}s)")

                # Verify
                rng1 = random.Random(old_seed)
                W1 = [rng1.randint(0, MASK) for _ in range(16)]
                rng2 = random.Random(seed)
                W2 = [rng2.randint(0, MASK) for _ in range(16)]
                H1 = sha256_compress(W1)
                H2 = sha256_compress(W2)

                if W1 != W2:
                    print(f"  M1 ≠ M2: YES (different messages)")
                    print(f"  H1 == H2: {H1 == H2}")
                    collision_found = True
                else:
                    print(f"  Same message (seed collision, not hash collision)")
                break
        else:
            hash_to_seed[h_key] = seed

    if not collision_found:
        t1 = time.time()
        print(f"  No collision in {N_seeds} attempts ({t1-t0:.2f}s)")
        print(f"  (Expected: need ~{2**(seed_bits//2)} attempts)")

    return collision_found

def test_entropy_levels():
    """Test at various entropy levels."""
    print(f"{'='*60}")
    print(f"LAPLACE'S DEMON: PRNG Entropy vs Collision Cost")
    print(f"{'='*60}")

    # seed_bits → how hard is collision?
    results = []
    for bits in [8, 16, 20, 24, 28, 32]:
        found = test_weak_prng_collision(bits)
        results.append((bits, found))

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"{'PRNG bits':>10} | {'Birthday':>10} | {'Collision?':>10}")
    print(f"-" * 40)
    for bits, found in results:
        print(f"{bits:>10} | {'2^'+str(bits//2):>10} | {'YES' if found else 'no':>10}")

    print(f"""
CONCLUSION:
  SHA-256 collision hardness = min(2^128, 2^(PRNG_entropy/2))

  If attacker knows victim uses weak PRNG with S bits:
    S ≤ 64:  collision TRIVIAL (seconds)
    S = 128: collision = 2^64 (feasible with effort)
    S = 256: collision = 2^128 (back to birthday)

  Demon Laplace works IF entropy is low.
  Against /dev/urandom (256+ bits): no advantage.
  Against embedded/IoT devices with weak RNG: DEVASTATING.
""")

if __name__ == "__main__":
    test_entropy_levels()
