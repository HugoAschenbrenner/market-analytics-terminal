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


        /* Premium sidebar module navigation */
        div[data-testid="stSidebar"] .stMarkdown h5 {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748b;
            margin-top: 0.35rem;
            margin-bottom: 0.20rem;
            font-weight: 800;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 0.32rem;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 14px;
            padding: 0.68rem 0.75rem;
            margin: 0;
            transition: all 0.16s ease-in-out;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            border-color: rgba(59, 130, 246, 0.45);
            background: rgba(239, 246, 255, 0.90);
            transform: translateX(2px);
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
            background: linear-gradient(180deg, #eff6ff 0%, #eaf2ff 100%);
            border-color: rgba(59, 130, 246, 0.55);
            box-shadow: 0 6px 18px rgba(37, 99, 235, 0.12);
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label p {
            font-size: 0.92rem;
            font-weight: 570;
            color: #1f2937;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
            color: #0f3d91;
            font-weight: 750;
        }


        /* Apple-style sidebar navigation */
        div[data-testid="stSidebar"] .stMarkdown h5 {
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #8a8f98;
            margin-top: 0.45rem;
            margin-bottom: 0.35rem;
            font-weight: 700;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 0.18rem;
            margin-top: 0.25rem;
        }

        /* Hide the raw radio dots */
        div[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {
            display: none !important;
        }

        /* Base item */
        div[data-testid="stSidebar"] div[role="radiogroup"] > label {
            background: transparent !important;
            border: 1px solid transparent !important;
            border-radius: 10px !important;
            padding: 0.52rem 0.62rem !important;
            margin: 0 !important;
            min-height: 38px;
            transition: background 0.14s ease-in-out, border-color 0.14s ease-in-out, transform 0.14s ease-in-out;
            box-shadow: none !important;
            cursor: pointer;
        }

        /* Text */
        div[data-testid="stSidebar"] div[role="radiogroup"] > label p {
            font-size: 0.91rem !important;
            font-weight: 520 !important;
            color: #2f343b !important;
            line-height: 1.1rem !important;
        }

        /* Hover: very light Apple-like grey */
        div[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            background: rgba(120, 120, 128, 0.10) !important;
            border-color: rgba(120, 120, 128, 0.04) !important;
            transform: none !important;
        }

        /* Selected item: Apple Finder-style subtle capsule */
        div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
            background: rgba(120, 120, 128, 0.16) !important;
            border-color: rgba(120, 120, 128, 0.08) !important;
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18) !important;
        }

        div[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) p {
            color: #111827 !important;
            font-weight: 700 !important;
        }

        /* Sidebar links: flatter, Apple-like */
        div[data-testid="stSidebar"] .stLinkButton > a {
            border-radius: 10px !important;
            border: 1px solid rgba(120, 120, 128, 0.14) !important;
            background: rgba(255, 255, 255, 0.55) !important;
            box-shadow: none !important;
            font-weight: 600 !important;
        }

        div[data-testid="stSidebar"] .stLinkButton > a:hover {
            background: rgba(120, 120, 128, 0.10) !important;
            border-color: rgba(120, 120, 128, 0.20) !important;
            transform: none !important;
            box-shadow: none !important;
        }


        /* Custom sidebar command menu */
        div[data-testid="stSidebar"] .stMarkdown h5 {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            color: #8a8f98;
            margin-top: 0.4rem;
            margin-bottom: 0.15rem;
            font-weight: 800;
        }

        div[data-testid="stSidebar"] .stButton > button {
            justify-content: flex-start !important;
            text-align: left !important;
            border-radius: 12px !important;
            border: 1px solid transparent !important;
            background: transparent !important;
            color: #2f343b !important;
            box-shadow: none !important;
            min-height: 38px;
            padding: 0.54rem 0.70rem !important;
            font-weight: 560 !important;
            transition: background 0.14s ease-in-out, transform 0.14s ease-in-out;
        }

        div[data-testid="stSidebar"] .stButton > button:hover {
            background: rgba(120, 120, 128, 0.10) !important;
            border-color: rgba(120, 120, 128, 0.06) !important;
            transform: none !important;
            box-shadow: none !important;
        }

        .mat-sidebar-active {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            min-height: 38px;
            padding: 0.54rem 0.70rem;
            margin: 0.16rem 0;
            border-radius: 12px;
            background: rgba(120, 120, 128, 0.16);
            border: 1px solid rgba(120, 120, 128, 0.08);
            color: #111827;
            font-weight: 760;
            line-height: 1.1rem;
        }

        .mat-sidebar-icon {
            width: 1.15rem;
            display: inline-flex;
            justify-content: center;
            color: #111827;
            font-weight: 800;
        }

        .mat-sidebar-label {
            font-size: 0.92rem;
            letter-spacing: -0.01em;
        }


        /* Sidebar hover stability fix: no layout shift */
        div[data-testid="stSidebar"] .stButton > button,
        div[data-testid="stSidebar"] .stButton > button:hover,
        div[data-testid="stSidebar"] .stButton > button:focus,
        div[data-testid="stSidebar"] .stButton > button:active {
            transform: none !important;
            box-shadow: none !important;
        }

        div[data-testid="stSidebar"] .stLinkButton > a,
        div[data-testid="stSidebar"] .stLinkButton > a:hover,
        div[data-testid="stSidebar"] .stLinkButton > a:focus,
        div[data-testid="stSidebar"] .stLinkButton > a:active {
            transform: none !important;
            box-shadow: none !important;
        }

        .mat-sidebar-active,
        .mat-sidebar-active:hover {
            transform: none !important;
            box-shadow: none !important;
        }


        /* Stable Apple-style sidebar links */
        .mat-sidebar-link {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            min-height: 38px;
            padding: 0.54rem 0.70rem;
            margin: 0.12rem 0;
            border-radius: 12px;
            color: #2f343b !important;
            text-decoration: none !important;
            border: 1px solid transparent;
            background: transparent;
            box-shadow: none;
            transition: background-color 0.14s ease-in-out, border-color 0.14s ease-in-out;
        }

        .mat-sidebar-link:hover {
            background: rgba(120, 120, 128, 0.10);
            border-color: rgba(120, 120, 128, 0.06);
            color: #111827 !important;
            text-decoration: none !important;
        }

        .mat-sidebar-link.mat-sidebar-active {
            background: rgba(120, 120, 128, 0.16);
            border-color: rgba(120, 120, 128, 0.08);
            color: #111827 !important;
            font-weight: 760;
        }

        .mat-sidebar-link,
        .mat-sidebar-link:hover,
        .mat-sidebar-link:focus,
        .mat-sidebar-link:active {
            transform: none !important;
            box-shadow: none !important;
        }

        .mat-sidebar-icon {
            width: 1.15rem;
            display: inline-flex;
            justify-content: center;
            color: inherit;
            font-weight: 800;
        }

        .mat-sidebar-label {
            font-size: 0.92rem;
            letter-spacing: -0.01em;
            color: inherit;
        }

        .stAlert {
            border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
