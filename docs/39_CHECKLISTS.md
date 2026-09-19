# 39. Checklists

Чеклисты масштабируются по protocol level (docs/45). P0 — ядро preflight
(agents/AGENT_PREFLIGHT.md).
P1 = ядро + стандартный блок. P2 = ядро + стандартный + полный блок.

## Расширенный чеклист (перед первой работой в сессии)

□ Workspace allowlist.
□ Последний DEC прочитан.
□ Active state прочитан (включая protocol.version/level).
□ Protocol level зафиксирован; enforcement достаточен для класса.
□ Active stage один.
□ Next stage locked.
□ Allowed и forbidden scope.
□ Data/network/spend boundary.
□ Незапланированные изменения отсутствуют.

## Ядро: перед первой mutation

□ Boundary owner-accepted.
□ Implementation authorization явная.
□ Allowed paths известны.
□ Rollback path.
□ Local tracking доступен.

(P0: pre-change checkpoint = git tag с readback; work package — короткая форма;
evidence = diff + test counts. P0 не освобождает от decision log.)

## Стандартный блок (P1 добавляет)

□ Required pre-change checkpoint verified (manifest + hash).
□ Work package заполнен полностью.
□ Acceptance и stop tests.
□ Full gates: integration/e2e/SAST/dependency/secret scan.
□ Reproducible build.
□ Live readback.
□ Expected и observed разделены; first FAIL сохранён.
□ Non-claims и missing facts.
□ Owner acceptance с evidenceReadHash.

## Полный блок (P2 добавляет)

□ Professional reviews с evidence.
□ Threat model для R4+.
□ Independent checkpoint readback + counters = 0.
□ EVIDENCE_READY snapshot неизменен.
□ Owner-accepted snapshot создан.
□ Acceptance receipt hashes совпадают.
□ Post-acceptance checkpoint отдельно разрешён и проверен.
□ Rollback anchor подтверждён владельцем.
□ Новый stage отдельно разрешён.
□ Для deputy: mandate действует, scope в пределах.
