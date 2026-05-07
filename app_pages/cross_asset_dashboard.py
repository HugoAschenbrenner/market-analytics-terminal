from app_pages.common import (
    render_module_header,
    render_planned_outputs,
    render_validation_box,
    render_status_badge,
)


def render() -> None:
    render_module_header(
        title="Cross-Asset Dashboard",
        caption="Market monitoring dashboard for equities, rates, FX, commodities, volatility, and credit proxies.",
        objective=(
            "Objective: produce a morning-meeting style dashboard that summarizes what moved, "
            "market tone, affected asset classes, and what to watch next."
        ),
    )

    render_status_badge("Planned — build after core risk modules")

    render_planned_outputs(
        [
            "Equity index moves",
            "Rates and curve moves",
            "FX moves",
            "Commodity moves",
            "Volatility regime",
            "Credit proxy moves",
            "Key movers table",
            "Risk-on / risk-off score",
            "Rates-led risk-off detection",
            "Mixed market signal detection",
            "Short market narrative",
            "Morning market snapshot export",
        ]
    )

    render_validation_box(
        [
            "Rates up must be treated as ambiguous unless confirmed by equity/vol/FX reaction.",
            "USD up can reflect risk-off or relative rates advantage.",
            "Oil up can be inflationary or growth-positive depending on context.",
            "Narrative must separate facts from interpretation.",
            "The dashboard must not generate buy/sell signals.",
        ]
    )
