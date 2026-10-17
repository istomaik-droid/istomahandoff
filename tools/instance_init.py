"""Создать файлы экземпляра протокола в проекте из канона этого кита.

Запуск: python <кит>/tools/instance_init.py <абсолютный путь к проекту>

Создаёт docs/09 (шаблон кита, protocol.version — версия кита из docs/42),
docs/10 (схема и правила кита, блок «## Записи» пуст: записи кита — журнал
самого протокола), docs/11 и templates/PROJECT_PROFILE.yaml (шаблоны),
evidence/.gitkeep; дописывает в .gitattributes правило evidence/** -text
(docs/31). Всё или ничего: существующие файлы не перезаписываются, все
проверки — до первой записи, при сбое записи созданное откатывается.
Коммит — за человеком.
"""
import os
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
RECORDS_RE = re.compile(r"(?ms)^(## Записи\s*\n+```yaml\n)(.*?)(^```)")
GITATTR_RULE = b"evidence/** -text"
GITATTR_RULE_RE = re.compile(rb"(?m)^evidence/\*\*[ \t]+-text[ \t]*\r?$")


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


def _kit(rel):
    return (KIT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def build():
    rows = re.findall(r"(?m)^\|\s*(\d+\.\d+)\s*\|\s*([0-9-]+)\s*\|\s*(.*?)\s*\|$",
                      _kit("docs/42_MAINTENANCE.md"))
    state, n = re.subn(r'(?m)^(\s+version:\s*)"[^"]*"',
                       rf'\g<1>"{rows[-1][0]}"' if rows else r"\g<1>",
                       _kit("docs/09_ACTIVE_STATE.md"), count=1)
    log, m = RECORDS_RE.subn(lambda m: m.group(1) + m.group(3),
                             _kit("docs/10_DECISION_LOG.md"), count=1)
    if not (rows and n and m):
        raise SystemExit("кит повреждён: нет версии docs/42, поля version "
                         "docs/09 или блока «## Записи» docs/10")
    return {"docs/09_ACTIVE_STATE.md": state, "docs/10_DECISION_LOG.md": log,
            "docs/11_HANDOFF_MEMO.md": _kit("docs/11_HANDOFF_MEMO.md"),
            "templates/PROJECT_PROFILE.yaml": _kit("templates/PROJECT_PROFILE.yaml"),
            "evidence/.gitkeep": ""}


def _problem(project, files):
    """Причина отказа или None; ничего не пишет."""
    existing = [rel for rel in files if (project / rel).exists()]
    if existing:
        return "уже есть: " + ", ".join(existing)
    for rel in [*files, ".gitattributes"]:
        parts = Path(rel).parts
        for i in range(1, len(parts)):
            parent = project.joinpath(*parts[:i])
            if parent.exists() and not parent.is_dir():
                return f"{Path(*parts[:i]).as_posix()} — не каталог"
        if _inside((project / rel).resolve(), KIT):
            return f"{rel} ведёт в кит (ссылка или junction)"
    ga = project / ".gitattributes"
    if ga.exists() and not ga.is_file():
        return ".gitattributes — не файл"
    return None


def _gitattributes(project):
    """(исходные байты или None, нужно ли дописать правило, причина отказа)."""
    ga = project / ".gitattributes"
    if not ga.is_file():
        return None, True, None
    try:
        raw = ga.read_bytes()
    except OSError as e:
        return None, True, f".gitattributes не читается ({e})"
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw, True, (".gitattributes в UTF-16 — git читает его как байты и "
                           "правил не видит; перекодируйте в UTF-8")
    need = not GITATTR_RULE_RE.search(raw.removeprefix(b"\xef\xbb\xbf"))
    if need and not os.access(ga, os.W_OK):
        return raw, True, (".gitattributes только для чтения — правило "
                           "evidence/** -text не дописать")
    return raw, need, None


def _rollback(project, created, raw, touched_ga):
    for path in reversed(created):
        if path.is_dir():
            path.rmdir()
        else:
            path.unlink(missing_ok=True)
    if touched_ga:  # правило дописывалось — вернуть исходные байты
        ga = project / ".gitattributes"
        if raw is None:
            ga.unlink(missing_ok=True)
        else:
            ga.write_bytes(raw)


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) != 1 or not Path(argv[0]).is_absolute():
        print("использование: instance_init.py <абсолютный путь к проекту>")
        return 2
    project = Path(argv[0]).resolve()
    if not project.is_dir():
        print(f"каталог не найден: {project.as_posix()}")
        return 2
    if _inside(project, KIT):
        print("отказ: проект — это кит или каталог внутри кита")
        return 1
    files = build()
    raw, need_rule, why = _gitattributes(project)
    why = _problem(project, files) or why
    if why:
        print(f"отказ, ничего не создано — {why}")
        return 1
    created, touched_ga = [], False  # что сделал этот запуск — для отката
    try:
        for rel, text in files.items():
            path = project / rel
            missing = [p for p in reversed(path.parents) if not p.exists()]
            for d in missing:
                d.mkdir()
                created.append(d)
            with path.open("x", encoding="utf-8", newline="\n") as f:
                created.append(path)
                f.write(text)
        if need_rule:
            sep = b"" if not raw or raw.endswith(b"\n") else b"\n"
            touched_ga = True
            with (project / ".gitattributes").open("ab") as f:
                f.write(sep + GITATTR_RULE + b"\n")
    except OSError as e:
        _rollback(project, created, raw, touched_ga)
        print(f"отказ, ничего не создано — сбой записи, созданное откатено: {e}")
        return 1
    for rel in files:
        print(f"создан {rel}")
    if need_rule:
        print(".gitattributes: добавлено evidence/** -text")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
