# Статус программы (снимок)

Короткий AI-оптимизированный срез: что доказано, что закрыто, что открыто.

## ДОКАЗАНО (неопровержимо)

### SHA-256 криптоанализ (Том II)
1. **T_ADD8** ✓DOK — W_SAT3 приводит к De3=0 за O(2²²) [П-2/П-4]
2. **T_CASCADE_MAX** ✓DOK — ΔW[3..15] дают 14 нулей De за O(2²²) [П-10]
3. **T_DE17_LINEAR** ✓DOK — De17 = Da13 + ΔW16 (аналитическое разложение) [П-11/П-12]
4. **T_SCHEDULE_DECOUPLING** ✓DOK — De_r зависит только от W[0..r-1] [П-9]
5. **T_WANG_CHAIN** ⚡VER — δe2..δe16=0 с P=1.0 (1000/1000) [П-26/П-92]
6. **Wang pair W0=c97624c6** ⚡VER — физически найдена (518s) [П-97]
7. **T_BARRIER_EQUALS_SCHEDULE** ✓DOK — барьер r=17 = schedule_barrier+1 [П-114]
8. **T_CH_INVARIANT** ✓DOK — Ch[b30,b31]=0 при carry[63]=0 строго (0/1M) [П-966]
9. **T_RANK5_INVARIANT** ✓DOK — rank_GF2(J_{5×15})=5 абсолютный [П-58]
10. **T_INFINITE_TOWER** ⚡VER — slope=1.000 до k=24 (200 сидов); height_2 ≥ **32** (финал, после П-67B) [П-59, П-67B]
11. **T_BIRTHDAY_COST17** ✓DOK — оптимум 2¹²⁸ [П-27A]
12. **T_SC_A1** ⚡VER — sufficient condition δa1=0x8000 (100000/100000) [П-24]
13. **T_JOINT_SC** ✓DOK — [П-24]
14. **T_WANG_ADAPTIVE** ⚡VER — (50000/50000) [П-25]

### Математика бита (Том I)
15. **Аксиомы D1-D5** ✓DOK — 20/20 осей pass, binary fails D5 [§28]
16. **Plurality Theorem (D3)** ✓DOK (negative) — нет universal framework для 13 primitives, но 6 sub-frameworks [§29]
17. **Upper bound (D5)** ✓DOK (negative) — N=∞ под D1-D5 [§30.3]
18. **General Discrimination Theorem** ✓DOK — phase-bits различают классы функций [§45]
19. **Z/m phase hierarchy** ✓DOK — m^(k-1) scaling [§46]
20. **XOR-fragility theorem** ✓DOK — XOR неустойчив в некоторых расширениях [§42]
21. **No-cloning для phase bits** ✓DOK [§5.6 L2]
22. **Theorem 7 (SuperBit exponential DISCRIM-DETECT)** ✓DOK [§67]
23. **Diagonal conjugacy universal on real SHA-256** ⚡VER [§119-C]
24. **W-atlas law ΔW ∝ 1/N_ADD** ⚡VER [§123]

### Info-Theory (Том III)
25. **χ²-fingerprint SHA-2 family** ⚡VER — z≈-2.5, p<10⁻⁷ [IT-1.3]
26. **σ₀/σ₁ главный вклад (88%)** ⚡VER [IT-2]
27. **Δ_χ² vs Δ_I dissociation** ⚡VER [IT-3]
28. **HW=2 exclusivity bit5_max** ⚡VER — exhaustive 130K [IT-4.1]
29. **Directional chain-3 signal** ⚡VER — p=0.002 Bonferroni [IT-4.Q7DEF]
30. **ρ(direct, chain_3) = +0.98** ⚡VER — same-sign 240/256 (one-sided binomial p~10⁻⁵²) [IT-6]

## ЗАКРЫТО (не повторять)

### Том II
- **T_HENSEL_INAPPLICABLE** ✗NEG — 2-адическая гладкость нарушена k≥2 [П-43]
- **T_NONLINEAR_MATRIX_FAILS** ✗NEG — исчерпывающий 2D подъём, 0/100 [П-44]
- **T_BOOMERANG_INFEASIBLE** ✗NEG — HW≈64, без структуры [П-29]
- **T_ROTATIONAL_NEGATIVE** ✗NEG — rotational differentials не дают преимущества [П-35]
- **T_MILP_INFEASIBLE_17** ✗NEG — SAT k≤16 мгновенно, k=17 timeout [П-34]
- **Wang в мультиблоке** ✗NEG — predict_delta не расширяется
- **Многоаттрактор P-36..P-41** ✗NEG — ротационный аттрактор опровергнут

