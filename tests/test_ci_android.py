"""CI phải chạy `cargo test` của vỏ Android.

Vì sao có file này: 13 ca trong `android/src-tauri` (connect, store, pipe) từng nằm ngoài CI —
E2E-OPEN-RUST ghi lại "cargo test chưa gắn CI (cần webkit2gtk trên runner), để PR riêng". Không có
job thì một lần sửa `connect.rs` sai (ví dụ bỏ phép so manifest, quay lại nhận captive portal 200)
vẫn merge xanh, vì bộ pytest không chạm tới mã Rust.

Test này giữ đúng ba thứ đã làm job đó chạy được, để lần sau không ai bỏ đi mà không thấy đỏ ở máy
có sẵn thư viện:

1. một job chạy `cargo test` trong `android/src-tauri`;
2. job đó cài webkit2gtk trước (runner không có sẵn, đây chính là lý do nó bị hoãn);
3. job đó có `timeout-minutes`, để một ca treo không giữ runner tới 6 tiếng.
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
ANDROID_DIR = "android/src-tauri"


def _workflow() -> dict:
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


def _steps(job: dict) -> list[dict]:
    return [s for s in job.get("steps", []) if isinstance(s, dict)]


def _runs_cargo_test_in_android(job: dict) -> bool:
    for step in _steps(job):
        run = str(step.get("run", ""))
        if "cargo test" not in run:
            continue
        wd = str(step.get("working-directory", "")).strip().rstrip("/")
        if wd == ANDROID_DIR or f"cd {ANDROID_DIR}" in run:
            return True
    return False


def _android_jobs() -> dict[str, dict]:
    return {name: job for name, job in _workflow()["jobs"].items()
            if isinstance(job, dict) and _runs_cargo_test_in_android(job)}


def test_ci_runs_android_cargo_test():
    jobs = _android_jobs()
    assert jobs, (
        f"không job nào trong {CI.name} chạy `cargo test` trong {ANDROID_DIR} — "
        "13 ca Rust của vỏ Android lại nằm ngoài CI"
    )


def test_android_job_installs_webkit2gtk():
    for name, job in _android_jobs().items():
        apt = "\n".join(str(s.get("run", "")) for s in _steps(job)
                        if "apt-get install" in str(s.get("run", "")))
        assert "libwebkit2gtk-4.1-dev" in apt, (
            f"job `{name}` chạy cargo test mà không cài libwebkit2gtk-4.1-dev; "
            "runner Ubuntu không có sẵn gói này nên build sẽ đỏ"
        )


def test_android_job_has_timeout():
    for name, job in _android_jobs().items():
        assert job.get("timeout-minutes"), (
            f"job `{name}` thiếu `timeout-minutes`; một ca treo sẽ giữ runner tới trần 6 tiếng"
        )


def test_android_job_is_on_pull_requests():
    wf = _workflow()
    # YAML 1.1 đọc `on:` thành True.
    triggers = wf.get("on", wf.get(True))
    assert "pull_request" in triggers, (
        "workflow chứa job Android không chạy trên pull_request — job chỉ đỏ sau khi merge thì vô dụng"
    )
