import pandas as pd
import pytest
from core.state import demo_book,validate_book,position
from core.models import TerminalState
from services.analytics import marked_positions,nav


def test_market_equity_and_options_share_underlying_and_book_override_is_explicit():
    s=TerminalState(demo_book());s.market.spots['SPY']=600
    m=marked_positions(s).set_index('id')
    assert m.loc['spy','mark']==m.loc['spy-put','spot']==600
    s.book.positions.loc[s.book.positions.id=='spy','mark_mode']='Book'
    assert marked_positions(s).set_index('id').loc['spy','mark']==550


def test_bond_and_cash_units_cannot_misstate_value():
    bond=pd.DataFrame([position('b','B','Bond',100,100,multiplier=1)])
    with pytest.raises(ValueError,match='bond_multiplier'):validate_book(bond)
    assert validate_book(bond.drop(columns='multiplier')).iloc[0].multiplier==.01
    with pytest.raises(ValueError,match='cash_unit'):validate_book(pd.DataFrame([position('c','USD','Cash',100,2)]))


def test_demo_repo_cash_proceeds_are_booked_and_greek_units_are_comparable():
    s=TerminalState(demo_book());m=marked_positions(s)
    assert s.book.repo_cash==150000
    assert nav(s,m)==pytest.approx(m.market_value.sum()-150000)
    row=m.query("asset_class=='Option'").iloc[0]
    assert row.gamma_cash_1pct==pytest.approx(.5*row.gamma*(row.spot*.01)**2)
