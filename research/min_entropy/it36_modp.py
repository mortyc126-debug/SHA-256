"""IT-36 (new math trick): Is SHA-256 output uniform modulo various primes p ≠ 2?

Classical SHA analysis = uniform in GF(2)^256 and Z/2^32.
Nobody systematically tests uniformity in Z/p for odd primes p.

Hypothesis: SHA-256 may be non-uniform in some Z/p that XOR-based probes
cannot detect. This would be a genuinely new structural bias.

Tests:
1. Compute hash H as 256-bit integer for N random messages
2. For each prime p in {3, 5, 7, 11, ..., some range}:
   - Compute H mod p for each hash
   - Chi² test vs uniform on Z_p
3. Also test quadratic residue bias: how many H are QR mod p?
4. Also test Legendre symbol (H|p) distribution

If ANY prime p gives chi² significantly different from RO null →
new SHA-256 bias in non-binary algebra.
"""
import hashlib, math, os, json, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
N = 200_000   # number of hashes

def is_prime(n):
    if n < 2: return False
    if n < 4: return True
    if n % 2 == 0: return False
    for i in range(3, int(math.isqrt(n))+1, 2):
        if n % i == 0: return False
    return True

# Small odd primes
SMALL_PRIMES = [p for p in range(3, 300) if is_prime(p)]
print(f"# Small primes to test: {len(SMALL_PRIMES)} (3 to {SMALL_PRIMES[-1]})")

# Large primes (Mersenne-like, near 2^k for k=5..20)
LARGE_PRIMES = []
for k in [5, 7, 11, 13, 17, 19, 23, 31]:
    p = 2**k - 1
    if is_prime(p): LARGE_PRIMES.append(p)
    else:
        # find next prime
        p = 2**k + 1
        while not is_prime(p): p += 2
        LARGE_PRIMES.append(p)
print(f"# Large primes to test: {LARGE_PRIMES}")

def main():
    t0 = time.time()
    print(f"\n# Generating {N} random SHA-256 hashes...")
    rng = np.random.default_rng(0xABCD1234)
    msgs = rng.integers(0, 256, size=(N, 64), dtype=np.uint8)
    # Compute hashes as Python ints
    print(f"# Computing hashes...")
    ts = time.time()
    H_list = []
    for i in range(N):
        d = hashlib.sha256(bytes(msgs[i])).digest()
        H = int.from_bytes(d, 'big')
        H_list.append(H)
    print(f"  time: {time.time()-ts:.0f}s")
    H_arr = np.array(H_list, dtype=object)  # Python int array

    # Chi² test for H mod p uniformity
    print(f"\n=== Chi² uniformity: H mod p ===")
    print(f"{'p':>6} {'chi2':>10} {'df':>4} {'z':>8} {'max_bin':>10} {'min_bin':>8}")
    chi2_results = {}
    for p in SMALL_PRIMES + LARGE_PRIMES:
        # compute H mod p using vectorized Python int
        mods = np.array([int(h % p) for h in H_list], dtype=np.int64)
        counts = np.bincount(mods, minlength=p)
        expected = N / p
        # chi² test
        chi2 = float(((counts - expected)**2 / expected).sum())
        df = p - 1
        z = (chi2 - df) / math.sqrt(2 * df)
        chi2_results[p] = {'chi2': chi2, 'df': df, 'z': z,
                           'max_bin': int(counts.max()), 'min_bin': int(counts.min())}
        marker = ' ★' if abs(z) > 4 else (' ⚠' if abs(z) > 3 else '  ')
        print(f"{marker} {p:>4} {chi2:>10.2f} {df:>4} {z:>+8.2f} {counts.max():>10} {counts.min():>8}")

    # Legendre symbol (H | p) distribution — for each prime,
    # what fraction of H are QR mod p vs NR mod p?
    # Under RO: 50% QR, 50% NR. If biased → structural signature.
    print(f"\n=== Legendre symbol bias (H|p) ===")
    print(f"Primes where bias |Δ| > 0.003:")
    leg_results = {}
    for p in SMALL_PRIMES[:40]:  # first 40 odd primes (up to 173)
        if p == 2: continue
        # compute Legendre via Euler's criterion: H^((p-1)/2) mod p
        half = (p - 1) // 2
        symbols = []
        for h in H_list[:min(N, 100000)]:  # sample up to 100K for speed
            r = pow(h, half, p)
            if r == 0: symbols.append(0)
            elif r == 1: symbols.append(1)
            else: symbols.append(-1)
        syms = np.array(symbols)
        qr = (syms == 1).sum()
        nr = (syms == -1).sum()
        zero = (syms == 0).sum()
        total = qr + nr
        if total == 0: continue
        phi = qr / total - 0.5
        z = phi / (0.5 / math.sqrt(total)) if total > 10 else 0
        leg_results[p] = {'qr': int(qr), 'nr': int(nr), 'zero': int(zero),
                          'phi': phi, 'z': z}
        if abs(phi) > 0.003:
            print(f"  p={p}: QR = {qr}, NR = {nr}, zero = {zero}, phi = {phi:+.5f}, z = {z:+.2f}")

    # Also test: HW of H mod p ≡ 0 bits of (H mod p)
    # And test: is H mod p biased in specific residue classes?
    print(f"\n=== Top chi² primes (structural bias search) ===")
    sorted_primes = sorted(chi2_results.items(), key=lambda kv: -abs(kv[1]['z']))
    for p, r in sorted_primes[:10]:
        print(f"  p={p:>4}: chi² = {r['chi2']:.2f}, df = {r['df']}, z = {r['z']:+.2f}")

    # Aggregated findings
    n_significant = sum(1 for r in chi2_results.values() if abs(r['z']) > 3)
    n_very_sig = sum(1 for r in chi2_results.values() if abs(r['z']) > 5)
    total_tests = len(chi2_results)
    print(f"\n=== SUMMARY ===")
    print(f"Total primes tested: {total_tests}")
    print(f"Significant (|z|>3, raw): {n_significant}")
    print(f"Very significant (|z|>5, raw): {n_very_sig}")
    print(f"Expected under H0 (multiple testing): ~{total_tests * 0.0027:.1f} at |z|>3")
    print(f"Bonferroni threshold for {total_tests} tests: |z| > {3.0 + math.sqrt(2*math.log(total_tests)):.2f}")

    if n_very_sig > 1:
        print("\n★ STRUCTURAL MOD-P BIAS FOUND — investigate further!")
    elif n_significant > 2*total_tests*0.003:
        print("\n⚠ Possible bias signal — verify with larger N")
    else:
        print("\n✓ No mod-p bias detected — consistent with RO")

    out = {'N': N, 'chi2_results': {str(p): r for p, r in chi2_results.items()},
           'legendre_results': {str(p): r for p, r in leg_results.items()},
           'total_primes_tested': total_tests,
           'n_significant_z3': n_significant,
           'n_very_significant_z5': n_very_sig}
    with open(os.path.join(HERE, 'it36_modp.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
