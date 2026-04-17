"""IT-30: Omega_3 on HC-optimized inputs (carry[62]=0 filtered).

Methodology's T_COMMIT_HIDING works on HC-optimized inputs where carry[62]=0
in block-2 compression. On these inputs, 4 hash bits H[6][b28,29,31], H[7][b29]
are biased with combined advantage = 0.30.

Our Ω_3 = +0.85 works on HW=2 inputs but gives no per-pair signal.

Hypothesis: if we apply Ω_3 on THE SAME input class as methodology (carry[62]=0),
it may give STRONGER structure than on HW=2 — because chosen-prefix creates
specific structural bias that Ω_3 can amplify.

Method:
1. Generate random 64-byte inputs.
2. For each, compute block-2 state through round 62 to check carry[62].
   carry[62] = carry-out of addition e[63] = d[62] + T1[62] mod 2^32.
3. Filter to inputs where carry[62] = 0.
4. Apply omega3_full to filtered set (target 130816 inputs).
5. Compare Ω_3 on HC-inputs vs HW=2 baseline (+0.85).

If Ω_3 on HC-inputs > +0.90 → methodology+Ω_3 combination gives stronger
structure, improved distinguisher possible.
"""
import hashlib, json, math, os, subprocess, tempfile, time
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'omega3_full')
N_TARGET = 130816
STRIDE = 8


def gen_random_inputs(N_raw, seed=0x11D)  :
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(N_raw, 64), dtype=np.uint8)


def compute_state_at_r(inputs, n_rounds):
    """Run full block-1 + partial block-2 (n_rounds) for given inputs. Returns state."""
    N = inputs.shape[0]
    b1 = inputs.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1,
                     ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    pad_block = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    pad_block = np.broadcast_to(pad_block, (N, 16))

    U32, MASK = ch.U32, ch.MASK
    W = np.empty((N, max(n_rounds, 16)), dtype=U32); W[:, :16] = pad_block
    for t in range(16, max(n_rounds, 16)):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK

    a, b, c, d, e, f, g, h = (s1[:, i].copy() for i in range(8))
    K = ch.K_VANILLA
    for t in range(n_rounds):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e_new = (d + T1) & MASK
        e = e_new
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    return s1, np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)


def compute_carry62(inputs):
    """Check carry-out at round 62 of block 2. Returns 0/1 array per input."""
    N = inputs.shape[0]
    b1 = inputs.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1,
                     ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    pad_block = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    pad_block = np.broadcast_to(pad_block, (N, 16))

    U32, MASK = ch.U32, ch.MASK
    W = np.empty((N, 64), dtype=U32); W[:, :16] = pad_block
    for t in range(16, 64):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK

    a, b, c, d, e, f, g, h = (s1[:, i].copy() for i in range(8))
    K = ch.K_VANILLA
    carry62 = None
    for t in range(63):  # iterate through round 62
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        # carry-out of (d + T1): MSB carry
        if t == 62:
            d64 = d.astype(np.uint64)
            T1_64 = T1.astype(np.uint64)
            carry62 = ((d64 + T1_64) >> 32).astype(np.uint8)
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    return carry62