### Том I
- **Memristor как примитив** ✗NEG — не проходит D1-D5 [§39]
- **S-bit на оптимизации (QUBO/MAX-SAT)** ✗NEG — не превосходит классику [§59]
- **Σ-bit супер-примитив** ✗NEG — недостаточно мощен [§61]
- **Avalanche wall R=1 real SHA** ✗NEG — не инвертируется раунд напрямую [§111]
- **Scalar МС-координаты** ✗NEG — все 16 кандидатов NULL [§125]
- **Vector валидация k=32** ✗NEG — все NULL [§126]
- **Stacked disqualifiers** ✗NEG — 3-5% маргинально [§131]
- **Tropical numpy vs scipy** ✗NEG — speedup был python artifact [§35]

### Том III
- **bit5_max как HW-parity** ✗NEG — эффект HW=2 exclusive, не чётность [IT-4.1]
- **2nd-order Walsh на state1** ✗NEG — RO-clean [IT-4.Q7]
- **Linear max\|z\| для распределённых сигналов** ✗NEG — недостаточен [IT-5G]

### Отозваны (⊘ROLL)
- **T_FREESTART_INFINITE_TOWER** ⊘ROLL → исправл. П-67 (DW=0 тривиально)
- **T_FULLSTATE_FREESTART_TOWER** ⊘ROLL [П-63-64]
- **T_DA_ODD_BIAS** ⊘ROLL → П-108 (T_DA_BIAS_ZERO)
- **T_HEIGHT_SHA256=6** ⊘ROLL — опровергнута; пересмотр: height₂ ≥ 11 (П-53) → ≥ 24 (П-59) → **≥ 32** (финал, П-67B)

## ОТКРЫТО (направления для работы)

### Вопросы первой категории (техника)
- **Sol_17 плотность neutral bits** ?OPEN — точно ≥2⁹⁶, стоимость обхода?
- **MITM O(2⁸⁰) реализация** ?OPEN — теоретическая, требует code [П-210]
- **Extension Wang-chain за r=17** ?OPEN — пока стена
- **Backward shortcut beyond ANF early-verify** ?OPEN — 7.6× пока потолок [§132/§133]
- **Open 119-C** ?OPEN — Φ-inverter fails на конкретных инстансах, но diagonal conjugacy универсальна [§120]
- **W-атлас обобщение на non-ADD функции** ?OPEN [§123]

### Вопросы структуры
- **22+ ось бита** ?OPEN — stochastic resonance, field bits кандидаты [§38-39]
- **5-я метагруппа (вне VAL/OP/REL/TIME)** ?OPEN [§40]
- **Path-bit computational separation** ?OPEN — формализация через Hopf [§80-84]
- **Bit-cosmos Platonic multi-axis** ?OPEN — как уложить в формальную теорию [§90-93]
- **Конечная верхняя граница осей при усилении аксиом** ?OPEN [§30]

### Info-Theory
- **Ω_k для других хэшей** ?OPEN — применить к SHA-3, BLAKE [IT-6]
- **Signal amplification у block-2** ?OPEN — механизм изучен, можно использовать [IT-4.S4]
- **Chain-test против quantum distinguishers** ?OPEN

## ТЕКУЩАЯ ФРОНТЬЕРНАЯ ЗАДАЧА

**Главный фокус** (по состоянию на апрель 2026):
1. Backward shortcut extension за пределы ANF early-verify (7.6×)
2. Реализация MITM O(2⁸⁰) как runnable code
3. Применение Ω_k/chain-test к SHA-3 как cross-hash фингерпринт

## Построенные инструменты (можно использовать)

- `superbit/` — SAT engine v1.0, σ-feedback, WalkSAT интеграции
- `research/min_entropy/sharp_analysis.py` — χ² fingerprint скан 7 хэшей
- `it4_walsh.py` + `it4_q7*_*` — Walsh chain-test с amplification
- `it6_full_output_map.py` — Ω_k инвариант по 256 битам
- `it7*` — collision probes, Wang-based, stratified
- `it8-9*.c` — cascade amplify, full-SHA, twoblock probes
- `sha256_chimera.py` — смешанные хэш-семьи
- Distinguisher v6.0 (neural, AUC=0.980) — в архиве П-1000..
