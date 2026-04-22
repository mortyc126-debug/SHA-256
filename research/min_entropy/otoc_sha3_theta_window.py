"""SHA-3 (Keccak) θ-step cascade analysis.

Keccak round = θ ∘ ρ ∘ π ∘ χ ∘ ι
- θ: column XOR diffusion (global linear mixing) — analog SHA's Σ
- ρ: rotation
- π: permutation
- χ: nonlinear (Maj-like)
- ι: round constant XOR

Test: disable θ at window [start, end) of rounds, measure OTOC.
Does Keccak have same prefix/reverse asymmetry as SHA-2?

Hypothesis: Since Keccak scrambles in 4 rounds total, critical zone should
be very narrow (maybe last 1-2 rounds). If similar "last rounds critical"
pattern, universal architectural property.
"""
import json, os, time
import numpy as np


OUT = '/home/user/SHA-256/research/min_entropy/otoc_sha3_theta_window_results.json'


RC = np.array([
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
], dtype=np.uint64)

ROT = np.array([
    [ 0, 36,  3, 41, 18],
    [ 1, 44, 10, 45,  2],
    [62,  6, 43, 15, 61],
    [28, 55, 25, 21, 56],
    [27, 20, 39,  8, 14],
], dtype=np.uint64)


def rotl64_vec(x, n):
    n = int(n) & 63
    if n == 0: return x
    return ((x << np.uint64(n)) | (x >> np.uint64(64 - n))) & np.uint64(0xFFFFFFFFFFFFFFFF)


def theta_step(s):
    """θ step: XOR columns."""
    s = s.copy()
    C = s[:, 0] ^ s[:, 1] ^ s[:, 2] ^ s[:, 3] ^ s[:, 4]  # (N, 5)
    D = np.empty_like(C)
    for x in range(5):
        D[:, x] = C[:, (x - 1) % 5] ^ rotl64_vec(C[:, (x + 1) % 5], 1)
    for y in range(5):
        s[:, y] ^= D
    return s


def rho_pi_step(s):
    """ρ + π combined."""
    B = np.zeros_like(s)
    for x in range(5):
        for y in range(5):
            new_x = y
            new_y = (2 * x + 3 * y) % 5
            B[:, new_y, new_x] = rotl64_vec(s[:, y, x], ROT[x, y])
    return B


def chi_step(s):
    """χ nonlinear step."""
    T = s.copy()
    s_new = T.copy()
    for x in range(5):
        for y in range(5):
            s_new[:, y, x] = T[:, y, x] ^ ((~T[:, y, (x + 1) % 5]) & T[:, y, (x + 2) % 5])
    return s_new


def iota_step(s, rc):
    """ι round constant."""
    s = s.copy()
    s[:, 0, 0] ^= rc
    return s


def keccak_f_with_theta_disabled(state, num_rounds, theta_disabled_start, theta_disabled_end):
    """Apply num_rounds of Keccak-f, disabling θ at rounds [start, end)."""
    s = state.copy()
    for r in range(num_rounds):
        if theta_disabled_start <= r < theta_disabled_end:
            pass  # skip θ
        else:
            s = theta_step(s)
        s = rho_pi_step(s)
        s = chi_step(s)
        s = iota_step(s, RC[r])
    return s


def absorb_sha3(messages):
    N = len(messages)
    padded = np.zeros((N, 136), dtype=np.uint8)
    for i, m in enumerate(messages):
        L = len(m)
        padded[i, :L] = np.frombuffer(m, dtype=np.uint8)
        padded[i, L] = 0x06
        padded[i, 135] = 0x80
    lanes = padded.view(dtype='<u8').reshape(N, 17)
    state = np.zeros((N, 5, 5), dtype=np.uint64)
    for idx in range(17):
        x = idx % 5; y = idx // 5
        state[:, y, x] = lanes[:, idx]
    return state


def state_to_bits256(state):
    N = state.shape[0]
    n_lanes = 4
    lanes_out = np.zeros((N, n_lanes), dtype=np.uint64)
    for idx in range(n_lanes):
        x = idx % 5; y = idx // 5
        lanes_out[:, idx] = state[:, y, x]
    out_bytes = lanes_out.view(dtype='<u1').reshape(N, n_lanes * 8)[:, :32]
    bits = np.unpackbits(out_bytes, axis=1, bitorder='big')[:, :256]
    return bits


