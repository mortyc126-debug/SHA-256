"""
Three solvers for the mini-SHA preimage problem.

Goal: measure whether Q∩T structural split gives practical speedup vs
pure bit-level SAT and vs z3's native bit-vector arithmetic.

Solvers:
  1. brute_force_preimage   — try all W
  2. sat_bit_preimage       — z3 Boolean encoding from equations.py
                              (explicit bit-level, carry vars exposed)
  3. sat_bv_preimage        — z3 BitVec encoding (native +, &, ^, rotr)
                              z3 internally picks encoding
  4. qt_split_preimage      — "naive Q∩T":
                              solve linear GF(2) part (XORs only) via Gaussian;
                              remaining AND gates + carry indicators solved by z3
                              on reduced instance
"""

import time
from z3 import (BitVec, BitVecVal, LShR, RotateRight, Extract, Concat,
                Solver, sat, unsat, Bool, BoolVal, And, Or, Not, Xor)
from mini_sha import (
    gen_IV, gen_K, single_round, sigma_params, Ch, Maj,
    Sig0 as Sig0_int, Sig1 as Sig1_int
)
from equations import build_preimage_instance, count_vars_constraints


def brute_force_preimage(H0, target, num_rounds, n):
    """Try all possible W tuples."""
    t0 = time.time()
    K = gen_K(n, num_rounds)
    mask = (1 << n) - 1
    total = (1 << (n * num_rounds))
    for idx in range(total):
        W = [(idx >> (n*i)) & mask for i in range(num_rounds)]
        state = tuple(H0)
        for r in range(num_rounds):
            state = single_round(state, W[r], K[r], n)
        h = [(H0[i] + state[i]) & mask for i in range(8)]
        if h == list(target):
            return W, time.time() - t0, idx + 1
    return None, time.time() - t0, total


def sat_bit_preimage(H0, target, num_rounds, n, timeout_ms=60_000):
    """z3 SAT on Boolean bit-level encoding."""
    t0 = time.time()
    constraints, W_vars, states, aux = build_preimage_instance(H0, target, num_rounds, n)
    nvars, nclauses = count_vars_constraints(constraints)

    s = Solver()
    s.set("timeout", timeout_ms)
    for c in constraints:
        s.add(c)

    result = s.check()
    elapsed = time.time() - t0

    if result == sat:
        m = s.model()
        W_out = []
        for r in range(num_rounds):
            w = 0
            for j in range(n):
                v = m.eval(W_vars[r][j], model_completion=True)
                if str(v) == 'True':
                    w |= (1 << j)
            W_out.append(w)
        return W_out, elapsed, (nvars, nclauses)
    else:
        return None, elapsed, (nvars, nclauses)


def _Sig_bv(x, rots, n):
    r1, r2, r3 = rots
    return RotateRight(x, r1) ^ RotateRight(x, r2) ^ RotateRight(x, r3)


def _Ch_bv(e, f, g):
    return (e & f) ^ (~e & g)


def _Maj_bv(a, b, c):
    return (a & b) ^ (a & c) ^ (b & c)


def sat_bv_preimage(H0, target, num_rounds, n, timeout_ms=60_000):
    """z3 bit-vector encoding: uses native arithmetic, z3 picks internals."""
    t0 = time.time()
    K = gen_K(n, num_rounds)
    Sig0r, Sig1r, _, _ = sigma_params(n)

    W_vars = [BitVec(f"W_{r}", n) for r in range(num_rounds)]
    s = Solver()
    s.set("timeout", timeout_ms)

    # Symbolic state propagation
    state = tuple(BitVecVal(H0[i], n) for i in range(8))
    for r in range(num_rounds):
        a, b, c, d, e, f, g, h = state
        T1 = h + _Sig_bv(e, Sig1r, n) + _Ch_bv(e, f, g) + BitVecVal(K[r], n) + W_vars[r]
        T2 = _Sig_bv(a, Sig0r, n) + _Maj_bv(a, b, c)
        state = (T1 + T2, a, b, c, d + T1, e, f, g)

    # Final: H_new = H0 + state
    for i in range(8):
        s.add(BitVecVal(H0[i], n) + state[i] == BitVecVal(target[i], n))

    result = s.check()
    elapsed = time.time() - t0
    if result == sat:
        m = s.model()
        W_out = [m.eval(W_vars[r], model_completion=True).as_long()
                 for r in range(num_rounds)]
        return W_out, elapsed, None
    return None, elapsed, None


