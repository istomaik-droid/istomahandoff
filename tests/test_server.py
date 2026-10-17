"""Тесты MCP-сервера протокола: запись решений и git-tools (DEC-0016, DEC-0017).

Фикстуры копий канона и локального bare-remote — в conftest.py.
"""
import asyncio
import importlib.util
import itertools
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import (LOG, commit_all, configure, copy_kit, git, link_dir,
                      make_instance, tree_digest, write_hook)

SHA = "0" * 63 + "1"
DEPUTY = {"owner": "Заместитель", "mandateRef": "MANDATE-0001"}
# невидимые символы — через chr(), чтобы их было видно в исходнике и диффе
LS, PS, NEL, FS, VT, RLO, ZWSP = (chr(c) for c in (
    0x2028, 0x2029, 0x85, 0x1C, 0x0B, 0x202E, 0x200B))
_module_ids = itertools.count()

_ENV = ("ISTOMAHANDOFF_ROOT", "ISTOMAHANDOFF_PROJECT", "CLAUDE_PROJECT_DIR",
        "ISTOMAHANDOFF_AUTOSYNC", "MCP_TRANSPORT")


def import_server(kit):
    spec = importlib.util.spec_from_file_location(
        f"server_under_test_{next(_module_ids)}", kit / "mcp_server" / "server.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def load_server(monkeypatch, kit):
    """Сервер из копии кита; root — ISTOMAHANDOFF_PROJECT (None — не задан).
    Окружение очищается: pytest из Claude Code наследует CLAUDE_PROJECT_DIR."""
    def _load(root, autosync=False, claude_dir=None, transport=None, kit=kit):
        for var in _ENV:
            monkeypatch.delenv(var, raising=False)
        if root is not None:
            monkeypatch.setenv("ISTOMAHANDOFF_PROJECT", str(root))
        if claude_dir is not None:
            monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude_dir))
        if autosync:
            monkeypatch.setenv("ISTOMAHANDOFF_AUTOSYNC", "1")
        if transport is not None:
            monkeypatch.setenv("MCP_TRANSPORT", transport)
        mod = import_server(kit)
        # канон — копия кита, проект — копия экземпляра, не реальные клоны
        assert mod.CANON == kit.resolve()
        return mod
    return _load


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


def test_missing_git_refuses_the_write(repo, monkeypatch, load_server):
    srv = load_server(repo)
    monkeypatch.setenv("PATH", "")
    before = log_bytes(repo)
    # без git ревизию кита не проверить — запись закрыта (fail-closed)
    with pytest.raises(ValueError, match="git"):
        decide(srv)
    assert log_bytes(repo) == before


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


def test_repo_field_names_the_enclosing_repository(tmp_path, kit, load_server):
    outer = tmp_path / "outer"
    make_instance(outer / "proj", kit)
    commit_all(outer)
    srv = load_server(outer / "proj")
    assert Path(srv.pre_deploy_check()["repo"]).resolve() == outer.resolve()


def test_head_is_none_in_a_repository_without_commits(tmp_path, kit, load_server):
    root = tmp_path / "fresh"
    make_instance(root, kit)
    git(tmp_path, "init", "-q", "-b", "master", str(root))
    srv = load_server(root)
    assert srv.pre_deploy_check()["head"] is None


# --- честные гейты (DEC-0017) ----------------------------------------------

def test_pre_deploy_check_recognizes_own_cyrillic_and_spaced_files(repo, load_server):
    (repo / "ЖУРНАЛ_СЕССИИ_2026-10-16.md").write_text("журнал\n", encoding="utf-8")
    (repo / "my notes.md").write_text("заметки\n", encoding="utf-8")
    srv = load_server(repo)
    res = srv.pre_deploy_check(own_files=["ЖУРНАЛ_СЕССИИ_2026-10-16.md", "my notes.md"])
    assert res["verdict"] == "DIRTY_OWN"
    assert sorted(res["changed"]) == ["my notes.md", "ЖУРНАЛ_СЕССИИ_2026-10-16.md"]


