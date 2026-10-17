"""MCP-сервер протокола istomahandoff.

Два корня (ADR-0001, DEC-0018). Канон — кит, в котором лежит этот сервер
(родитель mcp_server/): docs/, agents/, skills/, templates/ только читаются;
нормы в коде не дублируются. Экземпляр — проект: абсолютный путь из
ISTOMAHANDOFF_PROJECT (единственный ключ записи) либо CLAUDE_PROJECT_DIR от
Claude Code (только чтение); там docs/09, docs/10, docs/11, evidence/ и
git-репозиторий. Без проекта tools экземпляра отказывают (fail-closed),
канон доступен. Enforcement — только для добросовестного пути (E1–E2,
docs/44).

Запуск: python <кит>/mcp_server/server.py  (stdio-транспорт)
"""
import datetime as dt
import hashlib
import os
import random
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

from mcp.server.fastmcp import FastMCP

if os.environ.get("ISTOMAHANDOFF_ROOT", "").strip():
    raise RuntimeError(
        "ISTOMAHANDOFF_ROOT больше не поддерживается: канон — кит этого "
        "сервера, проект — ISTOMAHANDOFF_PROJECT (agents/AGENT_RUNTIMES.md, "
        "«Размещение»)")

LOG_REL = "docs/10_DECISION_LOG.md"
STATE_REL = "docs/09_ACTIVE_STATE.md"

# Канон — кит этого сервера; сервер его только читает.
CANON = Path(__file__).resolve().parent.parent
for _rel in (LOG_REL, "docs/16_STATE_MACHINE.md", "docs/42_MAINTENANCE.md"):
    if not (CANON / _rel).is_file():
        raise RuntimeError(f"каталог сервера — не кит протокола (нет {_rel}): {CANON}")


