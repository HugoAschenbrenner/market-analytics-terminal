import plotly.express as px
import streamlit as st
from core.i18n import t
from core.charting import chart
from components.book_editor import book_editor
from services.analytics import marked_positions

def render(state):
    book_editor(state)
    frame=marked_positions(state)
    chart(px.bar(frame,x='id',y='market_value',color='asset_class',title=t('exposure'),labels={'id':t('position'),'market_value':t('value'),'asset_class':t('asset_class')}))