def test_pre_deploy_check_sees_files_inside_new_directories(repo, load_server):
    (repo / "newmod").mkdir()
    (repo / "newmod" / "own.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "newmod" / "foreign.py").write_text("y = 2\n", encoding="utf-8")
    srv = load_server(repo)
    res = srv.pre_deploy_check(own_files=["newmod/own.py"])
    assert res["verdict"] == "DIRTY_FOREIGN"
    assert res["foreign"] == ["newmod/foreign.py"]
    # каталог в own_files не прячет чужой файл внутри
    assert srv.pre_deploy_check(own_files=["newmod/"])["verdict"] == "DIRTY_FOREIGN"


def test_pre_deploy_check_counts_both_sides_of_a_rename(repo, load_server):
    git(repo, "mv", "notes/ADR.md", "notes/ADR_v2.md")
    srv = load_server(repo)
    both = srv.pre_deploy_check(own_files=["notes/ADR.md", "notes/ADR_v2.md"])
    assert both["verdict"] == "DIRTY_OWN"
    new_only = srv.pre_deploy_check(own_files=["notes/ADR_v2.md"])
    assert new_only["verdict"] == "DIRTY_FOREIGN"
    assert new_only["foreign"] == ["notes/ADR.md"]


def test_pre_deploy_check_normalizes_own_paths(repo, load_server):
    with (repo / "src/app.py").open("a", encoding="utf-8", newline="\n") as f:
        f.write("y = 2\n")
    srv = load_server(repo)
    for own in ("src" + chr(92) + "app.py", "./src/app.py", str(repo / "src" / "app.py")):
        assert srv.pre_deploy_check(own_files=[own])["verdict"] == "DIRTY_OWN", own


def test_pre_deploy_check_keeps_short_names_and_dot_prefixes(repo, load_server):
    (repo / "x").write_text("x\n", encoding="utf-8")
    srv = load_server(repo)
    assert srv.pre_deploy_check()["verdict"] == "DIRTY_FOREIGN"  # не CLEAN
    assert srv.pre_deploy_check(["././x"])["verdict"] == "DIRTY_OWN"


def test_pre_deploy_check_does_not_repeat_paths(repo, load_server):
    git(repo, "mv", "notes/ADR.md", "notes/ADR_v2.md")
    (repo / "notes" / "ADR.md").write_text("снова\n", encoding="utf-8")
    changed = load_server(repo).pre_deploy_check()["changed"]
    assert len(changed) == len(set(changed))


def test_own_files_are_relative_to_the_repository_root(tmp_path, kit, load_server):
    outer = tmp_path / "outer"
    make_instance(outer / "proj", kit)
    commit_all(outer)
    target = outer / "proj" / "src" / "app.py"
    with target.open("a", encoding="utf-8", newline="\n") as f:
        f.write("y = 2\n")
    srv = load_server(outer / "proj")
    assert srv.pre_deploy_check(["proj/src/app.py"])["verdict"] == "DIRTY_OWN"
    assert srv.pre_deploy_check([str(target)])["verdict"] == "DIRTY_OWN"
    assert srv.pre_deploy_check(["src/app.py"])["verdict"] == "DIRTY_FOREIGN"


def test_gate_lists_are_capped_but_counted(repo, load_server):
    (repo / "build").mkdir()
    for i in range(250):
        (repo / "build" / f"f{i:03d}.txt").write_text("x\n", encoding="utf-8")
    srv = load_server(repo)
    res = srv.pre_deploy_check()
    assert res["verdict"] == "DIRTY_FOREIGN"
    assert res.get("changedCount") == 250 and res.get("foreignCount") == 250
    assert len(res["changed"]) < 250 and res.get("truncated") is True
    cp = srv.checkpoint_create("big")
    assert cp.get("untrackedCount") == 250 and len(cp["untracked"]) < 250


@pytest.mark.parametrize("change", ["unstaged", "staged", "new_staged", "removed"])
def test_checkpoint_refuses_any_tracked_change(repo, load_server, change):
    path = repo / "src/app.py"
    if change in ("unstaged", "staged"):
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write("y = 2\n")
        if change == "staged":
            git(repo, "add", "src/app.py")
    elif change == "new_staged":
        (repo / "new.md").write_text("новый\n", encoding="utf-8")
        git(repo, "add", "new.md")
    else:
        git(repo, "rm", "-q", "src/app.py")
    srv = load_server(repo)
    with pytest.raises(ValueError):
        srv.checkpoint_create("pre-change")
    assert git(repo, "tag", "--list", "checkpoint/*") == ""


def test_checkpoint_after_boundary_needs_the_decision_committed(repo, load_server):
    srv = load_server(repo)
    decide(srv, type="BOUNDARY")  # запись осталась в рабочем дереве
    with pytest.raises(ValueError):
        srv.checkpoint_create("pre-change")
    git(repo, "commit", "-q", "-m", "BOUNDARY", "--", LOG)
    assert srv.checkpoint_create("pre-change")["verified"] is True


def test_checkpoint_without_git_identity_refuses_clearly(repo, tmp_path, monkeypatch, load_server):
    empty = tmp_path / "empty.gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("EMAIL", raising=False)
    git(repo, "config", "--unset", "user.name")
    git(repo, "config", "--unset", "user.email")
    git(repo, "config", "user.useConfigOnly", "true")
    srv = load_server(repo)
    # совет — задать identity в этом репозитории, а не трогать глобальный конфиг
    with pytest.raises(ValueError, match="глобальный"):
        srv.checkpoint_create("pre-change")
    assert git(repo, "tag", "--list", "checkpoint/*") == ""


def test_checkpoint_readback_mismatch_is_not_verified(repo, monkeypatch, load_server):
    srv = load_server(repo)
    real = srv._git

    def fake(args, timeout=None, cwd=None):
        if args[:1] == ["rev-parse"] and args[-1].endswith("^{commit}"):
            return subprocess.CompletedProcess(args, 0, "0" * 40 + "\n", "")
        return real(args, timeout, cwd)

    monkeypatch.setattr(srv, "_git", fake)
    cp = srv.checkpoint_create("t")
    assert cp["verified"] is False and "READBACK" in cp["note"]


def test_checkpoint_is_annotated_and_reports_untracked_files(repo, load_server):
    (repo / "scratch.txt").write_text("черновик\n", encoding="utf-8")
    head = git(repo, "rev-parse", "HEAD")
    srv = load_server(repo)
    cp = srv.checkpoint_create("pre-change")
    assert cp["verified"] is True
    assert cp["sha"] == head
    assert cp.get("untracked") == ["scratch.txt"]
    assert cp.get("pushed") is False
    assert git(repo, "cat-file", "-t", cp["tag"]) == "tag"
    assert git(repo, "rev-parse", cp["tag"] + "^{commit}") == head


@pytest.mark.parametrize("fr, to, verdict, kind, field, value", [
    ("INTAKE", "TRIAGE", "VALID", "chain", None, None),
    ("EVIDENCE_READY", "TECHNICAL_REVIEW_PASSED", "VALID", "chain", None, None),
    ("TECHNICAL_REVIEW_PASSED", "RESULT_OWNER_ACCEPTED", "CONDITIONAL", "chain",
     "forbiddenWhen", "без evidence"),
    ("EVIDENCE_READY", "NEXT_WORK_ITEM_LOCKED", "FORBIDDEN", None, None, None),
    ("RESULT_OWNER_ACCEPTED", "RELEASE_AUTHORIZED", "FORBIDDEN", None, None, None),
    ("INTAKE", "BUILDING", "FORBIDDEN", "skip", None, None),
    ("BUILDING", "TECHNICAL_REVIEW_PASSED", "FORBIDDEN", "skip", None, None),
    ("POST_ACCEPTANCE_CHECKPOINT_VERIFIED", "RELEASED", "FORBIDDEN", "skip", None, None),
    ("BUILDING", "STOPPED", "VALID", "emergency", None, None),
    ("BUILDING", "ROLLED_BACK", "CONDITIONAL", "emergency",
     "requiresState", "ANY_MUTATED_STATE"),
    ("EVIDENCE_READY", "INCONCLUSIVE", "CONDITIONAL", "emergency",
     "requiresState", "INSUFFICIENT_EVIDENCE"),
    ("TRIAGE", "STOPPED_PROTOCOL_MISMATCH", "CONDITIONAL", "emergency",
     "requiresState", "PROTOCOL_MISMATCH"),
    ("BUILDING", "TRIAGE", "UNKNOWN", None, None, None),
    ("BUILDNG", "ROLLED_BACK", "UNKNOWN", None, None, None),
    ("", "ROLLED_BACK", "UNKNOWN", None, None, None),
])
def test_validate_transition_follows_docs16(repo, load_server, fr, to, verdict, kind, field, value):
    res = load_server(repo).validate_transition(fr, to)
    assert res["verdict"] == verdict
    assert res.get("kind") == kind
    if field:
        assert res.get(field) == value


SYNTH16 = """# 16. State machine

```text
A
  -> B
  -> C
  -> D
```

## Недопустимые переходы

```text
A -> B # комментарий, не условие
B -> C (без ревью) # пояснение
C -> D (без проверки)
C -> D
```

## Аварийные

```text
ANY_STATE -> STOPPED
ANY_STATE -> PAUSED (только по решению владельца)
```
"""


@pytest.mark.parametrize("fr, to, verdict, field, value", [
    ("A", "B", "FORBIDDEN", None, None),  # комментарий — не условие
    ("B", "C", "CONDITIONAL", "forbiddenWhen", "без ревью"),
    ("C", "D", "FORBIDDEN", None, None),  # безусловный запрет сильнее условного
    ("D", "STOPPED", "VALID", None, None),
    ("D", "PAUSED", "CONDITIONAL", "allowedWhen", "только по решению владельца"),
])
def test_validate_transition_reads_conditions_and_comments(kit, load_server, fr, to, verdict, field, value):
    (kit / "docs" / "16_STATE_MACHINE.md").write_text(SYNTH16, encoding="utf-8", newline="\n")
    res = load_server(None).validate_transition(fr, to)
    assert res["verdict"] == verdict
    if field:
        assert res.get(field) == value


# --- два корня: канон и экземпляр (DEC-0018) --------------------------------

INSTANCE_TOOLS = {
    "record_decision": lambda s: decide(s),
    "get_active_state": lambda s: s.get_active_state(),
    "list_expired": lambda s: s.list_expired(),
    "audit_sample": lambda s: s.audit_sample(),
    "evidence_hash": lambda s: s.evidence_hash(LOG),
    "pre_deploy_check": lambda s: s.pre_deploy_check(),
    "checkpoint_create": lambda s: s.checkpoint_create("t"),
}


@pytest.mark.parametrize("name", sorted(INSTANCE_TOOLS))
def test_instance_tools_refuse_without_project(kit, load_server, name):
    before = tree_digest(kit)
    srv = load_server(None)
    with pytest.raises(ValueError, match="корень проекта не задан"):
        INSTANCE_TOOLS[name](srv)
    assert tree_digest(kit) == before


def test_canon_is_served_without_project(load_server):
    srv = load_server(None)
    assert srv.validate_transition("INTAKE", "TRIAGE")["verdict"] == "VALID"
    ver = srv.protocol_version()
    assert ver["version"] and ver["project"] is None
    assert srv.get_doc("16_STATE_MACHINE").startswith("# 16. State machine")
    assert srv.get_doc("INDEX").startswith("# INDEX")
    assert srv.get_template("HANDOFF.md").startswith("# Handoff")
    assert srv.get_main_doc().startswith("# istomahandoff")
    names = {p.name for p in asyncio.run(srv.mcp.list_prompts())}
    assert names == {"preflight", "decision", "handoff", "incident", "verify"}
    lint = srv.protocol_lint()
    assert lint["target"] == "canon" and lint["exitCode"] == 0, lint["stdout"]
    assert lint["projectError"] is None


@pytest.mark.parametrize("where", ["kit", "inside"])
def test_project_inside_the_kit_is_refused(kit, load_server, where):
    before = tree_digest(kit)
    srv = load_server(kit if where == "kit" else kit / "docs")
    assert srv.PROJECT is None
    for name in sorted(INSTANCE_TOOLS):
        with pytest.raises(ValueError, match="кит"):
            INSTANCE_TOOLS[name](srv)
    # lint кита доступен всегда (ADR-0001 п.3): проверен кит, ошибка проекта — рядом
    lint = srv.protocol_lint()
    assert lint["target"] == "canon" and "кит" in lint["projectError"]
    assert tree_digest(kit) == before


@pytest.mark.skipif(os.name != "nt", reason="префикс \\\\?\\ — только Windows")
def test_kit_aliases_do_not_bypass_the_kit_check(kit, load_server):
    alias = "\\\\?\\" + str(kit)
    before = tree_digest(kit)
    for project in (alias, alias + "\\docs"):
        srv = load_server(project)
        assert srv.PROJECT is None
        with pytest.raises(ValueError, match="кит"):
            srv.get_active_state()
    with pytest.raises(ValueError, match="кит"):
        srv._atomic_write(Path(alias) / "docs" / "ZZ.md", b"x")
    assert tree_digest(kit) == before


def test_conflicting_project_roots_are_refused(repo, tmp_path, load_server):
    other = tmp_path / "other"
    other.mkdir()
    srv = load_server(repo, claude_dir=other)
    before = log_bytes(repo)
    for name in sorted(INSTANCE_TOOLS):
        with pytest.raises(ValueError, match="разные каталоги"):
            INSTANCE_TOOLS[name](srv)
    assert log_bytes(repo) == before


def test_matching_claude_project_dir_keeps_the_explicit_key(repo, load_server):
    srv = load_server(repo, claude_dir=repo)
    assert decide(srv)["id"] == "DEC-0002"


def test_claude_project_dir_reads_but_cannot_write(repo, load_server):
    srv = load_server(None, claude_dir=repo)
    assert srv.PROJECT == repo.resolve()
    assert "activeWorkItem" in srv.get_active_state()
    assert srv.pre_deploy_check()["verdict"] == "CLEAN"
    before = log_bytes(repo)
    with pytest.raises(ValueError, match="ISTOMAHANDOFF_PROJECT"):
        decide(srv)
    with pytest.raises(ValueError, match="ISTOMAHANDOFF_PROJECT"):
        srv.checkpoint_create("t")
    assert log_bytes(repo) == before
    assert git(repo, "tag", "--list") == ""


def test_relative_project_is_refused(repo, load_server, monkeypatch):
    monkeypatch.chdir(repo.parent)
    srv = load_server(Path(repo.name))
    with pytest.raises(ValueError, match="абсолютный"):
        decide(srv)
    with pytest.raises(ValueError, match="абсолютный"):
        srv.get_active_state()


def test_missing_project_directory_is_refused(tmp_path, load_server):
    srv = load_server(tmp_path / "nope")
    with pytest.raises(ValueError, match="не найден"):
        srv.get_active_state()
    assert not (tmp_path / "nope").exists()


def test_legacy_root_variable_stops_the_server(kit, repo, monkeypatch):
    for var in _ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ISTOMAHANDOFF_ROOT", str(repo))
    with pytest.raises(RuntimeError, match="ISTOMAHANDOFF_PROJECT"):
        import_server(kit)


def test_read_only_key_does_not_send_to_instance_init(tmp_path, load_server):
    plain = tmp_path / "plain"
    plain.mkdir()
    srv = load_server(None, claude_dir=plain)
    # подсказка instance_init бесполезна: запись всё равно закрыта ключом
    with pytest.raises(ValueError, match="ISTOMAHANDOFF_PROJECT"):
        decide(srv)
    with pytest.raises(ValueError, match="ISTOMAHANDOFF_PROJECT"):
        srv.checkpoint_create("t")
    assert list(plain.iterdir()) == []


def test_start_time_project_errors_say_to_restart(tmp_path, load_server):
    late = tmp_path / "late"
    srv = load_server(late)
    late.mkdir()  # каталог появился после старта: env читается один раз
    with pytest.raises(ValueError, match="перезапуст"):
        srv.get_active_state()


def test_unreadable_project_does_not_stop_the_server(tmp_path, load_server, monkeypatch):
    real = Path.is_dir

    def is_dir(self, *args, **kwargs):
        if self.name == "locked":
            raise PermissionError(13, "Access is denied", str(self))
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "is_dir", is_dir)
    srv = load_server(tmp_path / "locked")
    with pytest.raises(ValueError, match="недоступен"):
        srv.get_active_state()
    assert srv.validate_transition("INTAKE", "TRIAGE")["verdict"] == "VALID"


