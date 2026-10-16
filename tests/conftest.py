"""Общие фикстуры тестов: копии канона во временных каталогах.

Свежий git init и локальный bare-remote вместо GitHub — реальный репозиторий
и сеть не трогаются.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
CANON_DIRS = ("docs", "agents", "skills", "templates", "tools")
LOG = "docs/10_DECISION_LOG.md"

# Минимальный журнал: схема с enum типов, одна запись, раздел правил.
LOG_FIXTURE = """# 10. Decision log

Append-only.

```yaml
- id: DEC-XXXX
  date: <ISO8601>
  owner: <NAME>            # или deputy с mandateRef
  type: BOUNDARY | IMPLEMENTATION | ACCEPTANCE | BACKUP | RELEASE | STOP | PAUSE | CORRECTION | MIGRATION | MANDATE
  scope: <STAGE / WORKITEM>
  decision: <текст>
  allowed: []
  forbidden: []
  expiresAt: <ISO8601 | null>
  receiptSha256: <sha256>
  evidenceReadHash: <sha256 | null>   # ОБЯЗАТЕЛЕН для ACCEPTANCE/RELEASE
  mandateRef: <MANDATE-XXXX | null>   # обязателен для deputy
```

## Записи

```yaml
- id: DEC-0001
  date: 2026-09-19
  owner: OWNER
  type: CORRECTION
  scope: docs/
  decision: исходная запись
  allowed:
    - a
  forbidden:
    - b
  expiresAt: null
  receiptSha256: null
  evidenceReadHash: null
  mandateRef: null
```

## Правила

1. Каждое решение имеет ID.
"""

_GIT_ENV = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_PREFIX",
            "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
            "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE")


@pytest.fixture(autouse=True)
def isolate_git_env(monkeypatch):
    """Запуск pytest из git-хука наследует GIT_INDEX_FILE и т.п. внешнего
    репозитория — тесты не должны писать в его индекс."""
    for var in _GIT_ENV:
        monkeypatch.delenv(var, raising=False)


def git(cwd, *args, check=True):
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
    )
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {proc.stderr}")
    return proc.stdout.rstrip()  # не strip(): ведущий пробел значим в status


def configure(repo):
    git(repo, "config", "user.name", "test")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "core.autocrlf", "false")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "tag.gpgSign", "false")


def copy_canon(dest):
    for d in CANON_DIRS:
        shutil.copytree(REPO / d, dest / d,
                        ignore=shutil.ignore_patterns("__pycache__"))
    # LF, как на CI: результат не зависит от core.autocrlf машины
    for p in dest.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".yaml", ".py"):
            p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))
    (dest / LOG).write_text(LOG_FIXTURE, encoding="utf-8", newline="\n")


def write_hook(git_dir, name, body):
    hook = Path(git_dir) / "hooks" / name
    hook.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8", newline="\n")
    os.chmod(hook, 0o755)
    return hook


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    copy_canon(root)
    git(tmp_path, "init", "-q", "-b", "master", str(root))
    configure(root)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


@pytest.fixture
def remote(repo, tmp_path):
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "master", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "-u", "origin", "master")
    return bare
