"""Native skill store + opt-in resource loading. Synthetic payloads only; no LLM network."""
import hashlib
import json
import shutil
from zipfile import ZipFile

import pytest

from conftest import settle
from fakellm import Call, system_of
from osa import bots, router, server, skillpacks, skills


@pytest.fixture
def pack(tmp_path, monkeypatch):
    root = tmp_path / "pack"
    root.mkdir()
    shutil.copyfile(skillpacks.PACK / "manifest.json", root / "manifest.json")
    shutil.copytree(skillpacks.PACK / "ai-native-mentor", root / "ai-native-mentor")
    source = tmp_path / "source"
    for spec in json.loads((root / "manifest.json").read_text())["skills"]:
        d = source / spec["name"]
        (d / "scripts").mkdir(parents=True)
        (d / "SKILL.md").write_text(f"---\nname: {spec['name']}\ndescription: fixture\n---\n# Fixture\nFull method")
        (d / "scripts" / "helper.py").write_text("# Synthetic helper, not third-party payload\n")
    monkeypatch.setattr(skillpacks, "resource_root", lambda: tmp_path / "runtime")
    result = skillpacks.prepare(source, root)
    assert result == {"prepared": 7, "source_files": 14}
    return root, source


def test_prepare_preserves_sources_and_helpers(pack):
    root, source = pack
    hashes = json.loads((root / "source-hashes.json").read_text())
    for relative, digest in hashes.items():
        actual = root / relative
        original = source / relative.replace("SKILL.source.md", "SKILL.md")
        assert actual.read_bytes() == original.read_bytes()
        assert hashlib.sha256(actual.read_bytes()).hexdigest() == digest
    for p in root.glob("*/SKILL.md"):
        data = skills.from_file(p.read_text())
        assert len(data["description"]) <= 200
        assert len(data["body"]) <= skills.MAX_BODY


def test_native_discovery_idempotence_and_export(pack, make_bot):
    root, _ = pack
    bot = make_bot()
    first = skillpacks.install(root, bot["id"])
    second = skillpacks.install(root, bot["id"])
    assert len(first) == len(second) == 8
    assert [s["id"] for s in first] == [s["id"] for s in second]
    assert {s["name"] for s in skills.list_for(bot["id"])} == {s["name"] for s in first}
    mentor = skills.find(bot["id"], "ai-native-mentor")
    assert skills.parse(bot["id"], "/ai-native-mentor test")[0]["id"] == mentor["id"]
    assert skills.from_file(skills.to_file(mentor))["body"] == mentor["body"].strip()
    assert "load_skill" in skillpacks.runtime_hint(bot["id"])
    assert "ai-native-mentor" in skills.summary(bot["id"])


def test_shared_native_override_and_visibility(pack, make_bot):
    root, _ = pack
    a, b = make_bot(), make_bot()
    installed = skillpacks.install(root)
    try:
        assert len([s for s in skills.list_for(b["id"]) if s["name"] in {x["name"] for x in installed}]) == 8
        skills.save(a["id"], "ai-work-method", "custom override")
        assert json.loads(skillpacks.load_skill(a["id"], "ai-work-method"))["content"] == "custom override"
        skills.save(a["id"], "private-test", "private")
        assert "error" in json.loads(skillpacks.load_skill(b["id"], "private-test"))
        assert "error" in json.loads(skillpacks.read_resource(b["id"], "private-test"))
    finally:
        for s in installed:
            skills.delete(s["id"])


def _read_all(fn):
    parts, offset = [], 0
    while True:
        raw = fn(offset)
        assert len(raw) < 8000
        page = json.loads(raw)
        parts.append(page["content"])
        offset = page["next_offset"]
        if offset is None:
            return "".join(parts)


def test_skill_and_resource_pagination_no_truncation(pack, make_bot):
    root, _ = pack
    bot = make_bot()
    skillpacks.install(root, bot["id"])
    content = "Tiếng Việt\n" * 1200 + "END-MARKER"
    skills.save(bot["id"], "long-skill", content)
    assert _read_all(lambda o: skillpacks.load_skill(bot["id"], "long-skill", o)) == content
    file = skillpacks.resource_root() / "refinery" / "long.md"
    file.write_text(content)
    assert _read_all(lambda o: skillpacks.read_resource(bot["id"], "refinery", "long.md", o)) == content
    file.write_text("\x00" * 7000)
    assert _read_all(lambda o: skillpacks.read_resource(bot["id"], "refinery", "long.md", o)) == "\x00" * 7000
    assert "scripts/helper.py" in json.loads(skillpacks.read_resource(bot["id"], "refinery"))["content"]


