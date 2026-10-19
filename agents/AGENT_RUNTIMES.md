# Agent runtimes: как подключить протокол

Канон — файлы установленного кита (отдельный клон этого репозитория):
`agents/`, `skills/`, `docs/`, `templates/`; в проекты он не копируется
(«Размещение»). Каждый рантайм получает (1) главный файл инструкций и
(2) скиллы — по своему механизму. Содержимое одинаковое, различается только
размещение.

## Главный файл инструкций (минимум, одинаков для всех)

```text
Этот проект работает по протоколу istomahandoff.
Главное правило: НЕТ ЯВНОГО РЕШЕНИЯ ВЛАДЕЛЬЦА = НЕТ ПРАВА НА ДЕЙСТВИЕ.
Канон — установленный кит, только чтение: MCP-ресурсы protocol://… или
tool read_canon (istomahandoff.md, docs/NN, agents/, skills/, templates/).
Кит на диске — <путь к киту>: он вне workspace, его файлы читают, только
если это разрешено решением о подключении проекта.
Экземпляр — этот проект: docs/09, docs/10, docs/11, evidence/,
templates/PROJECT_PROFILE.yaml читаются из проекта (read_canon и
protocol:// отдают для этих путей шаблоны кита).
До первого чтения состояния и первой записи через MCP вызови
protocol_version: поле project должно совпасть с корнем этого проекта,
иначе — стоп и вопрос владельцу.
Перед работой прочитай agents/AGENT_CONTRACT.md и выполни обязательный
первый ответ. Действия: skills/preflight, decision, handoff, incident,
verify — по ситуации (whenToUse в каждом SKILL.md).
```

## Kimi Code

- Главный файл: `AGENTS.md` в корне проекта — вставить блок выше.
- Скиллы: копия `skills/*` кита в `~/.kimi-code/skills/` (user scope),
  обновляется вместе с китом; проектные копии не заводятся.
- Вызов: Skill `preflight`, `decision`, `handoff`, `incident`, `verify`.

## Claude Code

- Главный файл: `CLAUDE.md` в корне проекта — вставить блок выше.
- Скиллы: prompts сервера (`/mcp__istomahandoff__<имя>`); без сервера —
  копия `skills/*` кита в `~/.claude/skills/` (user scope), обновляется
  вместе с китом.
- Вызов: `/preflight`, `/decision`, `/handoff`, `/incident`, `/verify`.

## Codex / GPT

- Главный файл: `AGENTS.md` в корне проекта — вставить блок выше.
- Механизма скиллов нет: процедура читается из кита —
  `read_canon("skills/<имя>/SKILL.md")` по условию из whenToUse; без MCP —
  раздел AGENTS.md «При <условие из whenToUse> — выполни:» со ссылкой на
  SKILL.md кита или с inline-копией, которая обновляется при каждом
  обновлении кита.
- Вызов: по имени процедуры в тексте («выполни preflight»).

## Cursor

- Главный файл: правило `.cursor/rules/istomahandoff.mdc` с блоком выше.
- Скиллы: механизма нет — как у Codex.
- MCP поддерживается: проектный `.cursor/mcp.json` («Подключение»).

## Gemini CLI

- Главный файл: `GEMINI.md` в корне проекта — вставить блок выше.
- Скиллы: как у Codex (read_canon или раздел в GEMINI.md).

## Адаптация под возможности модели

Длинные инструкции деградируют на слабых моделях: пункты начинают
пропускаться. Правило: слабая/локальная модель — protocol level P0,
минимум текста инструкций, максимум переносится в MCP-tools (tool отказывает
сам, модель не обязана помнить норму). Сильная модель — полный набор.

## MCP-сервер

MCP-сервер — предпочтительный способ, скиллы-копии — fallback.
Сервер (`<кит>/mcp_server/server.py`, stdio) отдаёт канон docs/ и agents/
как resources, процедуры skills/ как prompts и добавляет tools
(protocol_lint, record_decision, validate_transition, read_canon и др. —
см. `mcp_server/README.md`). Нормы в коде не дублируются: сервер читает
файлы кита.

