import pytest
from sqlalchemy import func,select
from app.database import database
from app.models import Transaction,User
from app.seed import seed_demo


def test_demo_is_fictional_reproducible_and_refuses_existing_user(tmp_path):
    engine,sessions=database(f"sqlite:///{tmp_path/'seed.sqlite'}")
    try:
        with sessions.begin() as session:
            seed_demo(session,"demo@example.test","isolated-demo-password")
        with pytest.raises(ValueError),sessions.begin() as session:
            seed_demo(session,"demo@example.test","isolated-demo-password")
        with sessions() as session:
            assert session.scalar(select(func.count()).select_from(User))==1
            assert session.scalar(select(func.count()).select_from(Transaction))==66
    finally:
        engine.dispose()
