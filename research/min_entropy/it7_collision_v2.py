"""
IT-7 v2 (corrected): state1-diff as state, hash-diff as output.

Previous version had artifact: D_bits used as both state AND output
→ trivial Ω_1 ≈ 1 from self-correlation.

Correct setup:
  state  = D_state1 = state1(M) ⊕ state1(M')   — 256-bit intermediate
  output = delta_h  = SHA-256(M) ⊕ SHA-256(M')  — 256-bit hash diff
  f_in   = near-collision indicator: HW(delta_h) < threshold

Ω_k measures: does Walsh-k structure of state1_diff explain the
relationship between "being a near-collision pair" and "specific
hash-diff bit patterns"?

If high Ω_k → state1_diff carries collision-relevant structure
at Walsh order k, potentially exploitable by chain-guided search.
"""
import hashlib, json, math, os, time
import numpy as np

N_PAIRS = 200000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it7v2_collision.json')


def main():
    t_total = time.time()
    print(f"# IT-7 v2: corrected collision probe")
    print(f"# state=D_state1, output=delta_h, feature=near_collision")

    import sha256_chimera as ch

    rng = np.random.default_rng(0xC011DE)
    M1 = [rng.bytes(64) for _ in range(N_PAIRS)]
    M2 = [rng.bytes(64) for _ in range(N_PAIRS)]

    # Full SHA-256 digests
    print("# Hashing...")
    t0 = time.time()
    h1 = [hashlib.sha256(m).digest() for m in M1]
    h2 = [hashlib.sha256(m).digest() for m in M2]
    print(f"  {time.time()-t0:.1f}s")

    # Hash diff bits
    h1_arr = np.frombuffer(b''.join(h1), dtype=np.uint8).reshape(N_PAIRS, 32)
    h2_arr = np.frombuffer(b''.join(h2), dtype=np.uint8).reshape(N_PAIRS, 32)
    delta_h_bytes = h1_arr ^ h2_arr
    delta_h_bits = np.unpackbits(delta_h_bytes, axis=1, bitorder='big')  # (N, 256)

    hw = delta_h_bits.sum(axis=1)
    print(f"  HW(delta_h): mean={hw.mean():.2f} min={hw.min()} max={hw.max()}")

    # State1 via chimera
    print("# Computing state1...")
    t0 = time.time()
    def block1_state(messages):
        N = len(messages)
        U32 = ch.U32
        M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
        block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
        state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
        return ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)

    s1a = block1_state(M1)
    s1b = block1_state(M2)
    D_state = s1a ^ s1b   # (N, 8) uint32

    def state_to_bits(state):
        N = state.shape[0]; bits = np.zeros((N, 256), dtype=np.uint8)
        for w in range(8):
            for b in range(32):
                bits[:, w*32+b] = ((state[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
        return bits

    D_bits = state_to_bits(D_state)  # (N, 256) — state1 XOR diff
    print(f"  {time.time()-t0:.1f}s  HW(D_state1): mean={D_bits.sum(axis=1).mean():.2f}")

    # Features
    f_near = (hw < 128).astype(np.uint8)
    f_vnear = (hw < 120).astype(np.uint8)
    f_hw_lsb = (hw & 1).astype(np.uint8)

    sqrtN = math.sqrt(N_PAIRS)
    thresh = 3 / math.sqrt(254)

    results = {}
    for fname, f_arr in [('near128', f_near), ('vnear120', f_vnear), ('hw_lsb', f_hw_lsb)]:
        print(f"\n## Feature: {fname}  (mean={f_arr.mean():.4f})")

        # State = D_bits (state1 XOR diff), Output = delta_h_bits (hash diff)
        Y = 2.0 * D_bits.astype(np.float32) - 1.0     # state (N, 256)
        st = 2.0 * delta_h_bits.astype(np.float32) - 1.0  # output (N, 256)
        sf = 2.0 * f_arr.astype(np.float32) - 1.0     # feature (N,)

        # direct_z: corr(f_in, delta_h[b]) — does NOT go through state1
        direct_z = (st.T @ sf) / sqrtN  # (256,)
        print(f"  max|direct_z| = {np.abs(direct_z).max():.3f}")

        # chain_1: sum over D_state1 bits c of z(D[c], f) * z(D[c], delta_h[b]) / sqrtN
        z_in_1 = (Y.T @ sf) / sqrtN          # (256,) z(each D-bit, feature)
        Z_out_1 = (Y.T @ st) / sqrtN         # (256 D-bits, 256 h-bits)
        chain_1 = (z_in_1 @ Z_out_1) / sqrtN  # (256,)
        o1 = float(np.corrcoef(direct_z, chain_1)[0, 1])
        ss1 = int(np.sum(np.sign(direct_z) == np.sign(chain_1)))

        # chain_2
        t0 = time.time()
        M_in = (Y.T @ (Y * sf[:, None])) / sqrtN  # (256, 256)
        iu = np.triu_indices(256, k=1)
        M_in_flat = M_in[iu]
        chain_2 = np.zeros(256, dtype=np.float64)
        for b in range(256):
            st_b = st[:, b]
            M_out_b = (Y.T @ (Y * st_b[:, None])) / sqrtN
            chain_2[b] = float((M_in_flat * M_out_b[iu]).sum() / sqrtN)
        o2 = float(np.corrcoef(direct_z, chain_2)[0, 1])
        ss2 = int(np.sum(np.sign(direct_z) == np.sign(chain_2)))

        sig1 = 'YES' if abs(o1) > thresh else 'no'
        sig2 = 'YES' if abs(o2) > thresh else 'no'
        print(f"  Omega_1 = {o1:+.4f}  ss={ss1}/256  sig={sig1}")
        print(f"  Omega_2 = {o2:+.4f}  ss={ss2}/256  sig={sig2}  ({time.time()-t0:.0f}s)")

        results[fname] = {
            'omega_1': o1, 'ss1': ss1, 'omega_2': o2, 'ss2': ss2,
            'max_dz': float(np.abs(direct_z).max()),
            'sig_1': sig1, 'sig_2': sig2,
        }

    print(f"\n## 3σ threshold = {thresh:.4f}")
    any_sig = any(r['sig_1'] == 'YES' or r['sig_2'] == 'YES' for r in results.values())
    print(f"## Any significant: {any_sig}")

    out = {'meta': {'N': N_PAIRS, 'thresh': thresh}, 'results': results}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}\nTotal: {time.time()-t_total:.0f}s")


if __name__ == '__main__':
    main()
