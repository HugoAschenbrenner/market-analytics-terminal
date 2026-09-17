"""European, continuously monitored, zero-rebate barriers and certificates.

Prices are per underlying unit, with continuous rates/dividends. The barrier
formula integrates the absorbing (killed) lognormal transition density. This
independent reflection-principle implementation avoids eight separate case
formulas. Knock-in/out parity uses the same European vanilla convention.
"""
from math import exp, expm1, isfinite, log, sqrt

import numpy as np
from scipy.special import log_ndtr

from engines.options_pricing_engine import black_scholes_price


def _validate(spot, strike, barrier, maturity, rate, volatility, dividend):
    values = (spot, strike, barrier, maturity, rate, volatility, dividend)
    if not all(isfinite(v) for v in values):
        raise ValueError("workshop.finite")
    if min(spot, strike, barrier) <= 0 or min(maturity, volatility) < 0:
        raise ValueError("workshop.positive")
    # Keep exponential discounting representable rather than returning infinity.
    if max(abs(rate * maturity), abs(dividend * maturity)) > 500:
        raise ValueError("workshop.range")


def _log_difference(a, b):
    """log(exp(a) - exp(b)), retaining precision in close normal tails."""
    if b == -np.inf:
        return a
    if a <= b:
        return -np.inf
    return a + log(-expm1(b - a))


def _log_probability(lo, hi):
    if lo >= hi:
        return -np.inf
    if lo >= 0:
        return _log_difference(float(log_ndtr(-lo)), float(log_ndtr(-hi)))
    return _log_difference(float(log_ndtr(hi)), float(log_ndtr(lo)))


def _surviving_moment(power, lo, hi, distance, drift, variance, maturity):
    """E[exp(power * Z_T); lo < Z_T < hi, min Z > 0]."""
    sd = sqrt(variance)

    def moment(mean):
        shifted = mean + power * variance
        return (power * mean + .5 * power * power * variance
                + _log_probability((lo - shifted) / sd, (hi - shifted) / sd))

    direct = moment(distance + drift * maturity)
    reflected = (moment(-distance + drift * maturity)
                 - 2 * drift * distance * maturity / variance)
    return exp(_log_difference(direct, reflected))


def barrier_snapshot(option_type, direction, activation, spot, strike, barrier,
                     maturity, rate, volatility, dividend=0., touched=False):
    """All eight single-barrier variants, including expiry and known touch.

    A touch at equality counts; historical touch is irreversible even if spot
    subsequently recovers. ``touch_probability`` includes already observed
    touches and is risk-neutral, never a real-world forecast.
    """
    if option_type not in ("Call", "Put") or direction not in ("down", "up") or activation not in ("in", "out"):
        raise ValueError("workshop.variant")
    _validate(spot, strike, barrier, maturity, rate, volatility, dividend)
    sign = 1 if direction == "down" else -1
    hit = bool(touched or sign * (spot - barrier) <= 0)
    phi = 1 if option_type == "Call" else -1
    if maturity == 0 or volatility == 0:
        terminal = spot * exp((rate - dividend) * maturity)
        hit = hit or sign * (terminal - barrier) <= 0
        vanilla = exp(-rate * maturity) * max(phi * (terminal - strike), 0.)
        out = 0. if hit else vanilla
        probability = float(hit)
    else:
        vanilla = black_scholes_price(option_type, spot, strike, maturity, rate, volatility, dividend)
        if hit:
            out, probability = 0., 1.
        else:
            distance = sign * log(spot / barrier)
            drift = sign * (rate - dividend - .5 * volatility ** 2)
            variance = volatility ** 2 * maturity
            cutoff = sign * log(strike / barrier)
            if phi * sign > 0:
                lo, hi = max(0., cutoff), np.inf
            else:
                lo, hi = 0., max(0., cutoff)
            args = (lo, hi, distance, drift, variance, maturity)
            stock = barrier * _surviving_moment(sign, *args)
            cash = strike * _surviving_moment(0., *args)
            raw = exp(-rate * maturity) * phi * (stock - cash)
            tolerance = 1e-9 * max(1., spot, strike)
            if not isfinite(raw) or raw < -tolerance or raw > vanilla + tolerance:
                raise ValueError("workshop.numerical")
            out = min(vanilla, max(0., raw))
            survival = _surviving_moment(0., 0., np.inf, distance, drift, variance, maturity)
            probability = min(1., max(0., 1 - survival))
    knock_in = vanilla - out
    return dict(price=knock_in if activation == "in" else out,
                knock_in=knock_in, knock_out=out, vanilla=vanilla,
                touch_probability=probability, touched=bool(touched or sign * (spot - barrier) <= 0))


def _certificate_terms(kind, level, barrier, cap):
    if kind not in ("discount", "bonus", "capped_bonus"):
        raise ValueError("workshop.variant")
    if not all(isfinite(x) and x > 0 for x in (level, barrier, cap)):
        raise ValueError("workshop.positive")
    if kind != "discount" and barrier >= level:
        raise ValueError("workshop.barrier_below_bonus")
    if kind == "capped_bonus" and cap < level:
        raise ValueError("workshop.cap_above_bonus")


def certificate_payoff(kind, terminal, level=110., barrier=70., cap=120., touched=False):
    """Cash redemption per unit, not P&L; touched includes the entire life."""
    _certificate_terms(kind, level, barrier, cap)
    terminal = np.asarray(terminal, dtype=float)
    if not np.all(np.isfinite(terminal)) or np.any(terminal < 0):
        raise ValueError("workshop.positive")
    if kind == "discount":
        return np.minimum(terminal, cap)
    hit = np.asarray(touched, dtype=bool) | (terminal <= barrier)
    result = np.where(hit, terminal, np.maximum(terminal, level))
    return np.minimum(result, cap) if kind == "capped_bonus" else result


def certificate_snapshot(kind, spot, maturity, rate, volatility, dividend=0.,
                         level=110., barrier=70., cap=120., touched=False):
    """Replication for a claim delivering no interim dividend/coupon.

    Discount = prepaid underlying - call(cap).
    Bonus = prepaid underlying + down-and-out put(bonus, barrier).
    Capped bonus = bonus - call(cap), with cap >= bonus > barrier.
    No issuer credit spread, fees, taxes, bid/ask or early sale guarantee.
    """
    _certificate_terms(kind, level, barrier, cap)
    _validate(spot, level, barrier, maturity, rate, volatility, dividend)
    components = {"prepaid": spot * exp(-dividend * maturity)}
    touch_probability = None
    hit = bool(touched or spot <= barrier)
    if kind != "discount":
        put = barrier_snapshot("Put", "down", "out", spot, level, barrier,
                               maturity, rate, volatility, dividend, touched)
        components["bonus_put"] = put["price"]
        touch_probability = put["touch_probability"]
    if kind != "bonus":
        if maturity == 0 or volatility == 0:
            call = exp(-rate * maturity) * max(spot * exp((rate - dividend) * maturity) - cap, 0.)
        else:
            call = black_scholes_price("Call", spot, cap, maturity, rate, volatility, dividend)
        components["short_cap"] = -call
    return dict(price=sum(components.values()), components=components,
                touch_probability=touch_probability, touched=hit)
