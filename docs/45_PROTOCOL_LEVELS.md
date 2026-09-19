# 45. Уровни протокола

## Зачем

Единый чеклист на всё — это театр на R0 и дыра на R4. Уровни масштабируют
процессуальную нагрузку по риску.

## Уровни

| Уровень | Для классов | Preflight | Evidence | Checkpoint | Decision log |
| --- | --- | --- | --- | --- | --- |
| P0 LITE | R0–R1 | 5 пунктов ядра | diff + test counts | git tag с readback | одна строка + DEC-ID |
| P1 STANDARD | R2–R3 | полный | full evidence checkpoint | manifest + SHA-256 + readback | полный шаблон; для ACCEPTANCE/RELEASE обязателен evidenceReadHash (docs/10) |
| P2 FULL | R4–R5 | полный + mandate check | P1 + professional review-evidence | независимый readback + counters | полный + evidenceReadHash |

## Состав P0 LITE

- Preflight ядра (agents/AGENT_PREFLIGHT.md): DEC, active state, level, scope, boundaries.
- Требуется: явное разрешение владельца, allowed paths, rollback (git).
- Evidence: diff, фактические test counts, команды.
- Decision log: DEC-ID, scope, allowed/forbidden — одной записью.
- Запрещено при P0: новые зависимости, сетевые вызовы, изменение API,
  fixture, любые файлы вне allowed paths.

P0 — не «без протокола». Главное правило действует на всех уровнях.

## Правила

1. Уровень назначается в TRIAGE и фиксируется в ACTIVE_STATE.
2. Смешанный scope — по высшему классу.
3. Агент может повысить уровень в любой момент (обязан при обнаружении
   скрытого риска); фиксация в memo.
4. Понизить уровень может только владелец явным решением.
5. P2 для R4–R5 не снижается мандатом deputy.
6. Переход на более высокий уровень в середине работы — restart preflight
   полного набора.

## Признаки, что уровень занижен (агент обязан повысить)

- Потребовалась новая зависимость или сетевая интеграция.
- Изменение затронуло API, схему данных или авторизацию.
- Появился запрос на реальные данные.
- Результат невоспроизводим.
