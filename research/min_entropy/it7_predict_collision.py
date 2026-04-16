"""
IT-7P: Predictive test — can chain-2 score on state1_diff predict
collision proximity WITHOUT knowing the hash output?

Assumption: Ω_2 = 0.42 is real SHA-256 structure, not artifact.

Prediction: a score S(D) computed from state1_diff D = state1(M)⊕state1(M')
using Walsh-2 coefficients TRAINED on half the data should PREDICT
HW(delta_h) on the other half.

Method:
  1. Generate 400K random pairs.
  2. Split: train 200K, test 200K.
  3. Train: compute M_in[a,b] = Walsh-2 correlation of
     (D_train[a] XOR D_train[b]) with f_near(train).
     This is the "chain-2 learned signature" of near-collision.
  4. Test: for each test pair, compute
     S(D) = Σ_{a<b} M_in[a,b] · (2·(D[a]⊕D[b]) - 1)
     (how well this pair's Walsh-2 structure matches the near-collision pattern)
  5. Sort test pairs by S(D).
  6. Compare: top 10% by S vs bottom 10% — is mean HW(delta_h) lower?

If YES: chain-score is a practical collision search heuristic that
USES state1 information to guide toward near-collisions.
"""
import hashlib, json, math, os, time
import numpy as np

N_TOTAL = 400000
N_TRAIN = 200000
N_TEST = 200000
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'it7p_predict.json')