def test_uninitialized_project_is_refused(tmp_path, load_server):
    plain = tmp_path / "plain"
    plain.mkdir()
    srv = load_server(plain)
    for name in sorted(INSTANCE_TOOLS):
        with pytest.raises(ValueError, match="instance_init"):
            INSTANCE_TOOLS[name](srv)
    assert list(plain.iterdir()) == []


def test_numbering_and_writes_stay_in_the_project(kit, repo, load_server):
    assert len(dec_ids(kit)) > 1  # в копии кита — реальные записи кита
    before = tree_digest(kit)
    srv = load_server(repo)
    project = repo.resolve().as_posix()
    res = decide(srv)
    assert res["id"] == "DEC-0002" and res["project"] == project
    assert Path(res["log"]).resolve() == (repo / LOG).resolve()
    git(repo, "commit", "-q", "-m", "DEC-0002", "--", LOG)
    cp = srv.checkpoint_create("t")
    assert cp["verified"] is True and cp["project"] == project
    assert srv.pre_deploy_check()["project"] == project
    # поле project — у всех tools экземпляра с ответом-словарём (ADR, «Consequences»)
    assert srv.evidence_hash(LOG)["project"] == project
    assert srv.list_expired()["project"] == project
    assert srv.audit_sample()["project"] == project
    assert srv.protocol_version()["project"] == project
    assert tree_digest(kit) == before


