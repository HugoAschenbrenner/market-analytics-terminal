import numpy as np
import plotly.graph_objects as go
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.kpi_card import kpis
from components.formula_panel import formula_panel
from services.analytics import marked_positions

def render(state):
    book=state.book
    st.caption(t('financing.none'))
    bonds=marked_positions(state).query("asset_class == 'Bond'")
    if not bonds.empty:
        book.collateral_id=st.selectbox(t('collateral'),bonds.id.tolist(),index=bonds.id.tolist().index(book.collateral_id) if book.collateral_id in bonds.id.tolist() else 0)
    a,b,c,d=st.columns(4)
    book.repo_cash=a.number_input(t('financing.cash'),min_value=0.,value=book.repo_cash,step=10000.)
    book.repo_rate=b.number_input(t('financing.rate'),min_value=-10.,max_value=50.,value=book.repo_rate*100)/100
    book.repo_haircut=c.number_input(t('financing.haircut'),min_value=0.,max_value=90.,value=book.repo_haircut*100)/100
    book.repo_days=int(d.number_input(t('financing.days'),min_value=1,max_value=3650,value=book.repo_days))
    cost=book.repo_cash*book.repo_rate*book.repo_days/360
    kpis([('financing.cash',book.repo_cash),('financing.cost',cost)])
    rates=np.linspace(-.01,.10,30)
    chart(go.Figure(go.Scatter(x=rates*100,y=book.repo_cash*rates*book.repo_days/360)).update_layout(title=t('financing.cost'),xaxis_title=t('financing.rate'),yaxis_title=t('value')))
    formula_panel('financing.method',[r'I=C\,r\,\frac{d}{360}'])
