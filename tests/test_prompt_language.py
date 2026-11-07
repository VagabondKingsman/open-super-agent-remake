"""LLM-facing prompts are English, and the reply language follows the UI language.

Deliberate exceptions, not prompt prose:
- The stored attachment marker ``[附件]`` is named inside ROUTER_PROMPT. The web composer and
  channel ingress write that exact marker; the model has to recognize it.
- ``routines._QUIET_RE`` still accepts the legacy quiet markers ``无新内容`` and ``没有新内容``.
- ``memory.defang`` still rewrites the legacy Chinese system-notice markers, plus the English ones.
- ``需要你做的事`` is the approval-argument key the web UI and channels parse. It is not a prompt.
- User-authored text (bot instructions, memories, skill bodies) can be any language.
- UI strings stay in ``i18n.t`` / ``N_`` / ``later`` with Chinese keys.
"""
import ast
import re
from pathlib import Path

import pytest

from conftest import until
from osa import bots, i18n, library, memories, router, routines, search, server, teach, tools, verification, worker
from osa.computer import tools as ctools
from osa.skillpacks import SCHEMAS as SKILL_SCHEMAS
from osa.local_checks import SCHEMAS as CHECK_SCHEMAS

ROOT = Path(__file__).resolve().parent.parent
# The attachment marker is a stored contract. The prompt must name it.
ALLOWED_CJK = ("[附件]",)


def _schema_text(schema: dict) -> list[str]:
    fn = schema.get("function") or {}
    found = []
    if isinstance(fn.get("description"), str):
        found.append(fn["description"])
    props = ((fn.get("parameters") or {}).get("properties") or {})
    for spec in props.values():
        if isinstance(spec, dict) and isinstance(spec.get("description"), str):
            found.append(spec["description"])
    return found


def _prompt_blobs() -> list[tuple[str, str]]:
    blobs = [
        ("router.ROUTER_PROMPT", router.ROUTER_PROMPT),
        ("router.STATE_PROMPT", router.STATE_PROMPT),
        ("router.GROUP_PROMPT", router.GROUP_PROMPT),
        ("router.DM_TURN", router.DM_TURN),
        ("router.REPLY_TURN", router.REPLY_TURN),
        ("router.REPLY_SHOWN", router.REPLY_SHOWN),
        ("router.REPLY_OWED", router.REPLY_OWED),
        ("worker.WORKER_PROMPT", worker.WORKER_PROMPT),
        ("worker.PAGE_HINT", worker.PAGE_HINT),
        ("worker.CONTINUE_PROMPT", worker.CONTINUE_PROMPT),
        ("worker.STEP_EXHAUSTED", worker.STEP_EXHAUSTED),
        ("worker.REVIEWER_PROMPT", worker.REVIEWER_PROMPT),
        ("memories.IMPORT_PROMPT", memories.IMPORT_PROMPT),
        ("routines.QUIET_HINT", routines.QUIET_HINT),
        ("routines.PREVIOUS_LABEL", routines.PREVIOUS_LABEL),
        ("routines.FILTER_PROMPT", routines.FILTER_PROMPT),
        ("teach.DRAFT_PROMPT", teach.DRAFT_PROMPT),
        ("ctools.SYSTEM_HINT", ctools.SYSTEM_HINT),
    ]
    blobs += [(f"answer:{lang}", text) for lang, text in i18n.ANSWER_LANG.items()]
    blobs += [(f"angle:{i}", text) for i, text in enumerate(worker.HEAVY_ANGLES)]
    schemas = (router.ROUTER_TOOLS + [router.MESSAGE_BOT, router.HANDOFF] + ctools.SCHEMAS
               + [library.SAVE_PAGE, library.READ_PAGE, search.SEARCH_TOOL, verification.SCHEMA]
               + SKILL_SCHEMAS + CHECK_SCHEMAS)
    for schema in schemas:
        name = (schema.get("function") or {}).get("name", "?")
        blobs += [(f"schema:{name}", text) for text in _schema_text(schema)]
    for name, (_, desc, params) in tools.TOOLS.items():
        blobs.append((f"tool:{name}", desc))
        blobs += [(f"tool:{name}:{key}", value) for key, value in params.items()]
    return blobs


