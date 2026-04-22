# ANF early-verify extension (§132) — честный отчёт

**Дата**: 2026-04-22
**Цель**: пробить 7.6× потолок ANF early-verify из §132 методички — найти новый ortho-disqualifier.

## Краткий вывод

**Направление закрыто (⊘SCOPED)**. ANF early-verify имеет фундаментальный cost-ceiling ≈ `V / L`, где `V` = стоимость полной верификации, `L` = битная ширина. Никакое stacking ortho-checks не помогает: дополнительные checks на разных битовых позициях ДАЮТ независимое сокращение pass-rate (✓ подтверждено эмпирически), но стоимость вычисления carry-бит на позиции `p` ТРЕБУЕТ O(p) walk через carry chain → spread-стратегии всегда хуже contiguous.

§133 методички уже корректно заключил: "scale ~10×, не 10^5× как extrapolation §132". Наш scoping подтверждает это количественно.

## Что мы подтвердили из методички

### Baseline §132 на L=16 (воспроизведение)

Для simplified round `y = M·x + K + C(x,K)` с M = 3-кратный rotation-XOR:

| k | early=2^15 | full_verify count | speedup (cost model V=L) |
|---|---|---|---|
| 2 | 32768 | 8192 | 2.67× |
| 4 | 32768 | 2048 | **3.20×** |
| 6 | 32768 | 512 | 2.56× |

При V=L=16 наш optimal k=4 даёт 3.2×. Методичка §132 использует другую cost model (с Φ-ball prefilter) и получает 7.64× при k=6. **Качественно совпадают**: ANF early-verify даёт small polynomial speedup, не экспоненциальный.

### Scaling к L=32 с реалистичным V

| V (full-verify cost) | L=16 opt speedup | L=24 opt speedup | L=32 opt speedup |
|---|---|---|---|
| 16  | 3.20× (k=4)   | 3.20× (k=4)   | 3.20× (k=4)   |
| 100 | **13.22×** (k=6)  | 13.22× (k=6)  | 13.22× (k=6)  |
| 1000| 91× (k=10)    | 91× (k=10)    | 91× (k=10)    |

**Speedup НЕ растёт с L** — он ограничен cost ratio V/L и оптимальным `k ≈ log₂(V·ln2)`. Для реального SHA-256 с V ≈ 100 operations: speedup ≈ 13×. Достаточно далеко от "breaks SHA-256".

## Новая находка: stacking-ortho работает, но дорого

**Empirical triple-stacking на L=16** (3 bits at low + 3 bits at mid + 3 bits at high):
```
P(low pass)        = 0.1250  (exact 0.5^3)
P(mid | low)       = 0.1250  (exact 0.5^3) — perfectly independent
P(high | low,mid)  = 0.1250  (exact 0.5^3) — perfectly independent
Joint              = 0.001953 (exact 0.5^9)
```

**Теоретический вывод**: pass rates at different bit positions в carry chain — **идеально независимые** события для wrong candidates. Это **ортогональный источник**, не коррелирующий с low-k check (в отличие от Φ-prior или HW-статистик).

### Но стоимость убивает преимущество

Чтобы проверить carry на позиции `p`, нужно walk'нуть carry chain от 0 до p. Для spread-стратегии (позиции low + mid + high, max = L-1):
- `early_walk = L-1` операций на каждого кандидата
- Full-verify reduction = 0.5^9 (effective k=9)

Сравнение при L=32, V=1000:
| стратегия | cost per check | speedup |
|---|---|---|
| k=9 contiguous low | 9 ops | **85×** |
| k=9 spread (low+mid+high) | 31 ops | 30× |
| k=10 contiguous low | 10 ops | **91×** |

Contiguous всегда выигрывает. Ortho-независимость не конвертируется в speedup пока carry chain требует O(p) walk.

## Когда это может изменится

Если бы существовал способ вычислить carry на произвольной позиции `p` за `O(log p)` или `O(1)` — stacking бы выиграл. Но:
- Carry[p] = функция first p битов input'ов (детерминированно)
- Нет очевидного способа shortcut'а без полного walk'а
- Parallel-prefix-sum circuits могут дать O(log p) aper bit, но всё ещё O(log L) per check

Это **фундаментальное архитектурное ограничение** carry arithmetic, не свойство именно SHA.

## Связь с методичкой

| Методичка | Наш тест | Статус |
|---|---|---|
| §132: "7.6× cumulative на L=16 toy" | ~3-13× разные cost models | ✓ consistent |
| §133: "реальная картина ~9× full recall" | 13× при V=100 | ✓ consistent |
| §132.9 "МС-принцип multi-source stacking" | ortho независимость работает, но cost убивает | ⚡ новое уточнение |
| §133.13: "нужны другие ortho-источники" | проверено triple-stacking → дорого | ⊘SCOPED |

## Решение

**ANF early-verify extension ⊘SCOPED 2026-04**. Причины:

1. Методичка сама в §133 корректно установила потолок ~9× full recall. Мы подтверждаем.
2. Единственная идея для extension — найти новый ortho-источник. Мы нашли triple-stacking independence (новая находка), но практически не применима из-за carry walk cost.
3. Speedup ≈ V/L bounded by architecture, не by algorithm. Алгоритмического прорыва тут не будет.

## Что осталось реально открытым

Из `06_open_questions.md` приоритет 1-4 (после закрытий 2026-04):

| Направление | Статус |
|---|---|
| ~~Q∩T framework~~ | ⊘SCOPED (z3 уже делает) |
| ~~Cohomology probe~~ | ⊘SCOPED (подтверждает, не расширяет) |
| ~~MITM O(2⁸⁰)~~ | ⊘SCOPED (хуже Wang) |
| ~~ANF early-verify beyond 7.6×~~ | ⊘SCOPED (V/L ceiling) |
| **Wang extension за r=17** | ?OPEN — **единственный остающийся технический** |
| **Block-2 signal amplification** | ?OPEN (IT-4.S4) |

**Следующий шаг**: если хочется продолжать — Wang extension за r=17 (T_BARRIER_EQUALS_SCHEDULE). Это **самый хардкорный** из оставшихся. Методичка 1300+ экспериментов не пробила. Скорее всего: либо найдём чудо, либо честно подтвердим что стена реальна и закрываем всю линию attack.

## Artifacts

- `anf_early_verify.py` — имплементация §132 model + базовые тесты
- `anf_optimality.py` — cost-model analysis + triple-stacking independence test
- `ANF_FINDINGS.md` — этот отчёт