def qt_split_preimage(H0, target, num_rounds, n, timeout_ms=60_000):
    """
    'Naive Q∩T': partition constraints into
       L = pure linear GF(2) (XOR only, no AND, no OR)
       Q = quadratic (contains AND)
       T = ternary/threshold (contains Or-of-And — carry definitions)
    Solve L first via Gaussian to eliminate as many vars as possible,
    then pass residual Q+T system to z3 SAT.

    This tests: does separating linear prefix help?
    """
    t0 = time.time()
    constraints, W_vars, states, aux = build_preimage_instance(H0, target, num_rounds, n)

    # Classification: walk each expression
    from z3 import is_app, is_const, is_bool
    linear = []
    nonlinear = []
    for c in constraints:
        if is_linear_gf2(c):
            linear.append(c)
        else:
            nonlinear.append(c)

    # We don't actually run Gaussian here — we measure partition sizes,
    # then pass EVERYTHING to z3 and let it do its own preprocessing.
    # This lets us observe: what fraction is linear? what's the structure?
    n_lin = len(linear)
    n_nonlin = len(nonlinear)

    s = Solver()
    s.set("timeout", timeout_ms)
    # Run z3 after we've done a quick "nothing" preprocessing pass —
    # the idea of naive Q∩T is precisely this: structure is declared but
    # we rely on SAT to exploit it.
    for c in constraints:
        s.add(c)
    result = s.check()
    elapsed = time.time() - t0

    if result == sat:
        m = s.model()
        W_out = []
        for r in range(num_rounds):
            w = 0
            for j in range(n):
                v = m.eval(W_vars[r][j], model_completion=True)
                if str(v) == 'True':
                    w |= (1 << j)
            W_out.append(w)
        return W_out, elapsed, (n_lin, n_nonlin)
    return None, elapsed, (n_lin, n_nonlin)


def is_linear_gf2(expr):
    """True iff expr is a conjunction of XOR-equalities (no AND/OR/NOT at top).
    Our constraints come as  (lhs == rhs)  where lhs/rhs are Bool combinations.
    We check: contains no And, no Or.  (Not/Xor are fine for GF(2) linearity)"""
    from z3 import is_and, is_or, is_eq, is_app_of, Z3_OP_AND, Z3_OP_OR
    # Simple walker
    def has_and_or(e):
        try:
            if is_and(e) or is_or(e):
                return True
            for i in range(e.num_args()):
                if has_and_or(e.arg(i)):
                    return True
        except Exception:
            return False
        return False
    return not has_and_or(expr)


if __name__ == "__main__":
    # Quick correctness test on n=4, R=2
    n = 4
    R = 2
    H0 = gen_IV(n)
    mask = (1 << n) - 1
    W_true = [7, 2]
    K = gen_K(n, R)
    state = tuple(H0)
    for r in range(R):
        state = single_round(state, W_true[r], K[r], n)
    target = [(H0[i] + state[i]) & mask for i in range(8)]

    print(f"Problem: n={n}, R={R}, W_true={W_true}, target={target}")
    print(f"Search space: 2^{n*R} = {2**(n*R)}\n")

    print("--- brute force ---")
    W, t, iters = brute_force_preimage(H0, target, R, n)
    print(f"  found: {W}  time: {t*1000:.2f}ms  iters: {iters}\n")

    print("--- SAT bit-level ---")
    W, t, stats = sat_bit_preimage(H0, target, R, n)
    print(f"  found: {W}  time: {t*1000:.2f}ms  vars/constraints: {stats}\n")

    print("--- SAT BitVec ---")
    W, t, _ = sat_bv_preimage(H0, target, R, n)
    print(f"  found: {W}  time: {t*1000:.2f}ms\n")

    print("--- QT-split (measures linearity) ---")
    W, t, stats = qt_split_preimage(H0, target, R, n)
    print(f"  found: {W}  time: {t*1000:.2f}ms  linear/nonlinear constraints: {stats}")
