"""Synthetic checks only; no paid model, code execution or external sources."""
import json
import pytest
from conftest import settle
from fakellm import Call, system_of
from osa import bots, router, server, verification


def test_vi_en_counts_exact_unicode():
    texts = ["Tiếng Việt ở nhà 🙂", "A short English draft."]
    r = verification.verify({"texts": [{"id": str(i), "text": t} for i,t in enumerate(texts)]})
    assert [c["words"] for c in r["checks"]] == [5,4]
    assert [c["chars"] for c in r["checks"]] == [len(t) for t in texts]
    assert verification.verify({})["overall"] == "NOT_CHECKED"


def test_count_limits_and_claimed_count_regression():
    r = verification.verify({"texts": [{"id":"blog", "text":"word "*222, "min_words":160, "max_words":200, "claimed_words":185}]})
    assert r["checks"][0]["words"] == 222 and r["overall"] == "FAIL"
    assert set(r["checks"][0]["failed"]) == {"words_limit", "claimed_words"}


def test_rubric_and_decimal_sums():
    r = verification.verify({"sums":[{"id":"rubric","values":[2,0,1,2,2],"claimed_total":4}, {"id":"decimal","values":["0.1","0.2"],"claimed_total":"0.3"}]})
    assert r["checks"][0]["total"] == "7" and r["checks"][0]["status"] == "FAIL"
    assert r["checks"][1]["total"] == "0.3" and r["checks"][1]["status"] == "PASS"


def test_slide_partition_regression():
    r = verification.verify({"sums":[{"id":"partition","values":[3,2,2,1],"claimed_total":12}]})
    assert r["checks"][0]["total"] == "8" and r["overall"] == "FAIL"


def test_numeric_quotes_cross_locale_and_mismatch():
    args = {"source":"Giá 650.000 đồng.","draft":"Price 650,000 VND.","source_number_format":"vi","draft_number_format":"en",
            "number_checks":[{"id":"price","expected":650000,"actual":650000,"source_quote":"650.000","draft_quote":"650,000"}]}
    assert verification.verify(args)["overall"] == "PASS"
    args["number_checks"][0]["actual"] = 600000
    assert verification.verify(args)["overall"] == "FAIL"


def test_no_fake_evidence_or_manual_pass():
    r = verification.verify({"number_checks":[{"id":"ungrounded","expected":2,"actual":2}],
                             "checklist":[{"id":"runtime","check_ids":[]},{"id":"unknown","check_ids":["invented"]}]})
    assert r["overall"] == "NOT_CHECKED"
    assert all(c["status"] == "NOT_CHECKED" for c in r["checks"]+r["checklist"])


def test_ac_status_derived_only_from_results():
    r = verification.verify({"texts":[{"id":"limit","text":"hello", "max_words":0}],
                             "checklist":[{"id":"AC1","check_ids":["limit"]}]})
    assert r["checklist"][0]["status"] == "FAIL"


@pytest.mark.parametrize("args", [None, {"texts":None}, {"texts":[{}]}, {"texts":[{"id":"x","text":"x","max_words":True}]},
    {"texts":[{"id":"x","text":"x","min_words":3,"max_words":1}]}, {"draft":"x"*100001},
    {"sums":[{"id":"x","values":["__import__('os').system('false')"]}]},
    {"sums":[{"id":"x","values":[True]}]}, {"sums":[{"id":"x","values":["1e999999"]}]},
    {"sums":[{"id":"x","values":[1]},{"id":"x","values":[2]}]}])
def test_invalid_inputs_are_not_checked(args):
    assert verification.verify(args)["overall"] == "NOT_CHECKED"
    assert "error" in verification.verify(args)


def test_large_result_never_silently_truncated():
    args={"texts":[{"id":"x"*75+str(i),"text":"text"} for i in range(50)]}
    r=json.loads(verification.tool(args))
    assert len(verification.tool(args)) < 8000
    assert "split" in r["error"] and r["overall"] == "NOT_CHECKED"


async def test_router_worker_real_tool_integration_with_fake_model(make_bot,llm):
    b=make_bot("Verifier")
    llm.script("router:Verifier",Call("verify_facts",{"sums":[{"id":"r","values":[2,0,1,2,2]}]}),
               Call("dispatch",{"goal":"Verify word count"}),"Queued")
    llm.script("worker",Call("verify_facts",{"texts":[{"id":"body","text":"Hello world"}]}),"Checked")
    await server.safe_handle(bots.chat(b["chat_id"]),"Check fixture")
    await settle()
    for role in ("router","worker"):
        bodies=llm.bodies(role)
        assert "verify_facts" in system_of(bodies[0])
        assert "verify_facts" in {t["function"]["name"] for t in bodies[0]["tools"]}
    assert any('"total": "7"' in m.get("content","") for body in llm.bodies("router") for m in body["messages"] if m["role"]=="tool")
    assert any('"words": 2' in m.get("content","") for body in llm.bodies("worker") for m in body["messages"] if m["role"]=="tool")


def test_csv_delimiters_are_not_english_grouping():
    r=verification.verify({"source":"Finance,finance.csv,2026-10,120000000,approved", "draft":"Revenue 120000000 VND",
        "number_checks":[{"id":"csv","expected":120000000,"actual":120000000,
                          "source_quote":"Finance,finance.csv,2026-10,120000000,approved","draft_quote":"Revenue 120000000 VND"}]})
    assert r["checks"][0]["status"] == "PASS"


def test_exact_diff_hunk_check_and_complete_calculation():
    diff='--- a/a.py\n+++ b/a.py\n@@ -1,1 +1,2 @@\n-old\n+new\n+two\n+three\n'
    r=verification.verify({"diffs":[{"id":"patch","text":diff}]})
    h=r["checks"][0]["hunks"][0]
    assert h["header_new"]==2 and h["actual_new"]==3 and r["overall"]=="FAIL"
    assert r["calculation_status"]=="COMPLETE"
    good=verification.verify({"diffs":[{"id":"patch","text":diff.replace('+1,2','+1,3')}]})
    assert good["overall"] == "PASS"
