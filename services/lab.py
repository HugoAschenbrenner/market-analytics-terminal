"""Per-session lab inputs, shared by EQD, curves, dashboard and export."""
from dataclasses import dataclass, field, replace
from datetime import date
import numpy as np
import pandas as pd
import streamlit as st
from engines.option_chain_engine import sample_option_chain, analyze_option_chain, smile_metrics, term_structure
from engines.equity_derivatives_engine import OptionPosition,position_analytics,option_scenario,scenario_matrix,delta_hedge
from engines.scenario_engine import MarketScenario
from engines.rates_tools_engine import sample_curve_table,curve_from_table,zero_curve_table,cashflow_curve_risk,curve_spreads


@dataclass
class LabState:
    chain: pd.DataFrame = field(default_factory=sample_option_chain)
    as_of: date = date(2026,9,9)
    mode: str = 'iv'
    source: str = 'SYNTHETIC'
    currency: str = 'USD'
    selected_maturity: str = ''
    position: OptionPosition = field(default_factory=OptionPosition)
    position_source: str = 'Independent synthetic example'
    scenario: MarketScenario = field(default_factory=lambda:MarketScenario('Custom',equity=-.05,volatility=.03,rate_bp=25))
    hedge_scenario: MarketScenario = field(default_factory=lambda:MarketScenario('Instantaneous hedge',equity=-.05,volatility=.03))
    matrix_spots: tuple = (-.15,-.10,-.05,0.,.05,.10,.15)
    matrix_vol_points: tuple = (-10.,-5.,0.,5.,10.)
    curve: pd.DataFrame = field(default_factory=sample_curve_table)
    curve_source: str = 'SYNTHETIC'
    curve_maturity: int = 10
    curve_coupon: float = .035
    curve_notional: float = 100000.
    risk_tables: dict = field(default_factory=dict)
    risk_source: str = ''


def get_lab() -> LabState:
    if 'analytics_lab' not in st.session_state:
        st.session_state.analytics_lab=LabState()
    return st.session_state.analytics_lab


@st.cache_data(show_spinner=False,max_entries=12)
def chain_analysis(data: pd.DataFrame,as_of: date,mode: str) -> dict:
    return analyze_option_chain(data,as_of,mode)


def option_outputs(lab: LabState) -> dict:
    chain=chain_analysis(lab.chain,lab.as_of,lab.mode)
    if chain['chain'].empty:
        raise ValueError('The option chain contains no valid rows.')
    maturity=lab.selected_maturity if lab.selected_maturity in chain['chain'].maturity.values else chain['chain'].maturity.iloc[0]
    slice_=chain['chain'].query('maturity == @maturity')
    return dict(chain=chain,smile=smile_metrics(slice_),term=term_structure(chain['chain']),
        maturity=maturity,position=position_analytics(lab.position),scenario=option_scenario(lab.position,lab.scenario),
        matrix=scenario_matrix(lab.position,lab.matrix_spots,lab.matrix_vol_points),hedge=delta_hedge(lab.position,lab.hedge_scenario))


def curve_outputs(lab: LabState) -> dict:
    curve=curve_from_table(lab.curve)
    times=np.arange(.5,lab.curve_maturity+.5,.5)
    flows=np.full(len(times),lab.curve_notional*lab.curve_coupon/2);flows[-1]+=lab.curve_notional
    result=cashflow_curve_risk(times,flows,curve,lab.scenario)
    table=zero_curve_table(curve)
    grid=np.unique(np.r_[np.linspace(curve.tenors[0],curve.tenors[-1],80),curve.tenors,
        [tenor for tenor,_ in lab.scenario.curve_twist]])
    shock=curve.shocked(lab.scenario)
    comparison=pd.DataFrame({'tenor':grid,'base_rate':curve.zero(grid),'shocked_rate':shock.zero(grid),
                             'change_bp':lab.scenario.rate_at(grid)})
    return dict(curve=curve,table=table,comparison=comparison,spreads=curve_spreads(curve),risk=result)
