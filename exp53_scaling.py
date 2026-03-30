#!/usr/bin/env python3
"""
EXP 53: J-CAIR Scaling Analysis

exp52: J-CAIR beats random by 2 bits at N=144K.
Question: how does advantage SCALE with budget?

Also: what causes PLATEAU? And can we break through it?

Strategy:
1. Measure advantage at multiple budgets (1K, 10K, 100K, 1M)
2. Identify plateau onset — at which step does CAIR stop improving?
3. Test anti-plateau techniques: restarts, perturbation, temperature
4. Measure Jacobian accuracy p (fraction of correct predictions)
"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from sha256_core import *

def dH_pair(W16, DW16):
    Wf=[(W16[i]+DW16[i])&MASK for i in range(16)]
    Hn=sha256_compress(W16); Hf=sha256_compress(Wf)
    return sum(hw(Hn[i]^Hf[i]) for i in range(8))

def cair_step(W16, DW16, n_cand=30):
    cur = dH_pair(W16, DW16)
    best_imp = 0; best_W = W16; best_DW = DW16

    for _ in range(n_cand):
        # Flip random bit in DW or W
        if random.random() < 0.7:
            w=random.randint(0,15); b=random.randint(0,31)
            DW_n=list(DW16); DW_n[w]^=(1<<b)
            if DW_n[0]==0: DW_n[0]=1
            try:
                d = dH_pair(W16, DW_n)
                if cur-d > best_imp:
                    best_imp=cur-d; best_DW=DW_n; best_W=W16
            except: pass
        else:
            w=random.randint(0,15); b=random.randint(0,31)
            W_n=list(W16); W_n[w]^=(1<<b)
            try:
                d = dH_pair(W_n, DW16)
                if cur-d > best_imp:
                    best_imp=cur-d; best_DW=DW16; best_W=W_n
            except: pass

    return best_W, best_DW, cur-best_imp

def jscore_step(W16, DW16, n_jac=50, n_ver=15):
    """J-scored step: compute Jacobian scores, verify top candidates."""
    Wf=[(W16[i]+DW16[i])&MASK for i in range(16)]
    Hn=sha256_compress(W16); Hf=sha256_compress(Wf)
    base=[]
    for w in range(8):
        d=Hn[w]^Hf[w]
        for b in range(32): base.append((d>>b)&1)
    base=np.array(base); cur=int(base.sum())

    candidates=random.sample(range(512), min(n_jac, 512))
    scores={}

    for bi in candidates:
        w=bi//32; b=bi%32
        DW_p=list(DW16); DW_p[w]^=(1<<b)
        if DW_p[0]==0: DW_p[0]=1
        try:
            Wf_p=[(W16[i]+DW_p[i])&MASK for i in range(16)]
            Hn_p=sha256_compress(W16); Hf_p=sha256_compress(Wf_p)
            p_bits=[]
            for ww in range(8):
                d=Hn_p[ww]^Hf_p[ww]
                for bb in range(32): p_bits.append((d>>bb)&1)
            col=np.array(p_bits)^base
            fix=int(np.sum(col&base)); brk=int(np.sum(col&(1-base)))
            scores[bi]=fix-brk
        except: pass

    ranked=sorted(scores.items(), key=lambda x:-x[1])
    best_imp=0; best_DW=DW16

    for bi,sc in ranked[:n_ver]:
        w=bi//32; b=bi%32
        DW_p=list(DW16); DW_p[w]^=(1<<b)
        if DW_p[0]==0: DW_p[0]=1
        try:
            d=dH_pair(W16,DW_p)
            if cur-d>best_imp:
                best_imp=cur-d; best_DW=DW_p
        except: pass

    return W16, best_DW, cur-best_imp

def run_jcair(budget_evals):
    """Run J-CAIR with given eval budget. Return best δH."""
    n_starts = max(1, budget_evals // 5000)
    steps = budget_evals // (n_starts * 50)

    best = 256
    for _ in range(n_starts):
        W16=random_w16()
        DW16=[random.randint(0,MASK) for _ in range(16)]
        DW16[0]=max(DW16[0],1)
        stuck=0

        for step in range(steps):
            old=dH_pair(W16,DW16) if step==0 else dH_cur
            if step%3==0:
                W16,DW16,dH_cur=jscore_step(W16,DW16,n_jac=40,n_ver=12)
            else:
                W16,DW16,dH_cur=cair_step(W16,DW16,n_cand=25)
            best=min(best,dH_cur)

            if dH_cur>=old: stuck+=1
            else: stuck=0
            if stuck>30:
                for i in range(16): DW16[i]^=random.randint(0,0xFFFF)
                DW16[0]=max(DW16[0],1); stuck=0

    return best

def run_random(budget_evals):
    """Pure random search with given eval budget."""
    best=256
    for _ in range(budget_evals):
        W16=random_w16()
        DW16=[random.randint(0,MASK) for _ in range(16)]
        DW16[0]=max(DW16[0],1)
        try:
            best=min(best,dH_pair(W16,DW16))
        except: pass
    return best

def test_scaling():
    """Measure advantage at multiple budgets."""
    print("\n--- SCALING ANALYSIS ---")

    budgets = [2000, 5000, 15000, 50000, 150000]
    n_trials = 5

    print(f"{'Budget':>8} | {'J-CAIR':>8} | {'Random':>8} | {'Birthday':>8} | {'Advantage':>9}")
    print("-"*55)

    for budget in budgets:
        jcair_bests = [run_jcair(budget) for _ in range(n_trials)]
        random_bests = [run_random(budget) for _ in range(n_trials)]

        jm = np.mean(jcair_bests); rm = np.mean(random_bests)
        birthday = 128 - 8*np.sqrt(2*np.log(budget))
        adv = rm - jm

        print(f"{budget:>8} | {jm:>8.1f} | {rm:>8.1f} | {birthday:>8.1f} | {adv:>+9.1f}")

def test_plateau_analysis(max_steps=500, N=5):
    """When does CAIR plateau?"""
    print(f"\n--- PLATEAU ANALYSIS ---")

    for run in range(N):
        W16=random_w16()
        DW16=[random.randint(0,MASK) for _ in range(16)]
        DW16[0]=max(DW16[0],1)
        best=dH_pair(W16,DW16)
        milestones=[]

        for step in range(max_steps):
            if step%3==0:
                W16,DW16,dH=jscore_step(W16,DW16,n_jac=40,n_ver=12)
            else:
                W16,DW16,dH=cair_step(W16,DW16,n_cand=25)
            best=min(best,dH)
            if step in [10,25,50,100,200,300,400,499]:
                milestones.append((step,best))

        progress = ' '.join(f's{s}:{b}' for s,b in milestones)
        print(f"  Run {run+1}: {progress}")

def test_jacobian_accuracy(N=1000):
    """Measure: what fraction of J-scored predictions are correct?"""
    print(f"\n--- JACOBIAN ACCURACY ---")

    correct=0; total=0

    for _ in range(N):
        W16=random_w16()
        DW16=[random.randint(0,MASK) for _ in range(16)]
        DW16[0]=max(DW16[0],1)

        Wf=[(W16[i]+DW16[i])&MASK for i in range(16)]
        Hn=sha256_compress(W16); Hf=sha256_compress(Wf)
        base=[]
        for w in range(8):
            d=Hn[w]^Hf[w]
            for b in range(32): base.append((d>>b)&1)
        base=np.array(base); cur=int(base.sum())

        # Pick a random bit flip
        bi=random.randint(0,511)
        w=bi//32; b=bi%32
        DW_p=list(DW16); DW_p[w]^=(1<<b)
        if DW_p[0]==0: DW_p[0]=1

        try:
            # Jacobian prediction
            Wf_p=[(W16[i]+DW_p[i])&MASK for i in range(16)]
            Hf_p=sha256_compress(Wf_p)
            p_bits=[]
            for ww in range(8):
                d=Hn[ww]^Hf_p[ww]
                for bb in range(32): p_bits.append((d>>bb)&1)
            col=np.array(p_bits)^base
            fix=int(np.sum(col&base)); brk=int(np.sum(col&(1-base)))
            j_score = fix-brk  # >0 predicts improvement

            # Actual result
            actual_dH = dH_pair(W16, DW_p)
            actual_improved = actual_dH < cur

            j_predicted_improve = j_score > 0
            if j_predicted_improve == actual_improved:
                correct += 1
            total += 1
        except: pass

    accuracy = correct/total if total>0 else 0
    print(f"Jacobian prediction accuracy: {correct}/{total} = {accuracy:.4f}")
    print(f"Random baseline: 0.5000")
    print(f"Advantage: {accuracy-0.5:+.4f}")

def main():
    random.seed(42)
    print("="*60)
    print("EXP 53: J-CAIR SCALING ANALYSIS")
    print("="*60)
    test_jacobian_accuracy(800)
    test_plateau_analysis(400, 5)
    test_scaling()

if __name__ == "__main__":
    main()
