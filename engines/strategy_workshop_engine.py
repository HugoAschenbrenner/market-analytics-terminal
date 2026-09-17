"""Connect the audited expiry-payoff engine to optional BSM premiums/Greeks."""
from dataclasses import asdict

import numpy as np

from engines.options_payoff_engine import (
    build_strategy_legs, calculate_strategy_payoff_table,
    calculate_exact_breakevens, strategy_risk_profile,
)
from engines.options_pricing_engine import black_scholes_price, black_scholes_greeks


def strategy_workshop(strategy, spot, strike, strike_2, maturity, rate, volatility,
                      units=1., premiums=None):
    """One expiry, q=0, no funding; units are economic units, not contracts.

    Manual premiums change entry cost/P&L only. Greeks always use the supplied
    BSM parameters and long/short quantities, including any underlying leg.
    """
    skeleton = build_strategy_legs(strategy, spot, strike, 0., strike_2, 0., units)
    options = [leg for leg in skeleton if leg.instrument != 'underlying']
    model_premiums = [black_scholes_price(leg.instrument, spot, leg.strike, maturity, rate, volatility) for leg in options]
    chosen = model_premiums if premiums is None else list(premiums)
    if len(chosen) != len(options):
        raise ValueError('workshop.premium_count')
    p1, p2 = chosen[0], chosen[1] if len(chosen) > 1 else None
    legs = build_strategy_legs(strategy, spot, strike, p1, strike_2, p2, units)
    profile = strategy_risk_profile(strategy, spot, strike, p1, strike_2, p2, units)
    strikes = [leg.strike for leg in options]
    upper = max(1.6 * spot, 1.2 * max(strikes))
    prices = np.unique(np.r_[np.linspace(0., upper, 161), strikes])
    totals = dict(delta=0., gamma=0., vega_1pct=0.)
    debit = 0.
    for leg in legs:
        signed = leg.quantity * (1 if leg.position == 'long' else -1)
        if leg.instrument == 'underlying':
            debit += signed * spot
            totals['delta'] += signed
        else:
            debit += signed * leg.premium
            greeks = black_scholes_greeks(leg.instrument, spot, leg.strike, maturity, rate, volatility)
            for key in totals:
                totals[key] += signed * greeks[key]
    # Detect flat zero-P&L regions so a free option isn't presented as having
    # only isolated break-even points.
    knots = sorted({0., *strikes})
    zero_intervals = []
    for lo, hi in zip(knots, knots[1:] + [np.inf]):
        probe = lo + max(spot, 1.) if np.isinf(hi) else hi
        pnl = calculate_strategy_payoff_table(legs, [lo, probe]).pnl
        if np.all(np.abs(pnl) < 1e-9):
            zero_intervals.append((lo, hi))
    return dict(legs=legs, leg_records=[asdict(leg) for leg in legs],
                model_premiums=model_premiums, net_debit=debit, greeks=totals,
                table=calculate_strategy_payoff_table(legs, prices),
                breakevens=calculate_exact_breakevens(legs),
                zero_intervals=zero_intervals, risk_profile=profile)
