"""Bundled AI Native pack adapter. Skills remain in OSA's existing SQLite store.

Team-authored sources are bundled byte-for-byte; OSA adapters are generated at runtime.
No source code is executed by the installer or the read-only resource tools.
"""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import yaml

from . import memory, skills
from .config import CFG, ROOT

PACK = ROOT / "skills-pack" / "ai-native"
PAGE_SIZE = 5500  # JSON + text must fit Worker's 8000-character tool-result cap.


def resource_root() -> Path:
    return memory.db_path.parent / "skill-packs" / "ai-native"


def _files(root: Path) -> list[Path]:
    files = []
    if root.is_symlink():
        raise ValueError("Symlink not allowed in skill pack root")
    for p in sorted(root.rglob("*")):
        if any(part in {"__pycache__", ".pytest_cache", ".git", ".venv", "node_modules", ".DS_Store"} for part in p.relative_to(root).parts):
            continue
        if p.is_symlink():
            raise ValueError(f"Symlink not allowed in skill pack: {p.name}")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            files.append(p)
    return files


def _wrapper(spec: dict) -> str:
    name = spec["name"]
    body = f"""# {name} · OSA adapter

{spec['focus']}

## Nạp phương pháp đầy đủ trước khi làm

1. Gọi read_skill_resource(name=\"{name}\", path=\"SKILL.source.md\").
   Nếu next_offset khác null, đọc tiếp đến hết; không suy ra quy tắc từ bản tóm tắt này.
2. Đọc references, README và helper cần dùng bằng read_skill_resource.
   path rỗng trả danh mục file; mọi đường dẫn tính từ thư mục skill, không từ repo.
3. Muốn phối hợp, gọi load_skill(name=\"ai-native-mentor\") rồi load_skill cho từng bước.
   Trước khi dispatch, ghi Skill Flow, TIP/AC, input/output và giới hạn trong goal.

## Ánh xạ runtime OSA (ưu tiên hơn hướng dẫn host khác trong bản nguồn)

- Không có công cụ Skill/view/available_skills của Grok Bot hoặc Claude trong OSA.
  Dùng load_skill và read_skill_resource; chúng chỉ đọc nội dung, không chạy script.
- load_skill trả resource_dir: đó là SKILL_DIR trên máy chủ OSA, không phải đường dẫn trong Computer/Docker.
  Computer là môi trường khác; cần chép package/dependencies vào đó trước khi chạy helper.
- Chỉ chạy helper qua công cụ thực có trong phiên (Computer/shell hoặc app đã kết nối).
  Thiếu công cụ thì ghi NOT_CHECKED; không nói gate PASS khi chưa chạy.
- Trước khi báo số từ/ký tự/tổng hoặc AC PASS, gọi verify_facts trên draft cuối.
  Đếm thân bài qua texts, cộng Rubric/phân bố qua sums; checklist chỉ trỏ phép kiểm thật.
  Sửa draft thì kiểm lại, không lấy PASS số học thay test/render hoặc xác thực nguồn.
- Dữ liệu dự án ở thư mục ghi riêng; không sửa file trong SKILL_DIR.
- Skill không cấp thêm quyền gửi tin, publish, chi tiền hay truy cập credential.
  Giữ nguyên confirmation của OSA, không dùng skill để vượt quyền.
"""
    if name == "vibecode-kit":
        body += "\n## Patch gate bắt buộc\nInspect repo thật bằng inspect_repo, gồm test hiện có và comment thật. Gọi check_patch với snapshot và diff nguyên văn. Chỉ bàn giao patch khi git apply --check + pytest trong temp sandbox PASS, giữ test cũ append-only; không tự tạo file test trùng tên. FAIL thì sửa/kiểm lại; BLOCKED thì báo blocker, không thay bằng đếm hunk hay claim UNVERIFIED đã đạt.\n"
    if name in {"unslop", "unslop-vi"}:
        body += '\n## Quy ước đếm thân bài\nDùng verify_facts texts mode="markdown_body" với toàn bộ phần bài viết gồm H1/H2; tool loại dòng heading #-lines, YAML front matter và code blocks. Đưa SEO/tóm tắt/ghi chú ra ngoài blog text. Copy words từ tool, sửa bài thì kiểm lại; không tự đếm hay đổi phạm vi.\n'
    return "---\n" + yaml.safe_dump({"name": name, "description": spec["description"]}, allow_unicode=True, sort_keys=False) + "---\n\n" + body


