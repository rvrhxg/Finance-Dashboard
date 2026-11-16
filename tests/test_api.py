from fastapi.testclient import TestClient
from app.main import create_app


def test_finance_api_ownership_summary_budgets_import_and_logout(tmp_path):
    app=create_app(f"sqlite:///{tmp_path/'api.sqlite'}")
    headers={"Origin":"http://localhost:8002","Content-Type":"application/json"}
    with TestClient(app) as alice,TestClient(app) as bob:
        for client,email in [(alice,"a@example.test"),(bob,"b@example.test")]:
            response=client.post("/api/auth/register",json={"email":email,"password":"long-test-password","name":"Tester"},headers=headers)
            assert response.status_code==201,response.text
        category=alice.post("/api/categories",json={"name":"Food","kind":"expense"},headers=headers)
        assert category.status_code==201
        category_id=category.json()["id"]
        transaction={"category_id":category_id,"occurred_on":"2026-01-02","amount":"1234.56","note":"Groceries"}
        assert bob.post("/api/transactions",json=transaction,headers=headers).status_code==404
        created=alice.post("/api/transactions",json=transaction,headers=headers)
        assert created.status_code==201,created.text
        assert created.json()["amount_kopecks"]==123456
        assert bob.delete(f"/api/transactions/{created.json()['id']}",headers=headers).status_code==404
        assert alice.post("/api/budgets",json={"category_id":category_id,"month":"2026-01","amount":"5000"},headers=headers).status_code==200
        budget=alice.get("/api/budgets").json()[0]
        assert budget["limit_kopecks"]==500000 and budget["spent_kopecks"]==123456
        assert bob.get("/api/budgets").json()==[]
        report=alice.get("/api/analytics?start=2026-01-01&end=2026-01-31")
        assert report.status_code==200,report.text
        assert report.json()["balance_kopecks"]==-123456
        assert alice.get("/api/analytics?start=2026-02-01&end=2026-01-01").status_code==400
        csv="external_id,date,kind,category,amount,note\nx1,2026-01-01,income,Salary,100000.00,January\n"
        assert alice.post("/api/import",json={"content":csv},headers=headers).json()=={"added":1,"skipped":0}
        assert alice.post("/api/import",json={"content":csv},headers=headers).json()=={"added":0,"skipped":1}
        assert len(alice.get("/api/transactions").json())==2
        assert bob.get("/api/transactions").json()==[]
        assert alice.delete(f"/api/transactions/{created.json()['id']}",headers=headers).status_code==200
        assert alice.post("/api/auth/logout",json={},headers=headers).status_code==200
        assert alice.get("/api/categories").status_code==401
