"""Trang báo cáo tuần: số liệu từ observe.stats() ra markdown, cờ tăng chi phí, việc cần xem lại."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "scripts" / "weekly_report.py"


def _mod():
    spec = importlib.util.spec_from_file_location("weekly_report", HERE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


rep = _mod()


def _stats(**kw):
    kpi = {"cost": 1.0, "tokens": 1000, "input": 800, "output": 200, "cache_hit": 400, "cache_rate": 0.5,
           "calls": 20, "errors": 1, "ttft": 1500, "speed": 25.0, "tool_calls": 9, "tool_errors": 0,
           "tasks": 4, "done": 3, "failed": 1, "success": 0.75}
    return {"currency": "$", "start": 1_760_000_000, "end": 1_760_600_000, "kpi": {**kpi, **kw},
            "prev": {"cost": 0.5, "input": 400, "output": 100, "calls": 10, "errors": 0, "ttft": 1000},
            "models": [{"model": "grok-4.7", "provider": "xai", "cost": 0.9, "tokens": 900, "errors": 1}],
            "tools": [{"name": "fetch_url", "calls": 5, "errors": 2}, {"name": "remember", "calls": 4, "errors": 0}],
            "problems": [{"kind": "model", "count": 4, "error": "xai/grok-4.7: 502"},
                         {"kind": "task", "task_id": 7, "title": "theo dõi giá"}],
            "tasks": [], "bots": [], "roles": [], "routines": [], "series": [], "hours": []}


def test_the_page_carries_the_numbers_of_the_week():
    page = rep.page(_stats())
    assert page.startswith("# Báo cáo tuần")
    assert "| Chi phí | 1.0000 $" in page
    assert "| Gọi model | 20 |" in page
    assert "| First token (router) | 1,500 ms" in page
    assert "| Task | 4 (xong 3, hỏng 1) |" in page
    assert "| Task thành công | 75% |" in page
    assert "grok-4.7" in page and "xai" in page


def test_a_doubling_of_cost_is_flagged_but_a_small_move_is_not():
    assert "⚠️ +100%" in rep.page(_stats())                  # gấp đôi: tăng
    cost_row = next(l for l in rep.page(_stats(cost=0.52)).splitlines() if l.startswith("| Chi phí"))
    assert "⚠️" not in cost_row and "như kỳ trước" in cost_row      # +4%: không đáng nói
    t = rep.page(_stats(cost=0.3))
    assert "(-40%)" in next(l for l in t.splitlines() if l.startswith("| Chi phí"))   # rẻ đi: chỉ ghi số


def test_only_tools_with_errors_are_listed_and_problems_are_grouped():
    page = rep.page(_stats())
    tools = page.split("## Tool có lỗi")[1].split("##")[0]
    assert "fetch_url" in tools and "remember" not in tools
    problems = page.split("## Việc cần xem lại")[1]
    assert "×4" in problems and "theo dõi giá" in problems


def test_an_empty_week_says_so_and_eval_is_optional():
    page = rep.page({"currency": "$", "start": 1_760_000_000, "end": 1_760_600_000, "kpi": {}, "prev": None})
    assert "Không có gì hỏng trong kỳ này." in page
    assert "## Eval" not in page

    page = rep.page(_stats(), {"osa_commit": "abc123", "tasks": [
        {"id": "e01", "area": "core", "success": True}, {"id": "e02", "area": "code", "success": False}]})
    assert "1/2 kịch bản đạt" in page and "abc123" in page and "❌ e02" in page


def test_the_env_file_is_read_without_overwriting_what_is_already_set(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# chú thích\nOSA_DATA_DIR=/tmp/osa-data\nĐÃ_CÓ=trong file\n", encoding="utf-8")
    monkeypatch.delenv("OSA_DATA_DIR", raising=False)
    monkeypatch.setenv("ĐÃ_CÓ", "từ môi trường")
    rep._env_file(env)
    import os
    assert os.environ["OSA_DATA_DIR"] == "/tmp/osa-data"
    assert os.environ["ĐÃ_CÓ"] == "từ môi trường"       # 环境里已经有的不覆盖
