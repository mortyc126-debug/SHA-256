"""IT-33: Phase-transition map of Omega_3 vs HC optimization intensity.

Run one long HC (200 iterations) with snapshots at iter ∈ {0, 40, 80, 120, 160, 200}.
At each snapshot measure:
- Mean STATE_SUM at r=62 (HC objective)
- Ω_3 on full 256-bit spectrum (stride=8)
- phi for methodology bits H[6][b28,29,31], H[7][b29]
- phi for our H[5][b0..b5] bits
- TV advantage for combined 9 bits

Key questions:
1. Does Omega_3 grow monotonically with HC pressure?
2. Does it plateau or approach 1.0 asymptotically?
3. Where is the phase transition (if any)?
4. Do methodology and our H[5] bits emerge at same HC intensity or different?
"""
import json, math, os, subprocess, tempfile, time
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'omega3_full')

N_SAMPLES = 20000
N_ITERS = 200
SNAPSHOTS = [0, 40, 80, 120, 160, 200]


def state_sum_r62(inputs):
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
    for t in range(62):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    return (a.astype(np.uint64) + b.astype(np.uint64) + c.astype(np.uint64) + d.astype(np.uint64)
          + e.astype(np.uint64) + f.astype(np.uint64) + g.astype(np.uint64) + h.astype(np.uint64))


