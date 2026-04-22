"""SHA-256 reverse compression: invert one or more rounds given W and state.

Forward round t (state, W[t], K[t]):
  T1 = h + Σ1(e) + Ch(e,f,g) + K[t] + W[t]
  T2 = Σ0(a) + Maj(a,b,c)
  state_new = (T1+T2, a, b, c, d+T1, e, f, g)

Reverse round t (state_new, W[t], K[t]):
  a_old = b_new
  b_old = c_new
  c_old = d_new
  e_old = f_new
  f_old = g_new
  g_old = h_new
  T2 = Σ0(a_old) + Maj(a_old, b_old, c_old)
  T1 = a_new - T2
  d_old = e_new - T1
  h_old = T1 - Σ1(e_old) - Ch(e_old, f_old, g_old) - K[t] - W[t]

Verified against hashlib roundtrip.
"""
import hashlib
import numpy as np
import sha256_chimera as ch


U32 = np.uint32
MASK = ch.MASK


def forward_round(state, W_t, K_t):
    """Single forward round. state = (a..h) tuple of uint32."""
    a, b, c, d, e, f, g, h = state
    T1 = (h + ch.Sigma1(e) + ch.Ch(e, f, g) + U32(K_t) + U32(W_t)) & MASK
    T2 = (ch.Sigma0(a) + ch.Maj(a, b, c)) & MASK
    a_new = (T1 + T2) & MASK
    e_new = (d + T1) & MASK
    return (a_new, a, b, c, e_new, e, f, g)


def reverse_round(state_new, W_t, K_t):
    """Single reverse round. state_new = (a..h) tuple."""
    a_n, b_n, c_n, d_n, e_n, f_n, g_n, h_n = state_new
    # Recover non-T-dependent registers
    a_old = b_n
    b_old = c_n
    c_old = d_n
    e_old = f_n
    f_old = g_n
    g_old = h_n
    # T2 from a_old, b_old, c_old
    T2 = (ch.Sigma0(a_old) + ch.Maj(a_old, b_old, c_old)) & MASK
    # T1 from a_new and T2
    T1 = (a_n - T2) & MASK
    # d_old from e_new and T1
    d_old = (e_n - T1) & MASK
    # h_old from T1 minus contributions
    h_old = (T1 - ch.Sigma1(e_old) - ch.Ch(e_old, f_old, g_old)
             - U32(K_t) - U32(W_t)) & MASK
    return (a_old, b_old, c_old, d_old, e_old, f_old, g_old, h_old)


def forward_compression(state, W, num_rounds):
    """Apply num_rounds forward. W is list of 64 uint32, K is K_VANILLA."""
    s = state
    K = ch.K_VANILLA
    for t in range(num_rounds):
        s = forward_round(s, W[t], K[t])
    return s


def reverse_compression(state, W, num_rounds, start_round):
    """Reverse num_rounds rounds, starting from state at start_round (= round number after forward).

    E.g. to reverse forward rounds [start_round - num_rounds, start_round - 1], pass:
      state = state_after_forward(start_round)
      Reverses rounds [start_round-1 down to start_round-num_rounds]
    """
    s = state
    K = ch.K_VANILLA
    for t in range(start_round - 1, start_round - num_rounds - 1, -1):
        s = reverse_round(s, W[t], K[t])
    return s


def expand_schedule(W_in_16):
    """Expand W[0..15] to W[0..63] via standard sigma schedule."""
    W = [U32(w) for w in W_in_16] + [U32(0)] * 48
    for t in range(16, 64):
        W[t] = (ch.sigma1(W[t-2]) + W[t-7]
                + ch.sigma0(W[t-15]) + W[t-16]) & MASK
    return W


def test_roundtrip():
    """Forward N rounds then reverse N rounds = identity."""
    print("# Testing forward+reverse roundtrip:")
    rng = np.random.default_rng(42)
    for trial in range(3):
        # Random initial state and message
        state0 = tuple(U32(x) for x in rng.integers(0, 2**32, size=8))
        W_in = list(rng.integers(0, 2**32, size=16, dtype=np.int64).astype(U32))
        W = expand_schedule(W_in)
        for r in [1, 8, 16, 32, 48, 64]:
            state_fwd = forward_compression(state0, W, r)
            state_back = reverse_compression(state_fwd, W, r, r)
            ok = state_back == state0
            print(f"  trial {trial+1}, r={r:>2}: roundtrip {'✓' if ok else '✗'}")
            if not ok:
                print(f"    expected: {[hex(int(x)) for x in state0]}")
                print(f"    got:      {[hex(int(x)) for x in state_back]}")
                return False
    return True


def test_against_hashlib():
    """Forward 64 rounds + feed-forward = hashlib output."""
    print("\n# Testing forward 64R against hashlib:")
    test_msgs = [b'', b'abc', b'a' * 56]
    for msg in test_msgs:
        # Pad
        L = len(msg) * 8
        padded = bytearray(msg)
        padded.append(0x80)
        while (len(padded) % 64) != 56:
            padded.append(0)
        padded += L.to_bytes(8, 'big')
        # First block
        block = padded[:64]
        W_in = [int.from_bytes(block[4*i:4*(i+1)], 'big') for i in range(16)]
        W = expand_schedule(W_in)
        state0 = tuple(U32(x) for x in ch.IV_VANILLA)
        s64 = forward_compression(state0, W, 64)
        # Feed-forward
        s_final = tuple((s64[i] + state0[i]) & MASK for i in range(8))
        # Compare to hashlib (assuming single-block message)
        if len(padded) == 64:
            expected = hashlib.sha256(msg).digest()
            got = b''.join(int(s_final[i]).to_bytes(4, 'big') for i in range(8))
            ok = (got == expected)
            print(f"  msg={msg!r:20s} hashlib match: {'✓' if ok else '✗'}")
            if not ok:
                print(f"    expected: {expected.hex()}")
                print(f"    got:      {got.hex()}")
        else:
            print(f"  msg={msg!r:20s} (multi-block, skip)")
    return True


if __name__ == '__main__':
    test_roundtrip()
    test_against_hashlib()
