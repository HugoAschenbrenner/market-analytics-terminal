"""Explicit market units: returns in %, yield moves in basis points."""
import math


def finite(value):
    try:
        return value is not None and math.isfinite(float(value))
    except (ValueError,TypeError):
        return False


def number(value, digits=2, signed=False):
    return f'{float(value):+,.{digits}f}' if finite(value) and signed else f'{float(value):,.{digits}f}' if finite(value) else '—'


def level(security, value):
    if security.unit=='yield':return number(value,2)+'%' if finite(value) else '—'
    digits=3 if security.currency=='JPY' and security.unit=='fx' else 4 if security.unit=='fx' else 2
    return number(value,digits)


def move(security, quote):
    if quote is None:return '—'
    if security.unit=='yield':return number(None if quote.change is None else quote.change*100,1,True)+' bp' if quote.change is not None else '—'
    return number(quote.change_pct,2,True)+'%' if quote.change_pct is not None else '—'


def large(value):
    if not finite(value):return '—'
    for divisor,suffix in [(1e12,'T'),(1e9,'B'),(1e6,'M'),(1e3,'K')]:
        if abs(value)>=divisor:return f'{value/divisor:,.2f}{suffix}'
    return number(value)
