# Глава I.2. Фазы C и D — Phase bit иерархия + Альтернативные оси

> TL;DR: Фаза C строит phase→ebit→ghz→gates целочисленно (Bell, GHZ, DJ/BV, no-cloning). Фаза D — 4 независимых оси (reversible/stream/prob/braid). Capstone v1 unified_hierarchy.c заявил «6 осей полная таблица» — ✗NEG, опровергнут далее (см. §I.3).

## §I.2.1 Фаза C: иерархия phase bits [§5]

**Идея** [§5.1]: 3 дара кубитов (фаза, интерференция, запутанность). Первые 2 — чисто классически через phase bit ∈ {−1,0,+1}. Алгебраическая структура запутанности (Bell, GHZ) — phase-HDV над {−1,0,+1}⁴ и ⁸.

**phase_bits.c** ⚡VER [§5.2]: bind=a·b, bundle=a+b (интерференция).
- bundle(a,−a)=0 — деструктивная интерференция
- 20 паттернов, удаление #7 через −item_7: cos падает с +0.22 до +0.0009
- WHT нативно — один скалярный продукт = один коэффициент F̂(s)
- **Строгое расширение** бинарных: каждый бинарный HDV есть phase HDV.

**ebit_pairs.c** ⚡VER [§5.3]: phase-HDV длины 4. Bell states:
- Φ⁺=(+1,0,0,+1), Φ⁻=(+1,0,0,−1), Ψ⁺=(0,+1,+1,0), Ψ⁻=(0,+1,−1,0)
- Ортогональный базис: ⟨B_i|B_j⟩=2δ_ij
- **Non-factorizability** ✓DOK exhaustive search [−2,+2]: ни один Bell state не раскладывается
- Pair-relation memory: 64 ebit'а в bundle 1024 со 100% accuracy.

**ghz_triples.c** ⚡VER [§5.4]: phase-HDV длины 8. GHZ⁺=(+1,0,0,0,0,0,0,+1), GHZ⁻ с минусом, W=(0,+1,+1,0,+1,0,0,0).

**T_GHZ_DISCRIMINATION** ✓DOK [§5.4]: GHZ⁺ и GHZ⁻ имеют ИДЕНТИЧНЫЕ 2-битные маргиналы p(00)=p(11)=1/2, корр +1.
| state | ⟨Z⊗Z⊗Z⟩ через \|c\|² | ⟨X⊗X⊗X⟩ phase |
|---|---|---|
| GHZ⁺ | 0 | **+1** |
| GHZ⁻ | 0 | **−1** |
| W | −1 | 0 |

**Самое сильное утверждение фазы C**: вероятностное измерение НЕ может различить GHZ±. Phase-flip оператор сразу видит знак. Прямое доказательство: phase-bit амплитуды несут информацию, недоступную вероятностным распределениям.

**phase_gates.c** ⚡VER [§5.5]: H/X/Z/CNOT/WHT (без √2 нормализации).
- **Deutsch-Jozsa** n=6, N=64: 5/5 функций классифицированы (const→±64, balanced→0)
- **Bernstein-Vazirani** n=8, N=256: 5/5 скрытых строк восстановлены точно (amp[a]=+256)
- 4 алгебраических тождества: HXH=2Z, HZH=2X, WHT²=2ⁿI, CNOT²=I
- Структурное преимущество: одна WHT после оракула коллапсирует ответ.

**phase_limits.c** ⚡VER [§5.6]: no-go теоремы классически.
- **No-cloning**: CNOT клонер на |+⟩⊗|0⟩ выдаёт Bell Φ⁺, не |+⟩⊗|+⟩. Линейность + базис → автоматический no-clone.
- **Monogamy** (Φ⁺)_AB⊗|0⟩_C: ⟨Z_A·Z_B⟩=+1.0000, ⟨Z_A·Z_C⟩=⟨Z_B·Z_C⟩=+0.0000.
- **Complementarity** Z/X: |0⟩→Pr(Z=0)=1, Pr(X=0)=0.5.
- **Schmidt rank**: все 4 Bell states ранг 2.

**phase_universal.c** ⚡VER [§5.7]:
- {H,X,Z} max≤8: **64 матрицы**
- **{X, CNOT}** на 2 кубитах: ровно **24 = 4!** перестановок
- 3-CNOT SWAP identity ✓
- Полное замыкание {H,X,Z,CNOT} cap=4: **2988 матриц** (квантовый Clifford 2-qubit = 11520)

**phase_hdc.c** ⚡VER [§5.8]: мутабельная HDC.
- store: bundle += bind(key,value); **remove**: bundle −= bind(key,value)
- Exact removal ✓ (cos +0.23→+0.013, 19/19 сохранены)
- **In-place overwrite** ✓
- Capacity 100% до N=32, 92% при N=64.
- Бинарный HDC не может: чистого удаления, overwrite, доказательства отсутствия.

**phase_algo.c** ⚡VER [§5.9]:
- **3-SAT counting через одну WHT**: amp[0]=#SAT−#UNSAT
- 4/4 точных count'a (m=16,24,32,40)
- **Linearity test**: peak²/total = 1 ⇔ линейна. Linear→1.0000, nonlinear→0.2500.

