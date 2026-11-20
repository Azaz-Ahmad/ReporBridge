from app import db
from app.record_facilities import assign
from app.clinical.access import authorize
from app.clinical.gateway import ClinicalRetrieval
from app.clinical.contracts import Filters
from test_workflow import client, seed  # noqa:F401
import pytest
from fastapi import HTTPException


def test_facility_attribute_is_scoped_immutable_and_replayable(client):
    seed(client)
    with db.engine.begin() as connection:
        retrieval=ClinicalRetrieval(connection,authorize(connection,"coordinator","demo-amira"))
        item=retrieval.list(Filters(kind="Observation")).items[0]
        original=assign(connection,"coordinator","demo-amira",item.id,"Hospital A")
        assert assign(connection,"coordinator","demo-amira",item.id,"Hospital A")==original
        result=retrieval.get(evidence_id=item.id).evidence
        assert result.provenance["facility"]["origin"]=="Hospital A"
        assert result.digest==item.digest
        with pytest.raises(HTTPException):assign(connection,"coordinator","demo-amira",item.id,"Hospital B")
        with pytest.raises(HTTPException):assign(connection,"viewer","demo-no-grant",item.id,"Hospital A")
