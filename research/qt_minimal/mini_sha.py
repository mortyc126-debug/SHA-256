"""
Mini-SHA: parametric SHA-like compression with tunable word size and rounds.

Purpose: test ground for Q∩T solver experiments.
Structure mirrors SHA-256 proportionally:
  - 8 registers (a..h)
  - Each register = n-bit word (n configurable: 4, 8, 12, 16)
  - ADD modulo 2^n (introduces carry → T-constraints)
  - Ch/Maj bitwise (introduces Q-quadratic-GF(2) constraints)
  - Σ0/Σ1 as XOR of rotations (pure linear GF(2))
  - K[r] constants (derived from sqrt/cbrt of primes, scaled to n bits)

Preimage problem: given (H_0, h) find W[0..r-1] s.t. compress(H_0, W) = h.
Collision problem: find W ≠ W' with compress(H_0, W) = compress(H_0, W').
"""

import hashlib

def rotr(x, r, n):
    mask = (1 << n) - 1
    return ((x >> r) | (x << (n - r))) & mask

def shr(x, r, n):
    mask = (1 << n) - 1
    return (x >> r) & mask

# Rotation amounts scaled from SHA-256 (2,13,22; 6,11,25; 7,18,3; 17,19,10)
# For n=4: {1,2,3}; n=8: {1,3,5} or {2,3,5}; n≥16: scale proportionally
def sigma_params(n):
    """Return (Sig0_rots, Sig1_rots, sig0_rots_shr, sig1_rots_shr)
       where Sig* use 3 rotations, sig* use 2 rotations + 1 shift."""
    if n == 4:
        # tiny: pick odd-spread rotations
        return ((1, 2, 3), (1, 2, 3), (1, 2, 1), (1, 2, 1))
    elif n == 8:
        return ((1, 3, 5), (2, 4, 6), (1, 3, 2), (2, 4, 3))
    elif n == 12:
        return ((1, 5, 8), (3, 6, 9), (1, 5, 2), (3, 6, 4))
    elif n == 16:
        return ((1, 7, 11), (3, 6, 13), (1, 7, 2), (3, 6, 5))
    elif n == 20:
        return ((2, 8, 13), (4, 9, 15), (2, 8, 3), (4, 9, 5))
    elif n == 24:
        return ((2, 9, 16), (5, 11, 18), (2, 9, 3), (5, 11, 6))
    elif n == 28:
        return ((2, 11, 19), (5, 13, 22), (2, 11, 3), (5, 13, 7))
    elif n == 32:
        # Same as real SHA-256
        return ((2, 13, 22), (6, 11, 25), (7, 18, 3), (17, 19, 10))
    else:
        raise ValueError(f"unsupported n={n}")

def Sig0(x, n):
    r1, r2, r3 = sigma_params(n)[0]
    return rotr(x, r1, n) ^ rotr(x, r2, n) ^ rotr(x, r3, n)

def Sig1(x, n):
    r1, r2, r3 = sigma_params(n)[1]
    return rotr(x, r1, n) ^ rotr(x, r2, n) ^ rotr(x, r3, n)

def sig0_msg(x, n):
    r1, r2, s = sigma_params(n)[2]
    return rotr(x, r1, n) ^ rotr(x, r2, n) ^ shr(x, s, n)

def sig1_msg(x, n):
    r1, r2, s = sigma_params(n)[3]
    return rotr(x, r1, n) ^ rotr(x, r2, n) ^ shr(x, s, n)

def Ch(e, f, g, n):
    mask = (1 << n) - 1
    return ((e & f) ^ ((~e) & g)) & mask

def Maj(a, b, c, n):
    mask = (1 << n) - 1
    return ((a & b) ^ (a & c) ^ (b & c)) & mask

def gen_K(n, num_rounds):
    """Generate K[r] constants via SHA-256 seeded at round index, truncated to n bits."""
    mask = (1 << n) - 1
    K = []
    for r in range(num_rounds):
        h = hashlib.sha256(f"K_{n}_{r}".encode()).digest()
        k = int.from_bytes(h[:4], 'big') & mask
        K.append(k)
    return K

def gen_IV(n):
    """IV derived from sqrt of first 8 primes, scaled to n bits."""
    mask = (1 << n) - 1
    IV = []
    primes = [2, 3, 5, 7, 11, 13, 17, 19]
    for p in primes:
        h = hashlib.sha256(f"IV_{n}_{p}".encode()).digest()
        iv = int.from_bytes(h[:4], 'big') & mask
        IV.append(iv)
    return IV

def expand_schedule(W_in, num_rounds, n, M=16):
    """W[0..M-1] = W_in (M input words).  W[r] for r≥M = σ1(W[r-2]) + W[r-7] + σ0(W[r-15]) + W[r-16]."""
    mask = (1 << n) - 1
    assert len(W_in) == M
    W = list(W_in)
    for r in range(M, num_rounds):
        new_w = (sig1_msg(W[r-2], n) + W[r-7] + sig0_msg(W[r-15], n) + W[r-16]) & mask
        W.append(new_w)
    return W

def compress(H0, W_in, num_rounds, n, M=16):
    """Full mini-SHA compression.  Returns new H vector."""
    mask = (1 << n) - 1
    K = gen_K(n, num_rounds)
    W = expand_schedule(W_in, num_rounds, n, M) if num_rounds > M else list(W_in[:num_rounds])

    a, b, c, d, e, f, g, h = H0
    for r in range(num_rounds):
        T1 = (h + Sig1(e, n) + Ch(e, f, g, n) + K[r] + W[r]) & mask
        T2 = (Sig0(a, n) + Maj(a, b, c, n)) & mask
        h = g
        g = f
        f = e
        e = (d + T1) & mask
        d = c
        c = b
        b = a
        a = (T1 + T2) & mask

    return [(H0[i] + [a,b,c,d,e,f,g,h][i]) & mask for i in range(8)]


def single_round(state, W_r, K_r, n):
    """One round, state=(a,b,c,d,e,f,g,h). Returns new state."""
    mask = (1 << n) - 1
    a, b, c, d, e, f, g, h = state
    T1 = (h + Sig1(e, n) + Ch(e, f, g, n) + K_r + W_r) & mask
    T2 = (Sig0(a, n) + Maj(a, b, c, n)) & mask
    return ((T1 + T2) & mask, a, b, c, (d + T1) & mask, e, f, g)


if __name__ == "__main__":
    # Smoke test
    for n in [4, 8]:
        H0 = gen_IV(n)
        W = [i for i in range(16)]  # trivial input
        for R in [2, 4, 8, 16]:
            Rn = min(R, len(W))
            h = compress(H0, W[:16], Rn, n, M=16) if R >= 16 else [0]*8
            if R < 16:
                # Use only R words, skip schedule expansion
                mask = (1 << n) - 1
                K = gen_K(n, R)
                a,b,c,d,e,f,g,hh = H0
                state = (a,b,c,d,e,f,g,hh)
                for r in range(R):
                    state = single_round(state, W[r], K[r], n)
                h = [(H0[i] + state[i]) & mask for i in range(8)]
            print(f"n={n:2d} R={R:2d}  H={[hex(x) for x in h]}")
