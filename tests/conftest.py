"""Общие фикстуры тестов: копия кита (канон) и отдельный экземпляр-проект.

Свежий git init и локальный bare-remote вместо GitHub — реальный репозиторий
и сеть не трогаются.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
KIT_DIRS = ("docs", "agents", "skills", "templates", "tools", "mcp_server", "adr")
KIT_FILES = ("istomahandoff.md", "README.md", ".mcp.json.example")
LOG = "docs/10_DECISION_LOG.md"
STATE = "docs/09_ACTIVE_STATE.md"

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
# Журнал экземпляра: та же схема, собственная запись DEC-0001.
INSTANCE_LOG = LOG_FIXTURE.replace("decision: исходная запись",
                                   "decision: исходная запись проекта")

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


def copy_kit(dest, fixture_log=False):
    """Копия кита. fixture_log — заменить журнал кита минимальным (для lint
    кита); иначе в копии остаются реальные записи кита DEC-0001…"""
    for d in KIT_DIRS:
        shutil.copytree(REPO / d, dest / d,
                        ignore=shutil.ignore_patterns("__pycache__"))
    for f in KIT_FILES:
        shutil.copy2(REPO / f, dest / f)
    # LF, как на CI: результат не зависит от core.autocrlf машины
    for p in dest.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".yaml", ".py"):
            p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))
    if fixture_log:
        (dest / LOG).write_text(LOG_FIXTURE, encoding="utf-8", newline="\n")


def commit_all(root, message="base"):
    """git-репозиторий из каталога: init, identity теста, один коммит."""
    git(root.parent, "init", "-q", "-b", "master", str(root))
    configure(root)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)


def make_instance(dest, kit):
    """Экземпляр без файлов кита: docs/09 и docs/11 из шаблонов кита, журнал
    с одной собственной записью (не равной записи журнала кита — иначе это
    импорт), evidence/ и пара файлов проекта."""
    (dest / "docs").mkdir(parents=True)
    for rel in (STATE, "docs/11_HANDOFF_MEMO.md"):
        shutil.copy2(kit / rel, dest / rel)
    (dest / LOG).write_text(INSTANCE_LOG, encoding="utf-8", newline="\n")
    (dest / "evidence").mkdir()
    (dest / "evidence" / ".gitkeep").write_bytes(b"")
    (dest / "src").mkdir()
    (dest / "src" / "app.py").write_text("x = 1\n", encoding="utf-8", newline="\n")
    (dest / "notes").mkdir()
    (dest / "notes" / "ADR.md").write_text("# ADR\n", encoding="utf-8", newline="\n")


def link_dir(link, target):
    """Каталог-ссылка: junction на Windows (без прав администратора), symlink
    на Linux."""
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(target, link, target_is_directory=True)


def tree_digest(root):
    """Байты всех файлов каталога, включая .git, — для проверки «канон не
    изменён» (кэш байткода не в счёт)."""
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def write_hook(git_dir, name, body):
    hook = Path(git_dir) / "hooks" / name
    hook.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8", newline="\n")
    os.chmod(hook, 0o755)
    return hook


@pytest.fixture
def kit(tmp_path):
    """Установленный кит: отдельный git-клон (запись сверяет его ревизию)."""
    root = tmp_path / "kit"
    copy_kit(root)
    commit_all(root, "kit")
    return root


@pytest.fixture
def repo(tmp_path, kit):
    """Экземпляр-проект: отдельный git-репозиторий без файлов кита."""
    root = tmp_path / "repo"
    make_instance(root, kit)
    commit_all(root)
    return root


@pytest.fixture
def remote(repo, tmp_path):
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "master", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "-u", "origin", "master")
    return bare