def _same(a: Path, b: Path) -> bool:
    """Один и тот же каталог — по идентичности (samefile), а не по строке:
    префикс \\?\\ и UNC-алиасы Windows не обходят сравнение."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(str(a)) == os.path.normcase(str(b))


def _inside(path: Path, root: Path) -> bool:
    """path совпадает с root или лежит внутри (по идентичности каталогов)."""
    for candidate in (path, *path.parents):
        try:
            if os.path.samefile(candidate, root):
                return True
        except OSError:
            continue  # ещё не создан (файл до записи) или недоступен
    return False


def _resolve_project() -> tuple[Path | None, str | None, str | None]:
    """(проект, ключ, ошибка). Ключ — какая переменная назвала проект:
    explicit — ISTOMAHANDOFF_PROJECT (даёт запись), claude — только
    CLAUDE_PROJECT_DIR (только чтение); None — проект не задан."""
    explicit = os.environ.get("ISTOMAHANDOFF_PROJECT", "").strip()
    runtime = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if not explicit and not runtime:
        return None, None, (
            "корень проекта не задан (ISTOMAHANDOFF_PROJECT в env конфига "
            "сервера проекта; для чтения — CLAUDE_PROJECT_DIR от Claude Code) "
            "— tools экземпляра отключены, канон доступен")
    source = "explicit" if explicit else "claude"
    for name, raw in (("ISTOMAHANDOFF_PROJECT", explicit),
                      ("CLAUDE_PROJECT_DIR", runtime)):
        if raw and not Path(raw).is_absolute():
            return None, source, f"{name} — не абсолютный путь: {raw}"
    try:
        if explicit and runtime and not _same(Path(explicit).resolve(),
                                              Path(runtime).resolve()):
            return None, source, ("ISTOMAHANDOFF_PROJECT и CLAUDE_PROJECT_DIR "
                                  "указывают на разные каталоги — tools "
                                  "экземпляра отключены")
        project = Path(explicit or runtime).resolve()
        if not project.is_dir():
            return None, source, f"каталог проекта не найден: {project.as_posix()}"
    except OSError as e:  # нет прав: канон должен остаться доступным
        return None, source, f"каталог проекта недоступен: {explicit or runtime} ({e})"
    if _inside(project, CANON):
        return None, source, (
            "корень проекта — кит сервера или каталог внутри него: канон "
            "только читается; журнал протокола ведётся в рабочем клоне "
            "протокола через pull request (DEC-0016 протокола)")
    return project, source, None


PROJECT, PROJECT_SOURCE, _PROJECT_ERROR = _resolve_project()
if _PROJECT_ERROR:
    _PROJECT_ERROR += (" (проверено при старте сервера — после исправления "
                       "перезапустите сессию рантайма)")


def _project(write: bool = False) -> Path:
    """Корень экземпляра для tools экземпляра; без него — отказ (fail-closed).
    write — record_decision и checkpoint_create: только по явному ключу."""
    if PROJECT is None:
        raise ValueError(_PROJECT_ERROR)
    if write and PROJECT_SOURCE != "explicit":
        raise ValueError("запись — только в проект из ISTOMAHANDOFF_PROJECT "
                         "(явный ключ в env конфига сервера проекта); "
                         "CLAUDE_PROJECT_DIR даёт только чтение")
    if not (PROJECT / LOG_REL).is_file():
        raise ValueError(f"{PROJECT.as_posix()} — не экземпляр протокола: нет "
                         f"{LOG_REL} (создать: python {CANON.as_posix()}/tools/"
                         "instance_init.py <корень проекта>)")
    for rel in (LOG_REL, STATE_REL):
        if _inside((PROJECT / rel).resolve(), CANON):
            raise ValueError(f"{rel} проекта ведёт в кит (ссылка или junction): "
                             "журнал и состояние кита не выдаются за проектные")
    return PROJECT


mcp = FastMCP(
    "istomahandoff",
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", "8000")),
)

# stdio — локальный агент; streamable-http — VPS/сеть (MCP_TRANSPORT=http).
# В HTTP-режиме tools записи отказывают, пока у сервера нет аутентификации.
TRANSPORT = "streamable-http" if os.environ.get("MCP_TRANSPORT") == "http" else "stdio"

# Интерактивный Claude Code спрашивает человека на каждый вызов tool с этим
# флагом, даже в режимах auto/bypass; в dontAsk вызов отклоняется, в
# приложениях на Agent SDK решает их canUseTool; другие рантаймы флаг
# игнорируют. Это не доказательство участия владельца.
_HUMAN_CONFIRM = {"anthropic/requiresUserInteraction": True}

# Таймаут только для сетевых git-операций: убитый посреди коммит оставил бы
# .git/index.lock. На Windows таймаут не обрывает дочерние процессы git.
_NET_TIMEOUT = 60

# ---------------------------------------------------------------------------
# Чтение канона
# ---------------------------------------------------------------------------

_DOC_NAME_RE = re.compile(r"^(?:\d{2}_[A-Z0-9_]+|INDEX)$")  # INDEX — оглавление (docs/48)
_AGENT_NAME_RE = re.compile(r"^AGENT_[A-Z_]+$")
_TEMPLATE_NAME_RE = re.compile(r"^[A-Z_]+\.(?:md|yaml)$")
_RECORDS_RE = re.compile(r"(?ms)^## Записи\s*\n+```yaml\n(.*?)^```")


def _read_file(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        raise ValueError(f"файл не найден: {rel} ({root.as_posix()})")
    return path.read_text(encoding="utf-8")


def _strip_records(text: str) -> str:
    """docs/10 кита без записей: это журнал самого протокола, полномочий в
    проектах он не даёт; схема и правила остаются."""
    m = _RECORDS_RE.search(text)
    return text[:m.start(1)] + text[m.end(1):] if m else text


# --- resources ---------------------------------------------------------------

@mcp.resource("protocol://docs/{name}")
def get_doc(name: str) -> str:
    """Канонический документ протокола docs/<NN_NAME>.md (из кита);
    docs/10 — схема и правила журнала без записей кита."""
    if not _DOC_NAME_RE.match(name):
        raise ValueError(f"недопустимое имя документа: {name}")
    text = _read_file(CANON, f"docs/{name}.md")
    return _strip_records(text) if name == "10_DECISION_LOG" else text


@mcp.resource("protocol://agents/{name}")
def get_agent_doc(name: str) -> str:
    """Инструкция для агента agents/<NAME>.md."""
    if not _AGENT_NAME_RE.match(name):
        raise ValueError(f"недопустимое имя документа: {name}")
    return _read_file(CANON, f"agents/{name}.md")


@mcp.resource("protocol://templates/{name}")
def get_template(name: str) -> str:
    """Шаблон templates/<NAME>.md|yaml."""
    if not _TEMPLATE_NAME_RE.match(name):
        raise ValueError(f"недопустимое имя шаблона: {name}")
    return _read_file(CANON, f"templates/{name}")


@mcp.resource("protocol://istomahandoff")
def get_main_doc() -> str:
    """Мастер-документ протокола istomahandoff.md."""
    return _read_file(CANON, "istomahandoff.md")


_CANON_PATH_RE = re.compile(
    r"docs/(?:\d{2}_[A-Z0-9_]+|INDEX)\.md|agents/AGENT_[A-Z_]+\.md"
    r"|skills/[a-z]+/SKILL\.md|templates/[A-Z_]+\.(?:md|yaml)|istomahandoff\.md"
    r"|adr/ADR-\d{4}-[a-z0-9-]+\.md|mcp_server/README\.md|\.mcp\.json\.example")


@mcp.tool()
def read_canon(path: str) -> str:
    """Файл канона из кита по белому списку — для рантаймов, которые не
    показывают модели resources: docs/NN_*.md, docs/INDEX.md,
    agents/AGENT_*.md, skills/<имя>/SKILL.md, templates/<ИМЯ>.md|yaml,
    istomahandoff.md, adr/ADR-NNNN-*.md, mcp_server/README.md,
    .mcp.json.example. docs/10 — схема и правила без записей кита."""
    if not _CANON_PATH_RE.fullmatch(path):
        raise ValueError(f"недопустимый путь канона: {path!r} — допустимы "
                         "docs/NN_*.md, docs/INDEX.md, agents/AGENT_*.md, "
                         "skills/<имя>/SKILL.md, templates/<ИМЯ>.md|yaml, "
                         "istomahandoff.md, adr/ADR-NNNN-*.md, "
                         "mcp_server/README.md, .mcp.json.example")
    text = _read_file(CANON, path)
    return _strip_records(text) if path == LOG_REL else text


# --- prompts (процедуры из skills/) ------------------------------------------

def _register_skill_prompts() -> None:
    for skill_md in sorted(CANON.glob("skills/*/SKILL.md")):
        skill_name = skill_md.parent.name

        def _make(path: Path) -> object:
            def _prompt() -> str:
                text = path.read_text(encoding="utf-8")
                # отдать тело процедуры без frontmatter
                m = re.match(r"\A---\n.*?\n---\n+", text, re.S)
                return text[m.end():] if m else text
            return _prompt

        mcp.prompt(name=skill_name)(_make(skill_md))


_register_skill_prompts()

# ---------------------------------------------------------------------------
# Парсеры
# ---------------------------------------------------------------------------


def _read_decision_log() -> str:
    """Журнал экземпляра (docs/10 проекта)."""
    return _read_file(_project(), LOG_REL)


def _records_block(text: str) -> str:
    """yaml-блок секции «## Записи» docs/10."""
    m = _RECORDS_RE.search(text)
    if not m:
        raise ValueError("docs/10: не найден yaml-блок секции «## Записи»")
    return m.group(1)


def _parse_decisions() -> list[dict]:
    """Простой построчный парсер DEC-записей (без внешних зависимостей)."""
    block = _records_block(_read_decision_log())
    entries = []
    for chunk in re.split(r"(?m)^- id: ", block)[1:]:
        entry = {"id": chunk.splitlines()[0].strip()}
        key = None
        for line in chunk.splitlines()[1:]:
            m = re.match(r"^  (\w+):\s*(.*)$", line)
            lm = re.match(r"^    - (.*)$", line)
            if m:
                key, val = m.group(1), m.group(2).strip()
                if val in ("", "[]"):
                    entry[key] = [] if val == "[]" else ""
                elif val == "null":
                    entry[key] = None
                else:
                    entry[key] = val
            elif lm and key:
                if not isinstance(entry.get(key), list):
                    entry[key] = []
                entry[key].append(lm.group(1).strip())
            elif key and isinstance(entry.get(key), str):
                # продолжение многострочного значения
                entry[key] = (entry[key] + " " + line.strip()).strip()
        entries.append(entry)
    return entries


