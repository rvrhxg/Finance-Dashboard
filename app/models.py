from datetime import date
from sqlalchemy import BigInteger,CheckConstraint,Date,ForeignKey,String,UniqueConstraint
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(254),unique=True)
    name:Mapped[str]=mapped_column(String(100))
    password_hash:Mapped[str]=mapped_column(String(256))


class LoginSession(Base):
    __tablename__="sessions"
    token_hash:Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"))
    expires_at:Mapped[int]


class Category(Base):
    __tablename__="categories"
    __table_args__=(UniqueConstraint("user_id","name","kind"),CheckConstraint("kind IN ('income','expense')"))
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    name:Mapped[str]=mapped_column(String(80))
    kind:Mapped[str]=mapped_column(String(10))


class Transaction(Base):
    __tablename__="transactions"
    __table_args__=(UniqueConstraint("user_id","external_id"),CheckConstraint("amount_kopecks>0"))
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    category_id:Mapped[int]=mapped_column(ForeignKey("categories.id"))
    occurred_on:Mapped[date]=mapped_column(Date,index=True)
    amount_kopecks:Mapped[int]=mapped_column(BigInteger)
    note:Mapped[str]=mapped_column(String(500),default="")
    external_id:Mapped[str|None]=mapped_column(String(100),nullable=True)


class Budget(Base):
    __tablename__="budgets"
    __table_args__=(UniqueConstraint("user_id","category_id","month"),CheckConstraint("limit_kopecks>0"))
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    category_id:Mapped[int]=mapped_column(ForeignKey("categories.id"))
    month:Mapped[str]=mapped_column(String(7))
    limit_kopecks:Mapped[int]=mapped_column(BigInteger)
