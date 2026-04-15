"""
IT-4.Q7c: 3rd-order Walsh scan on state1 using C program.

Python wrapper:
  1. Enumerate HW=2 inputs.
  2. Compute state1 bits (after block 1 of SHA-256).
  3. Pack state1 into bitmasks + f_mask for bit5_max.
  4. Write to a temp binary file.
  5. Invoke C program it4_q7c_walsh3.
  6. Parse JSON output.
  7. Repeat for R RO realizations (keyed BLAKE2b).
  8. Compare SHA-256 vs RO band.
"""

import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np

import sha256_chimera as ch

LENGTH_BITS = 512
R_RO = 50
SEED = 0xC33C
WORDS = 2048              # must match C macro
C_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7c_walsh3')
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it4_q7c_results.json')


def low_hw2():
    L = 64
    inputs, pos = [], []
    for positions in combinations(range(LENGTH_BITS), 2):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        inputs.append(bytes(b))
        pos.append(positions)
    return inputs, pos


def state_after_block1(messages):
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


def keyed_blake_bits(inputs, key):
    N = len(inputs)
    byte_mat = np.empty((N, 32), dtype=np.uint8)
    for i, x in enumerate(inputs):
        byte_mat[i] = np.frombuffer(hashlib.blake2b(x, key=key, digest_size=32).digest(), dtype=np.uint8)
    return np.unpackbits(byte_mat, axis=1, bitorder='big')


def pack_bitmask(bits_vec):
    """bits_vec: (N,) uint8 0/1. Return WORDS uint64 with bit i = bits_vec[i]."""
    padded = np.zeros(WORDS * 64, dtype=np.uint8)
    padded[:len(bits_vec)] = bits_vec
    packed_bytes = np.packbits(padded, bitorder='little')
    # interpret bytes as little-endian uint64
    return np.frombuffer(packed_bytes.tobytes(), dtype=np.uint64)


def write_input_bin(state_bits, f_arr, path):
    """Binary format expected by C program:
       uint64 N | 256*WORDS uint64 state_bitmasks | WORDS uint64 f_mask
    """
    N = len(f_arr)
    with open(path, 'wb') as fp:
        fp.write(np.uint64(N).tobytes())
        for b in range(256):
            mask = pack_bitmask(state_bits[:, b])
            fp.write(mask.tobytes())
        f_mask = pack_bitmask(f_arr)
        fp.write(f_mask.tobytes())


def run_c_scan(bin_path):
    res = subprocess.run([C_BIN, bin_path], capture_output=True, text=True, check=True)
    return json.loads(res.stdout)


def sanity_check(inputs, pos):
    """Verify: bit5_max as itself (= state is f_mask) gives trivially max|z| = √N.
    Actually, let's test: use f_mask as state1 bit 0 → all triples including bit 0
    and 2 random-ish bits should have specific structure. Simpler sanity:
    compute 1st-order Walsh (subset of size 0: just popcount(f_mask) vs N/2).
    """
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f_arr = ((max_p >> 5) & 1).astype(np.uint8)
    print(f"# Sanity: N={N}, mean(f) = {f_arr.mean():.4f} (expected ≈ 0.5)")
    # A trivial triple (0, 1, 2) of bit5_max as all three bits:
    # state1 = f_arr at all bit positions → XOR of 3 = XOR of 3 copies = f_arr itself
    # So popcount = pop(f_arr XOR f_arr) = 0 → walsh = 1 → z = sqrt(N) = 362
    # Let's build a synthetic state1 where every bit = f_arr, and check.
    fake_state = np.broadcast_to(f_arr[:, None], (N, 256)).copy()
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        tmp_path = tmp.name
    try:
        write_input_bin(fake_state, f_arr, tmp_path)
        result = run_c_scan(tmp_path)
        print(f"  Sanity C result: max_abs_z = {result['max_abs_z']:.3f}  "
              f"(expected ≈ {math.sqrt(N):.2f})")
        assert result['max_abs_z'] > 0.9 * math.sqrt(N), \
            f"Sanity failed: {result['max_abs_z']} vs {math.sqrt(N)}"
    finally:
        os.unlink(tmp_path)
    print("  Sanity ✓")


