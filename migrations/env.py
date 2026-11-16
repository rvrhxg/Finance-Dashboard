import os
from alembic import context
from sqlalchemy import create_engine
from app.models import Base

config = context.config
target_metadata = Base.metadata


def run(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=os.environ.get('DATABASE_URL', config.get_main_option('sqlalchemy.url')),
                      target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get('connection') is not None:
    run(config.attributes['connection'])
else:
    engine = create_engine(os.environ.get('DATABASE_URL', config.get_main_option('sqlalchemy.url')))
    with engine.connect() as connection:
        run(connection)
