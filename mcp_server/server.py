"""MCP-сервер протокола istomahandoff.

Канон — файлы репозитория (docs/, agents/, skills/); нормы в коде не
дублируются, сервер читает их из файлов. Enforcement — только для
добросовестного пути (E1–E2, docs/44).

Запуск: python mcp_server/server.py  (stdio-транспорт)
Корень репозитория: родитель mcp_server/ либо env ISTOMAHANDOFF_ROOT
(позволяет одному установленному серверу обслуживать любой проект).
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

_env_root = os.environ.get("ISTOMAHANDOFF_ROOT", "").strip()
ROOT = Path(_env_root).resolve() if _env_root else Path(__file__).resolve().parent.parent
if not (ROOT / "docs").is_dir():
    raise RuntimeError(f"корень репозитория не содержит docs/: {ROOT}")

mcp = FastMCP(
    "istomahandoff",
    host=os.environ.get("MCP_HOST", "127.0.0.1"),
    port=int(os.environ.get("MCP_PORT", "8000")),
)

# Интерактивный Claude Code спрашивает человека на каждый вызов tool с этим
# флагом, даже в режимах auto/bypass; в dontAsk вызов отклоняется, в
# приложениях на Agent SDK решает их canUseTool; другие рантаймы флаг
# игнорируют. Это не доказательство участия владельца.
_HUMAN_CONFIRM = {"anthropic/requiresUserInteraction": True}

LOG_REL = "docs/10_DECISION_LOG.md"
# Таймаут только для сетевых git-операций: убитый посреди коммит оставил бы
# .git/index.lock. На Windows таймаут не обрывает дочерние процессы git.
_NET_TIMEOUT = 60

# ---------------------------------------------------------------------------
# Чтение канона
# ---------------------------------------------------------------------------

_DOC_NAME_RE = re.compile(r"^\d{2}_[A-Z0-9_]+$")
_AGENT_NAME_RE = re.compile(r"^AGENT_[A-Z_]+$")


def _read_repo_file(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"файл не найден: {path.relative_to(ROOT).as_posix()}")
    return path.read_text(encoding="utf-8")


# --- resources ---------------------------------------------------------------

@mcp.resource("protocol://docs/{name}")
def get_doc(name: str) -> str:
    """Канонический документ протокола docs/<NN_NAME>.md."""
    if not _DOC_NAME_RE.match(name):
        raise ValueError(f"недопустимое имя документа: {name}")
    return _read_repo_file(ROOT / "docs" / f"{name}.md")


@mcp.resource("protocol://agents/{name}")
def get_agent_doc(name: str) -> str:
    """Инструкция для агента agents/<NAME>.md."""
    if not _AGENT_NAME_RE.match(name):
        raise ValueError(f"недопустимое имя документа: {name}")
    return _read_repo_file(ROOT / "agents" / f"{name}.md")


# --- prompts (процедуры из skills/) ------------------------------------------

def _register_skill_prompts() -> None:
    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
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
# Парсеры канона
# ---------------------------------------------------------------------------


def _read_decision_log() -> str:
    return _read_repo_file(ROOT / "docs" / "10_DECISION_LOG.md")


def _records_block(text: str) -> str:
    """yaml-блок секции «## Записи» docs/10."""
    m = re.search(r"(?ms)^## Записи\s*\n+```yaml\n(.*?)^```", text)
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
    """Enum типов решений — из схемы docs/10, не из кода."""
    m = re.search(r"(?m)^\s+type:\s*([A-Z| ]+)$", _read_decision_log())
    if not m:
        raise ValueError("docs/10: не найден enum типов решений")
    return {t.strip() for t in m.group(1).split("|")}


