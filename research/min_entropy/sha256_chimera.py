"""
IT-2: SHA-256 chimera — vectorised reference + component-swappable variants.

Goal: identify which SHA-256 component is responsible for the χ² < RO
band fingerprint observed in IT-1.3 at k=12 on low-Hamming-weight inputs.

Strategy: implement SHA-256 in vectorised numpy uint32, with each
non-linear component pluggable via a flag. Run each variant on the
exhaustive low_hw_w2 input set and compare χ² at k=12 to the RO band
already established in cross_hash_k12_results.json.

Components considered:
    Σ0(a) = ROTR(a, 2) ⊕ ROTR(a,13) ⊕ ROTR(a,22)
    Σ1(e) = ROTR(e, 6) ⊕ ROTR(e,11) ⊕ ROTR(e,25)
    σ0(x) = ROTR(x, 7) ⊕ ROTR(x,18) ⊕ SHR(x, 3)
    σ1(x) = ROTR(x,17) ⊕ ROTR(x,19) ⊕ SHR(x,10)
    Ch(e,f,g) = (e ∧ f) ⊕ (¬e ∧ g)
    Maj(a,b,c) = (a ∧ b) ⊕ (a ∧ c) ⊕ (b ∧ c)
    K[0..63]   = ⌊2^32 · cube_root(prime_t)⌋
    IV[0..7]   = ⌊2^32 · sqrt(prime_t)⌋

Variants:
    V0  vanilla                                         (= hashlib.sha256)
    V1  Σ0,Σ1 → identity                                (kill big Sigma in compress)
    V2  σ0,σ1 → identity                                (kill little sigma in schedule)
    V3  V1 + V2                                          (no Σ, no σ)
    V4  K[t] := 0                                        (kill round constants)
    V5  Ch,Maj → linear XOR                              (kill non-linear bool fns)
    V6  V3 + V4                                          (linear schedule + linear compress)
    V7  V3 + V4 + V5                                     (almost-linear SHA-256)
    V8  K[t] := t · 0x9E3779B9   (golden ratio)          (replace K with simple structure)
    V9  IV := zeros                                      (kill IV constants)
"""

import hashlib
import math
import json
import os
import time
from itertools import combinations

import numpy as np


U32 = np.uint32
MASK = U32(0xFFFFFFFF)


# ---------------------------------------------------------------------------
# SHA-256 reference constants
# ---------------------------------------------------------------------------

K_VANILLA = np.array([
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
], dtype=U32)

IV_VANILLA = np.array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
], dtype=U32)


# ---------------------------------------------------------------------------
# Vectorised primitive ops on uint32 arrays of shape (N,)
# ---------------------------------------------------------------------------

def rotr(x, n):
    return ((x >> U32(n)) | (x << U32(32 - n))) & MASK


def shr(x, n):
    return (x >> U32(n)) & MASK


def Sigma0(a):     return rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
def Sigma1(e):     return rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
def sigma0(x):     return rotr(x, 7) ^ rotr(x, 18) ^ shr(x, 3)
def sigma1(x):     return rotr(x, 17) ^ rotr(x, 19) ^ shr(x, 10)
def Ch(e, f, g):   return ((e & f) ^ ((~e) & g)) & MASK
def Maj(a, b, c):  return ((a & b) ^ (a & c) ^ (b & c)) & MASK


def identity1(x):     return x
def linear3_xor(a, b, c):  return (a ^ b ^ c) & MASK


# ---------------------------------------------------------------------------
# Vectorised compress function: (state, message_block) → state
#   state: ndarray (N, 8) uint32
#   block: ndarray (N, 16) uint32
# `flags` selects which components are vanilla vs replaced.
# ---------------------------------------------------------------------------

