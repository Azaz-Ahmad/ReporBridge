from alembic import context
from app.db import engine, metadata
from app.clinical.schema_v1 import meta as clinical_metadata
from app.investigation.schema_v1 import meta as investigation_metadata
from app.prevention.schema_v1 import meta as prevention_metadata

with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=[metadata, clinical_metadata, investigation_metadata, prevention_metadata])
    with context.begin_transaction():
        context.run_migrations()
