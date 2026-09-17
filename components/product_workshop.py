"""Standalone educational products; never write into the shared position book."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.kpi_card import kpis
from core.charting import chart
from core.i18n import t, error_message
from engines.barrier_certificate_engine import barrier_snapshot, certificate_snapshot, certificate_payoff
from engines.options_payoff_engine import SUPPORTED_STRATEGIES, option_leg_pnl
from engines.strategy_workshop_engine import strategy_workshop


def _inputs(prefix, dividends=True):
    with st.container(border=True):
        st.markdown('**' + t('workshop.inputs') + '**')
        a, b, c = st.columns(3)
        spot = a.number_input(t('workshop.spot'), .01, 100000., 100., key=prefix+'_spot')
        maturity = b.number_input(t('maturity'), .01, 10., 1., step=.1, key=prefix+'_time')
        volatility = c.number_input(t('vol'), .1, 150., 30., step=1., key=prefix+'_vol') / 100
        a, b = st.columns(2)
        rate = a.number_input(t('rate'), -10., 30., 5., step=.25, key=prefix+'_rate') / 100
        dividend = b.number_input(t('workshop.dividend'), 0., 30., 0., step=.25, key=prefix+'_dividend') / 100 if dividends else 0.
        st.caption(t('workshop.parameters'))
    return dict(spot=spot, maturity=maturity, rate=rate, volatility=volatility, dividend=dividend)


def _num(key, label, value, column=st):
    return column.number_input(t(label), .01, 100000., float(value), key=key)


def _table(records):
    # Small read-only tables use semantic HTML so both custom themes apply.
    table=pd.DataFrame(records).to_html(index=False,border=0,escape=True,
        na_rep='—',float_format=lambda x:f'{x:,.4f}',classes='workshop-table')
    st.markdown('<div class="workshop-table-wrap">'+table+'</div>',unsafe_allow_html=True)


def render_strategies(state):
    lang = state.ui.language
    strategy = st.selectbox(t('workshop.strategy'), SUPPORTED_STRATEGIES,
                            index=SUPPORTED_STRATEGIES.index('Bull Call Spread'),
                            format_func=lambda x: t('workshop.strategy.'+x,lang), key='workshop_strategy')
    st.info(t('workshop.view.'+strategy))
    args = _inputs('strategy', dividends=False)
    spot = args['spot']
    two_strikes = strategy in ('Bull Call Spread','Bear Put Spread','Long Strangle','Collar')
    columns = st.columns(3 if two_strikes else 2)
    a, b, c = columns[0], columns[1], columns[-1]
    strike = _num('strategy_strike', 'workshop.strike', 100, a)
    second = _num('strategy_second_'+strategy, 'workshop.second_strike', 90 if strategy=='Bear Put Spread' else 110, b) if two_strikes else strike
    units = c.number_input(t('workshop.units'), 1., 10000., 1., step=1., key='strategy_units')
    if two_strikes and ((strategy=='Bear Put Spread' and second>=strike) or (strategy!='Bear Put Spread' and second<=strike)):
        st.warning(t('workshop.strike_order'))
        return
    st.caption(t('workshop.strategy_units',units=units))
    model_args = dict(strategy=strategy,spot=spot,strike=strike,strike_2=second,
                      maturity=args['maturity'],rate=args['rate'],volatility=args['volatility'],units=units)
    model = strategy_workshop(**model_args)
    mode = st.radio(t('workshop.premium_mode'), ['model','manual'],
                    format_func=lambda x:t('workshop.'+x,lang), horizontal=True, key='strategy_mode')
    result = model
    if mode == 'manual':
        premiums=[]
        for i, col in enumerate(st.columns(len(model['model_premiums']))):
            premiums.append(col.number_input(t('workshop.premium' if i==0 else 'workshop.premium2'),
                0.,1e9,float(model['model_premiums'][i]),format='%.4f',
                help=t('workshop.premium_help'),key=f'strategy_premium_{strategy}_{i}'))
        result = strategy_workshop(**model_args,premiums=premiums)
    profile = result['risk_profile']
    money = lambda x:t('workshop.unlimited') if isinstance(x,str) else f'{x:,.4f}'
    kpis([('workshop.debit',money(result['net_debit'])),('workshop.max_gain',money(profile['max_gain'])),('workshop.max_loss',money(profile['max_loss']))])
    st.caption(t('workshop.breakeven',values=', '.join(f'{x:,.4f}' for x in result['breakevens']) or t('workshop.no_roots')))
    if result['zero_intervals']:
        st.info(t('workshop.zero_region') + ' ' + '; '.join(f'[{a:g}, {b:g}]' for a,b in result['zero_intervals']))
    if profile['input_warning']:
        if mode=='model':
            st.info(t('workshop.carry_notice'))
        else:
            st.warning(t('workshop.premium_warning'))
    table = result['table']
    fig = go.Figure(go.Scatter(x=table.underlying_price,y=table.pnl,name=t('workshop.pnl'),line=dict(width=3)))
    rows=[]
    for i, leg in enumerate(result['legs']):
        name=t('workshop.stock') if leg.instrument=='underlying' else leg.instrument.title()
        signed=leg.quantity*(1 if leg.position=='long' else -1)
        label=f'{signed:+g} {name}' + (f' · K={leg.strike:g}' if leg.strike else '')
        fig.add_scatter(x=table.underlying_price,y=option_leg_pnl(table.underlying_price.to_numpy(),leg),name=label,line=dict(dash='dot',width=1))
        rows.append({t('workshop.instrument'):name,t('workshop.signed_units'):signed,
                     t('strike'):leg.strike,t('workshop.leg_premium'):None if leg.instrument=='underlying' else leg.premium})
    fig.add_hline(y=0,line_dash='dot')
    chart(fig.update_layout(xaxis_title=t('workshop.terminal'),yaxis_title=t('workshop.pnl')),key='strategy_payoff')
    st.caption(t('workshop.strategy_note'))
    with st.expander(t('workshop.legs')):
        _table(rows)
        st.caption(t('workshop.debit_help'))
    st.markdown('**'+t('workshop.greeks')+'**')
    g=result['greeks']
    kpis([('delta',g['delta']),('gamma',g['gamma']),('vega',g['vega_1pct'])])
    st.caption(t('workshop.greeks_note'))


def render_barriers(state):
    lang=state.ui.language
    a,b,c=st.columns(3)
    kind=a.selectbox(t('field.option_type'),['Call','Put'],key='barrier_kind')
    direction=b.selectbox(t('workshop.direction'),['down','up'],format_func=lambda x:t('workshop.'+x,lang),key='barrier_direction')
    activation=c.selectbox(t('workshop.activation'),['out','in'],format_func=lambda x:t('workshop.'+x,lang),key='barrier_activation')
    st.info(t('workshop.barrier_note'))
    args=_inputs('barrier')
    a,b=st.columns(2)
    strike=_num('barrier_strike','workshop.strike',100,a)
    barrier=_num('barrier_level_'+direction,'workshop.barrier',80 if direction=='down' else 120,b)
    touched=st.checkbox(t('workshop.touched'),help=t('workshop.history'),key='barrier_touched')
    value=barrier_snapshot(kind,direction,activation,strike=strike,barrier=barrier,touched=touched,**args)
    kpis([('workshop.price',f"{value['price']:.4f}"),('workshop.vanilla_value',f"{value['vanilla']:.4f}"),('workshop.touch_probability',f"{value['touch_probability']:.2%}")])
    st.caption(t('workshop.unit'))
    if value['touched']:
        st.info(t('workshop.touched_info'))
    st.caption(t('workshop.parity',ki=value['knock_in'],ko=value['knock_out'],vanilla=value['vanilla'],residual=value['knock_in']+value['knock_out']-value['vanilla']))
    spots=np.unique(np.r_[np.linspace(max(.01,.5*min(args['spot'],barrier)),1.5*max(args['spot'],barrier),100),barrier])
    # Preserve a touch already implied by the current spot across repricings.
    values=[barrier_snapshot(kind,direction,activation,strike=strike,barrier=barrier,
            touched=value['touched'],**(args|dict(spot=float(s)))) for s in spots]
    fig=go.Figure(go.Scatter(x=spots,y=[v['price'] for v in values],name=t('workshop.barriers')))
    fig.add_scatter(x=spots,y=[v['vanilla'] for v in values],name=t('vanilla'),line=dict(dash='dot'))
    fig.add_vline(x=barrier,line_dash='dash',name=t('workshop.barrier'),showlegend=True)
    chart(fig.update_layout(title=t('workshop.curve'),xaxis_title=t('workshop.spot'),yaxis_title=t('workshop.value_axis')),key='barrier_curve')
    st.caption(t('workshop.curve_note'))
    st.caption(t('workshop.probability_help'))


def render_certificates(state):
    lang=state.ui.language
    kind=st.selectbox(t('workshop.certificate'),['discount','bonus','capped_bonus'],
                      format_func=lambda x:t('workshop.'+x,lang),key='certificate_kind')
    st.info(t('workshop.discount_note' if kind=='discount' else 'workshop.bonus_note'))
    args=_inputs('certificate')
    columns=st.columns(3 if kind=='capped_bonus' else 2)
    a,b,c=columns[0],columns[1],columns[-1]
    level=_num('certificate_bonus','workshop.level',110,a) if kind!='discount' else 110.
    barrier=_num('certificate_barrier','workshop.barrier',70,b) if kind!='discount' else 70.
    cap=_num('certificate_cap','workshop.cap',120,a if kind=='discount' else c) if kind!='bonus' else 120.
    touched=st.checkbox(t('workshop.touched'),help=t('workshop.history'),key='certificate_touched') if kind!='discount' else False
    value=certificate_snapshot(kind,level=level,barrier=barrier,cap=cap,touched=touched,**args)
    metrics=[('workshop.price',f"{value['price']:.4f}")]
    if kind!='discount':metrics.append(('workshop.touch_probability',f"{value['touch_probability']:.2%}"))
    kpis(metrics)
    st.caption(t('workshop.unit'))
    if kind!='discount' and value['touched']:
        st.info(t('workshop.bonus_touched'))
    st.markdown('**'+t('workshop.replication')+'**')
    _table([{t('workshop.component'):t('workshop.'+k),t('workshop.value_axis'):v} for k,v in value['components'].items()])
    st.caption(t('workshop.replication_note'))
    upper=1.5*max(args['spot'],cap if kind!='bonus' else level,barrier)
    spots=np.unique(np.r_[np.linspace(0.,upper,150),barrier,np.nextafter(barrier,np.inf),level,cap])
    fig=go.Figure()
    if kind=='discount':
        fig.add_scatter(x=spots,y=certificate_payoff(kind,spots,level,barrier,cap),name=t('workshop.redemption'))
    else:
        if not value['touched']:
            surviving=spots[spots>barrier]
            fig.add_scatter(x=surviving,y=certificate_payoff(kind,surviving,level,barrier,cap),name=t('workshop.never_hit'))
        fig.add_scatter(x=spots,y=certificate_payoff(kind,spots,level,barrier,cap,True),name=t('workshop.hit'),line=dict(dash='dash'))
        fig.add_vline(x=barrier,line_dash='dot',name=t('workshop.barrier'),showlegend=True)
    chart(fig.update_layout(xaxis_title=t('workshop.terminal'),yaxis_title=t('workshop.payout')),key='certificate_payoff')
    st.caption(t('workshop.discount_redemption' if kind=='discount' else 'workshop.redemption_note'))
    if kind!='discount':
        st.caption(t('workshop.probability_help'))
        if args['dividend']==0 and kind=='bonus':st.caption(t('workshop.bonus_cost'))


def render_workshop(state):
    # Streamlit removes inactive widget state (including on the header's
    # language/theme rerun). Keep local experiments in a non-widget namespace.
    saved=st.session_state.get('_workshop_inputs',{})
    for key,value in saved.items():
        if key not in st.session_state:
            st.session_state[key]=value
    lang=state.ui.language
    st.subheader(t('workshop.intro'))
    st.caption(t('workshop.source'))
    tool=st.selectbox(t('workshop.choose'),['strategies','barriers','certificates'],
                      format_func=lambda x:t('workshop.'+x,lang),key='workshop_tool')
    try:
        {'strategies':render_strategies,'barriers':render_barriers,'certificates':render_certificates}[tool](state)
    except ValueError as exc:
        st.warning(error_message(exc))
    st.session_state['_workshop_inputs']=saved | {
        key:st.session_state[key] for key in st.session_state
        if key.startswith(('strategy_','barrier_','certificate_'))
        or key in ('workshop_tool','workshop_strategy')
    }
    with st.expander(t('workshop.sources')):
        st.markdown(t('workshop.sources_note'))
