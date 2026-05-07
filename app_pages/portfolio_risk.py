from app_pages.common import (
    render_module_header,
    render_planned_outputs,
    render_validation_box,
    render_status_badge,
)


def render() -> None:
    render_module_header(
        title="Portfolio Risk",
        caption="Portfolio risk, benchmark-relative analytics, VaR, Expected Shortfall, and R integration.",
        objective=(
            "Objective: create a PM/risk review tool that explains performance, downside risk, "
            "benchmark-relative risk, concentration, and basic optimization outputs."
        ),
    )

    render_status_badge("Planned — Python first, R analytics layer later")

    render_planned_outputs(
        [
            "Annualized return",
            "Annualized volatility",
            "Sharpe ratio",
            "Sortino ratio",
            "Max drawdown",
            "Historical VaR",
            "Expected Shortfall",
            "Tracking error",
            "Information ratio",
            "Benchmark comparison",
            "Risk contribution approximation",
            "R-based rolling risk analytics",
            "Portfolio review Excel report",
        ]
    )

    render_validation_box(
        [
            "Daily volatility must annualize with square root of 252.",
            "VaR and Expected Shortfall sign conventions must be explicit.",
            "Expected Shortfall must be worse than or equal to VaR in loss terms.",
            "Tracking error must equal volatility of active returns.",
            "Portfolio weights must sum to 100%.",
        ]
    )
