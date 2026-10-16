"""Тесты MCP-сервера протокола: запись решений и git-tools (DEC-0016).

Каждый тест работает на копии канона во временном каталоге: свежий git init
и локальный bare-remote вместо GitHub. Реальный репозиторий и сеть не трогаются.
"""
import asyncio
import importlib.util
import itertools
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SERVER_PY = REPO / "mcp_server" / "server.py"
CANON_DIRS = ("docs", "agents", "skills", "templates", "tools")
LOG = "docs/10_DECISION_LOG.md"
SHA = "0" * 63 + "1"
DEPUTY = {"owner": "Заместитель", "mandateRef": "MANDATE-0001"}
# невидимые символы — через chr(), чтобы их было видно в исходнике и диффе
LS, PS, NEL, FS, VT, RLO, ZWSP = (chr(c) for c in (
    0x2028, 0x2029, 0x85, 0x1C, 0x0B, 0x202E, 0x200B))
_module_ids = itertools.count()

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


def copy_canon(dest):
    for d in CANON_DIRS:
        shutil.copytree(REPO / d, dest / d,
                        ignore=shutil.ignore_patterns("__pycache__"))
    # LF, как на CI: результат не зависит от core.autocrlf машины
    for p in dest.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".yaml", ".py"):
            p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))
    (dest / LOG).write_text(LOG_FIXTURE, encoding="utf-8", newline="\n")


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


