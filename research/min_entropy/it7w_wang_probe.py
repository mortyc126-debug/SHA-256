"""
IT-7W: Wang-structured chain probe (amplified).

Improvements over IT-7P (which failed):
1. STRUCTURED pairs: fix deltaW[0] = 2^j (single-bit message diff),
   compute delta_e for rounds 1..24. This is the Wang-trail setup
   from v20 methodology.
2. ASYMMETRIC feature: delta_e[17] == 0 (the v20 barrier), not
   symmetric HW threshold.
3. REDUCED rounds via chimera: 16 and 24 rounds where signal is
   stronger (pre-thermostаt regime per IT-5s).
4. Chain-2 Omega on REDUCED-round state_diff.

Question: on Wang-structured pairs at reduced rounds, does chain-2
of state_diff predict whether delta_e[17] = 0?

If yes → chain-guided Wang search can be faster than birthday
at round 17, directly attacking the v20 barrier.
"""

import hashlib, json, math, os, time
import numpy as np
import sha256_chimera as ch

N_PAIRS = 200000
ROUND_LIST = [16, 20, 24, 32]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it7w_wang.json')


def gen_wang_pairs(n, seed=0xACC0):
    """Generate Wang-structured pairs: M' = M with W[0] flipped at bit j.
    For each pair, deltaW[0] = 2^j for random j in [0, 31].
    M is random 64-byte, M' differs only in first 4 bytes (W[0]).
    """
    rng = np.random.default_rng(seed)
    M1_list = []
    M2_list = []
    j_list = []
    for _ in range(n):
        m = bytearray(rng.bytes(64))
        j = int(rng.integers(0, 32))
        m2 = bytearray(m)
        # flip bit j of W[0] (big-endian: byte j//8 from start, bit 7-(j%8))
        byte_idx = j // 8
        bit_in_byte = 7 - (j % 8)
        m2[byte_idx] ^= (1 << bit_in_byte)
        M1_list.append(bytes(m))
        M2_list.append(bytes(m2))
        j_list.append(j)
    return M1_list, M2_list, np.asarray(j_list, dtype=np.int32)


def compress_r(messages, n_rounds):
    """Reduced-round block 1 compression. Returns (N, 8) uint32 state."""
    N = len(messages)
    U32, MASK = ch.U32, ch.MASK
    K = ch.K_VANILLA
    M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
    block = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
    state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()

    W = np.empty((N, max(n_rounds, 16)), dtype=U32)
    W[:, :16] = block
    for t in range(16, n_rounds):
        W[:, t] = (ch.sigma1(W[:, t-2]) + W[:, t-7]
                   + ch.sigma0(W[:, t-15]) + W[:, t-16]) & MASK
    a, b, c, d, e, f, g, h = (state[:, i].copy() for i in range(8))
    for t in range(n_rounds):
        T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
        h = g; g = f; f = e
        e = (d + T1) & MASK
        d = c; c = b; b = a
        a = (T1 + T2) & MASK
    new = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    return (new + state) & MASK


def state_to_bits(state):
    N = state.shape[0]
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w * 32 + b] = ((state[:, w] >> np.uint32(31 - b)) & 1).astype(np.uint8)
    return bits


def extract_e_register(state):
    """e-register = state word 4 (index 4 in [a,b,c,d,e,f,g,h])."""
    return state[:, 4]


def compute_omega_2(Y, sf, st, sqrtN):
    """Omega_2 with state=Y, feature=sf, output=st. All (N, 256)/(N,)."""
    direct_z = (st.T @ sf) / sqrtN
    M_in = (Y.T @ (Y * sf[:, None])) / sqrtN
    iu = np.triu_indices(256, k=1)
    M_in_flat = M_in[iu]
    chain_2 = np.zeros(256, dtype=np.float64)
    for b in range(256):
        st_b = st[:, b]
        M_out_b = (Y.T @ (Y * st_b[:, None])) / sqrtN
        chain_2[b] = float((M_in_flat * M_out_b[iu]).sum() / sqrtN)
    o2 = float(np.corrcoef(direct_z, chain_2)[0, 1])
    ss2 = int(np.sum(np.sign(direct_z) == np.sign(chain_2)))
    max_dz = float(np.abs(direct_z).max())

    # Predictive test: train on first half, predict on second (using score)
    N = len(sf)
    half = N // 2
    M_in_tr = (Y[:half].T @ (Y[:half] * sf[:half, None])) / math.sqrt(half)
    YM = Y[half:].astype(np.float32) @ M_in_tr
    Q = (Y[half:].astype(np.float32) * YM).sum(axis=1)
    tr_val = np.trace(M_in_tr)
    score = (Q - tr_val) / 2
    # Compare score to feature on test half
    corr_pred = float(np.corrcoef(score, sf[half:])[0, 1])

    return o2, ss2, max_dz, corr_pred