def test_type_enum_comes_from_the_kit_schema(kit, repo, load_server):
    log = repo / LOG
    text = log.read_text(encoding="utf-8")
    # схема в журнале проекта не читается: у экземпляра её копии может не быть
    log.write_text(text[text.index("## Записи"):], encoding="utf-8", newline="\n")
    kit_log = kit / LOG
    kit_log.write_text(kit_log.read_text(encoding="utf-8").replace(
        "| MANDATE\n", "| MANDATE | APPROVAL\n", 1), encoding="utf-8", newline="\n")
    git(kit, "commit", "-q", "-am", "новый тип в схеме кита")
    srv = load_server(repo)
    assert decide(srv, type="APPROVAL")["id"] == "DEC-0002"
    with pytest.raises(ValueError, match="docs/10 кита"):
        decide(srv, type="APPROVED")


def test_decision_log_resource_has_no_kit_records(kit, load_server):
    text = load_server(None).get_doc("10_DECISION_LOG")
    assert "- id: DEC-XXXX" in text and "## Записи" in text and "## Правила" in text
    assert not re.search(r"(?m)^- id: DEC-\d{4}", text)
    assert re.search(r"(?m)^- id: DEC-0001", (kit / LOG).read_text(encoding="utf-8"))


def test_journal_through_a_link_into_the_kit_is_refused(kit, tmp_path, load_server):
    proj = tmp_path / "linked"
    proj.mkdir()
    link_dir(proj / "docs", kit / "docs")  # docs проекта — ссылка в кит
    before = tree_digest(kit)
    srv = load_server(proj)
    # журнал кита не выдаётся за журнал проекта и не дописывается
    for name in ("record_decision", "get_active_state", "list_expired", "audit_sample"):
        with pytest.raises(ValueError, match="кит"):
            INSTANCE_TOOLS[name](srv)
    with pytest.raises(ValueError, match="кит"):
        srv._atomic_write(proj / LOG, b"x")  # последний рубеж — resolve() в _atomic_write
    assert tree_digest(kit) == before


