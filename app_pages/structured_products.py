from app_pages.common import (
    render_module_header,
    render_planned_outputs,
    render_validation_box,
    render_status_badge,
)


def render() -> None:
    render_module_header(
        title="Structured Products",
        caption="Autocallable note analytics: payoff logic, autocall probability, barrier risk, and factsheets.",
        objective=(
            "Objective: convert structured product terms into clear payoff analysis, scenario results, "
            "autocall probabilities, barrier risk, and client/desk-ready factsheets."
        ),
    )

    render_status_badge("Planned — build after fixed income and repo are stable")

    render_planned_outputs(
        [
            "Athena payoff logic",
            "Phoenix payoff logic",
            "Coupon and memory coupon logic",
            "Observation-date cashflow table",
            "Monte Carlo simulation under simplified GBM",
            "Autocall probability by date",
            "Barrier breach probability",
            "Capital loss probability",
            "Worst-of basket analytics",
            "Spot / volatility / correlation stress",
            "Worst performer contribution table",
            "Structured product factsheet export",
        ]
    )

    render_validation_box(
        [
            "Autocall must trigger only when the relevant barrier condition is met.",
            "Capital loss must apply when final underlying/worst-of is below protection barrier.",
            "Lower spot should reduce autocall probability, all else equal.",
            "Higher volatility should generally increase downside barrier breach probability.",
            "Worst-of performance must equal the minimum performance among underlyings.",
            "The model must not be described as bank-grade pricing.",
        ]
    )
