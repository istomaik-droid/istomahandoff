"""Тесты protocol_lint: инварианты журнала решений docs/10 (DEC-0017) и
проверка экземпляра --project (DEC-0018).

Lint запускается из копии кита (conftest.copy_kit), поэтому проверяется
код из рабочего дерева, а журнал реального репозитория не трогается.
"""
import os
import re
import shutil
import subprocess
import sys

import pytest

from conftest import LOG, configure, copy_kit, git, make_instance

SHA = "0" * 63 + "1"
ENTRY = """- id: {id}
  date: {date}
  owner: OWNER
  type: {type}
  scope: tests/
  decision: тест
  allowed:
    - a
  forbidden:
    - b
  expiresAt: {expires}
  receiptSha256: null
  evidenceReadHash: {hash}
  mandateRef: null
"""


def entry(id, date="2026-10-01", type="IMPLEMENTATION", expires="null", hash="null"):
    return ENTRY.format(id=id, date=date, type=type, expires=expires, hash=hash)


@pytest.fixture
def canon(tmp_path):
    root = tmp_path / "canon"
    copy_kit(root, fixture_log=True)
    return root


def lint(root, *args):
    proc = subprocess.run(
        [sys.executable, str(root / "tools" / "protocol_lint.py"), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL,
    )
    return proc.returncode, proc.stdout


def insert_entries(log, *entries, after_block=""):
    """Дописать записи в конец блока «## Записи» (и текст после него)."""
    text = log.read_text(encoding="utf-8")
    m = re.search(r"(?ms)^## Записи\s*\n+```yaml\n(.*?)^```\n", text)
    text = (text[:m.end(1)] + "".join(entries) + text[m.end(1):m.end()]
            + after_block + text[m.end():])
    log.write_text(text, encoding="utf-8", newline="\n")


def run_lint(root, *entries, after_block=""):
    """Дописать записи в журнал копии кита и запустить lint кита."""
    insert_entries(root / LOG, *entries, after_block=after_block)
    return lint(root)


def errors(out):
    return [line for line in out.splitlines() if line.startswith("ERROR")]


def test_lint_accepts_a_consistent_log(canon):
    code, out = run_lint(canon, entry("DEC-0002"),
                         entry("DEC-0003", type="ACCEPTANCE", hash=SHA,
                               expires="2099-12-31T10:00:00+03:00"))
    assert code == 0, out


@pytest.mark.parametrize("entries, culprit", [
    ([entry("DEC-0002", type="APPROVAL")], "DEC-0002"),    # type не из схемы
    ([entry("DEC-0002", type="ACCEPTANCE")], "DEC-0002"),  # правило 6: нет хэша
    ([entry("DEC-0002", type="RELEASE", hash="прочитал")], "DEC-0002"),
    ([entry("DEC-0002", type="ACCEPTANCE", hash=SHA + "0")], "DEC-0002"),
    ([entry("DEC-0002", type="RELEASE", hash=SHA + " # прочитал")], "DEC-0002"),
    ([entry("DEC-0002", expires="завтра")], "DEC-0002"),
    ([entry("DEC-0002", expires="2026-12-31 10:00")], "DEC-0002"),
    ([entry("DEC-0002", expires="2020-01-01T00:00:00 (продлено до 2099-12-31)")], "DEC-0002"),
    ([entry("DEC-0002", expires="2026-02-30")], "DEC-0002"),  # такой даты нет
    ([entry("DEC-018")], "DEC-018"),                       # id не в формате
])
def test_lint_rejects_broken_log_invariants(canon, entries, culprit):
    code, out = run_lint(canon, *entries)
    assert code == 1, out
    assert any(culprit in line for line in errors(out)), out


def test_lint_reports_duplicate_and_decreasing_ids_separately(canon):
    code, out = run_lint(canon, entry("DEC-0005"), entry("DEC-0005"), entry("DEC-0002"))
    assert code == 1, out
    assert any("DEC-0005" in line and "повтор" in line for line in errors(out)), out
    assert any("DEC-0002" in line and "расти" in line for line in errors(out)), out


def test_lint_reads_continuation_lines_like_the_server(canon):
    tail = entry("DEC-0002", expires="2020-01-01").replace(
        "  expiresAt: 2020-01-01\n",
        "  expiresAt: 2020-01-01\n    (продлено до 2099-12-31)\n")
    code, out = run_lint(canon, tail)
    assert code == 1, out
    assert any("DEC-0002" in line for line in errors(out)), out


def test_lint_rejects_records_outside_the_block(canon):
    code, out = run_lint(canon, after_block="\n" + entry("DEC-0002", type="RELEASE"))
    assert code == 1, out
    assert any("DEC-0002" in line for line in errors(out)), out


def test_lint_requires_the_type_enum_in_the_schema(canon):
    log = canon / LOG
    text = log.read_text(encoding="utf-8")
    schema_end = text.index("## Записи")
    head = re.sub(r"(?m)^  type: [A-Z| ]+$", "  type: <TYPE>", text[:schema_end])
    log.write_text(head + text[schema_end:], encoding="utf-8", newline="\n")
    code, out = lint(canon)
    assert code == 1, out
    # записи с правильным типом не объявляются «не из схемы»
    assert not any("DEC-0001" in line for line in errors(out)), out


def test_lint_requires_the_records_block(canon):
    log = canon / LOG
    log.write_text(log.read_text(encoding="utf-8").replace("## Записи", "## Entries"),
                   encoding="utf-8", newline="\n")
    code, out = lint(canon)
    assert code == 1, out


def test_lint_only_warns_about_dates_going_backwards(canon):
    code, out = run_lint(canon, entry("DEC-0002", date="2026-09-01"))
    assert code == 0, out
    assert any(line.startswith("WARNING") and "DEC-0002" in line
               for line in out.splitlines()), out


# --- экземпляр: protocol_lint.py --project (DEC-0018) ---------------------------

@pytest.fixture
def instance(tmp_path, canon):
    root = tmp_path / "proj"
    make_instance(root, canon)
    return root


def kit_version(kit):
    text = (kit / "docs" / "42_MAINTENANCE.md").read_text(encoding="utf-8")
    return re.findall(r"(?m)^\|\s*(\d+\.\d+)\s*\|", text)[-1]


def edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def warnings_(out):
    return [line for line in out.splitlines() if line.startswith("WARNING")]


STATE_ENUM = "  state: INTAKE | TRIAGE |"


def test_project_lint_accepts_a_fresh_instance(canon, instance):
    code, out = lint(canon, "--project", instance)
    assert code == 0, out
    assert "WARNING docs/09: protocol.version не заполнено" in out
    assert not any("импорт" in line for line in warnings_(out)), out


def test_project_lint_does_not_scan_project_docs(canon, instance):
    (instance / "README.md").write_text("см. docs/99, состояние FEATURE_READY\n",
                                        encoding="utf-8")
    (instance / "docs" / "49_PROJECT_NOTES.md").write_text("docs/77\n", encoding="utf-8")
    (instance / "skills" / "deploy").mkdir(parents=True)
    (instance / "skills" / "deploy" / "SKILL.md").write_text("без frontmatter\n",
                                                             encoding="utf-8")
    code, out = lint(canon, "--project", instance)
    assert code == 0, out
    assert f"Экземпляр: {instance.as_posix()}" in out  # проверен проект, а не кит


def test_project_lint_accepts_filled_state(canon, instance):
    state = instance / "docs" / "09_ACTIVE_STATE.md"
    edit(state, '"<SEMVER>"', f'"{kit_version(canon)}"')
    edit(state, "level: P0 | P1 | P2", "level: P1")
    line = next(x for x in state.read_text(encoding="utf-8").splitlines()
                if x.startswith(STATE_ENUM))
    edit(state, line, "  state: STOPPED_PROTOCOL_MISMATCH")
    code, out = lint(canon, "--project", instance)
    assert code == 0, out
    assert f"Экземпляр: {instance.as_posix()}" in out
    assert "docs/09" not in out


@pytest.mark.parametrize("old, new, culprit", [
    ('"<SEMVER>"', '"9.9"', "protocol.version"),
    ("level: P0 | P1 | P2", "level: P3", "protocol.level"),
    (None, "  state: BUILDNG", "activeWorkItem.state"),
])
def test_project_lint_checks_active_state_values(canon, instance, old, new, culprit):
    state = instance / "docs" / "09_ACTIVE_STATE.md"
    if old is None:
        old = next(x for x in state.read_text(encoding="utf-8").splitlines()
                   if x.startswith(STATE_ENUM))
    edit(state, old, new)
    code, out = lint(canon, "--project", instance)
    assert code == 1, out
    assert any(culprit in line for line in errors(out)), out


def test_project_lint_takes_the_type_enum_from_the_kit(canon, instance):
    log = instance / LOG
    edit(log, "BOUNDARY | IMPLEMENTATION |", "BOUNDARY |")  # копия схемы в проекте не читается
    insert_entries(log, entry("DEC-0002"), entry("DEC-0003", type="APPROVAL"))
    code, out = lint(canon, "--project", instance)
    assert code == 1, out
    assert any("DEC-0003" in line for line in errors(out)), out
    assert not any("DEC-0002" in line for line in errors(out)), out


def test_project_lint_checks_record_invariants(canon, instance):
    insert_entries(instance / LOG, entry("DEC-0005"), entry("DEC-0002", type="ACCEPTANCE"))
    code, out = lint(canon, "--project", instance)
    assert code == 1, out
    assert any("DEC-0002" in line and "расти" in line for line in errors(out)), out
    assert any("DEC-0002" in line and "правило 6" in line for line in errors(out)), out


@pytest.mark.parametrize("where", ["kit", "inside", "alias"])
def test_project_lint_refuses_the_kit(canon, where):
    if where == "alias" and os.name != "nt":
        pytest.skip("префикс \\\\?\\ — только Windows")
    target = {"kit": canon, "inside": canon / "docs",
              "alias": "\\\\?\\" + str(canon / "docs")}[where]
    code, out = lint(canon, "--project", target)
    assert code == 1, out
    assert any("кит" in line for line in errors(out)), out


def test_project_lint_explains_canon_at_the_project_root(canon, instance):
    shutil.copy2(canon / "istomahandoff.md", instance / "istomahandoff.md")
    shutil.copy2(canon / "docs" / "16_STATE_MACHINE.md", instance / "docs" / "16_STATE_MACHINE.md")
    (instance / "mcp_server").mkdir()
    (instance / "mcp_server" / "server.py").write_text("# копия сервера istomahandoff\n",
                                                       encoding="utf-8")
    code, out = lint(canon, "--project", instance)
    assert code == 0, out
    # клону протокола «удалите копию кита» был бы вредным советом — одна строка с оговоркой
    hits = [line for line in warnings_(out) if "копия кита" in line or "канон" in line]
    assert len(hits) == 1, out
    assert "клон протокола" in hits[0] and "mcp_server/server.py" in hits[0], out


def test_project_lint_requires_an_initialized_instance(canon, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    code, out = lint(canon, "--project", plain)
    assert code == 1, out
    assert any("instance_init" in line for line in errors(out)), out


@pytest.mark.parametrize("args, why", [
    (["--project", "proj"], "абсолютный"),
    (["--project", "NOPE"], "не найден"),
    (["--project"], "использование"),
    (["--projekt", "x"], "использование"),
])
def test_project_lint_rejects_bad_arguments(canon, tmp_path, monkeypatch, args, why):
    monkeypatch.chdir(tmp_path)
    make_instance(tmp_path / "proj", canon)  # без проверки пути lint пошёл бы дальше
    args = [str(tmp_path / "nope") if a == "NOPE" else a for a in args]
    code, out = lint(canon, *args)
    assert code in (1, 2) and why in out, out


def test_project_lint_tells_kit_copies_from_own_files(canon, instance):
    def put(rel, data):
        path = instance / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))

    put("mcp_server/server.py", "# свой сервер проекта\n")             # не копия кита
    put("tools/protocol_lint.py", "# старая копия lint istomahandoff\n")  # копия кита
    put(".claude/skills/verify/SKILL.md", "---\nname: verify\ndescription: свой\n---\n")
    put(".kimi-code/skills/verify/SKILL.md", "---\nname: verify\nwhenToUse: старая\n---\n")
    put(".claude/skills/handoff/SKILL.md", "---\nname: handoff\nwhenToUse: старая\n---\n")
    put(".claude/skills/decision/SKILL.md",  # та же копия, только CRLF
        (canon / "skills" / "decision" / "SKILL.md").read_bytes().replace(b"\n", b"\r\n"))
    code, out = lint(canon, "--project", instance)
    assert code == 0, out
    found = "\n".join(warnings_(out))
    assert "tools/protocol_lint.py: в проекте копия кита" in found
    assert "mcp_server/server.py" not in found
    assert ".kimi-code/skills/verify: копия скилла отличается от кита" in found
    assert ".claude/skills/handoff: копия скилла отличается от кита" in found
    assert ".claude/skills/verify" not in found and ".claude/skills/decision" not in found


