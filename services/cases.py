"""Versioned, bounded JSON cases. Decode/validate entirely before replacing state.

Only data and explicitly constructed domain models are accepted. No pickle,
imports, executable objects, provider requests or arbitrary session keys.
Calculated book risk is invalidated; labelled attribution snapshots are retained.
"""
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, timezone
import json
import math
import numpy as np
import pandas as pd
from core.models import TerminalState, MarketState, PositionBook, RiskState, ScenarioState, UIState, CURRENCIES
from core.state import validate_book, DEMO_BOOKS
from core.board import validate_board, DEFAULT_BOARD
from engines.equity_derivatives_engine import OptionPosition, position_analytics, option_scenario
from engines.scenario_engine import MarketScenario
from engines.desk_scenario_engine import DeskScenario, PRESETS
from engines.rates_tools_engine import curve_from_table
from engines.structured_risk_engine import validate_note_inputs
from services.lab import LabState, chain_analysis
from services.structured import contract_for

FORMAT = 'mat-analytical-case'
VERSION = 1
MAX_BYTES = 5_000_000
MAX_CELLS = 100_000
MODEL_METADATA = {
    'options': 'European BSM; continuous rate/dividend; ACT/365',
    'structured': 'V2 GBM at contractual observations; fixed seed; educational estimate',
    'rates': 'Independent continuous zero curve; shared bond YTM conventions retained',
    'risk': 'Saved attribution snapshot; current book risk recomputed from inputs',
    'fx': 'USD per unit of currency; base conversion = FX[position]/FX[base]',
    'schema': '1',
}
# Only selected views; numerical values live in validated domain models.
VIEW_KEYS = {'eqd_view', 'eqd_surface_view', 'eqd_smile_axis', 'eqd_greek', 'structured_mode',
             'structured_tabs', 'note_independent_tabs', 'derivative_tabs', 'risk_tabs',
             'risk_diagnostic', 'financing_tabs', 'board_view', 'demo_choice'}
INTERACTIVE_BOUNDS = {'S':(1,250), 'K':(1,250), 'T':(.01,10), 'sigma':(.01,1.5), 'r':(-.05,.2), 'q':(0,.2)}


@dataclass
class AnalyticalCase:
    terminal: TerminalState
    lab: LabState
    structured: TerminalState | None
    board: list
    views: dict
    interactive: dict | None
    created_at: str
    models: dict


def _require(condition, message):
    if not condition: raise ValueError(message)


def _number(value, low=-1e12, high=1e12, integer=False):
    _require(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
             and low <= value <= high and (not integer or int(value) == value), 'Invalid numeric input or supported range.')
    return value


def _object(value, allowed, required=()):
    _require(isinstance(value, dict) and set(value) <= set(allowed) and set(required) <= set(value), 'Unexpected or missing JSON fields.')
    return value


def _construct(cls, value):
    return cls(**_object(value, {f.name for f in fields(cls)}))


def _encode(value):
    if isinstance(value, pd.DataFrame):
        _require(value.size <= MAX_CELLS and not isinstance(value.index, pd.MultiIndex), 'Table too large or unsupported multi-index.')
        return {'$table':True, 'columns':_encode(value.columns.tolist()), 'index':_encode(value.index.tolist()),
                'index_kind':'datetime' if isinstance(value.index, pd.DatetimeIndex) else 'values',
                'index_name':_encode(value.index.name), 'column_name':_encode(value.columns.name),
                'data':_encode(value.to_numpy().tolist()), 'dtypes':[str(d) for d in value.dtypes]}
    if isinstance(value, (date, datetime, pd.Timestamp)): return value.isoformat()
    if isinstance(value, np.generic): return _encode(value.item())
    if isinstance(value, dict): return {str(k):_encode(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)): return [_encode(v) for v in value]
    if isinstance(value, float) and math.isnan(value): return None
    _require(value is None or isinstance(value, (str, int, float, bool)), 'Unsupported case value.')
    if isinstance(value, float): _require(math.isfinite(value), 'Infinite values cannot be saved.')
    return value


