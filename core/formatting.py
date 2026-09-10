import math

def number(value, digits=0):
    return "—" if not math.isfinite(float(value)) else f"{value:,.{digits}f}"

def compact(value):
    if abs(value) >= 1e6:
        return f"{value / 1e6:,.2f}m"
    if abs(value) >= 1e3:
        return f"{value / 1e3:,.1f}k"
    return number(value, 2)
