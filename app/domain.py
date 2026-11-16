from datetime import date
from decimal import Decimal, InvalidOperation


class ValidationError(ValueError):
    pass


def money_to_kopecks(value: str) -> int:
    if not isinstance(value, str) or len(value)>30:
        raise ValidationError("Amount must be a decimal string")
    try:
        amount=Decimal(value.strip().replace(",","."))
        if not amount.is_finite() or amount<=0 or amount>Decimal("1000000000"):
            raise ValidationError("Amount outside supported range")
        cents=amount*100
        if cents!=cents.to_integral_value():
            raise ValidationError("Use at most two decimal places")
        return int(cents)
    except InvalidOperation as error:
        raise ValidationError("Invalid decimal amount") from error


def validate_period(start: date,end: date):
    if start>end or (end-start).days>3660:
        raise ValidationError("Use an ordered period of at most ten years")


def summarize(rows):
    income=expense=0
    for row in rows:
        value=row["amount_kopecks"]
        if type(value) is not int or value<=0:
            raise ValidationError("Positive integer kopecks required")
        if row["kind"]=="income":
            income+=value
        elif row["kind"]=="expense":
            expense+=value
        else:
            raise ValidationError("Unknown transaction kind")
    return {"income_kopecks":income,"expense_kopecks":expense,"balance_kopecks":income-expense,"savings_rate_percent":round((income-expense)/income*100,2) if income else None}
