# MCP-сервер протокола istomahandoff

MCP-сервер (stdio) поверх канона протокола: нормы в коде не дублируются.
Два корня (DEC-0018, `adr/ADR-0001-kit-instance.md`): канон — кит, в котором
лежит сервер (`docs/`, `agents/`, `skills/`, `templates/`, только чтение);
экземпляр — проект из `ISTOMAHANDOFF_PROJECT` (docs/09, docs/10, docs/11,
evidence/ и его git-репозиторий).

## Что даёт

- Resources: `protocol://docs/<NN_NAME>` и `protocol://docs/INDEX` —
  документы docs/ (docs/10 — схема и правила без записей кита),
  `protocol://agents/<NAME>`, `protocol://templates/<NAME>`,
  `protocol://istomahandoff`.
- Prompts: 5 процедур из skills/ (preflight, decision, handoff, incident,
  verify) — тела SKILL.md как prompt messages.
- Tools канона (работают и без проекта): `read_canon` (те же файлы, а
  также `adr/ADR-NNNN-*.md`, этот README и `.mcp.json.example` — по белому
  списку, для рантаймов, которые не показывают resources),
  `validate_transition` (парсит docs/16), `protocol_version` (docs/42 и
  ревизия кита), `protocol_lint` (кит или экземпляр).
- Tools экземпляра: `record_decision`, `checkpoint_create` (git tag с
  readback, docs/19), `pre_deploy_check` (гейт чистого дерева, docs/38),
  `get_active_state`, `evidence_hash`, `list_expired`, `audit_sample`
  (docs/46).

## Запуск

```bash
pip install -r mcp_server/requirements.txt   # в .venv кита
ISTOMAHANDOFF_PROJECT=<абсолютный путь к проекту> python <кит>/mcp_server/server.py

# HTTP-режим (VPS, DEC-0009/DEC-0010): только loopback, доступ — SSH-туннель
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8000 python <кит>/mcp_server/server.py
ssh -L 8000:127.0.0.1:8000 <vps>   # с машины владельца
```

Подключение к рантаймам — см. `.mcp.json.example` и раздел «MCP-сервер»
в `agents/AGENT_RUNTIMES.md`. HTTP-режим — только на loopback, публичный
биндинг запрещён (DEC-0009, DEC-0010); при другом MCP_HOST SDK не включает
защиту от DNS rebinding.

## Два корня и охрана записи (DEC-0018)

- Канон — родитель `mcp_server/`; проект — абсолютный путь из
  `ISTOMAHANDOFF_PROJECT`, единственного ключа записи. `CLAUDE_PROJECT_DIR`
  от Claude Code (передаётся stdio-серверу — проверено в П2, DEC-0019) даёт
  только чтение и сверку: заданы оба и указывают в разные каталоги —
  отказ. `ISTOMAHANDOFF_ROOT` не
  поддерживается: с ней сервер не стартует. Корень проекта проверяется при
  старте: после исправления env или каталога нужен перезапуск сессии.