def _decode(value):
    if isinstance(value, list): return [_decode(v) for v in value]
    if not isinstance(value, dict): return value
    if '$table' not in value: return {k:_decode(v) for k,v in value.items()}
    _object(value, ('$table','columns','index','index_kind','index_name','column_name','data','dtypes'),
            ('$table','columns','index','index_kind','data','dtypes'))
    columns, index, data = value['columns'], value['index'], value['data']
    _require(value['$table'] is True and isinstance(columns,list) and isinstance(index,list) and isinstance(data,list), 'Invalid table.')
    _require(len(columns)<=1000 and len(index)<=5000 and len(columns)*len(index)<=MAX_CELLS, 'Table exceeds limits.')
    _require(all(isinstance(c,(str,int,float)) and not isinstance(c,bool) for c in columns) and len(set(columns))==len(columns), 'Invalid or duplicate columns.')
    _require(len(data)==len(index) and all(isinstance(row,list) and len(row)==len(columns) and all(not isinstance(x,(list,dict)) for x in row) for row in data), 'Invalid table dimensions or cells.')
    _require(all(not isinstance(x,(list,dict)) for x in index), 'Invalid index.')
    allowed = ('float64','int64','int32','bool','object','string','datetime64[ns]','datetime64[ns, UTC]')
    _require(len(value['dtypes'])==len(columns) and all(d in allowed for d in value['dtypes']), 'Unsupported table data types.')
    if value['index_kind']=='datetime': index=pd.to_datetime(index,errors='raise')
    else: _require(value['index_kind']=='values','Invalid index kind.')
    frame=pd.DataFrame(data,index=index,columns=columns)
    for col,dtype in zip(columns,value['dtypes']):
        if dtype.startswith('int'):
            _require(all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) and int(x)==x and abs(x)<2**63 for x in frame[col]),'Integer table column would lose precision.')
        if dtype=='bool': _require(all(isinstance(x,bool) for x in frame[col]),'Invalid Boolean table column.')
        if dtype.startswith('datetime'): frame[col]=pd.to_datetime(frame[col],utc='UTC' in dtype)
        else: frame[col]=frame[col].astype(dtype)
    frame.index.name=value.get('index_name'); frame.columns.name=value.get('column_name')
    return frame


def _walk(value, depth=0, count=None):
    count=[0] if count is None else count
    count[0]+=1
    _require(depth<=16 and count[0]<=250000,'Case nesting or element limit exceeded.')
    if isinstance(value,dict):
        _require(all(isinstance(k,str) and len(k)<=256 for k in value),'Invalid object key.')
        for item in value.values(): _walk(item,depth+1,count)
    elif isinstance(value,list):
        for item in value: _walk(item,depth+1,count)
    elif isinstance(value,str): _require(len(value)<=4096,'Text field too long.')
    elif isinstance(value,(float,int)) and not isinstance(value,bool): _require(math.isfinite(value),'Non-finite JSON number.')


def validate_interactive(value):
    _object(value,INTERACTIVE_BOUNDS,INTERACTIVE_BOUNDS)
    return {k:float(_number(value[k],*bounds)) for k,bounds in INTERACTIVE_BOUNDS.items()}


