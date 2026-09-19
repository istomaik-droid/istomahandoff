# 37. Шаблоны решений владельца

Не являются authorization, пока владелец явно не подтвердил.

## Boundary

```text
Разрешаю подготовить только документную границу <STAGE> в <SCOPE>.
Разрешаю определить outcome, actors, authority, data scope, state machine,
acceptance, stop, rollback, fixture и non-claims. Реализацию, реальные данные,
providers/effects/spend, pilot, production и deployment не начинать.
Следующий этап автоматически не открывать. По завершении представить точную
декомпозицию и отдельную рекомендацию владельцу.
```

## Implementation

```text
Подтверждаю проверенный rollback anchor <ANCHOR/SHAS>.
Разрешаю начать только <STAGE> в local synthetic ZERO-SPEND границе.
Уровень протокола: <P?>. Enforcement: <E?>.
Разрешено: <EXACT ALLOWLIST>.
Запрещено: <EXACT DENYLIST>.
Обязательны current authority, commit-time reauthorization, audit, Receipt,
idempotency, tenant isolation, fault tests, deterministic build, live preview
и evidence. Следующий этап автоматически не открывать. По завершении
представить tests, evidence, live readback и рекомендацию для owner acceptance.
```

## Owner acceptance

```text
Подтверждаю <STAGE>. Я прочитал evidence по хэшу <EVIDENCE_SHA256>.
Принимаю представленные evidence и технический результат <RESULT> строго
в <BOUNDARY>. Протокол уровень <P?>. Сохраняю <NON-CLAIMS/BLOCKERS>.
Следующий этап автоматически не открывать. Разрешаю зафиксировать owner
acceptance. Перед следующим этапом обязательны post-acceptance checkpoint,
его полная проверка и отдельное явное разрешение владельца.
```

Acceptance без строки «Я прочитал evidence по хэшу …» невалиден (docs/46).

## Post-acceptance checkpoint

```text
Разрешаю создать и полностью проверить post-acceptance checkpoint принятого
состояния <DECISION>. Checkpoint должен включать exact owner-accepted status,
immutable EVIDENCE_READY и owner-accepted snapshots, technical/acceptance
receipts, UI verification, live-readback и integrity evidence; исключать
dependencies, runtime state, caches, deterministic build output и recursive
archives. Обязательны persistent manifest, SHA-256 sidecar, creation readback,
independent repeat readback и нулевые mismatch/safety counters. Следующий
этап автоматически не открывать.
```

## Пауза

```text
СТОП. Новые изменения, процессы, checkpoint и переходы запрещены.
Зафиксируй current state, уже сделанные изменения, tests и открытые риски.
Не откатывай файлы без отдельного разрешения.
```

## Defect correction

```text
Разрешаю исправить только дефект <ID> внутри принятой границы <STAGE>.
Новую business logic и следующий stage не открывать. Сохранить исходный FAIL,
добавить regression test, повторить применимые gates и представить correction
evidence отдельно от исходного evidence.
```

## Мандат deputy (оформляется отдельно, см. templates/MANDATE.md)

```text
Выдаю мандат MANDATE-XXXX <NAME> на <SCOPE>, maxRiskClass <R?>,
действует до <ISO8601>. Не покрывает: R5, release, product boundary, spend.
Отзыв — однострочным решением в decision log.
```
