# 36. Handoff

## Минимальный пакет

1. Этот документ (с указанием версии протокола).
2. Current active state (включая protocol.version/level/enforcement).
3. Decision log.
4. Handoff memo.
5. Current stage boundary.
6. Last owner-acceptance receipt.
7. Last verified rollback anchor и hashes.
8. Active fixture version.
9. Architecture/ADR references.
10. Test commands и expected suites.
11. Local ports/start/stop или CI/CD команды.
12. Open risks, blockers, missing facts, non-claims.
13. Записи MANDATE-XXXX в decision log и activeMandates в ACTIVE_STATE, если deputy действует (docs/46).

Secrets, credentials, production data не передаются.

## Обязательный первый ответ агента

```text
Я прочитал current state и зафиксировал:
- версия протокола: <SEMVER>;
- protocol level: <P0/P1/P2>;
- enforcement level: <E0–E3> (фактический, заявленный средой);
- последнее решение: <DEC>;
- accepted predecessor: <state>;
- rollback anchor: <VERIFIED | NOT_VERIFIED | MISSING>;
- active scope: <scope>;
- forbidden scope: <scope>;
- data boundary: <boundary>;
- network/spend boundary: <boundary>;
- next stage: LOCKED;
- первая безопасная операция: <operation>.

До отдельного разрешения я не начну следующий stage и не расширю scope.
Если enforcement ниже заявленного — я заявлю об этом вместо продолжения.
```

Если ответ содержит предположение вместо verified state — handoff не принят.

## Acceptance внешнего агента

Agent готов, если может: указать последнее решение; назвать последний
rollback anchor; объяснить разницу EVIDENCE_READY и OWNER_ACCEPTED;
назвать local ports или CI/CD jobs; объяснить, почему UI не authority;
назвать текущий locked stage; перечислить stop conditions;
показать exact test plan; подтвердить запрет production data,
network effects, spend; объяснить границы enforcement (docs/44);
объяснить, почему решение без evidenceReadHash невалидно (docs/46).