def test_project_lint_canon_line_needs_both_canon_files(canon, instance):
    shutil.copy2(canon / "istomahandoff.md", instance / "istomahandoff.md")
    code, out = lint(canon, "--project", instance)
    assert "istomahandoff.md: в проекте копия кита" in out
    assert not any("в корне проекта лежит канон" in line for line in warnings_(out)), out


def test_project_lint_warns_about_missing_handoff_and_gitattributes(canon, instance):
    (instance / "docs" / "11_HANDOFF_MEMO.md").unlink()
    code, out = lint(canon, "--project", instance)
    assert code == 0, out
    found = "\n".join(warnings_(out))
    assert "docs/11_HANDOFF_MEMO.md отсутствует" in found
    assert ".gitattributes: нет правила evidence/** -text" in found


def git_repo(path):
    git(path.parent, "init", "-q", "-b", "master", str(path))
    configure(path)


@pytest.mark.parametrize("content, ok", [
    ("evidence/** -text\n", True),
    ("﻿evidence/** -text\n", True),  # BOM: Set-Content -Encoding UTF8
    ("evidence/** binary\n", True),        # binary включает -text
    ("/evidence/** -text\n", True),
    ("evidence/** -text\n* text=auto eol=crlf\n", False),  # поздняя строка снова меняет EOL
    ("*.png binary\n", False),
])
def test_project_lint_reads_gitattributes_like_git(canon, instance, content, ok):
    git_repo(instance)
    (instance / ".gitattributes").write_text(content, encoding="utf-8", newline="\n")
    code, out = lint(canon, "--project", instance)
    assert code == 0, out
    assert (not any(".gitattributes" in line for line in warnings_(out))) is ok, out


