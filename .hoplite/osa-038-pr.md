## Summary
- CI trên `b961870` đỏ vì e27 vẫn `xfail` sau khi PR #43 đã chặn bot duyệt thẻ.
- Bỏ `xfail`. Baseline e27 chuyển thành PASS.
- BOARD ghi EVAL-SUITE và P0-2 là Done.

## Verification
- `uv run pytest tests/test_evals.py -q --tb=line -k e27_other` → 1 passed.
- CI fail trước sửa: run `42863750569`, job backend, XPASS e27.
- Full suite: NOT_CHECKED.
