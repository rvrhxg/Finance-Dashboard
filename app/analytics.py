from datetime import date
import pandas as pd
from sqlalchemy import select
from .models import Category,Transaction
from .domain import summarize,validate_period


def analytics(session,user_id,start:date,end:date):
    validate_period(start,end)
    records=[{"date":t.occurred_on.isoformat(),"category":c.name,"kind":c.kind,"amount_kopecks":t.amount_kopecks} for t,c in session.execute(select(Transaction,Category).join(Category,Category.id==Transaction.category_id).where(Transaction.user_id==user_id,Category.user_id==user_id,Transaction.occurred_on>=start,Transaction.occurred_on<=end))]
    result=summarize(records)
    if not records:
        return {**result,"monthly":[],"categories":[],"count":0}
    frame=pd.DataFrame(records)
    frame["month"]=frame["date"].str.slice(0,7)
    # Integer input and integer sums; floats are only presentation percentages.
    monthly=frame.groupby(["month","kind"],sort=True)["amount_kopecks"].sum().reset_index()
    categories=frame[frame["kind"]=="expense"].groupby("category")["amount_kopecks"].sum().sort_values(ascending=False).reset_index()
    return {**result,"monthly":monthly.to_dict(orient="records"),"categories":categories.to_dict(orient="records"),"count":len(records)}