def main():
    t_total = time.time()
    print("# IT-4.Q7c: 3rd-order Walsh scan via C program")
    if not os.path.exists(C_BIN):
        print(f"ERROR: C binary not found at {C_BIN}")
        print("Build with: gcc -O3 -march=native -funroll-loops -o it4_q7c_walsh3 it4_q7c_walsh3.c -lm")
        return

    inputs, pos = low_hw2()
    N = len(inputs)
    max_p = np.asarray([p[-1] for p in pos], dtype=np.int64)
    f_arr = ((max_p >> 5) & 1).astype(np.uint8)
    print(f"# N = {N}, feature = bit5_max")

    # Sanity check
    sanity_check(inputs, pos)

    # ---- SHA-256 ----
    print("\n# Computing state1 for SHA-256...")
    t0 = time.time()
    state1 = state_after_block1(inputs)
    state1_bits = state_to_bits(state1)
    print(f"  state1 bits: {state1_bits.shape}  ({time.time()-t0:.1f}s)")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        sha_bin_path = tmp.name
    t0 = time.time()
    write_input_bin(state1_bits, f_arr, sha_bin_path)
    print(f"  Wrote bin file: {os.path.getsize(sha_bin_path) / 1024 / 1024:.2f} MB "
          f"({time.time()-t0:.1f}s)")

    print("  Running C scan for SHA-256...")
    t0 = time.time()
    sha_result = run_c_scan(sha_bin_path)
    sha_elapsed = time.time() - t0
    print(f"  Scan complete in {sha_elapsed:.1f}s:")
    print(f"    max|z| = {sha_result['max_abs_z']:.3f}  at triple {sha_result['best_triple']}")
    print(f"    Σz² = {sha_result['sum_z2']:.1f}  over {sha_result['n_triples']} triples")
    print(f"    n_above_3 = {sha_result['n_above_3']}  (expected ≈ "
          f"{sha_result['n_triples'] * 2.7e-3:.0f} under H_0)")
    print(f"    n_above_4 = {sha_result['n_above_4']}  (expected ≈ "
          f"{sha_result['n_triples'] * 6.3e-5:.1f} under H_0)")
    print(f"    n_above_5 = {sha_result['n_above_5']}  (expected ≈ "
          f"{sha_result['n_triples'] * 5.7e-7:.3f} under H_0)")
    os.unlink(sha_bin_path)

    # ---- RO null ----
    print(f"\n# RO null: R={R_RO} keyed-BLAKE2b realizations")
    nprng = np.random.default_rng(SEED)
    keys = [nprng.bytes(16) for _ in range(R_RO)]

    ro_max_abs = []
    ro_sum_z2 = []
    ro_n_above_4 = []
    ro_n_above_5 = []
    ro_top_triples = []

    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tmp:
        ro_bin_path = tmp.name
    t0_loop = time.time()
    try:
        for r, key in enumerate(keys):
            t0 = time.time()
            ro_bits = keyed_blake_bits(inputs, key)
            write_input_bin(ro_bits, f_arr, ro_bin_path)
            result = run_c_scan(ro_bin_path)
            ro_max_abs.append(result['max_abs_z'])
            ro_sum_z2.append(result['sum_z2'])
            ro_n_above_4.append(result['n_above_4'])
            ro_n_above_5.append(result['n_above_5'])
            ro_top_triples.append(result['top_k'][:5])
            el = time.time() - t0_loop
            eta = el / (r + 1) * (R_RO - r - 1)
            print(f"  r={r+1}/{R_RO}  max|z|={result['max_abs_z']:.2f}  "
                  f"Σz²={result['sum_z2']:.0f}  n>5={result['n_above_5']}  "
                  f"iter_time={time.time()-t0:.1f}s  total={el:.0f}s  eta={eta:.0f}s")
    finally:
        os.unlink(ro_bin_path)

    ro_max_abs = np.asarray(ro_max_abs)
    ro_sum_z2 = np.asarray(ro_sum_z2)
    ro_n5 = np.asarray(ro_n_above_5)
    ro_n4 = np.asarray(ro_n_above_4)

    print(f"\n## RO band statistics over R={R_RO}")
    print(f"  max|z|:   mean={ro_max_abs.mean():.3f}  std={ro_max_abs.std(ddof=1):.3f}  "
          f"q95={np.quantile(ro_max_abs, 0.95):.3f}  q99={np.quantile(ro_max_abs, 0.99):.3f}")
    print(f"  Σz²:      mean={ro_sum_z2.mean():.1f}  std={ro_sum_z2.std(ddof=1):.1f}")
    print(f"  n_above_4: mean={ro_n4.mean():.1f}   std={ro_n4.std(ddof=1):.1f}")
    print(f"  n_above_5: mean={ro_n5.mean():.2f}  std={ro_n5.std(ddof=1):.2f}")

    # Compare
    p_max = float((ro_max_abs >= sha_result['max_abs_z']).sum() + 1) / (R_RO + 1)
    p_sum = float((np.abs(ro_sum_z2 - ro_sum_z2.mean()) >=
                   abs(sha_result['sum_z2'] - ro_sum_z2.mean())).sum() + 1) / (R_RO + 1)
    print(f"\n## SHA-256 vs RO")
    print(f"  max|z|: SHA={sha_result['max_abs_z']:.3f}, P(RO ≥ SHA) = {p_max:.4f}")
    z_norm_max = (sha_result['max_abs_z'] - ro_max_abs.mean()) / ro_max_abs.std(ddof=1)
    z_norm_sum = (sha_result['sum_z2'] - ro_sum_z2.mean()) / ro_sum_z2.std(ddof=1)
    print(f"  Σz²:    SHA={sha_result['sum_z2']:.1f},  z_norm={z_norm_sum:+.3f}, p={p_sum:.4f}")
    print(f"  max|z| z_norm: {z_norm_max:+.3f}")

    # Save
    out = {
        'meta': {'N': N, 'R_RO': R_RO, 'feature': 'bit5_max', 'HW': 2,
                 'n_triples': sha_result['n_triples']},
        'sha': sha_result,
        'ro_band': {
            'max_abs_z': {'values': ro_max_abs.tolist(),
                          'mean': float(ro_max_abs.mean()),
                          'std': float(ro_max_abs.std(ddof=1)),
                          'q95': float(np.quantile(ro_max_abs, 0.95)),
                          'q99': float(np.quantile(ro_max_abs, 0.99))},
            'sum_z2':    {'values': ro_sum_z2.tolist(),
                          'mean': float(ro_sum_z2.mean()),
                          'std': float(ro_sum_z2.std(ddof=1))},
            'n_above_4': {'values': ro_n4.tolist(),
                          'mean': float(ro_n4.mean()),
                          'std': float(ro_n4.std(ddof=1))},
            'n_above_5': {'values': ro_n5.tolist(),
                          'mean': float(ro_n5.mean()),
                          'std': float(ro_n5.std(ddof=1))},
        },
        'verdict': {
            'z_norm_max': float(z_norm_max),
            'p_max': p_max,
            'z_norm_sum': float(z_norm_sum),
            'p_sum': p_sum,
        },
    }
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT_JSON}")
    print(f"Total time: {time.time()-t_total:.1f}s")


if __name__ == '__main__':
    main()