@pytest.mark.parametrize("target, data", [
    (".gitattributes", "# бинарные файлы\n*.png binary\n".encode("cp1251")),
    (".gitattributes", "evidence/** -text\n".encode("utf-16")),
    ("docs/09_ACTIVE_STATE.md", "# 09. Активное состояние\n".encode("cp1251")),
    (LOG, "# 10. Журнал\n".encode("utf-16")),
])
def test_project_lint_reports_unreadable_files_without_crashing(canon, instance, target, data):
    (instance / target).write_bytes(data)
    code, out = lint(canon, "--project", instance)
    assert "Итог:" in out, out  # отчёт, а не трассировка
    if target != ".gitattributes":
        assert code == 1 and any(target in line and "UTF-8" in line
                                 for line in errors(out)), out


def test_project_lint_checks_fields_only_in_project_records(canon, instance):
    # копия схемы в журнале проекта — не запись (ADR-0001 п.7)
    edit(instance / LOG, "  allowed: []\n  forbidden: []\n", "")
    code, out = lint(canon, "--project", instance)
    assert code == 0, out


def test_project_lint_requires_record_fields(canon, instance):
    broken = entry("DEC-0002").replace("  allowed:\n    - a\n  forbidden:\n    - b\n", "")
    insert_entries(instance / LOG, broken)
    code, out = lint(canon, "--project", instance)
    assert code == 1, out
    assert any("DEC-0002" in line and "нет поля" in line for line in errors(out)), out