def _dec_types() -> set[str]:
    """Enum типов решений — из схемы docs/10 кита (до «## Записи»), не из
    кода и не из копии схемы в журнале проекта."""
    text = _read_file(CANON, LOG_REL)
    m = _RECORDS_RE.search(text)
    schema = text[:m.start()] if m else text
    m = re.search(r"(?m)^\s+type:\s*([A-Z0-9_]+(?:\s*\|\s*[A-Z0-9_]+)+)\s*$", schema)
    if not m:
        raise ValueError("docs/10 кита: не найден enum типов решений")
    return {t.strip() for t in m.group(1).split("|")}


def _parse_state_machine() -> dict:
    """Цепочка, недопустимые и аварийные переходы — из docs/16 кита."""
    text = _read_file(CANON, "docs/16_STATE_MACHINE.md")

    def block_after(header_re: str) -> str:
        m = re.search(header_re + r"\s*\n+```text\n(.*?)```", text, re.S)
        return m.group(1) if m else ""

    chain_block = re.search(r"\A.*?```text\n(.*?)```", text, re.S)
    states = []
    if chain_block:
        for line in chain_block.group(1).splitlines():
            s = line.strip()
            if s.startswith("->"):
                states.append(s[2:].strip())
            elif s:
                states.append(s)
    chain = list(zip(states, states[1:]))

    arrow_re = re.compile(r"^(\S+)\s*->\s*(\S+)\s*(?:\((.*?)\))?\s*(?:#(.*))?$")

    def parse_arrows(block: str) -> list[dict]:
        # «(…)» — условие перехода, «# …» — комментарий
        out = []
        for line in block.splitlines():
            m = arrow_re.match(line.strip())
            if m:
                out.append({"from": m.group(1), "to": m.group(2),
                            "condition": (m.group(3) or "").strip(),
                            "note": (m.group(4) or "").strip()})
        return out

    return {
        "states": states,
        "chain": chain,
        "forbidden": parse_arrows(block_after(r"## Недопустимые переходы")),
        "emergency": parse_arrows(block_after(r"## Аварийные")),
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def protocol_lint() -> dict:
    """Lint кодом кита: экземпляра (--project), если задан корень проекта,
    иначе самого кита; проект задан, но неверен — lint кита (target: canon)
    и ошибка проекта в projectError. Копия lint в проекте не исполняется."""
    cmd = [sys.executable, str(CANON / "tools" / "protocol_lint.py")]
    if PROJECT is not None:
        cmd += ["--project", str(PROJECT)]
    proc = subprocess.run(
        cmd, cwd=CANON, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        # DEVNULL: иначе дочерний процесс наследует stdin-канал MCP и
        # subprocess.run зависает (Windows)
        stdin=subprocess.DEVNULL,
    )
    return {
        "exitCode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "target": "project" if PROJECT is not None else "canon",
        "root": (PROJECT or CANON).as_posix(),
        "projectError": _PROJECT_ERROR if PROJECT_SOURCE and PROJECT is None else None,
    }


_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")
_MANDATE_RE = re.compile(r"MANDATE-\d{4}")
_ISO_DATE_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)?")


