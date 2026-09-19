# 12. Risk classes

| Класс | Пример | Действия | Уровень |
| --- | --- | --- | --- |
| R0 | Опечатка | Trace | P0 |
| R1 | Локальный рефакторинг | Tests + review | P0 |
| R2 | Логика внутри boundary | Tests + review + acceptance | P1 |
| R3 | API/схема/миграция/зависимость | Owner review + integration + ADR | P1 |
| R4 | Данные/authority/security | Professional review + owner decision | P2 |
| R5 | Provider/license/contractor/production | Spend/release decision | P2 |

## Правила

1. Агент не понижает класс.
2. Класс фиксируется в TRIAGE.
3. R4+ требует threat model.
4. R5 требует spend/release decision.
5. Класс задаёт protocol level по таблице; смешанный scope — по высшему.
