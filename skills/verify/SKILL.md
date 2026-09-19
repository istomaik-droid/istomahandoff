---
name: verify
description: Запускает проектную verify-команду из PROJECT_PROFILE и оформляет результат как evidence
type: prompt
whenToUse: После правок кода, перед коммитом, перед evidence-ready и acceptance
---

Выполни проверку по протоколу и оформи результат.

1. Прочитай templates/PROJECT_PROFILE.yaml (или заполненный профиль проекта) — секция
   protocolMapping: verify_command, staging_env.
2. Запусти verify_command из рабочего корня. Если команда не задана — минимум:
   компиляция/синтаксис изменённых файлов + тесты по docs/30 для текущего уровня
   (P0: lint/typecheck/unit; P1: матрица без fault/isolation; P2: полная).
3. Мутирующие тесты — только против staging_env (docs/03), не против прода.
4. Выведи фактические counts и команды (agents/AGENT_PROGRESS.md):
   PASS/FAIL по каждой проверке, числа тестов, длительность.
5. Оформи evidence по docs/31: результат + хэш (sha256 вывода/артефакта) — под
   evidenceReadHash будущего acceptance. FAIL не переименовывается и не замалчивается.

«Готово» — только после фактического прохождения проверок. Не проверено — так и пиши.
