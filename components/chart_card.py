import plotly.graph_objects as go
from core.i18n import t
from core.charting import chart
from services.market_data import curve_overlay

def curve_chart(state,history=False,height=280):
    fig=go.Figure()
    for currency,payload in state.market.curves.items():
        for days,label in ([(0,'latest'),(7,'week'),(30,'month')] if history else [(0,'latest')]):
            series=curve_overlay(payload,days)
            if series is not None:
                fig.add_scatter(x=series.index,y=series.values,name=f'{currency} · {t(label)}' if history else currency,line=dict(dash='solid' if days==0 else 'dash' if days==7 else 'dot'))
    fig.update_layout(title=t('curve'),xaxis_title=t('tenor'),yaxis_title=t('yield'))
    chart(fig,height=height)
