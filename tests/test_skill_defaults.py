"""Fresh shared defaults, upgrades and edit protection; no real network or models."""
import asyncio
import hashlib
import json
import shutil
import sqlite3

import pytest
from osa import bots, memory, server, skillpacks, skills


@pytest.fixture
def defaults_store(tmp_path, monkeypatch):
    conn = sqlite3.connect(tmp_path / "fresh.db", check_same_thread=False)
    for name in ("skills", "bots", "chats", "messages", "settings"):   # v0.12：bots.create 在 settings 里记用过的最大编号
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


def test_fresh_defaults_restart_and_new_bot(defaults_store):
    pack = defaults_store
    assert skills.list_for(1) == []
    first = skillpacks.ensure_defaults(pack)
    assert len(first) == 12 and all(r["status"] == "installed" for r in first)
    before = memory.conn.execute("select id,name,updated from skills order by id").fetchall()
    assert all(r["status"] == "unchanged" for r in skillpacks.ensure_defaults(pack))
    assert before == memory.conn.execute("select id,name,updated from skills order by id").fetchall()
    assert memory.conn.execute("select count(*) from skills where bot_id is null").fetchone()[0] == 12
    bot = bots.create("Created after startup")
    assert len(skills.list_for(bot["id"])) == 12
    assert len(json.loads(skillpacks.load_skill(bot["id"], "unslop"))["content"]) < skills.MAX_BODY
    for name in (s["name"] for s in first):
        assert (skillpacks.resource_root() / name / "SKILL.md").is_file()
    assert (skillpacks.resource_root() / "unslop" / "SKILL.source.md").read_bytes() == (pack / "unslop" / "SKILL.md").read_bytes()


def test_user_edited_shared_method_not_overwritten(defaults_store):
    skillpacks.ensure_defaults(defaults_store)
    s = skills.find(1, "unslop")
    skills.save(None, "unslop", "my edited body", description="my description", sid=s["id"])
    result = skillpacks.ensure_defaults(defaults_store)
    assert next(r for r in result if r["name"] == "unslop")["status"] == "preserved-user-edit"
    assert skills.get(s["id"])["body"] == "my edited body"
    assert skills.get(s["id"])["description"] == "my description"


def test_user_resource_edits_preserved_on_upgrade(defaults_store):
    skillpacks.ensure_defaults(defaults_store)
    target = skillpacks.resource_root() / "refinery" / "SKILL.source.md"
    target.write_text("local resource edit")
    m = json.loads((defaults_store / "manifest.json").read_text());m["version"] += 1
    (defaults_store / "manifest.json").write_text(json.dumps(m))
    result = skillpacks.ensure_defaults(defaults_store)
    assert next(r for r in result if r["name"] == "refinery")["status"] == "preserved-user-edit"
    assert target.read_text() == "local resource edit"
    assert sum(r["status"] == "updated" for r in result) == 11


def test_unmanaged_name_collision_and_private_override(defaults_store):
    custom = skills.save(None, "unslop", "existing shared method")
    result = skillpacks.ensure_defaults(defaults_store)
    assert next(r for r in result if r["name"] == "unslop")["status"] == "preserved-unmanaged"
    assert skills.get(custom["id"])["body"] == "existing shared method"
    assert not (skillpacks.resource_root() / "unslop").exists()
    bot = bots.create("Private")
    private = skills.save(bot["id"], "vibecode-kit", "private override")
    skillpacks.ensure_defaults(defaults_store)
    assert skills.find(bot["id"], "vibecode-kit")["id"] == private["id"]


def test_delete_is_respected(defaults_store):
    skillpacks.ensure_defaults(defaults_store)
    skills.delete(skills.find(1, "unslop")["id"])
    result = skillpacks.ensure_defaults(defaults_store)
    assert next(r for r in result if r["name"] == "unslop")["status"] == "preserved-deletion"
    assert skills.find(1, "unslop") is None