def _parse_state_machine() -> dict:
    """Цепочка, недопустимые и аварийные переходы — из docs/16."""
    text = _read_repo_file(ROOT / "docs" / "16_STATE_MACHINE.md")

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
        out = []
        for line in block.splitlines():
            m = arrow_re.match(line.strip())
            if m:
                note = " ".join(x for x in (m.group(3), m.group(4)) if x)
                out.append({"from": m.group(1), "to": m.group(2), "note": note})
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
    """Запуск tools/protocol_lint.py; возвращает вывод и exit code."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "protocol_lint.py")],
        cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        # DEVNULL: иначе дочерний процесс наследует stdin-канал MCP и
        # subprocess.run зависает (Windows)
        stdin=subprocess.DEVNULL,
    )
    return {
        "exitCode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
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
    """Авто commit+push журнала — только у единственного писателя (DEC-0016)."""
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
    """Записать решение владельца в docs/10 (секция «## Записи»).

    DEC-ID назначается автоматически. ACCEPTANCE/RELEASE без
    evidenceReadHash отклоняются (docs/10, правило 6). owner — «OWNER»
    или имя deputy (тогда обязателен mandateRef). По умолчанию запись
    остаётся в рабочем дереве; авто commit+push — только при
    ISTOMAHANDOFF_AUTOSYNC=1 у единственного писателя журнала (DEC-0016).
    """
    types = _dec_types()
    if type not in types:
        raise ValueError(
            f"неизвестный type {type!r}; допустимые (из docs/10): "
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

    log_path = ROOT / LOG_REL
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
                       "изменением (авто-синхронизация — ISTOMAHANDOFF_AUTOSYNC=1, "
                       "DEC-0016)"}
    return {"id": dec_id, "date": dt.date.today().isoformat(), "type": type,
            "repo": _repo_root() or ROOT.as_posix(),
            "log": log_path.as_posix(), "git": git}


def _atomic_write(path: Path, data: bytes) -> None:
    """Атомарная запись: temp file + rename."""
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
    """Проверки до записи при авто-синхронизации (DEC-0016).

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
    """Авто commit+push docs/10 (DEC-0011 в границах DEC-0016).

    Коммитит только docs/10; при сбое коммита запись откатывается. Push —
    только если в коммите решения нет других файлов и среди неотправленных
    коммитов ветки нет чужих (свои решения после прошлого сбоя досылаются).
    """
    c = _git(["commit", "-m", f"Запиши {dec_id} (auto, MCP record_decision)",
              "--", LOG_REL])
    if c.returncode != 0:
        _atomic_write(ROOT / LOG_REL, original)
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
    """Содержимое docs/09_ACTIVE_STATE.md (mutable pointer протокола)."""
    return _read_repo_file(ROOT / "docs" / "09_ACTIVE_STATE.md")


@mcp.tool()
def evidence_hash(path: str) -> dict:
    """sha256 файла; путь обязан резолвиться внутри корня репозитория.

    Для evidenceReadHash хэш сообщает владелец, прочитав evidence (docs/46).
    """
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError(f"путь выходит за пределы репозитория: {path}")
    if p.is_symlink():
        raise ValueError(f"symlink не допускается: {path}")
    if not p.is_file():
        raise ValueError(f"файл не найден: {path}")
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"path": p.relative_to(ROOT).as_posix(), "sha256": digest}


@mcp.tool()
def validate_transition(from_state: str, to_state: str) -> dict:
    """Проверка перехода state machine по docs/16 (файл — источник истины)."""
    sm = _parse_state_machine()
    fr, to = from_state.strip(), to_state.strip()

    for f in sm["forbidden"]:
        if f["from"] == fr and f["to"] == to:
            return {
                "verdict": "FORBIDDEN",
                "reason": f"недопустимый переход по docs/16"
                          + (f": {f['note']}" if f["note"] else ""),
            }
    if (fr, to) in sm["chain"]:
        return {"verdict": "VALID", "kind": "chain",
                "reason": "последовательный переход канонической цепочки docs/16"}
    for e in sm["emergency"]:
        if e["to"] == to and (e["from"] == "ANY_STATE" or e["from"] == fr):
            return {
                "verdict": "VALID", "kind": "emergency",
                "reason": f"аварийный переход по docs/16 ({e['from']} -> {e['to']})"
                          + (f": {e['note']}" if e["note"] else ""),
            }
    known = set(sm["states"])
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
    """Просроченные и истекающие (в пределах within_days) DEC/MANDATE-записи."""
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
    return {"today": today.isoformat(), "expired": expired, "expiring": expiring}


