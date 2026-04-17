# Единая методичка — INDEX

**Консолидация** исследовательского корпуса SHA-256 + математика бита + info-theory (март 2025 — апрель 2026).

## Источники (оригиналы сохранены в корне репо)

- `/METHODOLOGY.md` — «Математика бита», 23420 строк, 133 секции
- `/methodology_v20 (5) (1).md` — «Дифф. криптоанализ SHA-256», 27739 строк, серия П-1..П-1300+
- `/INFO_THEORY_GUIDE.md` + `/research/min_entropy/*.md` — 16 отчётов серии IT

## Навигация

### 00_meta/ — Контекст для AI (читать ПЕРВЫМ)
- [status_legend.md](00_meta/status_legend.md) — Условные обозначения ✓DOK/⚡VER/∆EXP/✗NEG/⊘ROLL/?OPEN/⇒BRIDGE
- [glossary.md](00_meta/glossary.md) — Единый словарь терминов (δe, Φ, W, ANF, HDV, phase-bit, …)
- [key_numbers.md](00_meta/key_numbers.md) — Все численные результаты трёх томов
- [program_status.md](00_meta/program_status.md) — Снимок: ДОКАЗАНО / ЗАКРЫТО / ОТКРЫТО

### 01_vol_I/ — Том I «Математика бита»
- [01_fazy_A_B.md](01_vol_I/01_fazy_A_B.md) — HDC варианты, SHA-256 R=1 (1765×), bit calculus
- [02_fazy_C_D.md](01_vol_I/02_fazy_C_D.md) — Phase bits, GHZ, альтернативные оси
- [03_fazy_E_F.md](01_vol_I/03_fazy_E_F.md) — 5 новых осей, hierarchy_v2, граф зависимостей
- [04_part_II_extensions.md](01_vol_I/04_part_II_extensions.md) — 6 новых осей, клетки, нейробит (176.5×, 351×)
- [05_20_osey_kapstoun_v5_v6.md](01_vol_I/05_20_osey_kapstoun_v5_v6.md) — Аксиомы D1-D5, Plurality, CHSH, XOR-fragility
- [06_discrimination_superbit.md](01_vol_I/06_discrimination_superbit.md) — General Discrimination Theorem, Z/m, SHA 646×, SuperBit (Theorem 7)
- [07_path_bit_bit_cosmos.md](01_vol_I/07_path_bit_bit_cosmos.md) — Path-bit, Hopf algebra, Bit-Cosmos, conservation laws
- [08_astronomy_bit_phase_space.md](01_vol_I/08_astronomy_bit_phase_space.md) — Hadamard, carry phase space, W-atlas, ANF early-verify 7.6×

### 02_vol_II/ — Том II «Дифф. криптоанализ SHA-256»
- [01_bazovye_teoremy.md](02_vol_II/01_bazovye_teoremy.md) — Базовые v1..v12, П-1..П-9
- [02_kriptotopologia.md](02_vol_II/02_kriptotopologia.md) — Криптотопология, дифф. таблицы
- [03_kaskad_p10_p22.md](02_vol_II/03_kaskad_p10_p22.md) — Каскад П-10..П-22, T_CASCADE_MAX, барьер r=17
- [04_wang_chain_p23_p101.md](02_vol_II/04_wang_chain_p23_p101.md) — Wang-chain, T_WANG_CHAIN P=1.0, пара W0=c97624c6
- [05_padic_gf2_p42_p66.md](02_vol_II/05_padic_gf2_p42_p66.md) — p-адика, GF(2), T_INFINITE_TOWER
- [06_diffuzia_distinguisher.md](02_vol_II/06_diffuzia_distinguisher.md) — AUC=0.980, MITM O(2⁸⁰)
- [07_nova_mathematics.md](02_vol_II/07_nova_mathematics.md) — ★-Algebra, BTE, GPK, carry-rank=589
- [08_otkrytye_i_zakrytye.md](02_vol_II/08_otkrytye_i_zakrytye.md) — Итоги Тома II
- [09_praktiki_distinguisher_v6.md](02_vol_II/09_praktiki_distinguisher_v6.md) — Практические атаки (ECDSA/HMAC/Merkle), Distinguisher v6.0 φ=+0.414, Φ-manifold, Cycle dynamics
- [10_nonlinear_algebra_ALG.md](02_vol_II/10_nonlinear_algebra_ALG.md) — Серия XVII, SAA, T_UNIVERSAL_76, ALG 53 опр., Carry-Web, NK Framework
- [11_gpu_ctt_tlc_unified.md](02_vol_II/11_gpu_ctt_tlc_unified.md) — CTT, TLC, SCF, Unified hash theory, Carry Theory axioms, Beyond the Wall

