"""V2 book-consistent reports. The four audited legacy exporter APIs remain available."""
from io import BytesIO
from dataclasses import asdict
from datetime import datetime,timezone
import pandas as pd
from core.i18n import t
from services.book_risk import book_risk
from services.financing import repo_margin,repo_stress
from services.structured import contract_for
from engines.structured_risk_engine import value_note,bump_risk
from engines.desk_scenario_engine import scenario_summary


def report_tables(state):
    r=book_risk(state);marks=r['marks'];lang=state.ui.language
    scenarios=scenario_summary(marks,state.market,state.book)
    executive={'book':state.book.name,'base_currency':state.book.base_currency,'valuation_date':str(state.valuation_date),'exported_utc':datetime.now(timezone.utc).isoformat(),'nav':r['nav'],'repo_cash_liability':state.book.repo_cash,'historical_var':r['var'],'historical_es':r['es'],'net_dv01_per_bp':marks.dv01.sum(),'net_cs01_per_bp':marks.cs01.sum(),'worst_scenario_pnl':scenarios.pnl.min(),'maximum_liquidity_shortfall':scenarios.liquidity.max(),'risk_history_source':'SYNTHETIC'}
    metrics={k:r[k] for k in ['var','es','parametric_var','parametric_es','volatility']}
    metrics.update(confidence=state.risk.confidence,horizon_observations=state.risk.horizon,covariance=state.risk.estimator,annualization=252)
    sources=[dict(series=k,**{field:v.get(field,'') for field in ['source','provider','as_of','basis','url']}) for k,v in [*state.market.provenance.items(),*state.market.curves.items()]]
    sources.extend([dict(series='Book',source=state.book.source,as_of=str(state.valuation_date)),dict(series='Risk history',source='SYNTHETIC',as_of=str(r['pnl'].index[-1].date()))])
    methods=[t(k,lang) for k in ['disclaimer','book.note','risk.method','scenario.method','option.units','advanced.method','structured.method','financing.method','lending.method']]
    methods+=['Positive DV01/CS01 means a loss for a +1 bp yield/spread rise on a long bond. Signed exposures are translated to base currency. Bond ACT/ACT schedules and quoted-clean-price yield reconciliation are retained.', 'Historical horizon losses sum fixed-book daily P&L over overlapping windows; these synthetic returns are not a realized investment track record.', 'Structured Monte Carlo risk uses the contract parameters recorded in Structured_Terms. Financing liquidity and economic P&L are separate.']
    kv=lambda values:pd.DataFrame({'metric':list(values),'value':list(values.values())})
    tables={'Executive_Summary':kv(executive),'Positions':state.book.positions.copy(),'Marked_Positions':marks,'Risk_Metrics':kv(metrics),'Stress_Scenarios':scenarios,'Risk_Contributions':r['contributions'],'Greeks':marks.loc[marks.asset_class.isin(['Option','Structured']),[k for k in ['id','underlying','currency','delta','delta_cash','gamma','gamma_cash_1pct','vega','theta','rho','correlation_1pct','autocall_probability','loss_probability'] if k in marks]],'Bond_Risk':marks.loc[marks.asset_class=='Bond'],'Risk_History':r['pnl'].reset_index(),'Methodology':pd.DataFrame({'assumption':methods}),'Sources':pd.DataFrame(sources)}
    terms=[];probs=[];risks=[]
    for row in state.book.positions.query("asset_class=='Structured'").to_dict('records'):
        inputs,ratios,kind,memory,names=contract_for(row,state.market,state.book.structured_terms)
        terms.append(dict(id=row['id'],product=kind,memory=memory,underlyings=str(names),current_ratios=str(ratios),**{k:str(v) if isinstance(v,tuple) else v for k,v in asdict(inputs).items()}))
        result=value_note(inputs,ratios,kind,memory);probs.append(dict(id=row['id'],**result['summary']));risks.append(dict(id=row['id'],**bump_risk(inputs,ratios,kind,memory)))
    tables.update(Structured_Terms=pd.DataFrame(terms),Structured_Probabilities=pd.DataFrame(probs),Structured_Risk=pd.DataFrame(risks))
    collateral=float(marks.loc[marks.id==state.book.collateral_id,'market_value'].sum());b=state.book
    if b.repo_cash:
        margin=asdict(repo_margin(state,collateral));stress,need=repo_stress(state,collateral,min(.99,b.repo_haircut+.05),-.1)
        tables['Contractual_VM']=kv(margin);tables['Refinancing_Stress']=kv(dict(asdict(stress),book_cash_shortfall=need))
    else:tables['Contractual_VM']=kv({'repo_cash':0.,'status':'No booked repo'})
    tables['Financing_Terms']=kv(dict(repo_cash=b.repo_cash,repo_rate=b.repo_rate,contractual_haircut=b.repo_haircut,days=b.repo_days,collateral_id=b.collateral_id,**b.financing_terms))
    if b.lending_terms:
        from engines.sec_lending_engine import calculate_securities_lending_trade
        tables['Securities_Lending']=kv(asdict(calculate_securities_lending_trade(**b.lending_terms)))
    return tables


def generate_desk_report(state,section='all'):
    tables=report_tables(state)
    groups={'rates':['Bond_Risk','Stress_Scenarios'],'risk':['Risk_Metrics','Risk_Contributions','Risk_History','Stress_Scenarios'],
        'structured':['Structured_Terms','Structured_Probabilities','Structured_Risk','Greeks','Stress_Scenarios'],
        'financing':['Financing_Terms','Contractual_VM','Refinancing_Stress','Securities_Lending']}
    if section!='all':
        wanted=['Executive_Summary','Positions',*groups[section],'Methodology','Sources'];tables={k:v for k,v in tables.items() if k in wanted}
    output=BytesIO()
    with pd.ExcelWriter(output,engine='xlsxwriter',engine_kwargs={'options':{'strings_to_formulas':False,'strings_to_urls':False}}) as writer:
        header=writer.book.add_format({'bold':True,'bg_color':'#17334F','font_color':'#FFFFFF'})
        for name,frame in tables.items():
            frame=frame.copy()
            for col in frame:
                if frame[col].dtype=='object':frame[col]=frame[col].map(lambda x:str(x) if isinstance(x,(dict,list,tuple)) else x)
            frame.to_excel(writer,sheet_name=name,index=False)
            ws=writer.sheets[name];ws.freeze_panes(1,0);ws.set_row(0,22,header)
            if len(frame.columns):
                ws.autofilter(0,0,len(frame),len(frame.columns)-1)
                for i,col in enumerate(frame):ws.set_column(i,i,min(70,max(14,len(str(col))+2)))
    return output.getvalue()
