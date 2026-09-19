# 00. Governance и source control

## Обязательные вопросы

1. Кто единственный Product Owner.
2. Кто Owner Deputy и в пределах какого мандата (docs/46).
3. Где находится единственный разрешённый workspace.
4. Какие материалы — источники, какие — история.
5. Как ведутся decision log, risk classes (docs/12), acceptance, memo.
6. Как агент сообщает о progress, FAIL, unknown.
7. Какие действия требуют отдельного подтверждения.
8. Как запрещается автоматическое открытие следующего этапа.
9. Branching strategy, protected branches, PR/MR rules.
10. Commit signing.
11. CI/CD провайдер и обязательные gates.
12. Protocol level по умолчанию (до TRIAGE) и для типовых задач (docs/45).
13. Enforcement level среды и минимальный уровень для каждого risk class (docs/44).
14. Кто Sampling Auditor и как часто производится выборочная перепроверка (docs/46).

## Результат

`GOVERNANCE_READY` — но не разрешение на код.
GOVERNANCE_READY — статус готовности блока старта, не состояние state machine work item.
GOVERNANCE_READY требует записанного механизма мандатов, зафиксированных
protocol/enforcement levels и назначенного аудитора выборки.
PROJECT_PROFILE обязан содержать маппинг правил протокола на проектную
конкретику (команды, среды, файлы журнала).

## Роли

| Роль | Ответственность |
| --- | --- |
| Product Owner | Authority: границы, риск, бюджет, release |
| Owner Deputy | Только в пределах мандата; R5/release/product boundary/spend — нет (docs/46) |
| Agent | Исполнитель без authority |
| Developer | Выполняет принятый work package |
| Technical Reviewer | Human code review |
| Sampling Auditor | Выборочная перепроверка решений владельца |
| Security / Privacy / Legal / Data / Ops | Только свои области |
