from test_workflow import client, snapshot  # noqa: F401


def test_default_cohort_is_plain_idempotent_and_preserves_rules(client,monkeypatch):
    monkeypatch.setenv("DEMO_MODE","true")
    monkeypatch.delenv("REPROBRIDGE_TEST_MODE",raising=False)
    result=client("/demo/seed");assert result.status_code==200,result.text
    assert len(result.json()["patient_ids"])==3
    state=snapshot(client)
    assert [p["resource"]["name"][0]["given"][0] for p in state["patients"]]==["Amira","Lina","Sara"]
    assert client("/demo/seed").status_code==200
    assert snapshot(client)==state
    queue=client("/v1/tsp/queue",method="GET").json()
    assert {row["status"] for row in queue}=={"IN_WINDOW","WINDOW_PASSED","DUE_SOON"}
