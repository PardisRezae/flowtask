from pathlib import Path
from flowtask import db


def test_add_list_done_ready(tmp_path: Path):
    db_path = tmp_path / "t.db"
    db.init_db(db_path)

    t1 = db.add_task(db_path, title="A", priority=1)
    t2 = db.add_task(db_path, title="B", priority=1)
    db.add_dependency(db_path, t2, t1)

    ready = db.ready_tasks(db_path)
    assert [t.id for t in ready] == [t1]

    assert db.mark_done(db_path, t1) is True

    ready2 = db.ready_tasks(db_path)
    assert [t.id for t in ready2] == [t2]