@pytest.mark.parametrize("text, culprit", [
    ("Состояние ведём в Jira.\n", "protocol.version"),
    (None, "activeWorkItem.state"),
])
def test_project_lint_requires_active_state_keys(canon, instance, text, culprit):
    state = instance / "docs" / "09_ACTIVE_STATE.md"
    if text is None:
        line = next(x for x in state.read_text(encoding="utf-8").splitlines()
                    if x.startswith(STATE_ENUM))
        edit(state, line + "\n", "")
    else:
        state.write_text(text, encoding="utf-8", newline="\n")
    code, out = lint(canon, "--project", instance)
    assert code == 1, out
    assert any(culprit in line and "нет поля" in line for line in errors(out)), out


@pytest.mark.parametrize("old, new", [
    ("protocol:\n", "protocol:   # версия и уровень\n"),
    ('  version: "<SEMVER>"', '    version: "<SEMVER>"'),
])
def test_project_lint_reads_the_version_like_the_server(canon, instance, old, new):
    state = instance / "docs" / "09_ACTIVE_STATE.md"
    edit(state, old, new)
    edit(state, '"<SEMVER>"', f'"{kit_version(canon)}"')
    code, out = lint(canon, "--project", instance)
    assert code == 0, out
    assert "protocol.version" not in out