def _single_line(field: str, value: str) -> None:
    """Поле пишется одной видимой строкой yaml-блока docs/10: перевод строки
    или управляющий символ дописал бы в журнал вторую, поддельную запись, а
    невидимые символы форматирования (bidi, zero-width) прячут смысл текста."""
    bad = [c for c in value
           if unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp")]
    if bad:
        raise ValueError(f"{field}: недопустимый символ {bad[0]!r} — значение "
                         "записывается одной видимой строкой (docs/10)")


def _blank(value: str | None) -> bool:
    """Пусто для _parse_decisions: пробелы, «null», «[]» — нет значения."""
    return value is None or value.strip() in ("", "null", "[]")


def _autosync_enabled() -> bool:
    """Авто commit+push журнала — только у единственного писателя (DEC-0016
    протокола)."""
    return os.environ.get("ISTOMAHANDOFF_AUTOSYNC", "").strip().lower() in (
        "1", "true", "yes", "on")


@mcp.tool(meta=_HUMAN_CONFIRM)
def record_decision(
    type: str,
    decision: str,
    scope: str,
    allowed: list[str],
    forbidden: list[str],
    owner: str = "OWNER",
    evidenceReadHash: str | None = None,
    mandateRef: str | None = None,
    expiresAt: str | None = None,
) -> dict:
    """Записать решение владельца в docs/10 проекта (секция «## Записи»).

    Проект — только из ISTOMAHANDOFF_PROJECT. DEC-ID назначается
    автоматически по записям журнала проекта; enum типов — из схемы docs/10
    кита. ACCEPTANCE/RELEASE без evidenceReadHash отклоняются (docs/10,
    правило 6). owner — «OWNER» или имя deputy (тогда обязателен
    mandateRef). По умолчанию запись остаётся в рабочем дереве; авто
    commit+push — только при ISTOMAHANDOFF_AUTOSYNC=1 у единственного
    писателя журнала (DEC-0016 протокола).
    """
    root = _project(write=True)
    _write_guard(root)
    types = _dec_types()
    if type not in types:
        raise ValueError(
            f"неизвестный type {type!r}; допустимые (из docs/10 кита): "
            + ", ".join(sorted(types))
        )
    for field, value in (("decision", decision), ("scope", scope),
                         ("owner", owner),
                         ("evidenceReadHash", evidenceReadHash or ""),
                         ("mandateRef", mandateRef or ""),
                         ("expiresAt", expiresAt or "")):
        _single_line(field, value)
    for field, items in (("allowed", allowed), ("forbidden", forbidden)):
        for item in items:
            _single_line(field, item)
            if _blank(item):
                raise ValueError(f"{field}: пустой пункт (docs/10)")
    for field, value in (("decision", decision), ("owner", owner)):
        if _blank(value):
            raise ValueError(f"{field}: пустое значение (docs/10)")
    if type in ("ACCEPTANCE", "RELEASE") and not evidenceReadHash:
        raise ValueError(
            f"{type} без evidenceReadHash невалиден (docs/10, правило 6): "
            "хэш присылает владелец — он сам открывает evidence и сообщает "
            "его sha256 (docs/46); агент не подставляет хэш, посчитанный им самим."
        )
    if evidenceReadHash and not _SHA256_RE.fullmatch(evidenceReadHash):
        raise ValueError("evidenceReadHash: ожидается sha256 прочитанного "
                         "evidence — 64 hex-символа (docs/10)")
    if expiresAt and not (_ISO_DATE_RE.fullmatch(expiresAt)
                          and _parse_date(expiresAt)):
        raise ValueError(f"expiresAt {expiresAt!r} не распознан: ожидается "
                         "YYYY-MM-DD или YYYY-MM-DDTHH:MM:SS[±HH:MM] (иначе "
                         "list_expired его не увидит)")
    if owner != "OWNER" and _blank(mandateRef):
        raise ValueError("решение deputy без mandateRef недействительно "
                         "(docs/10: поле mandateRef; docs/46 п.7); "
                         "владелец пишется как owner=OWNER")
    if mandateRef and not _MANDATE_RE.fullmatch(mandateRef):
        raise ValueError(f"mandateRef {mandateRef!r}: ожидается MANDATE-XXXX "
                         "(docs/46)")
    if _blank(scope):
        raise ValueError("решение без scope не действительно (docs/10)")
    if not allowed or not forbidden:
        raise ValueError("решение без allowed/forbidden не действительно (docs/10)")

    sync = _autosync_enabled()
    upstream = fetched = None
    if sync:
        upstream, fetched = _prepare_sync()

    log_path = root / LOG_REL
    text = _read_decision_log()
    nums = [int(n) for n in
            re.findall(r"(?m)^- id: DEC-(\d{4})\b", _records_block(text))]
    dec_id = f"DEC-{max(nums, default=0) + 1:04d}"

    # формат — как у существующих записей DEC-0001...
    lines = [
        f"- id: {dec_id}",
        f"  date: {dt.date.today().isoformat()}",
        f"  owner: {owner}",
        f"  type: {type}",
        f"  scope: {scope}",
        f"  decision: {decision}",
        "  allowed:",
        *(f"    - {i}" for i in allowed),
        "  forbidden:",
        *(f"    - {i}" for i in forbidden),
        f"  expiresAt: {expiresAt if expiresAt else 'null'}",
        "  receiptSha256: null",
        f"  evidenceReadHash: {evidenceReadHash if evidenceReadHash else 'null'}",
        f"  mandateRef: {mandateRef if mandateRef else 'null'}",
    ]
    entry = "\n".join(lines) + "\n"

    m = re.search(r"(?ms)^(## Записи\s*\n+```yaml\n)(.*?)(^```)", text)
    if not m:
        raise ValueError("docs/10: не найден yaml-блок секции «## Записи»")
    new_text = text[:m.start(2)] + m.group(2) + entry + text[m.end(2):]

    original = log_path.read_bytes()
    _atomic_write(log_path, new_text.encode("utf-8"))

    if sync:
        git = _sync_decision_log(dec_id, upstream, fetched, original)
    else:
        git = {"autosync": False, "committed": False, "pushed": False,
               "note": "запись в рабочем дереве: закоммитьте её вместе с "
                       "изменением; если следом нужен checkpoint (BOUNDARY перед "
                       "pre-change) — отдельным коммитом до checkpoint_create "
                       "(авто-синхронизация — ISTOMAHANDOFF_AUTOSYNC=1, DEC-0016 "
                       "протокола)"}
    return {"id": dec_id, "date": dt.date.today().isoformat(), "type": type,
            "project": root.as_posix(), "repo": _repo_root() or root.as_posix(),
            "log": log_path.as_posix(), "git": git}


def _atomic_write(path: Path, data: bytes) -> None:
    """Атомарная запись: temp file + rename. В кит сервер не пишет."""
    if _inside(path.resolve(), CANON):
        raise ValueError(f"запись в кит запрещена: {path.as_posix()}")
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def _upstream() -> dict | None:
    """Upstream текущей ветки: remote и ветка назначения для push."""
    branch = _git(["symbolic-ref", "--quiet", "--short", "HEAD"]).stdout.strip()
    if not branch:
        return None
    remote = _git(["config", "--get", f"branch.{branch}.remote"]).stdout.strip()
    merge = _git(["config", "--get", f"branch.{branch}.merge"]).stdout.strip()
    if not remote or remote == "." or not merge:
        return None
    return {"remote": remote, "merge": merge}


def _rev_count(rev_range: str) -> int:
    out = _git(["rev-list", "--count", rev_range]).stdout.strip()
    return int(out) if out.isdigit() else -1


def _prepare_sync() -> tuple[dict | None, bool | None]:
    """Проверки до записи при авто-синхронизации (DEC-0016 протокола).

    Отказ, если в docs/10 есть незакоммиченные правки (авто-коммит забрал бы
    их вместе с решением) или клон отстаёт от upstream (DEC-ID мог быть уже
    занят). Возвращает (upstream, fetch удался).
    """
    if _git(["symbolic-ref", "--quiet", "HEAD"]).returncode != 0:
        raise ValueError("HEAD не на ветке (checkout коммита/тега или идёт "
                         "rebase) — авто-коммит ушёл бы мимо ветки; решение "
                         "не записано")
    st = _git(["status", "--porcelain", "--", LOG_REL])
    if st.returncode != 0:
        raise ValueError(f"git status не выполнен: {st.stderr.strip()}")
    if st.stdout.strip():
        raise ValueError("в docs/10 есть незакоммиченные правки — авто-коммит "
                         "забрал бы их вместе с решением; решение не записано")
    upstream = _upstream()
    if upstream is None:
        return None, None
    fetched = _git(["fetch", "--quiet", upstream["remote"]],
                   timeout=_NET_TIMEOUT).returncode == 0
    if fetched:
        if _git(["rev-parse", "--verify", "--quiet", "@{u}"]).returncode != 0:
            raise ValueError("upstream-ветка не найдена (удалена на remote или "
                             "ещё не создана) — проверьте git branch -vv; "
                             "решение не записано")
        behind = _rev_count("HEAD..@{u}")
        if behind and _rev_count("@{u}..HEAD") > 0:
            raise ValueError("ветка разошлась с upstream — выполните git pull "
                             "--rebase; решение не записано")
        if behind:
            raise ValueError(f"клон отстаёт от upstream на {behind} коммит(ов) — "
                             "DEC-ID мог быть уже занят; выполните git pull "
                             "--ff-only; решение не записано")
    return upstream, fetched


_OWN_COMMIT_RE = re.compile(r"Запиши DEC-\d{4} \(auto, MCP record_decision\)")


def _commit_files(rev: str) -> list[str]:
    out = _git(["-c", "core.quotePath=false", "diff-tree", "--root",
                "--no-commit-id", "--name-only", "-r", rev]).stdout
    return [line for line in out.splitlines() if line]


def _is_own_decision_commit(rev: str, log_in_repo: str) -> bool:
    """Коммит решения, сделанный сервером: своё сообщение и только docs/10."""
    subject = _git(["log", "-1", "--format=%s", rev]).stdout.strip()
    return bool(_OWN_COMMIT_RE.fullmatch(subject)) and \
        _commit_files(rev) == [log_in_repo]


def _sync_decision_log(dec_id: str, upstream: dict | None,
                       fetched: bool | None, original: bytes) -> dict:
    """Авто commit+push docs/10 (DEC-0011 в границах DEC-0016 протокола).

    Коммитит только docs/10; при сбое коммита запись откатывается. Push —
    только если в коммите решения нет других файлов и среди неотправленных
    коммитов ветки нет чужих (свои решения после прошлого сбоя досылаются).
    """
    c = _git(["commit", "-m", f"Запиши {dec_id} (auto, MCP record_decision)",
              "--", LOG_REL])
    if c.returncode != 0:
        _atomic_write(_project() / LOG_REL, original)
        _git(["reset", "-q", "--", LOG_REL])
        raise ValueError("git commit не удался, запись откатена — решение НЕ "
                         "записано: " + (c.stderr.strip() or c.stdout.strip()
                                         or "git commit failed"))
    out = {"autosync": True, "committed": True, "pushed": False}
    log_in_repo = _git(["rev-parse", "--show-prefix"]).stdout.strip() + LOG_REL
    files = _commit_files("HEAD")
    if files != [log_in_repo]:
        out.update(reason="COMMIT_NOT_ONLY_LOG", files=files,
                   note="в коммит решения попали другие файлы (pre-commit "
                        "хук?) — push пропущен; разберите коммит вручную")
        return out
    if upstream is None:
        out.update(reason="NO_UPSTREAM",
                   note="у ветки нет upstream — push не выполнялся")
        return out
    if not fetched:
        out.update(reason="FETCH_FAILED",
                   note="git fetch не удался: DEC-ID не сверен с upstream, push "
                        "пропущен. Когда remote станет доступен — git pull "
                        "--rebase; при конфликте в docs/10 этот DEC-ID уже "
                        "занят: перенумеруйте запись и выполните git push")
        return out
    pending = _git(["rev-list", "--reverse", "@{u}..HEAD"]).stdout.split()
    foreign = [r for r in pending[:-1]
               if not _is_own_decision_commit(r, log_in_repo)]
    if not pending or foreign:
        extra = [_git(["log", "-1", "--format=%h %s", r]).stdout.strip()
                 for r in foreign]
        out.update(reason="EXTRA_COMMITS", extraCommits=extra,
                   note="в ветке есть другие неотправленные коммиты — push "
                        "пропущен, чтобы не опубликовать их вместе с решением")
        return out
    p = _git(["push", upstream["remote"], f"HEAD:{upstream['merge']}"],
             timeout=_NET_TIMEOUT)
    if p.returncode != 0:
        out.update(reason="PUSH_FAILED", error=p.stderr.strip() or "git push failed",
                   note="решение закоммичено локально; следующий вызов "
                        "record_decision отправит его вместе с новым "
                        "(или выполните git push)")
        return out
    out["pushed"] = True
    if len(pending) > 1:
        out["pushedCommits"] = len(pending)
    return out


@mcp.tool()
def get_active_state() -> str:
    """Содержимое docs/09_ACTIVE_STATE.md проекта (mutable pointer экземпляра)."""
    return _read_file(_project(), STATE_REL)


@mcp.tool()
def evidence_hash(path: str) -> dict:
    """sha256 файла; путь обязан резолвиться внутри корня проекта.

    Для evidenceReadHash хэш сообщает владелец, прочитав evidence (docs/46).
    """
    root = _project()
    p = (root / path).resolve()
    if not p.is_relative_to(root):
        raise ValueError(f"путь выходит за пределы проекта: {path}")
    if p.is_symlink():
        raise ValueError(f"symlink не допускается: {path}")
    if not p.is_file():
        raise ValueError(f"файл не найден: {path}")
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"path": p.relative_to(root).as_posix(), "sha256": digest,
            "project": root.as_posix()}


