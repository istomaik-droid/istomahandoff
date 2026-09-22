# 30. Testing law

## Матрица

| Test class | Что доказывает |
| --- | --- |
| Source lint | Допустимая структура |
| Strict typecheck | Typed contracts |
| Architecture tests | Dependencies и boundaries |
| Focused contract tests | Positive state machine |
| Negative tests | Unauthorized, malformed, stale, expired, conflicting |
| Tenant isolation tests | Cross-domain fail closed |
| Property tests | Invariants |
| Fault injection | Atomic rollback |
| Concurrency tests | Version, race, duplicate |
| Leakage scan | Secrets, internal fields, foreign existence |
| Text integrity | Runtime strings, mojibake |
| Reproducible build | Два clean builds = same manifest |
| UI desktop/mobile | Surface читаем |
| Live readback | Tracking/readiness/UI согласованы |
| Checkpoint readback | Archive читается, совпадает |
| SAST | Static security |
| Dependency scan | Уязвимые зависимости |
| Secret scan | Утечки секретов |
| SBOM | Состав зависимостей |
| License scan | Лицензионная совместимость |

## Базовые команды

```text
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run architecture:test
npm.cmd run test:<current-stage>
npm.cmd test
npm.cmd run build
```

Имена focused scripts — из package.json.

Применимый набор классов зависит от protocol level (docs/45):
P0 — LINT/TYPECHECK/UNIT; P1 — матрица без fault/isolation; P2 — полная
матрица, включая fault/isolation, + профессиональные review-evidence.

## PASS semantics

PASS, только если:

1. Все применимые classes.
2. Expected = executed.
3. Failed = 0.
4. Critical stops = 0 или owner-accepted.
5. Fixture version/hash совпадают.
6. Build воспроизводим (для P1+).
7. Live readback соответствует evidence.
8. Missingness не скрыта.
9. First FAIL сохранён.
10. Owner принял evidence (с evidenceReadHash).

## Нельзя

писать PASS до запуска; менять expected; удалять failing test без обоснования;
считать skipped успешным; частичный suite за полный regression;
перезаписывать immutable receipt.

## Гейт-скрипт

Повторяемая проверка из 3+ команд оформляется одним гейт-скриптом:
собрать → тесты → вердикты одной таблицей. Один вызов — один ход агента —
один вердикт. Цепочки ручных команд по 3–5 ходов на шаг запрещены
(расход ходов — docs/41).
