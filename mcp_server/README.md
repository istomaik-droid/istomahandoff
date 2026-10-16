# MCP-сервер протокола istomahandoff

MCP-сервер (stdio) поверх канона протокола: нормы в коде не дублируются,
сервер читает `docs/`, `agents/`, `skills/` из репозитория.

## Что даёт

- Resources: `protocol://docs/<NN_NAME>` — документы docs/,
  `protocol://agents/<NAME>` — инструкции agents/.
- Prompts: 5 процедур из skills/ (preflight, decision, handoff, incident,
  verify) — тела SKILL.md как prompt messages.
- Tools: `protocol_lint`, `record_decision`, `get_active_state`,
  `evidence_hash`, `validate_transition` (парсит docs/16),
  `list_expired`, `audit_sample` (docs/46), `protocol_version` (docs/42),
  `checkpoint_create` (git tag с readback, docs/19), `pre_deploy_check`
  (гейт чистого дерева, docs/38).

## Запуск

```bash
pip install -r mcp_server/requirements.txt
python mcp_server/server.py   # stdio-транспорт (локальный агент)

# HTTP-режим (VPS, DEC-0009/DEC-0010): только loopback, доступ — SSH-туннель
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8000 python mcp_server/server.py
ssh -L 8000:127.0.0.1:8000 <vps>   # с машины владельца
```

Подключение к рантаймам — см. `.mcp.json.example` и раздел «MCP-сервер»
в `agents/AGENT_RUNTIMES.md`. Корень репозитория — родитель `mcp_server/`
либо переменная окружения `ISTOMAHANDOFF_ROOT` (один сервер может
обслуживать другой проект без копирования). HTTP-режим — только на
loopback, публичный биндинг запрещён (DEC-0009, DEC-0010); при другом
MCP_HOST SDK не включает защиту от DNS rebinding.

## Запись решений (DEC-0011, DEC-0016)

`record_decision` дописывает запись в docs/10 корня сервера. Отклоняются:
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

Инстанс, где авто-синхронизация работала по DEC-0011 (VPS, DEC-0012),
после обновления до этой версии перестаёт коммитить, пока в его юнит не
добавлен `Environment=ISTOMAHANDOFF_AUTOSYNC=1`; добавлять — только по
решению, которое назначает его единственным писателем.

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
  хоста может вызвать tools.
- Enforcement — только для добросовестного пути (E1–E2 по docs/44):
  сервер напоминает, валидирует и отказывает на уровне своих tools,
  но adversarial-агент может просто не вызывать его или править файлы
  напрямую. Это не защита от adversarial (docs/44).
- `record_decision` пишет только в docs/10 и только append; поле
  receiptSha256 сервер не вычисляет (null).
- Git-tools работают в репозитории корня сервера, а не в репозитории
  агента; ответ содержит `repo` — его нужно сверять со своим корнем.
- Флаг requiresUserInteraction — не доказательство участия владельца:
  сервер не получает подтверждения, что запрос видел человек.
- Таймаут есть только у сетевых git-операций (fetch, push); на Windows он
  не обрывает дочерние процессы git, и вызов может длиться дольше.
- Файлы с флагами skip-worktree и assume-unchanged `git status` не
  показывает — их правки гейты не видят.
- State machine и enum типов решений парсятся из docs/16 и docs/10 при
  каждом вызове; при смене формата этих файлов парсер нужно пересмотреть.
