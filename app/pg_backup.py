"""Trusted PostgreSQL dump/restore, with fresh file and empty target guards."""
import argparse
import os
import re
import subprocess
from pathlib import Path
import psycopg


def database_name() -> str:
    name = os.environ.get('PGDATABASE', '')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]{0,62}', name):
        raise ValueError('Explicit simple PGDATABASE name required; connection URLs are not accepted')
    return name


def client_command(program: str, file: Path) -> tuple[list[str], str]:
    if os.environ.get('PG_USE_DOCKER') != '1':
        return [program], str(file)
    # Linux CI uses a matching PostgreSQL client instead of the runner's version.
    if os.name != 'posix':
        raise ValueError('Docker client mode is intended for Linux CI')
    uid, gid = getattr(os, 'getuid')(), getattr(os, 'getgid')()
    command = ['docker', 'run', '--rm', '--network', 'host', '--user', f'{uid}:{gid}',
               '-v', f'{file.resolve().parent}:/backup']
    for key in ('PGHOST','PGPORT','PGUSER','PGPASSWORD','PGDATABASE','PGSSLMODE'):
        if key in os.environ:
            command.extend(['-e', key])
    return command+['postgres:17-alpine', program], '/backup/'+file.name


def dump(destination: Path) -> None:
    database_name()
    with destination.open('xb'):
        pass
    try:
        command, file = client_command('pg_dump', destination)
        subprocess.run(command+['--format=custom', '--no-owner', '--no-acl', '--file', file],
                       check=True, capture_output=True)
    except Exception:
        destination.unlink(missing_ok=True)
        raise ValueError('pg_dump failed; stderr is suppressed to protect connection details') from None


def restore(source: Path) -> None:
    name = database_name()
    if not source.is_file():
        raise ValueError('Trusted dump and explicit new target PGDATABASE required')
    with psycopg.connect(dbname=name) as connection:
        objects = connection.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'").fetchone()
        if objects is None or objects[0] != 0:
            raise ValueError('Restore target must be empty; no objects will be dropped')
    try:
        command, file = client_command('pg_restore', source)
        subprocess.run(command+['--exit-on-error', '--single-transaction', '--no-owner', '--no-acl',
                        '--dbname='+name, file], check=True, capture_output=True)
    except Exception:
        raise ValueError('pg_restore failed; no connection details are printed') from None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['backup', 'restore'])
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    try:
        dump(args.file) if args.operation == 'backup' else restore(args.file)
    except Exception:
        parser.exit(1, 'Operation failed. Check client tools, permissions, backup and empty target.\n')
    print('PostgreSQL operation completed. Verify application data before switching traffic.')


if __name__ == '__main__':
    main()
