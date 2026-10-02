"""Fixed offline illustrations assembled from the existing validated engines."""
from dataclasses import replace
from datetime import date
import numpy as np
import pandas as pd
from core.models import PositionBook, TerminalState
from core.state import position,validate_book
from engines.equity_derivatives_engine import OptionPosition,position_analytics,option_scenario,delta_hedge
from engines.scenario_engine import MarketScenario
from engines.desk_scenario_engine import DeskScenario,evaluate_scenario
from engines.structured_risk_engine import cashflows,value_note,bump_risk
from services.book_risk import book_risk
from services.structured_lab import demo_structured_lab
from services.structured import contract_for

DEMO_DATE=date(2026,9,9)


def collar_demo():
    stock=position('shares','SPY','Equity',1000,100,underlying='SPY',mark_mode='Market')
    put=position('protective-put','SPY-P90','Option',10,1,underlying='SPY',strike=90,maturity=.5,volatility=.25,option_type='Put',multiplier=100)
    call=position('covered-call','SPY-C110','Option',-10,1,underlying='SPY',strike=110,maturity=.5,volatility=.22,option_type='Call',multiplier=100)
    before=TerminalState(PositionBook(validate_book(pd.DataFrame([stock]))),valuation_date=DEMO_DATE)
    before.market.spots['SPY']=100.;before.market.rates['USD']=.03;before.market.mode='demo'
    after=replace(before,book=PositionBook(validate_book(pd.DataFrame([stock,put,call]))))
    b,a=book_risk(before),book_risk(after)
    premium=float(a['marks'].query("asset_class=='Option'").market_value.sum())
    spots=np.linspace(40,160,121)
    payoff=pd.DataFrame(dict(spot=spots,unprotected=1000*spots,collar=1000*(spots+np.maximum(90-spots,0)-np.maximum(spots-110,0))))
    shocks=[-.3,-.1,0,.1,.3]
    scenarios=pd.DataFrame([dict(spot_shock=x,unprotected=evaluate_scenario(b['marks'],before.market,before.book,DeskScenario('spot',equity=x))['pnl'],
                                collar=evaluate_scenario(a['marks'],after.market,after.book,DeskScenario('spot',equity=x))['pnl']) for x in shocks])
    return dict(before=b,after=a,premium=premium,payoff=payoff,scenarios=scenarios,state=after)


def eqd_demo():
    p=OptionPosition(spot=100,strike=100,maturity=.5,rate=.03,volatility=.25,dividend=0,quantity=10,multiplier=100)
    scenario=MarketScenario('Spot −8% / volatility +4 points',equity=-.08,volatility=.04)
    after=replace(p,spot=p.spot*(1+scenario.equity),volatility=p.volatility+scenario.volatility)
    return dict(position=p,scenario=scenario,greeks=position_analytics(p),after=position_analytics(after),
                pnl=option_scenario(p,scenario),hedge=delta_hedge(p,scenario))


def autocallable_demo():
    state=demo_structured_lab();row=state.book.positions.iloc[0].to_dict()
    i,ratios,kind,memory,names=contract_for(row,state.market,state.book.structured_terms)
    result=value_note(i,ratios,kind,memory)
    # Deliberately supplied contractual observations, not observations from a feed.
    paths=np.ones((3,len(result['times']),3))*.85
    paths[0,:4,:]=np.array([.92,.65,.80,1.02])[:,None]  # coupon memory, then call at year one
    paths[1,:,:]=.85  # survives to maturity, coupons pay, capital protected
    paths[2,:,:]=.65;paths[2,-1,:]=(.8,.45,.7)  # one severe name sets worst-of loss
    flows,timeline=cashflows(paths,i,kind,memory,capture_timeline=True)
    return dict(state=state,inputs=i,names=names,result=result,risk=bump_risk(i,ratios,kind,memory),paths=paths,flows=flows,timeline=timeline)
