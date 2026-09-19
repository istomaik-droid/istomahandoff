# 33. Stop conditions

Работа останавливается, если:

1. Нет owner authorization.
2. Pre-state не соответствует.
3. Checkpoint отсутствует или hash не совпадает.
4. Незапланированное изменение не агентом.
5. Выход за allowed path.
6. Production/client/personal/secret data.
7. Fixture активируется или меняется без owner decision.
8. Cross-domain leak.
9. Block/revoke/termination не останавливает action.
10. Mutation без audit/Receipt.
11. Retry создаёт второй effect.
12. Client field влияет на trusted context.
13. Approved source можно silently overwrite.
14. Unknown transport = acceptance/payment/signature.
15. Test/build/hash невоспроизводим (для P1+).
16. Expected и observed смешаны.
17. Professional blocker закрыт без reviewer evidence.
18. Agent выбирает provider/spend/deployment.
19. Неизвестный process занял порт.
20. Offline-first или auto-merge без решения.
21. Stage skip/merge/parallel без owner decision.
22. Missing evidence выдаётся за PASS.
23. Critical security/harm event.
24. Спор о том, было ли owner decision.
25. Protocol level не зафиксирован в ACTIVE_STATE.
26. Enforcement level ниже требуемого для risk class.
27. Решение ACCEPTANCE/RELEASE без evidenceReadHash.
28. Решение deputy вне мандата или после expiry.
29. Несовпадение protocol.version или protocol.level с ACTIVE_STATE (STOPPED_PROTOCOL_MISMATCH).

## При stop event

```text
STOP_ID
observedAt
source/evidence
possible impact
mutations already made
rollback availability
safe current state
owner decision required
```
