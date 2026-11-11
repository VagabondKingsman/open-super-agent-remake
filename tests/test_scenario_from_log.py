"""Log → gợi ý kịch bản eval: đếm lỗi theo dấu, bỏ lỗi đã có kịch bản, in khung YAML."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent / "scripts" / "scenario_from_log.py"


def _mod():
    spec = importlib.util.spec_from_file_location("scenario_from_log", HERE)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


log = _mod()


def test_the_same_error_with_different_numbers_has_one_signature():
    a = "2026-11-11 06:45:10,377 W osa.computer: retry 3/5 in 2.0s for bot 71"
    b = "2026-11-12 01:02:03,004 W osa.computer: retry 4/5 in 9.5s for bot 12"
    assert log.signature(a) == log.signature(b)
    assert log.signature(a) != log.signature("2026-11-11 06:45:10 W osa.computer: machine gone")
    # 临时路径和 uuid 也算一样
    x = "E osa: could not read /tmp/osa-rec-1794379673.jsonl (task 8f14e45f-ceea-467a-9a3b-0b1c2d3e4f50)"
    y = "E osa: could not read /tmp/osa-rec-1794379999.jsonl (task 11111111-2222-3333-4444-555555555555)"
    assert log.signature(x) == log.signature(y)


def test_only_warnings_and_errors_are_counted():
    assert log.level_of("2026-11-11 06:45:10,377 W osa.x: chậm") == "W"
    assert log.level_of("2026-11-11 06:45:10 E osa.x: hỏng") == "E"
    assert log.level_of("ERROR:    [Errno 98] address already in use") == "E"
    assert log.level_of("WARNING: something odd") == "W"
    assert log.level_of("2026-11-11 06:45:10,377 I httpx: 200 OK") == ""


def test_an_error_is_suggested_once_it_repeats():
    lines = [
        "2026-11-11 01:00:00,000 E osa.computer: vnc closed 1011 for task 3",
        "2026-11-11 01:00:05,000 I httpx: 200 OK",
        "2026-11-11 01:00:09,000 E osa.computer: vnc closed 1011 for task 8",
        "2026-11-11 01:00:11,000 E osa.computer: vnc closed 1011 for task 9",
        "2026-11-11 01:00:12,000 W osa.channels.telegram: retry in 5s",
    ]
    items = log.scan(lines, min_count=2)
    assert len(items) == 1                      # 一次的那个 W 不够格
    [vnc] = items
    assert vnc["count"] == 3 and vnc["severity"] == "error" and vnc["area"] == "computer"
    assert vnc["first"] == 1 and vnc["last"] == 4
    assert "<n>" in vnc["signature"]

    items = log.scan(lines, min_count=1)
    assert [i["count"] for i in items] == [3, 1]     # 多的在前
    assert items[1]["severity"] == "warning"


def test_a_signature_already_written_into_a_scenario_is_skipped(tmp_path, capsys):
    err = "2026-11-11 01:00:00,000 E osa.computer: vnc closed 1011 for task 3"
    items = log.scan([err, err.replace("task 3", "task 4")], min_count=2)
    assert not log.covered(items[0], tmp_path)                       # 还没有

    (tmp_path / "e99_vnc.yaml").write_text("notes: |\n  log: " + items[0]["signature"] + "\n", encoding="utf-8")
    assert log.covered(items[0], tmp_path)

    f = tmp_path / "osa.log"
    f.write_text("\n".join([err, err.replace("task 3", "task 4")]) + "\n", encoding="utf-8")
    assert log.main([str(f), "--scenarios", str(tmp_path)]) == 0
    assert "không có lỗi nào lặp" in capsys.readouterr().out

    assert log.main([str(f), "--scenarios", str(tmp_path), "--all", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]["count"] == 2 and out[0]["area"] == "computer"


def test_a_log_that_cannot_be_read_says_so(tmp_path, capsys):
    assert log.main([str(tmp_path / "nope.log")]) == 2
    assert "không đọc được" in capsys.readouterr().err
