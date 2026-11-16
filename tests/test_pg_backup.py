"""Opt-in round trip in two uniquely named disposable CI databases."""
import os
import uuid
import pytest
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url
from app.pg_backup import dump, restore


@pytest.mark.skipif(not os.environ.get('TEST_POSTGRES_URL'),reason='PostgreSQL URL not configured')
def test_postgres_dump_restore_and_nonempty_target_guard(tmp_path,monkeypatch):
    url=make_url(os.environ['TEST_POSTGRES_URL'])
    connection_args={'host':url.host,'port':url.port or 5432,'user':url.username,'password':url.password}
    names=['backup_src_'+uuid.uuid4().hex,'backup_dst_'+uuid.uuid4().hex]
    created=[]
    with psycopg.connect(dbname=url.database,autocommit=True,**connection_args) as admin:
        try:
            for name in names:
                admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
                created.append(name)
            with psycopg.connect(dbname=names[0],**connection_args) as source:
                source.execute('CREATE TABLE parent(id BIGINT PRIMARY KEY)')
                source.execute('CREATE TABLE child(parent_id BIGINT REFERENCES parent(id))')
                source.execute('INSERT INTO parent VALUES(12345678901)')
                source.execute('INSERT INTO child VALUES(12345678901)')
            for key,value in {'PGHOST':url.host,'PGPORT':str(url.port or 5432),'PGUSER':url.username,'PGPASSWORD':url.password,'PGDATABASE':names[0]}.items():
                monkeypatch.setenv(key,value or '')
            target=tmp_path/'database.dump'
            dump(target)
            with pytest.raises(FileExistsError):
                dump(target)
            monkeypatch.setenv('PGDATABASE',names[1])
            restore(target)
            with psycopg.connect(dbname=names[1],**connection_args) as restored:
                assert restored.execute('SELECT parent_id FROM child').fetchall()==[(12345678901,)]
            with pytest.raises(ValueError,match='empty'):
                restore(target)
        finally:
            for name in reversed(created):
                admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
