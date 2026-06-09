"""
Independent, from-scratch SHA-256 compression function with round-level
instrumentation, written to re-verify Volume II claims that have no code
on disk.  Nothing here imports the (non-existent) qt_solver package.

Conventions follow FIPS 180-4.  We expose intermediate (a..h) and the e/a
registers per round so differential claims can be checked directly.
"""

MASK = 0xFFFFFFFF

K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

IV = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]


def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & MASK


def shr(x, n):
    return (x >> n) & MASK


def Sig0(x):  # big sigma 0 (compression)
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)


def Sig1(x):  # big sigma 1 (compression)
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)


def sig0(x):  # small sigma 0 (schedule)
    return rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3)


def sig1(x):  # small sigma 1 (schedule)
    return rotr(x, 17) ^ rotr(x, 19) ^ shr(x, 10)


def Ch(e, f, g):
    return (e & f) ^ ((~e & MASK) & g)


def Maj(a, b, c):
    return (a & b) ^ (a & c) ^ (b & c)


def expand_schedule(W16):
    """Expand 16 message words to 64 via the SHA-256 schedule recurrence."""
    W = list(W16) + [0] * 48
    for t in range(16, 64):
        W[t] = (sig1(W[t - 2]) + W[t - 7] + sig0(W[t - 15]) + W[t - 16]) & MASK
    return W


def compress_trace(W64, iv=IV, rounds=64):
    """
    Run the compression function over an already-expanded 64-word schedule.
    Returns a list 'states' of length rounds+1 where states[r] = (a..h)
    BEFORE round r is applied (states[0] = iv).  This lets us read e_r = states[r][4].
    """
    a, b, c, d, e, f, g, h = iv
    states = [(a, b, c, d, e, f, g, h)]
    for r in range(rounds):
        T1 = (h + Sig1(e) + Ch(e, f, g) + K[r] + W64[r]) & MASK
        T2 = (Sig0(a) + Maj(a, b, c)) & MASK
        h = g
        g = f
        f = e
        e = (d + T1) & MASK
        d = c
        c = b
        b = a
        a = (T1 + T2) & MASK
        states.append((a, b, c, d, e, f, g, h))
    return states


def e_sequence(W64, iv=IV, rounds=64):
    """e_r for r = 0..rounds (e_0 = iv[4])."""
    return [s[4] for s in compress_trace(W64, iv, rounds)]


def sha256_digest_words(W16, iv=IV):
    """Final 8 output words (single block) for sanity vs hashlib."""
    W = expand_schedule(W16)
    st = compress_trace(W, iv, 64)[-1]
    return [(iv[i] + st[i]) & MASK for i in range(8)]


# ---- self-check against the Vol II proof_audit constants -------------------

def _check_constants():
    a_iv, b_iv, c_iv, d_iv, e_iv, f_iv, g_iv, h_iv = IV
    T1_0_base = (h_iv + Sig1(e_iv) + Ch(e_iv, f_iv, g_iv) + K[0]) & MASK  # C_IV
    T2_0 = (Sig0(a_iv) + Maj(a_iv, b_iv, c_iv)) & MASK
    BASE_A1 = (T1_0_base + T2_0) & MASK
    CONST_e1 = (d_iv + T1_0_base) & MASK
    checks = {
        "C_IV (=T1_0_base)": (T1_0_base, 0xf377ed68),
        "T2_0":              (T2_0,      0x08909ae5),
        "BASE_A1 (S_base)":  (BASE_A1,   0xfc08884d),
        "CONST_e1":          (CONST_e1,  0x98c7e2a2),
        "Sig1(0x8000)":      (Sig1(0x8000), 0x00400210),
        "Sig0(0x8000)":      (Sig0(0x8000), 0x02002004),
    }
    ok = True
    for name, (got, want) in checks.items():
        status = "OK" if got == want else "MISMATCH"
        if got != want:
            ok = False
        print(f"  {name:20s} = 0x{got:08x}  expected 0x{want:08x}  [{status}]")
    return ok


if __name__ == "__main__":
    import hashlib

    print("== SHA-256 sanity vs hashlib (empty message) ==")
    # empty message: one padded block
    block = bytearray(64)
    block[0] = 0x80  # single 1 bit then zeros; length 0
    W16 = [int.from_bytes(block[4 * i:4 * i + 4], "big") for i in range(16)]
    digest = b"".join(w.to_bytes(4, "big") for w in sha256_digest_words(W16))
    ref = hashlib.sha256(b"").digest()
    print("  ours:", digest.hex())
    print("  ref :", ref.hex())
    print("  MATCH" if digest == ref else "  MISMATCH")

    print("\n== Vol II base constants (vs 11_proof_audit.md) ==")
    allok = _check_constants()
    print("  ALL CONSTANTS OK" if allok else "  SOME MISMATCH")
