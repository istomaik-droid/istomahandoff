---
name: preflight
description: Выводит preflight-чеклист протокола по уровню задачи с фактическими данными из ACTIVE_STATE и DECISION_LOG
type: prompt
whenToUse: Перед началом действий по задаче, при смене stage, при восстановлении контекста
---

Выполни preflight по agents/AGENT_PREFLIGHT.md для текущего protocol level.

1. Прочитай docs/09_ACTIVE_STATE.md, docs/10_DECISION_LOG.md, docs/11_HANDOFF_MEMO.md.
2. Определи protocol level (P0/P1/P2) и enforcement level из ACTIVE_STATE.
3. Выведи чеклист, соответствующий уровню, подставив фактические значения:
   - ядро (все уровни, 5 пунктов): последний DEC-ID, последний verified rollback anchor,
     active/locked stage и level, разрешённые/запрещённые изменения, data/network/spend boundary;
   - P1 добавляет пункты 6–11 (checkpoint, файлы, тесты, locked stage, evidenceReadHash);
   - P2 добавляет пункты 12–13 (enforcement-достаточность, mandate check).
4. Если пункт неизвестен — остановись и запроси только недостающую существенную информацию.
5. Признак заниженного уровня — назови его и предложи повысить level (docs/45).

Не начинай действий по задаче до заполнения всех пунктов уровня.
