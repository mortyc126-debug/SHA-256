# Session 1: Foundations — δ-rings

**Дата**: 2026-04-22
**Цель**: понять определение δ-ring, проверить на простейших примерах, найти первое препятствие на пути к SHA.

## Что изучили

### δ-ring definition (Joyal 1985, stated Bhatt-Scholze 2019)

Для prime p, **δ-ring** — пара (A, δ) где A — коммутативное кольцо, δ: A → A с аксиомами:

- **D1**: δ(0) = δ(1) = 0
- **D2** (p=2): δ(x + y) = δ(x) + δ(y) − xy
- **D3** (p=2): δ(xy) = x²δ(y) + y²δ(x) + 2δ(x)δ(y)

Эквивалентно: определяем φ: A → A через φ(x) = x^p + p·δ(x). D1-D3 эквивалентны утверждению что **φ — ring homomorphism**, причём φ(x) ≡ x^p (mod p).

**Интуиция**: δ-структура — это choice of "Frobenius lift". В characteristic p, Frobenius x → x^p автоматически. В char 0 / mixed char нет канонического Frobenius — δ его выбирает.

### Примеры верифицированы (delta_rings.py)

| Ring | δ-structure | Status |
|---|---|---|
| Z (char 0) | δ(x) = (x−x²)/2, φ(x) = x | ✓ Axioms D1-D3 verified for x,y ∈ [-3, 3] |
| Z/4 | δ: Z/4 → Z/2 | ✓ Well-defined; δ(0)=δ(1)=0, δ(2)=δ(3)=1 |
| Bool_1 = F_2[t]/(t²-t) | φ(x) = x² = x = id, δ = 0 trivially | ❌ Trivial |
| Z/4[t]/(t²-t) lift | δ(t) = t(1-t)/2 = 0 (idempotence) | ❌ Trivial |

### **Первое препятствие обнаружено**

**Boolean ring = F_2[t_1,...,t_n]/(t_i²-t_i)** имеет **тривиальную δ-структуру**. Причина: idempotentность — t² = t заставляет δ(t) = (t − t²)/2 = 0, и распространяется на все элементы.

**Это значит**: если мы просто рассматриваем Bool_{256} как ring (на котором SHA действует), prismatic cohomology будет тривиальной. Никаких нетривиальных классов.

**Следствие**: naive applicaton prismatic cohomology к SHA **не работает**. Нужна более тонкая конструкция.

## Что нужно для Session 2

### Идея 1: Witt-vector δ-structure

W_n(F_2) = Z/2^n как кольцо. Но Z/2^n имеет нетривиальную δ-структуру (унаследованную от Z_2). Вопрос:

- δ на Z/2^32 (для 32-битных слов SHA) — что это?
- Есть ли совместимость δ с SHA операциями (ADD, XOR, rotations)?

**Подозрение** (из наших предыдущих Witt-findings): rotations НЕ совместимы с δ. Это то же самое препятствие что filtration в CROSS_POLLINATION.md.

### Идея 2: q-de Rham / prismatic с non-trivial prism

Вместо trivial prism (Z_p, (p)), использовать **q-prism** (Z_p[[q-1]], (q-1)). Это даёт q-de Rham cohomology (известный объект).

Может быть q-аналог rotation (q-twisted) даст нетривиальные классы.

### Идея 3: "Arithmetic" SHA

Переформулировать SHA так, чтобы Boolean ring НЕ использовался напрямую. Вместо (Z/2)^32 использовать W_32(F_2) = Z/2^32 (без idempotence x² = x).

Это наш **Witt-vector reformulation**: все биты SHA — это coordinate в Z/2^32 via Witt. Тогда δ нетривиально, и prismatic может work.

### План Session 2

**Цель**: проверить δ-структуру на W_n(F_2) и её совместимость с SHA операциями.

Конкретные шаги:
1. Реализовать δ на Z/2^n explicitly для n = 4, 8, 16
2. Проверить D1-D3 axioms
3. Взять каждую SHA-like операцию (ADD, XOR, ROTR, AND, Ch, Maj) — проверить δ(op(x)) = ? (compatibility)
4. Найти FIRST операцию которая ломает δ-compatibility

Это prerequisite для более глубокой prismatic работы.

## Metacognition: что я (Claude) узнал в этой session

- Как читать δ-ring axioms (D1-D3)
- Proficient в computing δ(x) для малых concrete rings
- Понимание почему Bool ring trivially = дегенерирует

Что **не знаю** / нужно учить дальше:
- Prism formally (pair (A, I))
- Prismatic site
- Prismatic cohomology computation techniques
- Связь с crystalline cohomology

**Честное self-assessment**: я не prismatic-expert. Могу только implement concrete examples и reason about them. Для реальной теории нужен Bhatt-Scholze paper "Prisms and Prismatic Cohomology" (2019) или Kedlaya's notes.

## Статус

- ✓ δ-ring definition понята
- ✓ Simple examples computed
- ✓ First obstruction identified (Bool ring trivial)
- → Session 2 target defined
