# 34. Context recovery

Если agent перезапущен, разговор обрезан, непонятно, где остановились:

1. Не менять файлы.
2. Прочитать этот протокол.
3. Прочитать tail ACTIVE_STATE.
4. Прочитать последние решения в decision log.
5. Прочитать tail HANDOFF_MEMO.
6. Прочитать active machine status.
7. Найти последний owner-acceptance receipt.
8. Найти последний verified rollback anchor.
9. Пересчитать hashes.
10. Сравнить server status, readiness, UI.
11. Убедиться, что next stage locked.
12. Сверить protocol.version и protocol.level с ACTIVE_STATE;
    при несовпадении — STOPPED_PROTOCOL_MISMATCH до решения MIGRATION.
13. Только после совпадения — продолжение.

Запрещено восстанавливать context только по памяти модели.
Запрещено восстанавливать context по истории переписки — в том числе
сжатой compression gateway; источник восстановления — документы (пп. 2–9).
Запрещено трактовать молчание владельца как разрешение при споре
о факте решения.
