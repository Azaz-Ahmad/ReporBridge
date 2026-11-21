"""Verify the local write queue preserves commits, rollback and database locking."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import create_engine
from app import main

def test_sqlite_writers_queue_before_database_timeout_and_release_on_rollback(monkeypatch,tmp_path):
    engine=create_engine("sqlite:///"+str(tmp_path/"writers.db"),connect_args={"timeout":0.03})
    with engine.begin() as connection:connection.exec_driver_sql("CREATE TABLE writes (value TEXT)")
    monkeypatch.setattr(main.db,"engine",engine)
    monkeypatch.setattr(main.prevention,"synchronize",lambda connection:None)
    holding=Event();second_started=Event();release=Event()
    def first(connection):
        connection.exec_driver_sql("INSERT INTO writes VALUES ('first')");holding.set()
        assert release.wait(3)
    def second(connection):connection.exec_driver_sql("INSERT INTO writes VALUES ('second')")
    def queued():second_started.set();return main.write(second)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(main.write,first);assert holding.wait(3)
            b=pool.submit(queued);assert second_started.wait(3)
            # Longer than the connection's SQLite busy timeout; the request must
            # remain queued outside SQLite rather than fail with database locked.
            assert not release.wait(0.15)
            release.set();a.result(timeout=3);b.result(timeout=3)
        def rejected(connection):
            connection.exec_driver_sql("INSERT INTO writes VALUES ('rolled back')")
            raise ValueError("synthetic rejected write")
        with pytest.raises(ValueError,match="synthetic rejected write"):main.write(rejected)
        main.write(lambda connection:connection.exec_driver_sql("INSERT INTO writes VALUES ('after rollback')"))
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT value FROM writes ORDER BY rowid").scalars().all()==["first","second","after rollback"]
    finally:release.set();engine.dispose()