@pytest.mark.parametrize("path", ["../secret", "/etc/passwd", "scripts/../../secret", "missing.md"])
def test_resource_path_restrictions(pack, make_bot, path):
    root, _ = pack
    bot = make_bot()
    skillpacks.install(root, bot["id"])
    assert "error" in json.loads(skillpacks.read_resource(bot["id"], "refinery", path))


def test_symlinks_bad_offsets_and_binary(pack, make_bot, tmp_path):
    root, _ = pack
    bot = make_bot()
    skillpacks.install(root, bot["id"])
    d = skillpacks.resource_root() / "refinery"
    secret = tmp_path / "secret.txt"
    secret.write_text("not a skill")
    (d / "link.md").symlink_to(secret)
    assert "error" in json.loads(skillpacks.read_resource(bot["id"], "refinery", "link.md"))
    (d / "binary").write_bytes(b"\xff\xfe")
    assert "error" in json.loads(skillpacks.read_resource(bot["id"], "refinery", "binary"))
    for offset in [-1, "bad", 999999, True]:
        assert "error" in json.loads(skillpacks.load_skill(bot["id"], "refinery", offset))
    for name in ["../refinery", None]:
        assert "error" in json.loads(skillpacks.load_skill(bot["id"], name))


def test_invalid_source_fails_before_db_mutation(pack, make_bot):
    root, source = pack
    bot = make_bot()
    (root / "vibecode-kit" / "SKILL.md").write_text("---\nname: wrong-name\n---\nbody")
    with pytest.raises(ValueError, match="mismatch"):
        skillpacks.install(root, bot["id"])
    assert skills.list_for(bot["id"]) == []
    (source / "refinery" / "bad-link").symlink_to("/etc/passwd")
    with pytest.raises(ValueError, match="Symlink"):
        skillpacks.prepare(source, root)


def test_archive_contains_full_packages(pack, tmp_path):
    root, _ = pack
    output = tmp_path / "pack.zip"
    skillpacks.archive(root, output)
    with ZipFile(output) as z:
        names = z.namelist()
        assert sum(n.endswith("/SKILL.md") for n in names) == 8
        assert "ai-native/refinery/SKILL.source.md" in names
        assert "ai-native/vibecode-kit/scripts/helper.py" in names
        assert z.testzip() is None


async def test_router_and_worker_load_same_skills_without_real_llm(pack, make_bot, llm, events):
    root, _ = pack
    bot = make_bot("SkillLearner")
    skillpacks.install(root, bot["id"])
    llm.script("router:SkillLearner", Call("load_skill", {"name": "ai-native-mentor"}),
               Call("dispatch", {"goal": "Skill Flow: ai-work-method -> vibecode-kit; TIP AC: load methods"}),
               "Đã giao")
    llm.script("worker", Call("load_skill", {"name": "vibecode-kit"}),
               Call("read_skill_resource", {"name": "vibecode-kit", "path": "SKILL.source.md"}), "Verified fixture")
    rt = router.runtime(bot["id"])
    await server.safe_handle(bots.chat(bot["chat_id"]), "Fix bug, không gọi dịch vụ thật")
    await settle()
    for role in ["router", "worker"]:
        requests = llm.bodies(role)
        assert requests and "ai-native-mentor" in system_of(requests[0])
        assert {"load_skill", "read_skill_resource"} <= {s["function"]["name"] for s in requests[0]["tools"]}
    tool_results = [m["content"] for b in llm.bodies("worker") for m in b["messages"] if m["role"] == "tool"]
    assert any("Full method" in out for out in tool_results)
    assert any(t.result == "Verified fixture" for t in rt.tasks.values())


def test_install_scope_capacity_and_pack_name_preflight(pack, make_bot):
    root, _ = pack
    bot = make_bot()
    with pytest.raises(ValueError, match="Bot not found"):
        skillpacks.install(root, 99999999)
    for n in range(skills.MAX_PER_BOT - 2):
        skills.save(bot["id"], f"existing-{n}", "fixture")
    with pytest.raises(ValueError, match="capacity"):
        skillpacks.install(root, bot["id"])
    assert not skillpacks.resource_root().exists()
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["skills"][0]["name"] = "../outside"
    (root / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="package skill name"):
        skillpacks.install(root)


def test_archive_inside_pack_does_not_include_itself(pack):
    root, _ = pack
    output = root / "self.zip"
    skillpacks.archive(root, output)
    with ZipFile(output) as z:
        assert "ai-native/self.zip" not in z.namelist()
        assert z.testzip() is None
