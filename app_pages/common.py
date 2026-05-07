import streamlit as st


def render_module_header(title: str, caption: str, objective: str) -> None:
    st.title(title)
    st.caption(caption)
    st.markdown(objective)
    st.warning(
        "Educational/proxy analytics only. Outputs are simplified and must not be interpreted as "
        "investment advice, trading signals, or bank-grade pricing."
    )


def render_workflow() -> None:
    st.subheader("Desk Workflow")

    cols = st.columns(5)
    steps = [
        ("1", "Input", "Upload or enter product, trade, market, or portfolio data."),
        ("2", "Calculation", "Run transparent pricing, risk, or performance calculations."),
        ("3", "Scenario", "Stress key variables such as rates, spot, volatility, spreads, or haircuts."),
        ("4", "Interpretation", "Explain the main drivers and risk concentration."),
        ("5", "Export", "Generate reusable Excel reports or factsheets."),
    ]

    for col, (number, title, description) in zip(cols, steps):
        with col:
            with st.container(border=True):
                st.caption(number)
                st.markdown(f"### {title}")
                st.write(description)


def render_planned_outputs(outputs: list[str]) -> None:
    st.subheader("Planned Desk Outputs")
    left, right = st.columns(2)

    midpoint = (len(outputs) + 1) // 2
    first_half = outputs[:midpoint]
    second_half = outputs[midpoint:]

    with left:
        for item in first_half:
            st.markdown(f"- {item}")

    with right:
        for item in second_half:
            st.markdown(f"- {item}")


def render_validation_box(items: list[str]) -> None:
    st.subheader("Financial Validation Focus")
    with st.container(border=True):
        for item in items:
            st.markdown(f"- {item}")


def render_status_badge(status: str = "Planned") -> None:
    st.info(f"Status: {status}")
