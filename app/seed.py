import argparse
import getpass
from datetime import date
from sqlalchemy import select
from .database import database
from .models import User,Category,Transaction,Budget
from .security import hash_password


def seed_demo(session,email,password):
    if session.scalar(select(User).where(User.email==email)):
        raise ValueError("Account exists; demo will not change it")
    user=User(email=email,name="Алексей Морозов",password_hash=hash_password(password))
    session.add(user)
    session.flush()
    categories={}
    for name,kind in [("Зарплата","income"),("Подработка","income"),("Продукты","expense"),("Дом","expense"),("Транспорт","expense"),("Досуг","expense")]:
        category=Category(user_id=user.id,name=name,kind=kind)
        session.add(category)
        session.flush()
        categories[name]=category.id
    year=date.today().year
    for month in range(1,12):
        for name,amount,day,note in [("Зарплата",9500000,5,"Зарплата"),("Подработка",(10000+month*900)*100,15,"Проектная работа"),("Продукты",(18000+month*300)*100,8,"Покупки продуктов"),("Дом",2800000,10,"Жильё и коммунальные услуги"),("Транспорт",420000,12,"Поездки"),("Досуг",(5000+month*200)*100,20,"Отдых и встречи")]:
            session.add(Transaction(user_id=user.id,category_id=categories[name],occurred_on=date(year,month,day),amount_kopecks=amount,note=note))
    for name,limit in [("Продукты",2500000),("Досуг",800000)]:
        session.add(Budget(user_id=user.id,category_id=categories[name],month=f"{year}-{date.today().month:02d}",limit_kopecks=limit))
    return user


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--email",required=True)
    args=parser.parse_args()
    email=args.email.strip().lower()
    if "@" not in email or len(email)>254:
        raise ValueError("Invalid email")
    password=getpass.getpass("Demo account password: ")
    engine,sessions=database()
    try:
        with sessions.begin() as session:
            seed_demo(session,email,password)
        print("Fictional demo data created; no bank connection used")
    finally:
        engine.dispose()