@mcp.tool()
def audit_sample(n: int = 3, seed: int | None = None) -> dict:
    """Sampling audit (docs/46): n случайных решений ACCEPTANCE/RELEASE."""
    entries = [e for e in _parse_decisions()
               if e.get("type") in ("ACCEPTANCE", "RELEASE")]
    if not entries:
        return {"sampled": 0, "items": [],
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
            p = (ROOT / m.group(0)).resolve()
            item["evidencePath"] = m.group(0)
            item["evidenceFileExists"] = (
                p.is_relative_to(ROOT) and p.is_file())
        items.append(item)
    return {"sampled": len(items), "items": items}


@mcp.tool()
def protocol_version() -> dict:
    """Последняя версия из change record docs/42."""
    text = _read_repo_file(ROOT / "docs" / "42_MAINTENANCE.md")
    rows = re.findall(r"(?m)^\|\s*(\d+\.\d+)\s*\|\s*([0-9-]+)\s*\|\s*(.*?)\s*\|$",
                      text)
    if not rows:
        raise ValueError("docs/42: не найдена таблица версий")
    version, date, change = rows[-1]
    return {"version": version, "date": date, "change": change,
            "source": "docs/42_MAINTENANCE.md"}


def _git(args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            # DEVNULL: иначе дочерний процесс наследует stdin-канал MCP и
            # subprocess.run зависает (Windows)
            stdin=subprocess.DEVNULL, timeout=timeout,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            ["git", *args], 124, "", f"git {args[0]}: таймаут {timeout} с")
    except OSError as e:
        return subprocess.CompletedProcess(
            ["git", *args], 127, "", f"git не запущен: {e}")


def _repo_root() -> str | None:
    """Корень git-репозитория, в котором работают git-tools сервера."""
    out = _git(["rev-parse", "--show-toplevel"]).stdout.strip()
    return out or None


@mcp.tool(meta=_HUMAN_CONFIRM)
def checkpoint_create(label: str = "") -> dict:
    """Git-tag checkpoint/<YYYYMMDD-HHMMSS>[-label] с readback (docs/19)."""
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = f"checkpoint/{stamp}"
    if label:
        safe = re.sub(r"[^a-z0-9-]+", "-", label.lower()).strip("-")
        if not safe:
            raise ValueError(f"label после sanitize пуст: {label!r} "
                             "(допустимо [a-z0-9-])")
        tag += f"-{safe}"

    proc = _git(["tag", tag])
    if proc.returncode != 0:
        raise ValueError(f"git tag {tag} не создан: {proc.stderr.strip()}")

    # readback: перечитать tag и сверить с HEAD
    head = _git(["rev-parse", "HEAD"]).stdout.strip()
    back = _git(["rev-parse", tag]).stdout.strip()
    verified = bool(head) and head == back
    result = {"tag": tag, "sha": back, "verified": verified,
              "repo": _repo_root()}
    if not verified:
        result["note"] = (f"READBACK НЕ СОШЁЛСЯ: HEAD={head}, "
                          f"tag={back} — checkpoint не считается созданным")
    return result


@mcp.tool()
def pre_deploy_check(own_files: list[str] | None = None) -> dict:
    """Pre-deploy gate чистого дерева (docs/38): задеплоенное = закоммиченное."""
    own = {p.replace("\\", "/") for p in (own_files or [])}
    proc = _git(["status", "--porcelain"])
    if proc.returncode != 0:
        raise ValueError(f"git status не выполнен: {proc.stderr.strip()}")
    changed = [line[3:].strip() for line in proc.stdout.splitlines() if line]
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
    return {"verdict": verdict, "changed": changed, "foreign": foreign,
            "note": note, "repo": _repo_root(),
            "head": _git(["rev-parse", "--verify", "--quiet", "HEAD"]).stdout.strip()
            or None}


if __name__ == "__main__":
    # stdio — локальный агент; streamable-http — VPS/сеть (MCP_TRANSPORT=http)
    transport = "streamable-http" if os.environ.get("MCP_TRANSPORT") == "http" else "stdio"
    mcp.run(transport=transport)
