"""Protocol lint — самопроверка согласованности протокола istomahandoff.

Проверяет (errors — exit 1, warnings — только вывод):
  1. Ссылки docs/NN, agents/X, templates/X, skills/x — цели существуют.
  2. docs/09 enum состояний покрывает каноническую state machine (14 состояний).
  3. Записи DEC в docs/10 содержат обязательные поля.
  4. Нумерация пунктов docs/33 (stop conditions) непрерывна.
  5. State-подобные токены (UPPER_SNAKE) — известны (warning, если нет).

Запуск: python tools/protocol_lint.py   (из корня репозитория протокола)
"""
import re
import sys
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
    text = p.read_text(encoding="utf-8")
    entries = re.split(r"(?m)^- id: ", text)[1:]
    for e in entries:
        dec_id = e.splitlines()[0].strip()
        for field in DEC_REQUIRED[1:]:
            if not re.search(rf"(?m)^\s+{re.escape(field)}", e):
                errors.append(f"docs/10: DEC {dec_id} — нет поля {field}")


def check_stop_conditions():
    p = ROOT / "docs" / "33_STOP_CONDITIONS.md"
    if not p.exists():
        errors.append("docs/33_STOP_CONDITIONS.md отсутствует")
        return
    nums = [int(m.group(1)) for m in
            re.finditer(r"(?m)^\s*(\d{1,2})\.\s", p.read_text(encoding="utf-8"))]
    if nums and nums != list(range(1, max(nums) + 1)):
        errors.append(f"docs/33: нумерация stop conditions не непрерывна: {nums}")


def check_skills():
    for p in sorted((ROOT / "skills").glob("*/SKILL.md")):
        head = p.read_text(encoding="utf-8")[:600]
        for field in ("name:", "description:", "whenToUse:"):
            if field not in head:
                errors.append(f"{rel(p)}: нет frontmatter-поля {field}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = list(scan_files())
    for p in files:
        text = p.read_text(encoding="utf-8")
        check_refs(p, text)
        if p.suffix == ".md":
            check_states(p, text)
    check_state_enum()
    check_decisions()
    check_stop_conditions()
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