- Fail-closed: без проекта, с проектом-китом или каталогом внутри кита
  (сравнение по идентичности каталогов — префикс `\\?\` и UNC-алиасы не
  обходят), без docs/10 в проекте (подсказка — `tools/instance_init.py`)
  или с docs/09, docs/10 проекта, ведущими в кит по ссылке, tools
  экземпляра отказывают; tools канона, resources и prompts доступны.
- `record_decision` и `checkpoint_create` отказывают также, если канон
  (`istomahandoff.md` и docs/16) лежит в корне проекта или его
  git-репозитория (клон протокола или проект с копией кита); кит — не
  отдельный git-клон (или git недоступен); кит был изменён на месте при
  старте сервера (загружен код не из HEAD); у отслеживаемых файлов кита
  есть незакоммиченные изменения; HEAD кита сменился после старта (нужен
  перезапуск сессии); вызов пришёл по HTTP — по `MCP_TRANSPORT=http` или
  по самому запросу (SSE, streamable-http при любом способе запуска).
  Git-проверки кита его не меняют (`--no-optional-locks`); переменные
  `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` и подобные из окружения
  рантайма git-tools не наследуют.
- Enum типов решений — из схемы docs/10 кита (до «## Записи»); копия схемы
  в журнале проекта не читается. Записи журнала кита наружу не отдаются.
- `protocol_version` — версия кита (последняя строка docs/42), ревизия кита
  (`loadedHead` и `loadedDirty` — код, загруженный сервером, `canonHead` и
  `canonDirty` — на диске, `canonTag` — релизный тег `kit-vX.Y`) и
  `protocol.version` из docs/09 проекта (`projectVersion`, `match`,
  `versionsSince`) — факты для docs/34 п.12; поле `project` — корень,
  который агент сверяет со своим до первой записи.
- `protocol_lint` исполняет lint кита: с проектом — `--project` (журнал и
  docs/09 проекта по схеме кита, копии кита в проекте, импорт записей
  журнала протокола); без проекта или при неверном проекте — lint самого
  кита (`target: canon`, ошибка проекта — в `projectError`); копия lint в
  проекте не исполняется.

## Запись решений (DEC-0011, DEC-0016)

`record_decision` дописывает запись в docs/10 проекта. Отклоняются:
переводы строк, управляющие и невидимые символы форматирования в полях
(иначе в журнал дописалась бы поддельная запись или скрытый текст); пустые
по смыслу значения (пробелы, `null`, `[]`); evidenceReadHash не в формате
sha256; expiresAt не в формате ISO8601; решение deputy без mandateRef вида
`MANDATE-XXXX`. Владелец пишется как `owner: OWNER` — как во всех записях
docs/10; любое другое значение owner считается deputy.

По умолчанию запись остаётся незакоммиченной — её коммитят вместе с
изменением. Авто commit+push включает `ISTOMAHANDOFF_AUTOSYNC=1` — только у
единственного писателя журнала, которого называет решение владельца.
Тогда сервер:

- отказывает до записи, если HEAD не на ветке, в docs/10 есть
  незакоммиченные правки, upstream-ветка не найдена, ветка разошлась с
  upstream или клон отстаёт от него (после `git fetch`);
- коммитит только docs/10; если коммит не удался, запись откатывается;
- пушит, только если в коммите решения нет других файлов и среди
  неотправленных коммитов нет чужих; свои решения, не ушедшие после сбоя,
  досылаются со следующим. Иначе `pushed: false` и `reason`:
  `COMMIT_NOT_ONLY_LOG`, `EXTRA_COMMITS`, `FETCH_FAILED`, `NO_UPSTREAM`,
  `PUSH_FAILED`. При `FETCH_FAILED` номер не сверен с upstream — возможен
  дубль DEC-ID (рецепт — в `note` ответа).

Инстанс на VPS (DEC-0012) работает в HTTP-режиме из клона, в котором
лежит и его журнал. С версии 2.15 запись в HTTP-режиме закрыта при любом
`ISTOMAHANDOFF_AUTOSYNC`, а журнал внутри кита — не проект: tools
экземпляра там откажут. Обновление VPS — отдельное решение (ADR-0001,
Non-claims).

`record_decision` и `checkpoint_create` помечены
`_meta["anthropic/requiresUserInteraction"]`: интерактивный Claude Code
спрашивает человека на каждый вызов, даже в режимах auto и bypass; в режиме
dontAsk и через `--permission-prompt-tool` вызов отклоняется; в приложениях
на Agent SDK решение принимает их `canUseTool`. Другие рантаймы флаг не
читают — в Kimi Code запись закрывается списком tools в конфиге
(agents/AGENT_RUNTIMES.md).

## Гейты (DEC-0017)

- `pre_deploy_check(own_files)` — изменения по `git status -z`: кириллица и
  пробелы в именах, файлы внутри новых каталогов, обе стороны
  переименования. own_files — пути относительно корня репозитория (поле
  `repo` ответа); каталог в own_files не покрывает файлы внутри. Списки
  `changed`/`foreign` обрезаются до 200 путей (`truncated: true`), счётчики
  `changedCount`/`foreignCount` — полные.
- `checkpoint_create(label)` — отказ, если у отслеживаемых файлов есть
  незакоммиченные изменения; поэтому запись решения (BOUNDARY перед
  pre-change) коммитится отдельным коммитом до checkpoint. Тег annotated —
  нужны git user.name и user.email в этом репозитории; тег только локальный
  (`pushed: false`), неотслеживаемые файлы — в `untracked`
  (`untrackedCount`).
- `validate_transition(from, to)` — `VALID` (шаг цепочки или аварийный
  переход из ANY_STATE), `FORBIDDEN` (недопустимый переход или прыжок через
  стадии, docs/33 п.21), `UNKNOWN` (в docs/16 не описан), `CONDITIONAL`:
  при `kind: chain` шаг недопустим, если выполняется `forbiddenWhen`
  (условие запрета docs/16); при `kind: emergency` переход допустим, только
  если текущее состояние подпадает под `requiresState` и/или выполнено
  `allowedWhen`.

## Ограничения (честно)

- Сервер работает с правами агента, который его вызывает; отдельной
  изоляции нет. В HTTP-режиме аутентификации нет: любой локальный процесс
  хоста может вызвать tools (запись в нём закрыта, чтение — нет).
- Enforcement — только для добросовестного пути (E1–E2 по docs/44):
  сервер напоминает, валидирует и отказывает на уровне своих tools,
  но adversarial-агент может просто не вызывать его или править файлы
  напрямую. Это не защита от adversarial (docs/44).
- `record_decision` пишет только в docs/10 и только append; поле
  receiptSha256 сервер не вычисляет (null).
- Git-tools работают в репозитории проекта из `ISTOMAHANDOFF_PROJECT`, а
  не в репозитории агента. Ответы tools экземпляра (кроме текстового
  `get_active_state`) и `protocol_version` содержат `project`, git-tools —
  ещё и `repo`; их нужно сверять со своим корнем, до первой записи — через
  `protocol_version`. Ошибочный путь в env сервер ловит только в случаях
  охраны записи (канон в проекте, кит).
- Сервер держит загруженный код до перезапуска: после `git pull` кита
  запись отказывает, пока сессия рантайма не перезапущена.
- Флаг requiresUserInteraction — не доказательство участия владельца:
  сервер не получает подтверждения, что запрос видел человек.
- Таймаут есть только у сетевых git-операций (fetch, push); на Windows он
  не обрывает дочерние процессы git, и вызов может длиться дольше.
- Файлы с флагами skip-worktree и assume-unchanged `git status` не
  показывает — их правки гейты не видят.
- State machine и enum типов решений парсятся из docs/16 и docs/10 кита
  при каждом вызове; при смене формата этих файлов парсер нужно
  пересмотреть.