def sb(s, N):
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w*32+b] = ((s[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits


def pack(v):
    pd = np.zeros(WORDS*64, dtype=np.uint8); pd[:len(v)] = v
    return np.frombuffer(np.packbits(pd, bitorder='little').tobytes(), dtype=np.uint64)


def main():
    t0 = time.time()
    print("# IT-30: Ω_3 on HC-optimized inputs (carry[62]=0)")

    # Generate raw inputs; filter to carry[62]=0
    # Methodology: natural fraction ~25-50% (varies), so 300K raw → ~130K filtered
    N_RAW = 300000
    print(f"# Generating {N_RAW} random inputs...", flush=True)
    inputs = gen_random_inputs(N_RAW)

    print(f"# Computing carry[62] for each...", flush=True)
    ts = time.time()
    carry62 = compute_carry62(inputs)
    print(f"  time: {time.time()-ts:.0f}s, carry[62]=0 fraction: {(carry62==0).sum()/N_RAW:.3f}", flush=True)

    # Filter carry[62]=0
    filtered_idx = np.where(carry62 == 0)[0]
    print(f"# After filter: {len(filtered_idx)} inputs", flush=True)
    if len(filtered_idx) < N_TARGET:
        print(f"# NOT ENOUGH FILTERED ({len(filtered_idx)} < {N_TARGET}). Need more raw.")
        # Generate more
        N_MORE = N_RAW
        print(f"# Generating {N_MORE} more...")
        more = gen_random_inputs(N_MORE, seed=0x22D)
        more_c = compute_carry62(more)
        more_idx = np.where(more_c == 0)[0]
        inputs = np.concatenate([inputs, more])
        carry62 = np.concatenate([carry62, more_c])
        filtered_idx = np.where(carry62 == 0)[0]
        print(f"# After additional filter: {len(filtered_idx)} total")

    # Take first N_TARGET
    use_idx = filtered_idx[:N_TARGET]
    hc_inputs = inputs[use_idx]
    N = len(hc_inputs)
    print(f"# Using {N} HC-optimized inputs")

    # Feature: HW parity of input
    fa = (np.unpackbits(hc_inputs, axis=1).sum(axis=1) & 1).astype(np.uint8)

    # Compute full SHA
    print("# Computing SHA states...", flush=True)
    s1, s2 = compute_state_at_r(hc_inputs, 64)  # actually computes full block2
    s1b = sb(s1, N); s2b = sb(s2, N)

    # Also measure per-bit phi on HC-inputs
    ones_hc = s2b.sum(axis=0)
    phi_hc = ones_hc / N - 0.5
    z_phi = phi_hc / (0.5 / np.sqrt(N))

    # Methodology bits check
    print(f"\n=== T_COMMIT_HIDING bits on our HC-filtered inputs ===")
    meth_bits = {'H[6][b28]': 220, 'H[6][b29]': 221, 'H[6][b31]': 223, 'H[7][b29]': 253}
    for lbl, idx in meth_bits.items():
        print(f"  {lbl} (idx {idx}): phi={phi_hc[idx]:+.5f}, z={z_phi[idx]:+.2f}")
    print(f"Max |z| overall: {np.abs(z_phi).max():.2f}")
    top_phi_idx = np.argsort(-np.abs(phi_hc))[:10]
    print(f"Top-10 |phi| bits: {top_phi_idx.tolist()}")
    for i in top_phi_idx[:5]:
        print(f"  bit {i} (H[{i//32}][b{i%32}]): phi={phi_hc[i]:+.5f}, z={z_phi[i]:+.2f}")

    # Run omega3_full
    print(f"\n# Running omega3_full on HC-inputs (stride={STRIDE})...", flush=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf: tp = tf.name
    try:
        with open(tp, 'wb') as fp:
            fp.write(np.uint64(N).tobytes())
            for b in range(256): fp.write(pack(s1b[:, b]).tobytes())
            fp.write(pack(fa).tobytes())
            for b in range(256): fp.write(pack(s2b[:, b]).tobytes())
        ts = time.time()
        res = subprocess.run([C_BIN, tp, str(STRIDE)], capture_output=True, text=True, check=True, timeout=150)
        d = json.loads(res.stdout)
        print(f"  Ω_3 = {d['omega3']:+.4f}  ss = {d['same_sign']}/256  t = {time.time()-ts:.0f}s", flush=True)
    finally:
        os.unlink(tp)

    # Compare to baseline
    print(f"\n=== COMPARISON ===")
    print(f"Baseline (HW=2, feature=bit5_max, stride=8): Ω_3 ≈ +0.85")
    print(f"HC-filtered (random+c62=0, feature=parity,  stride=8): Ω_3 = {d['omega3']:+.4f}")
    if abs(d['omega3']) > 0.9:
        print("  → STRONGER than baseline → HC-inputs amplify Ω_3 signal!")
    elif abs(d['omega3']) > 0.7:
        print("  → similar magnitude, universal invariant confirmed on new input class")
    else:
        print("  → weaker, HC structure doesn't align with Ω_3 direction")

    result = {
        'N': N, 'omega3': d['omega3'], 'ss': d['same_sign'],
        'direct_z': d['direct_z'], 'chain_z': d['chain_z'],
        'phi_hc': phi_hc.tolist(),
        'methodology_bits_phi': {lbl: float(phi_hc[idx]) for lbl, idx in meth_bits.items()},
    }
    with open(os.path.join(HERE, 'it30_hc_omega3.json'), 'w') as f:
        json.dump(result, f)
    print(f"\nWrote it30_hc_omega3.json, total {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