def _terminal(value):
    value=dict(_object(value, (f.name for f in fields(TerminalState)), ('book','market','risk','scenario','ui','valuation_date')))
    b=_construct(PositionBook,value['book']); b.positions=validate_book(b.positions)
    _require(b.name in DEMO_BOOKS and b.base_currency in CURRENCIES,'Unknown book or currency.')
    _require(b.source in ('SYNTHETIC','USER INPUT','PUBLIC','MIXED'),'Invalid book source.')
    for c in ('quantity','price','multiplier','strike'): _require((b.positions[c].abs()<=1e12).all(),'Position numeric limit exceeded.')
    _require((b.positions.maturity<=100).all() and (b.positions.volatility<=64).all(),'Position time/volatility limit exceeded.')
    _number(b.repo_cash,0); _number(b.repo_rate,-.1,.5); _number(b.repo_haircut,0,.9); _number(b.repo_days,1,3650,True)
    _number(b.revision,0,1e9,True)
    _require(not b.collateral_id or b.collateral_id in b.positions.id.values,'Unknown collateral position.')
    m=_construct(MarketState,value['market'])
    _require(m.mode in ('mixed','demo','saved') and m.source in ('SYNTHETIC','PUBLIC','USER INPUT','MIXED'),'Invalid market mode/source.')
    for mapping in (m.spots,m.fx,m.rates): _require(isinstance(mapping,dict) and 1<=len(mapping)<=500,'Invalid market assumptions.')
    _require(set(CURRENCIES)<=set(m.fx) and set(CURRENCIES)<=set(m.rates),'Missing currency conversion/rate.')
    for x in [*m.spots.values(),*m.fx.values()]: _number(x,1e-12,1e12)
    for x in m.rates.values(): _number(x,-.5,1.)
    _require(m.fx['USD']==1.,'FX must be USD per currency unit, with USD = 1.')
    _require(isinstance(m.curves,dict) and set(m.curves)<= {'USD','EUR'},'Unsupported curve currency.')
    for curve in m.curves.values():
        _require(isinstance(curve,dict) and curve.get('source') in ('SYNTHETIC','PUBLIC','USER INPUT'), 'Invalid curve metadata.')
        history=curve.get('history')
        _require(isinstance(history,pd.DataFrame) and list(history.columns)==[1,2,5,10,30] and 2<=len(history)<=756,'Invalid curve history.')
        _require(isinstance(history.index,pd.DatetimeIndex) and not history.index.hasnans and history.index.is_unique and history.index.is_monotonic_increasing,'Invalid curve dates.')
        _require(np.isfinite(history.to_numpy(dtype=float)).all() and (history.abs()<=100).all().all(),'Invalid percent curve levels.')
    _require(isinstance(m.provenance,dict),'Invalid provenance.')
    for key,item in m.provenance.items():
        _require(key in m.spots and isinstance(item,dict),'Invalid quote provenance.')
        _require(item.get('source') in ('SYNTHETIC','PUBLIC','USER INPUT'),'Invalid quote source.')
        if 'price' in item: _require(item['price']==m.spots[key],'Quote metadata and market spot disagree.')
    _require(isinstance(b.structured_terms,dict) and set(b.structured_terms)<=set(b.positions.query("asset_class=='Structured'").id),'Orphan structured contract.')
    workload=0
    for row in b.positions.query("asset_class=='Structured'").to_dict('records'):
        spec=b.structured_terms.get(row['id'],{})
        _object(spec, ('underlyings','fixings','volatilities','product','memory','simulations','autocall','coupon_barrier','protection','coupon','correlation','frequency'))
        for key in ('underlyings','fixings','volatilities'):
            if key in spec: spec[key]=tuple(spec[key])
        inputs,ratios,kind,memory,names=contract_for(row,m,b.structured_terms)
        _require(kind in ('Athena','Phoenix') and isinstance(memory,bool) and len(names)==len(set(names))==len(inputs.initial_spots),'Invalid structured contract.')
        validate_note_inputs(inputs)
        workload+=inputs.simulations*np.ceil(inputs.maturity_years*inputs.observations_per_year)*len(names)
        _require(workload<=2_000_000,'Structured book exceeds two million simulated observation values.')
        _require(np.isfinite(ratios).all() and min(ratios)>0,'Invalid fixings or spots.')
    _object(b.financing_terms,('basis','elapsed','threshold','mta','rounding'))
    if b.financing_terms:
        _require(b.financing_terms.get('basis',360) in (360,365),'Invalid repo day count.')
        _number(b.financing_terms.get('elapsed',0),0,b.repo_days,True)
        for key in ('threshold','mta','rounding'): _number(b.financing_terms.get(key,0),0)
    if b.lending_terms:
        from engines.sec_lending_engine import calculate_securities_lending_trade
        calculate_securities_lending_trade(**b.lending_terms)
    r=_construct(RiskState,value['risk']); r.results={}
    _require(r.confidence in (.95,.975,.99) and r.horizon in (1,5,10) and r.estimator in ('sample','ewma','ledoit_wolf'),'Unsupported risk controls.')
    sc=_construct(ScenarioState,value['scenario'])
    _require(sc.name in [s.name for s in PRESETS]+['custom'],'Unknown scenario.')
    if sc.shocks:
        shock=_construct(DeskScenario,sc.shocks)
        _require(len(shock.rates)==5,'Curve shock requires five tenors.')
        for x in [shock.equity,shock.fx,shock.volatility,shock.correlation,shock.credit,shock.haircut,shock.collateral,*shock.rates]: _number(x,-10000,10000)
        _require(min(shock.equity,shock.fx,shock.collateral)>-1,'Price shocks must exceed -100%.')
        sc.shocks=asdict(shock);sc.shocks['rates']=tuple(shock.rates)
    ui=_construct(UIState,value['ui'])
    from components.global_header import PAGES
    _require(ui.language in ('en','fr') and ui.theme in ('dark','light') and ui.page in PAGES,'Invalid UI preferences.')
    valuation=date.fromisoformat(value['valuation_date'])
    _require(date(1900,1,1)<=valuation<=date(2100,12,31),'Unsupported valuation date.')
    for row in b.positions.itertuples():
        if row.asset_class in ('Option','Structured'): _require(row.underlying in m.spots,'Missing underlying spot.')
        if row.asset_class=='Equity' and row.mark_mode=='Market': _require(row.ticker in m.spots,'Missing equity spot.')
    m.mode='saved'
    return TerminalState(b,m,r,sc,ui,valuation)


