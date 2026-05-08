import streamlit as st


def apply_global_styles() -> None:
    """Apply light premium UI styling across the Streamlit app."""

    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2.0rem;
            padding-bottom: 3.0rem;
            max-width: 1380px;
        }

        h1 {
            letter-spacing: -0.045em;
            font-weight: 800 !important;
        }

        h2, h3 {
            letter-spacing: -0.025em;
        }

        [data-testid="stMetric"] {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.035), rgba(59, 130, 246, 0.045));
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 18px;
            padding: 14px 16px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.78rem;
            color: #64748b;
        }

        [data-testid="stMetricValue"] {
            font-weight: 750;
            letter-spacing: -0.03em;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 18px !important;
            border-color: rgba(148, 163, 184, 0.22) !important;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.035);
        }

        .stButton > button,
        .stDownloadButton > button,
        .stLinkButton > a {
            border-radius: 999px !important;
            border: 1px solid rgba(59, 130, 246, 0.38) !important;
            font-weight: 650 !important;
            transition: all 0.15s ease-in-out;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover,
        .stLinkButton > a:hover {
            transform: translateY(-1px);
            border-color: rgba(59, 130, 246, 0.80) !important;
            box-shadow: 0 8px 20px rgba(59, 130, 246, 0.13);
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        section[data-testid="stSidebar"] h1 {
            font-size: 1.25rem !important;
            letter-spacing: -0.035em;
        }

        .stAlert {
            border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
