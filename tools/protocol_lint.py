"""Protocol lint — самопроверка согласованности протокола istomahandoff.

Проверяет (errors — exit 1, warnings — только вывод):
  1. Ссылки docs/NN, agents/X, templates/X, skills/x — цели существуют.
  2. docs/09 enum состояний покрывает каноническую state machine (14 состояний).
  3. Записи DEC в docs/10 содержат обязательные поля.
  4. Нумерация пунктов docs/33 (stop conditions) непрерывна.
  5. State-подобные токены (UPPER_SNAKE) — известны (warning, если нет).
  6. docs/INDEX.md покрывает все docs/NN_*.md и не ссылается на
     несуществующие (docs/48).
  7. Записи docs/10: все внутри блока «## Записи»; DEC-ID вида DEC-NNNN
     (мандат — запись DEC с type: MANDATE, номер MANDATE-XXXX — в тексте),
     уникальны и растут; type из enum схемы; у ACCEPTANCE/RELEASE — sha256
     в evidenceReadHash (правило 6); expiresAt — существующая дата ISO8601;
     дата раньше предыдущей — warning (история не правится).

Запуск: python tools/protocol_lint.py   (из корня репозитория протокола)

Экземпляр: python <кит>/tools/protocol_lint.py --project <абсолютный путь>
  Канон — этот кит. Проверяются только файлы экземпляра: записи docs/10
  проекта (инварианты п.7, enum типов — из схемы docs/10 кита; копия схемы
  в журнале проекта — не запись); docs/09 проекта — protocol.version из
  change record docs/42 кита, level P0..P2, state из docs/16 кита (нет
  ключа — error, плейсхолдер — warning); файл не в UTF-8 — error;
  документы и README проекта не сканируются. Warnings: нет docs/11; для
  evidence/ git не видит -text (git check-attr, без git — по тексту
  .gitattributes; docs/31); в проекте лежат копии кита (равны файлу кита
  или называют протокол) или копии скиллов кита, отличные от кита; в
  журнале проекта есть записи, побайтно равные записям журнала протокола
  (импорт).
"""
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCAN_DIRS = ["docs", "agents", "templates", "skills"]
SCAN_FILES = ["istomahandoff.md", "README.md"]
SKIP_FILES = {"CLAUDE.md"}  # чужой образец, не норма протокола

CANON_STATES = [
    "INTAKE", "TRIAGE", "DESIGN_READY", "BOUNDARY_OWNER_ACCEPTED",
    "PRE_CHANGE_CHECKPOINT_VERIFIED", "IMPLEMENTATION_AUTHORIZED", "BUILDING",
    "EVIDENCE_READY", "TECHNICAL_REVIEW_PASSED", "RESULT_OWNER_ACCEPTED",
    "POST_ACCEPTANCE_CHECKPOINT_VERIFIED", "RELEASE_AUTHORIZED", "RELEASED",
    "NEXT_WORK_ITEM_LOCKED",
]

# Аварийные состояния, маркеры готовности блоков, события memo, статусы update —
# не состояния machine, но легитимные UPPER_SNAKE токены протокола.
ALLOWED_TOKENS = set(CANON_STATES) | {
    "STOPPED_CONTEXT_CONFLICT", "STOPPED_PROTOCOL_MISMATCH", "INCONCLUSIVE",
    "ROLLED_BACK", "STOPPED", "GOVERNANCE_READY", "ARCHITECTURE_READY",
    "STARTED", "REVIEW_PASSED", "OWNER_ACCEPTED", "CHECKPOINT_VERIFIED",
    "IN_PROGRESS", "BLOCKED", "VERIFIED", "NOT_VERIFIED", "MISSING",
    "NOT_AUTHORIZED", "NOT_READY", "PROTOCOL_MISMATCH",
}

# Токены с такими суффиксами обязаны быть известными состояниями —
# ловит ссылки на несуществующие состояния (как NEXT_WORK_ITEM_BUILDING).
STATE_SUFFIXES = ("_READY", "_ACCEPTED", "_VERIFIED", "_AUTHORIZED",
                  "_LOCKED", "_BUILDING", "_PASSED", "_MISMATCH", "_CONFLICT")

