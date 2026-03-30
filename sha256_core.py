"""SHA-256 core internals for cryptanalysis experiments."""

import struct

MASK = 0xFFFFFFFF

# SHA-256 round constants
K = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

# Initial hash values
IV = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
]

def rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & MASK

def shr(x, n):
    return x >> n

def sigma0(x):
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)

def sigma1(x):
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)

def sig0(x):
    return rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3)

def sig1(x):
    return rotr(x, 17) ^ rotr(x, 19) ^ shr(x, 10)

def ch(e, f, g):
    return (e & f) ^ (~e & g) & MASK

def maj(a, b, c):
    return (a & b) ^ (a & c) ^ (b & c)

def schedule(W16):
    """Expand 16 message words to 64."""
    W = list(W16) + [0] * 48
    for t in range(16, 64):
        W[t] = (sig1(W[t-2]) + W[t-7] + sig0(W[t-15]) + W[t-16]) & MASK
    return W

def sha256_round(state, W_r, K_r):
    """Single SHA-256 round. Returns new state [a,b,c,d,e,f,g,h]."""
    a, b, c, d, e, f, g, h = state
    T1 = (h + sigma1(e) + ch(e, f, g) + K_r + W_r) & MASK
    T2 = (sigma0(a) + maj(a, b, c)) & MASK
    return [
        (T1 + T2) & MASK,  # a
        a,                   # b
        b,                   # c
        c,                   # d
        (d + T1) & MASK,    # e
        e,                   # f
        f,                   # g
        g,                   # h
    ]

def sha256_rounds(W16, num_rounds=64, iv=None):
    """Run SHA-256 for num_rounds rounds. Returns list of all states [state_0, ..., state_r]."""
    if iv is None:
        iv = list(IV)
    W = schedule(W16)
    states = [list(iv)]
    state = list(iv)
    for r in range(min(num_rounds, 64)):
        state = sha256_round(state, W[r], K[r])
        states.append(list(state))
    return states

def sha256_compress(W16, iv=None):
    """Full SHA-256 compression. Returns 8-word hash."""
    if iv is None:
        iv = list(IV)
    states = sha256_rounds(W16, 64, iv)
    final = states[-1]
    return [(iv[i] + final[i]) & MASK for i in range(8)]

def de(states_n, states_f, r):
    """Compute De_r = e_r(faulty) - e_r(normal) mod 2^32."""
    return (states_f[r][4] - states_n[r][4]) & MASK

def da(states_n, states_f, r):
    """Compute Da_r = a_r(faulty) - a_r(normal) mod 2^32."""
    return (states_f[r][0] - states_n[r][0]) & MASK

def hw(x):
    """Hamming weight of 32-bit integer."""
    return bin(x & MASK).count('1')

def xor_diff_state(s1, s2):
    """XOR difference of two 8-word states."""
    return [s1[i] ^ s2[i] for i in range(8)]

def hw_state(diff):
    """Total Hamming weight of state difference."""
    return sum(hw(d) for d in diff)

def random_w16():
    """Generate random 16-word message block."""
    import random
    return [random.randint(0, MASK) for _ in range(16)]

def wang_cascade(W0, W1, DW0=1):
    """Wang cascade: produce DWs such that De3..De16=0.
    Returns (Wn, Wf, DWs, states_n, states_f)."""
    Wn = [W0, W1] + [0] * 14
    DWs = [0] * 16
    DWs[0] = DW0

    # Step 0: DW2 freedom -> De3=0
    Wf_tmp = [(Wn[i] + DWs[i]) & MASK for i in range(16)]
    sn = sha256_rounds(Wn, 3)
    sf = sha256_rounds(Wf_tmp, 3)
    De3_nat = de(sn, sf, 3)
    DWs[2] = (-De3_nat) & MASK

    # Steps 1..13: cascade De4..De16=0
    for step in range(13):
        wi = step + 3
        dt = step + 4
        Wfc = [(Wn[i] + DWs[i]) & MASK for i in range(16)]
        tn = sha256_rounds(Wn, dt)
        tf = sha256_rounds(Wfc, dt)
        DWs[wi] = (-de(tn, tf, dt)) & MASK

    Wf = [(Wn[i] + DWs[i]) & MASK for i in range(16)]
    states_n = sha256_rounds(Wn, 64)
    states_f = sha256_rounds(Wf, 64)

    return Wn, Wf, DWs, states_n, states_f

def carry(a, b):
    """Carry operator: C(a,b) = (a+b - a^b) / 2"""
    return (((a + b) & MASK) ^ (a ^ b)) >> 1

def carry_gkp_classification(a, b, n=32):
    """Classify each bit position as G(generate), K(kill), P(propagate).
    G: a_i=1, b_i=1; K: a_i=0, b_i=0; P: a_i ≠ b_i."""
    classes = []
    for i in range(n):
        ai = (a >> i) & 1
        bi = (b >> i) & 1
        if ai == 1 and bi == 1:
            classes.append('G')
        elif ai == 0 and bi == 0:
            classes.append('K')
        else:
            classes.append('P')
    return classes

def raw_T1(state, W_r, K_r):
    """Raw T1 value (before mod 2^32 reduction)."""
    a, b, c, d, e, f, g, h = state
    return h + sigma1(e) + ch(e, f, g) + K_r + W_r
