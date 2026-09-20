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
from pathlib import Path

from mcp.server.fastmcp import FastMCP

_env_root = os.environ.get("ISTOMAHANDOFF_ROOT", "").strip()
ROOT = Path(_env_root).resolve() if _env_root else Path(__file__).resolve().parent.parent
if not (ROOT / "docs").is_dir():
    raise RuntimeError(f"корень репозитория не содержит docs/: {ROOT}")

mcp = FastMCP("istomahandoff")

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


@mcp.tool()
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
    evidenceReadHash отклоняются (docs/10, правило 6).
    """
    types = _dec_types()
    if type not in types:
        raise ValueError(
            f"неизвестный type {type!r}; допустимые (из docs/10): "
            + ", ".join(sorted(types))
        )
    if type in ("ACCEPTANCE", "RELEASE") and not evidenceReadHash:
        raise ValueError(
            f"{type} без evidenceReadHash невалиден (docs/10, правило 6): "
            "владелец обязан зафиксировать хэш прочитанного evidence. "
            "Сначала получите хэш через evidence_hash(path)."
        )
    if not scope:
        raise ValueError("решение без scope не действительно (docs/10)")
    if not allowed or not forbidden:
        raise ValueError("решение без allowed/forbidden не действительно (docs/10)")

    log_path = ROOT / "docs" / "10_DECISION_LOG.md"
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

    # атомарная запись: temp file + rename
    fd, tmp = tempfile.mkstemp(dir=log_path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
        os.replace(tmp, log_path)
    except BaseException:
        os.unlink(tmp)
        raise
    return {"id": dec_id, "date": dt.date.today().isoformat(), "type": type}


@mcp.tool()
def get_active_state() -> str:
    """Содержимое docs/09_ACTIVE_STATE.md (mutable pointer протокола)."""
    return _read_repo_file(ROOT / "docs" / "09_ACTIVE_STATE.md")


@mcp.tool()
def evidence_hash(path: str) -> dict:
    """sha256 файла; путь обязан резолвиться внутри корня репозитория."""
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


def _git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        # DEVNULL: иначе дочерний процесс наследует stdin-канал MCP и
        # subprocess.run зависает (Windows)
        stdin=subprocess.DEVNULL,
    )


@mcp.tool()
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
    result = {"tag": tag, "sha": back, "verified": verified}
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
            "note": note}


if __name__ == "__main__":
    mcp.run(transport="stdio")
