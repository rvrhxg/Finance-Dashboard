import pytest
from sqlalchemy import func,select
from app.database import database
from app.models import User,Transaction
from app.import_csv import import_csv
from app.domain import ValidationError


def test_csv_is_atomic_idempotent_and_owner_scoped(tmp_path):
    engine,sessions=database(f"sqlite:///{tmp_path/'import.sqlite'}")
    source="external_id,date,kind,category,amount,note\nrow1,2026-01-01,income,Salary,100000.99,January\nrow2,2026-01-02,expense,Food,1234.56,Groceries\n"
    try:
        with sessions.begin() as session:
            session.add_all([User(id=1,email="a@example.test",name="A",password_hash="unused"),User(id=2,email="b@example.test",name="B",password_hash="unused")])
        with sessions.begin() as session:
            assert import_csv(session,1,source)=={"added":2,"skipped":0}
        with sessions.begin() as session:
            assert import_csv(session,1,source)=={"added":0,"skipped":2}
            assert import_csv(session,2,source)=={"added":2,"skipped":0}
        with pytest.raises(ValidationError),sessions.begin() as session:
            import_csv(session,1,source.replace("100000.99","1.00"))
        invalid=source.replace("row1","new1").replace("row2","new2").replace("1234.56","NaN")
        with pytest.raises(ValidationError),sessions.begin() as session:
            import_csv(session,1,invalid)
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(Transaction))==4
    finally:
        engine.dispose()