DEC_REQUIRED = ["id:", "date:", "owner:", "type:", "scope:", "decision:",
                "allowed:", "forbidden:"]

ISO_DATE_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?)?")
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")

errors, warnings = [], []


def scan_files():
    for d in SCAN_DIRS:
        for p in sorted((ROOT / d).rglob("*")):
            if p.is_file() and p.name not in SKIP_FILES and p.suffix in (".md", ".yaml"):
                yield p
    for f in SCAN_FILES:
        p = ROOT / f
        if p.exists():
            yield p


def rel(p):
    return p.relative_to(ROOT).as_posix()


def check_refs(path, text):
    for m in re.finditer(r"docs/(\d{2})", text):
        n = m.group(1)
        if not list((ROOT / "docs").glob(f"{n}_*.md")):
            errors.append(f"{rel(path)}: ссылка docs/{n} — файл не существует")
    for m in re.finditer(r"agents/(AGENT_[A-Z_]+)", text):
        if not (ROOT / "agents" / f"{m.group(1)}.md").exists():
            errors.append(f"{rel(path)}: ссылка agents/{m.group(1)} — файл не существует")
    for m in re.finditer(r"templates/([A-Z_]+\.(?:md|yaml))", text):
        if not (ROOT / "templates" / m.group(1)).exists():
            errors.append(f"{rel(path)}: ссылка templates/{m.group(1)} — файл не существует")
    for m in re.finditer(r"skills/([a-z]+)", text):
        if not (ROOT / "skills" / m.group(1) / "SKILL.md").exists():
            errors.append(f"{rel(path)}: ссылка skills/{m.group(1)} — скилл не существует")


