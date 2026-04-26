"""
Q∩T equation generator for mini-SHA.

Produces TWO systems for a preimage/collision instance:

  Q-system: quadratic equations over GF(2)
    variables = {bits of state_r, bits of W[r], bits of carry}
    equations = bit-level constraints from XOR + AND (Ch, Maj, Σ, sigma, and
                explicit bit-wise carry evolution)

  T-system: threshold/carry equations over Z
    Each addition  s = x + y + z + ...  (mod 2^n)  generates:
      - XOR-part (linear over GF(2)): s_i = x_i ⊕ y_i ⊕ z_i ⊕ ... ⊕ carry_i
      - T-part (threshold over Z):    carry_{i+1} = floor((x_i + y_i + z_i + carry_i) / 2)

Convention: carry bits are the COUPLING variables between Q and T.
Q sees them as bits with XOR relations.
T sees them as integer floor-indicators.

NOTE: we express T constraints in the form
  c_{i+1} == Majority(x_i, y_i, z_i, c_i)   (for 3-input+carry)
  c_{i+1} == (x_i + y_i + c_i) >= 2         (for 2-input+carry)
This is already captured Q-side through AND gates.  The "T" framing comes in
when we have LARGE-arity adders (4+ terms) where threshold is more natural than
writing full-adder cascades.

For this prototype we focus on the simplest arity-2 case: each + is split into
a cascade of bit-wise half/full adders, producing Q-side equations AND
explicit carry variables. Then we can re-aggregate into T-form for analysis.
"""

from z3 import Bool, BoolVal, Xor, And, Or, Not, Implies, Solver, BoolRef, sat, unsat
from mini_sha import (
    sigma_params, Ch, Maj, gen_K, gen_IV, single_round
)


def bitvec(name, n):
    """Create n Bool vars named name_0 ... name_{n-1} (LSB first)."""
    return [Bool(f"{name}_{i}") for i in range(n)]


def const_to_bools(x, n):
    return [BoolVal(bool((x >> i) & 1)) for i in range(n)]


def xor_bits(*bitlists):
    """Element-wise XOR of multiple n-bit lists."""
    n = len(bitlists[0])
    out = []
    for i in range(n):
        acc = bitlists[0][i]
        for bl in bitlists[1:]:
            acc = Xor(acc, bl[i])
        out.append(acc)
    return out


def and_bits(a, b):
    return [And(a[i], b[i]) for i in range(len(a))]


def not_bits(a):
    return [Not(a[i]) for i in range(len(a))]


def rotr_bits(a, r):
    n = len(a)
    return [a[(i + r) % n] for i in range(n)]


def shr_bits(a, s):
    n = len(a)
    return [a[i + s] if i + s < n else BoolVal(False) for i in range(n)]


def Sig_bits(x, rots):
    r1, r2, r3 = rots
    return xor_bits(rotr_bits(x, r1), rotr_bits(x, r2), rotr_bits(x, r3))


def Ch_bits(e, f, g):
    """Ch = (e ∧ f) ⊕ (¬e ∧ g)"""
    return xor_bits(and_bits(e, f), and_bits(not_bits(e), g))


def Maj_bits(a, b, c):
    """Maj = (a ∧ b) ⊕ (a ∧ c) ⊕ (b ∧ c)"""
    return xor_bits(and_bits(a, b), and_bits(a, c), and_bits(b, c))


def adder_constraints(xs, out, carry_name, n):
    """
    Constrains:   out ≡  Σ xs  (mod 2^n)
    xs : list of bit-lists, each length n  (operands)
    out: bit-list length n                 (sum)
    carry_name: prefix for internal carry variables

    Returns:
      (constraints_list, carry_bits_dict)
      carry_bits_dict[i][j] = j-th carry column bit of the i-th partial sum
    """
    k = len(xs)
    assert k >= 2
    constraints = []
    carry_trace = {}

    # Accumulate partial sum with ripple-carry adders.
    # partial := xs[0];  for i=1..k-1: partial += xs[i] (produces fresh carries)
    partial = list(xs[0])
    for i in range(1, k):
        y = xs[i]
        # carry_i_0 starts at 0; we propagate through n bit positions
        new_partial = []
        carry = BoolVal(False)
        col_carries = []
        for j in range(n):
            # sum bit: partial_j XOR y_j XOR carry
            sum_bit = Xor(Xor(partial[j], y[j]), carry)
            new_partial.append(sum_bit)
            # next carry: maj(partial_j, y_j, carry)
            if j < n - 1:
                c_var = Bool(f"{carry_name}_{i}_{j}")
                col_carries.append(c_var)
                constraints.append(
                    c_var ==
                    Or(And(partial[j], y[j]),
                       And(partial[j], carry),
                       And(y[j], carry))
                )
                carry = c_var
        carry_trace[i] = col_carries
        partial = new_partial

    # Final equality:  partial == out
    for j in range(n):
        constraints.append(partial[j] == out[j])

    return constraints, carry_trace


