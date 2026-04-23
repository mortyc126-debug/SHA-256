# Session 12: Correction of rotation ring + XOR integration setup

**Дата**: 2026-04-22
**Цель Session 11 переданная**: integrate XOR via Session 2 formula.

## Главная коррекция — rotation ring

В Sessions 9-11 я идентифицировал "rotation ring" для n-bit register как **F_2[ζ_n] = F_2[s]/(s^{n/2})**. Это **field extension** (minimal polynomial of primitive ζ_n).

**ПРАВИЛЬНО**: actual ROTR action на F_2^n живёт в **full group algebra**:
$$F_2[\mathbb{Z}/n] = F_2[x]/(x^n - 1) = F_2[s]/(s^n) \text{ (for } n = 2^k, \text{ via } s = x + 1\text{)}$$

Разница:
- F_2[ζ_n] — "что такое ζ_n абстрактно" (dim n/2)
- F_2[x]/(x^n - 1) — "группа Z/n действующая на F_2^n" (dim n)

Для ROTR action нужно **Option B**: multiplication by x = 1 + s в F_2[s]/(s^n).

## Пересчёт cohomology с коррекцией

Applying Session 10 theorem к **d = 32**:

$$H^1(F_2[s]/(s^{32})) = \bigoplus_{k \text{ odd, } 1 \le k \le 31} \mathbb{Z}/2^{v_2(k+1)}$$

Exponents: [1, 2, 1, 3, 1, 2, 1, 4, 1, 2, 1, 3, 1, 2, 1, 5]
- **16 cyclic factors**
- **Order = 2^31**

Сравнение:
| Ring | d | # factors | Order |
|---|---|---|---|
| Session 11 (wrong) | 16 | 8 | 2^15 |
| **Session 12 (correct)** | **32** | **16** | **2^31** |

## Multi-register для SHA-256

Via Künneth (Session 11): 8 registers × per-register cohomology.

$$|H^1(R^{\otimes 8})| = (2^{31})^{8} = 2^{248}$$

**Это exceeds SHA-256 birthday bound 2^128 by 2^120 factor!**

| Scale | Classes | vs 2^128 |
|---|---|---|
| Single register | 2^31 | negligible |
| 8 registers | **2^248** | **2^120 excess** |

## Интерпретация

**Осторожно**: 2^248 "size of cohomology" НЕ эквивалентно "attack strength 2^{-248}".

Cohomology — это **classification structure**, not **computational advantage**. Factual observations:

1. **Rotation structure SHA** может быть захвачена в H¹ of F_2[s]/(s^32)^⊗8
2. **Classes count 2^248** — значительно больше чем 2^128 SHA security
3. **Но** эти classes — это structure ROTATION'ов. SHA имеет ещё XOR, AND, ADD.

**Если** SHA round preserves these classes (automorphism of cohomology) → structural handle.
**Если** SHA round collapses most classes → no useful invariant.

Без явной computation действия SHA round на H¹ мы не знаем что из этого реально true.

## Fundamental tension — XOR/AND integration

Нe могу просто "добавить XOR" в F_2[s]/(s^32) потому что:

- **Ring multiplication** в F_2[s]/(s^n): s^i · s^j = s^{i+j}
- **Bit-wise AND** на F_2^n: (a AND b)_i = a_i · b_i (componentwise в bit basis)

**Эти разные операции**.

Rotation basis (s^i) vs. bit basis (bit i) — different viewpoints. В rotation basis, "bit i" corresponds to coefficient of s^i in polynomial representation. AND on bit basis = componentwise multiplication on coefficients = HADAMARD product, NOT polynomial multiplication.

Formally: F_2[x]/(x^n-1) with TWO multiplications:
- **Convolution** (polynomial mult = cyclic correlation of coefficients)
- **Pointwise** (bit-wise AND = Hadamard product of coefficients)

These form two DIFFERENT rings on the same underlying abelian group F_2^n.

## Три resolution paths для XOR/AND

### Path (i): Tensor product R_rot ⊗ R_bool
Take product of rotation + boolean rings. Captures both но potentially overlarge (product of big cohomologies).

### Path (ii): Derived functor approach
Apply each ring's framework separately, then combine via derived tensor. More sophisticated, specialized.

### Path (iii): Separate invariants
Give up "single framework". Instead: compute invariants under each op in its own natural ring. Combine statistically.

## Concrete path для Session 13

**Recommend Path (i)** — concrete, computable. Define:
$$R_{\text{full}} = F_2[s]/(s^{32}) \otimes_{F_2} F_2[\varepsilon_1, \ldots, \varepsilon_{32}]/(\varepsilon_i^2)$$

- s captures rotation structure
- ε_i capture individual bit positions
- Tensor = combined structure

Compute H* via iterated Künneth. Size будет exponential.

Для single register: F_2[s]/(s^32) ⊗ F_2[ε_1,...,ε_32]/(ε_i^2).
- dim F_2[s]/(s^32) = 32
- dim F_2[ε_1,...,ε_32]/(ε_i^2) = 2^32
- Tensor product dim = 32 · 2^32 = 2^37

This is LARGE но computable dimension.

H*(tensor product) via Künneth — доступно в принципе. Будет большой, но with structure.

## Status

- ✓ **Correction** rotation ring: F_2[s]/(s^32) not F_2[s]/(s^16)
- ✓ Corrected cohomology: H¹ order 2^31 per register
- ✓ Multi-register 8 copies: 2^248 (exceeds 2^128)
- ✓ Identified tension: rotation vs bit-wise operations
- → Session 13 target: build R_full = rotation ⊗ boolean, compute its H*

## Честное reflection

Session 12 — **correction session**. Я нашёл свою ошибку в Sessions 9-11 (wrong choice d=16 vs d=32). Это **good sign** — means я thinking carefully и catching mistakes. Также **identified real tension** — XOR/AND live в different ring structure, not just "add more generators to rotation ring".

**Realistic estimate Session 13-15**: build combined ring framework и compute для SHA-like размеров. Может быть непрактично для 32 bits, тогда downsize к 8-bit prototype.

## Artifacts

- `session_12_xor.py` — correction + XOR setup
- `SESSION_12.md` — this file