def _visible(text: str) -> str:
    for item in ALLOWED_CJK:
        text = text.replace(item, "")
    return text


def test_prompt_constants_and_tool_schemas_have_no_cjk():
    hits = [f"{name}: {i18n.CJK.search(text).group(0)!r}"
            for name, text in _prompt_blobs() if i18n.CJK.search(_visible(text))]
    assert hits == []


def test_production_code_does_not_force_prompt_language_zh():
    bad = []
    for path in (ROOT / "osa").rglob("*.py"):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            if re.search(r"""in_lang\s*=\s*['"]zh['"]""", code):
                bad.append(f"{path.relative_to(ROOT)}:{i}")
    assert bad == []


@pytest.mark.parametrize("language", ["vi", "en", "zh"])
def test_model_paths_include_the_reply_directive(monkeypatch, language):
    monkeypatch.setattr(i18n, "_lang", language)
    directive = i18n.ANSWER_LANG[language]
    assert directive in i18n.model_hint()
    task = worker.Task(id=1, goal="check", bot_id=0)
    assert directive in worker.worker_system(task, pages=False)
    assert directive in worker.reviewer_system()
    assert directive in memories._import_prompt()
    assert directive in (teach.DRAFT_PROMPT + i18n.model_hint())
    assert directive in (routines.FILTER_PROMPT + i18n.model_hint())
    assert "=== Draft " in worker.REVIEWER_PROMPT
    assert "方案" not in worker.REVIEWER_PROMPT


@pytest.mark.parametrize("language, needle", [
    ("vi", "Reply in Vietnamese"),
    ("en", "Reply in English"),
    ("zh", "Reply in Chinese"),
])
async def test_router_system_prompt_carries_the_directive(monkeypatch, llm, events, make_bot, language, needle):
    monkeypatch.setattr(i18n, "_lang", language)
    bot = make_bot("LangBot")
    llm.script("router:LangBot", "ok")
    await server.safe_handle(bots.chat(bot["chat_id"]), "hello")
    await until(lambda: llm.bodies("router", "LangBot"), what="router turn")
    system = llm.bodies("router", "LangBot")[0]["messages"][0]["content"]
    assert needle in system
    assert "system-attached current state" in llm.bodies("router", "LangBot")[0]["messages"][-1]["content"]


def test_prompt_format_fields_are_closed():
    router.ROUTER_PROMPT.format(
        name="N", instructions="I", date="2026-11-07", capabilities="c", others="o",
        skills="s", routines="r", memories="m", group="")
    router.STATE_PROMPT.format(tasks="t", approvals="a", memories="", turn="")
    router.GROUP_PROMPT.format(title="T", members="M", lead="L")
    router.DM_TURN.format(name="N")
    router.REPLY_OWED.format(owed="O", name="N")
    worker.WORKER_PROMPT.format(date="2026-11-07")


def test_string_literals_sent_as_prompts_are_listed_above():
    """Fail when a new module-level prompt constant with CJK shows up outside the registry.

    Docstrings, i18n.t/N_/later keys, and comments are not prompts. The names scanned here
    are the ones this task treats as model instructions.
    """
    names = {label.split(".", 1)[-1].split(":", 1)[0] for label, _ in _prompt_blobs()}
    missing = []
    for path in (ROOT / "osa").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
                continue
            if not isinstance(node.value.value, str) or not i18n.CJK.search(_visible(node.value.value)):
                continue
            target = next((t.id for t in node.targets if isinstance(t, ast.Name)), "")
            if target.endswith(("PROMPT", "HINT")) and target not in names and len(node.value.value) > 40:
                missing.append(f"{path.name}:{target}")
    assert missing == []