@pytest.mark.parametrize("old, new", [
    ("protocol:\n", "protocol:   # версия и уровень\n"),
    ('  version: "<SEMVER>"', '    version: "<SEMVER>"'),
])
def test_protocol_version_reads_the_project_version_like_lint(repo, load_server, old, new):
    state = repo / "docs" / "09_ACTIVE_STATE.md"
    text = state.read_text(encoding="utf-8").replace(old, new, 1)
    srv = load_server(repo)
    version = srv.protocol_version()["version"]
    state.write_text(text.replace('"<SEMVER>"', f'"{version}"'), encoding="utf-8", newline="\n")
    assert srv.protocol_version()["projectVersion"] == version


def test_server_never_writes_into_the_kit(kit, load_server):
    srv = load_server(None)
    target = kit / "docs" / "new.md"
    with pytest.raises(ValueError, match="кит"):
        srv._atomic_write(target, b"x")
    assert not target.exists()


def test_protocol_version_compares_kit_and_project(repo, load_server):
    srv = load_server(repo)
    state = repo / "docs" / "09_ACTIVE_STATE.md"
    text = state.read_text(encoding="utf-8")
    res = srv.protocol_version()
    kit_version = res["version"]
    assert res["project"] == repo.resolve().as_posix()
    assert res["projectVersion"] is None and res["match"] is False  # шаблон
    state.write_text(text.replace('"<SEMVER>"', '"2.12"'), encoding="utf-8", newline="\n")
    res = srv.protocol_version()
    assert res["projectVersion"] == "2.12" and res["match"] is False
    assert res["versionsSince"][0] == "2.13" and res["versionsSince"][-1] == kit_version
    assert "docs/47" in res["note"]
    state.write_text(text.replace('"<SEMVER>"', f'"{kit_version}"'), encoding="utf-8",
                     newline="\n")
    res = srv.protocol_version()
    assert res["match"] is True and res["versionsSince"] == []


def test_protocol_version_reports_the_kit_revision(kit, load_server):
    srv = load_server(None)
    head = git(kit, "rev-parse", "HEAD")
    res = srv.protocol_version()
    assert (res["canonHead"], res["loadedHead"], res["canonDirty"], res["canonTag"]) == \
        (head, head, False, None)
    assert res["loadedDirty"] is False
    git(kit, "tag", "backup-before-pull")  # не релизный тег
    assert srv.protocol_version()["canonTag"] is None
    git(kit, "tag", "-a", "-m", "релиз", "kit-v9.9")
    assert srv.protocol_version()["canonTag"] == "kit-v9.9"
    with (kit / "docs" / "01_PRODUCT_BOUNDARY.md").open("a", encoding="utf-8") as f:
        f.write("правка\n")
    assert srv.protocol_version()["canonDirty"] is True
    git(kit, "commit", "-q", "-am", "новая версия кита")
    res = srv.protocol_version()
    assert res["loadedHead"] == head and res["canonHead"] not in (None, head)
    assert "перезапуст" in res["note"]


def test_protocol_version_without_a_kit_clone(tmp_path, load_server):
    plain = tmp_path / "plainkit"
    copy_kit(plain)
    res = load_server(None, kit=plain).protocol_version()
    assert res["version"]
    assert (res["canonHead"], res["loadedHead"], res["canonDirty"], res["canonTag"]) == \
        (None, None, None, None)


