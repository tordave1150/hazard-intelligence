"""Shared conservative rolling request budget; reserve before every HTTP attempt.

One short best-match request with <=10 variables is charged once per coordinate.
The bounded CAS ledger covers both daily/hourly jobs, including failed attempts.
It is not a guarantee against shared-egress/provider-side limits.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import time
from pymongo.errors import DuplicateKeyError

LIMITS = ((60, 500), (3600, 4500), (86400, 9000))
active_budget = ContextVar('open_meteo_budget', default=None)


class BudgetExceeded(RuntimeError):
    pass


class RequestBudget:
    def __init__(self, db=None, clock=time.time):
        self.store = db['provider_request_budget'] if db is not None else None
        self.clock = clock
        self.local = {'events': [], 'revision': 0}

    def reserve(self, units):
        if type(units) is not int or not 1 <= units <= 25:
            raise BudgetExceeded('INVALID_BUDGET_WEIGHT')
        now = int(self.clock())
        for _ in range(8):
            row = self.store.find_one({'_id': 'open_meteo'}) if self.store is not None else self.local
            if row is None:
                try:
                    self.store.insert_one({'_id': 'open_meteo', 'events': [], 'revision': 0})
                except DuplicateKeyError:
                    pass
                continue
            events = row.get('events')
            if not isinstance(events, list) or len(events) > 9000 or type(row.get('revision')) is not int:
                raise BudgetExceeded('INVALID_BUDGET_LEDGER')
            if any(not isinstance(e, dict) or set(e) != {'at', 'units'} or type(e['at']) is not int
                   or type(e['units']) is not int or not 1 <= e['units'] <= 25 or e['at'] > now + 5 for e in events):
                raise BudgetExceeded('INVALID_BUDGET_LEDGER')
            events = [e for e in events if e['at'] >= now - 86400]
            for window, limit in LIMITS:
                if sum(e['units'] for e in events if e['at'] >= now - window) + units > limit:
                    raise BudgetExceeded('PROVIDER_REQUEST_BUDGET_EXHAUSTED')
            updated = {'events': [*events, {'at': now, 'units': units}], 'revision': row['revision'] + 1}
            if self.store is None:
                self.local = updated
                return
            if self.store.update_one({'_id': 'open_meteo', 'revision': row['revision']}, {'$set': updated}).modified_count:
                return
        raise BudgetExceeded('BUDGET_RESERVATION_CONTENTION')


@contextmanager
def request_budget(db=None, clock=time.time):
    token = active_budget.set(RequestBudget(db, clock))
    try:
        yield
    finally:
        active_budget.reset(token)