def _lab(value):
    value=dict(_object(value, (f.name for f in fields(LabState))))
    value['as_of']=date.fromisoformat(value['as_of'])
    value['position']=_construct(OptionPosition,value['position']);position_analytics(value['position'])
    for key in ('scenario','hedge_scenario'):
        spec=dict(value[key]); spec['curve_twist']=tuple(tuple(x) for x in spec['curve_twist'])
        value[key]=_construct(MarketScenario,spec)
        option_scenario(value['position'],value[key])
    for key in ('matrix_spots','matrix_vol_points'):
        _require(isinstance(value[key],list) and 1<=len(value[key])<=31,'Invalid scenario matrix size.')
        for x in value[key]: _number(x,-.99 if key=='matrix_spots' else -100,2 if key=='matrix_spots' else 100)
        value[key]=tuple(value[key])
    lab=LabState(**value)
    _require(lab.currency in ('USD','EUR','GBP','JPY') and lab.mode in ('iv','price'),'Unsupported currency/input mode.')
    _require(lab.view in ('chain','position','scenario','hedge','greeks') and lab.volatility_view in ('heatmap','surface','smile','term'),'Invalid lab view.')
    _require(isinstance(lab.chain,pd.DataFrame) and 1<=len(lab.chain)<=2000,'Option chain requires 1–2000 rows.')
    _require(not chain_analysis(lab.chain,lab.as_of,lab.mode)['chain'].empty,'No valid option-chain rows.')
    _require(isinstance(lab.curve,pd.DataFrame) and 2<=len(lab.curve)<=100,'Curve requires 2–100 nodes.')
    curve_from_table(lab.curve)
    _number(lab.curve_maturity,1,30,True);_number(lab.curve_coupon,0,.3);_number(lab.curve_notional)
    _require(isinstance(lab.risk_tables,dict) and set(lab.risk_tables)<= {'Risk_Attribution','Risk_PCA','Risk_Stress'} and all(isinstance(x,pd.DataFrame) for x in lab.risk_tables.values()),'Invalid risk snapshot tables.')
    return lab