**Сводка** [§5.10]:
| # | примитив | добавляет |
|---|---|---|
| 0 | bit {0,1} | XOR |
| 1 | phase bit | субтракция, интерференция, native Walsh |
| 2 | ebit (4-d) | неразделимые пары, Bell |
| 3 | ghz (8-d) | тройные корреляции, phase>prob |
| 4 | gates | DJ/BV circuits |

## §I.2.2 Фаза D: альтернативные оси [§6]

**Вопрос** [§6.1]: phase — единственный путь? 4 направления независимы от phase и друг от друга.

**reversible_bits.c** ⚡VER [§6.2]: Bennett 1973, Fredkin-Toffoli 1982.
- 4 self-inverse гейта (NOT/CNOT/Toffoli/Fredkin), 16/16 ✓
- Fredkin conservation 256/256 (Hamming сохранён); Toffoli обратим но НЕ консервативен
- Reversible full adder: 3 CNOT + 2 Toffoli + 2 ancilla, обратный проход ✓ восстанавливает входы
- Bennett uncomputation: ancilla чистая
- **Новое свойство**: information conservation как ЖЁСТКОЕ ограничение, kT·ln2 не платится.

**stream_bits.c** ⚡VER [§6.3]: бит = функция времени.
- LFSR n=7 примитивный полином x⁷+x⁶+1: период **127=2⁷−1** ✓ (max length)
- Shift-XOR алгебра: S(x⊕y)=Sx⊕Sy ✓, F₂-модуль
- CA rule 30 (хаос), rule 110 (Тьюринг-полно)

**Автокорреляция** [§6.3]:
| τ | rule30 | rule110 | random |
|---|---|---|---|
| 1 | +0.544 | −0.028 | +0.006 |
| **7** | +0.522 | **+0.915** | −0.008 |
| 10 | +0.401 | −0.127 | +0.021 |

**T_GLIDER_PERIOD7** ⚡VER [§6.3]: rule 110 — скачок +0.915 на τ=7 = период глайдера. **Новое свойство**: ВРЕМЯ. Один локальный апдейт = Тьюринг-полнота.

**prob_bits.c** ⚡VER [§6.4]: pbit=(p₀,p₁).
- Joint/marginal через outer product, det=0.15 на коррелированном
- Bayes: P(sick)=0.1, TPR=0.9, FPR=0.1 → P(sick|test+)=0.5
- Энтропия: (0.5,0.5)→1.000
- BSC capacity: capacity ≡ MI численно (Шеннон ✓)

**T_PROB<PHASE** ✓DOK [§6.4]: Bell Φ⁺ и Φ⁻ имеют ИДЕНТИЧНЫЕ |amp|² распределения. Никакая pbit не различит. **pbits строго слабее phase**.

**braid_bits.c** ⚡VER [§6.5]: B_n Artin (1925), σ_i.
- Artin отношения как permutations: σ_1σ_3=σ_3σ_1, σ_1σ_2σ_1=σ_2σ_1σ_2 ✓ (Yang-Baxter)
- σ_1σ_1: identity как permutation, но writhe=2
- Linking number Hopf=2, σ⁻¹σ⁻¹=−2
- Writhe: trivial=0, Hopf=2, trefoil=3, fig8=0

**braid_jones.c** ⚡VER [§6.6]: reduced Burau ρ:B_3→GL_2(Z[t,t⁻¹]).
- ρ(σ_1)=[[−t,1],[0,1]], ρ(σ_2)=[[1,0],[t,−t]]
- Yang-Baxter как матрица: ρ(σ_1σ_2σ_1)=ρ(σ_2σ_1σ_2)=[[0,−t],[−t²,0]] байт-идентично
- **trefoil σ₁³**: [[−t³, t²−t+1],[0,1]] — правый-верх = **точный полином Александера 3_1** ✓DOK

**braid_hdc.c** ⚡VER [§6.7]: non-commutative binding с Burau-тегом.
- v-only match 3/6 (неоднозначно), tag match **1/6** (только CBA)
- Order-sensitive HDC без Clifford multivector blowup.

**anyonic_phases.c** ⚡VER [§6.8]: Burau trace.
- σ₁ⁿ: tr=(−t)ⁿ+1
- Yang-Baxter сохраняет фазу
- **Full twist (σ₁σ₂)³ ∈ Z(B_3)**: ρ=t³·I скаляр ✓DOK (центр действует скаляром)

## §I.2.3 Capstone v1: unified_hierarchy.c [§6.9] ⊘ROLL

**Гипотеза**: «6 элементов в таблице битов».
| примитив | T1 distinguish | T2 non-comm | T3 remove | T4 interfere |
|---|---|---|---|---|
| binary | ✓ | — | — | — |
| phase | ✓ | — | ✓ | ✓ |
| probability | ✓ | — | — | — |
| reversible | ✓ | ✓ | ✓* | — |
| stream | ✓ | — | ✓ | ✓ |
| **braid** | ✓ | ✓ | ✓ | ✓ |

Заявление: «braid — единственный 4/4; 6 осей — полная таблица».

**⊘ROLL** [§6.9]: ЛОЖНО. Опровергнуто **5 раз подряд** в фазе E (linear, selfref, church, modal, relational). Файл оставлен в репо как сертификат ошибочной гипотезы (см. §I.3).
