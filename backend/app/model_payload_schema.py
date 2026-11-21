import sqlalchemy as sa
meta=sa.MetaData()
calls=sa.Table("model_payload_calls",meta,sa.Column("id",sa.String(100),primary_key=True),
 sa.Column("run_id",sa.String(100),nullable=False,index=True),sa.Column("patient_id",sa.String(100),nullable=False,index=True),
 sa.Column("actor",sa.String(50),nullable=False),sa.Column("created",sa.String,nullable=False),sa.Column("detail",sa.JSON,nullable=False))
