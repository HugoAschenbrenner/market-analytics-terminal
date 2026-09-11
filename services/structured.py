"""One contract definition for book marks, scenarios and the product workspace."""
from engines.structured_products_valuation_engine import AutocallableValuationInputs
from engines.structured_risk_engine import value_note,bump_risk


def contract_for(row,market,contracts):
    key=row['id'];saved=contracts.get(key,{})
    default_underlyings=(row['underlying'],'QQQ') if row['underlying']!='QQQ' else ('QQQ','SPY')
    underlyings=tuple(saved.get('underlyings',default_underlyings))
    baseline={'SPY':550.,'QQQ':475.,'SX5E':5000.}
    fixings=tuple(saved.get('fixings',[baseline.get(k,market.spots.get(k,100.)) for k in underlyings]))
    if not all(k in market.spots for k in underlyings):raise ValueError('book.underlying')
    ratios=tuple(market.spots[k]/f for k,f in zip(underlyings,fixings))
    inputs=AutocallableValuationInputs(notional=100.,initial_spots=fixings,volatilities=tuple(saved.get('volatilities',[row['volatility']]*len(underlyings))),
        correlation=saved.get('correlation',.3),maturity_years=row['maturity'],observations_per_year=saved.get('frequency',4),
        autocall_barrier=saved.get('autocall',1.),coupon_barrier=saved.get('coupon_barrier',.7),protection_barrier=saved.get('protection',.6),
        coupon_rate=saved.get('coupon',.08),risk_free_rate=market.rates[row['currency']],simulations=saved.get('simulations',3000),seed=42)
    return inputs,ratios,saved.get('product','Athena'),saved.get('memory',True),underlyings


def note_value(row,market,contracts):
    inputs,ratios,product,memory,underlyings=contract_for(row,market,contracts)
    return value_note(inputs,ratios,product,memory),bump_risk(inputs,ratios,product,memory)