@pytest.mark.parametrize("path, head", [
    ("docs/16_STATE_MACHINE.md", "# 16. State machine"),
    ("docs/INDEX.md", "# INDEX"),
    ("agents/AGENT_CONTRACT.md", "#"),
    ("skills/decision/SKILL.md", "---"),
    ("templates/HANDOFF.md", "# Handoff"),
    ("templates/PROJECT_PROFILE.yaml", ""),
    ("istomahandoff.md", "# istomahandoff"),
    # ссылки AGENT_RUNTIMES должны разрешаться из экземпляра
    ("adr/ADR-0001-kit-instance.md", "# ADR-0001"),
    ("mcp_server/README.md", "# MCP-сервер"),
    (".mcp.json.example", "{"),
])
def test_read_canon_serves_whitelisted_kit_files(kit, load_server, path, head):
    text = load_server(None).read_canon(path)
    assert text == (kit / path).read_text(encoding="utf-8") and text.startswith(head)


def test_read_canon_strips_kit_records_from_the_log(kit, repo, load_server):
    srv = load_server(repo)
    text = srv.read_canon(LOG)
    assert text == srv._strip_records((kit / LOG).read_text(encoding="utf-8"))
    assert "- id: DEC-XXXX" in text and "## Правила" in text
    assert not re.search(r"(?m)^- id: DEC-\d{4}", text)


@pytest.mark.parametrize("path", [
    "../x", "docs/../../.env", "docs/10_DECISION_LOG.md/../x", "mcp_server/server.py",
    "/etc/passwd", "C:/Windows/win.ini", "docs" + chr(92) + "16_STATE_MACHINE.md",
    "docs/16_state_machine.md", "docs/99_MISSING.md", "README.md", ".git/config",
    "skills/../docs/16_STATE_MACHINE.md",
])
def test_read_canon_refuses_paths_outside_the_whitelist(load_server, path):
    with pytest.raises(ValueError):
        load_server(None).read_canon(path)


# --- instance_init (DEC-0018) ----------------------------------------------------

def run_tool(kit, tool, *args):
    proc = subprocess.run(
        [sys.executable, str(kit / "tools" / tool), *map(str, args)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        stdin=subprocess.DEVNULL)
    return proc.returncode, proc.stdout


def test_init_creates_an_instance_without_kit_records(kit, tmp_path, load_server):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".gitattributes").write_text("*.png binary", encoding="utf-8", newline="\n")
    code, out = run_tool(kit, "instance_init.py", proj)
    assert code == 0, out
    log = (proj / LOG).read_text(encoding="utf-8")
    assert "## Записи" in log and "## Правила" in log
    assert not re.search(r"(?m)^- id: DEC-\d{4}", log)
    assert (proj / "docs" / "11_HANDOFF_MEMO.md").is_file()
    assert (proj / "evidence" / ".gitkeep").is_file()
    assert (proj / "templates" / "PROJECT_PROFILE.yaml").read_bytes() == \
        (kit / "templates" / "PROJECT_PROFILE.yaml").read_bytes()
    assert (proj / ".gitattributes").read_text(encoding="utf-8") == \
        "*.png binary\nevidence/** -text\n"
    srv = load_server(proj)
    assert srv.protocol_version()["match"] is True
    code, out = run_tool(kit, "protocol_lint.py", "--project", proj)
    assert code == 0, out
    assert "protocol.version" not in out and "импорт" not in out
    assert decide(srv)["id"] == "DEC-0001"


@pytest.mark.skipif(os.name != "nt", reason="префикс \\\\?\\ — только Windows")
def test_init_refuses_a_kit_alias(kit):
    (kit / "sandbox").mkdir()
    before = tree_digest(kit)
    code, out = run_tool(kit, "instance_init.py", "\\\\?\\" + str(kit / "sandbox"))
    assert code == 1 and "кит" in out, out
    assert tree_digest(kit) == before


INIT_TARGETS = ("docs/09_ACTIVE_STATE.md", "docs/10_DECISION_LOG.md",
                "docs/11_HANDOFF_MEMO.md", "templates/PROJECT_PROFILE.yaml",
                "evidence/.gitkeep")


@pytest.mark.parametrize("existing", INIT_TARGETS)
def test_init_never_overwrites_any_target(kit, tmp_path, existing):
    proj = tmp_path / "proj"
    (proj / existing).parent.mkdir(parents=True)
    (proj / existing).write_bytes(b"own bytes of the project\n")
    before = tree_digest(proj)
    code, out = run_tool(kit, "instance_init.py", proj)
    assert code == 1 and "ничего не создано" in out, out
    assert tree_digest(proj) == before


@pytest.mark.parametrize("case", ["utf16-gitattributes", "evidence-is-a-file",
                                  "readonly-gitattributes"])
def test_init_is_all_or_nothing(kit, tmp_path, case):
    proj = tmp_path / "proj"
    proj.mkdir()
    ga = proj / ".gitattributes"
    if case == "utf16-gitattributes":
        ga.write_bytes("*.png binary\n".encode("utf-16"))  # Out-File Windows PowerShell 5.1
    elif case == "evidence-is-a-file":
        (proj / "evidence").write_text("файл, а не каталог\n", encoding="utf-8")
    else:
        ga.write_text("*.png binary\n", encoding="utf-8")
        os.chmod(ga, stat.S_IREAD)
    before = tree_digest(proj)
    try:
        code, out = run_tool(kit, "instance_init.py", proj)
    finally:
        if ga.exists():
            os.chmod(ga, stat.S_IREAD | stat.S_IWRITE)
    assert code == 1 and "ничего не создано" in out, out
    assert tree_digest(proj) == before


