from app_pages.common import (
    render_module_header,
    render_planned_outputs,
    render_validation_box,
    render_status_badge,
)


def render() -> None:
    render_module_header(
        title="Fixed Income Risk",
        caption="Bond portfolio risk analytics: duration, convexity, DV01, curve shocks, and risk reports.",
        objective=(
            "Objective: help a sales, trader, PM, or risk analyst understand where bond portfolio risk "
            "is concentrated and how the portfolio reacts to yield curve and spread shocks."
        ),
    )

    render_status_badge("Planned — first quantitative module to build")

    render_planned_outputs(
        [
            "Clean price / dirty price",
            "Accrued interest",
            "Yield to maturity",
            "Macaulay and modified duration",
            "Convexity",
            "DV01 by bond",
            "DV01 by maturity bucket",
            "Parallel curve shock P&L",
            "Steepener / flattener scenario P&L",
            "Spread shock P&L",
            "Simple hedge approximation",
            "Excel fixed income risk report",
        ]
    )

    render_validation_box(
        [
            "Clean price plus accrued interest must equal dirty price.",
            "Bond price must fall when yield rises.",
            "DV01 convention must be explicit and consistent.",
            "Portfolio DV01 must equal the sum of position DV01s.",
            "Bucket DV01 percentages must sum to approximately 100%.",
        ]
    )