@pytest.fixture
def load_server(monkeypatch):
    def _load(root, autosync=False):
        monkeypatch.setenv("ISTOMAHANDOFF_ROOT", str(root))
        if autosync:
            monkeypatch.setenv("ISTOMAHANDOFF_AUTOSYNC", "1")
        else:
            monkeypatch.delenv("ISTOMAHANDOFF_AUTOSYNC", raising=False)
        spec = importlib.util.spec_from_file_location(
            f"server_under_test_{next(_module_ids)}", SERVER_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # сервер обязан работать в копии, а не в реальном репозитории
        assert mod.ROOT.resolve() == Path(root).resolve()
        return mod
    return _load


def write_hook(git_dir, name, body):
    hook = Path(git_dir) / "hooks" / name
    hook.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8", newline="\n")
    os.chmod(hook, 0o755)
    return hook


def decide(srv, **overrides):
    args = dict(type="IMPLEMENTATION", decision="тестовое решение",
                scope="tests/", allowed=["a"], forbidden=["b"])
    args.update(overrides)
    return srv.record_decision(**args)


def log_bytes(root):
    return (root / LOG).read_bytes()


def dec_ids(root):
    return re.findall(r"(?m)^- id: (DEC-\d{4})", (root / LOG).read_text(encoding="utf-8"))


# --- валидация полей -------------------------------------------------------

@pytest.mark.parametrize("bad, good", [
    ({"decision": "текст\n- id: DEC-0999\n  type: RELEASE"}, {}),
    ({"decision": "текст\r- id: DEC-0999\r  type: RELEASE"}, {}),
    ({"decision": "текст" + LS + "  type: RELEASE"}, {}),
    ({"decision": "текст" + NEL + "- id: DEC-0999"}, {}),
    ({"decision": "текст" + FS + "- id: DEC-0999"}, {}),
    ({"decision": "текст" + VT + "- id: DEC-0999"}, {}),
    ({"decision": "разрешаю" + RLO + "ьсечерпаз"}, {}),
    ({"scope": "tests/\r\n- id: DEC-0999"}, {}),
    ({"expiresAt": "2099-12-31T00:00:00\n- id: DEC-0999\n  type: RELEASE"}, {}),
    ({"type": "ACCEPTANCE", "evidenceReadHash": SHA + "\n"},
     {"type": "ACCEPTANCE", "evidenceReadHash": SHA}),
    ({**DEPUTY, "owner": "Заместитель\n  type: RELEASE"}, DEPUTY),
    ({**DEPUTY, "mandateRef": "MANDATE-0001\n  type: RELEASE"}, DEPUTY),
])
def test_rejects_line_breaks_and_invisible_controls(repo, load_server, bad, good):
    srv = load_server(repo)
    before = log_bytes(repo)
    with pytest.raises(ValueError):
        decide(srv, **bad)
    assert log_bytes(repo) == before
    decide(srv, **good)  # контроль: то же решение без опасного символа
    assert dec_ids(repo) == ["DEC-0001", "DEC-0002"]


@pytest.mark.parametrize("bad", [
    {"allowed": ["ok", "x\n- id: DEC-0999"]},
    {"forbidden": ["x" + PS + "y"]},
    {"forbidden": ["  "]},
    {"forbidden": [ZWSP]},
    {"allowed": []},
    {"forbidden": []},
    {"scope": " "},
    {"scope": "null"},
    {"scope": "[]"},
    {"decision": ""},
    {"decision": "   "},
    {"decision": "null"},
    {**DEPUTY, "owner": "null"},
    {"owner": "Заместитель", "mandateRef": "  "},
    {"owner": "Заместитель", "mandateRef": "нет"},
])
def test_rejects_values_that_are_empty_or_malformed(repo, load_server, bad):
    srv = load_server(repo)
    before = log_bytes(repo)
    with pytest.raises(ValueError):
        decide(srv, **bad)
    assert log_bytes(repo) == before


@pytest.mark.parametrize("type_", ["ACCEPTANCE", "RELEASE"])
def test_acceptance_and_release_require_evidence_hash(repo, load_server, type_):
    srv = load_server(repo)
    before = log_bytes(repo)
    with pytest.raises(ValueError):
        decide(srv, type=type_)
    assert log_bytes(repo) == before


@pytest.mark.parametrize("bad_hash", ["прочитал", "abc", "x" + SHA, SHA + "0"])
def test_evidence_read_hash_must_be_sha256(repo, load_server, bad_hash):
    srv = load_server(repo)
    with pytest.raises(ValueError):
        decide(srv, type="ACCEPTANCE", evidenceReadHash=bad_hash)
    decide(srv, type="ACCEPTANCE", evidenceReadHash=SHA)
    assert dec_ids(repo) == ["DEC-0001", "DEC-0002"]


@pytest.mark.parametrize("bad_date", [
    "завтра", "2026-1-5", "2020-01-01T00:00:00 (продлено до 2099-12-31)",
    "2026-12-31 10:00",
])
def test_expires_at_must_be_strict_iso(repo, load_server, bad_date):
    srv = load_server(repo)
    with pytest.raises(ValueError):
        decide(srv, expiresAt=bad_date)
    decide(srv, expiresAt="2099-12-31T10:00:00+03:00")
    assert srv.list_expired(within_days=36500)["expiring"][0]["id"] == "DEC-0002"


def test_deputy_decision_requires_mandate_ref(repo, load_server):
    srv = load_server(repo)
    with pytest.raises(ValueError):
        decide(srv, owner="Заместитель")
    decide(srv, **DEPUTY)
    assert dec_ids(repo) == ["DEC-0001", "DEC-0002"]


# --- авто-синхронизация журнала --------------------------------------------

def test_autosync_is_off_by_default(repo, remote, load_server):
    srv = load_server(repo)
    head = git(repo, "rev-parse", "HEAD")
    res = decide(srv)
    assert res["id"] == "DEC-0002"
    assert res["git"]["committed"] is False
    assert res["git"]["pushed"] is False
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(remote, "rev-parse", "master") == head
    assert dec_ids(repo) == ["DEC-0001", "DEC-0002"]
    assert res.get("repo") and Path(res["repo"]).resolve() == repo.resolve()


@pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
def test_autosync_stays_off_for_falsy_values(repo, remote, monkeypatch, load_server, value):
    srv = load_server(repo)
    monkeypatch.setenv("ISTOMAHANDOFF_AUTOSYNC", value)
    head = git(repo, "rev-parse", "HEAD")
    assert decide(srv)["git"]["committed"] is False
    assert git(repo, "rev-parse", "HEAD") == head


def test_autosync_commits_and_pushes_only_the_decision(repo, remote, load_server):
    srv = load_server(repo, autosync=True)
    head = git(repo, "rev-parse", "HEAD")
    res = decide(srv)
    assert res["git"]["committed"] is True
    assert res["git"]["pushed"] is True
    new_head = git(repo, "rev-parse", "HEAD")
    assert git(repo, "rev-parse", "HEAD~1") == head
    assert git(repo, "diff", "--name-only", "HEAD~1", "HEAD") == LOG
    assert git(remote, "rev-parse", "master") == new_head


def test_autosync_leaves_other_changes_out_of_the_commit(repo, remote, load_server):
    with (repo / "docs/09_ACTIVE_STATE.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write("незакоммиченная правка\n")
    (repo / "draft.md").write_text("черновик\n", encoding="utf-8")
    git(repo, "add", "draft.md")
    srv = load_server(repo, autosync=True)
    res = decide(srv)
    assert res["git"]["pushed"] is True
    assert git(repo, "show", "--name-only", "--format=", "HEAD") == LOG
    assert git(remote, "ls-tree", "-r", "--name-only", "master", "draft.md") == ""
    status = git(repo, "status", "--porcelain").splitlines()
    assert "A  draft.md" in status and " M docs/09_ACTIVE_STATE.md" in status


def test_autosync_does_not_push_a_commit_that_a_hook_widened(repo, remote, load_server):
    write_hook(repo / ".git", "pre-commit", "git add -A")
    (repo / "draft.md").write_text("черновик, не для публикации\n", encoding="utf-8")
    remote_head = git(remote, "rev-parse", "master")
    srv = load_server(repo, autosync=True)
    res = decide(srv)
    assert res["git"]["committed"] is True
    assert res["git"]["pushed"] is False
    assert res["git"].get("reason") == "COMMIT_NOT_ONLY_LOG"
    assert git(remote, "rev-parse", "master") == remote_head


def test_autosync_does_not_publish_other_unpushed_commits(repo, remote, load_server):
    (repo / "draft.md").write_text("черновик, не для публикации\n", encoding="utf-8")
    git(repo, "add", "draft.md")
    git(repo, "commit", "-q", "-m", "WIP: черновик")
    remote_head = git(remote, "rev-parse", "master")
    srv = load_server(repo, autosync=True)
    res = decide(srv)
    assert res["git"]["committed"] is True
    assert res["git"]["pushed"] is False
    assert res["git"].get("reason") == "EXTRA_COMMITS"
    assert git(remote, "rev-parse", "master") == remote_head


def test_autosync_publishes_own_pending_decisions_after_a_failed_push(repo, remote, load_server):
    hook = write_hook(remote, "pre-receive", "exit 1")
    srv = load_server(repo, autosync=True)
    first = decide(srv)
    assert first["git"]["pushed"] is False
    assert first["git"].get("reason") == "PUSH_FAILED"
    hook.unlink()
    second = decide(srv)
    assert second["git"]["pushed"] is True
    assert git(remote, "rev-parse", "master") == git(repo, "rev-parse", "HEAD")
    assert git(remote, "rev-list", "--count", "master") == "3"  # base + 2 решения


def test_autosync_without_upstream_commits_locally(repo, load_server):
    srv = load_server(repo, autosync=True)
    res = decide(srv)
    assert res["git"]["committed"] is True
    assert res["git"]["pushed"] is False
    assert res["git"].get("reason") == "NO_UPSTREAM"
    assert git(repo, "status", "--porcelain") == ""


def test_autosync_refuses_on_detached_head(repo, remote, load_server):
    git(repo, "checkout", "-q", "--detach")
    before = log_bytes(repo)
    head = git(repo, "rev-parse", "HEAD")
    srv = load_server(repo, autosync=True)
    with pytest.raises(ValueError):
        decide(srv)
    assert log_bytes(repo) == before
    assert git(repo, "rev-parse", "HEAD") == head


def test_autosync_refuses_when_log_has_uncommitted_changes(repo, remote, load_server):
    with (repo / LOG).open("a", encoding="utf-8", newline="\n") as f:
        f.write("чужая незакоммиченная строка\n")
    dirty = log_bytes(repo)
    head = git(repo, "rev-parse", "HEAD")
    srv = load_server(repo, autosync=True)
    with pytest.raises(ValueError):
        decide(srv)
    assert log_bytes(repo) == dirty
    assert git(repo, "rev-parse", "HEAD") == head
    git(repo, "checkout", "--", LOG)
    assert decide(srv)["git"]["committed"] is True  # контроль


def test_autosync_refuses_when_clone_is_behind_upstream(repo, remote, tmp_path, load_server):
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(remote), str(other))
    configure(other)
    (other / "news.md").write_text("чужой коммит\n", encoding="utf-8")
    git(other, "add", "news.md")
    git(other, "commit", "-q", "-m", "чужой коммит")
    git(other, "push", "-q", "origin", "master")
    before = log_bytes(repo)
    head = git(repo, "rev-parse", "HEAD")
    srv = load_server(repo, autosync=True)
    with pytest.raises(ValueError):
        decide(srv)
    assert log_bytes(repo) == before
    assert git(repo, "rev-parse", "HEAD") == head
    git(repo, "pull", "-q", "--ff-only")
    assert decide(srv)["git"]["pushed"] is True  # контроль


def test_autosync_commit_failure_rolls_back_the_entry(repo, remote, tmp_path, monkeypatch, load_server):
    empty = tmp_path / "empty.gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("EMAIL", raising=False)
    git(repo, "config", "--unset", "user.name")
    git(repo, "config", "--unset", "user.email")
    git(repo, "config", "user.useConfigOnly", "true")
    before = log_bytes(repo)
    srv = load_server(repo, autosync=True)
    with pytest.raises(ValueError):
        decide(srv)
    assert log_bytes(repo) == before
    assert git(repo, "status", "--porcelain") == ""


def test_autosync_without_reachable_remote_keeps_local_commit(repo, remote, tmp_path, load_server):
    shutil.move(str(remote), str(tmp_path / "gone.git"))
    srv = load_server(repo, autosync=True)
    res = decide(srv)
    assert res["git"]["committed"] is True
    assert res["git"]["pushed"] is False
    assert res["git"].get("reason") == "FETCH_FAILED"
    assert dec_ids(repo) == ["DEC-0001", "DEC-0002"]
    assert git(repo, "status", "--porcelain") == ""


# --- git-окружение ------------------------------------------------------------

def test_git_timeout_is_reported_as_code_124(repo, load_server):
    srv = load_server(repo)
    proc = srv._git(["-c", "alias.slow=!sleep 3", "slow"], timeout=1)
    assert proc.returncode == 124


def test_missing_git_does_not_break_a_recorded_decision(repo, monkeypatch, load_server):
    srv = load_server(repo)
    monkeypatch.setenv("PATH", "")
    res = decide(srv)
    assert dec_ids(repo) == ["DEC-0001", "DEC-0002"]
    assert res["git"]["committed"] is False


# --- поверхность MCP --------------------------------------------------------

def test_mutating_tools_require_human_confirmation(repo, load_server):
    srv = load_server(repo)
    meta = {t.name: (t.meta or {}) for t in asyncio.run(srv.mcp.list_tools())}
    flag = "anthropic/requiresUserInteraction"
    assert meta["record_decision"].get(flag) is True
    assert meta["checkpoint_create"].get(flag) is True
    assert flag not in meta["protocol_version"]
    assert flag not in meta["pre_deploy_check"]


def test_git_tools_report_the_repository_they_checked(repo, load_server):
    srv = load_server(repo)
    head = git(repo, "rev-parse", "HEAD")
    res = srv.pre_deploy_check()
    assert res.get("repo") and Path(res["repo"]).resolve() == repo.resolve()
    assert res.get("head") == head
    cp = srv.checkpoint_create("t")
    assert cp.get("repo") and Path(cp["repo"]).resolve() == repo.resolve()
    assert cp["sha"] == head


def test_repo_field_names_the_enclosing_repository(tmp_path, load_server):
    outer = tmp_path / "outer"
    copy_canon(outer / "canon")
    git(tmp_path, "init", "-q", "-b", "master", str(outer))
    configure(outer)
    git(outer, "add", "-A")
    git(outer, "commit", "-q", "-m", "base")
    srv = load_server(outer / "canon")
    assert Path(srv.pre_deploy_check()["repo"]).resolve() == outer.resolve()


def test_head_is_none_in_a_repository_without_commits(tmp_path, load_server):
    root = tmp_path / "fresh"
    copy_canon(root)
    git(tmp_path, "init", "-q", "-b", "master", str(root))
    srv = load_server(root)
    assert srv.pre_deploy_check()["head"] is None
