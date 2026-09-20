"""Key-rate bumps of the audited cashflows, carry proxies and DV01-neutral trades."""
from datetime import timedelta
import numpy as np
import pandas as pd
from engines.fixed_income_engine import build_remaining_contractual_cashflows,calculate_dirty_price_from_ytm

TENORS=np.array([1,2,5,10,30.])

def key_rate_ladder(bonds,state):
    rows=[]
    for row in bonds.itertuples():
        _,cf,exponents=build_remaining_contractual_cashflows(row.coupon,2,state.valuation_date-timedelta(days=366),row.maturity_date,state.valuation_date)
        weights=np.array([np.interp(exponents/2,TENORS,np.eye(5)[i]) for i in range(5)])
        y=row.pricing_yield
        scale=row.quantity/100*state.market.fx[row.currency]/state.market.fx[state.book.base_currency]
        values=[]
        for w in weights:
            down=np.sum(cf/(1+(y-1e-4*w)/2)**exponents)
            up=np.sum(cf/(1+(y+1e-4*w)/2)**exponents)
            values.append((down-up)/2*scale)
        rows.append(dict(id=row.id,currency=row.currency,**{str(int(t)):v for t,v in zip(TENORS,values)}))
    return pd.DataFrame(rows,columns=['id','currency',*[str(int(t)) for t in TENORS]])

def carry_roll(bonds,curves,horizon=.25):
    rows=[]
    for row in bonds.itertuples():
        if row.currency not in curves:
            rows.append({'id':row.id,'carry':row.market_value*row.pricing_yield*horizon,'roll':np.nan});continue
        curve=curves[row.currency]['history'].iloc[-1]
        roll_bps=(np.interp(max(.01,row.maturity-horizon),curve.index,curve.values)-np.interp(row.maturity,curve.index,curve.values))*100
        rows.append({'id':row.id,'carry':row.market_value*row.pricing_yield*horizon,'roll':-row.dv01*roll_bps})
    return pd.DataFrame(rows)

def yield_price_curve(row,state):
    _,cf,exponents=build_remaining_contractual_cashflows(row.coupon,2,state.valuation_date-timedelta(days=366),row.maturity_date,state.valuation_date)
    yields=np.linspace(max(-.5,row.pricing_yield-.03),row.pricing_yield+.03,61)
    return pd.DataFrame({'yield':yields*100,'price':[calculate_dirty_price_from_ytm(cf,exponents,y,2) for y in yields]})

def reference_dv01(tenor,yield_rate,valuation_date):
    maturity=pd.Timestamp(valuation_date)+pd.DateOffset(years=int(tenor))
    _,cf,exponents=build_remaining_contractual_cashflows(yield_rate,2,valuation_date,maturity,valuation_date)
    lower=calculate_dirty_price_from_ytm(cf,exponents,yield_rate-1e-4,2)
    upper=calculate_dirty_price_from_ytm(cf,exponents,yield_rate+1e-4,2)
    return (lower-upper)/200  # currency DV01 per one unit of nominal

