"""
IT-7: Does state1 XOR-difference have chain-detectable structure
that the thermostаt hides from marginal metrics?

Setup:
  - N random 64-byte message pairs (M_i, M'_i)
  - state1_i = SHA-256-block1(M_i), state1'_i = SHA-256-block1(M'_i)
  - D_i = state1_i XOR state1'_i    (256-bit XOR difference)
  - h_i = SHA-256(M_i), h'_i = SHA-256(M'_i)
  - delta_h_i = h_i XOR h'_i         (256-bit output difference)

Feature (collision-relevant):
  f_in(i) = whether HW(delta_h_i) < 128   (near-collision indicator)

Target:
  t(i) = specific bit of D_i   (state1-difference bit)

Question: is there chain-k coherence between "how close pair is to
collision" and "specific structure of state1 difference"?

If YES → the collision landscape has exploitable Walsh structure in
state1 space, invisible to marginal metrics but visible to chain-test.

This is the bridge between IT-1..IT-6 methodology and the v20 collision
search problem.
"""

import hashlib, json, math, os, time
import numpy as np

LENGTH_BITS = 512
N_PAIRS = 200000       # number of random message pairs
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it7_collision_probe.json')


def gen_random_pairs(n, seed=0xC011DE):
    """Generate n random 64-byte message pairs."""
    rng = np.random.default_rng(seed)
    M1 = [rng.bytes(64) for _ in range(n)]
    M2 = [rng.bytes(64) for _ in range(n)]
    return M1, M2


def sha256_full(messages):
    """Full SHA-256 digest as 32-byte arrays."""
    return [hashlib.sha256(m).digest() for m in messages]


def sha256_block1_state(messages):
    """State after block 1 only (using our chimera). Returns (N, 8) uint32."""
    import sha256_chimera as ch
    N = len(messages)
    U32 = ch.U32
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
    return ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)


def state_to_bits(state):
    N = state.shape[0]
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w * 32 + b] = ((state[:, w] >> np.uint32(31 - b)) & 1).astype(np.uint8)
    return bits


def digest_to_bits(digests):
    N = len(digests)
    bits = np.zeros((N, 256), dtype=np.uint8)
    for i, d in enumerate(digests):
        for byte_idx in range(32):
            for bit_in_byte in range(8):
                bits[i, byte_idx * 8 + bit_in_byte] = (d[byte_idx] >> (7 - bit_in_byte)) & 1
    return bits


def compute_omega_1_2(D_bits, f_arr, N):
    """Ω_1 and Ω_2 of D_bits (state1 XOR diff) against feature f_arr,
    measured across 256 bits of D as "output bits"."""
    sqrtN = math.sqrt(N)
    Y = 2.0 * D_bits.astype(np.float32) - 1.0       # (N, 256)
    sf = 2.0 * f_arr.astype(np.float32) - 1.0        # (N,)

    # direct_z per D-bit
    direct_z = (Y.T @ sf) / sqrtN                    # (256,)

    # chain_1 per D-bit: use D_bits itself as "state" and each D-bit as "output"
    z_in_1 = (Y.T @ sf) / sqrtN                      # same as direct_z (order-1)
    Z_out_1 = (Y.T @ Y[:, :256].astype(np.float32)) / sqrtN  # trivially = identity-ish
    # Actually chain_1(b) = sum over D-bits c of z(D[c], f) * z(D[c], D[b]) / sqrtN
    # = z_in_1.dot(Z_corr[:, b]) / sqrtN where Z_corr[c, b] = corr(D[c], D[b])
    Z_corr = (Y.T @ Y) / sqrtN
    chain_1 = (z_in_1 @ Z_corr) / sqrtN              # (256,)

    omega_1 = float(np.corrcoef(direct_z, chain_1)[0, 1])
    ss1 = int(np.sum(np.sign(direct_z) == np.sign(chain_1)))

    # chain_2 per D-bit
    M_in = (Y.T @ (Y * sf[:, None])) / sqrtN
    iu = np.triu_indices(256, k=1)
    M_in_flat = M_in[iu]
    chain_2 = np.zeros(256, dtype=np.float64)
    for b in range(256):
        st_b = Y[:, b]
        M_out_b = (Y.T @ (Y * st_b[:, None])) / sqrtN
        chain_2[b] = float((M_in_flat * M_out_b[iu]).sum() / sqrtN)
    omega_2 = float(np.corrcoef(direct_z, chain_2)[0, 1])
    ss2 = int(np.sum(np.sign(direct_z) == np.sign(chain_2)))

    return direct_z, omega_1, ss1, omega_2, ss2