@mcp.tool()
def validate_transition(from_state: str, to_state: str) -> dict:
    """Проверка перехода state machine по docs/16 (файл — источник истины).

    VALID — шаг цепочки или аварийный переход из ANY_STATE; FORBIDDEN —
    недопустимый переход или прыжок через стадии цепочки (docs/33 п.21);
    UNKNOWN — переход в docs/16 не описан. CONDITIONAL: при kind=chain шаг
    недопустим, если выполняется forbiddenWhen (условие запрета docs/16);
    при kind=emergency переход допустим, только если текущее состояние
    подпадает под requiresState и/или выполнено allowedWhen.
    """
    sm = _parse_state_machine()
    fr, to = from_state.strip(), to_state.strip()
    states = sm["states"]
    rules = [f for f in sm["forbidden"] if f["from"] == fr and f["to"] == to]

    if (fr, to) in sm["chain"]:
        if rules and all(f["condition"] for f in rules):
            # запрет с условием на шаге цепочки — это условие самого шага
            conds = "; ".join(f["condition"] for f in rules)
            return {"verdict": "CONDITIONAL", "kind": "chain",
                    "forbiddenWhen": conds,
                    "reason": f"шаг цепочки docs/16 недопустим, если: {conds}"}
        if not rules:
            return {"verdict": "VALID", "kind": "chain",
                    "reason": "последовательный переход канонической цепочки docs/16"}
    if rules:
        why = "; ".join(f["condition"] or f["note"] for f in rules
                        if f["condition"] or f["note"])
        return {"verdict": "FORBIDDEN",
                "reason": "недопустимый переход по docs/16"
                          + (f": {why}" if why else "")}
    known = set(states) | {e["to"] for e in sm["emergency"]}
    for e in sm["emergency"]:
        if e["to"] != to:
            continue
        note = f": {e['note']}" if e["note"] else ""
        if e["from"] in ("ANY_STATE", fr):
            if e["condition"]:
                return {"verdict": "CONDITIONAL", "kind": "emergency",
                        "allowedWhen": e["condition"],
                        "reason": f"аварийный переход по docs/16 "
                                  f"({e['from']} -> {e['to']}) — только если: "
                                  f"{e['condition']}{note}"}
            return {"verdict": "VALID", "kind": "emergency",
                    "reason": f"аварийный переход по docs/16 "
                              f"({e['from']} -> {e['to']}){note}"}
        if fr not in known:
            continue  # опечатка или чужое состояние — ниже UNKNOWN с подсказкой
        # обобщённый источник (ANY_MUTATED_STATE и т.п.)
        res = {"verdict": "CONDITIONAL", "kind": "emergency",
               "requiresState": e["from"],
               "reason": f"аварийный переход по docs/16 ({e['from']} -> "
                         f"{e['to']}) — только если текущее состояние "
                         f"подпадает под {e['from']}{note}"}
        if e["condition"]:
            res["allowedWhen"] = e["condition"]
        return res
    if fr in states and to in states and states.index(to) > states.index(fr) + 1:
        return {"verdict": "FORBIDDEN", "kind": "skip",
                "reason": f"прыжок через стадии цепочки docs/16 — stop "
                          f"condition (docs/33 п.21), нужен отдельный DEC"}
    known = set(states)
    hint = ""
    if fr not in known:
        hint = f"; состояние {fr} не входит в каноническую цепочку"
    return {"verdict": "UNKNOWN",
            "reason": f"переход {fr} -> {to} не описан в docs/16{hint}"}