def export_case(terminal, lab, structured=None, board=None, views=None, interactive=None):
    shared=asdict(terminal);shared['risk']['results']={}
    independent=asdict(structured) if structured else None
    if independent: independent['risk']['results']={}
    document=dict(format=FORMAT,version=VERSION,created_at=datetime.now(timezone.utc).isoformat(),models=MODEL_METADATA,
                  terminal=shared,lab=asdict(lab),structured=independent,board=list(DEFAULT_BOARD) if board is None else board,
                  views={k:v for k,v in (views or {}).items() if k in VIEW_KEYS},interactive=interactive)
    raw=json.dumps(_encode(document),ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
    import_case(raw)  # A downloaded case must be restorable by the same validator.
    return raw


def import_case(raw):
    _require(isinstance(raw,(bytes,str)) and len(raw.encode('utf-8') if isinstance(raw,str) else raw)<=MAX_BYTES,'Case exceeds 5 MB.')
    def pairs(items):
        result={}
        for key,value in items:
            _require(key not in result,'Duplicate JSON key.');result[key]=value
        return result
    def constant(value): raise ValueError('Non-finite JSON values are forbidden.')
    try:
        doc=json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
        _walk(doc)
        _object(doc,('format','version','created_at','models','terminal','lab','structured','board','views','interactive'),
                ('format','version','created_at','models','terminal','lab','structured','board','views','interactive'))
        _require(doc['format']==FORMAT and type(doc['version']) is int and doc['version']==VERSION,'Unsupported case format/version.')
        datetime.fromisoformat(doc['created_at'])
        _object(doc['models'],MODEL_METADATA,MODEL_METADATA)
        _require(all(isinstance(v,str) for v in doc['models'].values()),'Invalid model metadata.')
        doc=_decode(doc)
        views=_object(doc['views'],VIEW_KEYS)
        _require(all(isinstance(v,str) and len(v)<=100 for v in views.values()),'Invalid view selection.')
        terminal=_terminal(doc['terminal']); lab=_lab(doc['lab'])
        structured=_terminal(doc['structured']) if doc['structured'] else None
        if structured: _require(structured.book.positions.asset_class.eq('Structured').all() and structured.book.repo_cash==0,'Independent structured case must contain notes only, with no repo.')
        return AnalyticalCase(terminal,lab,structured,validate_board(doc['board']),views,
                              validate_interactive(doc['interactive']) if doc['interactive'] is not None else None,
                              doc['created_at'],doc['models'])
    except (KeyError,TypeError,OverflowError,RecursionError,UnicodeError,AttributeError,IndexError) as exc:
        raise ValueError('Malformed analytical case; nothing was applied.') from exc


def apply_case(raw, session, query):
    candidate=import_case(raw)  # No state mutation above this line.
    # Build the complete replacement before mutating anything, including views.
    info={'created_at':candidate.created_at,'models':candidate.models,'imported_at':datetime.now(timezone.utc).isoformat()}
    updates=dict(terminal=candidate.terminal,analytics_lab=candidate.lab,board_ids=candidate.board,
                 board_ready=True,board_revision=1,case_metadata=info,case_restored=True)
    updates.update(valid_views(candidate.views,candidate.terminal.ui.language))
    if candidate.structured: updates['structured_lab']=candidate.structured
    if candidate.interactive:
        updates.update(interactive_case=candidate.interactive,interactive_revision=info['imported_at'])
    # Clear old widget values and generated result/download caches. All remaining
    # operations only install already-validated data; no calculations or parsing.
    for key in list(session): del session[key]
    session.update(updates)
    query.update(version='v2',page='cases',lang=candidate.terminal.ui.language,theme=candidate.terminal.ui.theme)
    return candidate


def valid_views(views,language):
    from core.i18n import t
    enums={'demo_choice':('collar','eqd','autocallable'), 'eqd_view':('chain','position','scenario','hedge','greeks'), 'eqd_surface_view':('heatmap','surface','smile','term'),
           'eqd_smile_axis':('moneyness','strike'), 'eqd_greek':('delta','gamma','vega_1pct'), 'structured_mode':('lab','book'),
           'risk_diagnostic':('rolling','correlation'), 'board_view':('quotes','news','events','sessions','portfolio')}
    for key,terms in {'structured_tabs':('product','risk','simulation','advanced'), 'note_independent_tabs':('product','risk','simulation','advanced'),
                      'derivative_tabs':('vanilla','greeks','volatility','structured','workshop','interactive_greeks'),
                      'risk_tabs':('book_exposure','risk_var','factor','stress','validation'), 'financing_tabs':('repo','lending','collateral')}.items():
        enums[key]=tuple(t(x,language) for x in terms)
    return {k:v for k,v in views.items() if k in enums and v in enums[k]}
