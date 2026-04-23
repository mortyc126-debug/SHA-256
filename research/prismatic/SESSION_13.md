# Session 13: Rotation action on H¹

**Дата**: 2026-04-22
**Цель Session 12 переданная**: integrate XOR via tensor R_rot ⊗ R_bool.

## Pivot (меньший scope)

Вместо amidancing к tensor products сразу, Session 13 сначала изучает **как rotation acts на H¹ of rotation ring**. Это более concrete.

## Главный результат — THEOREM

**Theorem (Session 13)**: Для R = F_2[s]/(s^n) с n = 2^k:
$$\text{Multiplication by } (1+s) \text{ acts as IDENTITY on } H^1_{dR}(R).$$

Более полно: ROTR_r = mult by (1+s)^r. ROTR_r acts identity on H¹ **iff r = 1**.

## Доказательство

**Action на generator [s^k · ds]** (для k odd, Session 10 basis):

$$(1+s) \cdot [s^k \cdot ds] = [s^k \cdot ds] + [s^{k+1} \cdot ds]$$

Для k odd, k+1 even. По Session 10 theorem: position k+1 даёт contribution Z/2^{v_2(k+2)}. Поскольку k+2 = odd+2 = odd, v_2(k+2) = 0. Так что [s^{k+1} · ds] = 0 в H¹.

**Следовательно**: (1+s) · [s^k · ds] = [s^k · ds] для всех odd k. **Identity on H¹**.

QED для r = 1.

**Для r > 1**: (1+s)^r expanded via Lucas's theorem в char 2:
$$(1+s)^r = \sum_{i: \text{binary}(i) \subseteq \text{binary}(r)} s^i$$

Action sends [s^k · ds] → [s^k · ds] + Σ_{i ⊂ r, i > 0} [s^{k+i} · ds].

Для identity: нужно все [s^{k+i} · ds] = 0, т.е. k+i even для всех i ⊂ r (i > 0).
Поскольку k odd: нужно i odd для всех i ⊂ r (i > 0).
Equivalently: каждый non-empty subset of r's binary bits contains LSB.
Это только если r has ONLY bit 0 set, т.е. r = 1.

QED.

## Numerical verification for n = 32

ROTR_r expansions (via Lucas):

| r | (1+s)^r non-zero positions | Non-identity (even) positions |
|---|---|---|
| 1 | {0, 1} | ∅ |
| 2 | {0, 2} | {2} |
| 3 | {0, 1, 2, 3} | {2} |
| 4 | {0, 4} | {4} |
| 8 | {0, 8} | {8} |
| 16 | {0, 16} | {16} |

Only r = 1 has no non-identity contributions. All other r ≥ 2 act non-trivially.

## Implications

### For SHA-256 Σ_0, Σ_1, σ_0, σ_1

SHA uses ROTR_r для r ∈ {2, 6, 7, 11, 13, 17, 18, 19, 22, 25}. All **≥ 2**.

Следовательно **все SHA rotations act non-trivially на H¹**. Каждая ROTR_r mixes cohomology classes. 

Σ_0(x) = ROTR_2(x) ⊕ ROTR_13(x) ⊕ ROTR_22(x):
- Каждый ROTR_r acts як Z_2-module automorphism of R
- Σ_0 = XOR trek = Z_2-linear combination of three maps
- Induced на H¹: specific linear map, computable по мере необходимости

### "Blind spot" of H¹: ROTR_1 orbits

Любые два элемента в one ROTR_1-orbit дают **same cohomology class**. Это partial information loss:
- H¹ не может distinguish x and ROTR_1(x) and ROTR_1²(x) ...
- Orbit size = 32 (order of ROTR_1)
- H¹ коллапсирует orbits → sees R / ROTR_1-orbit = R / (cyclic shift)

**Для SHA**: так как SHA uses ROTR_r for r ≥ 2, это не direct issue. H¹ distinguishes these.

## Что ещё нужно для полной SHA-картинки

1. **XOR as Z_2-module operation**: SHA XORs multiple things. At cohomology level, XOR of r values of ROTR gives sum map.

2. **AND via Ch, Maj**: AND действует НЕ через rotation ring. Требует separate structure (boolean ring) или derived approach.

3. **ADD mod 2^32**: respects δ-structure (Session 6). Acts как ring operation на Z_2-lift.

## Session 14 target

**Concrete**: compute action of Σ_0 (XOR of three ROTR) on H¹(F_2[s]/(s^32)).

Эта матрица показывает как SHA's Σ_0 mixes 16 cyclic factors of H¹. Размер = 16 × 16 over Z_2. Should be implementable.

Если эта матрица имеет **non-trivial kernel**, находим **invariants of Σ_0** — reduced classification space.

## Status

- ✓ Theorem proven: ROTR_1 = id on H¹, ROTR_r (r ≥ 2) non-trivial
- ✓ Clear understanding rotation spectrum: only trivial orbit is r=1
- ✓ SHA rotations (r ≥ 2) all non-trivial on H¹
- → Session 14: compute Σ_0 matrix на H¹

## Honest reflection

Session 13 — **clean theorem**. Action of ROTR_1 на H¹ = identity. Nice result, but partial:
- Shows cohomology "forgets" cyclic-by-1 structure
- But SHA uses bigger rotations, non-trivial on H¹

**Realistic**: Session 14 computes matrix Σ_0: H¹ → H¹. 16×16 matrix over Z_2. Doable.

Sessions 15+ integrate other ops. Still long path к полной SHA analysis.

## Artifacts

- `session_13_rotation_action.py` — computation of action
- `SESSION_13.md` — this file
