from pathlib import Path
import streamlit as st
from core.i18n import t


def render_r_companion():
    with st.expander(t('r.companion')):
        st.caption(t('r.note'))
        root=Path(__file__).resolve().parents[1]/'r_analytics'
        st.code('Rscript r_analytics/portfolio_performance_report.R',language='bash')
        for filename in ['performance_summary.csv','rolling_risk_metrics.csv','monthly_returns.csv','correlation_matrix.csv']:
            path=root/'outputs'/filename
            if path.exists():st.download_button(filename,path.read_bytes(),filename,'text/csv')
