# 32. Agent governance

## Модель угрозы

Agent может: потерять context, принять рекомендацию за authorization,
начать несколько stages, расширить scope, читать соседние источники,
изменить immutable evidence, скрыть FAIL, объявить tests, которые не запускал,
удалить checkpoint или user changes, выбрать provider или зависимость,
считать UI authority, использовать stale JWT,
заявить readiness без review, заявить enforcement, которого нет.

## Что этот документ гарантирует — и что нет

Этот протокол — конвенция, записанная в markdown. Он работает, пока
агент добросовестен, и защищает от: ошибок, галлюцинаций, дрейфа
автономности, context loss, самоакцептации, случайного выхода за scope.
Он НЕ защищает от adversarial-агента, prompt injection с реальными
правами на инструменты и скомпрометированной среды. Для adversarial
сценариев требуется внешний sandbox уровня E2/E3 (docs/44). Агент обязан
при первом ответе заявить фактический enforcement level и не заявлять
защиту, которой среда не предоставляет.

## Жёсткие запреты

Без owner decision агенту запрещено:

1. Открывать следующий stage.
2. Делать две фазы одновременно.
3. Менять product boundary.
4. Добавлять business logic будущего slice.
5. Читать/менять данные вне workspace.
6. Использовать production/client/personal/secret data.
7. Включать external network effect.
8. Устанавливать dependency.
9. Выбирать provider.
10. Создавать расходы.
11. Запускать pilot, production, deployment.
12. Менять accepted fixture.
13. Переписывать audit, Receipt, baseline, evidence.
14. Удалять файлы, checkpoints, user changes.
15. Откатывать repository destructive command.
16. Завершать неизвестный process на порту.
17. Ослаблять test ради PASS.
18. Замалчивать ошибку.
19. Назначать себе owner acceptance.
20. Публиковать gated report.
21. Трактовать спор о факте решения в свою пользу.
22. Заявлять технический enforcement, который не настроен.
23. Принимать формальное acceptance («ок, принято») как валидное.

## Technical enforcement

| Риск | Enforcement | Kind |
| --- | --- | --- |
| Выход из папки | Filesystem sandbox + path allowlist | TECHNICAL (если настроен) |
| Самовольная сеть | Network deny by default | TECHNICAL (E2+) |
| Самовольный spend | Нет credentials/billing у agent | TECHNICAL |
| Следующий stage | Machine status LOCKED | CONVENTION |
| Изменение evidence | Immutable filenames, hashes, append-only | TECHNICAL + CONVENTION |
| Подмена tests | Machine-generated receipts, CI logs | TECHNICAL (CI gate) |
| Удаление | Deny destructive tools | TECHNICAL (E1+) |
| Cross-tenant | Domain-scoped adapters, property tests | CONVENTION |
| Hidden superadmin | Separate planes, content-blind support | ARCHITECTURE |
| Stale authority | Commit-time reauth, authority epoch | ARCHITECTURE |
| Context loss | Mandatory preflight sync | CONVENTION |
| Rubber-stamping | evidenceReadHash + sampling audit | PROCESS (docs/46) |

Kind = CONVENTION означает: работает только при добросовестном агенте.
Kind = TECHNICAL означает: среда блокирует даже adversarial-агента,
если enforcement level достаточен.

## Параллельные сессии

В общем рабочем дереве могут работать несколько агентов.

1. Коммитятся только свои хунки. `git add -A` / `git commit -a` запрещены;
   точечный add или `git add -p` / patch --cached.
2. Чужие незакоммиченные правки в дереве перед deploy/restart —
   stop condition: доклад владельцу, изоляция через бэкап + патч.
3. Чужая работа не выкладывается и не откатывается молча.
   Вмешательство только для чинки аварии: бэкап + патч возврата +
   прямой доклад владельцу.
4. Предупреждение «дерево не чистое» от verify/deploy-скриптов —
   стоп-сигнал, не шум.