def round_constraints(state_in, state_out, W_r, K_r_const, n, round_idx):
    """
    Constraints relating state_in (8-tuple of bit-lists) -> state_out (8-tuple)
    through single round with message W_r (bit-list) and constant K_r (int).

    Returns (constraints_list, aux_vars_dict).
    """
    a, b, c, d, e, f, g, h = state_in
    a_p, b_p, c_p, d_p, e_p, f_p, g_p, h_p = state_out
    constraints = []
    aux = {}

    Sig0r, Sig1r, _, _ = sigma_params(n)

    # compute Sig1(e), Ch(e,f,g), Sig0(a), Maj(a,b,c) — all linear-ish
    Sig1_e = Sig_bits(e, Sig1r)
    Ch_efg = Ch_bits(e, f, g)
    Sig0_a = Sig_bits(a, Sig0r)
    Maj_abc = Maj_bits(a, b, c)

    K_bits = const_to_bools(K_r_const, n)

    # T1 = h + Sig1(e) + Ch(e,f,g) + K_r + W_r  (5-term adder, mod 2^n)
    T1 = bitvec(f"T1_r{round_idx}", n)
    c_T1, trace_T1 = adder_constraints([h, Sig1_e, Ch_efg, K_bits, W_r], T1,
                                        f"carryT1_r{round_idx}", n)
    constraints += c_T1
    aux[f"T1_r{round_idx}"] = T1
    aux[f"carryT1_r{round_idx}"] = trace_T1

    # T2 = Sig0(a) + Maj(a,b,c)  (2-term, mod 2^n)
    T2 = bitvec(f"T2_r{round_idx}", n)
    c_T2, trace_T2 = adder_constraints([Sig0_a, Maj_abc], T2,
                                        f"carryT2_r{round_idx}", n)
    constraints += c_T2
    aux[f"T2_r{round_idx}"] = T2
    aux[f"carryT2_r{round_idx}"] = trace_T2

    # a' = T1 + T2
    c_ap, trace_ap = adder_constraints([T1, T2], a_p,
                                        f"carryAp_r{round_idx}", n)
    constraints += c_ap
    aux[f"carryAp_r{round_idx}"] = trace_ap

    # e' = d + T1
    c_ep, trace_ep = adder_constraints([d, T1], e_p,
                                        f"carryEp_r{round_idx}", n)
    constraints += c_ep
    aux[f"carryEp_r{round_idx}"] = trace_ep

    # shift: b'=a, c'=b, d'=c; f'=e, g'=f, h'=g
    for i in range(n):
        constraints.append(b_p[i] == a[i])
        constraints.append(c_p[i] == b[i])
        constraints.append(d_p[i] == c[i])
        constraints.append(f_p[i] == e[i])
        constraints.append(g_p[i] == f[i])
        constraints.append(h_p[i] == g[i])

    return constraints, aux


def build_preimage_instance(H0, target_h, num_rounds, n):
    """
    Build Z3 Solver instance asking: find W[0..num_rounds-1] ∈ {0,1}^n such that
    mini-SHA compression (with W words, no schedule expansion, R rounds, feed-forward)
    gives hash == target_h.

    Returns (solver, W_vars, Q_constraints_list, T_adder_constraints_list,
             all_carry_vars, total_vars).

    Split into:
      Q: pure XOR/AND relations (bit-level logic, carry definitions)
      T: threshold = carry indicators (already inlined as Or-of-Ands in adder_constraints)
    """
    K = gen_K(n, num_rounds)

    # State bitvecs for r=0..num_rounds
    states = []
    for r in range(num_rounds + 1):
        st = tuple(bitvec(f"r{r}_reg{i}", n) for i in range(8))
        states.append(st)

    # W bitvecs
    W = [bitvec(f"W_{r}", n) for r in range(num_rounds)]

    constraints = []
    aux = {}

    # Pin initial state to H0
    for i in range(8):
        for j in range(n):
            constraints.append(states[0][i][j] == bool((H0[i] >> j) & 1))

    # Round constraints
    for r in range(num_rounds):
        rc, ra = round_constraints(states[r], states[r+1], W[r], K[r], n, r)
        constraints += rc
        aux.update(ra)

    # Final hash: H_new[i] = H0[i] + state_final[i]  (mod 2^n)
    H_final = [bitvec(f"H_{i}", n) for i in range(8)]
    for i in range(8):
        H0_bits = const_to_bools(H0[i], n)
        c_hf, _ = adder_constraints([H0_bits, states[num_rounds][i]], H_final[i],
                                     f"carryHF_{i}", n)
        constraints += c_hf
        # Pin to target
        for j in range(n):
            constraints.append(H_final[i][j] == bool((target_h[i] >> j) & 1))

    return constraints, W, states, aux


def count_vars_constraints(constraints):
    """Rough metrics."""
    # Collect all Bool names
    names = set()
    def walk(e):
        if isinstance(e, BoolRef):
            if e.num_args() == 0 and not (e.decl().name() in ('true', 'false')):
                names.add(e.decl().name())
            for i in range(e.num_args()):
                walk(e.arg(i))
    for c in constraints:
        walk(c)
    return len(names), len(constraints)


if __name__ == "__main__":
    # Smoke test: build preimage instance for tiny n=4, R=2
    n = 4
    R = 2
    H0 = gen_IV(n)
    # Compute a real target hash
    mask = (1 << n) - 1
    W_true = [3, 5]
    K = gen_K(n, R)
    state = tuple(H0)
    for r in range(R):
        state = single_round(state, W_true[r], K[r], n)
    target = [(H0[i] + state[i]) & mask for i in range(8)]

    print(f"n={n}, R={R}, W_true={W_true}, target={target}")

    constraints, W_vars, states, aux = build_preimage_instance(H0, target, R, n)
    nvars, nclauses = count_vars_constraints(constraints)
    print(f"Constraint count: {nclauses}, unique vars: {nvars}")
    print(f"Search space (brute force): 2^{n*R} = {2**(n*R)}")