def main():
    t_total = time.time()
    print("# IT-7W: Wang-structured chain probe (amplified)")
    print(f"# N_pairs = {N_PAIRS}, rounds = {ROUND_LIST}")

    M1, M2, j_arr = gen_wang_pairs(N_PAIRS)
    print(f"  Generated {N_PAIRS} Wang pairs (single-bit W[0] flip)")

    results = {}
    for r in ROUND_LIST:
        print(f"\n## Round r = {r}")
        t0 = time.time()

        # Compute reduced-round state for both M and M'
        s1 = compress_r(M1, r)
        s2 = compress_r(M2, r)
        D_state = s1 ^ s2
        D_bits = state_to_bits(D_state)

        # Extract e-register difference at round r
        e1 = extract_e_register(s1)
        e2 = extract_e_register(s2)
        delta_e = e1 ^ e2   # (N,) uint32

        # Feature: delta_e == 0 (the barrier condition)
        f_de_zero = (delta_e == 0).astype(np.uint8)
        n_zero = int(f_de_zero.sum())
        print(f"  delta_e[{r}] = 0: {n_zero}/{N_PAIRS} = {f_de_zero.mean():.6f}")

        if n_zero < 10:
            print(f"  Too few delta_e=0 pairs for meaningful Omega measurement")
            results[r] = {'n_zero': n_zero, 'omega_2': None, 'note': 'too few'}
            continue

        # Output bits: full state diff (256 bits)
        # But we want output to be DIFFERENT from state used for Walsh decomp
        # Use: output = hash-diff bits (full SHA-256 output diff)
        # For reduced rounds, output = state_r diff bits (same issue as IT-7 v1)
        # Better: use delta_e bits (32 bits of e-register diff) as partial output
        delta_e_bits = np.zeros((N_PAIRS, 32), dtype=np.uint8)
        for b in range(32):
            delta_e_bits[:, b] = ((delta_e >> np.uint32(31 - b)) & 1).astype(np.uint8)

        # State for Walsh = D_bits (full 256-bit state diff)
        # Output for Omega = delta_e_bits (32-bit e-register diff)
        # Feature = delta_e == 0
        sqrtN = math.sqrt(N_PAIRS)
        Y = 2.0 * D_bits.astype(np.float32) - 1.0
        sf = 2.0 * f_de_zero.astype(np.float32) - 1.0
        st = 2.0 * delta_e_bits.astype(np.float32) - 1.0   # (N, 32)

        # Direct z per e-bit
        direct_z = (st.T @ sf) / sqrtN   # (32,)
        print(f"  max|direct_z| on delta_e bits = {np.abs(direct_z).max():.3f}")

        # Chain-2 on state_diff
        M_in = (Y.T @ (Y * sf[:, None])) / sqrtN
        iu = np.triu_indices(256, k=1)
        M_in_flat = M_in[iu]
        chain_2 = np.zeros(32, dtype=np.float64)
        for b in range(32):
            st_b = st[:, b]
            M_out_b = (Y.T @ (Y * st_b[:, None])) / sqrtN
            chain_2[b] = float((M_in_flat * M_out_b[iu]).sum() / sqrtN)

        if np.std(direct_z) < 1e-10 or np.std(chain_2) < 1e-10:
            print(f"  Degenerate (constant) direct_z or chain_2")
            results[r] = {'n_zero': n_zero, 'omega_2': None, 'note': 'degenerate'}
            continue

        o2 = float(np.corrcoef(direct_z, chain_2)[0, 1])
        ss2 = int(np.sum(np.sign(direct_z) == np.sign(chain_2)))

        # Predictive test on holdout
        half = N_PAIRS // 2
        M_in_tr = (Y[:half].T @ (Y[:half] * sf[:half, None])) / math.sqrt(half)
        YM = Y[half:] @ M_in_tr
        Q = (Y[half:] * YM).sum(axis=1)
        tr_val = float(np.trace(M_in_tr))
        score = (Q - tr_val) / 2
        corr_pred = float(np.corrcoef(score, f_de_zero[half:].astype(np.float32))[0, 1])

        thresh = 3 / math.sqrt(30)   # 32 output bits
        sig = 'YES' if abs(o2) > thresh else 'no'
        print(f"  Omega_2 = {o2:+.4f}  ss={ss2}/32  sig={sig}")
        print(f"  Predictive corr (train/test) = {corr_pred:+.6f}")
        print(f"  time: {time.time()-t0:.1f}s")

        results[r] = {
            'n_zero': n_zero,
            'omega_2': o2, 'ss2': ss2,
            'max_dz': float(np.abs(direct_z).max()),
            'corr_pred': corr_pred,
            'sig': sig,
        }

    print(f"\n## Summary")
    for r in ROUND_LIST:
        info = results.get(r, {})
        if info.get('omega_2') is not None:
            print(f"  r={r:>2}: n_zero={info['n_zero']:>6}  O2={info['omega_2']:+.4f}  "
                  f"pred={info['corr_pred']:+.6f}  sig={info['sig']}")
        else:
            print(f"  r={r:>2}: {info.get('note', 'N/A')}")

    out = {'meta': {'N': N_PAIRS, 'rounds': ROUND_LIST}, 'results': results}
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}\nTotal: {time.time()-t_total:.0f}s")


if __name__ == '__main__':
    main()
