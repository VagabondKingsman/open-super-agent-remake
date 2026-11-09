"""Calls that skip the Router/Worker (event filter, memory import, teach, plugin llm) still obey the quota rule:
402 and quota 429 stop at once instead of letting the SDK retry them."""
import pytest
from fakellm import HttpError
from osa import memories, routines
from osa.providers import ProviderLimit

QUOTA = HttpError(429, {"error": {"code": "org_token_rate_limit_day", "message": "Free core models share 1000000 tokens per UTC day"}},
                  {"retry-after": "0"})


async def test_event_filter_quota_is_not_retried(llm):
    llm.script("other", QUOTA, '{"handle": false, "reason": "x"}')
    with pytest.raises(ProviderLimit):
        await routines._llm_filter("only urgent mail", "hello")
    assert len(llm.requests) == 1


async def test_memory_import_quota_is_not_retried(llm):
    llm.script("other", QUOTA, '{"items": [{"text": "from model"}]}')
    out = await memories.parse_import("- line one\n- line two")
    assert [x["text"] for x in out] == ["line one", "line two"]   # falls back to splitting lines
    assert len(llm.requests) == 1