def check_states(path, text):
    # убираем yaml-плейсхолдеры <...>
    t = re.sub(r"<[^>]*>", " ", text)
    for m in re.finditer(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", t):
        tok = m.group(0)
        if tok in ALLOWED_TOKENS:
            continue
        if tok.endswith(STATE_SUFFIXES):
            errors.append(f"{rel(path)}: неизвестное состояние {tok}")


def check_state_enum():
    p = ROOT / "docs" / "09_ACTIVE_STATE.md"
    if not p.exists():
        errors.append("docs/09_ACTIVE_STATE.md отсутствует")
        return
    text = p.read_text(encoding="utf-8")
    for s in CANON_STATES:
        if s not in text:
            errors.append(f"docs/09: состояние {s} отсутствует в ACTIVE_STATE")


def check_decisions():
    p = ROOT / "docs" / "10_DECISION_LOG.md"
    if not p.exists():
        errors.append("docs/10_DECISION_LOG.md отсутствует")
        return
    check_decision_fields(p.read_text(encoding="utf-8"))


def check_decision_fields(text):
    entries = re.split(r"(?m)^- id: ", text)[1:]
    for e in entries:
        dec_id = e.splitlines()[0].strip()
        for field in DEC_REQUIRED[1:]:
            if not re.search(rf"(?m)^\s+{re.escape(field)}", e):
                errors.append(f"docs/10: DEC {dec_id} — нет поля {field}")


def _record_fields(chunk):
    """Скалярные поля записи — как их читает сервер (_parse_decisions):
    строка продолжения с отступом приклеивается к значению через пробел."""
    fields, key = {}, None
    for line in chunk.splitlines()[1:]:
        m = re.match(r"^  (\w+):[ \t]*(.*)$", line)
        if m:
            key, fields[m.group(1)] = m.group(1), m.group(2).strip()
        elif re.match(r"^    - ", line):
            key = None  # пункт списка allowed/forbidden
        elif key and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields


def _valid_date(value):
    """ISO8601, который увидит list_expired сервера (разбор value[:19])."""
    if not ISO_DATE_RE.fullmatch(value):
        return False
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            datetime.strptime(value[:19], fmt)
            return True
        except ValueError:
            continue
    return False


RECORDS_RE = re.compile(r"(?ms)^## Записи\s*\n+```yaml\n(.*?)^```")


def schema_types(text):
    """Enum типов — только из схемы (до «## Записи»), не из первой записи."""
    block = RECORDS_RE.search(text)
    schema = re.search(r"(?m)^\s+type:\s*([A-Z0-9_]+(?:\s*\|\s*[A-Z0-9_]+)+)\s*$",
                       text[:block.start()] if block else text)
    if not schema:
        errors.append("docs/10: в схеме не найден enum типов (type: A | B | …)")
        return set()
    return {t.strip() for t in schema.group(1).split("|")}


def check_decision_records():
    p = ROOT / "docs" / "10_DECISION_LOG.md"
    if not p.exists():
        return  # отсутствие файла сообщает check_decisions
    text = p.read_text(encoding="utf-8")
    if not RECORDS_RE.search(text):
        errors.append("docs/10: не найден yaml-блок секции «## Записи»")
        return
    check_records(text, schema_types(text))


def check_records(text, types):
    block = RECORDS_RE.search(text)
    if not block:
        errors.append("docs/10: не найден yaml-блок секции «## Записи»")
        return
    outside = text[:block.start(1)] + text[block.end(1):]
    for m in re.finditer(r"(?m)^- id: (DEC-\d+)", outside):
        errors.append(f"docs/10: {m.group(1)} — запись вне блока «## Записи»: "
                      "сервер её не видит")
    seen, last_num, last_date = set(), 0, ""
    for chunk in re.split(r"(?m)^- id: ", block.group(1))[1:]:
        dec_id = chunk.splitlines()[0].strip()
        fields = _record_fields(chunk)
        m = re.fullmatch(r"DEC-(\d{4})", dec_id)
        if not m:
            errors.append(f"docs/10: {dec_id} — id не в формате DEC-NNNN")
            continue
        num = int(m.group(1))
        if dec_id in seen:
            errors.append(f"docs/10: {dec_id} — повтор DEC-ID")
        elif num <= last_num:
            errors.append(f"docs/10: {dec_id} стоит после DEC-{last_num:04d} — "
                          "номера должны расти")
        seen.add(dec_id)
        last_num = max(last_num, num)
        type_ = fields.get("type", "").strip()
        if types and type_ not in types:
            errors.append(f"docs/10: {dec_id} — type {type_!r} не из схемы")
        if type_ in ("ACCEPTANCE", "RELEASE") and not SHA256_RE.fullmatch(
                fields.get("evidenceReadHash", "").strip()):
            errors.append(f"docs/10: {dec_id} — {type_} без sha256 в "
                          "evidenceReadHash (правило 6)")
        expires = fields.get("expiresAt", "").strip()
        if expires not in ("", "null") and not _valid_date(expires):
            errors.append(f"docs/10: {dec_id} — expiresAt {expires!r} не "
                          "ISO8601 или такой даты нет")
        date = fields.get("date", "").strip()
        if date and last_date and date < last_date:
            warnings.append(f"docs/10: {dec_id} — дата {date} раньше "
                            f"предыдущей записи ({last_date})")
        last_date = max(last_date, date)


def check_stop_conditions():
    p = ROOT / "docs" / "33_STOP_CONDITIONS.md"
    if not p.exists():
        errors.append("docs/33_STOP_CONDITIONS.md отсутствует")
        return
    nums = [int(m.group(1)) for m in
            re.finditer(r"(?m)^\s*(\d{1,2})\.\s", p.read_text(encoding="utf-8"))]
    if nums and nums != list(range(1, max(nums) + 1)):
        errors.append(f"docs/33: нумерация stop conditions не непрерывна: {nums}")


def check_index():
    p = ROOT / "docs" / "INDEX.md"
    if not p.exists():
        errors.append("docs/INDEX.md отсутствует")
        return
    listed = set(re.findall(r"docs/(\d{2})", p.read_text(encoding="utf-8")))
    actual = {f.name[:2] for f in (ROOT / "docs").glob("[0-9][0-9]_*.md")}
    for n in sorted(actual - listed):
        errors.append(f"docs/INDEX.md: нет записи для docs/{n}")
    for n in sorted(listed - actual):
        errors.append(f"docs/INDEX.md: запись docs/{n} — файл не существует")


def check_skills():
    for p in sorted((ROOT / "skills").glob("*/SKILL.md")):
        head = p.read_text(encoding="utf-8")[:600]
        for field in ("name:", "description:", "whenToUse:"):
            if field not in head:
                errors.append(f"{rel(p)}: нет frontmatter-поля {field}")


# --- экземпляр (--project) ------------------------------------------------

# Признаки копии кита в проекте: устаревают и не обновляются вместе с китом.
KIT_MARKERS = ("mcp_server/server.py", "tools/protocol_lint.py",
               "docs/16_STATE_MACHINE.md", "agents/AGENT_CONTRACT.md",
               "istomahandoff.md")
SKILL_COPY_DIRS = (".kimi-code/skills", ".claude/skills")


def _inside(path, root):
    """path совпадает с root или лежит внутри — по идентичности каталогов,
    а не по строке (префикс \\?\\ и UNC-алиасы Windows)."""
    for candidate in (path, *path.parents):
        try:
            if os.path.samefile(candidate, root):
                return True
        except OSError:
            continue
    return False


# Переменные, которые увели бы git в чужой репозиторий (как в сервере).
GIT_REDIRECT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
                    "GIT_NAMESPACE", "GIT_PREFIX")
