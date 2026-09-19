# 19. Data и checkpoint

## Data classification

| Класс | Обработка |
| --- | --- |
| Public | Свободно |
| Internal | Ограниченный доступ |
| Confidential | Шифрование, audit |
| Restricted | Минимальный доступ, шифрование, retention |

## Retention и deletion

Purpose, retention policy, legal hold, deletion procedure,
verification, audit.

## Backup 3-2-1

3 копии, 2 носителя, 1 offsite, шифрование,
restore drills, RPO/RTO, rehearsed DR.

## Когда нужен checkpoint

| Checkpoint | Момент | Назначение |
| --- | --- | --- |
| Pre-change | После boundary, до mutation | Возврат к принятому состоянию |
| Post-acceptance | После acceptance | Rollback anchor результата |

Checkpoint не создаётся автоматически.

Полнота процедуры зависит от protocol level: P0 — git tag с readback;
P1 — manifest + SHA-256 sidecar + creation readback; P2 — независимый
source-aware readback + archive-only readback + counters (docs/45).

## Полная процедура (P2)

1. Owner decision.
2. Проверить exact accepted pre-state.
3. Source inventory.
4. Фильтр forbidden entries.
5. Отказ от unsafe path, duplicate, explicit link.
6. Manifest: path, length, SHA-256.
7. Archive/tag/snapshot.
8. SHA-256 sidecar.
9. Creation readback.
10. Independent source-aware readback.
11. Archive-only readback.
12. Accepted-state artifacts.
13. Counters.
14. Checkpoint receipt.
15. Re-read receipt и archive.
16. Представить anchor, hash, manifest hash, counters.

## Успешный checkpoint

```text
missing = 0
unexpected = 0
sourceMismatch = 0
lengthMismatch = 0
hashMismatch = 0
duplicates = 0
forbiddenEntries = 0
unsafePaths = 0
explicitLinks = 0
acceptedStateMismatch = 0
```

## Исключать

dependencies, runtime state, caches, deterministic build output,
logs, PID, temp, recursive archives, secrets, credentials, tokens,
unsafe links.