def main():
    t_total = time.time()
    print("# IT-7P: predictive collision test (train/test split)")

    import sha256_chimera as ch

    rng = np.random.default_rng(0xBED1C7)
    print(f"# Generating {N_TOTAL} random pairs...")
    M1 = [rng.bytes(64) for _ in range(N_TOTAL)]
    M2 = [rng.bytes(64) for _ in range(N_TOTAL)]

    # SHA-256 full output
    print("# Hashing...")
    t0 = time.time()
    h1 = [hashlib.sha256(m).digest() for m in M1]
    h2 = [hashlib.sha256(m).digest() for m in M2]
    print(f"  {time.time()-t0:.1f}s")

    h1_arr = np.frombuffer(b''.join(h1), dtype=np.uint8).reshape(N_TOTAL, 32)
    h2_arr = np.frombuffer(b''.join(h2), dtype=np.uint8).reshape(N_TOTAL, 32)
    delta_h = h1_arr ^ h2_arr
    delta_h_bits = np.unpackbits(delta_h, axis=1, bitorder='big')
    hw_all = delta_h_bits.sum(axis=1).astype(np.int32)

    # State1
    print("# Computing state1...")
    t0 = time.time()
    def block1_state(messages):
        N = len(messages)
        U32 = ch.U32
        M_bytes = np.frombuffer(b''.join(messages), dtype=np.uint8).reshape(N, 64)
        block1 = M_bytes.view(dtype='>u4').reshape(N, 16).astype(U32)
        state = np.broadcast_to(ch.IV_VANILLA, (N, 8)).copy()
        return ch.compress(state, block1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)

    s1a = block1_state(M1)
    s1b = block1_state(M2)
    D_uint32 = s1a ^ s1b
    print(f"  {time.time()-t0:.1f}s")

    def state_to_bits(state):
        N = state.shape[0]
        bits = np.zeros((N, 256), dtype=np.uint8)
        for w in range(8):
            for b in range(32):
                bits[:, w*32+b] = ((state[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
        return bits

    D_bits = state_to_bits(D_uint32)

    # ---- Split ----
    D_train = D_bits[:N_TRAIN]
    D_test = D_bits[N_TRAIN:]
    hw_train = hw_all[:N_TRAIN]
    hw_test = hw_all[N_TRAIN:]

    print(f"\n# Train: N={N_TRAIN}, mean HW={hw_train.mean():.2f}")
    print(f"# Test:  N={N_TEST},  mean HW={hw_test.mean():.2f}")

    # ---- Train: learn Walsh-2 signature of near-collision ----
    print("\n# Training Walsh-2 signature on train set...")
    t0 = time.time()
    f_train = (hw_train < 128).astype(np.float32)
    sf_train = 2.0 * f_train - 1.0
    Y_train = 2.0 * D_train.astype(np.float32) - 1.0
    sqrtN_tr = math.sqrt(N_TRAIN)

    # M_in[a, b] = (1/sqrtN) * Σ_i Y[i,a] * Y[i,b] * sf[i]
    M_in = (Y_train.T @ (Y_train * sf_train[:, None])) / sqrtN_tr   # (256, 256)
    print(f"  Walsh-2 matrix computed in {time.time()-t0:.1f}s")
    print(f"  M_in max = {np.abs(M_in).max():.4f}, mean = {M_in.mean():.6f}")

    # ---- Test: compute chain-score for each test pair ----
    print("\n# Computing chain-score on test set...")
    t0 = time.time()
    Y_test = 2.0 * D_test.astype(np.float32) - 1.0

    # For each test pair i:
    #   S_i = Σ_{a<b} M_in[a,b] · Y_test[i,a] · Y_test[i,b]
    # This is a quadratic form: S_i = Y_test[i,:] @ M_in @ Y_test[i,:].T / 2
    # (factor 1/2 because we want upper triangle only, but M_in is symmetric
    #  so full product = 2 * upper_triangle + diagonal)

    # Actually: Y[i,a]*Y[i,b] for a≠b. M_in is the correlation matrix.
    # Full quadratic form: Q_i = Y[i] @ M_in @ Y[i] = Σ_{a,b} M_in[a,b] Y[i,a] Y[i,b]
    # = Σ_{a≠b} M_in[a,b] Y[i,a] Y[i,b] + Σ_a M_in[a,a] Y[i,a]^2
    # Since Y[i,a]^2 = 1 always: diagonal term = Σ M_in[a,a] = trace(M_in)
    # So Σ_{a≠b} = Q_i - trace(M_in)
    # And Σ_{a<b} = (Q_i - trace(M_in)) / 2

    # Vectorized: Q = diag(Y_test @ M_in @ Y_test.T)
    # But Y_test is (N_TEST, 256), M_in is (256, 256).
    # Q = (Y_test * (Y_test @ M_in)).sum(axis=1)  — element-wise trick
    YM = Y_test @ M_in                              # (N_TEST, 256)
    Q = (Y_test * YM).sum(axis=1)                   # (N_TEST,)
    tr = np.trace(M_in)
    score = (Q - tr) / 2                             # (N_TEST,) chain-2 score
    print(f"  Computed in {time.time()-t0:.1f}s")
    print(f"  score: mean={score.mean():.2f}, std={score.std():.2f}, min={score.min():.1f}, max={score.max():.1f}")

    # ---- Evaluate: does score predict HW(delta_h)? ----
    print("\n# Evaluation: does chain-score predict collision proximity?")

    # Correlation
    corr_score_hw = float(np.corrcoef(score, hw_test)[0, 1])
    print(f"  corr(score, HW(delta_h)) = {corr_score_hw:+.6f}")

    # Top/bottom percentile comparison
    for pct in [1, 5, 10, 25]:
        n_pct = max(1, N_TEST * pct // 100)
        top_idx = np.argsort(-score)[:n_pct]       # highest score
        bot_idx = np.argsort(score)[:n_pct]         # lowest score
        mid_idx = np.argsort(np.abs(score - score.mean()))[:n_pct]  # most average

        hw_top = hw_test[top_idx].mean()
        hw_bot = hw_test[bot_idx].mean()
        hw_mid = hw_test[mid_idx].mean()
        hw_rnd = hw_test.mean()

        delta_top = hw_top - hw_rnd
        delta_bot = hw_bot - hw_rnd

        print(f"  Top {pct}% score:    mean HW = {hw_top:.2f}  (Δ = {delta_top:+.2f})")
        print(f"  Bottom {pct}% score: mean HW = {hw_bot:.2f}  (Δ = {delta_bot:+.2f})")
        print(f"  Middle {pct}%:       mean HW = {hw_mid:.2f}")
        print(f"  Random baseline:     mean HW = {hw_rnd:.2f}")

        # Is the difference significant?
        std_hw = hw_test.std() / math.sqrt(n_pct)
        z_top = delta_top / std_hw if std_hw > 0 else 0
        z_bot = delta_bot / std_hw if std_hw > 0 else 0
        print(f"  z_top = {z_top:+.2f},  z_bot = {z_bot:+.2f}  (|z|>3 → significant)")
        print()

    # Also: check if near-collision rate is higher in top-scored pairs
    print("  Near-collision rate (HW < 128):")
    for pct in [1, 5, 10]:
        n_pct = max(1, N_TEST * pct // 100)
        top_idx = np.argsort(-score)[:n_pct]
        bot_idx = np.argsort(score)[:n_pct]
        rate_top = (hw_test[top_idx] < 128).mean()
        rate_bot = (hw_test[bot_idx] < 128).mean()
        rate_rnd = (hw_test < 128).mean()
        print(f"    Top {pct}%: {rate_top:.4f}  Bot {pct}%: {rate_bot:.4f}  Random: {rate_rnd:.4f}")

    out = {
        'meta': {'N_total': N_TOTAL, 'N_train': N_TRAIN, 'N_test': N_TEST},
        'corr_score_hw': corr_score_hw,
        'score_stats': {'mean': float(score.mean()), 'std': float(score.std())},
        'hw_stats': {'mean': float(hw_test.mean()), 'std': float(hw_test.std())},
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {OUT}")
    print(f"Total: {time.time()-t_total:.0f}s")


if __name__ == '__main__':
    main()