def test_project_lint_accepts_states_named_by_the_canon(canon, instance):
    state = instance / "docs" / "09_ACTIVE_STATE.md"
    line = next(x for x in state.read_text(encoding="utf-8").splitlines()
                if x.startswith(STATE_ENUM))
    edit(state, line, "  state: STOPPED_CONTEXT_CONFLICT")  # istomahandoff.md, не docs/16
    code, out = lint(canon, "--project", instance)
    assert code == 0, out
    assert any("STOPPED_CONTEXT_CONFLICT" in line and "docs/16" in line
               for line in warnings_(out)), out


@pytest.mark.parametrize("holds_canon, gap", [
    (False, ""), (True, ""),
    # между записями протокола и своими — пустая строка, комментарий, пробелы
    (False, "\n"), (False, "# --- записи проекта ---\n"), (False, "   \n"),
])
def test_project_lint_warns_about_imported_kit_records(tmp_path, holds_canon, gap):
    kit = tmp_path / "kit"
    copy_kit(kit)  # реальный журнал кита: DEC-0001…
    proj = tmp_path / "proj"
    make_instance(proj, kit)
    if holds_canon:  # клон протокола или проект с копией кита — не различить
        shutil.copy2(kit / "istomahandoff.md", proj / "istomahandoff.md")
        shutil.copy2(kit / "docs" / "16_STATE_MACHINE.md", proj / "docs" / "16_STATE_MACHINE.md")
    kit_log = (kit / LOG).read_text(encoding="utf-8")
    imported = re.search(r"(?ms)^## Записи\s*\n+```yaml\n(.*?)^```", kit_log).group(1)
    n = len(re.findall(r"(?m)^- id: ", imported))
    log = proj / LOG
    text = log.read_text(encoding="utf-8")
    m = re.search(r"(?ms)^## Записи\s*\n+```yaml\n(.*?)^```", text)
    # журнал экземпляра, собранный копированием кита: записи протокола + свои
    log.write_text(text[:m.start(1)] + imported + gap
                   + entry(f"DEC-{n + 1:04d}", date="2099-01-01")
                   + text[m.end(1):], encoding="utf-8", newline="\n")
    code, out = lint(kit, "--project", proj)
    assert code == 0, out
    hits = [line for line in warnings_(out) if "импорт" in line]
    assert len(hits) == 1, out
    assert "DEC-0001" in hits[0] and f"DEC-{n:04d}" in hits[0]
    assert f"DEC-{n + 1:04d}" not in hits[0]
    # клону протокола совет «нужна CORRECTION» без оговорки был бы ложным
    assert ("клон протокола" in hits[0]) is holds_canon, hits[0]
