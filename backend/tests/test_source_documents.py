import base64
from sqlalchemy import select
from app import db,history,source_documents
from app.clinical.schema_v1 import access_log,grants
from test_workflow import client,seed,snapshot
from test_historical_candidates import start,candidates

def test_documents_are_exact_scoped_audited_and_do_not_change_windows(client,monkeypatch):
    _,_,candidate=start(client,monkeypatch)
    with db.engine.begin() as c:source_documents.seed(c,"coordinator","demo-amira")
    before=client("/v1/tsp/patients/demo-amira/window",method="GET").json()
    response=client("/v1/source-documents/patients/demo-amira",method="GET")
    assert response.status_code==200,response.text
    docs=response.json();assert len(docs)==4
    historical=next(d for d in docs if d["simulated"])
    stored=history.records(history.data())[1]["content"][0]["attachment"]["data"]
    assert historical["text"]==base64.b64decode(stored).decode()
    assert history.data()["finding"] in historical["text"]
    assert historical["facility"]=="Hospital A" and historical["date"].startswith("2011-07-10")
    assert historical["citations"][0]["candidate_id"]==candidate["id"]
    assert historical["citations"][0]["excerpt"]==history.data()["finding"]
    assert all(len(d["digest"])==64 and d["version"]==1 for d in docs)
    with db.engine.begin() as c:
        assert c.execute(select(access_log).where(access_log.c.action=="source_documents_viewed")).first()
        c.execute(grants.delete().where(grants.c.patient_id=="demo-amira",grants.c.role=="viewer"))
    assert client("/v1/source-documents/patients/demo-amira",method="GET",role="viewer").status_code==404
    assert client("/v1/tsp/patients/demo-amira/window",method="GET").json()==before
    assert candidates(client)[0]["id"]==candidate["id"]

def test_document_seed_idempotent_and_no_candidate_from_copy_documents(client,monkeypatch):
    monkeypatch.setenv("DEMO_MODE","true");seed(client)
    for _ in range(2):
        with db.engine.begin() as c:source_documents.seed(c,"coordinator","demo-amira")
    docs=client("/v1/source-documents/patients/demo-amira",method="GET").json()
    assert len(docs)==3 and all(d["facility"]=="Hospital B" for d in docs)
    assert candidates(client)==[]
    assert len(snapshot(client)["clinical_obligations"])==1