def compute_full_hash(inputs):
    N = inputs.shape[0]
    b1 = inputs.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1,
                     ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    pad_block = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    pad_block = np.broadcast_to(pad_block, (N, 16))
    s2 = ch.compress(s1, pad_block, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    return s1, s2


def sb(s, N):
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w*32+b] = ((s[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits


def pack(v):
    pd = np.zeros(WORDS*64, dtype=np.uint8); pd[:len(v)] = v
    return np.frombuffer(np.packbits(pd, bitorder='little').tobytes(), dtype=np.uint64)


def measure_snapshot(inputs, snap_name):
    """Measure all metrics for this snapshot of HC-optimized inputs."""
    N = inputs.shape[0]
    ss = state_sum_r62(inputs)
    s1, s2 = compute_full_hash(inputs)
    s1b = sb(s1, N); s2b = sb(s2, N)
    phi = s2b.sum(axis=0) / N - 0.5
    z = phi / (0.5/np.sqrt(N))
    # Methodology bits
    meth_idx = [220, 221, 223, 253]
    our_idx = [160, 161, 162, 163, 164, 165]
    meth_phi = phi[meth_idx]
    our_phi = phi[our_idx]
    # Omega_3
    fa = (np.unpackbits(inputs, axis=1).sum(axis=1) & 1).astype(np.uint8)
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf: tp = tf.name
    try:
        with open(tp, 'wb') as fp:
            fp.write(np.uint64(N).tobytes())
            for b in range(256): fp.write(pack(s1b[:, b]).tobytes())
            fp.write(pack(fa).tobytes())
            for b in range(256): fp.write(pack(s2b[:, b]).tobytes())
        res = subprocess.run([C_BIN, tp, '8'], capture_output=True, text=True, check=True, timeout=120)
        d = json.loads(res.stdout)
    finally:
        os.unlink(tp)

    max_z = np.abs(z).max()
    sig_bits = (np.abs(z) > 3).sum()
    print(f"[{snap_name}]  SS_mean={ss.mean():.3e}  Ω_3={d['omega3']:+.4f}  "
          f"ss={d['same_sign']}/256  max|z|={max_z:.2f}  sig_bits({{|z|>3}})={sig_bits}  "
          f"meth_max_z={max(abs(z[i]) for i in meth_idx):.2f}  "
          f"our_max_z={max(abs(z[i]) for i in our_idx):.2f}", flush=True)

    return {
        'snap': snap_name,
        'N': N,
        'SS_mean': float(ss.mean()),
        'SS_min': float(ss.min()),
        'omega3': d['omega3'],
        'ss_omega3': d['same_sign'],
        'max_z': float(max_z),
        'n_sig_bits': int(sig_bits),
        'meth_phi': meth_phi.tolist(),
        'meth_z': [float(z[i]) for i in meth_idx],
        'our_phi': our_phi.tolist(),
        'our_z': [float(z[i]) for i in our_idx],
        'phi_top20_bits': [int(i) for i in np.argsort(-np.abs(z))[:20]],
        'phi_top20_z': [float(z[i]) for i in np.argsort(-np.abs(z))[:20]],
    }


def main():
    t0 = time.time()
    rng = np.random.default_rng(0x13370102)
    print(f"# IT-33: Phase-transition scan (N={N_SAMPLES}, HC iters={N_ITERS})")
    print(f"# Snapshots at iters: {SNAPSHOTS}")

    inputs = rng.integers(0, 256, size=(N_SAMPLES, 64), dtype=np.uint8)

    # Initial snapshot (iter=0)
    print(f"\n### Measuring snapshot iter=0 (random inputs)...")
    results = [measure_snapshot(inputs.copy(), 'iter=0')]

    # Run HC with snapshots
    ss_current = state_sum_r62(inputs)
    accepts = 0
    next_snap_idx = 1
    print(f"\n### Starting HC optimization...")
    for it in range(N_ITERS):
        # Flip 1 bit in first 8 bytes (W[0..1]) per sample
        trial = inputs.copy()
        byte_idx = rng.integers(0, 8, size=N_SAMPLES)
        bit_idx = rng.integers(0, 8, size=N_SAMPLES)
        for i in range(N_SAMPLES):
            trial[i, byte_idx[i]] ^= (1 << bit_idx[i])
        ss_trial = state_sum_r62(trial)
        better = ss_trial < ss_current
        inputs = np.where(better[:, None], trial, inputs)
        ss_current = np.where(better, ss_trial, ss_current)
        accepts += better.sum()
        # Snapshot check
        if next_snap_idx < len(SNAPSHOTS) and (it + 1) == SNAPSHOTS[next_snap_idx]:
            print(f"\n### Snapshot iter={it+1}", flush=True)
            results.append(measure_snapshot(inputs.copy(), f'iter={it+1}'))
            next_snap_idx += 1

    # Print summary table
    print(f"\n=== IT-33 SUMMARY TABLE ===")
    print(f"{'snapshot':<10} {'SS_mean':>10} {'Ω_3':>9} {'ss':>9} {'max|z|':>7} {'#sig':>5} "
          f"{'meth_max_z':>10} {'our_max_z':>9}")
    for r in results:
        meth_max = max(abs(v) for v in r['meth_z'])
        our_max = max(abs(v) for v in r['our_z'])
        print(f"{r['snap']:<10} {r['SS_mean']:>10.2e} {r['omega3']:>+9.4f} {r['ss_omega3']:>4}/256 "
              f"{r['max_z']:>7.2f} {r['n_sig_bits']:>5}  {meth_max:>10.2f} {our_max:>9.2f}")

    with open(os.path.join(HERE, 'it33_phase_map.json'), 'w') as f:
        json.dump({'meta': {'N_SAMPLES': N_SAMPLES, 'N_ITERS': N_ITERS,
                            'snapshots': SNAPSHOTS}, 'results': results}, f, indent=2)

    print(f"\n--- KEY OBSERVATIONS ---")
    omega_trajectory = [r['omega3'] for r in results]
    ss_trajectory = [r['SS_mean'] for r in results]
    print(f"Ω_3 trajectory: {[f'{v:+.3f}' for v in omega_trajectory]}")
    print(f"SS trajectory: {[f'{v:.2e}' for v in ss_trajectory]}")

    # Growth rate
    if len(omega_trajectory) >= 2:
        delta = omega_trajectory[-1] - omega_trajectory[0]
        print(f"Ω_3 total increase over HC: {delta:+.4f}")
        if omega_trajectory[-1] > 0.99:
            print("  → APPROACHES 1.0 — deterministic regime")
        elif delta > 0.10:
            print(f"  → significant growth, structure amplified by HC")
        else:
            print(f"  → small change, Ω_3 robust to HC intensity")

    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == '__main__':
    main()
