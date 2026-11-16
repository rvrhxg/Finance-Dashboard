from datetime import date
from app.database import database
from app.models import User,Category,Transaction
from app.analytics import analytics


def test_owner_period_categories_and_integer_monthly_totals(tmp_path):
    engine,sessions=database(f"sqlite:///{tmp_path/'analytics.sqlite'}")
    try:
        with sessions.begin() as session:
            session.add_all([User(id=1,email="a@example.test",name="A",password_hash="unused"),User(id=2,email="b@example.test",name="B",password_hash="unused")])
            session.flush()
            session.add_all([Category(id=1,user_id=1,name="Salary",kind="income"),Category(id=2,user_id=1,name="Food",kind="expense"),Category(id=3,user_id=2,name="Private",kind="income")])
            session.flush()
            session.add_all([Transaction(user_id=1,category_id=1,occurred_on=date(2026,1,1),amount_kopecks=10000000),Transaction(user_id=1,category_id=2,occurred_on=date(2026,1,2),amount_kopecks=123456),Transaction(user_id=1,category_id=2,occurred_on=date(2026,2,1),amount_kopecks=999),Transaction(user_id=2,category_id=3,occurred_on=date(2026,1,1),amount_kopecks=777)])
        with sessions() as session:
            result=analytics(session,1,date(2026,1,1),date(2026,1,31))
            assert result["income_kopecks"]==10000000
            assert result["expense_kopecks"]==123456
            assert result["balance_kopecks"]==9876544
            assert result["categories"]==[{"category":"Food","amount_kopecks":123456}]
            assert result["count"]==2
            assert all(type(row["amount_kopecks"]) is int for row in result["monthly"])
            assert analytics(session,2,date(2026,1,1),date(2026,1,31))["income_kopecks"]==777
    finally:
        engine.dispose()
