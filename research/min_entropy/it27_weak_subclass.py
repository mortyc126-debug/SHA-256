"""IT-27: Search for weak message subclass — partitions where Omega_3 breaks.

All input classes tested in IT-23 gave Omega_3 ≈ +0.85. What if a NARROWER
subclass gives different Omega_3? That subclass would be a 'weak message
class' — exploitable structure for attack construction.

Partitions of HW=2 exhaustive (N=130816 → ~65K per half):

P1: position of larger bit — top 256 vs bottom 256
P2: distance between bits — close (<64) vs far (>=64)
P3: both bits in same byte vs different bytes
P4: positions parity (i+j) mod 2 — even sum vs odd sum
P5: high bit XOR low bit value — does the XOR pattern matter?
P6: position-mod-7 — both ≡ 0 mod 7 vs not

For each partition: measure Omega_3 on each half, compare to baseline +0.85.
Significant gap → weak class identified.

Cost: ~6 partitions × 2 halves × ~50s = 10 min budget. Use stride=8.
"""
import json, math, os, subprocess, tempfile, time
from itertools import combinations
import numpy as np
import sha256_chimera as ch

WORDS = 2048
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'omega3_full')
STRIDE = 8


def low_hw2():
    inputs, pos = [], []
    for p in combinations(range(512), 2):
        b = bytearray(64)
        for q in p: b[q >> 3] |= 1 << (q & 7)
        inputs.append(bytes(b)); pos.append(p)
    return inputs, pos


def sb(s, N):
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w*32+b] = ((s[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits


def pack(v, target_bits=WORDS*64):
    pd = np.zeros(target_bits, dtype=np.uint8); pd[:len(v)] = v
    return np.frombuffer(np.packbits(pd, bitorder='little').tobytes(), dtype=np.uint64)


def measure_omega3(state1_bits, state2_bits, fa, label):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as tf: tp = tf.name
    try:
        N = len(fa)
        with open(tp, 'wb') as fp:
            fp.write(np.uint64(N).tobytes())
            for b in range(256): fp.write(pack(state1_bits[:, b]).tobytes())
            fp.write(pack(fa).tobytes())
            for b in range(256): fp.write(pack(state2_bits[:, b]).tobytes())
        ts = time.time()
        res = subprocess.run([C_BIN, tp, str(STRIDE)], capture_output=True, text=True, check=True, timeout=120)
        dt = time.time() - ts
        d = json.loads(res.stdout)
        print(f"  [{label}] N={N} Ω_3={d['omega3']:+.4f} ss={d['same_sign']}/256 t={dt:.0f}s", flush=True)
        return d
    finally:
        os.unlink(tp)


def main():
    t0 = time.time()
    print("# IT-27: Weak message subclass search via Omega_3 partitions")
    inputs, pos = low_hw2(); N = len(inputs)

    # Compute full SHA for all
    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N, 64)
    b1 = M.view('>u4').reshape(N, 16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
    b2 = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
    b2 = np.broadcast_to(b2, (N, 16))
    s2 = ch.compress(s1, b2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    s1b = sb(s1, N)
    s2b = sb(s2, N)

    mp = np.array([p[-1] for p in pos], dtype=np.int64)
    ip = np.array([p[0] for p in pos], dtype=np.int64)
    fa_full = ((mp >> 5) & 1).astype(np.uint8)

    # Define partitions (each returns boolean array of length N)
    partitions = [
        ('P1a: max_pos < 256', mp < 256),
        ('P1b: max_pos >= 256', mp >= 256),
        ('P2a: distance < 64', (mp - ip) < 64),
        ('P2b: distance >= 64', (mp - ip) >= 64),
        ('P3a: same byte', (mp >> 3) == (ip >> 3)),
        ('P3b: diff byte', (mp >> 3) != (ip >> 3)),
        ('P4a: parity sum even', ((mp + ip) & 1) == 0),
        ('P4b: parity sum odd', ((mp + ip) & 1) == 1),
        ('P5a: max_pos & 1 = 0', (mp & 1) == 0),
        ('P5b: max_pos & 1 = 1', (mp & 1) == 1),
    ]

    results = []
    for label, mask in partitions:
        idx = np.where(mask)[0]
        if len(idx) < 5000:
            print(f"  [{label}] SKIP (too small: N={len(idx)})")
            continue
        # Truncate to power-of-2-ish for stable C binary
        keep = min(len(idx), 130816)  # cap at full size
        idx_keep = idx[:keep]
        s1_sub = s1b[idx_keep]
        s2_sub = s2b[idx_keep]
        fa_sub = fa_full[idx_keep]
        d = measure_omega3(s1_sub, s2_sub, fa_sub, label)
        results.append({'label': label, 'N': len(idx_keep),
                        'omega3': d['omega3'], 'ss': d['same_sign']})

    print("\n=== IT-27 SUMMARY ===")
    print(f"{'partition':<30} {'N':>8} {'Ω_3':>10} {'ss':>10}")
    for r in results:
        print(f"{r['label']:<30} {r['N']:>8} {r['omega3']:>+10.4f} {r['ss']:>4}/256")

    # Look for biggest deviation from baseline +0.85 (full HW=2 measured earlier)
    baseline = 0.85
    print(f"\nBaseline (full HW=2): Ω_3 ≈ +{baseline}")
    devs = [(r['label'], r['omega3'] - baseline, r) for r in results]
    devs.sort(key=lambda x: abs(x[1]), reverse=True)
    print(f"\nTop 5 deviations from baseline:")
    for lbl, dev, r in devs[:5]:
        print(f"  {lbl:<30} Ω_3={r['omega3']:+.4f}  dev={dev:+.4f}")

    # Look for opposing pairs (P_a vs P_b)
    print(f"\nOpposing pair gaps (a vs b):")
    by_label = {r['label']: r for r in results}
    for prefix in ['P1', 'P2', 'P3', 'P4', 'P5']:
        a = by_label.get(f'{prefix}a: ' + next((r['label'] for r in results if r['label'].startswith(f'{prefix}a:')), '').split(':')[1].strip(), None)
        # simpler:
        a = next((r for r in results if r['label'].startswith(f'{prefix}a:')), None)
        b = next((r for r in results if r['label'].startswith(f'{prefix}b:')), None)
        if a and b:
            gap = a['omega3'] - b['omega3']
            print(f"  {prefix}: a={a['omega3']:+.4f}  b={b['omega3']:+.4f}  gap={gap:+.4f}")

    print("\n--- INTERPRETATION ---")
    print("If any partition gives Ω_3 << +0.85 → that subclass is 'structure-breaking'")
    print("If any opposing pair has gap > 0.2 → split class → discriminator found")
    print("If all stay near +0.85 → conservation is uniform, no exploitable subclass")

    with open(os.path.join(HERE, 'it27_weak_subclass.json'), 'w') as f:
        json.dump({'baseline': baseline, 'results': results}, f, indent=2)
    print(f"\nTotal: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
