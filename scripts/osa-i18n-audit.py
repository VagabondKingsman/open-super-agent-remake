#!/usr/bin/env python3
"""Offline regression audit. Never dispatches a real task or contacts an external service.
Run from the repository root: uv run python scripts/osa-i18n-audit.py
"""
import ast
import asyncio
import importlib.util
import itertools
import json
import re
import subprocess
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from osa import auth, bots, catalog, i18n, library, router, routines, search, tasklog, templates, tools
from osa.computer import tools as computer_tools
from osa import channels

HAN = re.compile(r"[\u3400-\u9fff]")


class LocaleTests(unittest.TestCase):
    def setUp(self):
        i18n.set_locale("vi")

    def tearDown(self):
        i18n.set_locale("vi")

    def test_locale_packs_and_formatting(self):
        packs = {loc: json.loads((ROOT / f"osa/locales/{loc}/strings.json").read_text()) for loc in i18n.SUPPORTED}
        self.assertEqual(set(packs["vi"]), set(packs["zh"]))
        self.assertEqual(set(packs["en"]), set(packs["zh"]))
        for loc in ("vi", "en"):
            i18n.set_locale(loc)
            self.assertFalse(HAN.search(json.dumps(i18n.strings(), ensure_ascii=False)))
            for key, value in packs[loc].items():
                fields = set(re.findall(r"\{(v\d+)\}", value))
                self.assertEqual(fields, set(re.findall(r"\{(v\d+)\}", packs["zh"][key])), key)
                if fields:
                    i18n.s(key, **{f: "AUDIT" for f in fields})

    def test_backend_keys_exist(self):
        keys = i18n.strings()
        for path in (ROOT / "osa").rglob("*.py"):
            if "locales" in path.parts:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id == "_s" or isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id == "i18n" and fn.attr == "s":
                    if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        self.assertIn(node.args[0].value, keys, f"{path}:{node.lineno}")

    def test_frontend_keys_and_values(self):
        packs = {loc: json.loads((ROOT / f"web/src/locales/{loc}/common.json").read_text()) for loc in i18n.SUPPORTED}
        self.assertFalse(set(packs["zh"]) - set(packs["vi"]))
        self.assertFalse(HAN.search(json.dumps(list(packs["vi"].values()), ensure_ascii=False)))
        for path in (ROOT / "web/src").rglob("*"):
            if path.suffix not in (".ts", ".tsx"):
                continue
            for match in re.finditer(r"i18n\.t\(('(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")", path.read_text()):
                key = ast.literal_eval(match[1])
                self.assertIn(key, packs["vi"], f"{path}: {key}")

    def test_all_builtin_tool_schema_overlays(self):
        schemas = i18n.localize_tools(router.ROUTER_TOOLS + [router.HANDOFF, library.SAVE_PAGE, library.READ_PAGE, search.SEARCH_TOOL] + computer_tools.SCHEMAS + tools.schemas())
        self.assertFalse(HAN.search(json.dumps(schemas, ensure_ascii=False)))

    def test_public_catalog_overlay_including_copy_label(self):
        self.assertFalse(HAN.search(json.dumps(catalog.public(), ensure_ascii=False)))
        self.assertFalse(HAN.search(json.dumps(catalog.categories(), ensure_ascii=False)))

    def test_builtin_templates_and_skill_links(self):
        for loc in ("vi", "en"):
            i18n.set_locale(loc)
            for item in templates.builtin():
                text = templates.builtin_text(item["id"])
                self.assertFalse(HAN.search(text))
                value = templates.parse(text)
                names = {s["name"] for s in value["skills"]}
                self.assertTrue(all(not r.get("skill") or r["skill"] in names for r in value["routines"]))

    def test_seeded_legacy_routines_without_rewriting_user_text(self):
        old = i18n._strings("zh")["legacy_routine_news"]
        self.assertFalse(HAN.search(i18n.legacy_routine_default(old)))
        self.assertEqual(i18n.legacy_routine_default("Custom instructions"), "Custom instructions")
        text = "[任务已派发] [定时任务 Audit] 这是定时任务「Audit」（每 1 小时）的一次运行。\n\n要求：" + old
        self.assertFalse(HAN.search(i18n.localize_task_goal(text)))

    def test_routine_goals(self):
        routine = {"name": "Audit", "bot_id": 1, "skill": "", "prompt": "Kiểm tra cron", "trigger": {"kind": "daily", "days": [1, 5], "times": ["09:00", "18:30"]}}
        text = routines.goal_for(routine, "Sự kiện thử")
        self.assertIn("Đây là một lần chạy lịch", text)
        self.assertIn("Yêu cầu: Kiểm tra cron", text)
        self.assertIn("T2, T6", text)
        self.assertFalse(HAN.search(text))

    def test_legacy_and_new_wrappers(self):
        for prefix in ("[任务已派发]", "[Đã giao task]", "[Task dispatched]"):
            self.assertEqual(i18n.task_dispatch_goal(prefix + " Goal"), "Goal")
            row = tasklog._task((1, 0, prefix + " Goal", '{"kind":"dispatch"}', 1, 1))
            self.assertEqual(row["goal"], "Goal")
        for prefix in ("[任务 #1 结果]", "[Kết quả task #1]", "[Task #1 result]"):
            self.assertEqual(i18n.task_result_body(prefix + "\nResult"), "Result")

    def test_login_and_oauth_html(self):
        from osa.server import _oauth_page
        text = auth._page('/?x="', "Lỗi thử").body.decode()
        self.assertIn('lang="vi"', text)
        self.assertIn("Đăng nhập", text)
        self.assertIn("&quot;", text)
        self.assertFalse(HAN.search(text))
        self.assertIn('lang="vi"', _oauth_page(False, "Lỗi", "Thử lại").body.decode())

    def test_channel_commands_and_cards(self):
        for text in ("Cho phép #12", "cho phép #12", "ALLOW #12", "拒绝 #12", "Luôn cho phép #12"):
            self.assertIsNotNone(channels._WORD_CMD.match(text))
        self.assertEqual(channels.word_command("ok", 12), "Cho phép #12")
        with patch.object(channels, "_bot_name", return_value="Audit"), patch.object(channels, "public_url", return_value=""):
            for args in ('{"reason":"Hãy giúp"}', '{"需要你做的事":"Hãy giúp"}'):
                card = channels.card_for({"id": 1, "bot_id": 1, "kind": "help", "args": args, "task_id": 2})
                self.assertIn("Hãy giúp", card["body"])
                self.assertFalse(HAN.search(json.dumps(card, ensure_ascii=False)))

    def test_standalone_helper_localized(self):
        result = subprocess.run([sys.executable, str(ROOT / "osa/computer/cdp_helper.py")], input=json.dumps({"op": "audit-invalid", "_locale_strings": i18n.strings()}), capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Thao tác không rõ: audit-invalid", result.stderr)
        self.assertFalse(HAN.search(result.stderr))

    def test_keyword_filter(self):
        self.assertIn("loại trừ", routines._keyword_filter({"exclude": ["spam"]}, "SPAM"))
        self.assertIn("Không khớp", routines._keyword_filter({"include": ["cron"]}, "hello"))
        self.assertIsNone(routines._keyword_filter({"include": ["cron"]}, "CRON audit"))

    def test_bad_trigger_shapes_are_localized_validation_errors(self):
        for value in (None, [], {"kind": "daily", "times": [5]}, {"kind": "daily", "times": "09:00"}, {"kind": "daily", "times": ["09:00"], "days": [0]}, {"kind": "daily", "times": ["09:00"], "days": ["x"]}, {"kind": "every", "minutes": []}, {"kind": "every", "minutes": "bad"}, {"kind": "every", "minutes": 5.5}, {"kind": "webhook", "include": "word"}, {"kind": "webhook", "exclude": [1]}, {"kind": "webhook", "llm_filter": {"bad": 1}}):
            with self.subTest(value=value), self.assertRaises(ValueError) as caught:
                routines._clean_trigger(value)
            self.assertFalse(HAN.search(str(caught.exception)))

    def test_next_run_calculation(self):
        now = time.mktime((2026, 11, 6, 21, 0, 0, 0, 0, -1))
        self.assertEqual(routines.next_after({"kind": "every", "minutes": 5}, now), now + 300)
        result = routines.next_after({"kind": "daily", "times": ["09:00"], "days": [1]}, now)
        expected = time.mktime((2026, 11, 9, 9, 0, 0, 0, 0, -1))
        self.assertEqual(result, expected)
        self.assertIsNone(routines.next_after({"kind": "webhook"}, now))


class CronConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        i18n.set_locale("vi")
        routines.FIRING.clear()
        routines.RUNNING.clear()

    async def asyncTearDown(self):
        routines.FIRING.clear()
        routines.RUNNING.clear()

    async def test_simultaneous_webhooks_dispatch_once(self):
        row = {"id": -999, "bot_id": 1, "name": "Audit", "trigger": {"kind": "webhook", "llm_filter": "Quy tắc"}, "skill": "", "prompt": "Kiểm tra"}
        async def filtered(*_):
            await asyncio.sleep(0)
            return True, "OK"
        dispatched = AsyncMock(return_value=SimpleNamespace(id=-998))
        with patch.object(routines, "_record", side_effect=itertools.count(-100)), patch.object(routines, "_changed", new=AsyncMock()), patch.object(routines, "_llm_filter", side_effect=filtered), patch.object(routines, "_finish"), patch.object(routines, "conn") as connection, patch.object(bots, "get", return_value={"id": 1}), patch.object(router, "runtime", return_value=SimpleNamespace(dispatch=dispatched)):
            results = await asyncio.gather(routines.fire(row, "webhook", "One"), routines.fire(row, "webhook", "Two"))
            self.assertEqual(sum(r["accepted"] for r in results), 1)
            self.assertEqual(dispatched.await_count, 1)
            self.assertEqual(dispatched.await_args.kwargs["label"], "[Lịch Audit]")
            self.assertFalse(routines.FIRING)
            await dispatched.await_args.kwargs["on_done"](SimpleNamespace(status="done", result="OK"))
            self.assertFalse(routines.RUNNING)

    async def test_runtime_failure_releases_reservation(self):
        row = {"id": -999, "bot_id": 1, "name": "Audit", "trigger": {"kind": "every", "minutes": 5}, "skill": "", "prompt": "Kiểm tra"}
        with patch.object(routines, "_record", return_value=-1), patch.object(routines, "_changed", new=AsyncMock()), patch.object(routines, "_finish"), patch.object(bots, "get", return_value={"id": 1}), patch.object(router, "runtime", side_effect=RuntimeError("Lỗi thử")):
            result = await routines.fire(row, "schedule")
            self.assertFalse(result["accepted"])
            self.assertFalse(routines.FIRING)
            self.assertFalse(routines.RUNNING)


if __name__ == "__main__":
    unittest.main(verbosity=2)
