"""
Session 12b: Full bit support per ideal, R, L (skip slow derived test).

Session 12 died at Step 7 (OOM einsum), but Step 6 confirmed D^4/R PERFECT.
This is enough for semisimple-like classification.

Just need cheap final task: bit support per ideal, R, L.
"""

import sys
sys.path.insert(0, '/home/user/SHA-256/research/prismatic')

import numpy as np
from session_21_perfect import extract_perfect_subalgebra
from session_20b_derived import GF2Basis


LOG = '/home/user/SHA-256/research/composition_lemma/session_12b_log.txt'


def log(msg):
    print(msg, flush=True)
    with open(LOG, 'a') as f:
        f.write(msg + '\n')


def support_bits(I_basis_coeffs, D4_matrices):
    support_rows = np.zeros(32, dtype=np.uint8)
    support_cols = np.zeros(32, dtype=np.uint8)
    for v in I_basis_coeffs:
        nz = np.where(v == 1)[0]
        for i in nz:
            support_rows |= (D4_matrices[i].sum(axis=1) > 0).astype(np.uint8)
            support_cols |= (D4_matrices[i].sum(axis=0) > 0).astype(np.uint8)
    return support_rows, support_cols


def main():
    with open(LOG, 'w') as f:
        f.write('')

    log("=== Session 12b: Bit support analysis ===\n")

    D4 = extract_perfect_subalgebra()
    n = len(D4)
    log(f"D^4 dim {n}")

    # Load R basis
    decomp = np.load('/home/user/SHA-256/research/composition_lemma/decomposition.npz')
    R_basis = GF2Basis(n)
    for key in decomp.files:
        basis = decomp[key]
        for i in range(basis.shape[0]):
            R_basis.add(basis[i].copy())
    log(f"R dim: {R_basis.size()}")

    # L: standard basis vectors not in R pivot positions
    R_pivots = set(R_basis.pivots)
    L_basis = []
    for i in range(n):
        if i not in R_pivots:
            v = np.zeros(n, dtype=np.uint8)
            v[i] = 1
            L_basis.append(v)
    log(f"L dim: {len(L_basis)}")

    log("\n--- Per-ideal bit support ---")
    distinct_supports = {}
    for j, key in enumerate(decomp.files):
        basis = decomp[key]
        bl = [basis[i] for i in range(basis.shape[0])]
        sr, sc = support_bits(bl, D4)
        rows = np.where(sr == 1)[0].tolist()
        cols = np.where(sc == 1)[0].tolist()
        d = basis.shape[0]
        log(f"Ideal {j} (dim {d}, indices_subset_of_D4_basis): {len(rows)} rows, {len(cols)} cols")
        log(f"  rows: {rows}")
        log(f"  cols: {cols}")
        sig = (tuple(rows), tuple(cols))
        distinct_supports.setdefault(sig, []).append(j)

    log(f"\n--- Distinct support patterns: {len(distinct_supports)} ---")
    for (rows, cols), ideals in sorted(distinct_supports.items(), key=lambda x: len(x[0][0])):
        log(f"  Support pattern (rows={list(rows)}, cols={list(cols)}): ideals {ideals}")

    log("\n--- R (solvable radical) bit support ---")
    sr, sc = support_bits(R_basis.basis, D4)
    rows = np.where(sr == 1)[0].tolist()
    cols = np.where(sc == 1)[0].tolist()
    log(f"R: rows ({len(rows)}): {rows}")
    log(f"R: cols ({len(cols)}): {cols}")

    log("\n--- L (Levi complement) bit support ---")
    sr, sc = support_bits(L_basis, D4)
    rows = np.where(sr == 1)[0].tolist()
    cols = np.where(sc == 1)[0].tolist()
    log(f"L: rows ({len(rows)}): {rows}")
    log(f"L: cols ({len(cols)}): {cols}")


if __name__ == "__main__":
    main()
