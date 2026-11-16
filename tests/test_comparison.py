from datetime import date
from sqlalchemy import event
from app.analytics import compare_periods
from app.database import database
from app.models import User, Category, Transaction
from app.periods import previous_period, percentage_change
import pytest


def test_equal_inclusive_periods_leap_year_boundaries_and_zero_baseline():
    assert previous_period(date(2024,3,1),date(2024,3,31)) == (date(2024,1,30),date(2024,2,29))
    assert previous_period(date(2026,1,1),date(2026,1,1)) == (date(2025,12,31),date(2025,12,31))
    assert percentage_change(10,0) is None
    assert percentage_change(-50,-100) == 50.0
    with pytest.raises(ValueError):
        previous_period(date.min,date.min)


def test_aggregate_reports_compare_without_loading_transactions(tmp_path):
    engine,sessions=database(f"sqlite:///{tmp_path/'comparison.sqlite'}")
    try:
        with sessions.begin() as session:
            session.add(User(id=1,email='a@example.test',name='A',password_hash='unused'))
            session.flush()
            session.add_all([Category(id=1,user_id=1,name='Income',kind='income'),Category(id=2,user_id=1,name='Expense',kind='expense')])
            session.flush()
            session.add(Transaction(user_id=1,category_id=1,occurred_on=date(2026,1,31),amount_kopecks=10000))
            session.add_all([Transaction(user_id=1,category_id=1,occurred_on=date(2026,2,1),amount_kopecks=200) for _ in range(100)])
            session.add(Transaction(user_id=1,category_id=2,occurred_on=date(2026,2,1),amount_kopecks=1234))
        statements=[]
        def capture(connection,cursor,statement,parameters,context,many):
            statements.append(statement)
        event.listen(engine,'before_cursor_execute',capture)
        with sessions() as session:
            result=compare_periods(session,1,date(2026,2,1),date(2026,2,1))
        assert result['current']['income_kopecks']==20000
        assert result['current']['count']==101
        assert result['changes']['income_kopecks']=={'delta_kopecks':10000,'percent':100.0}
        assert result['changes']['expense_kopecks']['percent'] is None
        assert len(statements)==4
        assert all('GROUP BY' in statement for statement in statements)
    finally:
        engine.dispose()
