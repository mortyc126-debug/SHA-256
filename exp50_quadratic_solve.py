#!/usr/bin/env python3
"""
EXP 50: Quadratic Carry Solve — Macaulay Linearization

GF(2) solve: rank=256 but residual=128 (carry decorrelation).
Step back: carry makes system QUADRATIC (degree 2).
Step forward: linearize quadratic system via Macaulay method.

Replace each product x_i·x_j with new variable y_{ij}.
288 variables → 288 + 288*287/2 ≈ 41616 extended variables.
256 equations → extended to include quadratic relations.

If extended rank < extended variables → solutions exist.
If solutions are CONSISTENT (y_{ij} = x_i·x_j) → real collision.

OUR method: not standard Macaulay (which is generic).
We use CARRY STRUCTURE: only products within carry chains matter.
Carry: c_{i+1} = a_i·b_i ⊕ (a_i⊕b_i)·c_i — only ADJACENT products.
This is SPARSE quadratic — far fewer monomials than generic.
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def partial_wang_with_free(W0, W1, DW0, DW_free):
    """Partial Wang: 8 zeros, DW[10..15] free."""
    Wn = [W0, W1] + [0]*14
    DWs = [0]*16; DWs[0] = DW0
    Wf_tmp = [(Wn[i]+DWs[i])&MASK for i in range(16)]
    sn = sha256_rounds(Wn, 3); sf = sha256_rounds(Wf_tmp, 3)
    DWs[2] = (-de(sn, sf, 3)) & MASK
    for step in range(7):
        wi=step+3; dt=step+4
        Wfc=[(Wn[i]+DWs[i])&MASK for i in range(16)]
        tn=sha256_rounds(Wn,dt); tf=sha256_rounds(Wfc,dt)
        DWs[wi]=(-de(tn,tf,dt))&MASK
    for i in range(6): DWs[10+i]=DW_free[i]
    Wf=[(Wn[i]+DWs[i])&MASK for i in range(16)]
    return Wn, Wf, DWs

def numerical_quadratic_jacobian(W0, W1, DW0, DW_free, n_input_bits=64):
    """
    Build QUADRATIC Jacobian: include linear AND pairwise product terms.

    Instead of J[output_bit][input_bit],
    build J_ext[output_bit][input_bit OR input_bit_pair].

    For efficiency: use only first n_input_bits of the 288 total.
    """
    # Base computation
    Wn, Wf, _ = partial_wang_with_free(W0, W1, DW0, DW_free)
    Hn = sha256_compress(Wn); Hf = sha256_compress(Wf)
    dH_base = []
    for w in range(8):
        d=Hn[w]^Hf[w]
        for b in range(32): dH_base.append((d>>b)&1)
    dH_base = np.array(dH_base, dtype=np.int64)

    # Function to flip input bit and get δH change
    def flip_and_measure(bit_idx):
        """Flip one of the 288 input bits, return δH change vector."""
        W0p, W1p, DW0p, DWfp = W0, W1, DW0, list(DW_free)

        if bit_idx < 32:  # W0
            W0p = W0 ^ (1 << bit_idx)
        elif bit_idx < 64:  # W1
            W1p = W1 ^ (1 << (bit_idx-32))
        elif bit_idx < 96:  # DW0
            DW0p = DW0 ^ (1 << (bit_idx-64))
            if DW0p == 0: DW0p = 1
        else:  # DW[10..15]
            dw_word = (bit_idx - 96) // 32
            dw_bit = (bit_idx - 96) % 32
            DWfp[dw_word] ^= (1 << dw_bit)

        Wn_p, Wf_p, _ = partial_wang_with_free(W0p, W1p, DW0p, DWfp)
        Hn_p=sha256_compress(Wn_p); Hf_p=sha256_compress(Wf_p)
        dH_p = []
        for w in range(8):
            d=Hn_p[w]^Hf_p[w]
            for b in range(32): dH_p.append((d>>b)&1)
        return np.array(dH_p, dtype=np.int64) ^ dH_base

    # Linear Jacobian
    n = min(n_input_bits, 288)
    J_lin = np.zeros((n, 256), dtype=np.int64)
    for i in range(n):
        J_lin[i] = flip_and_measure(i)

    # Quadratic: flip TWO bits simultaneously, compare with single flips
    # (f(x⊕ei⊕ej) ⊕ f(x⊕ei) ⊕ f(x⊕ej) ⊕ f(x)) = quadratic term
    n_pairs = min(n * (n-1) // 2, 2000)  # Limit for speed

    J_quad_rows = []
    pair_indices = []
    count = 0

    for i in range(n):
        if count >= n_pairs: break
        for j in range(i+1, n):
            if count >= n_pairs: break

            # Flip both i and j
            W0p, W1p, DW0p, DWfp = W0, W1, DW0, list(DW_free)

            for bit_idx in [i, j]:
                if bit_idx < 32:
                    W0p ^= (1 << bit_idx)
                elif bit_idx < 64:
                    W1p ^= (1 << (bit_idx-32))
                elif bit_idx < 96:
                    DW0p ^= (1 << (bit_idx-64))
                else:
                    dw_word = (bit_idx-96)//32
                    dw_bit = (bit_idx-96)%32
                    DWfp[dw_word] ^= (1 << dw_bit)

            if DW0p == 0: DW0p = 1

            Wn_p,Wf_p,_ = partial_wang_with_free(W0p,W1p,DW0p,DWfp)
            Hn_p=sha256_compress(Wn_p); Hf_p=sha256_compress(Wf_p)
            dH_both = []
            for w in range(8):
                d=Hn_p[w]^Hf_p[w]
                for b in range(32): dH_both.append((d>>b)&1)
            dH_both = np.array(dH_both, dtype=np.int64)

            # Quadratic contribution = f(x+ei+ej) ⊕ f(x+ei) ⊕ f(x+ej) ⊕ f(x)
            quad_row = (dH_both ^ J_lin[i] ^ J_lin[j] ^ dH_base) ^ dH_base
            # Simplify: quad = dH_both ⊕ dH_i ⊕ dH_j (all relative to base)
            quad_row = dH_both ^ (dH_base ^ J_lin[i]) ^ (dH_base ^ J_lin[j]) ^ dH_base
            # Actually: f(x+ei+ej) - f(x) = [f(x+ei)-f(x)] + [f(x+ej)-f(x)] + quad
            # So: quad = [f(x+ei+ej)⊕f(x)] ⊕ [f(x+ei)⊕f(x)] ⊕ [f(x+ej)⊕f(x)]
            quad_row = dH_both ^ J_lin[i] ^ J_lin[j]

            J_quad_rows.append(quad_row)
            pair_indices.append((i, j))
            count += 1

    return J_lin, np.array(J_quad_rows) if J_quad_rows else np.zeros((0,256)), dH_base

def test_quadratic_structure(N=20):
    """How much does the quadratic term contribute?"""
    print("\n--- TEST 1: QUADRATIC vs LINEAR CONTRIBUTION ---")

    for trial in range(min(N, 5)):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        DW0=random.randint(1,MASK)
        DW_free=[random.randint(0,MASK) for _ in range(6)]

        J_lin, J_quad, dH_base = numerical_quadratic_jacobian(
            W0, W1, DW0, DW_free, n_input_bits=64)

        lin_hw = np.mean([hw_bits(row) for row in J_lin])
        quad_hw = np.mean([hw_bits(row) for row in J_quad]) if len(J_quad)>0 else 0

        lin_rank = np.linalg.matrix_rank(J_lin.astype(float))

        if len(J_quad) > 0:
            # Combined rank
            J_combined = np.vstack([J_lin, J_quad])
            comb_rank = np.linalg.matrix_rank(J_combined.astype(float))
            quad_fraction = quad_hw / (lin_hw + 1e-10)
        else:
            comb_rank = lin_rank
            quad_fraction = 0

        print(f"  Trial {trial}: lin_rank={lin_rank}, combined_rank={comb_rank}, "
              f"quad/lin ratio={quad_fraction:.4f}")

def hw_bits(arr):
    return np.sum(arr != 0)

def test_quadratic_solve(N=50):
    """
    Attempt to solve using BOTH linear and quadratic terms.

    Strategy:
    1. Build extended system: [J_lin; J_quad] · x_ext = target
    2. Solve in GF(2)
    3. Check consistency: are quadratic solutions y_{ij} = x_i·x_j?
    4. Apply to real SHA-256 and measure residual
    """
    print(f"\n--- TEST 2: QUADRATIC SOLVE (N={N}) ---")

    residuals_lin = []
    residuals_quad = []

    for trial in range(N):
        W0=random.randint(0,MASK); W1=random.randint(0,MASK)
        DW0=random.randint(1,MASK)
        DW_free=[random.randint(0,MASK) for _ in range(6)]

        J_lin, J_quad, dH_base = numerical_quadratic_jacobian(
            W0, W1, DW0, DW_free, n_input_bits=96)

        target = dH_base.copy()  # Want to flip these bits to 0

        # LINEAR solve (96 vars, 256 eqs)
        Jt = J_lin.T % 2  # 256 × 96
        Aug = np.hstack([Jt, target.reshape(-1,1)]).astype(np.int64) % 2
        m,n1 = Aug.shape; n=n1-1
        rank=0
        for col in range(n):
            pivot=-1
            for row in range(rank,m):
                if Aug[row,col]%2==1: pivot=row; break
            if pivot==-1: continue
            Aug[[rank,pivot]]=Aug[[pivot,rank]]
            for row in range(m):
                if row!=rank and Aug[row,col]%2==1:
                    Aug[row]=(Aug[row]+Aug[rank])%2
            rank+=1

        x_lin = np.zeros(n, dtype=np.int64)
        piv=0
        for col in range(n):
            if piv<m and Aug[piv,col]%2==1:
                x_lin[col]=Aug[piv,-1]%2; piv+=1

        # Apply linear solution
        W0l,W1l,DW0l,DWfl = W0,W1,DW0,list(DW_free)
        for i in range(96):
            if x_lin[i]==1:
                if i<32: W0l^=(1<<i)
                elif i<64: W1l^=(1<<(i-32))
                else: DW0l^=(1<<(i-64))
        if DW0l==0: DW0l=1

        Wn_l,Wf_l,_=partial_wang_with_free(W0l,W1l,DW0l,DWfl)
        Hn_l=sha256_compress(Wn_l); Hf_l=sha256_compress(Wf_l)
        res_lin=sum(hw(Hn_l[w]^Hf_l[w]) for w in range(8))
        residuals_lin.append(res_lin)

        # QUADRATIC solve: use quad terms as additional equations
        if len(J_quad) > 0:
            # Extended variable: x_ext = [x_1,...,x_n, x_1·x_2, x_1·x_3, ...]
            # Additional equations from quadratic: sum of quad_row·x_pairs = 0
            # For simplicity: use quad rows as additional CONSTRAINTS on x
            # Augment: stack linear and quadratic
            n_q = min(len(J_quad), 200)
            J_aug = np.vstack([J_lin[:96], J_quad[:n_q]])  # (96+n_q) × 256
            target_aug = np.concatenate([target, np.zeros(n_q, dtype=np.int64)])

            # Solve augmented system
            Jat = J_aug.T % 2  # 256 × (96+n_q)
            Aug2 = np.hstack([Jat, target.reshape(-1,1)]).astype(np.int64) % 2
            m2,n2=Aug2.shape; nn=n2-1
            rank2=0
            for col in range(min(nn,256)):
                pivot=-1
                for row in range(rank2,m2):
                    if Aug2[row,col]%2==1: pivot=row; break
                if pivot==-1: continue
                Aug2[[rank2,pivot]]=Aug2[[pivot,rank2]]
                for row in range(m2):
                    if row!=rank2 and Aug2[row,col]%2==1:
                        Aug2[row]=(Aug2[row]+Aug2[rank2])%2
                rank2+=1

            x_quad = np.zeros(nn, dtype=np.int64)
            piv=0
            for col in range(nn):
                if piv<m2 and Aug2[piv,col]%2==1:
                    x_quad[col]=Aug2[piv,-1]%2; piv+=1

            # Apply (only first 96 bits correspond to our variables)
            W0q,W1q,DW0q,DWfq = W0,W1,DW0,list(DW_free)
            for i in range(min(96,nn)):
                if x_quad[i]==1:
                    if i<32: W0q^=(1<<i)
                    elif i<64: W1q^=(1<<(i-32))
                    else: DW0q^=(1<<(i-64))
            if DW0q==0: DW0q=1

            Wn_q,Wf_q,_=partial_wang_with_free(W0q,W1q,DW0q,DWfq)
            Hn_q=sha256_compress(Wn_q); Hf_q=sha256_compress(Wf_q)
            res_quad=sum(hw(Hn_q[w]^Hf_q[w]) for w in range(8))
            residuals_quad.append(res_quad)

    rl=np.array(residuals_lin)
    rq=np.array(residuals_quad) if residuals_quad else np.array([128])

    print(f"Linear solve residual:    E[δH]={rl.mean():.2f}, min={rl.min()}")
    print(f"Quadratic solve residual: E[δH]={rq.mean():.2f}, min={rq.min()}")
    print(f"Improvement quad vs lin:  {rl.mean()-rq.mean():+.2f}")

    if rq.mean() < rl.mean() - 5:
        print(f"*** QUADRATIC SOLVE IMPROVES! ***")
    if rq.min() < 50:
        print(f"*** NEAR-COLLISION from quadratic solve! ***")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 50: QUADRATIC CARRY SOLVE")
    print("Macaulay linearization of carry constraints")
    print("="*60)
    test_quadratic_structure(5)
    test_quadratic_solve(30)

    print("\n"+"="*60)
    print("VERDICT")
    print("="*60)

if __name__ == "__main__":
    main()