def curve_trade(tenors,yields,notional,valuation_date,view='steepener'):
    tenors=np.asarray(tenors,float);yields=np.asarray(yields,float)
    if len(tenors) not in (2,3) or len(yields)!=len(tenors) or not np.isfinite([*tenors,*yields,notional]).all() or notional<=0 or (np.diff(tenors)<=0).any():
        raise ValueError('Invalid curve trade inputs')
    dv=np.array([reference_dv01(t,y,valuation_date) for t,y in zip(tenors,yields)])
    if len(tenors)==2:
        if view not in ('steepener','flattener'):raise ValueError('Invalid curve view')
        quantities=np.array([notional,-notional*dv[0]/dv[1]])*(1 if view=='steepener' else -1)
    else:
        left=(tenors[2]-tenors[1])/(tenors[2]-tenors[0]);right=1-left
        target=np.array([left,-1,right])*notional*dv[1]
        quantities=target/dv
    legs=pd.DataFrame({'tenor':tenors,'notional':quantities,'dv01':quantities*dv})
    shape=np.linspace(-20,20,len(tenors))
    curvature=np.zeros(len(tenors));curvature[len(tenors)//2]=20
    shocks={'parallel':np.ones(len(tenors))*25,'steepener':shape,'flattener':-shape,'curvature':curvature}
    pnl=pd.DataFrame([{'scenario':k,'pnl':float(-legs.dv01@shock)} for k,shock in shocks.items()])
    return {'legs':legs,'scenarios':pnl}


from dataclasses import dataclass
from engines.scenario_engine import MarketScenario


@dataclass(frozen=True)
class ZeroCurve:
    """Continuously compounded zero rates, linear in tenor, flat at both ends."""
    tenors: tuple[float, ...]
    rates: tuple[float, ...]

    def __post_init__(self):
        t, r = np.asarray(self.tenors,float), np.asarray(self.rates,float)
        if t.ndim != 1 or r.shape != t.shape or len(t)<2 or not np.isfinite([*t,*r]).all() or (t<=0).any() or (np.diff(t)<=0).any():
            raise ValueError('At least two unique, increasing positive curve tenors and finite decimal zero rates are required.')

    def zero(self, times):
        times = np.asarray(times,float)
        if not np.isfinite(times).all() or (times<0).any():
            raise ValueError('Cash-flow times must be finite and nonnegative.')
        return np.interp(times, self.tenors, self.rates)

    def discount(self, times):
        with np.errstate(over='ignore'):
            factors = np.exp(-self.zero(times)*np.asarray(times,float))
        if not np.isfinite(factors).all() or (factors<=0).any():
            raise ValueError('Curve discount factors overflow or underflow.')
        return factors

    def shocked(self, scenario: MarketScenario):
        # Include twist nodes so kinks between quoted curve pillars are preserved.
        nodes = sorted(set(self.tenors) | {t for t,_ in scenario.curve_twist})
        return ZeroCurve(tuple(nodes),tuple(self.zero(nodes)+scenario.rate_at(nodes)/10000))


def curve_from_table(table: pd.DataFrame) -> ZeroCurve:
    if not {'tenor','market_rate','rate_type'}.issubset(table):
        raise ValueError('Curve columns: tenor (years), market_rate (decimal), rate_type (zero).')
    if not table.rate_type.eq('zero').all():
        raise ValueError('Only direct continuously compounded zero rates are supported; par yields are not zero rates.')
    frame=table.sort_values('tenor')
    return ZeroCurve(tuple(frame.tenor.astype(float)),tuple(frame.market_rate.astype(float)))


def zero_curve_table(curve: ZeroCurve) -> pd.DataFrame:
    times=np.asarray(curve.tenors);factors=curve.discount(times)
    previous_times=np.r_[0,times[:-1]];previous_df=np.r_[1.,factors[:-1]]
    forwards=np.log(previous_df/factors)/(times-previous_times)
    return pd.DataFrame({'tenor':times,'zero_rate':curve.rates,'discount_factor':factors,
                         'forward_start':previous_times,'forward_end':times,'forward_rate':forwards})


def curve_spreads(curve: ZeroCurve) -> dict:
    def spread(short,long):
        return float((curve.zero(long)-curve.zero(short))*10000) if curve.tenors[0]<=short and curve.tenors[-1]>=long else None
    return {'2s10s_bp':spread(2.,10.),'5s30s_bp':spread(5.,30.)}


def cashflow_curve_risk(times, cashflows, curve: ZeroCurve, scenario: MarketScenario) -> dict:
    """Full discounting and nodal DV01; caller supplies actual remaining cash flows.

    Cash flows are in one currency and already include signed position size.
    This function deliberately does not reinterpret a bond's quoted YTM.
    """
    times, flows=np.asarray(times,float),np.asarray(cashflows,float)
    if times.ndim!=1 or flows.shape!=times.shape or not len(times) or not np.isfinite(flows).all() or (times<=0).any():
        raise ValueError('Matching finite remaining cash flows and strictly positive times are required.')
    base_values=flows*curve.discount(times);base=float(base_values.sum())
    shocked=curve.shocked(scenario);shocked_value=float(flows@shocked.discount(times))
    dv01=[]
    for node in range(len(curve.tenors)):
        bump=np.zeros(len(curve.tenors));bump[node]=1e-4
        lower=ZeroCurve(curve.tenors,tuple(np.asarray(curve.rates)-bump))
        upper=ZeroCurve(curve.tenors,tuple(np.asarray(curve.rates)+bump))
        dv01.append(float(flows@(lower.discount(times)-upper.discount(times))/2))
    parallel_down=curve.shocked(MarketScenario(rate_bp=-1))
    parallel_up=curve.shocked(MarketScenario(rate_bp=1))
    parallel_dv01=float(flows@(parallel_down.discount(times)-parallel_up.discount(times))/2)
    duration_contributions=times*base_values/base if abs(base)>1e-12 else np.zeros_like(times)
    return dict(base_value=base,shocked_value=shocked_value,pnl=shocked_value-base,dv01=parallel_dv01,
        duration=float(duration_contributions.sum()),
        buckets=pd.DataFrame({'tenor':curve.tenors,'dv01':dv01}),
        cashflows=pd.DataFrame({'time':times,'cashflow':flows,'present_value':base_values,'duration_contribution':duration_contributions}))


def sample_curve_table() -> pd.DataFrame:
    return pd.DataFrame({'tenor':[.5,1.,2.,5.,10.,30.],
                         'market_rate':[.032,.033,.034,.037,.04,.043],'rate_type':'zero'})
