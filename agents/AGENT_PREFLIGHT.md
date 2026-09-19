# Agent preflight

Перед каждым действием вывести список соответствующий protocol level.

## Ядро (все уровни, 5 пунктов)

```text
1. Последний accepted decision (DEC-ID).
2. Последний verified rollback anchor.
3. Текущий active/locked stage и protocol.level.
4. Разрешённые и запрещённые изменения.
5. Data/network/spend boundary.
```

## Стандартный блок (P1 добавляет, пункты 6–11)

```text
6. Нужен ли checkpoint до mutation и его вид (git tag / manifest).
7. Какие файлы будут прочитаны.
8. Какие файлы будут изменены.
9. Какие tests будут запущены (имена скриптов).
10. Какой следующий stage останется locked.
11. Для acceptance-подобных действий: evidenceReadHash зафиксирован.
```

## Полный блок (P2 добавляет, пункты 12–13)

```text
12. Enforcement level достаточен для risk class (инаже STOP).
13. Mandate check: если действует deputy — scope и expiry мандата.
```

Если пункт неизвестен — остановиться и запросить только недостающую
существенную информацию.

Признак заниженного уровня — повысить level и перезапустить preflight
полного набора (docs/45).
