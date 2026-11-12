"""OSA-008: crash/fault injection between resource files and SQLite during default-skill reconcile.

Invariants after any fault + restart: no exception, no duplicate skills, user edits and
deletions (tombstones) preserved, nothing reinstalled behind the user's back, state converges.
"""
import hashlib
import json
import shutil
import sqlite3

import pytest
from osa import bots, memory, skillpacks, skills

NAMES = 9


class Boom(RuntimeError):
    pass


class FaultConn:
    """Delegating connection that raises on the n-th statement matching a SQL fragment."""

    def __init__(self, real, fragment, nth=1):
        self.real, self.fragment, self.nth, self.hits = real, fragment, nth, 0

    def execute(self, sql, *args):
        if self.fragment in sql:
            self.hits += 1
            if self.hits == self.nth:
                raise Boom(self.fragment)
        return self.real.execute(sql, *args)

    def __enter__(self):
        return self.real.__enter__()

    def __exit__(self, *exc):
        return self.real.__exit__(*exc)

    def __getattr__(self, name):
        return getattr(self.real, name)


@pytest.fixture
def store(tmp_path, monkeypatch):
    conn = sqlite3.connect(tmp_path / "fresh.db", check_same_thread=False)
    conn.row_factory = memory.conn.row_factory
    for name in ("skills", "bots", "chats", "messages", "settings"):
        sql = memory.conn.execute("select sql from sqlite_master where name=?", (name,)).fetchone()[0]
        conn.execute(sql)
    monkeypatch.setattr(memory, "conn", conn)
    monkeypatch.setattr(memory, "db_path", tmp_path / "fresh.db")
    monkeypatch.setattr(skills, "conn", conn)
    monkeypatch.setattr(bots, "conn", conn)
    monkeypatch.setattr(skillpacks, "resource_root", lambda: tmp_path / "runtime")
    monkeypatch.setitem(skillpacks.CFG, "skills", {"ai_native_defaults": True})
    monkeypatch.delenv("OSA_AI_NATIVE_DEFAULTS", raising=False)
    pack = tmp_path / "pack"
    shutil.copytree(skillpacks.PACK, pack, ignore=shutil.ignore_patterns("*.zip", "__pycache__"))
    yield pack
    conn.close()


def status(result):
    return {r["name"]: r["status"] for r in result}


def bump(pack):
    """New bundle version with changed source text, so resources really differ on disk."""
    m = json.loads((pack / "manifest.json").read_text())
    m["version"] += 1
    (pack / "manifest.json").write_text(json.dumps(m))
    hashes = json.loads((pack / "source-hashes.json").read_text())
    for key in hashes:
        if key.endswith("/SKILL.md"):
            p = pack / key
            p.write_bytes(p.read_bytes() + b"\nNew source guidance.\n")
            hashes[key] = hashlib.sha256(p.read_bytes()).hexdigest()
    (pack / "source-hashes.json").write_text(json.dumps(hashes))


def fail_nth_write(monkeypatch, nth):
    real, calls = skillpacks._write_resources, []

    def wrapper(name, resources):
        calls.append(name)
        if len(calls) == nth:
            raise Boom(name)
        return real(name, resources)
    monkeypatch.setattr(skillpacks, "_write_resources", wrapper)
    return lambda: monkeypatch.setattr(skillpacks, "_write_resources", real)


def fail_sql(monkeypatch, fragment, nth=1):
    real = memory.conn
    monkeypatch.setattr(memory, "conn", FaultConn(real, fragment, nth))
    return lambda: monkeypatch.setattr(memory, "conn", real)


def assert_consistent(pack):
    """Every shared default has exactly one row, a state row pointing at it, and intact resources."""
    rows = memory.conn.execute("select name from skills where bot_id is null").fetchall()
    names = [r[0] for r in rows]
    assert len(names) == len(set(names))
    _, payloads = skillpacks._payloads(pack)
    for data, resources in payloads:
        if data["name"] in names:
            assert skillpacks._installed_resources(skillpacks.resource_root() / data["name"]) == resources


def test_fresh_install_crash_between_files_rolls_back_then_converges(store, monkeypatch):
    restore = fail_nth_write(monkeypatch, 3)
    with pytest.raises(Boom):
        skillpacks.ensure_defaults(store)
    assert memory.conn.execute("select count(*) from skills").fetchone()[0] == 0
    restore()
    result = skillpacks.ensure_defaults(store)
    assert len(result) == NAMES and set(status(result).values()) == {"installed"}
    assert_consistent(store)
    assert set(status(skillpacks.ensure_defaults(store)).values()) == {"unchanged"}


