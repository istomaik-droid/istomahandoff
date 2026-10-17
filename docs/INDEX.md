# INDEX — оглавление документов протокола

Одна строка на документ (docs/48). Тиры: M — must-read в начале работы
(agents/AGENT_CONTRACT); R — reference, читать по требованию, когда задача
попадает в scope документа.

| Документ | Тир | Назначение / когда читать |
| --- | --- | --- |
| docs/00 | R | Governance, роли, source control — при смене ролей, аудите, споре о полномочиях |
| docs/01 | R | Product boundary — что входит и не входит в продукт |
| docs/02 | R | Foundation boundary — границы foundation-слоя |
| docs/03 | R | Data и fixture strategy — работа с данными и фикстурами |
| docs/04 | R | Authentication и enrollment — аутентификация, регистрация |
| docs/05 | R | Budget и providers — расход, выбор провайдера, compression gateway, модель по классу задачи |
| docs/06 | R | Positioning и measurement — позиционирование, измерение результата |
| docs/07 | R | Connectivity, legal, privacy, security — связность, право, приватность |
| docs/08 | R | Delivery sequence и architecture readiness — порядок доставки, готовность архитектуры |
| docs/09 | M | Active state — шаблон состояния экземпляра (заполняется в проекте), enum состояний |
| docs/10 | M | Decision log — журнал решений DEC, формат записи |
| docs/11 | M | Handoff memo — формат мемо передачи |
| docs/12 | R | Risk classes — классы риска R0–R5 |
| docs/13 | R | Change rules — правила внесения изменений |
| docs/14 | R | Work package contract — контракт пакета работ |
| docs/15 | R | Change envelope — конверт изменения |
| docs/16 | R | State machine — переходы состояний, validate_transition |
| docs/17 | R | Инженерные практики — практики разработки |
| docs/18 | R | Security baseline — базовые требования безопасности |
| docs/19 | R | Data и checkpoint — checkpoint'ы, backup, checkpoint_create |
| docs/20 | R | Архитектурный закон — архитектурные инварианты |
| docs/21 | R | Identity, auth, session — идентичность и сессии |
| docs/22 | R | Authorization и tenant isolation — авторизация, изоляция |
| docs/23 | R | Strict ingress, commands, trusted time — вход, команды, время |
| docs/24 | R | Transaction, idempotency, audit, correction — транзакции, идемпотентность |
| docs/25 | R | Browser и request integrity — целостность браузерных запросов |
| docs/26 | R | Files, binary evidence, upload — файлы и загрузки |
| docs/27 | R | Offline boundary — границы офлайн-работы |
| docs/28 | R | Export, restore, recovery — экспорт и восстановление |
| docs/29 | R | AI и автоматизация — использование ИИ в продукте |
| docs/30 | R | Testing law — закон тестирования, гейт-скрипты |
| docs/31 | R | Evidence model — модель доказательств, receipts |
| docs/32 | R | Agent governance — управление агентом |
| docs/33 | R | Stop conditions — условия остановки, включая лимит ходов |
| docs/34 | R | Context recovery — восстановление контекста после потери |
| docs/35 | R | Incident handling — обработка инцидентов |
| docs/36 | R | Handoff — процедура передачи работы |
| docs/37 | R | Шаблоны решений владельца — формы записи решений |
| docs/38 | R | Release gates — гейты релиза, pre_deploy_check |
| docs/39 | R | Checklists — чеклисты процесса |
| docs/40 | R | Антипаттерны — типовые ошибки и их замены |
| docs/41 | R | Метрики — метрики протокола, стоимость |
| docs/42 | R | Maintenance — версионирование и порядок изменения протокола |
| docs/43 | R | Финальная формула — итоговая формула протокола |
| docs/44 | R | Границы enforcement — уровни E0–E3, честные пределы конвенции |
| docs/45 | R | Уровни протокола — P0/P1/P2 по классам риска |
| docs/46 | R | Мандаты владельца — deputy, evidenceReadHash, sampling audit |
| docs/47 | R | Миграция версий — переход work items между версиями протокола |
| docs/48 | R | Индекс и чтение по требованию — норма этого оглавления |