def test_hash_upgrade_updates_untouched_skill_without_duplicate(defaults_store):
    initial = skillpacks.ensure_defaults(defaults_store)
    p = defaults_store / "refinery" / "SKILL.md"
    p.write_bytes(p.read_bytes() + b"\nNew source guidance.\n")
    hashes = json.loads((defaults_store / "source-hashes.json").read_text())
    hashes["refinery/SKILL.md"] = hashlib.sha256(p.read_bytes()).hexdigest()
    (defaults_store / "source-hashes.json").write_text(json.dumps(hashes))
    result = skillpacks.ensure_defaults(defaults_store)
    assert next(r for r in result if r["name"] == "refinery")["status"] == "updated"
    assert [r["id"] for r in result] == [r["id"] for r in initial]
    assert (skillpacks.resource_root() / "refinery" / "SKILL.source.md").read_bytes() == p.read_bytes()
    assert memory.conn.execute("select count(*) from skills").fetchone()[0] == 12


def test_opt_out_and_invalid_toggle(defaults_store, monkeypatch):
    monkeypatch.setitem(skillpacks.CFG, "skills", {"ai_native_defaults": False})
    assert skillpacks.ensure_defaults(defaults_store) == []
    assert skills.list_for(1) == [] and not skillpacks.resource_root().exists()
    monkeypatch.setenv("OSA_AI_NATIVE_DEFAULTS", "true")
    assert len(skillpacks.ensure_defaults(defaults_store)) == 12
    monkeypatch.setenv("OSA_AI_NATIVE_DEFAULTS", "false")
    assert skillpacks.ensure_defaults(defaults_store) == []
    assert len(skills.list_for(1)) == 12
    monkeypatch.setenv("OSA_AI_NATIVE_DEFAULTS", "typo")
    with pytest.raises(ValueError, match="true/false"):
        skillpacks.ensure_defaults(defaults_store)


def test_tampered_bundle_fails_before_write(defaults_store):
    (defaults_store / "unslop" / "SKILL.md").write_text("tampered")
    with pytest.raises(ValueError, match="mismatch"):
        skillpacks.ensure_defaults(defaults_store)
    assert not skillpacks.resource_root().exists()
    assert skills.list_for(1) == []


def test_adopt_exact_legacy_imports(defaults_store):
    original = skillpacks.install(defaults_store)
    result = skillpacks.ensure_defaults(defaults_store)
    assert len(result) == 12 and all(r["status"] == "adopted" for r in result)
    assert [r["id"] for r in result] == [r["id"] for r in original]


async def test_real_lifespan_reconciles_defaults(defaults_store, monkeypatch):
    async def noop():
        pass
    async def idle():
        await asyncio.Future()
    original = skillpacks.ensure_defaults
    monkeypatch.setattr(skillpacks, "ensure_defaults", lambda: original(defaults_store))
    monkeypatch.setattr(server.settings, "apply", lambda: None)
    monkeypatch.setattr(server.tasklog, "startup", lambda: None)
    monkeypatch.setattr(server.routines, "import_legacy", lambda _: None)
    monkeypatch.setattr(server.search, "sync", lambda: None)
    monkeypatch.setattr(server.backup, "RESTART", False)
    for obj in (server.mcp_hub, server.channels):
        monkeypatch.setattr(obj, "start", noop)
        monkeypatch.setattr(obj, "stop", noop)
    for obj, name in ((server, "watchdog"), (server.routines, "scheduler"),
                      (server.computer, "idle_pauser"), (server.search, "embed_loop"),
                      (server.prices, "loop"), (server.tasklog, "prune_loop")):
        monkeypatch.setattr(obj, name, idle)
    before = asyncio.all_tasks()
    async with server.lifespan(server.app):
        assert len(skills.list_for(bots.primary()["id"])) == 12
        created = asyncio.all_tasks() - before
    await asyncio.gather(*created, return_exceptions=True)


def test_container_includes_default_payload():
    dockerfile = (skillpacks.PACK.parents[1] / "Dockerfile").read_text()
    assert "COPY skills-pack/ai-native/ skills-pack/ai-native/" in dockerfile
    assert skillpacks.verify_sources()["source_files"] == 133