@pytest.mark.parametrize("fragment,nth", [("insert into skills", 4), ("insert or replace into bundled_skill_state", 1),
                                          ("insert or replace into bundled_skill_state", 8)])
def test_fresh_install_crash_at_db_step_converges(store, monkeypatch, fragment, nth):
    restore = fail_sql(monkeypatch, fragment, nth)
    with pytest.raises(Boom):
        skillpacks.ensure_defaults(store)
    restore()
    assert memory.conn.execute("select count(*) from skills").fetchone()[0] == 0   # whole txn rolled back
    result = skillpacks.ensure_defaults(store)
    assert set(status(result).values()) == {"installed"} and len(result) == NAMES
    assert memory.conn.execute("select count(*) from skills").fetchone()[0] == NAMES
    assert_consistent(store)


def test_leftover_files_without_db_rows_are_installed_not_duplicated(store):
    skillpacks.ensure_defaults(store)
    memory.conn.execute("delete from skills")
    memory.conn.execute("delete from bundled_skill_state")
    memory.conn.commit()
    result = skillpacks.ensure_defaults(store)
    assert set(status(result).values()) == {"installed"}
    assert memory.conn.execute("select count(*) from skills").fetchone()[0] == NAMES
    assert_consistent(store)


@pytest.mark.parametrize("fault", ["files", "state", "update"])
def test_upgrade_crash_then_restart_completes_upgrade(store, monkeypatch, fault):
    skillpacks.ensure_defaults(store)
    ids = {r["name"]: r["id"] for r in skillpacks.ensure_defaults(store)}
    bump(store)
    restore = (fail_nth_write(monkeypatch, 3) if fault == "files" else
               fail_sql(monkeypatch, "insert or replace into bundled_skill_state", 2) if fault == "state" else
               fail_sql(monkeypatch, "update skills set", 3))
    with pytest.raises(Boom):
        skillpacks.ensure_defaults(store)
    restore()
    result = skillpacks.ensure_defaults(store)
    assert set(status(result).values()) == {"updated"}   # earlier files were already swapped; not mistaken for user edits
    assert {r["name"]: r["id"] for r in result} == ids
    assert memory.conn.execute("select count(*) from skills").fetchone()[0] == NAMES
    assert set(status(skillpacks.ensure_defaults(store)).values()) == {"unchanged"}
    assert_consistent(store)


def test_upgrade_crash_preserves_user_edits_and_tombstones(store, monkeypatch):
    skillpacks.ensure_defaults(store)
    body_id = skills.find(1, "unslop")["id"]
    skills.save(None, "unslop", "my edited body", description="mine", sid=body_id)
    res_file = skillpacks.resource_root() / "refinery" / "SKILL.source.md"
    res_file.write_text("local resource edit")
    skills.delete(skills.find(1, "vibecode-kit")["id"])
    bump(store)
    restore = fail_nth_write(monkeypatch, 4)
    with pytest.raises(Boom):
        skillpacks.ensure_defaults(store)
    restore()
    for _ in range(2):   # idempotent across restarts
        result = status(skillpacks.ensure_defaults(store))
        assert result["unslop"] == "preserved-user-edit" and result["refinery"] == "preserved-user-edit"
        assert result["vibecode-kit"] == "preserved-deletion"
    assert skills.get(body_id)["body"] == "my edited body" and skills.get(body_id)["description"] == "mine"
    assert res_file.read_text() == "local resource edit"
    assert skills.find(1, "vibecode-kit") is None
    assert memory.conn.execute("select count(*) from skills where name='vibecode-kit'").fetchone()[0] == 0
    assert memory.conn.execute("select count(*) from skills").fetchone()[0] == NAMES - 1


def test_tombstone_survives_fresh_install_crash_and_restart(store, monkeypatch):
    skillpacks.ensure_defaults(store)
    skills.delete(skills.find(1, "unslop")["id"])
    restore = fail_sql(monkeypatch, "insert or replace into bundled_skill_state", 1)
    bump(store)
    with pytest.raises(Boom):
        skillpacks.ensure_defaults(store)
    restore()
    assert status(skillpacks.ensure_defaults(store))["unslop"] == "preserved-deletion"
    assert skills.find(1, "unslop") is None


def test_row_without_files_is_not_reinstalled_over_user_state(store):
    skillpacks.ensure_defaults(store)
    shutil.rmtree(skillpacks.resource_root() / "unslop")
    result = status(skillpacks.ensure_defaults(store))
    assert result["unslop"] == "preserved-user-edit"
    assert not (skillpacks.resource_root() / "unslop").exists()   # no auto-reinstall
    assert skills.find(1, "unslop") is not None
    assert memory.conn.execute("select count(*) from skills where name='unslop'").fetchone()[0] == 1