# protocol.version — тем же выражением, что protocol_version сервера
VERSION_RE = re.compile(r'(?m)^protocol:[ \t]*(?:#.*)?\n(?:[ \t]+.*\n)*?[ \t]+version:'
                        r'[ \t]*"?([^"\s#]*)"?')


def _read_project_text(path, rel):
    """Текст файла экземпляра; не UTF-8 — ERROR вместо трассировки."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append(f"{rel}: не UTF-8 — файлы экземпляра хранятся в UTF-8")
        return None


def _state_fields(text):
    """(раздел, ключ) → значение yaml-блока docs/09: ключи с любым отступом
    относятся к своему разделу верхнего уровня, берётся первое вхождение."""
    fields, section = {}, None
    for line in text.splitlines():
        top = re.match(r"^([A-Za-z]\w*):\s*(?:#.*)?$", line)
        sub = re.match(r"^[ \t]+(\w+):\s*([^#\n]*)", line)
        if top:
            section = top.group(1)
        elif sub and section:
            fields.setdefault((section, sub.group(1)), sub.group(2).strip().strip('"'))
    return fields


def _unfilled(value):
    return not value or value.startswith("<") or "|" in value or value in ("null", "~")


def docs16_states():
    """Состояния цепочки и цели аварийных переходов — из docs/16 кита."""
    text = (ROOT / "docs" / "16_STATE_MACHINE.md").read_text(encoding="utf-8")
    chain = re.search(r"\A.*?```text\n(.*?)```", text, re.S)
    states = {s.strip().removeprefix("->").strip()
              for s in (chain.group(1).splitlines() if chain else []) if s.strip()}
    emergency = re.search(r"## Аварийные\s*\n+```text\n(.*?)```", text, re.S)
    if emergency:
        states |= set(re.findall(r"->\s*([A-Z_]+)", emergency.group(1)))
    return states


def check_instance_state(text):
    f = _state_fields(text)
    # строки change record — тем же разбором, что protocol_version сервера
    versions = [r[0] for r in re.findall(
        r"(?m)^\|\s*(\d+\.\d+)\s*\|\s*([0-9-]+)\s*\|\s*(.*?)\s*\|$",
        (ROOT / "docs" / "42_MAINTENANCE.md").read_text(encoding="utf-8"))]
    states = docs16_states()
    main_doc = (ROOT / "istomahandoff.md").read_text(encoding="utf-8")
    version = VERSION_RE.search(text)
    values = {"version": version.group(1) if version else None,
              "level": f.get(("protocol", "level")),
              "state": f.get(("activeWorkItem", "state"))}
    checks = (
        ("protocol", "version", lambda v: v in versions,
         "нет в change record docs/42 кита"),
        ("protocol", "level", lambda v: v in ("P0", "P1", "P2"), "ожидается P0 | P1 | P2"),
        ("activeWorkItem", "state", lambda v: v in states,
         "состояния нет в docs/16 кита"),
    )
    for section, key, ok, why in checks:
        value = values[key]
        if value is None:
            errors.append(f"docs/09: нет поля {section}.{key} (шаблон — docs/09 кита)")
        elif _unfilled(value):
            warnings.append(f"docs/09: {section}.{key} не заполнено")
        elif ok(value):
            continue
        elif key == "state" and f"`{value}`" in main_doc:
            # пробел канона: состояние названо в istomahandoff.md, а docs/16 его не знает
            warnings.append(f"docs/09: {section}.{key} = {value!r} — состояние названо "
                            "в istomahandoff.md, но не описано в docs/16 кита "
                            "(validate_transition его не знает)")
        else:
            errors.append(f"docs/09: {section}.{key} = {value!r} — {why}")


def _same_text(a, b):
    return a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")


def _kit_copy(path, kit_file):
    """Копия кита: равна файлу кита (без учёта EOL) или называет протокол;
    свой файл проекта по тому же пути копией не считается."""
    if kit_file.is_file() and _same_text(path, kit_file):
        return True
    return b"istomahandoff" in path.read_bytes().lower()


def _record_chunks(text):
    """{DEC-ID: текст записи} блока «## Записи»; EOL, хвостовые пробелы и
    строки-промежутки между записями (пустые, комментарии) не в счёт."""
    block = RECORDS_RE.search(text.replace("\r\n", "\n"))
    out = {}
    for chunk in re.split(r"(?m)^(?=- id: )", block.group(1) if block else ""):
        if not chunk.startswith("- id: "):
            continue
        lines = [line.rstrip() for line in chunk.split("\n")]
        while lines and (not lines[-1] or lines[-1].lstrip().startswith("#")):
            lines.pop()
        out.setdefault(lines[0][6:].strip(), "\n".join(lines))
    return out


def _evidence_text_attr(project):
    """Атрибут text для файлов evidence/ так, как его видит git (порядок
    строк, макросы, BOM, вложенные .gitattributes); None — без git."""
    env = {k: v for k, v in os.environ.items() if k not in GIT_REDIRECT_ENV}
    try:
        proc = subprocess.run(["git", "check-attr", "text", "--", "evidence/.probe"],
                              cwd=project, capture_output=True, text=True,
                              encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, env=env, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r": text: (\S+)$", proc.stdout.strip())
    return m.group(1) if proc.returncode == 0 and m else None


def check_gitattributes(project):
    attr = _evidence_text_attr(project)
    if attr is None:  # не git-репозиторий или git недоступен — по байтам файла
        ga = project / ".gitattributes"
        raw = ga.read_bytes().removeprefix(b"\xef\xbb\xbf") if ga.is_file() else b""
        attr = "unset" if re.search(rb"(?m)^evidence/\*\*[ \t]+-text[ \t]*\r?$", raw) \
            else "unspecified"
    if attr == "unspecified":
        warnings.append(".gitattributes: нет правила evidence/** -text "
                        "(docs/31, «Хэш evidence»)")
    elif attr != "unset":
        warnings.append(f".gitattributes: для evidence/ git видит text={attr} — EOL "
                        "меняется и хэш evidence зависит от ОС; нужно evidence/** "
                        "-text без поздних переопределений (docs/31, «Хэш evidence»)")


def check_instance(project):
    log = project / "docs" / "10_DECISION_LOG.md"
    kit_log = (ROOT / "docs" / "10_DECISION_LOG.md").read_text(encoding="utf-8")
    holds_canon = (project / "istomahandoff.md").is_file() and \
        (project / "docs" / "16_STATE_MACHINE.md").is_file()
    text = _read_project_text(log, "docs/10_DECISION_LOG.md") if log.is_file() else None
    if not log.is_file():
        errors.append("docs/10_DECISION_LOG.md отсутствует — экземпляр не "
                      "инициализирован (tools/instance_init.py)")
    elif text is not None:
        block = RECORDS_RE.search(text)
        # поля проверяются у записей проекта; копия схемы — не запись (ADR-0001 п.7)
        check_decision_fields(block.group(1) if block else "")
        check_records(text, schema_types(kit_log))
        kit_records = set(_record_chunks(kit_log).values())
        imported = [dec_id for dec_id, chunk in _record_chunks(text).items()
                    if chunk in kit_records]
        if imported:
            # с каноном в корне клон протокола и проект с копией кита по
            # журналу не различить — совет CORRECTION только с оговоркой
            warnings.append(
                "docs/10: записи " + ", ".join(imported) + " побайтно "
                "совпадают с журналом протокола (кита) — "
                + ("если это рабочий клон протокола, это его собственный "
                   "журнал; если проект с копией кита — импорт: "
                   if holds_canon else "импорт: ")
                + "полномочий в проекте они не дают, нужна CORRECTION в "
                  "журнале проекта")
    state = project / "docs" / "09_ACTIVE_STATE.md"
    if not state.is_file():
        errors.append("docs/09_ACTIVE_STATE.md отсутствует")
    else:
        state_text = _read_project_text(state, "docs/09_ACTIVE_STATE.md")
        if state_text is not None:
            check_instance_state(state_text)
    if not (project / "docs" / "11_HANDOFF_MEMO.md").is_file():
        warnings.append("docs/11_HANDOFF_MEMO.md отсутствует")
    check_gitattributes(project)
    copies = [rel_path for rel_path in KIT_MARKERS
              if (project / rel_path).is_file() and
              _kit_copy(project / rel_path, ROOT / rel_path)]
    if holds_canon:
        # клону протокола «удалите копию кита» был бы вредным советом
        warnings.append("в корне проекта лежит канон (" + ", ".join(copies) + "): "
                        "если это рабочий клон протокола, его проверяет "
                        "python tools/protocol_lint.py в самом клоне; если "
                        "проект с копией кита — копия удаляется при миграции "
                        "экземпляра")
    else:
        for rel_path in copies:
            warnings.append(f"{rel_path}: в проекте копия кита — не обновляется "
                            "вместе с китом")
    for d in SKILL_COPY_DIRS:
        for kit_skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
            copy = project / d / kit_skill.parent.name / "SKILL.md"
            if not copy.is_file() or _same_text(copy, kit_skill):
                continue
            raw = copy.read_bytes()
            # у скиллов кита во frontmatter есть whenToUse; свой скилл проекта
            # с тем же именем копией не считается
            if b"whenToUse:" in raw or b"istomahandoff" in raw.lower():
                warnings.append(f"{d}/{kit_skill.parent.name}: копия скилла "
                                "отличается от кита")


def main_project(arg):
    project = Path(arg)
    if not project.is_absolute():
        errors.append(f"--project: ожидается абсолютный путь, получено {arg!r}")
    elif not project.resolve().is_dir():
        errors.append(f"--project: каталог не найден: {arg}")
    elif _inside(project.resolve(), ROOT):
        errors.append("--project: каталог — кит или внутри кита; кит проверяется "
                      "без --project")
    else:
        check_instance(project.resolve())
    print(f"Экземпляр: {Path(arg).as_posix()}; канон: {ROOT.as_posix()}")
    for w in sorted(set(warnings)):
        print(f"WARNING {w}")
    for e in sorted(set(errors)):
        print(f"ERROR   {e}")
    print(f"Итог: {len(set(errors))} errors, {len(set(warnings))} warnings")
    sys.exit(1 if errors else 0)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if args:
        if len(args) == 2 and args[0] == "--project":
            main_project(args[1])
        print("использование: protocol_lint.py [--project <абсолютный путь>]")
        sys.exit(2)
    files = list(scan_files())
    for p in files:
        text = p.read_text(encoding="utf-8")
        check_refs(p, text)
        if p.suffix == ".md":
            check_states(p, text)
    check_state_enum()
    check_decisions()
    check_decision_records()
    check_stop_conditions()
    check_index()
    check_skills()

    print(f"Проверено файлов: {len(files)}")
    for w in sorted(set(warnings)):
        print(f"WARNING {w}")
    for e in sorted(set(errors)):
        print(f"ERROR   {e}")
    print(f"Итог: {len(set(errors))} errors, {len(set(warnings))} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
