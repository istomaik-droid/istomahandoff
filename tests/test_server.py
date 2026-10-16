"""Тесты MCP-сервера протокола: запись решений и git-tools (DEC-0016, DEC-0017).

Фикстуры копий канона и локального bare-remote — в conftest.py.
"""
import asyncio
import importlib.util
import itertools
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import LOG, REPO, configure, copy_canon, git, write_hook

SERVER_PY = REPO / "mcp_server" / "server.py"
SHA = "0" * 63 + "1"
DEPUTY = {"owner": "Заместитель", "mandateRef": "MANDATE-0001"}
# невидимые символы — через chr(), чтобы их было видно в исходнике и диффе
LS, PS, NEL, FS, VT, RLO, ZWSP = (chr(c) for c in (
    0x2028, 0x2029, 0x85, 0x1C, 0x0B, 0x202E, 0x200B))
_module_ids = itertools.count()

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
    git(repo, "mv", "templates/ADR.md", "templates/ADR_v2.md")
    srv = load_server(repo)
    both = srv.pre_deploy_check(own_files=["templates/ADR.md", "templates/ADR_v2.md"])
    assert both["verdict"] == "DIRTY_OWN"
    new_only = srv.pre_deploy_check(own_files=["templates/ADR_v2.md"])
    assert new_only["verdict"] == "DIRTY_FOREIGN"
    assert new_only["foreign"] == ["templates/ADR.md"]


def test_pre_deploy_check_normalizes_own_paths(repo, load_server):
    with (repo / "docs/01_PRODUCT_BOUNDARY.md").open("a", encoding="utf-8", newline="\n") as f:
        f.write("правка\n")
    srv = load_server(repo)
    for own in ("docs" + chr(92) + "01_PRODUCT_BOUNDARY.md", "./docs/01_PRODUCT_BOUNDARY.md",
                str(repo / "docs" / "01_PRODUCT_BOUNDARY.md")):
        assert srv.pre_deploy_check(own_files=[own])["verdict"] == "DIRTY_OWN", own


def test_pre_deploy_check_keeps_short_names_and_dot_prefixes(repo, load_server):
    (repo / "x").write_text("x\n", encoding="utf-8")
    srv = load_server(repo)
    assert srv.pre_deploy_check()["verdict"] == "DIRTY_FOREIGN"  # не CLEAN
    assert srv.pre_deploy_check(["././x"])["verdict"] == "DIRTY_OWN"


def test_pre_deploy_check_does_not_repeat_paths(repo, load_server):
    git(repo, "mv", "templates/ADR.md", "templates/ADR_v2.md")
    (repo / "templates" / "ADR.md").write_text("снова\n", encoding="utf-8")
    changed = load_server(repo).pre_deploy_check()["changed"]
    assert len(changed) == len(set(changed))


def test_own_files_are_relative_to_the_repository_root(tmp_path, load_server):
    outer = tmp_path / "outer"
    copy_canon(outer / "canon")
    git(tmp_path, "init", "-q", "-b", "master", str(outer))
    configure(outer)
    git(outer, "add", "-A")
    git(outer, "commit", "-q", "-m", "base")
    target = outer / "canon" / "docs" / "01_PRODUCT_BOUNDARY.md"
    with target.open("a", encoding="utf-8", newline="\n") as f:
        f.write("правка\n")
    srv = load_server(outer / "canon")
    assert srv.pre_deploy_check(["canon/docs/01_PRODUCT_BOUNDARY.md"])["verdict"] == "DIRTY_OWN"
    assert srv.pre_deploy_check([str(target)])["verdict"] == "DIRTY_OWN"
    assert srv.pre_deploy_check(["docs/01_PRODUCT_BOUNDARY.md"])["verdict"] == "DIRTY_FOREIGN"


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
    path = repo / "docs/01_PRODUCT_BOUNDARY.md"
    if change in ("unstaged", "staged"):
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write("правка\n")
        if change == "staged":
            git(repo, "add", "docs/01_PRODUCT_BOUNDARY.md")
    elif change == "new_staged":
        (repo / "new.md").write_text("новый\n", encoding="utf-8")
        git(repo, "add", "new.md")
    else:
        git(repo, "rm", "-q", "docs/01_PRODUCT_BOUNDARY.md")
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

    def fake(args, timeout=None):
        if args[:1] == ["rev-parse"] and args[-1].endswith("^{commit}"):
            return subprocess.CompletedProcess(args, 0, "0" * 40 + "\n", "")
        return real(args, timeout)

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
def test_validate_transition_reads_conditions_and_comments(repo, load_server, fr, to, verdict, field, value):
    (repo / "docs" / "16_STATE_MACHINE.md").write_text(SYNTH16, encoding="utf-8", newline="\n")
    res = load_server(repo).validate_transition(fr, to)
    assert res["verdict"] == verdict
    if field:
        assert res.get(field) == value
