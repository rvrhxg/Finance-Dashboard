"""Bounded aggregate results: transactions stay in the database."""
from datetime import date
from sqlalchemy import String, cast, func, select
from .models import Category, Transaction
from .domain import summarize, validate_period, ValidationError
from .periods import previous_period, percentage_change


def analytics(session, user_id, start: date, end: date):
    validate_period(start, end)
    conditions = [Transaction.user_id == user_id, Category.user_id == user_id,
                  Transaction.occurred_on >= start, Transaction.occurred_on <= end]
    month = func.substr(cast(Transaction.occurred_on, String), 1, 7)
    grouped = session.execute(select(month, Category.kind, func.sum(Transaction.amount_kopecks), func.count())
                              .join(Category, Category.id == Transaction.category_id)
                              .where(*conditions).group_by(month, Category.kind).order_by(month, Category.kind)).all()
    monthly = [{'month': m, 'kind': kind, 'amount_kopecks': int(amount)} for m, kind, amount, _ in grouped]
    categories = session.execute(select(Category.name, func.sum(Transaction.amount_kopecks))
                                 .join(Transaction, Transaction.category_id == Category.id)
                                 .where(*conditions, Category.kind == 'expense').group_by(Category.name)
                                 .order_by(func.sum(Transaction.amount_kopecks).desc(), Category.name)).all()
    return {**summarize(monthly), 'monthly': monthly,
            'categories': [{'category': name, 'amount_kopecks': int(amount)} for name, amount in categories],
            'count': sum(count for _, _, _, count in grouped)}


def compare_periods(session, user_id, start: date, end: date):
    try:
        prior_start, prior_end = previous_period(start, end)
    except ValueError as error:
        raise ValidationError(str(error)) from error
    current = analytics(session, user_id, start, end)
    previous = analytics(session, user_id, prior_start, prior_end)
    return {'current': current, 'previous': previous,
            'current_period': {'start': start.isoformat(), 'end': end.isoformat()},
            'previous_period': {'start': prior_start.isoformat(), 'end': prior_end.isoformat()},
            'changes': {key: {'delta_kopecks': current[key] - previous[key],
                              'percent': percentage_change(current[key], previous[key])}
                        for key in ('income_kopecks', 'expense_kopecks', 'balance_kopecks')}}