def measure(r_obs, theta_dis_start, theta_dis_end, N=100, seed=42, msg_bytes=64):
    rng = np.random.default_rng(seed)
    base_msgs_arr = rng.integers(0, 256, size=(N, msg_bytes), dtype=np.uint8)
    base_msgs = [bytes(base_msgs_arr[i]) for i in range(N)]

    state_base = absorb_sha3(base_msgs)
    state_base_evolved = keccak_f_with_theta_disabled(state_base, r_obs, theta_dis_start, theta_dis_end)
    bits_base = state_to_bits256(state_base_evolved)

    msg_bits = msg_bytes * 8
    C = np.zeros((msg_bits, 256), dtype=np.float64)
    for i in range(msg_bits):
        byte_idx = i // 8; bit_idx = 7 - (i % 8)
        flip_arr = base_msgs_arr.copy()
        flip_arr[:, byte_idx] ^= np.uint8(1 << bit_idx)
        flip_msgs = [bytes(flip_arr[j]) for j in range(N)]
        state_flip = absorb_sha3(flip_msgs)
        state_flip_evolved = keccak_f_with_theta_disabled(state_flip, r_obs, theta_dis_start, theta_dis_end)
        bits_flip = state_to_bits256(state_flip_evolved)
        C[i] = (bits_base != bits_flip).mean(axis=0) - 0.5
    return C


def main():
    t0 = time.time()
    print("# SHA-3 (Keccak) θ-step cascade analysis")

    N = 100
    r_obs = 6  # just past SHA-3's scramble point r=4

    # Baseline
    C_base = measure(r_obs, -1, -1, N=N)
    F_base = float((C_base ** 2).sum())
    print(f"  r_obs={r_obs}, N={N}, baseline ||C||² = {F_base:.1f}")

    # Prefix window
    print(f"\n## Prefix [0, w) θ disabled")
    print(f"  {'w':>2}   {'||C||²':>10}   {'excess':>10}")
    prefix_res = {}
    for w in [0, 1, 2, 3, 4, 5, 6]:
        C = measure(r_obs, 0, w, N=N)
        F_sq = float((C**2).sum())
        excess = F_sq - F_base
        prefix_res[w] = {'frob_sq': F_sq, 'excess': excess}
        print(f"  {w:>2}   {F_sq:>10.1f}   {excess:>+10.1f}")

    # Reverse window
    print(f"\n## Reverse [r-w, r) θ disabled")
    print(f"  {'w':>2}   {'range':>8}   {'||C||²':>10}   {'excess':>10}")
    reverse_res = {}
    for w in [0, 1, 2, 3, 4, 5, 6]:
        C = measure(r_obs, r_obs - w, r_obs, N=N)
        F_sq = float((C**2).sum())
        excess = F_sq - F_base
        rng_str = f"[{r_obs-w},{r_obs})" if w > 0 else 'none'
        reverse_res[w] = {'frob_sq': F_sq, 'excess': excess, 'range': rng_str}
        print(f"  {w:>2}   {rng_str:>8}   {F_sq:>10.1f}   {excess:>+10.1f}")

    def crit_w(res):
        for w in sorted(res):
            if w > 0 and res[w]['excess'] > 100:
                return w
        return None

    pc = crit_w(prefix_res); rc = crit_w(reverse_res)
    print(f"\n## Critical windows (excess > 100):")
    print(f"  Prefix:  w = {pc}")
    print(f"  Reverse: w = {rc}")

    print(f"\n## Cross-architecture cascade comparison (at r_obs = scramble+2):")
    print(f"  Hash       prefix_crit   reverse_crit   critical_zone_width")
    print(f"  SHA-256    w=18-19       w=8-9          8-9 of 24 rounds")
    print(f"  SHA-512    w=20          w=6            6 of 24 rounds")
    print(f"  SHA-3      w={pc}           w={rc}            {rc if rc else '?'} of {r_obs} rounds")

    out = {
        'r_obs': r_obs, 'N': N, 'F_base': F_base,
        'prefix': prefix_res, 'reverse': reverse_res,
        'prefix_critical_w': pc, 'reverse_critical_w': rc,
        'runtime_sec': time.time() - t0,
    }
    with open(OUT, 'w') as f: json.dump(out, f, indent=2)
    print(f"\nSaved: {OUT}  ({time.time()-t0:.0f}s)")


if __name__ == '__main__': main()
