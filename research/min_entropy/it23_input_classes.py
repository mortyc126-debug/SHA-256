"""IT-23: Omega_3 conservation on OTHER input classes.

Tests:
  (a) Random uniform 64-byte inputs (N=130816)
  (b) HW=3 inputs subsampled (N=130816 from C(512,3)=22M)
  (c) Counter inputs (M = i for i=0..N-1)

For each input class, measure Omega_3 at r=0 and r=64 of block 2.
If Omega_3 >> 0 for all classes → UNIVERSAL property of SHA-2 round function.
If Omega_3 = 0 for some classes → property specific to HW=2 structure.

Feature: for HW=2/HW=3, use bit5_max position; for random/counter,
use HW_parity of input.
"""
import json, math, os, random, subprocess, tempfile, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'omega3_full')
N_TARGET = 130816  # match HW=2 exhaustive size for fair comparison
STRIDE = 8  # ~345K triples per call, ~48s


def full_sha(inputs):
    N = len(inputs)
    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1,
                     ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    b2 = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    b2 = np.broadcast_to(b2, (N, 16))
    s2 = ch.compress(s1, b2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
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


def run_omega3(state1_bits, state2_bits, fa):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf: tp = tf.name
    try:
        N = len(fa)
        with open(tp, 'wb') as fp:
            fp.write(np.uint64(N).tobytes())
            for b in range(256): fp.write(pack(state1_bits[:, b]).tobytes())
            fp.write(pack(fa).tobytes())
            for b in range(256): fp.write(pack(state2_bits[:, b]).tobytes())
        res = subprocess.run([C_BIN, tp, str(STRIDE)], capture_output=True, text=True, check=True, timeout=100)
        d = json.loads(res.stdout)
        return d
    finally:
        os.unlink(tp)


def test_class(class_name, inputs, feature_arr):
    print(f"\n## {class_name} (N={len(inputs)})")
    s1, s2 = full_sha(inputs)
    s1b, s2b = sb(s1, len(inputs)), sb(s2, len(inputs))
    # r=0 test (state1 itself)
    ts = time.time()
    d_r0 = run_omega3(s1b, s1b, feature_arr)
    print(f"  r=0:  Ω_3={d_r0['omega3']:+.4f}  ss={d_r0['same_sign']}/256  t={time.time()-ts:.0f}s", flush=True)
    # r=64 test (full hash)
    ts = time.time()
    d_r64 = run_omega3(s1b, s2b, feature_arr)
    print(f"  r=64: Ω_3={d_r64['omega3']:+.4f}  ss={d_r64['same_sign']}/256  t={time.time()-ts:.0f}s", flush=True)
    return {'class': class_name, 'N': len(inputs),
            'r0': {'omega3': d_r0['omega3'], 'ss': d_r0['same_sign']},
            'r64': {'omega3': d_r64['omega3'], 'ss': d_r64['same_sign']}}


def main():
    t0 = time.time()
    print(f"# IT-23: Ω_3 universality across input classes")

    results = []

    # CLASS A: HW=2 exhaustive (baseline, should reproduce +0.9 at r=64)
    print("\n### Class A: HW=2 exhaustive (baseline)")
    inputs_hw2 = []
    positions_hw2 = []
    for p in combinations(range(512), 2):
        b = bytearray(64)
        for q in p: b[q >> 3] |= 1 << (q & 7)
        inputs_hw2.append(bytes(b)); positions_hw2.append(p)
    mp = np.asarray([p[-1] for p in positions_hw2])
    fa_hw2 = ((mp >> 5) & 1).astype(np.uint8)
    results.append(test_class("HW=2 exhaustive", inputs_hw2, fa_hw2))

    # CLASS B: HW=3 subsampled
    print("\n### Class B: HW=3 subsampled")
    rng = random.Random(0x1337)
    all_hw3 = list(combinations(range(512), 3))
    sample_idx = rng.sample(range(len(all_hw3)), N_TARGET)
    inputs_hw3 = []
    positions_hw3 = []
    for idx in sample_idx:
        pos = all_hw3[idx]
        b = bytearray(64)
        for q in pos: b[q >> 3] |= 1 << (q & 7)
        inputs_hw3.append(bytes(b)); positions_hw3.append(pos)
    mp3 = np.asarray([p[-1] for p in positions_hw3])
    fa_hw3 = ((mp3 >> 5) & 1).astype(np.uint8)
    results.append(test_class("HW=3 subsampled", inputs_hw3, fa_hw3))

    # CLASS C: counter (M = i)
    print("\n### Class C: counter")
    inputs_cnt = [(i).to_bytes(64, 'big') for i in range(N_TARGET)]
    # Feature: HW parity of input
    fa_cnt = np.array([bin(i).count('1') & 1 for i in range(N_TARGET)], dtype=np.uint8)
    results.append(test_class("counter", inputs_cnt, fa_cnt))

    # CLASS D: random uniform
    print("\n### Class D: random uniform 64-byte")
    rng2 = random.Random(0xDEADBEEF)
    inputs_rnd = [bytes(rng2.randint(0,255) for _ in range(64)) for _ in range(N_TARGET)]
    # Feature: HW parity of input
    fa_rnd = np.array([bin(int.from_bytes(m,'big')).count('1') & 1 for m in inputs_rnd], dtype=np.uint8)
    results.append(test_class("random uniform", inputs_rnd, fa_rnd))

    # Summary
    print("\n=== IT-23 SUMMARY ===")
    print(f"{'input class':<20} {'N':>8} {'Ω_3(r=0)':>12} {'ss_r0':>8} {'Ω_3(r=64)':>12} {'ss_r64':>8}")
    for r in results:
        print(f"{r['class']:<20} {r['N']:>8} {r['r0']['omega3']:>+12.4f} {r['r0']['ss']:>4}/256 "
              f"{r['r64']['omega3']:>+12.4f} {r['r64']['ss']:>4}/256")

    print("\n--- INTERPRETATION ---")
    print("If all classes give Ω_3 = +0.9 at both r=0 and r=64 → UNIVERSAL conservation")
    print("If random/counter gives Ω_3 = 0 → conservation specific to sparse inputs")
    print("Drop r=0 → r=64: measures how much signal survives 64 rounds of block 2")

    with open(os.path.join(HERE, 'it23_input_classes.json'), 'w') as f:
        json.dump({'results': results, 'meta': {'N': N_TARGET, 'stride': STRIDE}}, f, indent=2)
    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
