from datetime import timedelta
from engines.repo_engine import calculate_contractual_variation_margin,calculate_refinancing_haircut_stress


def repo_margin(state,collateral,shock=0.):
    b=state.book;terms=b.financing_terms
    return calculate_contractual_variation_margin(b.repo_cash,b.repo_rate,state.valuation_date,state.valuation_date+timedelta(days=b.repo_days),state.valuation_date+timedelta(days=min(terms.get('elapsed',0),b.repo_days)),terms.get('basis',360),collateral*(1+shock),b.repo_haircut,'Cash borrower / repo',threshold=terms.get('threshold',0.),minimum_transfer_amount=terms.get('mta',0.),rounding_increment=terms.get('rounding',1.),currency=b.base_currency)


def repo_stress(state,collateral,haircut,shock):
    r=calculate_refinancing_haircut_stress(collateral,state.book.repo_haircut,haircut,shock,state.book.base_currency)
    # The audited report includes loss of funding capacity. The actual book may
    # borrow less than that capacity; its cash shortfall is shown separately.
    shortfall=max(0.,state.book.repo_cash-r.stressed_refinancing_funding_capacity)
    return r,shortfall