def compress(state, block, flags, K):
    """Vectorised SHA-256 compress over N parallel inputs."""
    N = state.shape[0]

    sm0 = identity1 if flags['no_sigma_sched'] else sigma0
    sm1 = identity1 if flags['no_sigma_sched'] else sigma1
    Sg0 = identity1 if flags['no_Sigma_compr'] else Sigma0
    Sg1 = identity1 if flags['no_Sigma_compr'] else Sigma1
    chf = (lambda e, f, g: linear3_xor(e, f, g)) if flags['linear_chmaj'] else Ch
    maf = (lambda a, b, c: linear3_xor(a, b, c)) if flags['linear_chmaj'] else Maj

    # Message schedule: W[0..15] = block, W[16..63] = sm1 + W[t-7] + sm0 + W[t-16]
    W = np.empty((N, 64), dtype=U32)
    W[:, :16] = block
    for t in range(16, 64):
        W[:, t] = (sm1(W[:, t-2]) + W[:, t-7]
                   + sm0(W[:, t-15]) + W[:, t-16]) & MASK

    a, b, c, d, e, f, g, h = (state[:, i].copy() for i in range(8))

    for t in range(64):
        T1 = (h + Sg1(e) + chf(e, f, g) + U32(K[t]) + W[:, t]) & MASK
        T2 = (Sg0(a) + maf(a, b, c)) & MASK
        h = g
        g = f
        f = e
        e = (d + T1) & MASK
        d = c
        c = b
        b = a
        a = (T1 + T2) & MASK

    new_state = np.column_stack([a, b, c, d, e, f, g, h]).astype(U32)
    return (new_state + state) & MASK


def hash_messages(messages_bytes, flags, K=K_VANILLA, IV=IV_VANILLA):
    """
    Hash N messages, each EXACTLY 64 bytes long, using flagged SHA-256.
    Padding: 0x80 || zeros || 64-bit length (=512). One additional block.

    Returns ndarray (N, 8) uint32 of final state.
    """
    N = len(messages_bytes)
    # Block 1: messages (64 bytes each) → 16 uint32s, big-endian
    M_bytes = np.frombuffer(b''.join(messages_bytes), dtype=np.uint8).reshape(N, 64)
    block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)

    # Block 2: padding for 64-byte messages
    #   bit string: 0x80 || 55 zero bytes || (length=512 in 64-bit BE)
    pad = bytearray(64)
    pad[0] = 0x80
    # length in bits = 512, big-endian last 8 bytes
    pad[-8:] = (512).to_bytes(8, 'big')
    block2 = np.frombuffer(bytes(pad), dtype=np.uint8) \
        .view(dtype='>u4').reshape(1, 16).astype(U32)
    block2 = np.broadcast_to(block2, (N, 16))

    state = np.broadcast_to(IV, (N, 8)).copy()
    state = compress(state, block1, flags, K)
    state = compress(state, block2, flags, K)
    return state


def first_24bits(state):
    """Take first 24 bits of the SHA-256 output (high 24 bits of state[0])."""
    return (state[:, 0] >> U32(8)).astype(np.uint32)


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------

VARIANTS = {
    'V0_vanilla':           dict(no_sigma_sched=False, no_Sigma_compr=False, linear_chmaj=False),
    'V1_no_Sigma_compr':    dict(no_sigma_sched=False, no_Sigma_compr=True,  linear_chmaj=False),
    'V2_no_sigma_sched':    dict(no_sigma_sched=True,  no_Sigma_compr=False, linear_chmaj=False),
    'V3_no_both_diffusion': dict(no_sigma_sched=True,  no_Sigma_compr=True,  linear_chmaj=False),
    'V5_linear_chmaj':      dict(no_sigma_sched=False, no_Sigma_compr=False, linear_chmaj=True),
    'V7_almost_linear':     dict(no_sigma_sched=True,  no_Sigma_compr=True,  linear_chmaj=True),
}

