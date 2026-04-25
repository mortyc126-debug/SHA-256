"""
Session 65: Joint compression of (input, output) pairs.

INDIRECT TEST: gzip is a generic compression oracle. For pairs (m, SHA(m)):
  - If they're "independent" (random function): joint size ~ 2 × input.
  - If correlated (structured): joint size < 2 × input.

Subtle indirect test for hidden joint structure.

Compare:
1. gzip(concat(m_1, ..., m_N)) — pure inputs
2. gzip(concat(H(m_1), ..., H(m_N))) — pure outputs
3. gzip(concat(m_1, H(m_1), m_2, H(m_2), ...)) — interleaved pairs
4. gzip(concat(m_1, ..., m_N, H(m_1), ..., H(m_N))) — separated

If joint compression < pure compression, structure exists.
For random oracle: should be SAME (no structure).
"""
import hashlib
import gzip
import numpy as np


def main():
    print("=== Session 65: Joint compression of (input, SHA(input)) pairs ===\n")
    rng = np.random.default_rng(0)
    N = 1000  # number of input messages

    print(f"  Generating {N} 32-byte random messages and their SHA-256 digests.\n")
    messages = []
    digests = []
    for _ in range(N):
        msg = bytes(rng.integers(0, 256, size=32, dtype=np.uint8))
        digest = hashlib.sha256(msg).digest()
        messages.append(msg)
        digests.append(digest)

    # Concat each
    M_concat = b''.join(messages)  # 32K bytes
    D_concat = b''.join(digests)   # 32K bytes
    Pair_interleaved = b''.join(m + d for m, d in zip(messages, digests))
    Pair_separated = M_concat + D_concat

    # Random control
    R_concat = bytes(rng.integers(0, 256, size=len(M_concat), dtype=np.uint8))
    R_pair_interleaved = bytes(rng.integers(0, 256, size=len(Pair_interleaved), dtype=np.uint8))

    print(f"  {'Configuration':<40}  {'size':>7}  {'gzip':>7}  {'ratio':>8}")
    print(f"  {'-'*65}")

    def report(label, data):
        c = gzip.compress(data, compresslevel=9)
        ratio = len(c) / len(data)
        print(f"  {label:<40}  {len(data):>7}  {len(c):>7}  {ratio:>8.4f}")
        return ratio

    r_M = report("M (1000 random messages)", M_concat)
    r_D = report("D (1000 SHA digests)", D_concat)
    r_pair_int = report("Pairs interleaved [m_i || d_i]_i", Pair_interleaved)
    r_pair_sep = report("Pairs separated [M || D]", Pair_separated)
    r_random = report("Random control (same size)", R_concat)
    r_random_pair = report("Random control (pair size)", R_pair_interleaved)

    print(f"\n  Compression ratio analysis:")
    print(f"    Pairs interleaved ratio: {r_pair_int:.4f}")
    print(f"    Pairs separated ratio: {r_pair_sep:.4f}")
    print(f"    Expected if (m, H(m)) independent: ~ avg(r_M, r_D) = {(r_M + r_D)/2:.4f}")
    print(f"    Random control: {r_random_pair:.4f}")

    deviation_int = r_pair_int - (r_M + r_D) / 2
    deviation_sep = r_pair_sep - (r_M + r_D) / 2

    print(f"\n  Deviation from independence:")
    print(f"    Interleaved: {deviation_int:+.4f}")
    print(f"    Separated: {deviation_sep:+.4f}")

    if abs(deviation_int) > 0.01 or abs(deviation_sep) > 0.01:
        print(f"  ⚠ NON-TRIVIAL deviation — possible joint structure!")
    else:
        print(f"  ✓ Pairs compress as if independent — no exploitable joint structure.")

    print("""

=== Theorem 65.1 (joint compression, empirical) ===

If gzip(pairs) compression ratio matches gzip(M) and gzip(D) average:
  → (m, H(m)) pairs are statistically independent, no joint correlation
    detectable by general compression.

If significant deviation:
  → SHA introduces correlated structure that gzip exploits, indicating
    SHA is detectably non-random as a function.

This indirect test does NOT directly attack SHA but probes for "input-output
joint structure" that any compression-based attack might exploit.
""")


if __name__ == "__main__":
    main()