def _parse_date(value: str) -> dt.date | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value[:19], fmt).date()
        except ValueError:
            continue
    return None


@mcp.tool()
def list_expired(within_days: int = 7) -> dict:
    """Просроченные и истекающие (в пределах within_days) DEC/MANDATE-записи проекта."""
    root = _project()
    today = dt.date.today()
    horizon = today + dt.timedelta(days=within_days)
    expired, expiring = [], []
    for e in _parse_decisions():
        exp = e.get("expiresAt")
        if not exp:
            continue
        d = _parse_date(exp)
        if d is None:
            continue
        item = {"id": e["id"], "type": e.get("type"), "expiresAt": exp}
        if d < today:
            expired.append(item)
        elif d <= horizon:
            expiring.append(item)
    return {"today": today.isoformat(), "expired": expired, "expiring": expiring,
            "project": root.as_posix()}


@mcp.tool()
def audit_sample(n: int = 3, seed: int | None = None) -> dict:
    """Sampling audit (docs/46): n случайных решений ACCEPTANCE/RELEASE проекта."""
    root = _project()
    entries = [e for e in _parse_decisions()
               if e.get("type") in ("ACCEPTANCE", "RELEASE")]
    if not entries:
        return {"sampled": 0, "items": [], "project": root.as_posix(),
                "note": "нет записей ACCEPTANCE/RELEASE для аудита"}
    rng = random.Random(seed)
    sample = rng.sample(entries, min(n, len(entries)))
    items = []
    for e in sample:
        h = e.get("evidenceReadHash")
        item = {
            "id": e["id"], "type": e["type"],
            "evidenceReadHash": h or None,
            "evidenceReadHashPresent": bool(h),
            "evidencePath": None,
            "evidenceFileExists": None,
        }
        # путь evidence в схеме DEC отдельным полем не задан — ищем в тексте
        blob = " ".join(str(v) for v in e.values() if v)
        m = re.search(r"evidence/[\w./-]+", blob)
        if m:
            p = (root / m.group(0)).resolve()
            item["evidencePath"] = m.group(0)
            item["evidenceFileExists"] = (
                p.is_relative_to(root) and p.is_file())
        items.append(item)
    return {"sampled": len(items), "items": items, "project": root.as_posix()}


# то же выражение — в tools/protocol_lint.py (VERSION_RE)
_VERSION_RE = re.compile(r'(?m)^protocol:[ \t]*(?:#.*)?\n(?:[ \t]+.*\n)*?[ \t]+version:'
                         r'[ \t]*"?([^"\s#]*)"?')


@mcp.tool()
def protocol_version() -> dict:
    """Версия кита (последняя строка change record docs/42), ревизия кита —
    загруженного кода (loadedHead, loadedDirty), на диске (canonHead,
    canonDirty) и релизный тег kit-vX.Y — и protocol.version из docs/09
    проекта: match и versionsSince — факты для сверки по docs/34 п.12,
    порядок миграции — docs/47."""
    text = _read_file(CANON, "docs/42_MAINTENANCE.md")
    rows = re.findall(r"(?m)^\|\s*(\d+\.\d+)\s*\|\s*([0-9-]+)\s*\|\s*(.*?)\s*\|$",
                      text)
    if not rows:
        raise ValueError("docs/42: не найдена таблица версий")
    version, date, change = rows[-1]
    head, _ = _kit_head()
    dirty = tag = None
    if head:
        st = _kit_status()
        dirty = bool(st.stdout.strip()) if st.returncode == 0 else None
        tag = _git(["describe", "--tags", "--exact-match", "--match", "kit-v*",
                    "HEAD"], cwd=CANON).stdout.strip() or None
    res = {"version": version, "date": date, "change": change,
           "source": "docs/42_MAINTENANCE.md", "canon": CANON.as_posix(),
           "canonHead": head, "loadedHead": _KIT_HEAD_AT_START,
           "loadedDirty": _KIT_DIRTY_AT_START,
           "canonDirty": dirty, "canonTag": tag,
           "project": PROJECT.as_posix() if PROJECT else None,
           "projectVersion": None, "match": None, "versionsSince": None}
    notes = []
    if _KIT_HEAD_AT_START is None:
        notes.append(f"ревизия кита при старте сервера не определена "
                     f"({_KIT_START_ERROR}) — после исправления перезапустите "
                     "сессию рантайма")
    elif head != _KIT_HEAD_AT_START:
        notes.append("кит на диске не совпадает с загруженным кодом сервера — "
                     "перезапустите сессию рантайма")
    if _KIT_DIRTY_AT_START:
        notes.append("кит был изменён на месте при старте сервера — загружен код "
                     "не из HEAD кита: приведите кит к HEAD и перезапустите сессию")
    if PROJECT is None:
        notes.append(_PROJECT_ERROR)
    else:
        state = PROJECT / STATE_REL
        m = _VERSION_RE.search(state.read_text(encoding="utf-8")) if state.is_file() else None
        pv = m.group(1) if m and m.group(1) and not m.group(1).startswith("<") else None
        known = [r[0] for r in rows]
        res["projectVersion"] = pv
        res["match"] = pv == version
        if pv in known:
            res["versionsSince"] = known[known.index(pv) + 1:]
        if not res["match"]:
            notes.append(
                "protocol.version в docs/09 проекта "
                + (pv if pv else "не заполнена")
                + (" — нет в change record docs/42" if pv and pv not in known else "")
                + f"; кит — {version}: сверка по docs/34 п.12, порядок — docs/47")
    if notes:
        res["note"] = "; ".join(notes)
    return res