def main():
    t_total = time.time()
    print(f"# IT-7: collision-relevant chain probe on state1 XOR-differences")
    print(f"# N_pairs = {N_PAIRS}")

    # Generate random pairs
    print("# Generating random message pairs...")
    M1, M2 = gen_random_pairs(N_PAIRS)

    # Compute SHA-256 outputs
    print("# Computing SHA-256 full digests...")
    t0 = time.time()
    h1 = sha256_full(M1)
    h2 = sha256_full(M2)
    print(f"  hashing: {time.time()-t0:.1f}s")

    # Output difference bits
    h1_bits = digest_to_bits(h1)
    h2_bits = digest_to_bits(h2)
    delta_h = (h1_bits ^ h2_bits).astype(np.uint8)   # (N, 256) XOR diff of outputs

    # HW of output difference
    hw_delta_h = delta_h.sum(axis=1)                  # (N,) Hamming weight
    print(f"  mean HW(delta_h) = {hw_delta_h.mean():.2f}  (expected 128)")
    print(f"  min HW = {hw_delta_h.min()}, max HW = {hw_delta_h.max()}")

    # Feature: is this pair "close to collision"? HW < 128
    f_near_collision = (hw_delta_h < 128).astype(np.uint8)
    print(f"  f_near_collision: {f_near_collision.sum()}/{N_PAIRS} = {f_near_collision.mean():.4f}")

    # Also: use HW < 120 (even closer to collision)
    f_very_near = (hw_delta_h < 120).astype(np.uint8)
    print(f"  f_very_near (HW<120): {f_very_near.sum()}/{N_PAIRS}")

    # Feature: lowest byte of HW (continuous proxy encoded as bit)
    f_hw_lsb = (hw_delta_h & 1).astype(np.uint8)

    # Compute state1 differences
    print("\n# Computing state1 (block 1 output) for both M and M'...")
    t0 = time.time()
    s1_a = sha256_block1_state(M1)
    s1_b = sha256_block1_state(M2)
    print(f"  state1 compute: {time.time()-t0:.1f}s")

    # State1 XOR difference
    D_state = (s1_a ^ s1_b)
    D_bits = state_to_bits(D_state)                   # (N, 256)
    hw_D = D_bits.sum(axis=1)
    print(f"  mean HW(D_state1) = {hw_D.mean():.2f}  (expected 128)")

    # ---- Main measurement: Ω_k of state1-XOR-diff ----

    print(f"\n# Ω_k measurement: D_state1 vs f_near_collision")
    print(f"#   D_bits as 'state', each D-bit as 'output bit'")
    print(f"#   f_in = near-collision indicator (HW < 128)")

    t0 = time.time()
    dz, o1, ss1, o2, ss2 = compute_omega_1_2(D_bits, f_near_collision, N_PAIRS)
    print(f"  Ω_1 = {o1:+.4f}  same-sign = {ss1}/256")
    print(f"  Ω_2 = {o2:+.4f}  same-sign = {ss2}/256")
    print(f"  max|direct_z| = {np.abs(dz).max():.3f}")
    print(f"  time: {time.time()-t0:.1f}s")

    thresh = 3 / math.sqrt(254)
    print(f"  3σ threshold = {thresh:.4f}")
    print(f"  Ω_1 significant: {'YES' if abs(o1) > thresh else 'no'}")
    print(f"  Ω_2 significant: {'YES' if abs(o2) > thresh else 'no'}")

    # Repeat with f_very_near
    print(f"\n# Same with f_very_near (HW < 120):")
    t0 = time.time()
    dz2, o1b, ss1b, o2b, ss2b = compute_omega_1_2(D_bits, f_very_near, N_PAIRS)
    print(f"  Ω_1 = {o1b:+.4f}  same-sign = {ss1b}/256")
    print(f"  Ω_2 = {o2b:+.4f}  same-sign = {ss2b}/256")
    print(f"  max|direct_z| = {np.abs(dz2).max():.3f}")
    print(f"  time: {time.time()-t0:.1f}s")

    # Repeat with HW_lsb (parity of collision distance)
    print(f"\n# HW parity feature:")
    t0 = time.time()
    dz3, o1c, ss1c, o2c, ss2c = compute_omega_1_2(D_bits, f_hw_lsb, N_PAIRS)
    print(f"  Ω_1 = {o1c:+.4f}  same-sign = {ss1c}/256")
    print(f"  Ω_2 = {o2c:+.4f}  same-sign = {ss2c}/256")
    print(f"  max|direct_z| = {np.abs(dz3).max():.3f}")
    print(f"  time: {time.time()-t0:.1f}s")

    # ---- Verdict ----
    print(f"\n## Verdict")
    any_sig = any(abs(x) > thresh for x in [o1, o2, o1b, o2b, o1c, o2c])
    if any_sig:
        print("  SIGNAL DETECTED in state1 XOR-difference vs collision proximity.")
        print("  Chain-test finds structure that thermostаt hides from marginal metrics.")
        print("  This opens a potential channel for chain-guided collision search.")
    else:
        print("  No chain-detectable structure in state1 XOR-diff vs collision proximity.")
        print("  State1 difference is RO-like even for chain-test at this N.")
        print("  Either N is too small, or the opening is even more subtle.")
        if N_PAIRS < 1000000:
            print(f"  Note: N={N_PAIRS}. Larger N might reveal sub-threshold signals.")

    out = {
        'meta': {'N_pairs': N_PAIRS},
        'near_collision_128': {'omega_1': o1, 'ss1': ss1, 'omega_2': o2, 'ss2': ss2,
                               'max_dz': float(np.abs(dz).max())},
        'very_near_120': {'omega_1': o1b, 'ss1': ss1b, 'omega_2': o2b, 'ss2': ss2b,
                           'max_dz': float(np.abs(dz2).max())},
        'hw_parity': {'omega_1': o1c, 'ss1': ss1c, 'omega_2': o2c, 'ss2': ss2c,
                       'max_dz': float(np.abs(dz3).max())},
        'hw_stats': {'mean': float(hw_delta_h.mean()), 'std': float(hw_delta_h.std()),
                     'min': int(hw_delta_h.min()), 'max': int(hw_delta_h.max())},
        'thresh_3sig': thresh,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total: {time.time()-t_total:.0f}s")


if __name__ == '__main__':
    main()
