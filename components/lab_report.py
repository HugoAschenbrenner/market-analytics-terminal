import streamlit as st
from components.lab_common import tr
from reports.lab_report import generate_lab_report
from services.lab import get_lab


def render_lab_export():
    if st.button(tr('Prepare combined analytics workbook','Préparer le rapport analytique commun'),key='lab_prepare_export'):
        try:
            data=generate_lab_report(get_lab())
            st.download_button(tr('Download Excel workbook','Télécharger le rapport Excel'),data,
                               'MAT_equity_volatility_risk.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key='lab_download')
        except (ValueError,TypeError) as exc:
            st.warning(str(exc))
    st.caption(tr('Includes inputs, source/date, chain, Greeks, scenario, hedge and curve data; risk attribution is included after visiting its view. Export is generated from current inputs on request.',
        'Inclut saisies, source/date, chaîne, Greeks, scénario, couverture et courbe ; attribution du risque incluse après ouverture de sa vue. Généré à la demande depuis les saisies courantes.'))
