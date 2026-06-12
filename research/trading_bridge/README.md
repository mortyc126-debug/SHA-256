# SHA-256 research → Observer: intel layer (prototypes)

Прототипы, переносящие математику из METHODOLOGY / трёх томов / исследований в
торгового бота Observer. Цель — **структура, смысл, архитектура**, а не
production-готовность: у Observer есть саморазвитие (`self_modify`/`executor`),
он допишет детали. Всё в стиле проекта: детерминированно, без ИИ, drop-in рядом
с `watchdog.py`, чистый stdlib, русские докстринги, работает и standalone.

## Модули

| Файл | Из исследования | Что даёт Observer | Демо |
|---|---|---|---|
| `orderflow_walsh.py` | directional chain-test / Walsh (Том III, §4.4) | детектор **структуры потока ордеров** — айсберги/проработка при дельте≈0, невидимые для линейной дельты | z=288 на worked-order |
| `hdv_memory.py` | HDV-память + Хэмминг (Том I §4.2, 1765×) | **память прецедентов**: «когда рынок так выглядел — что было дальше» (насмотренность как HDC) | A→рост 0.94, B→падение 0.0 |
| `null_model.py` | честный per-target null (Phase 8C, IT-1.3) | замена порогов `vol>avg×4` на **адаптивные** z/перцентиль от своей нулевой модели | adaptive 4437 vs avg×4 2280 |
| `regime_otoc.py` | OTOC-скрэмблинг (Том III §III.8) | **датчик режима**: эффективный (не торговать) vs структурный (доверять тренду); ручки size/ai | random→0, структурный→выше |
| `phase_cycle.py` | фазовое кодирование Z/m (Том I §76, §5) | **внутридневной сезонный приор** (последний час склонен к росту и т.п.) | нашёл пик в фазе 6/8 |
| `observer_intel.py` | фасад | связывает всё в один `IntelLayer.update()` → strategy/risk/dispatcher/watchdog | полная сводка за один вызов |

Запуск любого: `python3 <module>.py` — печатает самодемонстрацию.

## Архитектура встраивания

```
Stream → Watchdog.on_trade / on_orderbook
             │  (копит знаки сделок _dirs, объёмы, цены, returns)
             ▼
        IntelLayer.update(snapshot, dirs, returns, hour, minute)
             │
   ┌─────────┼──────────────┬───────────────┬──────────────┐
   ▼         ▼              ▼               ▼              ▼
orderflow  regime_otoc   hdv_memory      phase_cycle   null_model
 _walsh   (режим)       (прецеденты)    (сезонность)  (аномалии)
   └─────────┴──────────────┴───────────────┴──────────────┘
             ▼
      IntelLayer.intel  →  strategy.evaluate : sig.strength ×= confidence_mult
                        →  risk.position_size: × size_mult (режим)
                        →  dispatcher        : interval × ai_factor
                        →  watchdog.alerts   : WORKED_ORDER (новый класс аномалии)

после закрытия сделки:
      risk.close_position → IntelLayer.learn(outcome_pct, hour, minute)
                            (память прецедентов + фазы дописываются сами)
```

## Конкретные точки врезки (минимальные диффы)

1. **`watchdog.py`** — копить направленный поток и отдавать структуру:
   ```python
   self._dirs = deque(maxlen=256)               # в __init__
   # в on_trade: self._dirs.append(1 if direction=="buy" else -1 if direction=="sell" else 0)
   ```
2. **`main.py`/`stream.py`** — один `IntelLayer` на тикер; на снапшоте звать
   `update(...)`, класть результат в дашборд и в контекст консилиума.
3. **`strategy.py`** — `sig.strength = min(1.0, sig.strength * intel.confidence_mult)`;
   при `intel.structured_flow` добавить причину «структурный поток по тренду».
4. **`risk.py`** — `position_size(..., vol_adj=sig.vol_adj * intel.size_mult)`.
5. **`dispatcher.py`** — домножать интервал консилиума на `intel.ai_factor`
   (структурный режим/worked-order → чаще).
6. **`risk.close_position`/`reflector`** — звать `intel.learn(pnl_pct, ...)`.

## Что честно и что нет

- **Механика корректна и null-контролируема** (каждый сигнал — против своей
  нулевой модели; урок Phase 8C вшит, чтобы не повторить артефакт IT-6).
- **Проверено на синтетике** — в архиве нет `market.db`. Предсказательную
  ценность (структура потока / режим / прецеденты реально предшествуют
  движению?) надо бэктестить на реальном тиковом потоке Observer. Хук готов:
  прогон `IntelLayer.update` по скользящим окнам из `data/<TICKER>/market.db`,
  разметка доходностью на N минут вперёд.
- `regime_otoc` нормировка — прототипная (ordering верный: случайность<структура),
  числовую шкалу бот откалибрует на своей истории.
- Детектор ловит **структуру/режим/прецедент, не направление**. Направление —
  по-прежнему тренд из `strategy.py`. Это слой уверенности и тайминга.
- **Не применимо** (не натягивал): carry / MITM / Wang / p-адика / ramification /
  prismatic — это структурные атаки на SHA, рыночного аналога нет.

## Происхождение (для саморазвития бота)

Каждый модуль ссылается в докстринге на конкретный раздел исследования, чтобы
`executor.py` при доработке понимал замысел: §4.2 (HDV), §4.4 (Walsh), §5/§76
(phase), Том III IT-1.3/Q7D (chain-test, χ²), §III.8 (OTOC), Phase 8C (null).
