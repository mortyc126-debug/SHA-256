# Приложение: Индекс программ и инструментов

Все исполнимые файлы и скрипты в репозитории. Короткое описание + том.

## superbit/ (Том I — SuperBit Engine)

| Файл | Назначение | Том |
|---|---|---|
| `__init__.py` | Экспорты package | I §63-79 |
| `core.py` | σ-map, σ-feedback, Lyapunov | I §65 |
| `monitor.py` | Monitoring σ-flow | I §65 |
| `optimize.py` | SA replacement, sample-repair | I §64 |
| `register.py` | Σ-registry for state | I §63 |
| `sat.py` | Native-σ WalkSAT, CaDiCaL/Kissat integration | I §69, §71 |

## research/min_entropy/ — Том III

### Python экспериментальные скрипты

| Файл | Назначение | IT-шаг |
|---|---|---|
| `experiment.py` | Main min-entropy estimation pipeline | IT-1 |
| `sharp_analysis.py` | χ² fingerprint скан 7 хэшей | IT-1.1..1.3 |
| `sha256_chimera.py` | Chimera mixed hash families | IT-2 |
| `compare_hashes.py` | Cross-family comparison | IT-1.3 |
| `cross_hash_k12.py` | k=12 cross-hash scan | IT-1.3 |
| `replication.py` | Replication of baseline experiments | IT-1 |
| `it3_estimator.py` | Δ_χ² / Δ_I estimator | IT-3 |
| `it3_main.py` | IT-3 main driver | IT-3 |
| `it3_unification.py` | Attempt unified theory | IT-3 |
| `it4_1_hw_scan.py` | HW-parity hypothesis probe | IT-4.1 |
| `it4_2_chimera_attribution.py` | Chimera attribution | IT-4.2 |
| `it4_q1_bit_specificity.py` | bit5 uniqueness | IT-4.Q1 |
| `it4_q2_hw_parity.py` | Q2 HW parity check | IT-4.Q2 |
| `it4_q3_role_asymmetry.py` | Role asymmetry | IT-4.Q3 |
| `it4_q3b_hw4_reproducibility.py` | HW=4 cherry-pick check | IT-4.Q3b |
| `it4_q7_bilinear.py` | 2nd-order Walsh | IT-4.Q7 |
| `it4_q7b_reverse_trace.py` | Reverse trace probe | IT-4.Q7b |
| `it4_q7c_walsh3.c` + exec | 3rd-order Walsh C-level | IT-4.Q7C |
| `it4_q7c_wrapper.py` | Q7c Python wrapper | IT-4.Q7C |
| `it4_q7d_chain3.c` + exec | Directional chain-3 C | IT-4.Q7D ⭐ |
| `it4_q7d_r500.py` | Amplified R=500 | IT-4.Q7DEF |
| `it4_q7d_wrapper.py` | Q7d wrapper | IT-4.Q7D |
| `it4_q7e_crosstarget.py` | Cross-target replication | IT-4.Q7DEF |
| `it4_q7f_chain4.c` + exec | Walsh-4 chain | IT-4.Q7DEF |
| `it4_q7f_wrapper.py` | Q7f wrapper | IT-4.Q7DEF |
| `it4_s1_full_output_scan.py` | S1 full 256-bit output | IT-4.S1 |
| `it4_s2_rounds.py` | S2 round decay | IT-4.S2 |
| `it4_s3_cross_hash.py` | S3 cross-hash | IT-4.S3 |
| `it4_s4_block2_amp.py` | S4 block-2 amplification | IT-4.S4 |
| `it4_targeted.py` | Targeted scan | IT-4 |
| `it4_validate_and_classify.py` | Validation & classify | IT-4 |
| `it4_walsh.py` | Walsh full scan | IT-4 |
| `it5s_round_order_map.py` | Round × Walsh order map | IT-5S |
| `it6_full_output_map.py` | ~~Ω_k inv.~~ chi_arr-basis probe | IT-6 ⊘ROLL [§III.7] |
| `it6b_fast.py` + `it6b_omega_spectrum.py` | ~~Ω_k spectrum~~ artifact | IT-6 ⊘ROLL |
| `it6c_cross_feature.py` | ~~Cross-feature analysis~~ artifact | IT-6 ⊘ROLL |
| `phase8c_proper_audit.py` + `it4_q7d_chain3_local` | PROPER audit with per-target RO null — reveals artifact | Phase 8C ⭐ |

### Collision probes (IT-7 serie)

| Файл | Назначение |
|---|---|
| `it7_collision_probe.py` | Baseline collision probe |
| `it7_collision_v2.py` | V2 collision |
| `it7_cumulative.c` + exec | Cumulative distinguisher |
| `it7_cumulative_output.csv` | Data |
| `it7_j16.c` + exec | J-16 probe |
| `it7_predict_collision.py` | Collision prediction |
| `it7_stratified.c` + exec | Stratified search |
| `it7w_wang_probe.py` | Wang-based probe |
| `it7w2_continuous.py` | Continuous variant |
| `it7x_microscopic.py` | Micro-level probe |
| `it7z100m.c` + exec | 100M test |
| `it7z_own_standard.py` | Own standard |

### Full-SHA cascade (IT-8, IT-9)

