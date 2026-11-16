"""Disposable PostgreSQL schema; no public tables are reset."""
import os
import uuid
from datetime import date
from urllib.parse import quote
import pytest
from sqlalchemy import create_engine, text
from app.database import database
from app.models import User, Category, Transaction
from app.analytics import compare_periods


@pytest.mark.skipif(not os.environ.get('TEST_POSTGRES_URL'),reason='PostgreSQL URL not configured')
def test_postgres_migrations_exact_bigint_aggregates_and_owner_isolation():
    url=os.environ['TEST_POSTGRES_URL']
    root=create_engine(url)
    schema='ledger_'+uuid.uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine=None
    try:
        engine,sessions=database(url+'?options='+quote(f'-csearch_path={schema}'))
        with sessions.begin() as session:
            session.add_all([User(id=1,email='a@example.test',name='A',password_hash='unused'),User(id=2,email='b@example.test',name='B',password_hash='unused')])
            session.flush()
            session.add_all([Category(id=1,user_id=1,name='Income',kind='income'),Category(id=2,user_id=2,name='Private',kind='income')])
            session.flush()
            session.add_all([Transaction(user_id=1,category_id=1,occurred_on=date(2026,2,1),amount_kopecks=12345678901),Transaction(user_id=1,category_id=1,occurred_on=date(2026,1,31),amount_kopecks=100),Transaction(user_id=2,category_id=2,occurred_on=date(2026,2,1),amount_kopecks=999)])
        with sessions() as session:
            result=compare_periods(session,1,date(2026,2,1),date(2026,2,1))
            assert result['current']['income_kopecks']==12345678901
            assert result['previous']['income_kopecks']==100
            assert result['current']['monthly']==[{'month':'2026-02','kind':'income','amount_kopecks':12345678901}]
            assert result['changes']['income_kopecks']['delta_kopecks']==12345678801
    finally:
        if engine is not None:
            engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