@pytest.mark.parametrize("fail_mode, nth", [("x", 3), ("ab", 1)])
def test_init_rolls_back_a_failed_write(kit, tmp_path, monkeypatch, fail_mode, nth):
    spec = importlib.util.spec_from_file_location(
        f"instance_init_under_test_{next(_module_ids)}", kit / "tools" / "instance_init.py")
    init = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(init)
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".gitattributes").write_bytes(b"*.png binary\n")
    before = tree_digest(proj)
    real_open, calls = Path.open, []

    def flaky(self, *args, **kwargs):  # сбой записи посреди работы (диск, антивирус)
        if args and args[0] == fail_mode:
            calls.append(self)
            if len(calls) == nth:
                raise OSError(28, "No space left on device")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", flaky)
    assert init.main([str(proj)]) == 1
    monkeypatch.undo()
    assert tree_digest(proj) == before
    assert sorted(p.name for p in proj.iterdir()) == [".gitattributes"]


def test_init_appends_the_rule_to_a_non_utf8_gitattributes(kit, tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    original = "# бинарные файлы\n*.png binary\n".encode("cp1251")
    (proj / ".gitattributes").write_bytes(original)
    code, out = run_tool(kit, "instance_init.py", proj)
    assert code == 0, out
    assert (proj / ".gitattributes").read_bytes() == original + b"evidence/** -text\n"


def test_init_keeps_a_single_evidence_rule(kit, tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / ".gitattributes").write_bytes(b"\xef\xbb\xbfevidence/** -text\n")  # с BOM
    code, out = run_tool(kit, "instance_init.py", proj)
    assert code == 0, out
    assert (proj / ".gitattributes").read_bytes().count(b"evidence/** -text") == 1


def test_init_refuses_targets_that_lead_into_the_kit(kit, tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    link_dir(proj / "evidence", kit / "agents")  # evidence/.gitkeep легла бы в кит
    before = tree_digest(kit)
    code, out = run_tool(kit, "instance_init.py", proj)
    assert code == 1 and "кит" in out, out
    assert tree_digest(kit) == before
    assert not (proj / "docs").exists()


def test_init_never_overwrites(kit, repo):
    before = tree_digest(repo)
    code, out = run_tool(kit, "instance_init.py", repo)
    assert code == 1 and "ничего не создано" in out
    assert tree_digest(repo) == before


@pytest.mark.parametrize("target, why", [
    ("kit", "кит"), ("inside", "кит"), ("relative", "абсолютн"), ("missing", "не найден")])
def test_init_refuses_bad_targets(kit, tmp_path, monkeypatch, target, why):
    monkeypatch.chdir(tmp_path)
    arg = {"kit": kit, "inside": kit / "docs", "relative": "proj",
           "missing": tmp_path / "nope"}[target]
    (tmp_path / "proj").mkdir()
    before = tree_digest(kit)
    code, out = run_tool(kit, "instance_init.py", arg)
    assert code in (1, 2) and why in out, out
    assert tree_digest(kit) == before
    assert list((tmp_path / "proj").iterdir()) == []
    assert not (tmp_path / "nope").exists()


# --- охрана записи (DEC-0018) ---------------------------------------------------

def test_no_writes_into_a_project_holding_canon(kit, repo, load_server):
    shutil.copy2(kit / "istomahandoff.md", repo / "istomahandoff.md")
    shutil.copy2(kit / "docs" / "16_STATE_MACHINE.md", repo / "docs" / "16_STATE_MACHINE.md")
    srv = load_server(repo)
    before = log_bytes(repo)
    with pytest.raises(ValueError, match="канон"):
        decide(srv)
    with pytest.raises(ValueError, match="канон"):
        srv.checkpoint_create("t")
    assert log_bytes(repo) == before
    assert git(repo, "tag", "--list") == ""
    assert "activeWorkItem" in srv.get_active_state()  # чтение работает
    assert srv.pre_deploy_check()["verdict"] == "DIRTY_FOREIGN"


def test_no_writes_into_an_instance_nested_in_a_protocol_clone(kit, tmp_path, load_server):
    clone = tmp_path / "clone"
    copy_kit(clone)
    make_instance(clone / "examples" / "demo", kit)
    commit_all(clone)
    srv = load_server(clone / "examples" / "demo")
    # тег и коммит ушли бы в репозиторий клона протокола — в обход pull request
    with pytest.raises(ValueError, match="канон"):
        decide(srv)
    with pytest.raises(ValueError, match="канон"):
        srv.checkpoint_create("t")
    assert git(clone, "tag", "--list") == ""


def test_kit_dirty_at_start_refuses_writes(kit, repo, load_server):
    target = kit / "mcp_server" / "server.py"
    original = target.read_bytes()
    target.write_bytes(original + b"\nMARKER = 1\n")
    srv = load_server(repo)
    target.write_bytes(original)  # кит снова чист, но загружен код не из HEAD
    assert srv.MARKER == 1
    with pytest.raises(ValueError, match="при старте"):
        decide(srv)
    assert srv.protocol_version()["loadedDirty"] is True


def test_kit_check_failure_at_start_says_to_restart(repo, load_server, monkeypatch):
    import mcp.server.fastmcp  # noqa: F401 — до PATH="", импорт SDK не зависит от PATH
    path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", "")
    srv = load_server(repo)
    monkeypatch.setenv("PATH", path)
    with pytest.raises(ValueError, match="перезапуст"):
        decide(srv)
    res = srv.protocol_version()
    assert res["loadedHead"] is None and res["canonHead"]
    assert "перезапуст" in res["note"]


def test_git_environment_of_the_caller_is_ignored(tmp_path, repo, load_server, monkeypatch):
    plain = tmp_path / "plainkit"
    copy_kit(plain)  # не git-клон: запись должна быть закрыта
    other = tmp_path / "other"
    other.mkdir()
    (other / "f.txt").write_text("x\n", encoding="utf-8")
    commit_all(other)
    head = git(repo, "rev-parse", "HEAD")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))  # запуск из хука чужого репо
    srv = load_server(repo, kit=plain)
    with pytest.raises(ValueError, match="клон"):
        decide(srv)
    assert srv.pre_deploy_check()["head"] == head


