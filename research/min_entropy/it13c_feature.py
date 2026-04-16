"""IT-13c: just feature-scan at K=130K (Arm 2 of IT-13b that died)."""
import hashlib, json, math, os, subprocess, tempfile, time
from itertools import combinations
from math import comb
import numpy as np
import sha256_chimera as ch

WORDS = 2048
N_TOP = 24
HERE = os.path.dirname(os.path.abspath(__file__))
C_BIN = os.path.join(HERE, 'it4_q7d_chain3')
OUT = os.path.join(HERE, 'it13c_feature.json')

def low_hw2():
    inputs, pos = [], []
    for p in combinations(range(512), 2):
        b = bytearray(64)
        for q in p: b[q >> 3] |= 1 << (q & 7)
        inputs.append(bytes(b)); pos.append(p)
    return inputs, pos

def sbits(state, N):
    bits = np.zeros((N, 256), dtype=np.uint8)
    for w in range(8):
        for b in range(32):
            bits[:, w*32+b] = ((state[:, w] >> np.uint32(31-b)) & 1).astype(np.uint8)
    return bits

def pack(v):
    pad = np.zeros(WORDS*64, dtype=np.uint8); pad[:len(v)] = v
    return np.frombuffer(np.packbits(pad, bitorder='little').tobytes(), dtype=np.uint64)

def feat(pos, name):
    mp = np.asarray([p[-1] for p in pos]); ip = np.asarray([p[0] for p in pos])
    return {'bit5_max': ((mp>>5)&1).astype(np.uint8),
            'bit4_max': ((mp>>4)&1).astype(np.uint8),
            'bit6_max': ((mp>>6)&1).astype(np.uint8),
            'parity_lsb': ((ip&1)^(mp&1)).astype(np.uint8),
            'mid_bit3':  (((mp+ip)>>3)&1).astype(np.uint8)}[name]

def runc(K, s1b, fa, ta, p):
    with open(p,'wb') as fp:
        fp.write(np.uint64(K).tobytes())
        for b in range(256): fp.write(pack(s1b[:K,b]).tobytes())
        fp.write(pack(fa[:K]).tobytes()); fp.write(pack(ta[:K]).tobytes())
    return json.loads(subprocess.run([C_BIN, p], capture_output=True, text=True, check=True).stdout)

def binom_p(k, n):
    if k < n-k: k = n-k
    return 2*sum(comb(n,i) for i in range(k,n+1))/(1<<n)

def main():
    t0 = time.time()
    inputs, pos = low_hw2(); N = len(inputs)
    M = np.frombuffer(b''.join(inputs), dtype=np.uint8).reshape(N,64)
    b1 = M.view('>u4').reshape(N,16).astype(ch.U32)
    s1 = ch.compress(np.broadcast_to(ch.IV_VANILLA,(N,8)).copy(), b1, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    pad=bytearray(64); pad[0]=0x80; pad[-8:]=(512).to_bytes(8,'big')
    b2 = np.frombuffer(bytes(pad),dtype=np.uint8).view('>u4').reshape(1,16).astype(ch.U32)
    b2 = np.broadcast_to(b2,(N,16))
    s2 = ch.compress(s1, b2, ch.VARIANTS['V0_vanilla'], ch.K_VANILLA)
    s1b, s2b = sbits(s1,N), sbits(s2,N)

    f0 = feat(pos, 'bit5_max')
    direct = np.zeros(256)
    for b in range(256):
        w = 1 - 2*((f0^s2b[:,b]).sum())/N
        direct[b] = w*math.sqrt(N)
    top = np.argsort(-np.abs(direct))[:N_TOP].tolist()
    print(f"# top-{N_TOP}: max|z|={abs(direct[top[0]]):.2f} min|z|={abs(direct[top[-1]]):.2f}")

    results = []
    for fname in ['bit4_max', 'bit6_max', 'parity_lsb', 'mid_bit3']:
        fa = feat(pos, fname)
        dz = np.zeros(N_TOP); cz = np.zeros(N_TOP)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as t: tp = t.name
        ts = time.time()
        for i,b in enumerate(top):
            tb = s2b[:,b]
            w = 1 - 2*((fa^tb).sum())/N
            dz[i] = w*math.sqrt(N)
            cz[i] = runc(N, s1b, fa, tb, tp)['chain_sum']
        os.unlink(tp)
        c = float(np.corrcoef(dz, cz)[0,1])
        ss = int((np.sign(dz)==np.sign(cz)).sum())
        p = binom_p(ss, N_TOP)
        print(f"  {fname:<12} Ω_3={c:+.4f}  ss={ss}/{N_TOP}  p={p:.2e}  t={time.time()-ts:.0f}s")
        results.append({'feature':fname,'corr':c,'ss':ss,'n':N_TOP,'p':p,
                        'direct_z':dz.tolist(),'chain_z':cz.tolist()})

    print("\n=== SUMMARY ===")
    print(f"{'feature':<12} {'Omega_3':>10} {'same_sign':>12} {'p':>12}")
    print(f"{'bit5_max(IT6)':<12} {0.9795:>+10.4f} {240:>5}/256       {1e-40:>12.0e}")
    print(f"{'bit5_max(IT13bA1)':<12} {0.9982:>+10.4f} {24:>5}/24        {1.19e-7:>12.2e}")
    for r in results:
        print(f"{r['feature']:<12} {r['corr']:>+10.4f} {r['ss']:>5}/{r['n']:<5}     {r['p']:>12.2e}")

    with open(OUT,'w') as f: json.dump({'results':results,'top_bits':top},f,indent=2)
    print(f"\nWrote {OUT}, total {time.time()-t0:.0f}s")

if __name__=='__main__': main()
