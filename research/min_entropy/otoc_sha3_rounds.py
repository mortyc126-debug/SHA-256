"""OTOC round-by-round for SHA-3 (Keccak-f[1600]).

Direct comparison with SHA-256 OTOC scrambling rate.

For SHA-3-256:
- Absorb 64-byte input → state (5×5×64 = 1600 bits)
- Apply r Keccak rounds (max 24)
- Extract first 256 bits of state as "output"

Measure ||C(r)||_F² for r ∈ {1..24}.

Compare with SHA-256 result (Phase D OTOC):
- SHA-256: full scrambling at r ≈ 24 of 64 (~37% rounds)
- SHA-3:   full scrambling at r ≈ ? of 24 (?)

Theoretical: SHA-3 designed to scramble FAST (Keccak θ-step is global mixing).
Expected: full scrambling within ~5-10 Keccak rounds.
"""
import json, os, time
import numpy as np

from keccak_vec import keccak_f, absorb_sha3_256


OUT = '/home/user/SHA-256/research/min_entropy/otoc_sha3_rounds_results.json'


def state_bits_first256(state_arr):
    """Extract first 256 bits from Keccak state (N, 5, 5) uint64.

    SHA-3-256 output: first 4 lanes = (x=0,y=0), (x=1,y=0), (x=2,y=0), (x=3,y=0)
    Each lane is 64 bits, little-endian.
    """
    N = state_arr.shape[0]
    n_lanes = 4
    # Extract lanes
    lanes_out = np.zeros((N, n_lanes), dtype=np.uint64)
    for idx in range(n_lanes):
        x = idx % 5; y = idx // 5
        lanes_out[:, idx] = state_arr[:, y, x]
    # Convert to bytes (LE per lane) then bits
    out_bytes = lanes_out.view(dtype='<u1').reshape(N, n_lanes * 8)[:, :32]
    bits = np.unpackbits(out_bytes, axis=1, bitorder='big')[:, :256]
    return bits


def measure_sha3_otoc(r, N=200, seed=42):
    """Compute OTOC matrix for SHA-3 at r Keccak rounds."""
    rng = np.random.default_rng(seed)
    msg_bytes = 64

    # Generate N base messages
    base_msgs = rng.integers(0, 256, size=(N, msg_bytes), dtype=np.uint8)
    base_msgs_list = [bytes(base_msgs[i]) for i in range(N)]

    # Absorb base
    state_base = absorb_sha3_256(base_msgs_list)
    state_base_evolved = keccak_f(state_base, num_rounds=r)
    bits_base = state_bits_first256(state_base_evolved)

    msg_bits = msg_bytes * 8
    C = np.zeros((msg_bits, 256), dtype=np.float64)
    for i in range(msg_bits):
        byte = i // 8; bit = 7 - (i % 8)
        flip_msgs = base_msgs.copy()
        flip_msgs[:, byte] ^= np.uint8(1 << bit)
        flip_list = [bytes(flip_msgs[j]) for j in range(N)]
        state_flip = absorb_sha3_256(flip_list)
        state_flip_evolved = keccak_f(state_flip, num_rounds=r)
        bits_flip = state_bits_first256(state_flip_evolved)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# SHA-3 OTOC round-by-round (Keccak-f[1600])")

    rounds_to_test = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24]
    N = 200

    print(f"\n  N={N} messages, msg=512 bits, output=256 bits")
    print(f"\n{'r':>3}  {'||C||_F²':>10}  {'mean|C|':>10}  {'time':>6}")
    results = {}
    F_inf = 512 * 256 * 0.25 / N  # theoretical RO limit ~163.84
    for r in rounds_to_test:
        ts = time.time()
        C = measure_sha3_otoc(r, N=N)
        F_sq = float((C ** 2).sum())
        mean_abs = float(np.mean(np.abs(C)))
        elapsed = time.time() - ts
        results[r] = {'frobenius_sq': F_sq, 'mean_abs': mean_abs, 'time': elapsed}
        print(f"{r:>3}  {F_sq:>10.2f}  {mean_abs:>10.4f}  {elapsed:>5.1f}s")

    print(f"\n## Comparison with theoretical RO limit:")
    print(f"  Limit: {F_inf:.2f}")
    print(f"  At r=24 (full SHA-3-256): {results[24]['frobenius_sq']:.2f}")

    # Find round at which scrambled (within 5% of limit)
    scrambled_round = None
    for r in rounds_to_test:
        if abs(results[r]['frobenius_sq'] - F_inf) / F_inf < 0.05:
            scrambled_round = r; break
    if scrambled_round:
        print(f"  Reaches RO-like (within 5%) at r = {scrambled_round}")
    else:
        print(f"  Does not reach RO-like within tested range")

    # Compare with SHA-256 (loaded from previous results)
    print(f"\n## Comparison with SHA-256 (from otoc_sha256_results.json):")
    sha256_path = '/home/user/SHA-256/research/min_entropy/otoc_sha256_results.json'
    if os.path.exists(sha256_path):
        with open(sha256_path) as f: sha256 = json.load(f)
        print(f"{'r':>3}  {'SHA-256 F²':>10}  {'SHA-3 F²':>10}")
        for r in [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24]:
            sha_v = sha256['results'].get(str(r), {}).get('frobenius_sq', None)
            sha3_v = results.get(r, {}).get('frobenius_sq', None)
            if sha_v is not None and sha3_v is not None:
                print(f"{r:>3}  {sha_v:>10.2f}  {sha3_v:>10.2f}")
        # Compute scrambling speed ratio
        print(f"\n## Scrambling speed:")
        print(f"  SHA-256: full scramble at r ≈ 24 (of 64 total = 37% of rounds)")
        if scrambled_round:
            print(f"  SHA-3:   full scramble at r ≈ {scrambled_round} (of 24 total = {scrambled_round/24*100:.0f}% of rounds)")

    out = {
        'N': N,
        'rounds': rounds_to_test,
        'results': {str(r): v for r, v in results.items()},
        'theoretical_limit': F_inf,
        'scrambled_round': scrambled_round,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