def test_writes_refused_over_an_http_request(repo, load_server):
    from mcp.server.lowlevel.server import request_ctx
    from mcp.shared.context import RequestContext
    srv = load_server(repo)  # MCP_TRANSPORT не задан: запуск через mcp run, uvicorn

    def call(request):
        token = request_ctx.set(RequestContext(request_id=1, meta=None, session=None,
                                               lifespan_context=None, request=request))
        try:
            return decide(srv)
        finally:
            request_ctx.reset(token)

    before = log_bytes(repo)
    with pytest.raises(ValueError, match="HTTP"):
        call(object())  # у SSE и streamable-http в контексте — HTTP-запрос
    assert log_bytes(repo) == before
    assert call(None)["id"] == "DEC-0002"  # stdio: HTTP-запроса нет


def test_writes_refused_when_kit_changes_after_start(kit, repo, load_server):
    srv = load_server(repo)
    target = kit / "docs" / "01_PRODUCT_BOUNDARY.md"
    original = target.read_bytes()
    target.write_bytes(original + "правка на месте\n".encode("utf-8"))
    before = log_bytes(repo)
    with pytest.raises(ValueError, match="кит изменён"):
        decide(srv)
    with pytest.raises(ValueError, match="кит изменён"):
        srv.checkpoint_create("t")
    assert log_bytes(repo) == before
    target.write_bytes(original)
    assert decide(srv)["id"] == "DEC-0002"  # контроль: правка убрана
    git(kit, "commit", "-q", "--allow-empty", "-m", "новая версия кита")
    with pytest.raises(ValueError, match="перезапуст"):
        decide(srv)
    assert dec_ids(repo) == ["DEC-0001", "DEC-0002"]


def test_kit_checks_do_not_write_into_the_kit(kit, repo, load_server):
    srv = load_server(repo)
    stale = kit / "docs" / "01_PRODUCT_BOUNDARY.md"  # тот же текст, новый mtime:
    st = stale.stat()                                # обычный git status
    os.utime(stale, (st.st_atime, st.st_mtime + 5))  # переписал бы .git/index
    before = tree_digest(kit)
    assert decide(srv)["id"] == "DEC-0002"
    srv.protocol_version()
    assert tree_digest(kit) == before


def test_untracked_files_in_the_kit_do_not_block_writes(kit, repo, load_server):
    (kit / ".venv").mkdir()
    (kit / ".venv" / "pyvenv.cfg").write_text("home = x\n", encoding="utf-8")
    srv = load_server(repo)
    assert decide(srv)["id"] == "DEC-0002"


@pytest.mark.parametrize("layout", ["no-git", "nested"])
def test_writes_need_the_kit_as_a_separate_clone(tmp_path, repo, load_server, layout):
    if layout == "no-git":
        other_kit = tmp_path / "plainkit"
        copy_kit(other_kit)
    else:
        outer = tmp_path / "vendor"
        other_kit = outer / "istomahandoff"
        copy_kit(other_kit)
        commit_all(outer)
    srv = load_server(repo, kit=other_kit)
    before = log_bytes(repo)
    with pytest.raises(ValueError, match="клон"):
        decide(srv)
    with pytest.raises(ValueError, match="клон"):
        srv.checkpoint_create("t")
    assert log_bytes(repo) == before
    assert srv.validate_transition("INTAKE", "TRIAGE")["verdict"] == "VALID"
    assert "activeWorkItem" in srv.get_active_state()


def test_http_mode_refuses_writes(repo, load_server):
    srv = load_server(repo, transport="http")
    assert srv.TRANSPORT == "streamable-http"
    before = log_bytes(repo)
    with pytest.raises(ValueError, match="HTTP"):
        decide(srv)
    with pytest.raises(ValueError, match="HTTP"):
        srv.checkpoint_create("t")
    assert log_bytes(repo) == before
    assert srv.pre_deploy_check()["verdict"] == "CLEAN"


def test_protocol_lint_runs_kit_code_against_the_project(repo, load_server):
    (repo / "tools").mkdir()
    (repo / "tools" / "protocol_lint.py").write_text(
        "# старая копия lint istomahandoff\nprint('КОПИЯ В ПРОЕКТЕ')\n", encoding="utf-8")
    res = load_server(repo).protocol_lint()
    assert res["target"] == "project" and res["root"] == repo.resolve().as_posix()
    assert "КОПИЯ" not in res["stdout"]
    assert res["exitCode"] == 0, res["stdout"]
    assert "tools/protocol_lint.py: в проекте копия кита" in res["stdout"]