def test_truncated_resource_file_treated_as_user_edit(store):
    skillpacks.ensure_defaults(store)
    target = skillpacks.resource_root() / "refinery" / "SKILL.source.md"
    target.write_bytes(target.read_bytes()[:10])
    assert status(skillpacks.ensure_defaults(store))["refinery"] == "preserved-user-edit"
    assert len(target.read_bytes()) == 10


def test_legacy_row_with_missing_files_is_adopted_and_files_restored(store):
    skillpacks.install(store)
    shutil.rmtree(skillpacks.resource_root())
    result = skillpacks.ensure_defaults(store)
    assert set(status(result).values()) == {"adopted"}
    assert_consistent(store)


def test_explicit_install_crash_midway_then_startup_converges(store, monkeypatch):
    real = skills.save
    calls = []

    def flaky(*a, **k):
        calls.append(1)
        if len(calls) == 4:
            raise Boom("save")
        return real(*a, **k)
    monkeypatch.setattr(skills, "save", flaky)
    with pytest.raises(Boom):
        skillpacks.install(store)
    monkeypatch.setattr(skills, "save", real)
    assert memory.conn.execute("select count(*) from skills").fetchone()[0] == 3
    result = status(skillpacks.ensure_defaults(store))
    assert list(result.values()).count("adopted") == 3 and list(result.values()).count("installed") == 6
    assert memory.conn.execute("select count(*) from skills").fetchone()[0] == NAMES
    assert_consistent(store)


def test_state_lost_keeps_manual_edit_as_unmanaged(store):
    skillpacks.ensure_defaults(store)
    sid = skills.find(1, "unslop")["id"]
    skills.save(None, "unslop", "my edited body", sid=sid)
    memory.conn.execute("drop table bundled_skill_state")
    memory.conn.commit()
    result = status(skillpacks.ensure_defaults(store))
    assert result["unslop"] == "preserved-unmanaged"
    assert skills.get(sid)["body"] == "my edited body"
    assert memory.conn.execute("select count(*) from skills where name='unslop'").fetchone()[0] == 1


def test_stale_state_pointing_at_other_row_is_user_edit(store):
    skillpacks.ensure_defaults(store)
    skills.delete(skills.find(1, "unslop")["id"])
    manual = skills.save(None, "unslop", "recreated by hand")
    assert status(skillpacks.ensure_defaults(store))["unslop"] == "preserved-user-edit"
    assert skills.get(manual["id"])["body"] == "recreated by hand"


def test_hard_kill_between_swap_renames_restores_old_tree(store):
    skillpacks.ensure_defaults(store)
    root = skillpacks.resource_root()
    # Process died after target -> stage/old but before stage/new -> target.
    stage = root / ".stage-unslop-dead" / "old"
    stage.parent.mkdir()
    (root / "unslop").rename(stage)
    (root / ".stage-unslop-dead" / "new").mkdir()
    shutil.copytree(root / "refinery", root / ".stage-refinery-dead" / "new")   # complete orphan stage
    result = status(skillpacks.ensure_defaults(store))
    assert set(result.values()) == {"unchanged"}
    assert (root / "unslop" / "SKILL.source.md").is_file()
    assert not list(root.glob(".stage-*"))
    assert_consistent(store)


def test_opt_out_ignores_partial_state(store, monkeypatch):
    skillpacks.ensure_defaults(store)
    skills.delete(skills.find(1, "unslop")["id"])
    shutil.rmtree(skillpacks.resource_root() / "refinery")
    before = (memory.conn.execute("select * from skills order by id").fetchall(),
              memory.conn.execute("select * from bundled_skill_state order by name").fetchall())
    monkeypatch.setitem(skillpacks.CFG, "skills", {"ai_native_defaults": False})
    assert skillpacks.ensure_defaults(store) == []
    monkeypatch.setenv("OSA_AI_NATIVE_DEFAULTS", "false")
    assert skillpacks.ensure_defaults(store) == []
    assert before == (memory.conn.execute("select * from skills order by id").fetchall(),
                      memory.conn.execute("select * from bundled_skill_state order by name").fetchall())
    assert not (skillpacks.resource_root() / "refinery").exists()


def test_tampered_bundle_mid_upgrade_fails_before_any_write(store):
    skillpacks.ensure_defaults(store)
    snapshot = skillpacks._installed_resources(skillpacks.resource_root() / "unslop")
    bump(store)
    (store / "unslop" / "SKILL.md").write_text("tampered")
    with pytest.raises(ValueError, match="mismatch"):
        skillpacks.ensure_defaults(store)
    assert skillpacks._installed_resources(skillpacks.resource_root() / "unslop") == snapshot