# Переменные, которые увели бы git в чужой репозиторий (запуск рантайма из
# git-хука или оболочки с GIT_DIR): git-tools работают только в своём корне.
_GIT_REDIRECT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                     "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                     "GIT_NAMESPACE", "GIT_PREFIX")


def _git(args: list[str], timeout: int | None = None,
         cwd: Path | None = None) -> subprocess.CompletedProcess:
    """git в репозитории проекта (cwd по умолчанию — корень экземпляра)."""
    where = cwd if cwd is not None else _project()
    try:
        return subprocess.run(
            ["git", *args], cwd=where, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            # DEVNULL: иначе дочерний процесс наследует stdin-канал MCP и
            # subprocess.run зависает (Windows)
            stdin=subprocess.DEVNULL, timeout=timeout,
            env={**{k: v for k, v in os.environ.items() if k not in _GIT_REDIRECT_ENV},
                 "GIT_TERMINAL_PROMPT": "0"},
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            ["git", *args], 124, "", f"git {args[0]}: таймаут {timeout} с")
    except OSError as e:
        return subprocess.CompletedProcess(
            ["git", *args], 127, "", f"git не запущен: {e}")


def _repo_root() -> str | None:
    """Корень git-репозитория проекта, в котором работают git-tools сервера."""
    out = _git(["rev-parse", "--show-toplevel"]).stdout.strip()
    return out or None


def _kit_head() -> tuple[str | None, str | None]:
    """(HEAD кита, причина, если HEAD не определён). HEAD — только у
    отдельного git-клона: корень его репозитория — сам кит."""
    top = _git(["rev-parse", "--show-toplevel"], cwd=CANON)
    if top.returncode != 0 or not top.stdout.strip():
        why = top.stderr.strip().splitlines()[-1:] or ["нет вывода"]
        return None, "кит не в git-клоне или git недоступен: " + why[0]
    if not _same(Path(top.stdout.strip()).resolve(), CANON):
        return None, (f"кит лежит внутри git-репозитория {top.stdout.strip()} — "
                      "нужен отдельный клон кита")
    head = _git(["rev-parse", "--verify", "--quiet", "HEAD"], cwd=CANON).stdout.strip()
    return (head, None) if head else (None, "в клоне кита нет коммитов")


def _kit_status() -> subprocess.CompletedProcess:
    # --no-optional-locks: status не обновляет .git/index кита — кит только читается
    return _git(["--no-optional-locks", "status", "--porcelain",
                 "--untracked-files=no"], cwd=CANON)


# Ревизия кода, загруженного сервером: запись сверяет с ней кит на диске. Код
# совпадает с HEAD, только если кит при старте был чист.
_KIT_HEAD_AT_START, _KIT_START_ERROR = _kit_head()
_KIT_DIRTY_AT_START = None
if _KIT_HEAD_AT_START:
    _st = _kit_status()
    _KIT_DIRTY_AT_START = _st.returncode != 0 or bool(_st.stdout.strip())


def _over_http() -> bool:
    """Вызов пришёл по HTTP (SSE или streamable-http): в контексте запроса
    лежит HTTP-запрос; у stdio и прямого вызова его нет."""
    try:
        return mcp.get_context().request_context.request is not None
    except (LookupError, ValueError):
        return False


def _holds_canon(root: Path) -> bool:
    return (root / "istomahandoff.md").is_file() and \
        (root / "docs" / "16_STATE_MACHINE.md").is_file()


def _write_guard(root: Path) -> None:
    """Охрана записи (ADR-0001 пп. 4–6): не по HTTP, не туда, где лежит
    канон (в корне проекта или его git-репозитория), и только кодом той
    ревизии кита, что лежит на диске."""
    if TRANSPORT != "stdio" or _over_http():
        raise ValueError("в HTTP-режиме запись отключена, пока у сервера нет "
                         "аутентификации")
    top = _git(["rev-parse", "--show-toplevel"], cwd=root).stdout.strip()
    for where in (root, Path(top) if top else None):
        if where is not None and _holds_canon(where):
            raise ValueError(f"канон (istomahandoff.md и docs/16) лежит в "
                             f"{where.as_posix()} — корне проекта или его "
                             "git-репозитория: это клон протокола или проект с "
                             "копией кита, запись через MCP запрещена; журнал "
                             "протокола ведётся через pull request (DEC-0016 "
                             "протокола)")
    if _KIT_HEAD_AT_START is None:
        raise ValueError(f"ревизия кита при старте сервера не определена "
                         f"({_KIT_START_ERROR}) — запись отключена "
                         "(agents/AGENT_RUNTIMES.md, «Размещение»); после "
                         "исправления перезапустите сессию рантайма")
    if _KIT_DIRTY_AT_START:
        raise ValueError("кит был изменён на месте при старте сервера — загружен "
                         "код не из HEAD кита, запись отключена: приведите кит "
                         "к HEAD и перезапустите сессию рантайма")
    st = _kit_status()
    if st.returncode != 0:
        raise ValueError("git status кита не выполнен — ревизию не проверить, "
                         "запись отключена: " + st.stderr.strip())
    if st.stdout.strip():
        raise ValueError("кит изменён на месте (незакоммиченные правки "
                         "отслеживаемых файлов) — запись отключена: кит "
                         "обновляется только git pull --ff-only")
    head = _git(["rev-parse", "--verify", "--quiet", "HEAD"], cwd=CANON).stdout.strip()
    if head != _KIT_HEAD_AT_START:
        raise ValueError("кит обновлён после старта сервера (HEAD сменился) — "
                         "запись отключена: перезапустите сессию рантайма, "
                         "чтобы сервер загрузил новый код")


