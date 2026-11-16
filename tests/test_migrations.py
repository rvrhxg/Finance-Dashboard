from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_upgrade_retains_transactions_and_index_downgrade_is_reversible(tmp_path):
    engine=create_engine(f"sqlite:///{tmp_path/'migration.sqlite'}")
    try:
        with engine.begin() as connection:
            config=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
            config.attributes['connection']=connection
            command.upgrade(config,'0001')
            connection.execute(text("INSERT INTO users VALUES(1,'a@example.test','A','hash')"))
            connection.execute(text("INSERT INTO categories VALUES(1,1,'Food','expense')"))
            connection.execute(text("INSERT INTO transactions VALUES(1,1,1,'2026-01-01',123456,'Note',NULL)"))
            command.upgrade(config,'head')
            assert connection.scalar(text('SELECT version_num FROM alembic_version'))=='0002'
            assert connection.scalar(text('SELECT amount_kopecks FROM transactions'))==123456
            assert 'ix_transactions_owner_period' in {row['name'] for row in inspect(connection).get_indexes('transactions')}
            command.downgrade(config,'0001')
            assert connection.scalar(text('SELECT count(*) FROM transactions'))==1
            command.upgrade(config,'head')
            command.check(config)
    finally:
        engine.dispose()