### 03_vol_III/ — Том III «Info-theory fingerprinting»
- [01_framework.md](03_vol_III/01_framework.md) — Ĥ_∞, Rényi, Δ_χ²/Δ_I/Ω_k, chain-test theory
- [02_min_entropy_chi2.md](03_vol_III/02_min_entropy_chi2.md) — IT-1, IT-1.3 (SHA-2 z≈-2.5, p<10⁻⁷), IT-2 (σ₀/σ₁ 88%), IT-3
- [03_walsh_chain_test.md](03_vol_III/03_walsh_chain_test.md) — IT-4 Q7D (z=-3.87, p=0.002 Bonferroni), Walsh-4 z=-6.40
- [04_surgical_omega_k.md](03_vol_III/04_surgical_omega_k.md) — IT-4.S1-S4, IT-5G/S, IT-6 (Ω_3=+0.98, 240/256 same-sign)
- [05_bridges_otkrytoe.md](03_vol_III/05_bridges_otkrytoe.md) — Мосты с Томами I/II, открытые, закрытые

### Приложения (корень unified/)
- [04_bridges.md](04_bridges.md) — 8 мостов между Томами I/II/III
- [05_negatives.md](05_negatives.md) — ~41 закрытое направление
- [06_open_questions.md](06_open_questions.md) — ~24 открытых вопроса, приоритизированных
- [07_chronology.md](07_chronology.md) — Сквозная хронология трёх линий
- [08_files_index.md](08_files_index.md) — Индекс программ и инструментов

## Как читать (для AI перезапускающего сессию)

### Быстрый старт (5 минут чтения)
1. `00_meta/status_legend.md` — понять кодировку статусов.
2. `00_meta/program_status.md` — ДОКАЗАНО / ЗАКРЫТО / ОТКРЫТО.
3. `00_meta/key_numbers.md` — все главные числа.
4. `04_bridges.md` — как связаны три тома.

### Полное погружение (1-2 часа)
5. Глоссарий, потом Том I гл. 1-8 последовательно.
6. Том II гл. 1-8 последовательно (основная атака).
7. Том III гл. 1-5 (fingerprint instruments).
8. Приложения 05-07 для контекста закрытых/открытых.

### По задаче
- **Ищешь shortcut атаку?** → Том II гл. 4 (Wang), Том I гл. 8 (ANF early-verify §132), открытый ?OPEN приоритет 1.
- **Ищешь distinguisher?** → Том III гл. 3-4 (chain-test, Ω_k), Том II гл. 6 (AUC=0.980).
- **Теория битов?** → Том I гл. 5-7 (D1-D5, Discrimination theorem, bit-cosmos).
- **Что пробовали?** → `05_negatives.md` прежде чем повторять.
- **Что открыто?** → `06_open_questions.md` приоритеты 1-4.

## Статус консолидации

**Создано**: 21 глава (I:8 + II:8 + III:5) + 4 метафайла + 5 приложений + этот INDEX.
**Размер суммарно**: ~200 KB структурированного телеграфного текста vs 2.5 MB исходников (≈12× компрессия).
**Охват**: все уникальные теоремы, все ключевые числа, все статусы, все кросс-ссылки сохранены.
**Потеряно** (осознанно): вводные абзацы, повторные "что доказано", мета-философия, три дубля хронологии, артефакты session summaries.

## Принципы консолидации

1. **Уникальный контент preserved**: каждая теорема/открытие/число сохранено с явной ссылкой на исходник.
2. **Телеграфный стиль**: факт → формулировка → статус → ссылка. Без воды.
3. **Статусы обязательны**: ✓DOK / ⚡VER / ∆EXP / ✗NEG / ⊘ROLL / ?OPEN — чтобы AI не ходил кругами.
4. **Кросс-ссылки явные**: ⇒BRIDGE между томами, см. `04_bridges.md` для связей.
5. **Негативы сохранены**: в `05_negatives.md` — чтобы не повторять закрытое.
6. **Навигация по задаче**: индекс выше позволяет прыгнуть в нужный раздел за 1 шаг.

## Что дальше

**Для продолжения программы** приоритетные направления (из `06_open_questions.md`):
1. Backward shortcut beyond §132 (ANF early-verify 7.6×) — первый приоритет.
2. MITM O(2⁸⁰) реализация [П-210].
3. Ω_k для SHA-3/BLAKE.
4. Signal amplification у block-2 [IT-4.S4].

**Инструменты готовы** (см. `08_files_index.md`):
- superbit/ — полный SAT engine.
- it6_full_output_map.py — Ω_k универсальный.
- sharp_analysis.py — χ² fingerprint любой hash family.
- Distinguisher v6.0 neural — в архиве П-1000..