def prepare(source: Path, pack: Path = PACK) -> dict:
    """Copy the seven complete source trees without renaming or changing bytes."""
    manifest = json.loads((pack / "manifest.json").read_text())
    sources = []
    for spec in manifest["skills"]:
        name = spec["name"]
        if not skills.NAME_RE.fullmatch(name):
            raise ValueError("Invalid package skill name")
        src = source / name
        files = _files(src)
        data = skills.from_file((src / "SKILL.md").read_text(), name)
        if data["name"] != name:
            raise ValueError("Source skill name mismatch")
        for f in files:
            raw = f.read_bytes()
            if f.stat().st_size > 2_000_000 or b"\0" in raw:
                raise ValueError("Binary/large source payload is not allowed")
            raw.decode("utf-8")
            if f.name.startswith(".env") or f.suffix in {".key", ".pem", ".p12"}:
                raise ValueError("Credential files are not allowed in a skill pack")
        sources.append((name, src, files))
    hashes = {}
    for name, src, files in sources:
        dest = pack / name
        dest.mkdir(parents=True, exist_ok=True)
        # Remove only the old generated alias, never a source file or user resource.
        alias = dest / "SKILL.source.md"
        if alias.exists() and not (src / "SKILL.source.md").exists():
            if alias.read_bytes() != (src / "SKILL.md").read_bytes():
                raise ValueError("Old source alias differs; inspect before updating pack")
            alias.unlink()
        for file in files:
            relative = file.relative_to(src)
            target = dest / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
            hashes[f"{name}/{relative.as_posix()}"] = hashlib.sha256(file.read_bytes()).hexdigest()
    (pack / "source-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    return {"prepared": len(sources), "source_files": len(hashes)}


def verify_sources(pack: Path = PACK) -> dict:
    """Check exact payload file set and SHA-256 before installing any source."""
    manifest = json.loads((pack / "manifest.json").read_text())
    names = [s["name"] for s in manifest["skills"]]
    if len(set(names)) != len(names) or any(not skills.NAME_RE.fullmatch(n) for n in names):
        raise ValueError("Invalid or duplicate package skill name")
    expected = json.loads((pack / "source-hashes.json").read_text())
    actual = {f"{name}/{p.relative_to(pack / name).as_posix()}": hashlib.sha256(p.read_bytes()).hexdigest()
              for name in names for p in _files(pack / name)}
    if actual != expected:
        raise ValueError("Source hash/file-set mismatch; re-audit and regenerate source-hashes.json")
    return {"source_files": len(actual), "sha256": "PASS"}


def _payloads(pack):
    manifest = json.loads((pack / "manifest.json").read_text())
    names = [s["name"] for s in manifest["skills"]] + ["ai-native-mentor"]
    if len(set(names)) != len(names) or any(not skills.NAME_RE.fullmatch(n) for n in names):
        raise ValueError("Invalid or duplicate package skill name")
    verify_sources(pack)
    specs = {s["name"]: s for s in manifest["skills"]}
    out = []
    for name in names:
        directory = pack / name
        resources = {p.relative_to(directory).as_posix(): p.read_bytes() for p in _files(directory)}
        original = skills.from_file(resources["SKILL.md"].decode("utf-8"), name)
        if original["name"] != name:
            raise ValueError(f"Skill name mismatch: {name}")
        if name in specs:
            resources["SKILL.source.md"] = resources["SKILL.md"]
            resources["SKILL.md"] = _wrapper(specs[name]).encode("utf-8")
        data = skills.from_file(resources["SKILL.md"].decode("utf-8"), name)
        out.append((data, resources))
    return manifest.get("version", 1), out


def _resource_hash(resources):
    return hashlib.sha256(json.dumps({p: hashlib.sha256(b).hexdigest() for p, b in sorted(resources.items())},
                                     sort_keys=True).encode()).hexdigest()


def _installed_resources(directory):
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in _files(directory)}


