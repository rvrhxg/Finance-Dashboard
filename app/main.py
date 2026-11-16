import os
import time
from pathlib import Path
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .database import database
from .models import User, LoginSession, Category, Transaction, Budget
from .security import hash_password, verify_password, new_token, token_hash
from .analytics import analytics, compare_periods
from .import_csv import import_csv
from .domain import money_to_kopecks
from datetime import date
from .domain import ValidationError


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=12, max_length=128)
    name: str = Field(default="Customer", max_length=100)


class CategoryInput(BaseModel):
    name: str = Field(min_length=1,max_length=80)
    kind: str = Field(pattern="^(income|expense)$")


class TransactionInput(BaseModel):
    category_id: StrictInt = Field(gt=0)
    occurred_on: str
    amount: str = Field(min_length=1,max_length=30)
    note: str = Field(default="",max_length=500)


class CsvInput(BaseModel):
    content: str = Field(max_length=200000)


class BudgetInput(BaseModel):
    category_id: StrictInt = Field(gt=0)
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    amount: str = Field(min_length=1,max_length=30)


def create_app(url=None, origin=None):
    origin = origin or os.environ.get("APP_ORIGIN", "http://localhost:8002")
    secure = os.environ.get("ENVIRONMENT") == "production"
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("APP_ORIGIN must be an HTTP(S) origin without path or credentials")
    if secure and not origin.startswith("https://"):
        raise ValueError("Production requires HTTPS APP_ORIGIN")
    engine, sessions = database(url)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="Ledger Finance API", lifespan=lifespan)
    app.state.sessions = sessions
    attempts = {}
    dummy = hash_password("dummy-password-value")

    @app.middleware("http")
    async def browser_security(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if request.headers.get("origin") != origin:
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Origin rejected"}, status_code=403)
            if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "JSON required"}, status_code=415)
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 262144:
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path in {"/", "/app.js", "/style.css"}:
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    def identity(request, session):
        token = request.cookies.get("session", "")
        login = session.get(LoginSession, token_hash(token)) if len(token) == 64 else None
        if not login or login.expires_at <= int(time.time()):
            raise HTTPException(401, "Authentication required")
        return session.get(User, login.user_id)

    def profile(user):
        return {"id": user.id, "name": user.name, "email": user.email}

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response):
        with sessions.begin() as session:
            identity(request, session)
            session.delete(session.get(LoginSession, token_hash(request.cookies["session"])))
        response.delete_cookie("session", httponly=True, secure=secure, samesite="strict")
        return {"ok": True}

    @app.post("/api/auth/{action}")
    def auth(action: str, data: Credentials, request: Request, response: Response):
        if action not in {"login", "register"}:
            raise HTTPException(404)
        now = int(time.time())
        for key in list(attempts):
            if attempts[key][1] < now:
                del attempts[key]
        key = request.client.host
        count, until = attempts.get(key, (0, now + 60))
        attempts[key] = (count + 1, until)
        if count >= 15:
            raise HTTPException(429, "Try again later")
        with sessions.begin() as session:
            email = data.email.strip().lower()
            user = session.scalar(select(User).where(User.email == email))
            if action == "register":
                if not data.name.strip():
                    raise HTTPException(400,"Name required")
                if user:
                    raise HTTPException(409, "Email unavailable")
                user = User(email=email, name=data.name.strip(), password_hash=hash_password(data.password))
                session.add(user)
                try:
                    session.flush()
                except IntegrityError:
                    raise HTTPException(409, "Email unavailable")
                response.status_code = 201
            elif not verify_password(data.password, user.password_hash if user else dummy) or not user:
                raise HTTPException(401, "Invalid credentials")
            token = new_token()
            session.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=now+86400))
            response.set_cookie("session", token, httponly=True, secure=secure, samesite="strict", max_age=86400)
            return profile(user)

    @app.get("/api/auth/me")
    def me(request: Request):
        with sessions() as session:
            return profile(identity(request, session))

    def own_category(session,user_id,category_id):
        category=session.scalar(select(Category).where(Category.id==category_id,Category.user_id==user_id))
        if not category:
            raise HTTPException(404,"Category not found")
        return category

    @app.get("/api/categories")
    def categories(request: Request):
        with sessions() as session:
            user=identity(request,session)
            return [{"id":c.id,"name":c.name,"kind":c.kind} for c in session.scalars(select(Category).where(Category.user_id==user.id).order_by(Category.name))]

    @app.post("/api/categories",status_code=201)
    def add_category(data: CategoryInput,request: Request):
        try:
            with sessions.begin() as session:
                user=identity(request,session)
                if not data.name.strip():
                    raise HTTPException(400,"Name required")
                category=Category(user_id=user.id,name=data.name.strip(),kind=data.kind)
                session.add(category)
                session.flush()
                return {"id":category.id,"name":category.name,"kind":category.kind}
        except IntegrityError:
            raise HTTPException(409,"Category exists")

    def transaction_data(t):
        return {"id":t.id,"category_id":t.category_id,"occurred_on":t.occurred_on.isoformat(),"amount_kopecks":t.amount_kopecks,"note":t.note,"external_id":t.external_id}

    @app.get("/api/transactions")
    def transactions(request: Request):
        with sessions() as session:
            user=identity(request,session)
            return [transaction_data(t) for t in session.scalars(select(Transaction).where(Transaction.user_id==user.id).order_by(Transaction.occurred_on.desc(),Transaction.id.desc()).limit(500))]

    @app.post("/api/transactions",status_code=201)
    def add_transaction(data: TransactionInput,request: Request):
        try:
            amount=money_to_kopecks(data.amount)
            occurred=date.fromisoformat(data.occurred_on)
            with sessions.begin() as session:
                user=identity(request,session)
                own_category(session,user.id,data.category_id)
                transaction=Transaction(user_id=user.id,category_id=data.category_id,occurred_on=occurred,amount_kopecks=amount,note=data.note)
                session.add(transaction)
                session.flush()
                return transaction_data(transaction)
        except ValueError as error:
            raise HTTPException(400,str(error))

    @app.delete("/api/transactions/{transaction_id}")
    def delete_transaction(transaction_id: int,request: Request):
        with sessions.begin() as session:
            user=identity(request,session)
            transaction=session.scalar(select(Transaction).where(Transaction.id==transaction_id,Transaction.user_id==user.id))
            if not transaction:
                raise HTTPException(404,"Transaction not found")
            session.delete(transaction)
            return {"ok":True}

    @app.get("/api/analytics")
    def report(request: Request,start: date,end: date):
        try:
            with sessions() as session:
                user=identity(request,session)
                return analytics(session,user.id,start,end)
        except ValidationError as error:
            raise HTTPException(400,str(error))

    @app.get('/api/analytics/compare')
    def comparison(request: Request, start: date, end: date):
        try:
            with sessions() as session:
                user = identity(request, session)
                return compare_periods(session, user.id, start, end)
        except ValidationError as error:
            raise HTTPException(400, str(error))

    @app.get('/api/analytics/monthly.csv')
    def monthly_export(request: Request, start: date, end: date):
        import pandas as pd
        try:
            with sessions() as session:
                user = identity(request, session)
                monthly = analytics(session, user.id, start, end)['monthly']
            frame = pd.DataFrame(monthly, columns=['month', 'kind', 'amount_kopecks'])
            return Response(frame.to_csv(index=False), media_type='text/csv',
                            headers={'Content-Disposition': 'attachment; filename="ledger-monthly.csv"'})
        except ValidationError as error:
            raise HTTPException(400, str(error))

    @app.post("/api/import")
    def csv_import(data: CsvInput,request: Request):
        try:
            with sessions.begin() as session:
                user=identity(request,session)
                return import_csv(session,user.id,data.content)
        except ValidationError as error:
            raise HTTPException(400,str(error))
        except IntegrityError:
            raise HTTPException(409,"Concurrent import conflict; retry")

    @app.post("/api/budgets")
    def budget(data: BudgetInput,request: Request):
        try:
            date.fromisoformat(data.month+"-01")
            amount=money_to_kopecks(data.amount)
            with sessions.begin() as session:
                user=identity(request,session)
                category=own_category(session,user.id,data.category_id)
                if category.kind!="expense":
                    raise HTTPException(400,"Expense category required")
                row=session.scalar(select(Budget).where(Budget.user_id==user.id,Budget.category_id==category.id,Budget.month==data.month))
                if row:
                    row.limit_kopecks=amount
                else:
                    row=Budget(user_id=user.id,category_id=category.id,month=data.month,limit_kopecks=amount)
                    session.add(row)
                session.flush()
                return {"id":row.id,"limit_kopecks":row.limit_kopecks}
        except ValueError as error:
            raise HTTPException(400,str(error))

    @app.get("/api/budgets")
    def budgets(request: Request):
        from sqlalchemy import func
        from calendar import monthrange
        with sessions() as session:
            user=identity(request,session)
            result=[]
            for row in session.scalars(select(Budget).where(Budget.user_id==user.id)):
                first=date.fromisoformat(row.month+"-01")
                last=first.replace(day=monthrange(first.year,first.month)[1])
                spent=session.scalar(select(func.coalesce(func.sum(Transaction.amount_kopecks),0)).where(Transaction.user_id==user.id,Transaction.category_id==row.category_id,Transaction.occurred_on>=first,Transaction.occurred_on<=last))
                result.append({"id":row.id,"category_id":row.category_id,"month":row.month,"limit_kopecks":row.limit_kopecks,"spent_kopecks":spent})
            return result

    static = Path(__file__).resolve().parent.parent / "public"
    if static.exists():
        app.mount("/", StaticFiles(directory=static, html=True), name="storefront")
    return app