# K-replacements:
K_ZERO   = np.zeros(64, dtype=U32)
K_GOLDEN = np.array([(t * 0x9E3779B9) & 0xFFFFFFFF for t in range(64)], dtype=U32)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def gen_low_hw2():
    L = 64
    out = []
    for positions in combinations(range(512), 2):
        b = bytearray(L)
        for p in positions:
            b[p >> 3] |= 1 << (p & 7)
        out.append(bytes(b))
    return out


def chi2_at_k(trunc24, k, N):
    shift = 24 - k
    buckets = trunc24 >> shift if shift > 0 else trunc24
    M = 1 << k
    counts = np.bincount(buckets, minlength=M)
    expected = N / M
    return float(((counts - expected) ** 2).sum() / expected)


def verify_against_hashlib(messages):
    """Sanity check: V0_vanilla on a few messages = hashlib.sha256."""
    state = hash_messages(messages[:5], VARIANTS['V0_vanilla'])
    for i, msg in enumerate(messages[:5]):
        ours = state[i].astype('>u4').tobytes()
        ref = hashlib.sha256(msg).digest()
        assert ours == ref, f"Mismatch at {i}: {ours.hex()} vs {ref.hex()}"
    print("# Vanilla matches hashlib.sha256 on 5 test inputs ✓")


def main():
    t_total = time.time()
    print("# IT-2: chimera attribution on low_hw_w2")
    inputs = gen_low_hw2()
    N = len(inputs)
    print(f"# N = {N}")

    verify_against_hashlib(inputs)

    # Load RO band from IT-1.3 cross_hash_k12_results.json
    ro_path = os.path.join(os.path.dirname(__file__), 'cross_hash_k12_results.json')
    with open(ro_path) as f:
        ro_band = json.load(f)['ro_band']
    print(f"# Loaded RO band from IT-1.3: k ∈ {sorted(int(k) for k in ro_band)}")

    K_LIST = [8, 9, 10, 11, 12, 13, 14, 15, 16]

    # ------------------------------------------------------------------
    # Test each variant × each K-replacement
    # ------------------------------------------------------------------
    EXPS = []
    for vname, vflags in VARIANTS.items():
        EXPS.append((vname, vflags, K_VANILLA, 'K_vanilla'))
    EXPS.append(('V0_vanilla',         VARIANTS['V0_vanilla'],         K_ZERO,   'K_zero'))
    EXPS.append(('V0_vanilla',         VARIANTS['V0_vanilla'],         K_GOLDEN, 'K_golden'))
    EXPS.append(('V7_almost_linear',   VARIANTS['V7_almost_linear'],   K_ZERO,   'K_zero'))

    results = {}
    print(f"\n{'name':<35} {'time':>6}  " + "  ".join(f"k={k:>2}" for k in K_LIST))
    print('-' * (45 + 7 * len(K_LIST)))
    for vname, vflags, Karr, klabel in EXPS:
        label = f"{vname} | {klabel}"
        t0 = time.time()
        state = hash_messages(inputs, vflags, K=Karr)
        trunc = first_24bits(state)
        elapsed = time.time() - t0
        chi2_per_k = {}
        z_per_k = {}
        for k in K_LIST:
            v = chi2_at_k(trunc, k, N)
            chi2_per_k[k] = v
            ro = ro_band[str(k)]
            z = (v - ro['mean']) / ro['std']
            z_per_k[k] = z
        results[label] = {'chi2': chi2_per_k, 'z': z_per_k, 'time': elapsed}
        zrow = "  ".join(f"{z_per_k[k]:+5.2f}" for k in K_LIST)
        print(f"{label:<35} {elapsed:>5.1f}s  {zrow}")

    out = {
        'meta': {'N': N, 'k_list': K_LIST},
        'ro_band': ro_band,
        'variants': results,
    }
    out_path = os.path.join(os.path.dirname(__file__), 'chimera_results.json')
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)

    print(f"\nWrote {out_path}")
    print(f"Total time: {time.time() - t_total:.1f}s")


if __name__ == '__main__':
    main()