### Размещение

Два корня (`adr/ADR-0001-kit-instance.md`, DEC-0018).

- Канон — установленный кит: отдельный чистый клон этого репозитория на
  машине. Он меняется только `git pull --ff-only` слитого master с зелёным
  CI, сервер запускается из его `.venv` (`pip install -r
  mcp_server/requirements.txt`) и кит только читает. Откат — checkout
  предыдущего тега `kit-vX.Y`, пока экземпляры не мигрировали на новую
  версию; после миграции — исправление вперёд новой версией (понижение
  версии запрещено, docs/47 п.7).
- Экземпляр — проект: абсолютный путь в `ISTOMAHANDOFF_PROJECT` (env
  проектного конфига сервера). Файлы экземпляра лежат в проекте на прежних
  путях — docs/09, docs/10 (свой блок «## Записи»), docs/11, evidence/,
  templates/PROJECT_PROFILE.yaml — и создаются
  `python <кит>/tools/instance_init.py <проект>`.
- `ISTOMAHANDOFF_PROJECT` — единственный ключ записи: он появляется в
  конфиге проекта по решению владельца о подключении проекта; то же решение
  фиксирует право читать файлы кита вне workspace (agents/AGENT_CONTRACT).
  `CLAUDE_PROJECT_DIR` Claude Code передаёт stdio-серверу (проверено в П2,
  DEC-0019) — она даёт только чтение и сверку: заданы оба и расходятся —
  отказ. С `ISTOMAHANDOFF_ROOT` сервер не стартует.
- Fail-closed: без проекта, с проектом-китом или каталогом внутри кита,
  без docs/10 в проекте tools экземпляра (record_decision,
  checkpoint_create, pre_deploy_check, get_active_state, list_expired,
  audit_sample, evidence_hash) отказывают; канон (resources, prompts,
  validate_transition, protocol_version, read_canon, lint кита) доступен.
- record_decision и checkpoint_create отказывают также, если канон лежит в
  корне проекта или его git-репозитория (клон протокола или проект с копией
  кита), кит — не отдельный git-клон, кит изменён на месте (в том числе при
  старте сервера) или обновлён после старта (нужен перезапуск сессии),
  вызов пришёл по HTTP.
- Рабочий клон протокола — обычный проект для установленного кита: чтение и
  pre_deploy_check работают, запись решений и checkpoint_create через MCP
  закрыты; журнал протокола ведётся вручную через pull request (DEC-0016
  протокола); особенности клона — в его AGENTS.md.
- Ответы tools экземпляра (кроме текстового get_active_state) и
  protocol_version содержат `project`, git-tools — ещё и `repo`,
  protocol_lint — `root`; корень проекта сверяют через protocol_version до
  первой записи (главный файл).
- Версии: annotated-теги `kit-vX.Y` на строки docs/42. Minor мигрирует по
  docs/47 п.5 (порядок — docs/34 п.12); major — только решение MIGRATION
  владельца. In-flight work item, который остаётся на старой версии,
  получает отдельный worktree кита на её теге — до `git pull` новой major
  (сервер этого worktree — в конфиге проекта).
- Авто commit+push журнала (`ISTOMAHANDOFF_AUTOSYNC=1`) включается только
  у единственного писателя docs/10; без неё запись остаётся в рабочем
  дереве (mcp_server/README.md).

### Подключение

- Проектный `.mcp.json` в корне git-репозитория проекта по образцу
  `.mcp.json.example` — python из `.venv` кита, `<кит>/mcp_server/server.py`
  и `env.ISTOMAHANDOFF_PROJECT` — читают и Claude Code, и Kimi Code: один
  конфиг на оба рантайма.
- Kimi Code (расширение 0.8.2, по его коду; DEC-0019) читает три слоя:
  пользовательский `~/.kimi-code/mcp.json`, `.mcp.json` корня
  git-репозитория и `.kimi-code/mcp.json` каталога сессии. Поздний слой
  целиком заменяет запись с тем же именем сервера (поля не сливаются),
  проектные слои читаются только в доверенном workspace. Поэтому старый
  `.kimi-code/mcp.json` проекта перекрывает его `.mcp.json`, а проектная
  запись содержит команду, args и env полностью. Пользовательская запись —
  тот же сервер без `ISTOMAHANDOFF_PROJECT` и только чтение канона:
  `"enabledTools": ["protocol_lint", "validate_transition",
  "protocol_version", "read_canon"]`. Проверка в сессии — поле `canon`
  ответа `protocol_version` (путь кита).
- Claude Code: проектный `.mcp.json` (подтверждается при первом запуске)
  либо `claude mcp add --scope local istomahandoff --env
  ISTOMAHANDOFF_PROJECT=<проект> -- <python кита> <кит>/mcp_server/server.py`
  — запись в `~/.claude.json` под ключом каталога проекта. Ключ
  чувствителен к регистру буквы диска: сессии из VS Code пишут `c:/…`, из
  терминала — `C:/…`; запись нужна под тем ключом, откуда запускается
  сессия (`claude mcp get istomahandoff` в каталоге проекта). В user scope —
  сервер без `ISTOMAHANDOFF_PROJECT`, только чтение (запись по
  `CLAUDE_PROJECT_DIR` сервер не даёт).
- Codex: секция `mcp_servers` в `config.toml`; `ISTOMAHANDOFF_PROJECT` —
  только в конфиге этого проекта (поддерживает ли версия Codex проектный
  конфиг, не проверено); в пользовательском `~/.codex/config.toml` — сервер
  без неё, только чтение канона. HTTP-транспорт в Codex моложе stdio: если
  версия не принимает `url` — локальный stdio-запуск сервера кита (VPS не
  нужен).
- Cursor: проектный `.cursor/mcp.json` с тем же `env`; глобальный
  `~/.cursor/mcp.json` — без `ISTOMAHANDOFF_PROJECT`.
- Ключ записи — только в конфиге проекта: пользовательский или глобальный
  конфиг с `ISTOMAHANDOFF_PROJECT` направил бы решения всех проектов в
  один журнал, а рантаймы без `CLAUDE_PROJECT_DIR` сервер не сверяет.
- В `.mcp.json.example` путь к python — для Windows; на Linux и macOS —
  `<кит>/.venv/bin/python`.

Enforcement сервера — только для добросовестного пути (E1–E2, docs/44).

## Правила инстанцирования

1. Канон в проект не копируется; экземпляр создаёт
   `python <кит>/tools/instance_init.py <проект>` — без записей журнала
   кита, protocol.version — версия кита (docs/42); существующие файлы не
   перезаписываются.
2. Порядок подключения: решение владельца о подключении проекта →
   instance_init → это решение — первой записью журнала проекта, вручную
   (ключа записи у сервера ещё нет) → `env.ISTOMAHANDOFF_PROJECT` в
   проектном конфиге → перезапуск сессии и сверка `project` через
   protocol_version.
3. Версия экземпляра — protocol.version в docs/09 проекта; после
   обновления кита расхождение показывает `protocol_version`, порядок —
   docs/34 п.12 и docs/47.
4. Проектная конкретика (verify_command, staging, журнал) — только через
   templates/PROJECT_PROFILE.yaml проекта, не правкой скиллов.
5. Проверка экземпляра — `python <кит>/tools/protocol_lint.py --project
   <проект>` (или tool protocol_lint): журнал, docs/09, копии кита в
   проекте, импорт записей журнала протокола.
6. Если рантайм не поддерживает ни скиллы, ни главный файл — протокол
   работает как E0-конвенция: агент обязан прочитать agents/ сам,
   enforcement отсутствует (docs/44).
