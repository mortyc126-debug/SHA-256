# Session 8: Z_2[i] ramified extension — δ obstruction

**Дата**: 2026-04-22
**Цель Session 7 переданная**: smallest ramified extension Z_2[T]/(T²+1) = Z_2[i].

## Главный результат

**Theorem (Session 8)**: **Z_2[i] не admits δ-structure**, лифтящую Frobenius с F_2[i] = Z_2[i]/(2).

Доказательство constructive:
- Frobenius lift φ должен удовлетворять φ(i)² = φ(i²) = -1 ⇒ φ(i) ∈ {±i}
- Для φ(i) = i: δ(i) = (i − i²)/2 = (1+i)/2
- Для φ(i) = -i: δ(i) = (-i − i²)/2 = (1-i)/2
- Оба: (1±i)/2 ∉ Z_2[i], потому что (1±i) имеет нечётные components

**Структурная причина**: 2 ramified в Z_2[i]:
$$2 = -i \cdot (1+i)^2$$
Uniformizer π = 1+i; π² = 2i = (unit)·2. Элементы (1±i) = π·(unit) имеют только ОДИН фактор π, не два. Значит (1±i) не делится на 2.

## Эмпирическая верификация

Тестирование на конкретных элементах подтверждает:
- δ_identity(0) = 0 ✓
- δ_identity(1) = 0 ✓
- δ_identity(i) — **NOT WELL-DEFINED** (diff = 1 + i not divisible by 2)
- δ_identity(1+i) — **NOT WELL-DEFINED**
- δ_identity(2) = -1 ✓ (well-defined для elements в (2)·Z_2[i])
- δ_identity(3+2i) = -1 + i — well-defined

Pattern: δ defined для x ∈ (2)·Z_2[i] (где divisibility automatic) И x с подходящей "carry" структурой, но **не на базисном элементе i**.

## Что это значит

### Для нашей программы

Наша Session 7 hypothesis "rotations as q-twists" предполагала путь:
- Embed SHA в Z_2[ζ_n] (cyclotomic)
- ROTR_r = multiplication by ζ_n^r
- Use δ-structure of Z_2[ζ_n] для prismatic analysis

**Session 8 убивает этот путь directly**: Z_2[i] = Z_2[ζ_4] — наименьший ramified cyclotomic case — уже не имеет δ. Для Z_2[ζ_32] (нужного для full SHA) тем более.

### Resolution paths

Три возможных направления, все теоретические:

#### Path 1: Perfectoid extension
Адjoin all 2-power roots of unity: **Z_2[ζ_{2^∞}]**.
- After p-adic completion → **perfectoid** ring
- Perfectoid rings always admit canonical Frobenius (unique lift)
- δ-structure existует canonically
- **Цена**: ring HUGE (uncountable rank), abstract

#### Path 2: q-Witt avoids ramified specialization
Session 7's q-Witt prism (Z_2[[q-1]], (1+q)) работает because q **формальная**.
- Хорошая теория есть
- Связь с rotations через "evaluation q → ζ_n" — но эта evaluation бьёт в стену Path 1

#### Path 3: Absolute prismatic site (Bhatt-Scholze)
**Bhatt-Scholze** определяют prismatic cohomology для произвольных rings R, не только δ-rings.
- Берём R = Z_2[i]/(2) = F_2[i]/(i²+1) = F_2[i]/(i+1)² = **F_2[ε]/(ε²)** (dual numbers!)
- Computeprismatic cohomology через derived (∞-categorical) methods
- Не требует explicit δ on Z_2[i]
- **Это правильный path** теоретически

## Концептуальное переосмысление

После Session 8 чёткое понимание:
1. **Ramified extensions Z_p[ζ_n] для n с p | n не имеют простых δ-structures**
2. **Direct attempt построить δ-ring matching SHA rotations** — fails on smallest case
3. **Правильный target**: F_2[ε]/(ε²) и его абсолютная prismatic cohomology

**F_2[ε]/(ε²) — dual numbers** — fundamental object в algebraic geometry. Его prismatic cohomology — known computation в Bhatt-Scholze framework. Это connecting point с known theory.

## Открытые вопросы

### Q1: Что такое prismatic cohomology of F_2[ε]/(ε²)?
Основной вопрос для Session 9. Это "tangent space cohomology" в каком-то смысле. Должно быть computable concretely.

### Q2: Связь dual numbers с SHA rotations
F_2[i]/(i²+1) = F_2[ε]/(ε²) (substituting ε = i+1). Так что **ramified rotation structure** ~~ **dual numbers structure**. Если посчитаем prismatic of dual numbers, получим что-то relevant к ramified rotations.

### Q3: Multi-variable extension к F_2[x_1, ..., x_n]
Для full SHA нужны n=32 переменных. F_2[ε_1, ..., ε_n]/(ε_i²)? Или более сложная structure?

## Status

- ✓ Z_2[i] arithmetic implemented
- ✓ Both Frobenius lifts (φ(i) = ±i) tested
- ✓ **Theorem proved**: Z_2[i] не admits δ-structure (constructive)
- ✓ Resolution paths identified (perfectoid / q-Witt / absolute prismatic)
- → Session 9 target: prismatic cohomology of F_2[ε]/(ε²) (dual numbers)

## Honest reflection

Session 8 — **valuable negative result**. Закрывает naive direct path и **точно** указывает где жить настоящему framework: F_2[ε]/(ε²) dual numbers + absolute prismatic site.

Это переход из "hypothesis territory" в "computable concrete object". Dual numbers — стандарт в alg geom, их prismatic cohomology should be in literature.

**Realistic estimate Session 9-10**: read Bhatt-Scholze sections on prismatic cohomology of simple rings, find dual numbers computation, apply.

## Artifacts

- `session_8_zi.py` — Z_2[i] arithmetic + δ-obstruction proof
- `SESSION_8.md` — this file
