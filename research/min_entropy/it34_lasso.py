"""IT-34: LASSO / sparse regression on state1_diff -> hash_diff_HW.

Feed differential SHA-256 pairs (m_A, m_B=m_A XOR e) to LASSO regression.
Features: 256-bit state1_diff (from block-1 output XOR).
Target: HW(hash_diff) — total Hamming weight of final hash diff.

If LASSO finds sparse predictor with <10 bits and R² > 0:
  → interpretable analytical formula for HW(hash_diff) from state1_diff bits.
  → this IS new mathematics — explicit relation the community may have missed.

If LASSO finds nothing (R² ≈ 0): no sparse linear formula exists at this level.

Also tries polynomial features (pairwise products of state1 bits) via L1-logistic.
This probes for quadratic analytical formulas.
"""
import json, math, os, time
from itertools import combinations
import numpy as np
from sklearn.linear_model import Lasso, LassoCV, LogisticRegression
from sklearn.metrics import r2_score, roc_auc_score
import sha256_chimera as ch

HERE = os.path.dirname(os.path.abspath(__file__))
N_PAIRS = 50000  # N pairs to generate

def full_sha_pairs(N, rng):
    """Generate N pairs (m_A, m_B=m_A XOR small_diff), return state1_diff and hash_diff."""
    m_A = rng.integers(0, 256, size=(N, 64), dtype=np.uint8)
    # Random diff: 1-8 bit flips per pair
    diff_mask = np.zeros((N, 64), dtype=np.uint8)
    for i in range(N):
        hw_d = rng.integers(1, 9)
        bits = rng.choice(512, size=hw_d, replace=False)
        for b in bits: diff_mask[i, b >> 3] ^= 1 << (b & 7)
    m_B = m_A ^ diff_mask

    def sha_full_batch(inputs):
        b1 = inputs.view('>u4').reshape(N, 16).astype(ch.U32)
        s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy(), b1,
                         ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
        pad = bytearray(64); pad[0] = 0x80; pad[-8:] = (512).to_bytes(8, 'big')
        pad_block = np.frombuffer(bytes(pad), dtype=np.uint8).view('>u4').reshape(1, 16).astype(ch.U32)
        pad_block = np.broadcast_to(pad_block, (N, 16))
        s2 = ch.compress(s1, pad_block, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
        return s1, s2

    s1_A, s2_A = sha_full_batch(m_A)
    s1_B, s2_B = sha_full_batch(m_B)

    # Diffs
    ds1 = s1_A ^ s1_B  # (N, 8) uint32
    ds2 = s2_A ^ s2_B  # (N, 8) uint32

    # Convert to bit arrays
    def to_bits(s):
        bits = np.zeros((N, 256), dtype=np.float32)
        for w in range(8):
            for b in range(32):
                bits[:, w*32+b] = ((s[:, w] >> np.uint32(31-b)) & 1).astype(np.float32)
        return bits
    ds1_bits = to_bits(ds1)
    ds2_bits = to_bits(ds2)
    hw_hash = ds2_bits.sum(axis=1)
    return ds1_bits, ds2_bits, hw_hash


def main():
    t0 = time.time()
    rng = np.random.default_rng(0xCAFE1337)
    print(f"# IT-34: LASSO search for sparse analytical formula")
    print(f"# Generating {N_PAIRS} pairs...")

    X, Y_bits, hw_hash = full_sha_pairs(N_PAIRS, rng)
    print(f"# X shape: {X.shape}, HW stats: mean={hw_hash.mean():.2f} std={hw_hash.std():.2f}")

    # Test 1: Linear regression state1_diff -> HW(hash_diff)
    print(f"\n=== Test 1: LASSO on state1_diff → HW(hash_diff) ===")
    N_train = int(N_PAIRS * 0.8)
    X_tr, X_te = X[:N_train], X[N_train:]
    y_tr, y_te = hw_hash[:N_train], hw_hash[N_train:]
    for alpha in [0.01, 0.1, 0.5, 1.0]:
        model = Lasso(alpha=alpha, max_iter=5000)
        model.fit(X_tr, y_tr)
        r2 = r2_score(y_te, model.predict(X_te))
        n_nz = (model.coef_ != 0).sum()
        top_coef = sorted(enumerate(model.coef_), key=lambda kv: -abs(kv[1]))[:5]
        print(f"  α={alpha}: R² = {r2:+.6f}, non-zero coefs = {n_nz}, "
              f"top 5 = {[(i, f'{v:+.3f}') for i, v in top_coef]}")

    # Test 2: LASSO per-output-bit (256 binary classifications)
    print(f"\n=== Test 2: LASSO per-hash-bit ===")
    print(f"For each hash output bit b, predict whether ds2_bits[b] = 1 from state1_diff.")
    Y = Y_bits[:, :]  # (N, 256)
    best_r2 = []
    for target_bit in [0, 50, 100, 160, 200, 250]:  # sample
        y_target = Y[:, target_bit]
        y_tr, y_te = y_target[:N_train], y_target[N_train:]
        if y_tr.sum() < 100 or (N_train - y_tr.sum()) < 100:
            print(f"  bit {target_bit}: skipped (degenerate)")
            continue
        model = LogisticRegression(penalty='l1', solver='liblinear', C=0.1, max_iter=500)
        model.fit(X_tr, y_tr)
        auc = roc_auc_score(y_te, model.predict_proba(X_te)[:, 1])
        n_nz = (model.coef_ != 0).sum()
        top = sorted(enumerate(model.coef_[0]), key=lambda kv: -abs(kv[1]))[:3]
        print(f"  bit {target_bit} (H[{target_bit//32}][b{target_bit%32}]): "
              f"AUC = {auc:.4f}, non-zero = {n_nz}, top 3: {[(i, f'{v:+.2f}') for i,v in top]}")
        best_r2.append((target_bit, auc))

    # Test 3: Full AUC per-bit scan
    print(f"\n=== Test 3: Per-bit AUC scan with LASSO (all 256 bits) ===")
    aucs = []
    for target_bit in range(256):
        y_target = Y[:, target_bit]
        y_tr, y_te = y_target[:N_train], y_target[N_train:]
        if y_tr.sum() < 100 or (N_train - y_tr.sum()) < 100:
            aucs.append((target_bit, 0.5)); continue
        model = LogisticRegression(penalty='l1', solver='liblinear', C=0.05, max_iter=300)
        model.fit(X_tr, y_tr)
        auc = roc_auc_score(y_te, model.predict_proba(X_te)[:, 1])
        aucs.append((target_bit, auc))
    aucs.sort(key=lambda kv: -kv[1])
    print(f"Top 20 bits by LASSO AUC:")
    for bit, auc in aucs[:20]:
        print(f"  bit {bit:>3} H[{bit//32}][b{bit%32}]: AUC = {auc:.4f}")
    print(f"Bottom 5 bits (least predictable):")
    for bit, auc in aucs[-5:]:
        print(f"  bit {bit:>3} H[{bit//32}][b{bit%32}]: AUC = {auc:.4f}")
    print(f"\nMean AUC across 256 bits: {np.mean([a for _,a in aucs]):.4f}")
    print(f"(Random baseline: 0.5)")
    print(f"Bits with AUC > 0.55: {sum(1 for _,a in aucs if a > 0.55)}")

    out = {
        'n_pairs': N_PAIRS,
        'top_aucs_per_bit': aucs[:30],
        'mean_auc_across_bits': float(np.mean([a for _,a in aucs])),
    }
    with open(os.path.join(HERE, 'it34_lasso.json'), 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nTotal time: {time.time()-t0:.0f}s")


if __name__ == '__main__': main()
