"""All rows validated before mutation; caller owns the surrounding transaction."""
import csv
import io
from datetime import date
from sqlalchemy import select
from .models import Category,Transaction
from .domain import ValidationError,money_to_kopecks


def import_csv(session,user_id,content):
    if not isinstance(content,str) or len(content.encode())>200000:
        raise ValidationError("CSV too large")
    reader=csv.DictReader(io.StringIO(content))
    required={"external_id","date","kind","category","amount","note"}
    if not reader.fieldnames or len(reader.fieldnames)!=len(required) or set(reader.fieldnames)!=required:
        raise ValidationError("Expected external_id,date,kind,category,amount,note columns")
    prepared=[]
    seen=set()
    for row in reader:
        if len(prepared)>=1000:
            raise ValidationError("At most 1000 rows per import")
        if None in row or any(value is None for value in row.values()):
            raise ValidationError("Malformed CSV row")
        external=row["external_id"].strip()
        category=row["category"].strip()
        if not 1<=len(external)<=100 or external in seen:
            raise ValidationError("Missing or duplicate external_id")
        if row["kind"] not in {"income","expense"} or not 1<=len(category)<=80 or len(row["note"])>500:
            raise ValidationError("Invalid category, kind or note")
        try:
            occurred=date.fromisoformat(row["date"])
        except ValueError as error:
            raise ValidationError("Invalid date") from error
        prepared.append((external,occurred,row["kind"],category,money_to_kopecks(row["amount"]),row["note"]))
        seen.add(external)
    added=skipped=0
    for external,occurred,kind,name,amount,note in prepared:
        previous=session.scalar(select(Transaction).where(Transaction.user_id==user_id,Transaction.external_id==external))
        if previous:
            old_category=session.get(Category,previous.category_id)
            if (previous.occurred_on,old_category.kind,old_category.name,previous.amount_kopecks,previous.note)!=(occurred,kind,name,amount,note):
                raise ValidationError("external_id already used with different contents")
            skipped+=1
            continue
        category=session.scalar(select(Category).where(Category.user_id==user_id,Category.kind==kind,Category.name==name))
        if not category:
            category=Category(user_id=user_id,name=name,kind=kind)
            session.add(category)
            session.flush()
        session.add(Transaction(user_id=user_id,category_id=category.id,external_id=external,occurred_on=occurred,amount_kopecks=amount,note=note))
        session.flush()
        added+=1
    return {"added":added,"skipped":skipped}