def _record_hash(data):
    return hashlib.sha256(json.dumps({k: data[k] for k in ("name", "description", "body")},
                                     sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _write_resources(name, resources):
    """Replace one preflighted tree; never execute a helper during installation."""
    root = resource_root()
    root.mkdir(parents=True, exist_ok=True)
    target = root / name
    if target.is_symlink():
        raise ValueError("Runtime skill directory is a symlink")
    with tempfile.TemporaryDirectory(prefix=".stage-", dir=root) as tmp:
        staged = Path(tmp) / "new"
        staged.mkdir()
        for relative, data in resources.items():
            dest = staged / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        old = Path(tmp) / "old"
        if target.exists():
            target.rename(old)
        try:
            staged.rename(target)
        except OSError:
            if old.exists():
                old.rename(target)
            raise


def install(pack: Path = PACK, bot_id: int | None = None) -> list[dict]:
    """Explicit reinstall via native parsing/saving. This command replaces edits."""
    _, payloads = _payloads(pack)
    if bot_id is not None:
        from . import bots
        if not bots.get(bot_id):
            raise ValueError("Bot not found")
    existing = {r[0] for r in memory.conn.execute("select name from skills where bot_id is ?", (bot_id,))}
    if len(existing | {d["name"] for d, _ in payloads}) > skills.MAX_PER_BOT:
        raise ValueError("Skill capacity exceeded")
    for data, resources in payloads:
        _write_resources(data["name"], resources)
    saved = [skills.save(bot_id, **data, source="import") for data, _ in payloads]
    return [{"id": s["id"], "name": s["name"], "bot_id": s["bot_id"], "body_chars": len(s["body"])} for s in saved]


def defaults_enabled():
    override = os.environ.get("OSA_AI_NATIVE_DEFAULTS")
    if override is not None:
        if override.lower() not in {"true", "false", "1", "0"}:
            raise ValueError("OSA_AI_NATIVE_DEFAULTS must be true/false/1/0")
        return override.lower() in {"true", "1"}
    enabled = (CFG.get("skills") or {}).get("ai_native_defaults", True)
    if not isinstance(enabled, bool):
        raise ValueError("skills.ai_native_defaults must be boolean")
    return enabled


def ensure_defaults(pack: Path = PACK) -> list[dict]:
    """Startup reconciliation. Preserve manual collisions, edits, overrides and deletions."""
    if not defaults_enabled():
        return []
    version, payloads = _payloads(pack)  # Complete validation before SQLite/filesystem changes.
    conn = memory.conn
    results = []
    with conn:
        conn.execute("BEGIN IMMEDIATE")  # Serialize first startup across server processes.
        conn.execute("""create table if not exists bundled_skill_state(
            name text primary key, skill_id integer, version text, bundle_hash text,
            record_hash text, resources_hash text)""")
        existing = {name: sid for sid, name in conn.execute("select id, name from skills where bot_id is null")}
        states = {r[0]: r[1:] for r in conn.execute("select name,skill_id,version,bundle_hash,record_hash,resources_hash from bundled_skill_state")}
        missing = {d["name"] for d, _ in payloads} - existing.keys() - states.keys()
        if len(existing) + len(missing) > skills.MAX_PER_BOT:
            raise ValueError("Shared skill capacity exceeded")
        for data, resources in payloads:
            name = data["name"]
            sid, prior = existing.get(name), states.get(name)
            record_hash, resource_hash = _record_hash(data), _resource_hash(resources)
            bundle_hash = hashlib.sha256(json.dumps([version, record_hash, resource_hash]).encode()).hexdigest()
            current = skills.get(sid) if sid is not None else None
            status = "installed"
            if prior and current is None:
                results.append({"name": name, "status": "preserved-deletion"})
                continue
            if current:
                directory = resource_root() / name
                try:
                    actual_resources = _resource_hash(_installed_resources(directory)) if directory.exists() else None
                except (OSError, ValueError):
                    actual_resources = "unreadable-or-symlink"
                if prior:
                    if sid != prior[0] or _record_hash(current) != prior[3] or actual_resources != prior[4]:
                        results.append({"name": name, "status": "preserved-user-edit", "id": sid})
                        continue
                    if bundle_hash == prior[2]:
                        results.append({"name": name, "status": "unchanged", "id": sid, "hash": bundle_hash})
                        continue
                    status = "updated"
                else:
                    # Adopt only exact legacy imports, not a manual same-name method.
                    if _record_hash(current) != record_hash or actual_resources not in (None, resource_hash):
                        results.append({"name": name, "status": "preserved-unmanaged", "id": sid})
                        continue
                    status = "adopted"
            _write_resources(name, resources)
            now = time.time()
            if sid is None:
                sid = conn.execute("insert into skills(bot_id,name,description,body,source,created,updated) values(null,?,?,?,?,?,?)",
                                   (name, data["description"], data["body"], "import", now, now)).lastrowid
            else:
                conn.execute("update skills set description=?,body=?,updated=? where id=?",
                             (data["description"], data["body"], now, sid))
            conn.execute("insert or replace into bundled_skill_state values(?,?,?,?,?,?)",
                         (name, sid, str(version), bundle_hash, record_hash, resource_hash))
            results.append({"name": name, "status": status, "id": sid, "hash": bundle_hash})
    return results


def _page(text: str, offset: int) -> dict:
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0 or offset > len(text):
        raise ValueError("Invalid offset")
    end = min(offset + PAGE_SIZE, len(text))
    while len(json.dumps(text[offset:end], ensure_ascii=False)) > 6000:
        end = offset + (end - offset) // 2
    return {"offset": offset, "next_offset": end if end < len(text) else None,
            "end_offset": end, "total_chars": len(text),
            "read_status": "COMPLETE" if end == len(text) else "CONTINUE_REQUIRED",
            "content": text[offset:end]}


def load_skill(bot_id: int, name: str, offset: int = 0) -> str:
    """Read any visible native skill; bot-specific overrides still win."""
    if not isinstance(name, str) or not skills.NAME_RE.fullmatch(name):
        return json.dumps({"error": "Invalid skill name"})
    s = skills.find(bot_id, name)
    if not s:
        return json.dumps({"error": "Skill not found or not visible"})
    try:
        out = {"name": s["name"], "description": s["description"], **_page(s["body"], offset)}
        directory = resource_root() / s["name"]
        if directory.is_dir() and skills.NAME_RE.fullmatch(s["name"]):
            out["resource_dir"] = str(directory)
            out["resource_hint"] = "Use read_skill_resource with an empty path to list files."
            if (directory / "SKILL.source.md").is_file():
                out["method_source"] = {"tool": "read_skill_resource", "name": s["name"],
                                        "path": "SKILL.source.md", "offset": 0,
                                        "required": "This is an adapter, not the method. Read every source page before applying it."}
        return json.dumps(out, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"error": str(e)})


def read_resource(bot_id: int, name: str, path: str = "", offset: int = 0) -> str:
    """Read pack text only, with pagination. No arbitrary file access or execution."""
    if not isinstance(name, str) or not skills.NAME_RE.fullmatch(name) or not skills.find(bot_id, name):
        return json.dumps({"error": "Skill not found or not visible"})
    try:
        directory = resource_root() / name
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("No installed resources")
        base = directory.resolve()
        if not isinstance(path, str):
            raise ValueError("Invalid resource path")
        relative = Path(path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Path must stay inside the skill directory")
        target = directory / relative
        # Reject even internal symlinks: resources must be copied, not linked.
        if any(p.is_symlink() for p in [target, *target.parents] if p != base.parent):
            raise ValueError("Symlinks are not allowed")
        if not target.resolve().is_relative_to(base):
            raise ValueError("Path must stay inside the skill directory")
        if not path:
            listing = "\n".join(p.relative_to(directory).as_posix() for p in _files(directory))
            return json.dumps({"name": name, "kind": "file-list", **_page(listing, offset)}, ensure_ascii=False)
        if not target.is_file() or target.stat().st_size > 2_000_000:
            raise ValueError("Resource missing or too large")
        return json.dumps({"name": name, "path": path, **_page(target.read_text(encoding="utf-8"), offset)}, ensure_ascii=False)
    except (ValueError, OSError, UnicodeError) as e:
        return json.dumps({"error": str(e)})


SCHEMAS = [
    {"type": "function", "function": {"name": "load_skill",
     "description": "Read a visible OSA skill before using it. Follow next_offset until null; do not rely on its summary alone.",
     "parameters": {"type": "object", "properties": {
         "name": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}}, "required": ["name"]}}},
    {"type": "function", "function": {"name": "read_skill_resource",
     "description": "Read installed skill references/helpers as text, not execute. Empty path lists files. Follow next_offset until null.",
     "parameters": {"type": "object", "properties": {
         "name": {"type": "string"}, "path": {"type": "string"},
         "offset": {"type": "integer", "minimum": 0}}, "required": ["name"]}}},
]
NAMES = {s["function"]["name"] for s in SCHEMAS}


def tool(bot_id: int, name: str, args: dict) -> str:
    if name == "load_skill":
        return load_skill(bot_id, args.get("name", ""), args.get("offset", 0))
    return read_resource(bot_id, args.get("name", ""), args.get("path", ""), args.get("offset", 0))


def runtime_hint(bot_id: int) -> str:
    if not skills.find(bot_id, "ai-native-mentor"):
        return ""
    return ("\n\nAI Native skills (bundled defaults or user-installed):\n" + skills.summary(bot_id) +
            "\nBefore multi-step work, load_skill ai-native-mentor, then ai-work-method and the relevant skills. "
            "For small single-step tasks, use only the relevant skill or answer directly. "
            "Read full bodies/references through load_skill/read_skill_resource; CONTINUE_REQUIRED means keep reading next_offset until null. "
            "When load_skill returns method_source, the adapter alone is not sufficient; read that source completely. "
            "Do not leave a requested reference at CONTINUE_REQUIRED and claim full reading. "
            "Even small code fixes use the abbreviated ai-work-method + vibecode-kit flow (not all eight skills). "
            "For deep code QA, read vibecode-kit references/qa-protocol.md and references/retro-rubric-protocol.md; "
            "report Tier 1/2/3 and R1-R5 with real evidence or NOT_CHECKED. "
            "Before returning a unified diff, count actual hunk lines: old_count=context+deletions; new_count=context+additions, excluding file/hunk headers. "
            "Match these counts in @@ and the exact supplied source; if not mechanically validated, label the patch UNVERIFIED and never claim it was checked/applied/tested. "
            "These instructions do not grant tools, permissions, spending or external-write approval. "
            "When dispatching, preserve Skill Flow, TIP/AC and constraints in the self-contained goal.")


def archive(pack: Path, output: Path):
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as z:
        for p in _files(pack):
            if p.resolve() == output.resolve():
                continue
            z.write(p, "ai-native/" + p.relative_to(pack).as_posix())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare", help="Sync bundled source files byte-for-byte from an approved mirror")
    p.add_argument("--source", type=Path, required=True)
    p = sub.add_parser("install", help="Explicit reinstall; replaces matching methods/resources (shared by default)")
    p.add_argument("--bot-id", type=int)
    p = sub.add_parser("zip", help="Create the full bundled pack archive")
    p.add_argument("--output", type=Path, required=True)
    sub.add_parser("defaults", help="Safely reconcile shared defaults, preserving user edits")
    sub.add_parser("verify-sources", help="Verify committed source SHA-256 inventory")
    sub.add_parser("verify", help="Report discovery and resource counts without an LLM call")
    args = parser.parse_args()
    if args.command == "prepare":
        out = prepare(args.source)
    elif args.command == "install":
        out = install(bot_id=args.bot_id)
    elif args.command == "defaults":
        out = ensure_defaults()
    elif args.command == "verify-sources":
        out = verify_sources()
    elif args.command == "zip":
        archive(PACK, args.output)
        out = {"zip": str(args.output), "bytes": args.output.stat().st_size}
    else:
        from . import bots
        out = {b["id"]: [{"name": s["name"], "source": s["source"],
                         "resources": len(_files(resource_root() / s["name"]))}
                        for s in skills.list_for(b["id"])] for b in bots.list_bots()}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
