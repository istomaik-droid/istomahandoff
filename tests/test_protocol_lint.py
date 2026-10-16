"""Тесты protocol_lint: инварианты журнала решений docs/10 (DEC-0017).

Lint запускается из копии канона (conftest.copy_canon), поэтому проверяется
код из рабочего дерева, а журнал реального репозитория не трогается.
"""
import re
import subprocess
import sys

import pytest

from conftest import LOG, copy_canon

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
    copy_canon(root)
    return root


def lint(root):
    proc = subprocess.run(
        [sys.executable, str(root / "tools" / "protocol_lint.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL,
    )
    return proc.returncode, proc.stdout


def run_lint(root, *entries, after_block=""):
    """Дописать записи в конец блока «## Записи» (и текст после него), запустить lint."""
    log = root / LOG
    text = log.read_text(encoding="utf-8")
    m = re.search(r"(?ms)^## Записи\s*\n+```yaml\n(.*?)^```\n", text)
    text = (text[:m.end(1)] + "".join(entries) + text[m.end(1):m.end()]
            + after_block + text[m.end():])
    log.write_text(text, encoding="utf-8", newline="\n")
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
