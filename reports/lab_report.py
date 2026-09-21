"""One structured workbook for related laboratory outputs, not one file per chart."""
from dataclasses import asdict
import pandas as pd
from reports.desk_report import write_workbook
from services.lab import option_outputs,curve_outputs


def lab_report_tables(lab) -> dict[str,pd.DataFrame]:
    options=option_outputs(lab);curves=curve_outputs(lab)
    kv=lambda mapping:pd.DataFrame({'metric':mapping.keys(),'value':[str(v) if isinstance(v,(dict,tuple)) else v for v in mapping.values()]})
    smile={k:v for k,v in options['smile'].items() if k!='methods'}
    methods=[
        'European BSM with continuous rate/dividend and ACT/365; existing transparent pricer.',
        'IV is decimal: 0.215 = 21.5%; a +3 vol-point change is +0.03. Brent brackets no-arbitrage bounds.',
        'Smile: OTM put below forward, call above. Linear IV interpolation by K/S or spot delta; no extrapolation.',
        'No full static-arbitrage-free surface claim. Not executable market quotes.',
        'Cash delta = N*M*Delta*S; cash gamma = N*M*Gamma*S^2; 1% gamma P&L = cash gamma*0.01^2/2.',
        'Vega per 1 vol point; theta per calendar day; rho per +1 percentage point = 100 bp.',
        'Scenario P&L compares five-Greek Taylor approximation to full BSM revaluation; residual includes omitted cross terms and higher orders.',
        'P&L matrix uses instantaneous spot/vol shocks with fixed rates/time. Invalid nonpositive IV cells are explicitly flagged.',
        'Static hedge: underlying units = -position delta. Spot/vol shocks only; no financing, transaction costs or time passage.',
        'Zero curves: continuous compounding, linear zero-rate interpolation, flat endpoints. Forward rates are continuous interval forwards.',
        'Curve example: semiannual coupon bond at coupon date, independent from the shared book and its YTM valuation.',
        'Gaussian VaR has zero mean and sqrt(horizon) scaling. Euler components sum to Gaussian VaR; historical VaR is distinct.',
        'Risk snapshot is from the last attribution view opened in this session; source and units are preserved.',
        'Lab positions are independent of the shared book; do not add these example P&Ls to portfolio totals.',
    ]
    return {'Inputs':kv(asdict(lab.position)), 'Scenario':kv(asdict(lab.scenario)),
        'Sources':kv({'chain_source':lab.source,'chain_as_of':str(lab.as_of),'chain_mode':lab.mode,
            'position_source':lab.position_source,'quote_currency':lab.currency,'selected_maturity':options['maturity'],
            'curve_source':lab.curve_source,'risk_source':lab.risk_source or 'Not calculated this session'}),
        'Option_Chain':options['chain']['chain'],'Rejected_Quotes':options['chain']['rejected'],
        'Smile_Metrics':kv(smile),'Smile_Methods':kv(options['smile']['methods']),'Term_Structure':options['term']['data'],
        'Cash_Greeks':kv(options['position']),'Scenario_PnL':kv({**options['scenario']['parts'],**{k:v for k,v in options['scenario'].items() if k!='parts'}}),
        'Spot_Vol_Matrix':options['matrix'],'Delta_Hedge':kv(options['hedge']),'Hedge_Inputs':kv(asdict(lab.hedge_scenario)),
        'Curve_Inputs':lab.curve,'Zero_Curve':curves['table'],'Curve_Scenario':curves['comparison'],
        'Curve_Cashflows':curves['risk']['cashflows'],'Curve_DV01':curves['risk']['buckets'],
        'Curve_Summary':kv({k:v for k,v in curves['risk'].items() if not isinstance(v,pd.DataFrame)}),
        **lab.risk_tables,'Methodology':pd.DataFrame({'convention':methods})}


def generate_lab_report(lab) -> bytes:
    return write_workbook(lab_report_tables(lab))
