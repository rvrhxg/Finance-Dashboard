"""Linux CI smoke: disposable schema on service PostgreSQL, isolated container."""
import os
import subprocess
import time
import uuid
from urllib.parse import quote
import httpx
from sqlalchemy import create_engine, text
from app.database import database


schema = "container_" + uuid.uuid4().hex
name = "ledger-ci-" + uuid.uuid4().hex
root = create_engine(os.environ["TEST_POSTGRES_URL"])
created = False


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def ready():
    for _ in range(60):
        try:
            if httpx.get("http://127.0.0.1:8002/api/health", timeout=1).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(.25)
    raise RuntimeError("Container not ready")


with root.begin() as connection:
    connection.execute(text(f'CREATE SCHEMA "{schema}"'))
url = os.environ["TEST_POSTGRES_URL"] + "?options=" + quote(f"-csearch_path={schema}")
try:
    engine, sessions = database(url)
    engine.dispose()
    docker("run", "-d", "--name", name, "--network", "host", "-e", f"DATABASE_URL={url}", "-e", "APP_ORIGIN=http://127.0.0.1:8002", "ledger-test")
    created = True
    ready()
    with httpx.Client(base_url="http://127.0.0.1:8002", headers={"Origin": "http://127.0.0.1:8002"}) as client:
        credentials = {"email": "container@example.test", "password": uuid.uuid4().hex}
        assert client.post("/api/auth/register", json=credentials).status_code == 201
        category=client.post('/api/categories',json={'name':'Food','kind':'expense'})
        assert category.status_code==201,category.text
        transaction=client.post('/api/transactions',json={'category_id':category.json()['id'],'occurred_on':'2026-01-02','amount':'1234.56','note':'Persistent transaction'})
        assert transaction.status_code==201,transaction.text
        docker("restart", name)
        ready()
        assert client.post("/api/auth/login", json=credentials).status_code == 200
        history = client.get("/api/transactions").json()
        assert history[0]["id"] == transaction.json()["id"]
        report=client.get("/api/analytics?start=2026-01-01&end=2026-01-31")
        assert report.status_code==200,report.text
        assert report.json()["expense_kopecks"]==123456
        assert docker("exec", name, "id", "-u") == "1000"
    print("Docker PostgreSQL finance persistence and non-root checks passed")
except Exception:
    if created:
        print(docker("logs", name))
    raise
finally:
    if created:
        docker("rm", "-f", name)
    with root.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    root.dispose()