| Файл | Назначение |
|---|---|
| `it8a_carry_migration.c` + exec | Carry migration test |
| `it8b_cworld.c` + exec | C-world exploit |
| `it8b_verify.c` + exec | Verification |
| `it8b2_exploit.c` + exec | Exploit v2 |
| `it8c_parallel.c` + exec | Parallel variant |
| `it8d_amplify.c` + exec | Amplify |
| `it8e_cascade.c` + exec | Cascade variant |
| `it8f_r64.c` + exec | r=64 full rounds |
| `it9_full256.c` + exec | Full 256-bit |
| `it9b_tails.c` + exec | Tails |
| `it9c_full_sha.c` + exec | Full SHA |
| `it9d_endtoend.c` + exec | End-to-end |
| `it9e_twoblock.c` + exec | Two-block |

### JSON артефакты (результаты)

Все `*.json` и `*.csv` — результаты запусков. Критичные:
- `sharp_results.json` (24KB): **χ²-fingerprint всех 7 хэшей**
- `it4_walsh.json` (49KB): **64-feature Walsh scan**
- `it4_q7d_r500_results.json` (24KB): **Q7D amplified R=500 p=0.002 Bonferroni**
- `it6_full_output_map.json` (25KB): ~~Ω_k + ρ=+0.98 данные~~ ⊘ROLL [§III.7]: chi_arr artifact
- `phase8c_proper_audit.json`: **PROPER audit showing IT-6 claim is artifact** (SHA Ω=0.979, RO Ω=0.978 same protocol)
- `it3_results.json` (87KB): **Δ_χ² / Δ_I full**
- `chimera_results.json`: Mixed hash families
- `it7_cumulative_output.csv`: Cumulative distinguisher trace

## Главные исходники (корень)

| Файл | Назначение | Том |
|---|---|---|
| `METHODOLOGY.md` | **Исходный** — Математика бита | I |
| `methodology_v20 (5) (1).md` | **Исходный** — Дифф. криптоанализ | II |
| `INFO_THEORY_GUIDE.md` | Фреймворк info-theory | III |

## unified/ — Консолидированная методичка (эта)

### 00_meta/
- `status_legend.md` — Условные обозначения статуса
- `glossary.md` — Единый словарь терминов
- `key_numbers.md` — Все численные результаты
- `program_status.md` — Снимок: ДОКАЗАНО / ЗАКРЫТО / ОТКРЫТО

### 01_vol_I/ (Том I)
- `01_fazy_A_B.md` — HDC + SHA R=1
- `02_fazy_C_D.md` — Phase bits + альтернативные оси
- `03_fazy_E_F.md` — 6 новых осей + Consolidation
- `04_part_II_extensions.md` — Pairs, triples, нейробит
- `05_20_osey_kapstoun_v5_v6.md` — Аксиомы D1-D5, CHSH, XOR-fragility
- `06_discrimination_superbit.md` — Discrimination theorem, SuperBit
- `07_path_bit_bit_cosmos.md` — Path-bit, Bit-Cosmos Platonic
- `08_astronomy_bit_phase_space.md` — Carry phase space, W-atlas, ANF early-verify

### 02_vol_II/ (Том II)
- `01_bazovye_teoremy.md` — Базовые v1..v12, П-1..П-9
- `02_kriptotopologia.md` — Криптотопология
- `03_kaskad_p10_p22.md` — Каскад П-10..П-22
- `04_wang_chain_p23_p101.md` — Wang-chain, пара W0=c97624c6
- `05_padic_gf2_p42_p66.md` — p-адика, GF(2), Якобиан
- `06_diffuzia_distinguisher.md` — AUC=0.980, MITM 2⁸⁰
- `07_nova_mathematics.md` — ★-Algebra, BTE, GPK
- `08_otkrytye_i_zakrytye.md` — Итоги Тома II

### 03_vol_III/ (Том III)
- `01_framework.md` — Δ_χ², Δ_I, Ω_k, chain-test
- `02_min_entropy_chi2.md` — IT-1, IT-1.3, IT-2, IT-3
- `03_walsh_chain_test.md` — IT-4 Q7D Bonferroni
- `04_surgical_omega_k.md` — IT-4.S1-S4, IT-5, IT-6
- `05_bridges_otkrytoe.md` — Cross-references + frontier

### Корень unified/
- `04_bridges.md` — Мосты между томами
- `05_negatives.md` — Закрытые направления
- `06_open_questions.md` — Открытые вопросы
- `07_chronology.md` — Хронология
- `08_files_index.md` — Этот файл
- `INDEX.md` — Навигация

## Инструменты для новой сессии

**Готово к использованию:**
1. **superbit/** — полный SAT engine с σ-feedback
2. **it4_walsh.py + q7d_chain3** — directional Walsh chain-test
3. ~~**it6_full_output_map.py** — Ω_k для любого хэша (универсальный инструмент)~~ ⊘ROLL [§III.7]: инструмент работает, но измеряет artifact (chi_arr-basis alignment, not SHA invariant). Для proper probe нужен отдельный new tool.
4. **sharp_analysis.py** — χ² fingerprint любой hash family
5. **sha256_chimera.py** — смешанные хэш-семьи для контроля

**Требуется написать (TODO):**
- MITM O(2⁸⁰) реализация [П-210]
- ~~Ω_k для SHA-3/BLAKE benchmark~~ ⊘ROLL [§III.7]: direction closed
- Chain-test orthogonal to ANF — extension §132 beyond 7.6×