def _status_entries() -> list[tuple[str, str]]:
    """(XY, путь) по `git status -z`: пути относительно корня репозитория,
    без экранирования (кириллица, пробелы), файлы внутри новых каталогов
    перечислены поштучно, у переименования — оба пути."""
    proc = _git(["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    if proc.returncode != 0:
        raise ValueError(f"git status не выполнен: {proc.stderr.strip()}")
    recs = proc.stdout.split("\0")
    out, i = [], 0
    while i < len(recs):
        rec = recs[i]
        i += 1
        if len(rec) < 4:
            continue
        out.append((rec[:2], rec[3:]))
        if "R" in rec[:2] or "C" in rec[:2]:
            # в формате -z за новым путём следует исходный
            if i < len(recs) and recs[i]:
                out.append((rec[:2], recs[i]))
            i += 1
    return out


_LIST_CAP = 200  # длинные списки путей в ответах гейтов обрезаются, счётчик — полный


def _norm_path(path: str, root: str | None) -> str:
    """own_files к виду путей git status: «/», без «./», относительно корня."""
    p = path.replace("\\", "/")
    if root and Path(p).is_absolute():
        try:
            p = Path(p).resolve().relative_to(Path(root).resolve()).as_posix()
        except ValueError:
            pass
    while p.startswith("./"):
        p = p[2:]
    return p


@mcp.tool(meta=_HUMAN_CONFIRM)
def checkpoint_create(label: str = "") -> dict:
    """Git-tag checkpoint/<YYYYMMDD-HHMMSS>[-label] с readback (docs/19).

    Отказ, если у отслеживаемых файлов есть незакоммиченные изменения: тег
    фиксирует HEAD, и checkpoint не совпал бы с рабочим деревом (запись
    решения в docs/10 коммитится до checkpoint). Неотслеживаемые файлы
    перечисляются в ответе. Тег annotated — нужны git user.name и
    user.email; тег только локальный (push не выполняется). Проект — только
    из ISTOMAHANDOFF_PROJECT.
    """
    root = _project(write=True)
    _write_guard(root)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = f"checkpoint/{stamp}"
    if label:
        safe = re.sub(r"[^a-z0-9-]+", "-", label.lower()).strip("-")
        if not safe:
            raise ValueError(f"label после sanitize пуст: {label!r} "
                             "(допустимо [a-z0-9-])")
        tag += f"-{safe}"

    if _git(["var", "GIT_COMMITTER_IDENT"]).returncode != 0:
        raise ValueError("git identity не задана: annotated tag требует "
                         "user.name и user.email — задайте их в этом "
                         "репозитории (git config user.name / user.email); "
                         "глобальный конфиг без решения владельца не менять")
    entries = _status_entries()
    dirty = [p for xy, p in entries if xy != "??"]
    if dirty:
        log_in_repo = _git(["rev-parse", "--show-prefix"]).stdout.strip() + LOG_REL
        hint = (" — запись решения в docs/10 закоммитьте отдельным коммитом "
                "до checkpoint" if log_in_repo in dirty else "")
        raise ValueError("незакоммиченные изменения отслеживаемых файлов — "
                         "checkpoint зафиксировал бы не то состояние: "
                         + ", ".join(dirty[:20]) + hint)
    untracked = [p for xy, p in entries if xy == "??"]

    proc = _git(["tag", "-a", "-m", f"checkpoint {stamp} {label}".strip(), tag])
    if proc.returncode != 0:
        raise ValueError(f"git tag {tag} не создан: {proc.stderr.strip()}")

    # readback: перечитать tag и сверить коммит, на который он указывает, с HEAD
    head = _git(["rev-parse", "HEAD"]).stdout.strip()
    back = _git(["rev-parse", f"{tag}^{{commit}}"]).stdout.strip()
    verified = bool(head) and head == back
    result = {"tag": tag, "sha": back, "verified": verified,
              "project": root.as_posix(), "repo": _repo_root(), "pushed": False,
              "untracked": untracked[:_LIST_CAP],
              "untrackedCount": len(untracked)}
    if not verified:
        result["note"] = (f"READBACK НЕ СОШЁЛСЯ: HEAD={head}, "
                          f"tag={back} — checkpoint не считается созданным")
    return result


@mcp.tool()
def pre_deploy_check(own_files: list[str] | None = None) -> dict:
    """Pre-deploy gate чистого дерева (docs/38): задеплоенное = закоммиченное.

    own_files — пути относительно корня репозитория проекта (поле repo
    ответа); каталог в own_files не покрывает файлы внутри него.
    """
    project = _project()
    root = _repo_root()
    own = {_norm_path(p, root) for p in (own_files or [])}
    changed = list(dict.fromkeys(p for _, p in _status_entries()))
    foreign = [p for p in changed if p not in own]
    if not changed:
        verdict = "CLEAN"
    elif not foreign:
        verdict = "DIRTY_OWN"
    else:
        verdict = "DIRTY_FOREIGN"
    note = {
        "CLEAN": "дерево чисто: задеплоенное = закоммиченное (docs/38)",
        "DIRTY_OWN": "незакоммичены только свои файлы: деплой запрещён до "
                     "коммита — задеплоенное = закоммиченное (docs/38)",
        "DIRTY_FOREIGN": "STOP (docs/38): в дереве файлы не из own_files — "
                         "чужие незакоммиченные изменения, деплой запрещён",
    }[verdict]
    return {"verdict": verdict,
            "changed": changed[:_LIST_CAP], "changedCount": len(changed),
            "foreign": foreign[:_LIST_CAP], "foreignCount": len(foreign),
            "truncated": len(changed) > _LIST_CAP,
            "note": note, "project": project.as_posix(), "repo": root,
            "head": _git(["rev-parse", "--verify", "--quiet", "HEAD"]).stdout.strip()
            or None}


if __name__ == "__main__":
    mcp.run(transport=TRANSPORT)
