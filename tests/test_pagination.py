from fastapi.testclient import TestClient
from datetime import date
from app.main import create_app
from app.models import Category, Transaction


def test_pages_cover_more_than_old_cap_and_do_not_leak(tmp_path):
    app=create_app(f"sqlite:///{tmp_path/'pages.sqlite'}")
    headers={'Origin':'http://localhost:8002'}
    with TestClient(app) as a, TestClient(app) as b:
        for c,email in [(a,'pages@example.test'),(b,'other@example.test')]:
            assert c.post('/api/auth/register',json={'email':email,'password':'long-test-password'},headers=headers).status_code==201
        with app.state.sessions.begin() as s:
            category=Category(user_id=1,name='Demo',kind='expense');s.add(category);s.flush()
            s.add_all([Transaction(user_id=1,category_id=category.id,occurred_on=date(2026,1,1),amount_kopecks=1) for _ in range(505)])
        ids=[]
        for offset in range(0,505,100):
            r=a.get(f'/api/transactions?limit=100&offset={offset}')
            assert r.headers['x-total-count']=='505'
            ids.extend(t['id'] for t in r.json())
        assert len(ids)==len(set(ids))==505 and ids==sorted(ids,reverse=True)
        assert b.get('/api/transactions?offset=0&limit=100').json()==[]
        assert a.get('/api/transactions?offset=505').json()==[]
        for query in ['limit=0','limit=101','offset=-1']:
            assert a.get('/api/transactions?'+query).status_code==422
