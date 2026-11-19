import sqlalchemy as sa
meta = sa.MetaData()
clocks = sa.Table("demo_session_clocks", meta,
    sa.Column("session_id", sa.String(64), primary_key=True),
    sa.Column("as_of", sa.String(10), nullable=False))
