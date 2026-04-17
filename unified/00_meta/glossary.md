# Глоссарий

Единый словарь терминов по всем трём томам. Упорядочено алфавитно.

## SHA-256 примитивы

- **Ch(e,f,g)** = (e∧f) ⊕ (¬e∧g) — choice функция компрессии
- **Maj(a,b,c)** = (a∧b) ⊕ (a∧c) ⊕ (b∧c) — majority
- **Σ0(x)** = ROTR²(x) ⊕ ROTR¹³(x) ⊕ ROTR²²(x)
- **Σ1(x)** = ROTR⁶(x) ⊕ ROTR¹¹(x) ⊕ ROTR²⁵(x)
- **σ0(x)** = ROTR⁷(x) ⊕ ROTR¹⁸(x) ⊕ SHR³(x) — schedule
- **σ1(x)** = ROTR¹⁷(x) ⊕ ROTR¹⁹(x) ⊕ SHR¹⁰(x) — schedule
- **IV** — начальное состояние a..h[0], константы SHA-256
- **W[r]** — message schedule word на раунде r (0..63)
- **K[r]** — round constant
- **state[r]** = (a..h) на раунде r

## Дифференциалы (Том II)

- **δe_r** — additive differential e на раунде r (mod 2³²)
- **δW_r, ΔW_r** — дифференциал schedule word (XOR vs additive)
- **δa, δb..δh** — дифференциалы 8 регистров
- **δA** — набор (δa..δh) целиком
- **De_r** — дифференциал δe, сведённый к нулю (целевой)
- **Da_r** — дифференциал δa, аналогично
- **wf[r], wn[r]** — W-forward/W-needed в Wang-chain
- **Wang-chain** — δe2=...=δe16=0 с P=1.0 (ключевая атака)
- **neutral bits** — Λ=32 бита свободы в Sol_17

## Carry & phase space (Том I §114-123)

- **Φ (phi)** — carry variable, сопряжённая координата к bit-position
- **W** — скрытый бит, не видимый стандартными методами (Том I)
- **W-атлас** — эмпирический закон ΔW ∝ 1/N_ADD
- **carry-rank** — размер образа carry-out отображения (=589/592)
- **η** — spectral gap ≈ 0.189
- **τ★** — фундаментальная временная шкала = 4 раунда

## Bit primitive axes (Том I)

- **HDV** — Hyperdimensional Vector (Kanerva), D~2000-10000
- **⊗ (bind)** — XOR по позициям, коммутативен, инволютивен
- **⊕ (bundle)** — majority агрегация
- **sim(a,b)** = 1 − Hamming(a,b)/D
- **phase-bit / φ-bit** — U(1)-расширение с комплексной фазой
- **neurobit** — temporal coding + dynamic cost (stream × cost)
- **s-bit** — self-tuning stochastic signed bit
- **superbit / σ-bit** — σ-feedback primitive (phase + p-bit + SAT)
- **path-bit** — foundational via iterated integrals, Hopf algebra
- **T_X, F_X, Ch_X** — carrier, forgetful map, characteristic op оси X
- **D1-D5** — аксиомы расширения бита (§28)
- **Z/m** — cyclic group, уровни phase hierarchy

## Walsh / ANF / Boolean (оба тома)

- **ANF** — Algebraic Normal Form, Zhegalkin над F₂
- **Walsh spectrum** — коэффициенты Ŵ_S = 2^{-n}Σ(-1)^{f⊕S·x}
- **bit calculus** — дискретная производная ∂_i f = f(x) ⊕ f(x⊕e_i)
- **Inf_i(f)** — влияние бита i = Pr[∂_i f = 1]
- **linearity test** — BLR/Walsh тест близости к линейной

## Info-theory fingerprint (Том III)

- **Ĥ_∞** — оценка min-entropy
- **χ²-fingerprint** — excess χ²-distance от uniform (SHA-2 семья < RO, z ≈ -2.5)
- **Δ_I, Δ_χ²** — информационные инварианты, разделяющие marginal vs structural
- **directional chain-test** — Σ z_in(S)·z_out(S) по подмножествам S размера k
- **Ω_k** — новый инвариант: корреляция по output битам в k-подпространстве
- **chain_k** — chain-test order k
- **bit5_max** — word-parity максимальной позиции, HW=2 exclusive signal

## Ключевые структурные объекты

- **M-мир** — аддитивные дифференциалы (mod 2³²)
- **c-мир** — битовые дифференциалы (XOR, ⊕)
- **GPK-моноид** — {G,P,K} carry-структура без каскада
- **Интенсиональная рамка** — {С,П,Н,Д} алфавит SHA-256
- **BTE Theory** — Brick-Theoretic Extension (новая матем., §225)
- **★-Algebra** — Star-algebra (§190-200, Part 1)
- **height_2(SHA)** — высота p-адической башни (k=2), ≥11 или ∞
- **Sol_k** — множество решений mod 2^k

## Метрики атак

- **Birthday bound** — 2¹²⁸ для 256-битного выхода
- **MITM** — Meet-in-the-Middle, цель O(2⁸⁰) через state[16]
- **Distinguisher AUC** — 0.980 (v6.0, нейросеть)
- **Oracle distance 2⁻²⁶** — мультипликативный bias на коллизию

## Экспериментальные серии

- **П-N** — эксперимент N в Дифф. криптоанализе (1..1300+)
- **§N** — секция Математики бита (1..133)
- **IT-N, IT-N.M** — итерация Info-Theory исследования (1..6 + подитерации)
- **v1..v26** — версии методички (v20 — текущая основа)
